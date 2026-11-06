"""Objective 3 reports, lineage and manifests.

Writes reports/objective_3/README.md, RUN_REPORT.md, BLOCKED_OR_DEFERRED.md, DATA_LINEAGE.json and FIGURE_MANIFEST.csv.
Every number is read from the database. The gate table comes from the latest VERIFY run; `all` runs verify again after
the report so that the report hashes are re-checked.
"""

from __future__ import annotations

import csv
import importlib.metadata
import io
import json
import platform
from pathlib import Path

from kambale.objective_3 import O3_CODE_VERSION, O3_SCHEMA_VERSION
from kambale.objective_3.features import predictor_sets
from kambale.objective_3.config import (O3_CONFIG_PATH, O3_DB_PATH, O3_FIGURE_DIR, O3_REPORT_DIR, O3_TABLE_DIR,
                                        PROJECT_ROOT, StopError, code_commit, load_config, sha256_bytes, utc_now)
from kambale.objective_3.db import connect_o3
from kambale.objective_3.figures import FIGURES
from kambale.objective_3.tables import TABLES

EXIT_GATES = ("G01", "G02", "G03", "G05", "G08", "G09", "G10", "G11", "G12", "G13", "G15", "G16", "G17", "G19",
              "G20", "G21", "G22", "G25", "G26", "G28")
PYTEST_OUTPUT = O3_REPORT_DIR / "PYTEST_OUTPUT.txt"
COMPOSITES = ("M2_SEL", "M2_WF_SEL")


def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _one(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else {}


def _f(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _versions() -> list[str]:
    out = []
    for pkg in ("numpy", "scipy", "scikit-learn", "matplotlib", "PyYAML", "pytest"):
        try:
            out.append(f"{pkg} {importlib.metadata.version(pkg)}")
        except importlib.metadata.PackageNotFoundError:
            out.append(f"{pkg} not installed")
    return out


def _table_md(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()[1:]


def _manifest_rows(conn, rid: int, report_paths: list[Path]) -> list[dict]:
    rows = []
    for fig in _rows(conn, "SELECT figure_id, status FROM figure_registry ORDER BY figure_id"):
        if fig["status"] != "GENERATED":
            continue
        stem = FIGURES[fig["figure_id"]][1]
        for ext in ("svg", "pdf", "png"):
            path = O3_FIGURE_DIR / f"{stem}.{ext}"
            rows.append({"artifact_path": _rel(path), "kind": "FIGURE", "id": fig["figure_id"],
                         "sha256": sha256_bytes(path.read_bytes()), "bytes": path.stat().st_size,
                         "source": "figure_sql_registry"})
    for tab in _rows(conn, "SELECT table_id, status FROM table_registry ORDER BY table_id"):
        if tab["status"] != "GENERATED":
            continue
        stem = TABLES[tab["table_id"]][1]
        for ext in ("csv", "md", "tex"):
            path = O3_TABLE_DIR / f"{stem}.{ext}"
            rows.append({"artifact_path": _rel(path), "kind": "TABLE", "id": tab["table_id"],
                         "sha256": sha256_bytes(path.read_bytes()), "bytes": path.stat().st_size,
                         "source": "table_sql_registry"})
    for art in _rows(conn, "SELECT artifact_path, artifact_sha256, bytes, training_run_id FROM model_artifacts "
                           "ORDER BY artifact_id"):
        rows.append({"artifact_path": art["artifact_path"], "kind": "MODEL_ARTIFACT", "id": str(art["training_run_id"]),
                     "sha256": art["artifact_sha256"], "bytes": art["bytes"], "source": "model_artifacts"})
    for path in report_paths:
        rows.append({"artifact_path": _rel(path), "kind": "REPORT", "id": path.stem,
                     "sha256": sha256_bytes(path.read_bytes()), "bytes": path.stat().st_size, "source": "report"})
    return rows


def _write_manifest(path: Path, rows: list[dict]) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["artifact_path", "kind", "id", "sha256", "bytes", "source"],
                            lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")


def _gate_table(gates: list[dict]) -> list[str]:
    out = ["| gate | name | status | detail |", "|---|---|---|---|"]
    for g in gates:
        out.append(f"| {g['gate_id']} | {g['gate_name']} | {g['status']} | {g['detail'].replace('|', '\\|')} |")
    return out


def _tier_summary(conn, plan: dict, cfg: dict) -> dict:
    """Everything the report states about one split plan, read from the database."""
    pid = plan["split_plan_id"]
    runs = _rows(conn, "SELECT * FROM training_runs WHERE split_plan_id = ? ORDER BY fold_id, family_id, candidate_run_id",
                 (pid,))
    composites = {(r["fold_id"], r["family_id"]): r for r in runs if r["family_id"] in COMPOSITES}
    m1 = {r["fold_id"]: r for r in runs if r["family_id"] == "M1_IK"}
    m3 = {r["fold_id"]: r for r in runs if r["family_id"] == "M3_HYBRID"}
    trials_n = {r["training_run_id"]: r["n"] for r in _rows(
        conn, "SELECT training_run_id, COUNT(*) n FROM hyperparameter_trials GROUP BY training_run_id")}
    pure_folds = []
    m1_lines = []
    for f in sorted(m1):
        hp = json.loads(m1[f]["hyperparameters_json"] or "{}")
        label = hp.get("covariance_label", m1[f]["status"])
        pure = (hp.get("covariance") or {}).get("covariance") == "PURE_NUGGET"
        if pure:
            pure_folds.append(f)
        m1_lines.append({"fold_id": f, "status": m1[f]["status"], "label": label, "pure": pure,
                         "inner": m1[f]["inner_cv_score"], "trials": trials_n.get(m1[f]["training_run_id"], 0)})
    m3_lines = []
    for f in sorted(m3):
        hp = json.loads(m3[f]["hyperparameters_json"] or "{}")
        m3_lines.append({"fold_id": f, "status": m3[f]["status"], "label": hp.get("residual_covariance_label", "n/a"),
                         "fallback": hp.get("fallback", "n/a"), "trend": hp.get("trend_candidate", "n/a"),
                         "trials": trials_n.get(m3[f]["training_run_id"], 0)})
    sel_lines = []
    for f in sorted({r["fold_id"] for r in runs}):
        row = {"fold_id": f}
        for name in COMPOSITES:
            r = composites.get((f, name))
            if r is None:
                row[name] = "n/a"
                row[name + "_score"] = None
            else:
                hp = json.loads(r["hyperparameters_json"] or "{}")
                row[name] = f"{hp.get('selected_candidate', 'none')} ({r['status']})"
                row[name + "_score"] = r["inner_cv_score"]
        sel_lines.append(row)
    fam_counts = _rows(conn, "SELECT family_id, COUNT(*) n, SUM(clipped_calibrated) clipped FROM predictions_oof "
                             "WHERE split_plan_id = ? GROUP BY family_id ORDER BY family_id", (pid,))
    fails = _rows(conn, "SELECT family_id, COUNT(*) n FROM prediction_failures WHERE split_plan_id = ? "
                        "GROUP BY family_id ORDER BY family_id", (pid,))
    return {"split_plan_id": pid, "method": plan["method"], "primary": int(plan["primary_plan"]) == 1,
            "n_folds": plan["n_folds"], "plan_sha256": plan["plan_sha256"], "selected": sel_lines,
            "m1": m1_lines, "m3": m3_lines, "pure_m1_folds": pure_folds,
            "m3_fallback_folds": [r["fold_id"] for r in m3_lines if r["status"] == "FALLBACK"],
            "fam_counts": fam_counts, "fails": fails}


def write_all(o3_path=O3_DB_PATH) -> dict:
    cfg, cfg_sha = load_config(O3_CONFIG_PATH)
    conn = connect_o3(o3_path)
    try:
        rc = _one(conn, "SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1")
        if not rc:
            raise StopError("no receipt: run the import first")
        rid = rc["receipt_id"]
        plans = _rows(conn, "SELECT * FROM spatial_split_plans ORDER BY primary_plan DESC, split_plan_id")
        primary_plan = next(p for p in plans if int(p["primary_plan"]) == 1)
        plan = primary_plan["split_plan_id"]
        vr = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'VERIFY' ORDER BY run_id DESC LIMIT 1")
        if not vr:
            raise StopError("no VERIFY run: run verify before report")
        gates = _rows(conn, "SELECT gate_id, gate_name, status, scope, detail FROM gate_results WHERE run_id = ? "
                            "ORDER BY gate_id", (vr["run_id"],))
        status = {g["gate_id"]: g["status"] for g in gates}
        exit_failed = [g for g in EXIT_GATES if status.get(g) != "PASS"]
        stopped = any(g["status"] == "STOP" for g in gates)
        target = _one(conn, "SELECT * FROM target_registries WHERE receipt_id = ? ORDER BY target_id LIMIT 1", (rid,))
        label = _one(conn, "SELECT * FROM label_versions WHERE receipt_id = ? LIMIT 1", (rid,))
        geom = _one(conn, "SELECT * FROM geometry_versions WHERE receipt_id = ? LIMIT 1", (rid,))
        tiers = [_tier_summary(conn, p, cfg) for p in plans]
        leakage = _rows(conn, "SELECT check_name, status, detail FROM leakage_audit_log ORDER BY audit_id")
        artifacts = _one(conn, "SELECT COUNT(*) n, SUM(bytes) b FROM model_artifacts")
        pytest_text = PYTEST_OUTPUT.read_text(encoding="utf-8").strip() if PYTEST_OUTPUT.exists() else (
            "Not recorded. Run pytest with its output written to reports/objective_3/PYTEST_OUTPUT.txt and run report again.")
        created = utc_now()
        import_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'IMPORT' AND receipt_id = ? "
                                "ORDER BY run_id DESC LIMIT 1", (rid,))
        split_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'SPLITS' AND receipt_id = ? "
                               "ORDER BY run_id DESC LIMIT 1", (rid,))
        train_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'TRAIN' AND receipt_id = ? "
                               "ORDER BY run_id DESC LIMIT 1", (rid,))
        n_obs = conn.execute("SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = ?", (rid,)).fetchone()[0]
        holes = conn.execute("SELECT COUNT(DISTINCT hole_id) FROM analysis_observations WHERE receipt_id = ?", (rid,)).fetchone()[0]
        lines = conn.execute("SELECT COUNT(DISTINCT line_code) FROM analysis_observations WHERE receipt_id = ?", (rid,)).fetchone()[0]
        trials = conn.execute("SELECT COUNT(*) FROM hyperparameter_trials").fetchone()[0]
        tier_names = ", ".join(f"{t['split_plan_id']} ({t['method']})" for t in tiers)

        # Tables are written before the manifest, so their hashes can be listed.
        from kambale.objective_3 import tables as tables_mod
        table_summary = tables_mod.render_all(o3_path, split_plan_id=plan)
        tables = _rows(conn, "SELECT table_id, title, status, row_count, reason FROM table_registry ORDER BY table_id")

        readme = [
            "# Objective 3 outputs", "",
            "Indicator geostatistics, machine learning and hybrid occurrence models at the Kambale deposit. The stage reads "
            "Objective 1 (geology, labels, geometry) and Objective 2 (support and the continuity handoff) read-only and "
            "writes database/kambale_obj3_models.sqlite.", "",
            f"Current status: {'STOPPED' if stopped else ('exit conditions met' if not exit_failed else 'exit conditions not met')}.",
            f"Handoff to Objective 4: {'blocked by a STOP gate' if stopped else 'out-of-fold predictions and failure masks frozen for both split plans'}.",
            f"Objective 2 continuity handoff: {rc['o2_handoff_status']} (candidate family {rc['o2_candidate_family']}).", "",
            "Contents:", "",
            "- RUN_REPORT.md: the run, its models, gates, limitations and the Objective 4 handoff.",
            "- BLOCKED_OR_DEFERRED.md: every warning, failure, skip and deferred item.",
            "- DATA_LINEAGE.json: upstream receipts, configuration, code and output hashes.",
            "- FIGURE_MANIFEST.csv: SHA-256 and registered SQL for every figure and table file.",
            "- ../../figures/objective_3 and ../../tables/objective_3: the outputs.", "",
            "Reproduce with the commands in RUN_REPORT.md section 12.",
        ]
        readme_path = O3_REPORT_DIR / "README.md"
        readme_path.write_text("\n".join(readme) + "\n", encoding="utf-8", newline="\n")

        body = []
        body += ["# Objective 3 run report: indicator geostatistics, machine learning and hybrid occurrence models", "",
                 f"Configuration {cfg['config_version']} (SHA-256 {cfg_sha[:12]}), code {O3_CODE_VERSION}, schema "
                 f"{O3_SCHEMA_VERSION}, commit {code_commit()}. Import run {import_run.get('run_id')}, split run "
                 f"{split_run.get('run_id')}, training run {train_run.get('run_id')}, gate run {vr['run_id']}. "
                 f"Report written {created}.", "",
                 "## 1. Status", "",
                 ("A STOP gate failed. The run is stopped and the Objective 4 handoff is withheld." if stopped else
                  ("Every required exit gate is PASS." if not exit_failed else
                   "Exit gates not met: " + ", ".join(exit_failed) + ".")),
                 f"Objective 2 continuity handoff: **{rc['o2_handoff_status']}**, candidate family "
                 f"**{rc['o2_candidate_family']}**. Because no continuity model is identified, every M1 and M3 covariance "
                 "below is chosen by inner cross-validation from a predeclared grid, and a pure-nugget choice is reported "
                 "as such.", ""]
        body += ["## 2. Inputs and receipt", "",
                 f"- Objective 1 snapshot: {rc['upstream_path']} (read-only; dataset version "
                 f"{rc['upstream_dataset_version_id']}, ETL {rc['upstream_etl_version']}, content SHA-256 "
                 f"{rc['content_sha256'][:12]}).",
                 f"- Objective 2 receipt {rc['o2_receipt_id']} at {rc['o2_path']}, content SHA-256 "
                 f"{rc['o2_content_sha256'][:12]}, handoff {rc['o2_handoff_id']} ({rc['o2_handoff_status']}).",
                 f"- Intervals imported: {n_obs}; holes {holes}; approved drill lines {lines}.",
                 f"- Label rule {rc['label_rule_id']} {rc['label_rule_status']}; binary target {target.get('binary_n')} "
                 f"({target.get('positive_n')} POSITIVE, {target.get('negative_n')} NEGATIVE); excluded "
                 f"{target.get('ambiguous_n')} AMBIGUOUS and {target.get('unresolved_n')} UNRESOLVED.",
                 f"- Geometry {geom.get('geometry_status')}, vertical basis {geom.get('vertical_basis')}; z_absolute_used="
                 f"{geom.get('z_absolute_used')}. Coordinates {geom.get('crs_key')}, datum {geom.get('datum_status')}.", ""]
        sets = predictor_sets(cfg)
        body += ["## 3. Configuration", "",
                 f"Predeclared version {cfg['config_version']} (supersedes {cfg.get('supersedes')}). Predictor sets: "
                 + "; ".join(f"{k} = {', '.join(v)}" for k, v in sets.items()) + ". The depth below the weathering front "
                 "is a fold-safe inverse-distance surface built from training holes only (see section 5).",
                 f"Two validation tiers are run: {tier_names}. The primary tier is {plan}; the second tier is an "
                 "interpolation check at one hole spacing. Both are reported; neither is pooled with the other.",
                 f"Inner tuning is {cfg['inner_cv']['method']} with {cfg['inner_cv']['n_folds']} folds, selecting the lowest mean "
                 "log loss. The decision threshold is the inner-CV Youden-J maximum; ties go to the threshold closest to 0.5. "
                 "M2_SEL and M2_WF_SEL copy the inner-selected member of their pair. M1 and M3 covariances come from the "
                 f"grid of range {cfg['kriging']['grid']['range_m']} m by nugget fraction {cfg['kriging']['grid']['nugget_fraction']}, "
                 "plus PURE_NUGGET.",
                 f"Random forest and {cfg['models']['gradient_boosting']['implementation']} are the two M2 estimators; "
                 "XGBoost is not installed in the verified environment. Logistic regression and training prevalence are "
                 "the baselines.", ""]
        body += ["## 4. Frozen spatial splits", ""]
        for i, t in enumerate(tiers, start=1):
            audits = _rows(conn, "SELECT * FROM split_audit WHERE split_plan_id = ? ORDER BY fold_id", (t["split_plan_id"],))
            body += [f"### 4.{i} {t['split_plan_id']} ({t['method']}{', primary' if t['primary'] else ', second tier'})",
                     "", f"Plan hash {t['plan_sha256']}.", "",
                     "| fold | test lines | test holes | test intervals | test positive | train intervals | min collar distance (m) | audit |",
                     "|---|---|---|---|---|---|---|---|"]
            for a in audits:
                test_lines = conn.execute("SELECT GROUP_CONCAT(DISTINCT line_code) FROM split_membership WHERE "
                                          "split_plan_id = ? AND fold_id = ? AND role = 'TEST'",
                                          (t["split_plan_id"], a["fold_id"])).fetchone()[0]
                body.append(f"| {a['fold_id']} | {test_lines} | {a['test_holes']} | {a['n_test']} | {a['test_positive']} | "
                            f"{a['n_train']} | {_f(a['min_train_test_collar_distance_m'], 1)} | {a['status']} |")
            body.append("")
        body += ["## 5. Models and training-only diagnostics", ""]
        for i, t in enumerate(tiers, start=1):
            body += [f"### 5.{i} {t['split_plan_id']}", "",
                     "Selected trend candidates by inner-CV log loss (the composites are the selection records):", "",
                     "| fold | M2_SEL (from plain pair) | inner CV | M2_WF_SEL (from weathering-front pair) | inner CV |",
                     "|---|---|---|---|---|"]
            for s in t["selected"]:
                body.append(f"| {s['fold_id']} | {s['M2_SEL']} | {_f(s['M2_SEL_score'], 4)} | {s['M2_WF_SEL']} | "
                            f"{_f(s['M2_WF_SEL_score'], 4)} |")
            body += ["", "M1 indicator kriging: covariance chosen by inner CV per fold.", "",
                     "| fold | status | chosen covariance | inner-CV log loss | trials recorded |", "|---|---|---|---|---|"]
            for m in t["m1"]:
                body.append(f"| {m['fold_id']} | {m['status']} | {m['label']} | {_f(m['inner'], 4)} | {m['trials']} |")
            body += ["", "M3 hybrid on the calibrated M2_WF_SEL trend: residual covariance and status per fold.", "",
                     "| fold | trend | status | residual covariance | fallback | trials recorded |", "|---|---|---|---|---|---|"]
            for m in t["m3"]:
                body.append(f"| {m['fold_id']} | {m['trend']} | {m['status']} | {m['label']} | {m['fallback']} | {m['trials']} |")
            pure = t["pure_m1_folds"]
            body += ["", (f"Pure-nugget M1 (equal to the training prevalence) in folds {pure}." if pure else
                          "M1 selected a spatial covariance in every fold."),
                     (f"M3 is recorded as FALLBACK_ML_ONLY in folds {t['m3_fallback_folds']}; there it is identical to "
                      "M2_WF_SEL and is not a hybrid result." if t["m3_fallback_folds"] else
                      "M3 used a kriged residual in every fold (HYBRID_USED)."), "",
                     "Out-of-fold prediction counts for this tier (no outer performance is computed here; Objective 4 "
                     "evaluates):", "", "| family | predictions | clipped (calibrated) | failures |", "|---|---|---|---|"]
            fails = {f["family_id"]: f["n"] for f in t["fails"]}
            for p in t["fam_counts"]:
                body.append(f"| {p['family_id']} | {p['n']} | {p['clipped'] or 0} | {fails.get(p['family_id'], 0)} |")
            body.append("")
        body += ["Inner scores are whole-hole cross-validation log losses on the outer training folds. They are selection "
                 f"diagnostics, not held-out performance. {trials} hyperparameter trials were recorded across both tiers.", ""]
        body += ["## 6. Gate results", ""]
        body += _gate_table(gates)
        body += ["", f"Exit gates: {', '.join(EXIT_GATES)}. {'All exit gates PASS.' if not exit_failed else 'Failing exit gates: ' + ', '.join(exit_failed) + '.'}", ""]
        body += ["## 7. Tables", ""]
        for tb in tables:
            body.append(f"- {tb['table_id']}: {tb['status']}, {tb['row_count']} rows; {tb['title']}.")
        body += ["", "The rendered tables are in tables/objective_3 as CSV, Markdown and LaTeX.", ""]
        body += ["## 8. Figures", "",
                 f"Figures F01 to F05 show the primary tier {plan}. F06 shows the covariance selection of both tiers' "
                 "M1 and M3 fits per fold.", ""]
        figures = _rows(conn, "SELECT figure_id, title, status, reason FROM figure_registry ORDER BY figure_id")
        for f in figures:
            body.append(f"- {f['figure_id']} ({f['status']}): {f['title']}. {f['reason']}.")
        body += ["", "", "## 9. Tests", "", "```text", pytest_text, "```", ""]
        body += ["## 10. Deviations, warnings and limitations", "",
                 "- The fold-safe weathering-front predictor is an inverse-distance surface of the front heights of the "
                 "training holes. It is a modelled, not an observed, front at a grid cell; it is not a geological "
                 "covariate measured at the prediction location.",
                 "- The front is defined only where the log records a mw or sw interval; every hole in this snapshot carries one.",
                 "- The covariance grid is predeclared; the chosen covariance is per fold and can differ between folds.",
                 "- XGBoost is not installed; scikit-learn's histogram gradient boosting is the declared fallback.",
                 "- The final full-data refit is PENDING_O4. Objective 3 does not fit on all observations and does not call "
                 "that fit spatially validated.",
                 "- The code commit is the last committed revision; the Objective 3 working tree is deliberately not "
                 "committed. The configuration hash, SQL hashes and artifact hashes identify the exact run.",
                 ""]
        body += ["## 11. Objective 4 handoff contract", ""]
        for t in tiers:
            body.append(f"- Split plan `{t['split_plan_id']}` ({t['method']}, primary={int(t['primary'])}), hash "
                        f"`{t['plan_sha256']}`, {t['n_folds']} folds.")
        body += [f"- Target: `{target.get('target_id')}`, rule {target.get('label_rule_id')} {target.get('label_rule_status')}, "
                 f"{target.get('binary_n')} binary intervals.",
                 f"- Geometry: `{geom.get('geometry_version_id')}`, {geom.get('geometry_status')}, vertical basis "
                 f"{geom.get('vertical_basis')}, z_absolute_used=0.",
                 "- Predictions: `predictions_oof`, one row per (training run, held-out interval), with `p_raw`, "
                 "`p_calibrated`, clipping flags, training-selected threshold and predicted class. The composites M2_SEL and "
                 "M2_WF_SEL and the hybrid M3_HYBRID are written as their own runs.",
                 "- Failures: `prediction_failures`, one row per (plan, fold, held-out interval, family) that could not be predicted.",
                 "- Fits and diagnostics: `training_runs`, `hyperparameter_trials` (every covariance grid point for M1 and M3), "
                 "`variogram_training_fits` and `hybrid_residual_variogram` (the chosen covariance per fold), `calibration_fits`, "
                 "`residual_diagnostics`.",
                 "- Artifacts: `model_artifacts`, parameter and provenance records with SHA-256.",
                 "- Selection policy: inner whole-hole CV log loss; no outer test result was used to select a model, a "
                 "covariance or a threshold. O4 may evaluate and rank, but must not refit models or change the splits.",
                 "- Final refit: `final_refits` row PENDING_O4. After O4 locks selection, Objective 3 must refit the selected "
                 "pipeline on all eligible approved observations and hash the artifact; that fit is not spatially validated.",
                 ""]
        body += ["## 12. Commands and environment", "",
                 "```bash", "./.venv/Scripts/python.exe -I -m kambale.objective_3 all",
                 "./.venv/Scripts/python.exe -I -m pytest -o addopts= -q tests/objective_3 > reports/objective_3/PYTEST_OUTPUT.txt",
                 "./.venv/Scripts/python.exe -I -m kambale.objective_3 report",
                 "./.venv/Scripts/python.exe -I -m kambale.objective_3 verify", "```", "",
                 "`all` runs import, splits, train, verify, figures, tables, verify, report and verify. A STOP at a verify "
                 "step ends the run before the next write.", "",
                 f"Python {platform.python_version()} on {platform.platform()}; " + "; ".join(_versions()) + ".", ""]
        body += ["## 13. Database row counts and receipts", "", "| table | rows |", "|---|---|"]
        table_names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        for n in table_names:
            body.append(f"| {n} | {conn.execute('SELECT COUNT(*) FROM \"' + n + '\"').fetchone()[0]} |")
        body += ["", "Counts are taken when this report is written. The post-report VERIFY run adds one `stage_runs` row and "
                     "one gate set; that run is the authoritative final check and its gate rows are in the database.",
                 "", f"O1 receipt content SHA-256: {rc['content_sha256']}. O2 receipt {rc['o2_receipt_id']} content SHA-256: "
                     f"{rc['o2_content_sha256']}. Ordered identifier digest: {rc['ordered_id_digest']}. Selection query "
                     f"SHA-256: {rc['selection_query_sha256']}.", ""]
        run_path = O3_REPORT_DIR / "RUN_REPORT.md"
        run_path.write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")

        blocked = ["# Objective 3: blocked, skipped, failed and deferred items", "",
                   f"Gate results are from VERIFY run {vr['run_id']}. Every WARN, SKIP, STOP and model failure is listed.", "",
                   "## Gates with a warning or a stop", ""]
        flagged = [g for g in gates if g["status"] != "PASS"]
        if flagged:
            blocked += ["| gate | status | detail |", "|---|---|---|"]
            for g in flagged:
                blocked.append(f"| {g['gate_id']} {g['gate_name']} | {g['status']} | {g['detail'].replace('|', chr(92) + '|')} |")
        else:
            blocked.append("- none")
        blocked += ["", "## Model failures and fallbacks", ""]
        fallback_rows = _rows(conn, "SELECT split_plan_id, fold_id, family_id, candidate_run_id, status, reason FROM "
                                    "training_runs WHERE status <> 'COMPLETED' ORDER BY split_plan_id, fold_id, family_id")
        for r in fallback_rows:
            blocked.append(f"- {r['split_plan_id']} fold {r['fold_id']} {r['candidate_run_id']}: {r['status']}: {r['reason']}")
        blocked += ["", "## Leakage audit", ""]
        for c in leakage:
            blocked.append(f"- {c['status']} {c['check_name']}: {c['detail']}")
        blocked += ["", "## Deferred work (not performed in this stage)", ""]
        for t in tiers:
            if t["pure_m1_folds"]:
                blocked.append(f"- {t['split_plan_id']}: M1 is the training prevalence in folds {t['pure_m1_folds']} "
                               "(pure-nugget covariance selected by inner CV).")
            if t["m3_fallback_folds"]:
                blocked.append(f"- {t['split_plan_id']}: M3 is the ML-only fallback in folds {t['m3_fallback_folds']}; it is "
                               "not a validated hybrid.")
        blocked += ["- Outer-test evaluation and model ranking: Objective 4.",
                    "- Final full-data refit: PENDING_O4.",
                    "- Geological covariates: none exist at prediction locations beyond the fold-safe front surface.",
                    "- Absolute elevation: no collar RL; no DEM and no absolute-Z product.",
                    "- XGBoost: not installed; sklearn histogram gradient boosting is the declared fallback.",
                    "- Commit and push: not done; this waits for the user's instruction.", ""]
        blocked_path = O3_REPORT_DIR / "BLOCKED_OR_DEFERRED.md"
        blocked_path.write_text("\n".join(blocked) + "\n", encoding="utf-8", newline="\n")

        lineage = {
            "objective": 3,
            "code_version": O3_CODE_VERSION,
            "schema_version": O3_SCHEMA_VERSION,
            "config_version": cfg["config_version"],
            "config_sha256": cfg_sha,
            "code_commit": code_commit(),
            "working_tree_committed": False,
            "created_utc": created,
            "upstream": {
                "objective_1": {"path": rc["upstream_path"], "dataset_version_id": rc["upstream_dataset_version_id"],
                                "dataset_version_key": rc["upstream_dataset_version_key"],
                                "content_sha256": rc["content_sha256"], "row_count": rc["row_count"]},
                "objective_2": {"path": rc["o2_path"], "receipt_id": rc["o2_receipt_id"],
                                "content_sha256": rc["o2_content_sha256"], "handoff_id": rc["o2_handoff_id"],
                                "handoff_status": rc["o2_handoff_status"], "candidate_family": rc["o2_candidate_family"]},
            },
            "runs": {"import": import_run.get("run_id"), "splits": split_run.get("run_id"),
                     "train": train_run.get("run_id"), "verify": vr["run_id"]},
            "target": target, "label_version": label, "geometry_version": geom,
            "split_plans": plans,
            "tiers": [{k: v for k, v in t.items() if k not in ("fam_counts", "fails")} for t in tiers],
            "model_artifacts": {"count": artifacts.get("n"), "bytes": artifacts.get("b")},
            "figures": figures, "tables": tables,
            "output_hashes": [{"path": r["artifact_path"], "sha256": r["sha256"], "bytes": r["bytes"]}
                              for r in _manifest_rows(conn, rid, [])],
        }
        lineage_path = O3_REPORT_DIR / "DATA_LINEAGE.json"
        lineage_path.write_text(json.dumps(lineage, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8",
                                newline="\n")

        report_paths = [readme_path, run_path, blocked_path, lineage_path]
        rows = _manifest_rows(conn, rid, report_paths)
        manifest_path = O3_REPORT_DIR / "FIGURE_MANIFEST.csv"
        _write_manifest(manifest_path, rows)
        # Register the report files and the manifest itself; the manifest does not list itself.
        conn.execute("DELETE FROM export_manifests WHERE artifact_kind IN ('REPORT','MANIFEST')")
        for path in report_paths + [manifest_path]:
            conn.execute("INSERT INTO export_manifests (artifact_path, artifact_kind, artifact_id, sha256, bytes, "
                         "created_utc) VALUES (?, ?, ?, ?, ?, ?)",
                         (_rel(path), "REPORT" if path.suffix != ".csv" else "MANIFEST", path.stem,
                          sha256_bytes(path.read_bytes()), path.stat().st_size, created))
        return {"status": "STOPPED" if stopped else "COMPLETE", "exit_failed": exit_failed,
                "figures": {f["figure_id"]: f["status"] for f in figures},
                "tables": table_summary, "report": _rel(run_path), "manifest": _rel(manifest_path)}
    finally:
        conn.close()

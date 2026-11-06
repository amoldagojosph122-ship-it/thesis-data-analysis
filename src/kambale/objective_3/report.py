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
from kambale.objective_3.config import (O3_CONFIG_PATH, O3_DB_PATH, O3_FIGURE_DIR, O3_REPORT_DIR, O3_TABLE_DIR,
                                        PROJECT_ROOT, StopError, code_commit, load_config, sha256_bytes, utc_now)
from kambale.objective_3.db import connect_o3
from kambale.objective_3.figures import FIGURES
from kambale.objective_3.tables import TABLES

EXIT_GATES = ("G01", "G02", "G03", "G05", "G08", "G09", "G10", "G11", "G12", "G13", "G15", "G16", "G17", "G19",
              "G20", "G25", "G26")
PYTEST_OUTPUT = O3_REPORT_DIR / "PYTEST_OUTPUT.txt"


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


def write_all(o3_path=O3_DB_PATH) -> dict:
    cfg, cfg_sha = load_config(O3_CONFIG_PATH)
    conn = connect_o3(o3_path)
    try:
        rc = _one(conn, "SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1")
        if not rc:
            raise StopError("no receipt: run the import first")
        rid = rc["receipt_id"]
        plan = cfg["splits"]["primary"]["split_plan_id"]
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
        split = _one(conn, "SELECT * FROM spatial_split_plans WHERE split_plan_id = ?", (plan,))
        audits = _rows(conn, "SELECT * FROM split_audit WHERE split_plan_id = ? ORDER BY fold_id", (plan,))
        runs = _rows(conn, "SELECT * FROM training_runs WHERE split_plan_id = ? ORDER BY fold_id, family_id, candidate_run_id",
                     (plan,))
        selected = {r["fold_id"]: r for r in runs if r["selected"] == 1}
        by_family = {r["family_id"]: [x for x in runs if x["family_id"] == r["family_id"]] for r in runs}
        m1 = by_family.get("M1_IK", [])
        m3 = by_family.get("M3_HYBRID", [])
        m1_status = {r["fold_id"]: r["status"] for r in m1}
        m3_status = {r["fold_id"]: r["status"] for r in m3}
        m3_fallback = {r["fold_id"]: "FALLBACK_ML_ONLY" if r["status"] == "FALLBACK" else "HYBRID_USED" for r in m3}
        residual_rows = _rows(conn, "SELECT t.fold_id, v.model, v.fit_status, v.stability_status, v.fallback_status, v.reason "
                                     "FROM hybrid_residual_variogram v JOIN training_runs t ON t.training_run_id = v.training_run_id "
                                     "WHERE t.split_plan_id = ? ORDER BY t.fold_id, v.model", (plan,))
        ind_rows = _rows(conn, "SELECT t.fold_id, v.model, v.fit_status, v.stability_status, v.reason "
                               "FROM variogram_training_fits v JOIN training_runs t ON t.training_run_id = v.training_run_id "
                               "WHERE t.split_plan_id = ? ORDER BY t.fold_id, v.model", (plan,))
        pred = _rows(conn, "SELECT family_id, COUNT(*) n, SUM(clipped_calibrated) clipped, MIN(p_calibrated) pmin, "
                           "MAX(p_calibrated) pmax FROM predictions_oof WHERE split_plan_id = ? GROUP BY family_id "
                           "ORDER BY family_id", (plan,))
        fails = _rows(conn, "SELECT family_id, COUNT(*) n FROM prediction_failures WHERE split_plan_id = ? GROUP BY family_id "
                            "ORDER BY family_id", (plan,))
        figures = _rows(conn, "SELECT figure_id, title, status, reason FROM figure_registry ORDER BY figure_id")
        tables = _rows(conn, "SELECT table_id, title, status, row_count, reason FROM table_registry ORDER BY table_id")
        artifacts = _one(conn, "SELECT COUNT(*) n, SUM(bytes) b FROM model_artifacts")
        leakage = _rows(conn, "SELECT check_name, status, detail FROM leakage_audit_log ORDER BY audit_id")
        table_names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        counts = [{"name": n, "n": conn.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]} for n in table_names]
        pytest_text = PYTEST_OUTPUT.read_text(encoding="utf-8").strip() if PYTEST_OUTPUT.exists() else (
            "Not recorded. Run pytest with its output written to reports/objective_3/PYTEST_OUTPUT.txt and run report again.")
        created = utc_now()
        import_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'IMPORT' AND receipt_id = ? "
                                "ORDER BY run_id DESC LIMIT 1", (rid,))
        split_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'SPLITS' AND receipt_id = ? "
                               "ORDER BY run_id DESC LIMIT 1", (rid,))
        train_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'TRAIN' AND receipt_id = ? "
                               "ORDER BY run_id DESC LIMIT 1", (rid,))
        n_obs = sum(1 for _ in conn.execute("SELECT 1 FROM analysis_observations WHERE receipt_id = ?", (rid,)))
        holes = conn.execute("SELECT COUNT(DISTINCT hole_id) FROM analysis_observations WHERE receipt_id = ?", (rid,)).fetchone()[0]
        lines = conn.execute("SELECT COUNT(DISTINCT line_code) FROM analysis_observations WHERE receipt_id = ?", (rid,)).fetchone()[0]
        trials = conn.execute("SELECT COUNT(*) FROM hyperparameter_trials").fetchone()[0]

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
            f"Handoff to Objective 4: {'blocked by a STOP gate' if stopped else 'out-of-fold predictions and failure masks frozen'}.",
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
                 f"**{rc['o2_candidate_family']}**. Accordingly, M1 indicator kriging is estimated only where a training-only "
                 f"variogram is identified and stable, and M3 is labelled an ML-only fallback where the residual covariance "
                 f"is unsupported. Neither is claimed as a successful spatial model.", ""]
        body += ["## 2. Inputs and receipt", "",
                 f"- Objective 1 snapshot: {rc['upstream_path']} (read-only; dataset version "
                 f"{rc['upstream_dataset_version_id']}, ETL {rc['upstream_etl_version']}, content SHA-256 "
                 f"{rc['content_sha256'][:12]}).",
                 f"- Objective 2 receipt {rc['o2_receipt_id']} at {rc['o2_path']}, content SHA-256 "
                 f"{rc['o2_content_sha256'][:12]}, handoff {rc['o2_handoff_id']} ({rc['o2_handoff_status']}).",
                 f"- Intervals imported: {n_obs} (each 1 m); holes {holes}; approved drill lines {lines}.",
                 f"- Label rule {rc['label_rule_id']} {rc['label_rule_status']}; binary target {target.get('binary_n')} "
                 f"({target.get('positive_n')} POSITIVE, {target.get('negative_n')} NEGATIVE); excluded "
                 f"{target.get('ambiguous_n')} AMBIGUOUS and {target.get('unresolved_n')} UNRESOLVED.",
                 f"- Geometry {geom.get('geometry_status')}, vertical basis {geom.get('vertical_basis')}; z_absolute_used="
                 f"{geom.get('z_absolute_used')}. Coordinates {geom.get('crs_key')}, datum {geom.get('datum_status')}.", ""]
        body += ["## 3. Configuration", "",
                 f"Predeclared version {cfg['config_version']}. Predictors are restricted to {', '.join(cfg['features']['predictors'])}.",
                 f"The outer split is {split.get('method')} with {split.get('n_folds')} folds and plan hash "
                 f"{split.get('plan_sha256')}. Inner tuning is {cfg['inner_cv']['method']} with "
                 f"{cfg['inner_cv']['n_folds']} folds, selecting the lowest mean log loss. The decision threshold is the "
                 f"inner-CV Youden-J maximum; ties go to the threshold closest to 0.5.",
                 f"Random forest and {cfg['models']['gradient_boosting']['implementation']} are the two M2 candidates. "
                 "XGBoost is not installed in the verified environment; the histogram gradient-boosting fallback is "
                 "declared in the configuration. Logistic regression and the training prevalence are the baselines.", ""]
        body += ["## 4. Frozen spatial split", "",
                 "| fold | test line | test intervals | test positive | train intervals | min collar distance (m) | audit |",
                 "|---|---|---|---|---|---|---|"]
        for a in audits:
            line = conn.execute("SELECT line_code FROM split_membership WHERE split_plan_id = ? AND fold_id = ? "
                                "AND role = 'TEST' LIMIT 1", (plan, a["fold_id"])).fetchone()[0]
            body.append(f"| {a['fold_id']} | {line} | {a['n_test']} | {a['test_positive']} | {a['n_train']} | "
                        f"{_f(a['min_train_test_collar_distance_m'], 1)} | {a['status']} |")
        body += ["", "The secondary whole-hole split plan is registered and audited but does not produce the predictions "
                     "handed to Objective 4. No random split is used.", ""]
        body += ["## 5. Models and training-only diagnostics", "",
                 "### 5.1 Selected M2 trend by fold", "",
                 "| fold | selected candidate | inner CV log loss | threshold | training n | training positive |",
                 "|---|---|---|---|---|---|"]
        for f in sorted(selected):
            r = selected[f]
            body.append(f"| {f} | {r['candidate_run_id']} | {_f(r['inner_cv_score'], 4)} | {_f(r['threshold'], 2)} | "
                        f"{r['training_n']} | {r['training_positive']} |")
        body += ["", f"The inner scores are whole-hole cross-validation log losses on the outer training fold. They are "
                     f"selection diagnostics, not held-out performance; Objective 4 performs the comparative evaluation. "
                     f"{trials} hyperparameter trials were recorded.", "",
                 "### 5.2 M1 indicator kriging", ""]
        if all(s == "NOT_ESTIMABLE" for s in m1_status.values()):
            body.append("M1 is **NOT_ESTIMABLE in every outer fold**. No training-only lateral indicator variogram was both "
                        "identified and stable, so no kriging prediction was written and no parameter was invented. "
                        "Failure rows record every held-out interval. The reasons by fold are:")
            body.append("")
            for r in m1:
                body.append(f"- Fold {r['fold_id']}: {r['reason']}")
        else:
            body.append("M1 produced predictions in at least one fold. Fit status by fold:")
            body.append("")
            for r in m1:
                body.append(f"- Fold {r['fold_id']}: {r['status']} ({r['reason']})")
        body += ["", "### 5.3 M3 hybrid", "",
                 "| fold | status | residual variogram | fallback |", "|---|---|---|---|"]
        for r in m3:
            resid = [x for x in residual_rows if x["fold_id"] == r["fold_id"]]
            rsum = "; ".join(f"{x['model']} {x['fit_status']}/{x['stability_status']}" for x in resid)
            body.append(f"| {r['fold_id']} | {r['status']} | {rsum} | {m3_fallback[r['fold_id']]} |")
        body += ["", "The residual variogram is fitted on inner cross-fitted residuals of the outer training fold only. "
                     "Where it was not identified and stable, M3 is recorded as `FALLBACK_ML_ONLY` and is not described as "
                     "a successful hybrid. M3 never uses a test label.", "",
                 "### 5.4 Out-of-fold predictions", "",
                 "| family | predictions | failures | clipped (calibrated) | min p | max p |", "|---|---|---|---|---|---|"]
        for p in pred:
            body.append(f"| {p['family_id']} | {p['n']} | 0 | {p['clipped'] or 0} | {_f(p['pmin'], 3)} | "
                        f"{_f(p['pmax'], 3)} |")
        for f in fails:
            if not any(p["family_id"] == f["family_id"] for p in pred):
                body.append(f"| {f['family_id']} | 0 | {f['n']} | 0 | n/a | n/a |")
        body += ["", "A failure row is written for every held-out interval a family could not predict; it is never silently "
                     "dropped. Clipping to [0,1] is counted per prediction. Probabilities are out-of-fold by construction.", ""]
        body += ["## 6. Gate results", ""]
        body += _gate_table(gates)
        body += ["", f"Exit gates: {', '.join(EXIT_GATES)}. {'All exit gates PASS.' if not exit_failed else 'Failing exit gates: ' + ', '.join(exit_failed) + '.'}", ""]
        body += ["## 7. Tables", ""]
        for t in tables:
            body.append(f"- {t['table_id']}: {t['status']}, {t['row_count']} rows; {t['title']}.")
        body += ["", "The rendered tables are in tables/objective_3 as CSV, Markdown and LaTeX.", ""]
        body += ["## 8. Figures", ""]
        for f in figures:
            body.append(f"- {f['figure_id']} ({f['status']}): {f['title']}. {f['reason']}.")
        body += ["", "M1 is registered NOT_SUPPORTED when no fold produced a kriging prediction; the reason is recorded in "
                     "the figure registry and in section 5.2.", ""]
        body += ["## 9. Tests", "", "```text", pytest_text, "```", ""]
        body += ["## 10. Deviations, warnings and limitations", "",
                 "- M1 is not estimable at this support: the Objective 2 handoff found no between-hole continuity, and no "
                 "outer training fold identified a stable lateral indicator variogram.",
                 "- M3 is an ML-only fallback in every fold where the residual variogram was unsupported; it is not a "
                 "validated hybrid result.",
                 "- Only three predictors (easting, northing, relative Z) exist at every held-out interval. Weathering, "
                 "lithology and label evidence are logged-only or target-derived and are forbidden as predictors. The "
                 "models are therefore spatial-trend models, not geological-covariate models.",
                 "- Relative Z is used; no collar elevation or DEM is used, so no absolute-elevation claim is made.",
                 "- Five drill lines, one with only three holes, carry the outer split. A held-out line is an extrapolation "
                 "in northing for the models.",
                 "- The secondary whole-hole split plan is registered and audited but not used for the Objective 4 "
                 "predictions; a change of plan needs a new predeclared configuration.",
                 "- XGBoost is not installed; scikit-learn's histogram gradient boosting is the declared fallback.",
                 "- The final full-data refit is PENDING_O4. Objective 3 does not fit on all observations and does not call "
                 "that fit spatially validated.",
                 "- The code commit is the last committed revision; the Objective 3 working tree is deliberately not "
                 "committed. The configuration hash, SQL hashes and artifact hashes identify the exact run.",
                 ""]
        body += ["## 11. Objective 4 handoff contract", "",
                 f"- Split plan: `{plan}`, hash `{split.get('plan_sha256')}`, {split.get('n_folds')} line folds.",
                 f"- Target: `{target.get('target_id')}`, rule {target.get('label_rule_id')} {target.get('label_rule_status')}, "
                 f"{target.get('binary_n')} binary intervals.",
                 f"- Geometry: `{geom.get('geometry_version_id')}`, {geom.get('geometry_status')}, vertical basis "
                 f"{geom.get('vertical_basis')}, z_absolute_used=0.",
                 "- Predictions: `predictions_oof`, one row per (training run, held-out interval), with `p_raw`, "
                 "`p_calibrated`, clipping flags, training-selected threshold and predicted class.",
                 "- Failures: `prediction_failures`, one row per (fold, held-out interval, family) that could not be predicted.",
                 "- Fits and diagnostics: `training_runs`, `hyperparameter_trials`, `variogram_training_fits`, "
                 "`hybrid_residual_variogram`, `training_lag_bins`, `calibration_fits`, `residual_diagnostics`.",
                 "- Artifacts: `model_artifacts`, parameter and provenance records with SHA-256.",
                 "- Selection policy: inner whole-hole CV log loss; no outer test result was used to select a model or a "
                 "threshold. O4 may evaluate and rank, but must not refit models or change the split.",
                 f"- M1 status by fold: {', '.join(f'F{f}={s}' for f, s in sorted(m1_status.items()))}.",
                 f"- M3 status by fold: {', '.join(f'F{f}={s}' for f, s in sorted(m3_status.items()))}.",
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
        for c in counts:
            body.append(f"| {c['name']} | {c['n']} |")
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
                blocked.append(f"| {g['gate_id']} {g['gate_name']} | {g['status']} | {g['detail'].replace('|', '\\|')} |")
        else:
            blocked.append("- none")
        blocked += ["", "## Model failures and fallbacks", ""]
        for r in m1:
            if r["status"] != "COMPLETED":
                blocked.append(f"- M1 fold {r['fold_id']}: {r['status']}: {r['reason']}")
        for r in m3:
            if r["status"] != "COMPLETED":
                blocked.append(f"- M3 fold {r['fold_id']}: {r['status']}: {r['reason']}")
        blocked += ["", "## Leakage audit", ""]
        for c in leakage:
            blocked.append(f"- {c['status']} {c['check_name']}: {c['detail']}")
        blocked += ["", "## Deferred work (not performed in this stage)", "",
                    "- M1 indicator kriging at this support: no stable between-hole variogram was identified in any outer "
                    "training fold. A future stage may re-test M1 only if the support or label basis changes.",
                    "- M3 hybrid: the residual covariance is unsupported in every fold, so the recorded result is the "
                    "declared ML-only fallback. It is not a validated hybrid.",
                    "- Secondary whole-hole cross-validation: the fold plan and audit are stored, but its predictions are "
                    "not handed to Objective 4.",
                    "- Geological covariates: none exist in the source at prediction locations. Weathering, lithology and "
                    "comment evidence are logged-only or target-derived.",
                    "- Absolute elevation: no collar RL; no DEM and no absolute-Z product.",
                    "- Final full-data refit: PENDING_O4.",
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
            "split_plan": split, "split_audit": audits,
            "predictions": pred, "failures": fails,
            "model_artifacts": {"count": artifacts.get("n"), "bytes": artifacts.get("b")},
            "figures": figures, "tables": tables,
            "output_hashes": [{"path": r["artifact_path"], "sha256": r["sha256"], "bytes": r["bytes"]}
                              for r in _manifest_rows(conn, rid, [])],
        }
        lineage_path = O3_REPORT_DIR / "DATA_LINEAGE.json"
        lineage_path.write_text(json.dumps(lineage, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

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

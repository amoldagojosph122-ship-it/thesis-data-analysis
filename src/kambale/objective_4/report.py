"""Objective 4 reports, lineage and manifests."""

from __future__ import annotations

import csv
import importlib.metadata
import io
import json
import platform
from pathlib import Path

from kambale.objective_4 import O4_CODE_VERSION, O4_SCHEMA_VERSION
from kambale.objective_4.config import (O4_CONFIG_PATH, O4_DB_PATH, O4_FIGURE_DIR, O4_REPORT_DIR, O4_TABLE_DIR,
                                        PROJECT_ROOT, StopError, code_commit, load_config, sha256_bytes, utc_now)
from kambale.objective_4.db import connect_o4
from kambale.objective_4.figures import FIGURES
from kambale.objective_4.tables import TABLES

EXIT_GATES = ("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G10", "G11", "G12", "G13", "G15", "G16",
              "G17", "G18", "G19", "G20", "G21", "G24", "G25")
PYTEST_OUTPUT = O4_REPORT_DIR / "PYTEST_OUTPUT.txt"


def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _one(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else {}


def _f(value, digits=4):
    return "n/a" if value is None else f"{value:.{digits}f}"


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _versions():
    out = []
    for pkg in ("numpy", "scipy", "scikit-learn", "matplotlib", "PyYAML", "pytest"):
        try:
            out.append(f"{pkg} {importlib.metadata.version(pkg)}")
        except importlib.metadata.PackageNotFoundError:
            out.append(f"{pkg} not installed")
    return out


def _manifest_rows(conn, report_paths):
    rows = []
    for fig in _rows(conn, "SELECT figure_id, status FROM figure_registry ORDER BY figure_id"):
        if fig["status"] != "GENERATED":
            continue
        stem = FIGURES[fig["figure_id"]][1]
        for ext in ("svg", "pdf", "png"):
            path = O4_FIGURE_DIR / f"{stem}.{ext}"
            rows.append({"artifact_path": _rel(path), "kind": "FIGURE", "id": fig["figure_id"],
                         "sha256": sha256_bytes(path.read_bytes()), "bytes": path.stat().st_size,
                         "source": "figure_sql_registry"})
    for tab in _rows(conn, "SELECT table_id, status FROM table_registry ORDER BY table_id"):
        if tab["status"] != "GENERATED":
            continue
        stem = TABLES[tab["table_id"]][1]
        for ext in ("csv", "md", "tex"):
            path = O4_TABLE_DIR / f"{stem}.{ext}"
            rows.append({"artifact_path": _rel(path), "kind": "TABLE", "id": tab["table_id"],
                         "sha256": sha256_bytes(path.read_bytes()), "bytes": path.stat().st_size,
                         "source": "table_sql_registry"})
    for path in report_paths:
        rows.append({"artifact_path": _rel(path), "kind": "REPORT", "id": path.stem,
                     "sha256": sha256_bytes(path.read_bytes()), "bytes": path.stat().st_size, "source": "report"})
    return rows


def _write_manifest(path: Path, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["artifact_path", "kind", "id", "sha256", "bytes", "source"],
                            lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")


def _gate_table(gates):
    out = ["| gate | name | status | detail |", "|---|---|---|---|"]
    for g in gates:
        out.append(f"| {g['gate_id']} | {g['gate_name']} | {g['status']} | {g['detail'].replace('|', '\\|')} |")
    return out


def write_all(o4_path=None) -> dict:
    cfg, cfg_sha = load_config(O4_CONFIG_PATH)
    conn = connect_o4(o4_path or O4_DB_PATH)
    try:
        rc = _one(conn, "SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1")
        if not rc:
            raise StopError("no receipt: run the import first")
        vr = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'VERIFY' ORDER BY run_id DESC LIMIT 1")
        if not vr:
            raise StopError("no VERIFY run: run verify before report")
        gates = _rows(conn, "SELECT gate_id, gate_name, status, scope, detail FROM gate_results WHERE run_id = ? "
                            "ORDER BY gate_id", (vr["run_id"],))
        status = {g["gate_id"]: g["status"] for g in gates}
        exit_failed = [g for g in EXIT_GATES if status.get(g) != "PASS"]
        stopped = any(g["status"] == "STOP" for g in gates)
        plan = _one(conn, "SELECT * FROM evaluation_plan")
        cov = _rows(conn, "SELECT c.*, r.role, r.comparable, r.fallback_identical_to FROM prediction_coverage c "
                          "JOIN candidate_registry r ON r.model_id = c.model_id ORDER BY r.comparable DESC, c.coverage DESC, c.model_id")
        pooled = _rows(conn, "SELECT * FROM pooled_metrics WHERE weighting = 'INTERVAL' ORDER BY model_id, metric_id")
        pooled_hole = _rows(conn, "SELECT * FROM pooled_metrics WHERE weighting = 'EQUAL_HOLE' ORDER BY model_id, metric_id")
        cal = _rows(conn, "SELECT * FROM calibration_diagnostics ORDER BY model_id")
        dec = _rows(conn, "SELECT * FROM comparison_decisions ORDER BY CASE WHEN rank IS NULL THEN 99 ELSE rank END, model_id")
        handoff = _one(conn, "SELECT * FROM locked_handoff_receipts ORDER BY receipt_id DESC LIMIT 1")
        pairs = _rows(conn, "SELECT * FROM paired_differences WHERE scope = 'POOLED' AND weighting = 'INTERVAL' "
                            "ORDER BY pair_id")
        audits = _rows(conn, "SELECT * FROM evaluation_audit_log ORDER BY audit_id")
        figures = _rows(conn, "SELECT figure_id, title, status, reason FROM figure_registry ORDER BY figure_id")
        tables = _rows(conn, "SELECT table_id, title, status, row_count, reason FROM table_registry ORDER BY table_id")
        counts = [{"name": r[0], "n": conn.execute(f'SELECT COUNT(*) FROM "{r[0]}"').fetchone()[0]}
                  for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        n_common = conn.execute("SELECT COUNT(*) FROM evaluation_population WHERE in_common_cohort = 1").fetchone()[0]
        n_all = conn.execute("SELECT COUNT(*) FROM evaluation_population").fetchone()[0]
        n_holes = conn.execute("SELECT COUNT(DISTINCT hole_id) FROM evaluation_population").fetchone()[0]
        n_lines = conn.execute("SELECT COUNT(DISTINCT line_code) FROM evaluation_population").fetchone()[0]
        prev = conn.execute("SELECT AVG(true_label), SUM(true_label) FROM evaluation_population "
                            "WHERE in_common_cohort = 1").fetchone()
        bootstrap_n = conn.execute("SELECT COUNT(*) FROM bootstrap_replicates").fetchone()[0]
        pytest_text = PYTEST_OUTPUT.read_text(encoding="utf-8").strip() if PYTEST_OUTPUT.exists() else (
            "Not recorded. Run pytest with its output written to reports/objective_4/PYTEST_OUTPUT.txt and run report again.")
        created = utc_now()
        import_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'IMPORT' ORDER BY run_id DESC LIMIT 1")
        eval_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'EVALUATE' ORDER BY run_id DESC LIMIT 1")
        selected = next((d for d in dec if d["role"] == "SELECTED"), {})
        comparator = next((d for d in dec if d["role"] == "COMPARATOR"), {})
        m1 = next((c for c in cov if c["model_id"] == "M1_IK"), {})
        m3 = next((c for c in cov if c["model_id"] == "M3_HYBRID"), {})

        from kambale.objective_4 import tables as tables_mod
        table_summary = tables_mod.render_all(o4_path)
        tables = _rows(conn, "SELECT table_id, title, status, row_count, reason FROM table_registry ORDER BY table_id")

        readme = [
            "# Objective 4 outputs", "",
            "Independent spatial validation and probability-based performance evaluation of the frozen Objective 3 "
            "predictions. The stage reads earlier databases read-only and writes database/kambale_obj4_validation.sqlite.", "",
            f"Current status: {'STOPPED' if stopped else ('exit conditions met' if not exit_failed else 'exit conditions not met')}.",
            f"Locked model choice for Objective 5: {selected.get('model_id', 'n/a')} "
            f"({selected.get('improvement_status', 'n/a')}, {selected.get('selection_basis', 'n/a')}).", "",
            "Contents:", "",
            "- RUN_REPORT.md: the evaluation, its uncertainty and the locked decision.",
            "- BLOCKED_OR_DEFERRED.md: every warning, failure and deferred item.",
            "- DATA_LINEAGE.json: upstream receipts, configuration, code and output hashes.",
            "- FIGURE_MANIFEST.csv: SHA-256 for every figure, table and report file.",
            "- ../../figures/objective_4 and ../../tables/objective_4: the outputs.", "",
            "Reproduce with the commands in RUN_REPORT.md section 14.",
        ]
        readme_path = O4_REPORT_DIR / "README.md"
        readme_path.write_text("\n".join(readme) + "\n", encoding="utf-8", newline="\n")

        body = []
        body += ["# Objective 4 run report: independent spatial validation and probability-based performance", "",
                 f"Configuration {cfg['config_version']} (SHA-256 {cfg_sha[:12]}), code {O4_CODE_VERSION}, schema "
                 f"{O4_SCHEMA_VERSION}, commit {code_commit()}. Import run {import_run.get('run_id')}, evaluation run "
                 f"{eval_run.get('run_id')}, gate run {vr['run_id']}. Report written {created}.", "",
                 "## 1. Status", "",
                 ("A STOP gate failed. The run is stopped and the Objective 5 handoff is withheld." if stopped else
                  ("Every required exit gate is PASS." if not exit_failed else
                   "Exit gates not met: " + ", ".join(exit_failed) + ".")),
                 f"Locked model choice: **{selected.get('model_id', 'n/a')}**; improvement status "
                 f"**{selected.get('improvement_status', 'n/a')}**; selection basis "
                 f"**{selected.get('selection_basis', 'n/a')}**.", ""]
        body += ["## 2. Inputs and receipt", "",
                 f"- Objective 3 database: {rc['o3_path']} (read-only; receipt {rc['o3_receipt_id']}, config "
                 f"{rc['o3_config_version']}, split {rc['o3_split_plan_id']}).",
                 f"- Frozen prediction snapshot SHA-256: {rc['o3_prediction_snapshot_sha256'][:16]}..., "
                 f"{rc['o3_prediction_count']} prediction rows and {rc['o3_failure_count']} failure rows.",
                 f"- Objective 1 content SHA-256 {rc['o1_content_sha256'][:12]}; label rule "
                 f"{rc['o1_label_rule_id']} {rc['o1_label_rule_status']}; geometry {rc['geometry_status']}, "
                 f"{rc['vertical_basis']}; datum {rc['crs_datum_status']}.",
                 f"- Common held-out cohort: {n_common} intervals in {n_holes} holes and {n_lines} drill lines; "
                 f"positive prevalence {prev[0]:.3f} ({prev[1]} positives).", ""]
        body += ["## 3. Evaluation plan", "",
                 f"- Primary endpoint: **{plan.get('primary_endpoint')}**, {plan.get('primary_weighting')}-weighted; "
                 f"secondary weighting {plan.get('secondary_weighting')}.",
                 f"- Unit: {plan.get('unit_of_analysis')}.",
                 f"- Cohort: {plan.get('cohort_definition')}.",
                 f"- Bootstrap: {plan.get('bootstrap_design')}; {cfg['evaluation']['bootstrap']['n_replicates']} "
                 "replicates per design.",
                 f"- Calibration policy: {plan.get('calibration_policy')}.",
                 f"- Plan SHA-256: {plan.get('plan_sha256')}.", ""]
        body += ["## 4. Coverage", "",
                 "| model | role | predicted / expected | failed | coverage | status |",
                 "|---|---|---|---|---|---|"]
        for c in cov:
            body.append(f"| {c['model_id']} | {c['role']} | {c['n_predicted']} / {c['n_expected']} | "
                        f"{c['n_failed']} | {c['coverage']:.3f} | {c['status']} |")
        body += ["", "A model's failures are part of its applicability; they are never silently removed. M1 produced no "
                     "prediction in any fold; M3 is the recorded ML-only fallback and is identical to M2_RF in every "
                     "fold.", ""]
        body += ["## 5. Primary probability results (pooled, interval-weighted)", "",
                 "| model | Brier | Brier (equal-hole) | log loss | ROC-AUC | PR-AUC | ECE | slope | intercept |",
                 "|---|---|---|---|---|---|---|---|---|"]
        hole = {(r["model_id"], r["metric_id"]): r["value"] for r in pooled_hole}
        calmap = {r["model_id"]: r for r in cal}
        for m in [c["model_id"] for c in cov]:
            vals = {r["metric_id"]: r["value"] for r in pooled if r["model_id"] == m}
            d = calmap.get(m, {})
            body.append(f"| {m} | {_f(vals.get('BRIER'))} | {_f(hole.get((m, 'BRIER')))} | {_f(vals.get('LOG_LOSS'))} | "
                        f"{_f(vals.get('ROC_AUC'))} | {_f(vals.get('PR_AUC'))} | {_f(vals.get('ECE'))} | "
                        f"{_f(d.get('slope'), 3)} | {_f(d.get('intercept'), 3)} |")
        body += ["", "Lower Brier and log loss are better; higher AUC and PR-AUC are better. The calibration slope and "
                     "intercept are diagnostic fits on the held-out predictions and are not applied. An undefined metric "
                     "is shown as n/a with its status stored in O4-T02. M1 has no prediction.",
                 "", "The metric ranking is not unanimous: random forest has the lowest Brier and highest ROC-AUC, while "
                     "logistic regression has the highest PR-AUC. The differences are small, and the primary Brier "
                     "contrast between them is inconclusive at this support. " +
                     ("The decision therefore reports a point-estimate selection with an explicit caveat rather than a "
                      "claim of a credible improvement." if selected.get("improvement_status") == "INCONCLUSIVE" else
                      "The decision status is stored in O4-T05."), ""]
        body += ["## 6. Paired comparisons and uncertainty", "",
                 "| pair | delta Brier (a - b) | 95% hole CI | 95% line CI | folds a better | status |",
                 "|---|---|---|---|---|---|"]
        for p in pairs:
            folds_a = conn.execute("SELECT COUNT(*) FROM paired_differences WHERE pair_id = ? AND scope = 'FOLD' AND "
                                   "weighting = 'INTERVAL' AND delta_brier < 0", (p["pair_id"],)).fetchone()[0]
            body.append(f"| {p['pair_id']} | {_f(p['delta_brier'], 6)} | "
                        f"[{_f(p['ci_low'], 6)}, {_f(p['ci_high'], 6)}] | "
                        f"[{_f(p['ci_low_line'], 6)}, {_f(p['ci_high_line'], 6)}] | {folds_a} / 5 | {p['status']} |")
        body += ["", "Negative delta means model a has the lower Brier. The hole-cluster interval is the primary "
                     "uncertainty statement; the five-line interval is a sensitivity analysis and is too coarse to "
                     "establish significance on its own. An interval that includes zero is not evidence of an "
                     "improvement. No interval-level i.i.d. bootstrap is used.", ""]
        body += ["## 7. Decision", "",
                 "| rank | model | role | status | selection basis | delta Brier | 95% CI | folds better | calibration | discrimination | coverage |",
                 "|---|---|---|---|---|---|---|---|---|---|---|"]
        for d in dec:
            body.append(f"| {d['rank'] if d['rank'] is not None else ''} | {d['model_id']} | {d['role']} | "
                        f"{d['improvement_status']} | {d['selection_basis']} | {_f(d['delta_brier'], 6)} | "
                        f"[{_f(d['ci_low'], 6)}, {_f(d['ci_high'], 6)}] | "
                        f"{d['fold_consistency'] if d['fold_consistency'] is not None else ''} | "
                        f"{d['calibration_status']} | {d['discrimination_status']} | {_f(d['coverage'], 3)} |")
        body += ["", f"Selected model: **{selected.get('model_id', 'n/a')}**. Its improvement over the next-best model "
                     f"({comparator.get('model_id', 'n/a')}) is **{selected.get('improvement_status', 'n/a')}**: "
                     f"delta Brier {_f(selected.get('delta_brier'), 6)}, 95% hole-cluster interval "
                     f"[{_f(selected.get('ci_low'), 6)}, {_f(selected.get('ci_high'), 6)}], and the selected model is "
                     f"better in {selected.get('fold_consistency', 'n/a')} of five lines. " +
                     ("The selection is on the point estimate with an explicit caveat; no credible improvement over "
                      "the comparator is claimed." if selected.get("improvement_status") == "INCONCLUSIVE" else
                      "The improvement is supported by the predeclared rule." if selected.get("improvement_status") ==
                      "SUPPORTED_IMPROVEMENT" else "No improvement over the comparator is claimed.") +
                     " The M1 contrast is not estimable (0 coverage). The M3 hybrid is the fallback identical to M2_RF "
                     "and is not a separate candidate.", ""]
        body += ["## 8. Gates", ""]
        body += _gate_table(gates)
        body += ["", f"Exit gates: {', '.join(EXIT_GATES)}. "
                     f"{'All exit gates PASS.' if not exit_failed else 'Failing exit gates: ' + ', '.join(exit_failed) + '.'}",
                 ""]
        body += ["## 9. Audit", ""]
        for a in audits:
            body.append(f"- {a['status']} {a['check_name']}: {a['detail']}")
        body += ["", "## 10. Tables", ""]
        for t in tables:
            body.append(f"- {t['table_id']}: {t['status']}, {t['row_count']} rows; {t['title']}.")
        body += ["", "## 11. Figures", ""]
        for f in figures:
            body.append(f"- {f['figure_id']} ({f['status']}): {f['title']}. {f['reason']}")
        body += ["", "## 12. Tests", "", "```text", pytest_text, "```", ""]
        body += ["## 13. Limitations", "",
                 "- Internal spatially held-out validation on five drill lines; not an external prospective campaign.",
                 "- The effective independent spatial units are five lines and 71 holes, not 1,829 intervals. The primary "
                 "uncertainty resamples holes; the line-level interval is a coarse sensitivity.",
                 "- Only easting, northing and relative Z are predictors. The models are spatial-trend models, not "
                 "geological-covariate models.",
                 "- Relative Z only; no collar elevation or DEM. No absolute-elevation product.",
                 "- M1 is not estimable and M3 is the ML-only fallback; the hybrid claim is not supported.",
                 "- The random forest is selected on the point estimate but its improvement over logistic regression is "
                 "inconclusive at this support." if selected.get("improvement_status") == "INCONCLUSIVE" else
                 "- The selected model's improvement is labelled with its stored status; see O4-T05.",
                 "- No grade, tonnage or resource is estimated.",
                 "- The Objective 3 working tree is not committed; the hashes in the receipt identify the exact run.", ""]
        body += ["## 14. Commands and environment", "",
                 "```bash", "./.venv/Scripts/python.exe -I -m kambale.objective_4 all",
                 "./.venv/Scripts/python.exe -I -m pytest -o addopts= -q tests/objective_4 > reports/objective_4/PYTEST_OUTPUT.txt",
                 "./.venv/Scripts/python.exe -I -m kambale.objective_4 report",
                 "./.venv/Scripts/python.exe -I -m kambale.objective_4 verify", "```", "",
                 "`all` runs import, evaluate, verify, figures, tables, verify, report and verify.", "",
                 f"Python {platform.python_version()} on {platform.platform()}; " + "; ".join(_versions()) + ".", ""]
        body += ["## 15. Database row counts and receipts", "", "| table | rows |", "|---|---|"]
        for c in counts:
            body.append(f"| {c['name']} | {c['n']} |")
        body += ["", "Counts are taken when this report is written. The post-report VERIFY run adds one `stage_runs` row "
                     "and one gate set; it is the authoritative final check.", "",
                 f"O3 snapshot SHA-256: {rc['o3_prediction_snapshot_sha256']}. O3 split hash: "
                 f"{rc['o3_split_plan_sha256']}. O1 content SHA-256: {rc['o1_content_sha256']}.", ""]
        run_path = O4_REPORT_DIR / "RUN_REPORT.md"
        run_path.write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")

        blocked = ["# Objective 4: blocked, skipped, warned and deferred items", "",
                   f"Gate results are from VERIFY run {vr['run_id']}.", "",
                   "## Gates with a warning or a stop", ""]
        flagged = [g for g in gates if g["status"] != "PASS"]
        if flagged:
            blocked += ["| gate | status | detail |", "|---|---|---|"]
            for g in flagged:
                blocked.append(f"| {g['gate_id']} {g['gate_name']} | {g['status']} | {g['detail'].replace('|', '\\|')} |")
        else:
            blocked.append("- none")
        blocked += ["", "## Model applicability", "",
                    f"- M1_IK: {m1.get('n_predicted', 0)} predictions and {m1.get('n_failed', 0)} explicit failures; "
                    "coverage 0; not comparable.",
                    f"- M3_HYBRID: {m3.get('n_predicted', 0)} predictions; recorded as the ML-only fallback identical "
                    "to M2_RF; not a separate hybrid candidate.",
                    "- The four feasible models cover every held-out interval.",
                    "", "## Deferred work", "",
                    "- Objective 5 uncertainty volumes and simulations: not started.",
                    "- External prospective validation: not available; the internal held-out result is not a guarantee "
                    "of performance in distant geology.",
                    "- The final full-data refit of the selected model: not run in O4; it is the O3 final-fit task "
                    "triggered by this receipt.",
                    "- Commit and push: not done; this waits for the user's instruction.", ""]
        blocked_path = O4_REPORT_DIR / "BLOCKED_OR_DEFERRED.md"
        blocked_path.write_text("\n".join(blocked) + "\n", encoding="utf-8", newline="\n")

        lineage = {
            "objective": 4,
            "code_version": O4_CODE_VERSION,
            "schema_version": O4_SCHEMA_VERSION,
            "config_version": cfg["config_version"],
            "config_sha256": cfg_sha,
            "code_commit": code_commit(),
            "working_tree_committed": False,
            "created_utc": created,
            "upstream": {
                "objective_3": {"path": rc["o3_path"], "receipt_id": rc["o3_receipt_id"],
                                "config_version": rc["o3_config_version"],
                                "split_plan_id": rc["o3_split_plan_id"],
                                "split_plan_sha256": rc["o3_split_plan_sha256"],
                                "prediction_snapshot_sha256": rc["o3_prediction_snapshot_sha256"],
                                "predictions": rc["o3_prediction_count"], "failures": rc["o3_failure_count"]},
                "objective_1": {"content_sha256": rc["o1_content_sha256"],
                                "label_rule_id": rc["o1_label_rule_id"],
                                "label_rule_definition_sha256": rc["o1_label_rule_definition_sha256"]},
            },
            "runs": {"import": import_run.get("run_id"), "evaluate": eval_run.get("run_id"), "verify": vr["run_id"]},
            "plan": plan, "coverage": cov, "pooled_metrics": pooled, "calibration": cal,
            "decisions": dec, "handoff": handoff, "paired": pairs,
            "bootstrap_replicates": bootstrap_n,
            "figures": figures, "tables": tables,
            "output_hashes": [{"path": r["artifact_path"], "sha256": r["sha256"], "bytes": r["bytes"]}
                              for r in _manifest_rows(conn, [])],
        }
        lineage_path = O4_REPORT_DIR / "DATA_LINEAGE.json"
        lineage_path.write_text(json.dumps(lineage, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

        report_paths = [readme_path, run_path, blocked_path, lineage_path]
        rows = _manifest_rows(conn, report_paths)
        manifest_path = O4_REPORT_DIR / "FIGURE_MANIFEST.csv"
        _write_manifest(manifest_path, rows)
        conn.execute("DELETE FROM export_manifests WHERE artifact_kind IN ('REPORT','MANIFEST')")
        for path in report_paths + [manifest_path]:
            conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_id, sha256, "
                         "bytes, created_utc) VALUES (?, ?, ?, ?, ?, ?)",
                         (_rel(path), "REPORT" if path.suffix != ".csv" else "MANIFEST", path.stem,
                          sha256_bytes(path.read_bytes()), path.stat().st_size, created))
        return {"status": "STOPPED" if stopped else "COMPLETE", "exit_failed": exit_failed,
                "selected_model": selected.get("model_id"), "improvement_status": selected.get("improvement_status"),
                "figures": {f["figure_id"]: f["status"] for f in figures},
                "tables": table_summary, "report": _rel(run_path), "manifest": _rel(manifest_path)}
    finally:
        conn.close()

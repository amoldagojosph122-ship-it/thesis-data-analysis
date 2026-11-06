"""Objective 4 reports, lineage and manifests, one set per evaluation tier.

Every statement about a model, pair or decision is generated from the database and the tier's config. Identity flags
decide whether a hybrid contrast is described as an advantage (it never is when M3 equals its trend).
"""

from __future__ import annotations

import csv
import importlib.metadata
import io
import json
import platform
from pathlib import Path

from kambale.objective_4 import O4_CODE_VERSION, O4_SCHEMA_VERSION
from kambale.objective_4.config import (O4_CONFIG_PATH, O4_DB_PATH, O4_FIGURE_DIR, O4_REPORT_DIR, O4_TABLE_DIR,
                                        PROJECT_ROOT, StopError, code_commit, load_config, sha256_bytes, tier_stem,
                                        utc_now)
from kambale.objective_4.db import connect_o4
from kambale.objective_4.decision import TIER_TEXT
from kambale.objective_4.figures import FIGURES, MODEL_LABEL
from kambale.objective_4.tables import TABLES

EXIT_GATES = ("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G10", "G11", "G12", "G13", "G15", "G16",
              "G17", "G18", "G19", "G20", "G21", "G24", "G25", "G28", "G29")
NESTED_CHAIN = ("PREV_vs_M2SEL", "M2SEL_vs_M2WFSEL", "M2WFSEL_vs_M3", "PREV_vs_M1")
WEATHERING = ("LOG_vs_LOGWF", "RF_vs_RFWF", "HGB_vs_HGBWF")
FAMILY = ("LOG_vs_RF", "RF_vs_HGB")
METRIC_DIRECTION = {"BRIER": "lower", "LOG_LOSS": "lower", "ECE": "lower", "ROC_AUC": "higher", "PR_AUC": "higher"}
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


def _short(model):
    return MODEL_LABEL.get(model, model)


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
            path = O4_FIGURE_DIR / f"{tier_stem(stem)}.{ext}"
            rows.append({"artifact_path": _rel(path), "kind": "FIGURE", "id": fig["figure_id"],
                         "sha256": sha256_bytes(path.read_bytes()), "bytes": path.stat().st_size,
                         "source": "figure_sql_registry"})
    for tab in _rows(conn, "SELECT table_id, status FROM table_registry ORDER BY table_id"):
        if tab["status"] != "GENERATED":
            continue
        stem = TABLES[tab["table_id"]][1]
        for ext in ("csv", "md", "tex"):
            path = O4_TABLE_DIR / f"{tier_stem(stem)}.{ext}"
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


def _pair_line(conn, p, label_col=True):
    folds_b = conn.execute("SELECT COUNT(*) FROM paired_differences WHERE pair_id = ? AND scope = 'FOLD' AND "
                           "weighting = 'INTERVAL' AND delta_brier < 0", (p["pair_id"],)).fetchone()[0]
    if p["status"] == "IDENTICAL":
        ci, line_ci, half = "identical; no interval", "n/a", "n/a"
    else:
        ci = f"[{_f(p['ci_low'], 6)}, {_f(p['ci_high'], 6)}]"
        line_ci = f"[{_f(p['ci_low_line'], 6)}, {_f(p['ci_high_line'], 6)}]"
        half = _f(p["detectable_half_width"], 6) if p["power_label"] == "UNRESOLVED" else "-"
    return (f"| {p['pair_id']} | {_short(p['model_a'])} vs {_short(p['model_b'])} | {_f(p['delta_brier'], 6)} | {ci} | "
            f"{line_ci} | {p['power_label'] or 'n/a'} | {half} | {folds_b} / 5 | {p['status']} |")


PAIR_HEADER = ["| pair | a vs b | delta Brier (b - a) | 95% hole CI | 95% line CI | power | half-width | folds b lower | status |",
               "|---|---|---|---|---|---|---|---|---|"]


def _rule_text(cfg):
    dec = cfg["evaluation"]["decision"]
    return [f"- Selection: {dec['select']}.", f"- Comparator: {dec['comparator']}.",
            f"- Improvement rule (predeclared, verbatim from the config): {' '.join(dec['improvement_rule'].split())}",
            f"- Calibration and discrimination are diagnostic conditions inside the rule; the calibration fit is never applied."]


def _best_by_metric(pooled, comparable):
    best = {}
    for metric, direction in METRIC_DIRECTION.items():
        cands = [(r["value"], r["model_id"]) for r in pooled if r["metric_id"] == metric and r["model_id"] in comparable
                 and r["value"] is not None]
        if not cands:
            continue
        best[metric] = (min(cands) if direction == "lower" else max(cands))[1]
    return best


def write_all(o4_path=None) -> dict:
    O4_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cfg, cfg_sha = load_config(O4_CONFIG_PATH)
    tier = cfg["tier"]
    tier_number = 1 if tier == "TIER_1_EXTRAPOLATION" else 2
    text = TIER_TEXT[tier]
    ev = cfg["evaluation"]
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
        reg = {r["model_id"]: r for r in _rows(conn, "SELECT * FROM candidate_registry")}
        cov = _rows(conn, "SELECT c.*, r.role, r.comparable, r.identity_status, r.identical_to FROM prediction_coverage c "
                          "JOIN candidate_registry r ON r.model_id = c.model_id ORDER BY c.model_id")
        cov_by = {c["model_id"]: c for c in cov}
        pooled = _rows(conn, "SELECT * FROM pooled_metrics WHERE weighting = 'INTERVAL' ORDER BY model_id, metric_id")
        pooled_hole = _rows(conn, "SELECT * FROM pooled_metrics WHERE weighting = 'EQUAL_HOLE' ORDER BY model_id, metric_id")
        cal = _rows(conn, "SELECT * FROM calibration_diagnostics ORDER BY model_id")
        dec = _rows(conn, "SELECT * FROM comparison_decisions ORDER BY CASE WHEN rank IS NULL THEN 99 ELSE rank END, model_id")
        handoff = _one(conn, "SELECT * FROM locked_handoff_receipts ORDER BY receipt_id DESC LIMIT 1")
        pairs = _rows(conn, "SELECT * FROM paired_differences WHERE scope = 'POOLED' AND weighting = 'INTERVAL'")
        pairs_by = {p["pair_id"]: p for p in pairs}
        audits = _rows(conn, "SELECT * FROM evaluation_audit_log ORDER BY audit_id")
        figures = _rows(conn, "SELECT figure_id, title, status, reason FROM figure_registry ORDER BY figure_id")
        counts = [{"name": r[0], "n": conn.execute(f'SELECT COUNT(*) FROM "{r[0]}"').fetchone()[0]}
                  for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        n_common = conn.execute("SELECT COUNT(*) FROM evaluation_population WHERE in_common_cohort = 1").fetchone()[0]
        n_holes = conn.execute("SELECT COUNT(DISTINCT hole_id) FROM evaluation_population WHERE in_common_cohort = 1").fetchone()[0]
        n_lines = conn.execute("SELECT COUNT(DISTINCT line_code) FROM evaluation_population WHERE in_common_cohort = 1").fetchone()[0]
        prev = conn.execute("SELECT AVG(true_label), SUM(true_label) FROM evaluation_population "
                            "WHERE in_common_cohort = 1").fetchone()
        bootstrap_n = conn.execute("SELECT COUNT(*) FROM bootstrap_replicates").fetchone()[0]
        pytest_text = PYTEST_OUTPUT.read_text(encoding="utf-8").strip() if PYTEST_OUTPUT.exists() else (
            f"Not recorded. Run pytest with its output written to {_rel(PYTEST_OUTPUT)} and run report again.")
        created = utc_now()
        import_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'IMPORT' ORDER BY run_id DESC LIMIT 1")
        eval_run = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'EVALUATE' ORDER BY run_id DESC LIMIT 1")
        selected = next((d for d in dec if d["role"] == "SELECTED"), {})
        comparator = next((d for d in dec if d["role"] == "COMPARATOR"), {})
        comparable = {m for m, r in reg.items() if r["comparable"] == 1}
        best = _best_by_metric(pooled, comparable)
        hole_by = {(r["model_id"], r["metric_id"]): r["value"] for r in pooled_hole}
        calmap = {r["model_id"]: r for r in cal}
        pooled_by = {(r["model_id"], r["metric_id"]): r["value"] for r in pooled}

        from kambale.objective_4 import tables as tables_mod
        table_summary = tables_mod.render_all(o4_path)
        tables = _rows(conn, "SELECT table_id, title, status, row_count, reason FROM table_registry ORDER BY table_id")

        readme = [
            f"# Objective 4 outputs: {tier}", "",
            "Independent spatial validation and probability-based performance evaluation of the frozen Objective 3 "
            f"predictions for the claim: {cfg['claim'].strip()}", "",
            f"Database: {_rel(O4_DB_PATH)}. Split plan: {cfg['paths']['o3_split_plan_id']}.", "",
            f"Current status: {'STOPPED' if stopped else ('exit conditions met' if not exit_failed else 'exit conditions not met')}.",
            f"Locked model choice: {selected.get('model_id', 'n/a')} ({selected.get('improvement_status', 'n/a')}, "
            f"{selected.get('selection_basis', 'n/a')}).", "",
            "Contents:", "",
            "- RUN_REPORT.md: the evaluation, its uncertainty, power and the locked decision.",
            "- BLOCKED_OR_DEFERRED.md: every warning, failure and deferred item.",
            "- DATA_LINEAGE.json: upstream receipts, configuration, code and output hashes.",
            "- FIGURE_MANIFEST.csv: SHA-256 for every figure, table and report file.",
            f"- {_rel(O4_FIGURE_DIR)} and {_rel(O4_TABLE_DIR)}: the outputs.", "",
            "Reproduce with the commands in RUN_REPORT.md section 14.",
        ]
        readme_path = O4_REPORT_DIR / "README.md"
        readme_path.write_text("\n".join(readme) + "\n", encoding="utf-8", newline="\n")

        body = []
        body += [f"# Objective 4 run report: {tier}", "",
                 f"Configuration {cfg['config_version']} (SHA-256 {cfg_sha[:12]}), code {O4_CODE_VERSION}, schema "
                 f"{O4_SCHEMA_VERSION}, commit {code_commit()}. Import run {import_run.get('run_id')}, evaluation run "
                 f"{eval_run.get('run_id')}, gate run {vr['run_id']}. Report written {created}.", "",
                 f"**Claim.** {cfg['claim'].strip()}", "",
                 "## 1. Status", "",
                 ("A STOP gate failed. The run is stopped and the Objective 5 handoff is withheld." if stopped else
                  ("Every required exit gate is PASS." if not exit_failed else
                   "Exit gates not met: " + ", ".join(exit_failed) + ".")),
                 f"Locked model choice: **{selected.get('model_id', 'n/a')}**; improvement status "
                 f"**{selected.get('improvement_status', 'n/a')}**; selection basis "
                 f"**{selected.get('selection_basis', 'n/a')}**; comparator **{comparator.get('model_id', 'n/a')}**.", ""]
        body += ["## 2. Inputs and receipt", "",
                 f"- Tier: {tier}; fold unit {ev['fold_unit']}; Objective 3 split plan {rc['o3_split_plan_id']} "
                 f"(SHA-256 {rc['o3_split_plan_sha256'][:16]}).",
                 f"- Objective 3 database: {rc['o3_path']} (read-only; receipt {rc['o3_receipt_id']}, config "
                 f"{rc['o3_config_version']}).",
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
                 f"- Bootstrap: {plan.get('bootstrap_design')}; {ev['bootstrap']['n_replicates']} replicates per design, "
                 f"seed {ev['bootstrap']['seed']}.",
                 f"- Calibration policy: {plan.get('calibration_policy')}.",
                 f"- Plan SHA-256: {plan.get('plan_sha256')}.", ""]
        body += ["## 4. Models: coverage, identity and decision role", "",
                 "| model | role | identity | identical to | coverage | status | comparable | decision |",
                 "|---|---|---|---|---|---|---|---|"]
        for c in cov:
            d = next((x for x in dec if x["model_id"] == c["model_id"]), {})
            body.append(f"| {c['model_id']} | {c['role']} | {c['identity_status']} | {c['identical_to'] or '-'} | "
                        f"{c['n_predicted']} / {c['n_expected']} ({c['coverage']:.3f}) | {c['status']} | "
                        f"{c['comparable']} | {d.get('role', 'n/a')} |")
        body += ["", "Identity means the calibrated probabilities equal the named earlier feasible model's on every common "
                     "interval (tolerance 1e-12). Identical models are reported once, are not ranked, and are NOT_COMPARABLE "
                     "with that reason. Coverage and identity are separate columns."]
        ids_list = [c for c in cov if c["identity_status"] == "IDENTICAL_TO"]
        body += ["", "Identities found: " + ("; ".join(f"{c['model_id']} = {c['identical_to']}" for c in ids_list)
                                             if ids_list else "none") + ".", ""]
        body += ["## 5. Primary probability results (pooled, interval-weighted)", "",
                 "| model | Brier | Brier (equal-hole) | log loss | ROC-AUC | PR-AUC | ECE | slope | intercept |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for c in cov:
            m = c["model_id"]
            d = calmap.get(m, {})
            body.append(f"| {m} | {_f(pooled_by.get((m, 'BRIER')))} | {_f(hole_by.get((m, 'BRIER')))} | "
                        f"{_f(pooled_by.get((m, 'LOG_LOSS')))} | {_f(pooled_by.get((m, 'ROC_AUC')))} | "
                        f"{_f(pooled_by.get((m, 'PR_AUC')))} | {_f(pooled_by.get((m, 'ECE')))} | "
                        f"{_f(d.get('slope'), 3)} | {_f(d.get('intercept'), 3)} |")
        best_txt = ", ".join(f"{metric} {_short(model)}" for metric, model in best.items())
        same = len(set(best.values())) == 1
        body += ["", "Lower Brier and log loss are better; higher AUC and PR-AUC are better. Calibration slope and intercept "
                     "are diagnostic fits on the held-out predictions and are not applied. Undefined metrics are n/a and "
                     "carry a status in O4-T02. Best comparable model by metric: " + best_txt + ". " +
                     ("The same model is best on every metric." if same else
                      "The metric ranking is not unanimous; differences are judged by the interval and the decision "
                      "rule below, not by the point ranking alone.") , ""]
        body += ["## 6. Paired comparisons (difference = Brier(b) minus Brier(a))", "",
                 "Negative means model b has the lower Brier. The power label follows the hole-cluster interval: RESOLVED "
                 "when it excludes zero; UNRESOLVED when it includes zero, with the half-width the smallest difference this "
                 "design could have detected; IDENTICAL when the two models are the same predictions.", ""]
        body += ["### 6.1 Nested chain: trend, then weathering, then kriging, and trend then kriging", ""] + PAIR_HEADER
        for pid in NESTED_CHAIN:
            if pid in pairs_by:
                body.append(_pair_line(conn, pairs_by[pid]))
        m3 = reg.get("M3_HYBRID", {})
        if m3.get("identity_status") == "IDENTICAL_TO":
            body += ["", f"M3_HYBRID is identical to {m3['identical_to']} on every common interval. Its residual kriging "
                         "adds nothing in this evaluation: the contrast M2_WF_SEL to M3 is exactly zero by construction, "
                         "and no hybrid advantage is claimed."]
        if reg.get("M1_IK", {}).get("identity_status") == "DISTINCT" and "PREV_vs_M1" in pairs_by:
            p = pairs_by["PREV_vs_M1"]
            body += ["", f"M1 (indicator kriging) is distinct from the prevalence baseline. Its contrast with the "
                         f"prevalence baseline is {p['power_label']} (delta {_f(p['delta_brier'], 6)})."]
        body += ["", "### 6.2 Weathering-front effect inside each family", ""] + PAIR_HEADER
        for pid in WEATHERING:
            if pid in pairs_by:
                body.append(_pair_line(conn, pairs_by[pid]))
        body += ["", "### 6.3 Family comparisons", ""] + PAIR_HEADER
        for pid in FAMILY:
            if pid in pairs_by:
                body.append(_pair_line(conn, pairs_by[pid]))
        body += ["", "Every configured pair is listed in O4-T04 with its weighting sensitivity.", ""]
        resolved = [p for p in pairs if p["power_label"] == "RESOLVED"]
        unresolved = [p for p in pairs if p["power_label"] == "UNRESOLVED"]
        identical_pairs = [p for p in pairs if p["power_label"] == "IDENTICAL"]
        body += ["### 6.4 Which comparisons are powered", ""]
        body += ["- RESOLVED (interval excludes zero): " +
                 (", ".join(f"{p['pair_id']} ({_f(p['delta_brier'], 4)})" for p in resolved) or "none") + "."]
        body += ["- UNRESOLVED (interval includes zero; smallest detectable difference = half-width): " +
                 (", ".join(f"{p['pair_id']} (+/- {_f(p['detectable_half_width'], 4)})" for p in unresolved) or "none") + "."]
        body += ["- IDENTICAL (no interval; the two models are the same predictions): " +
                 (", ".join(f"{p['pair_id']} ({p['model_a']} = {p['model_b']})" for p in identical_pairs) or "none") + ".", ""]
        body += ["## 7. Decision", "",
                 "| rank | model | role | identity | status | basis | delta Brier | 95% CI | folds better | calibration | discrimination | coverage |",
                 "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for d in dec:
            r = reg.get(d["model_id"], {})
            body.append(f"| {d['rank'] if d['rank'] is not None else ''} | {d['model_id']} | {d['role']} | "
                        f"{r.get('identity_status', '')} | {d['improvement_status']} | {d['selection_basis']} | "
                        f"{_f(d['delta_brier'], 6)} | [{_f(d['ci_low'], 6)}, {_f(d['ci_high'], 6)}] | "
                        f"{d['fold_consistency'] if d['fold_consistency'] is not None else ''} | "
                        f"{d['calibration_status']} | {d['discrimination_status']} | {_f(d['coverage'], 3)} |")
        body += ["", "Rule (predeclared):"] + _rule_text(cfg) + [""]
        sel_status = selected.get("improvement_status")
        if sel_status == "SUPPORTED_IMPROVEMENT":
            verdict = ("The predeclared improvement rule is met, so the selected model is claimed to improve on the comparator "
                       "for this claim.")
        elif sel_status == "INCONCLUSIVE":
            verdict = ("The point estimate selects this model, but the predeclared improvement rule is not met. The choice is a "
                       "point-estimate selection with a caveat, and no credible improvement over the comparator is claimed.")
        elif sel_status == "NO_IMPROVEMENT":
            verdict = "The predeclared rule finds no improvement over the comparator; no improvement is claimed."
        else:
            verdict = "The decision status is stored in O4-T05."
        body += [f"Selected {selected.get('model_id', 'n/a')} against comparator {comparator.get('model_id', 'n/a')}: delta "
                 f"Brier (selected minus comparator) {_f(selected.get('delta_brier'), 6)}, 95% hole-cluster interval "
                 f"[{_f(selected.get('ci_low'), 6)}, {_f(selected.get('ci_high'), 6)}], selected better in "
                 f"{selected.get('fold_consistency', 'n/a')} of 5 folds. Status **{sel_status}**. {verdict}", ""]
        if m3.get("identity_status") == "IDENTICAL_TO":
            body += ["No selection result here is a hybrid advantage: M3_HYBRID is identical to its trend "
                     f"({m3['identical_to']}), so any gain attributed to the hybrid family is zero by construction.", ""]
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
                 f"- {text['caveat']}",
                 f"- The effective independent spatial units are {n_lines} drill lines and {n_holes} holes, not "
                 f"{n_common} intervals. The primary uncertainty resamples holes; the line-level interval is a coarse "
                 "sensitivity.",
                 "- Only easting, northing and relative Z are predictors. The models are spatial-trend and kriging models, "
                 "not geological-covariate models.",
                 "- Relative Z only; no collar elevation or DEM. No absolute-elevation product.",
                 "- Where a pair is UNRESOLVED, the data cannot distinguish the models at the stated half-width; no ranking "
                 "is claimed for that pair.",
                 "- No grade, tonnage or resource is estimated.",
                 "- The Objective 3 working tree is not committed; the hashes in the receipt identify the exact run.", ""]
        body += ["## 14. Commands and environment", "",
                 "```bash",
                 f"./.venv/Scripts/python.exe -I -m kambale.objective_4 all --tier {tier_number}",
                 "./.venv/Scripts/python.exe -I -m pytest tests/objective_4 -q",
                 f"./.venv/Scripts/python.exe -I -m kambale.objective_4 report --tier {tier_number}",
                 f"./.venv/Scripts/python.exe -I -m kambale.objective_4 verify --tier {tier_number}", "```", "",
                 "`all` runs import, evaluate, verify, figures, tables, verify, report and verify. The tier argument selects "
                 "the config, database and output directories.", "",
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

        blocked = [f"# Objective 4 blocked, skipped, warned and deferred items: {tier}", "",
                   f"Gate results are from VERIFY run {vr['run_id']}.", "",
                   "## Gates with a warning or a stop", ""]
        flagged = [g for g in gates if g["status"] != "PASS"]
        if flagged:
            blocked += ["| gate | status | detail |", "|---|---|---|"]
            for g in flagged:
                blocked.append(f"| {g['gate_id']} {g['gate_name']} | {g['status']} | {g['detail'].replace('|', '\\|')} |")
        else:
            blocked.append("- none")
        blocked += ["", "## Model applicability", ""]
        for c in cov:
            blocked.append(f"- {c['model_id']}: {c['n_predicted']} of {c['n_expected']} predicted; coverage {c['coverage']:.3f}; "
                           f"identity {c['identity_status']}"
                           + (f" to {c['identical_to']}" if c["identical_to"] else "") + "; "
                           + ("ranked" if c["comparable"] else "not ranked") + ".")
        blocked += ["", "## Deferred work", "",
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
            "tier": tier,
            "claim": cfg["claim"].strip(),
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
            "plan": plan, "coverage": cov, "identities": [{"model_id": c["model_id"], "identity_status": c["identity_status"],
                                                           "identical_to": c["identical_to"]} for c in cov],
            "pooled_metrics": pooled, "calibration": cal,
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
        return {"status": "STOPPED" if stopped else "COMPLETE", "tier": tier, "exit_failed": exit_failed,
                "selected_model": selected.get("model_id"), "improvement_status": selected.get("improvement_status"),
                "figures": {f["figure_id"]: f["status"] for f in figures},
                "tables": table_summary, "report": _rel(run_path), "manifest": _rel(manifest_path)}
    finally:
        conn.close()

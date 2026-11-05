"""Gate runner for Objective 2 (specification 03). Each executed gate writes one gate_results row for a VERIFY run.

Gates that are checked by tests rather than by this runner are listed in RUN_REPORT.md; nothing is marked PASS
without an executed check. G07 runs a brute-force pair count on a seeded subset, so the blockwise counts are compared
with a double loop on every verify run.
"""

from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from kambale.objective_2 import pairs, variogram
from kambale.objective_2.config import (O2_CONFIG_PATH, O2_DB_PATH, PROJECT_ROOT, UPSTREAM_DB_PATH, code_commit,
                                        load_config, sha256_text, utc_now)
from kambale.objective_2.db import connect_o2, connect_upstream_readonly
from kambale.objective_2.importer import IMPORT_QUERY
from kambale.objective_2.pairs import bin_edges

PAIR_CHECK_SEED = 20261105
PAIR_CHECK_SIZE = 160


def _result(gate_id, name, status, scope, detail):
    return {"gate_id": gate_id, "gate_name": name, "status": status, "scope": scope, "detail": detail}


def _pair_check(conn, rid: int) -> tuple[str, str]:
    """G07. Blockwise lateral pair counts must equal a brute-force double loop on a seeded subset; same-hole pairs and
    zero-distance pairs must never reach a bin."""
    obs = variogram.load_observations(conn, rid)
    rng = np.random.default_rng(PAIR_CHECK_SEED)
    size = min(PAIR_CHECK_SIZE, obs.X.shape[0])
    idx = np.sort(rng.choice(obs.X.shape[0], size=size, replace=False))
    X, I = obs.X[idx], obs.I[idx]
    _, hole = np.unique(obs.hole[idx], return_inverse=True)
    n_per_hole = np.bincount(hole).astype(np.float64)
    edges = bin_edges(20.0, 500.0)
    acc = pairs.accumulate(X, I, hole, n_per_hole, edges, within="EXCLUDED", horizontal=True, max_abs_dz=3.0)
    brute = np.zeros(len(edges) - 1, dtype=np.int64)
    zero = 0
    for i in range(size):
        for j in range(i + 1, size):
            if hole[i] == hole[j]:
                continue
            h = math.hypot(X[j, 0] - X[i, 0], X[j, 1] - X[i, 1])
            if h <= 1e-6:
                zero += 1
                continue
            if abs(X[j, 2] - X[i, 2]) > 3.0 or not (edges[0] <= h < edges[-1]):
                continue
            brute[int(np.searchsorted(edges, h, side="right")) - 1] += 1
    agree = np.array_equal(brute, acc["n_pairs"])
    return ("PASS" if agree else "STOP",
            f"subset of {size} intervals: blockwise and brute-force counts {'agree' if agree else 'DISAGREE'} "
            f"over {int(brute.sum())} pairs; {zero} zero-distance pairs excluded")


def _absolute_columns(conn) -> list[str]:
    found = []
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
        for col in conn.execute(f"PRAGMA table_info({table})").fetchall():
            if "absolute" in col["name"].lower():
                found.append(f"{table}.{col['name']}")
    return found


def run(o2_path=O2_DB_PATH, upstream=UPSTREAM_DB_PATH, config_path=O2_CONFIG_PATH) -> dict:
    config, config_sha = load_config(config_path)
    conn = connect_o2(o2_path)
    receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
    if receipt is None:
        raise RuntimeError("no receipt: run the import first")
    rid = receipt["receipt_id"]
    run_id = conn.execute("INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, started_utc, "
                          "status, code_commit, note) VALUES ('VERIFY', ?, ?, ?, ?, 'RUNNING', ?, 'gate runner')",
                          (config["config_version"], config_sha, rid, utc_now(), code_commit())).lastrowid
    g = []
    obs_count = conn.execute("SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = ?", (rid,)).fetchone()[0]

    # G01 receipt match against the live upstream snapshot; G02 and G03 use the same upstream connection.
    up = connect_upstream_readonly(upstream)
    try:
        version = up.execute("SELECT dataset_version_key FROM v_active_version").fetchone()[0]
        rows = [dict(r) for r in up.execute(IMPORT_QUERY)]
        absolute = up.execute("SELECT COUNT(*) FROM v_interval_geometry WHERE z_absolute_m IS NOT NULL").fetchone()[0]
        orient = [tuple(r) for r in up.execute("SELECT DISTINCT dip_deg, azimuth_deg FROM v_survey")]
        rule_def = up.execute("SELECT definition_sha256 FROM graphite_label_rules WHERE rule_id = ?",
                              (receipt["label_rule_id"],)).fetchone()[0]
    finally:
        up.close()
    canon = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    recomputed = sha256_text(canon)
    same = recomputed == receipt["content_sha256"] and version == receipt["upstream_dataset_version_key"]
    g.append(_result("G01", "Receipt match", "PASS" if same else "STOP", "input",
                     f"recomputed content {recomputed[:12]} vs receipt {receipt['content_sha256'][:12]}"))
    g.append(_result("G02", "Approved label rule", "PASS" if receipt["label_rule_status"] == "APPROVED" and rule_def ==
                     receipt["label_rule_definition_sha256"] else "STOP", "input",
                     f"{receipt['label_rule_id']} {receipt['label_rule_status']}"))
    g.append(_result("G03", "Relative geometry only", "PASS" if absolute == 0 and receipt["geometry_status"] ==
                     "PROVISIONAL_RELATIVE" else "STOP", "input", f"z_absolute_m non-null rows = {absolute}"))
    g.append(_result("G04", "Coordinate pair and datum", "PASS" if receipt["coordinate_pair_status"] == "APPROVED" and
                     receipt["crs_datum_status"] == "VERIFIED" else "STOP", "input",
                     f"pair {receipt['coordinate_pair_status']}; datum {receipt['crs_datum_status']}"))
    lines_n = conn.execute("SELECT COUNT(DISTINCT line_code) FROM collar_locations WHERE receipt_id = ?", (rid,)).fetchone()[0]
    multi = conn.execute("SELECT COUNT(*) FROM (SELECT hole_id FROM analysis_observations WHERE receipt_id = ? "
                         "GROUP BY hole_id HAVING COUNT(DISTINCT line_code) > 1)", (rid,)).fetchone()[0]
    line_status = "STOP" if multi else ("WARN" if lines_n == 0 or receipt["drill_line_status"] != "APPROVED" else "PASS")
    g.append(_result("G05", "Drill-line grouping", line_status, "input",
                     f"{lines_n} line codes; drill-line status {receipt['drill_line_status']}; holes on two lines: {multi}"))
    bad_support = conn.execute("SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = ? AND (ABS(support_length_m - 1.0) "
                               "> 1e-9 OR ABS((depth_to_m - depth_from_m) - 1.0) > 1e-9)", (rid,)).fetchone()[0]
    g.append(_result("G06", "Support one metre", "PASS" if bad_support == 0 else "STOP", "input",
                     f"{bad_support} intervals differ from 1 m in support or depth span"))
    pair_status, pair_detail = _pair_check(conn, rid)
    g.append(_result("G07", "Pair validity", pair_status, "analysis", pair_detail))
    cnt_bad = conn.execute("SELECT COUNT(*) FROM hole_occurrence_summaries WHERE receipt_id = ? AND n_intervals != "
                           "binary_n + ambiguous_n + unresolved_n", (rid,)).fetchone()[0]
    cnt_bad += conn.execute("SELECT COUNT(*) FROM line_occurrence_summaries WHERE receipt_id = ? AND n_intervals != "
                            "binary_n + ambiguous_n + unresolved_n", (rid,)).fetchone()[0]
    g.append(_result("G08", "Exclusion accounting", "PASS" if cnt_bad == 0 else "STOP", "summary",
                     f"{cnt_bad} hole or line rows fail the identity"))
    declared = (config["geometry"]["declared_dip_deg"], config["geometry"]["declared_azimuth_deg"])
    uniform = len(orient) == 1
    matches = bool(orient) and all(o == declared for o in orient)
    # A mismatch with the declared convention stops the run. A match is a WARN because one orientation for all holes
    # means the sampling geometry cannot identify structure (specification 03, G09).
    g.append(_result("G09", "Declared orientation", "WARN" if matches else "STOP", "input",
                     f"survey orientations {orient}; declared {declared}; uniform across holes = {uniform}"))
    fracs = conn.execute("SELECT line_code, graphitic_fraction_binary FROM line_occurrence_summaries WHERE receipt_id = ?",
                         (rid,)).fetchall()
    low = [f"{r['line_code']} {r['graphitic_fraction_binary']:.3f}" for r in fracs
           if r["graphitic_fraction_binary"] is not None and r["graphitic_fraction_binary"] < 0.10]
    g.append(_result("G10", "Class imbalance", "WARN" if low else "PASS", "summary",
                     "lines below 10 per cent positive: " + (", ".join(low) or "none")))
    skipped_dirs = [r["direction_id"] for r in conn.execute(
        "SELECT direction_id FROM direction_registry WHERE receipt_id = ? AND status <> 'SUPPORTED'", (rid,))]
    g.append(_result("G12", "Directional support", "WARN" if skipped_dirs else "PASS", "analysis",
                     "skipped directions: " + (", ".join(skipped_dirs) or "none")))
    viol = conn.execute("SELECT COUNT(*) FROM variogram_lag_bins b JOIN variogram_experiments e ON e.experiment_id = b.experiment_id "
                        "WHERE e.receipt_id = ? AND ((b.supported = 1 AND b.gamma IS NULL) OR (b.supported = 0 AND b.gamma IS NOT NULL))",
                        (rid,)).fetchone()[0]
    g.append(_result("G11", "Bin support consistency", "PASS" if viol == 0 else "STOP", "analysis",
                     f"{viol} bins with inconsistent support and gamma"))
    no_param = conn.execute("SELECT COUNT(*) FROM variogram_fits f JOIN variogram_experiments e ON e.experiment_id = f.experiment_id "
                            "WHERE e.receipt_id = ? AND f.fit_status <> 'FITTED' AND EXISTS (SELECT 1 FROM variogram_fit_parameters p "
                            "WHERE p.fit_id = f.fit_id)", (rid,)).fetchone()[0]
    g.append(_result("G13", "No parameters for unidentified fits", "PASS" if no_param == 0 else "STOP", "analysis",
                     f"{no_param} unidentified fits carry parameters"))
    adm = conn.execute("SELECT COUNT(*) FROM variogram_fits f JOIN variogram_experiments e ON e.experiment_id = f.experiment_id "
                       "JOIN variogram_fit_parameters p ON p.fit_id = f.fit_id WHERE e.receipt_id = ? AND f.fit_status = 'FITTED' "
                       "AND (f.admissible <> 1 OR p.estimate < 0 OR (p.parameter = 'range_m' AND p.estimate <= 0))", (rid,)).fetchone()[0]
    g.append(_result("G14", "Fit admissibility", "PASS" if adm == 0 else "STOP", "analysis", f"{adm} inadmissible fitted parameters"))
    bound_hits = conn.execute("SELECT COUNT(*) FROM variogram_fit_parameters p JOIN variogram_fits f ON f.fit_id = p.fit_id "
                              "JOIN variogram_experiments e ON e.experiment_id = f.experiment_id WHERE e.receipt_id = ? "
                              "AND f.fit_status = 'FITTED' AND p.parameter IN ('range_m', 'structured_sill') "
                              "AND (ABS(p.estimate - p.lower_bound) < 1e-9 OR ABS(p.estimate - p.upper_bound) < 1e-9)",
                              (rid,)).fetchone()[0]
    untested = conn.execute("SELECT COUNT(*) FROM variogram_fits f JOIN variogram_experiments e ON e.experiment_id = f.experiment_id "
                            "WHERE e.receipt_id = ? AND e.variant = 'BASE' AND e.direction_id = 'LATERAL_BETWEEN' "
                            "AND f.fit_status = 'FITTED' AND f.stability_status = 'NOT_ASSESSED'", (rid,)).fetchone()[0]
    g.append(_result("G15", "Identifiability", "PASS" if bound_hits == 0 and untested == 0 else "STOP", "analysis",
                     f"{bound_hits} FITTED range or sill values on a bound; {untested} FITTED lateral fits without a "
                     "leave-one-line-out envelope"))
    unstable = conn.execute("SELECT COUNT(*) FROM variogram_fits f JOIN variogram_experiments e ON e.experiment_id = f.experiment_id "
                            "WHERE e.receipt_id = ? AND f.stability_status = 'UNSTABLE'", (rid,)).fetchone()[0]
    lines_bin = conn.execute("SELECT COUNT(DISTINCT line_code) FROM analysis_observations WHERE receipt_id = ? "
                             "AND in_binary_target = 1", (rid,)).fetchone()[0]
    loo_rows = conn.execute("SELECT COUNT(*) FROM sensitivity_runs WHERE run_id = (SELECT MAX(run_id) FROM stage_runs "
                            "WHERE run_kind = 'ANALYSE' AND receipt_id = ?) AND variant_name IN "
                            "('LEAVE_ONE_LINE_OUT:spherical', 'LEAVE_ONE_LINE_OUT:exponential')", (rid,)).fetchone()[0]
    complete = loo_rows == 2 * lines_bin
    g.append(_result("G16", "Leave-one-line-out stability", "STOP" if not complete else ("WARN" if unstable else "PASS"),
                     "analysis", f"{unstable} fits are unstable; {loo_rows} refit rows for {lines_bin} lines (two models each)"))
    dep = conn.execute("SELECT COUNT(*) FROM variogram_fits f JOIN variogram_experiments e ON e.experiment_id = f.experiment_id "
                       "WHERE e.receipt_id = ? AND ABS(f.marginal_departure) > 0.5", (rid,)).fetchone()[0]
    g.append(_result("G17", "Marginal variance departure", "WARN" if dep else "PASS", "analysis",
                     f"{dep} fits depart from p(1-p) by more than 50 per cent"))
    anis = dict(conn.execute("SELECT decision, COUNT(*) FROM anisotropy_diagnostics WHERE receipt_id = ? GROUP BY decision",
                             (rid,)).fetchall())
    claimed = anis.get("ANISOTROPY_SUPPORTED", 0)
    g.append(_result("G18", "Anisotropy claims", "STOP" if claimed else "PASS", "analysis",
                     "anisotropy decisions: " + (", ".join(f"{k} {v}" for k, v in sorted(anis.items())) or "none recorded")))
    within = conn.execute("SELECT COUNT(*) FROM variogram_experiments WHERE receipt_id = ? AND variant = 'BASE' "
                          "AND direction_id <> 'DOWNHOLE_WITHIN' AND within_hole_pairs <> 'EXCLUDED'", (rid,)).fetchone()[0]
    lateral = conn.execute("SELECT COUNT(*) FROM variogram_experiments WHERE receipt_id = ? AND variant = 'BASE' "
                           "AND direction_id = 'LATERAL_BETWEEN'", (rid,)).fetchone()[0]
    g.append(_result("G19", "Base excludes within-hole pairs", "PASS" if within == 0 and lateral == 1 else "STOP", "analysis",
                     f"{within} base between-hole experiments include within-hole pairs; lateral handoff base present: {lateral == 1}"))
    names = [e["name"] for e in config["sensitivity"]]
    n_sens = conn.execute("SELECT COUNT(DISTINCT variant_name) FROM sensitivity_runs WHERE run_id = (SELECT MAX(run_id) "
                          "FROM stage_runs WHERE run_kind = 'ANALYSE' AND receipt_id = ?) AND variant_name IN "
                          f"({','.join('?' * len(names))})", (rid, *names)).fetchone()[0]
    g.append(_result("G20", "Sensitivity completeness", "PASS" if n_sens == len(names) else "STOP", "analysis",
                     f"{n_sens} of {len(names)} configured sensitivity entries have a row (completed or skipped with reason)"))
    sections = conn.execute("SELECT COUNT(*), SUM(vertical_basis = 'RELATIVE_DEPTH') FROM geological_section_registry "
                            "WHERE receipt_id = ?", (rid,)).fetchone()
    n_sec, n_rel = sections[0], sections[1] or 0
    g.append(_result("G21", "Relative depth only", "STOP" if n_rel != n_sec else ("WARN" if n_sec else "PASS"), "geometry",
                     f"{n_rel} of {n_sec} sections labelled RELATIVE_DEPTH; no collar elevation is available, so the "
                     "relative-depth limitation is always reported"))
    absolute_cols = _absolute_columns(conn)
    g.append(_result("G22", "No absolute-elevation products", "STOP" if absolute_cols else "PASS", "geometry",
                     "absolute-elevation columns in the Objective 2 database: " + (", ".join(absolute_cols) or "none")))
    inferred = conn.execute("SELECT COUNT(*) FROM geological_section_registry WHERE receipt_id = ? "
                            "AND observed_or_inferred <> 'OBSERVED_LOG_ONLY'", (rid,)).fetchone()[0]
    g.append(_result("G23", "Observed versus inferred", "PASS" if inferred == 0 else "STOP", "geometry",
                     f"{inferred} section rows claim an inferred contact as observation"))
    synthetic = conn.execute("SELECT COUNT(*) FROM source_receipts WHERE upstream_logical_name <> 'obj1_master'").fetchone()[0]
    synthetic += conn.execute("SELECT COUNT(*) FROM export_manifests WHERE LOWER(artifact_path) LIKE '%synthetic%'").fetchone()[0]
    g.append(_result("G24", "Synthetic pattern not exported", "PASS" if synthetic == 0 else "STOP", "exports",
                     f"{synthetic} receipts or manifest entries carry synthetic data"))
    full = conn.execute("SELECT COUNT(*) FROM continuity_handoff_decisions WHERE receipt_id = ? AND "
                        "full_data_parameters_for_test_folds <> 0", (rid,)).fetchone()[0]
    g.append(_result("G25", "No full-data parameters for test folds", "PASS" if full == 0 else "STOP", "handoff",
                     f"{full} handoff rows allow full-data parameters"))
    status_bad = conn.execute("SELECT COUNT(*) FROM continuity_handoff_decisions WHERE receipt_id = ? AND (decision_status NOT IN "
                              "('PROVISIONAL','NOT_IDENTIFIABLE','REJECTED') OR candidate_family NOT IN ('LATERAL_BETWEEN','NONE'))",
                              (rid,)).fetchone()[0]
    g.append(_result("G27", "Handoff status and basis vocabulary", "PASS" if status_bad == 0 else "STOP", "handoff",
                     f"{status_bad} handoff rows outside the stage vocabulary or the lateral basis"))
    rat = conn.execute("SELECT COUNT(*) FROM continuity_handoff_decisions WHERE receipt_id = ? AND decision_status = 'PROVISIONAL' "
                       "AND rationale NOT LIKE '%exploratory%'", (rid,)).fetchone()[0]
    g.append(_result("G26", "All-data fits labelled exploratory", "PASS" if rat == 0 else "STOP", "handoff",
                     f"{rat} provisional handoffs do not carry the exploratory label"))
    # G28 to G30: provenance of figures and tables, SQL unchanged since registration, and export hashes.
    no_fig_q = conn.execute("SELECT COUNT(*) FROM figure_registry f WHERE NOT EXISTS (SELECT 1 FROM figure_query_registry q "
                            "WHERE q.figure_id = f.figure_id)").fetchone()[0]
    no_tab_q = conn.execute("SELECT COUNT(*) FROM table_registry t WHERE NOT EXISTS (SELECT 1 FROM table_query_registry q "
                            "WHERE q.table_id = t.table_id)").fetchone()[0]
    changed_sql = []
    for row in conn.execute("SELECT sql_path, sql_sha256 FROM figure_query_registry UNION SELECT sql_path, sql_sha256 "
                            "FROM table_query_registry").fetchall():
        path = PROJECT_ROOT / row["sql_path"]
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sql_sha256"]:
            changed_sql.append(row["sql_path"])
    g.append(_result("G28", "Query provenance", "PASS" if no_fig_q == 0 and no_tab_q == 0 and not changed_sql else "STOP",
                     "figures", f"{no_fig_q} figures and {no_tab_q} tables without registered queries; {len(changed_sql)} SQL "
                                "files differ from their registered hash"))
    not_supported_no_reason = conn.execute("SELECT COUNT(*) FROM figure_registry WHERE status = 'NOT_SUPPORTED' "
                                           "AND (reason IS NULL OR reason = '')").fetchone()[0]
    g.append(_result("G29", "NOT_SUPPORTED entries carry a reason", "PASS" if not_supported_no_reason == 0 else "STOP", "figures",
                     f"{not_supported_no_reason} NOT_SUPPORTED figures without a stated reason"))
    bad_hash = []
    for row in conn.execute("SELECT artifact_path, artifact_sha256 FROM export_manifests"):
        path = PROJECT_ROOT / row["artifact_path"]
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != row["artifact_sha256"]:
            bad_hash.append(row["artifact_path"])
    g.append(_result("G30", "Export hashes", "PASS" if not bad_hash else "STOP", "exports",
                     f"{len(bad_hash)} manifest entries differ from the file on disk"))

    for row in g:
        conn.execute("INSERT INTO gate_results (run_id, gate_id, gate_name, status, scope, detail, created_utc) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (run_id, row["gate_id"], row["gate_name"], row["status"], row["scope"], row["detail"], utc_now()))
    stopped = any(r["status"] == "STOP" for r in g)
    conn.execute("UPDATE stage_runs SET status = ?, finished_utc = ? WHERE run_id = ?",
                 ("STOPPED" if stopped else "COMPLETED", utc_now(), run_id))
    conn.close()
    return {"run_id": run_id, "gates": g, "stopped": stopped, "observations": obs_count}

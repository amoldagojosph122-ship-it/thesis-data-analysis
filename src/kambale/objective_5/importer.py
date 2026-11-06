"""Read-only import of the locked inputs into the Objective 5 database, with file receipts.

Imported: every logged interval of the Objective 3 receipt (binary targets flagged), collar coordinates of the same dataset
version, the observed weathering front of each hole (Objective 3 rule, reused), the locked handoffs of both Objective 4
tiers, the Objective 4 validated pooled scores of the selected and runner-up models, and the Objective 2 down-hole
variogram check. A handoff mismatch or a down-hole parameter mismatch stops the import before anything is written.
"""

from __future__ import annotations

import json
import re
import sqlite3

from kambale.objective_3 import weathering_front
from kambale.objective_3.config import load_config as load_o3_config
from kambale.objective_5.config import (O2_DB_PATH, O3_CONFIG_PATH, O3_DB_PATH, O5_CONFIG_PATH, PROJECT_ROOT,
                                        THESIS_DB_PATH, StopError, code_commit, load_config, rel, sha256_file, utc_now)
from kambale.objective_5.db import connect_o5, connect_readonly

# gates.STOP states "tolerance 1e-4" for the down-hole parameters; the value is held here, not in the configuration.
DOWNHOLE_TOLERANCE = 1e-4

CLEARED_TABLES = ("final_refits", "bootstrap_replicates", "bootstrap_summary", "grid_cells", "grid_layers", "grid_meta",
                  "carried_validation", "handoffs", "downhole_variogram", "hole_fronts", "collars", "observations",
                  "input_files", "source_receipts", "classification_rules", "figure_sql_registry", "figure_registry",
                  "table_sql_registry", "table_registry", "export_manifests")


def check_handoff_match(tier: str, selected: str, runner_up: str, required: dict) -> str:
    """MATCH when the locked selected and runner-up models equal the configuration; otherwise StopError."""
    req = required[tier]
    if selected != req["selected"] or runner_up != req["runner_up"]:
        raise StopError(f"{tier}: locked handoff names selected {selected} and runner-up {runner_up}; the configuration "
                        f"requires {req['selected']} and {req['runner_up']}")
    return "MATCH"


def check_downhole(found: dict, expected: dict, tolerance: float) -> float:
    """Compare the fitted down-hole model with the predeclared values; StopError on any difference above tolerance."""
    if found["model"] != expected["model"]:
        raise StopError(f"down-hole model {found['model']} differs from the expected {expected['model']}")
    pairs = (("nugget", "nugget"), ("structured_sill", "structured_sill"), ("practical_range_m", "practical_range_m"))
    worst = 0.0
    for got_key, exp_key in pairs:
        diff = abs(float(found[got_key]) - float(expected[exp_key]))
        worst = max(worst, diff)
        if diff > tolerance:
            raise StopError(f"down-hole {got_key} {found[got_key]} differs from expected {expected[exp_key]} by {diff:g} "
                            f"(tolerance {tolerance:g})")
    return worst


def parse_downhole_experiment(text: str) -> tuple[str, str]:
    """'DOWNHOLE_WITHIN, config O2-CFG-...' -> ('DOWNHOLE_WITHIN', 'O2-CFG-...')."""
    m = re.match(r"^\s*([A-Z_0-9]+)\s*,\s*config\s+(\S+)\s*$", text)
    if not m:
        raise StopError(f"cannot parse the down-hole experiment reference {text!r}")
    return m.group(1), m.group(2)


def select_downhole_fit(o2: sqlite3.Connection, experiment_text: str) -> dict:
    """The FITTED model of the named down-hole experiment with the smaller objective value."""
    direction, config_version = parse_downhole_experiment(experiment_text)
    rows = o2.execute(
        "SELECT f.fit_id, f.experiment_id, f.model, f.objective_value, e.config_version "
        "FROM variogram_fits f JOIN variogram_experiments e ON e.experiment_id = f.experiment_id "
        "WHERE e.direction_id = ? AND e.config_version = ? AND e.variant = 'BASE' AND f.fit_status = 'FITTED' "
        "AND f.objective_value IS NOT NULL ORDER BY f.objective_value, f.fit_id", (direction, config_version)).fetchall()
    if not rows:
        raise StopError(f"no FITTED {direction} fit for configuration {config_version}")
    best = dict(rows[0])
    params = {r["parameter"]: float(r["estimate"]) for r in o2.execute(
        "SELECT parameter, estimate FROM variogram_fit_parameters WHERE fit_id = ?", (best["fit_id"],))}
    missing = {"nugget", "structured_sill", "range_m"} - set(params)
    if missing:
        raise StopError(f"down-hole fit {best['fit_id']} lacks parameters {sorted(missing)}")
    return {"fit_id": best["fit_id"], "experiment_id": best["experiment_id"], "config_version": config_version,
            "model": best["model"], "objective_value": float(best["objective_value"]), "nugget": params["nugget"],
            "structured_sill": params["structured_sill"], "practical_range_m": params["range_m"]}


def read_handoff(tier: str, o4_path, required: dict) -> dict:
    o4 = connect_readonly(o4_path)
    try:
        sel = o4.execute("SELECT * FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()
        ru = o4.execute("SELECT * FROM comparison_decisions WHERE role = 'COMPARATOR'").fetchone()
        lh = o4.execute("SELECT * FROM locked_handoff_receipts WHERE tier = ?", (tier,)).fetchone()
        if sel is None or ru is None or lh is None:
            raise StopError(f"{tier}: the Objective 4 database lacks a selected/comparator decision or a locked receipt")
        if lh["selected_model_id"] != sel["model_id"] or lh["decision_id"] != sel["decision_id"]:
            raise StopError(f"{tier}: the locked receipt does not name the selected decision row")
        pooled = [dict(r) for r in o4.execute(
            "SELECT model_id, metric_id, weighting, value, status, n, n_positive FROM pooled_metrics "
            "WHERE model_id IN (?, ?) AND metric_id IN ('BRIER', 'ROC_AUC')", (sel["model_id"], ru["model_id"]))]
        handoff = dict(lh)
    finally:
        o4.close()
    status = check_handoff_match(tier, sel["model_id"], ru["model_id"], required)
    return {"tier": tier, "selected": sel["model_id"], "runner_up": ru["model_id"], "sel_row": dict(sel),
            "ru_decision_id": ru["decision_id"], "locked": handoff, "pooled": pooled, "match_status": status}


def _o3_latest_receipt(o3: sqlite3.Connection) -> dict:
    row = o3.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
    if row is None:
        raise StopError("the Objective 3 database has no receipt")
    return dict(row)


def import_inputs(o5_path=None, config_path=None) -> dict:
    cfg, cfg_sha = load_config(config_path or O5_CONFIG_PATH)
    inputs = cfg["inputs"]
    if inputs["label_rule_id"] != "DESIGN_8_2_v1":
        raise StopError("inputs.label_rule_id must be DESIGN_8_2_v1")
    o3_cfg, o3_cfg_sha = load_o3_config(O3_CONFIG_PATH)
    front_cfg = o3_cfg["features"]["derived"]["depth_below_weathering_front_m"]
    required = inputs["require_handoff_match"]

    # 1. Handoffs and the down-hole check come first: a STOP here writes nothing.
    o4_paths = {item["tier"]: PROJECT_ROOT / item["database"] for item in inputs["handoffs"]}
    handoffs = []
    for item in inputs["handoffs"]:
        handoffs.append(read_handoff(item["tier"], o4_paths[item["tier"]], required))
    o2 = connect_readonly(O2_DB_PATH)
    try:
        downhole = select_downhole_fit(o2, inputs["downhole_variogram"]["experiment"])
    finally:
        o2.close()
    exp = inputs["downhole_variogram"]["expected_values"]
    tol = DOWNHOLE_TOLERANCE
    worst = check_downhole(downhole, exp, tol)
    downhole["status"] = "MATCH"
    downhole["max_abs_difference"] = worst
    downhole["tolerance"] = tol

    # 2. O3 observations, collars and observed fronts.
    o3 = connect_readonly(O3_DB_PATH)
    try:
        receipt = _o3_latest_receipt(o3)
        if receipt["label_rule_id"] != inputs["label_rule_id"]:
            raise StopError("the Objective 3 receipt uses a different label rule")
        obs = [dict(r) for r in o3.execute(
            "SELECT upstream_interval_id, hole_id, line_code, depth_from_m, midpoint_m, easting_m, northing_m, "
            "z_relative_m, in_binary_target, indicator, weathering_code, label_state FROM analysis_observations "
            "WHERE receipt_id = ? ORDER BY upstream_interval_id", (receipt["receipt_id"],))]
        fronts = weathering_front.hole_fronts(o3, receipt["receipt_id"], list(front_cfg["front_codes"]))
    finally:
        o3.close()
    binary = [r for r in obs if r["in_binary_target"] == 1]
    if not binary:
        raise StopError("no binary intervals in the Objective 3 receipt")
    holes_obs = sorted({r["hole_id"] for r in obs})

    thesis = connect_readonly(THESIS_DB_PATH)
    try:
        collars = [dict(r) for r in thesis.execute(
            "SELECT hole_id, line_code, utm_easting_m, utm_northing_m, max_depth_m, dataset_version_id FROM holes "
            "WHERE dataset_version_id = ? ORDER BY hole_id", (receipt["upstream_dataset_version_id"],))]
    finally:
        thesis.close()
    collar_ids = {c["hole_id"] for c in collars}
    if collar_ids != set(holes_obs):
        raise StopError("collar hole identifiers differ from the Objective 3 observation holes")
    if any(c["utm_easting_m"] is None or c["utm_northing_m"] is None for c in collars):
        raise StopError("a collar lacks UTM coordinates")
    line_of = {}
    for r in obs:
        line_of.setdefault(r["hole_id"], r["line_code"])

    # 3. Write everything in one transaction.
    o5 = connect_o5(o5_path)
    try:
        run_id = o5.execute("INSERT INTO stage_runs (run_kind, config_version, config_sha256, started_utc, status, "
                            "code_commit, note) VALUES ('IMPORT', ?, ?, ?, 'RUNNING', ?, 'locked inputs')",
                            (cfg["config_version"], cfg_sha, utc_now(), code_commit())).lastrowid
        now = utc_now()
        o5.execute("BEGIN IMMEDIATE")
        try:
            for table in CLEARED_TABLES:
                o5.execute(f"DELETE FROM {table}")
            files = {"o5_config": O5_CONFIG_PATH, "o3_config": O3_CONFIG_PATH, "o3_database": O3_DB_PATH,
                     "o2_database": O2_DB_PATH, "thesis_database": THESIS_DB_PATH}
            for item in inputs["handoffs"]:
                files[f"o4_{item['tier'].lower()}_database"] = o4_paths[item["tier"]]
            for role, path in files.items():
                o5.execute("INSERT INTO input_files (role, path, bytes, sha256, recorded_utc) VALUES (?, ?, ?, ?, ?)",
                           (role, rel(path), path.stat().st_size, sha256_file(path), now))
            n_binary = len(binary)
            prevalence = sum(r["indicator"] for r in binary) / n_binary
            receipt_id = o5.execute(
                "INSERT INTO source_receipts (o3_path, o3_receipt_id, label_rule_id, geometry_status, vertical_basis, "
                "crs_key, config_version, config_sha256, n_intervals, n_binary, n_holes, n_collars, prevalence, "
                "imported_utc, code_commit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rel(O3_DB_PATH), receipt["receipt_id"], inputs["label_rule_id"], receipt["geometry_status"],
                 receipt["vertical_basis"], receipt["crs_key"], cfg["config_version"], cfg_sha, len(obs), n_binary,
                 len(holes_obs), len(collars), prevalence, now, code_commit())).lastrowid
            o5.executemany(
                "INSERT INTO observations (upstream_interval_id, receipt_id, hole_id, line_code, depth_from_m, midpoint_m, "
                "easting_m, northing_m, z_relative_m, in_binary_target, indicator, weathering_code, label_state) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(r["upstream_interval_id"], receipt_id, r["hole_id"], r["line_code"], r["depth_from_m"],
                  r["midpoint_m"], r["easting_m"], r["northing_m"], r["z_relative_m"], r["in_binary_target"],
                  r["indicator"], r["weathering_code"], r["label_state"]) for r in obs])
            o5.executemany(
                "INSERT INTO collars (hole_id, line_code, easting_m, northing_m, max_depth_m, dataset_version_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(c["hole_id"], line_of[c["hole_id"]], c["utm_easting_m"], c["utm_northing_m"], c["max_depth_m"],
                  c["dataset_version_id"]) for c in collars])
            o5.executemany("INSERT INTO hole_fronts (hole_id, easting_m, northing_m, front_z_m) VALUES (?, ?, ?, ?)",
                           [(h, v[0], v[1], v[2]) for h, v in sorted(fronts.items())])
            for hd in handoffs:
                sel_row = hd["sel_row"]
                lk = hd["locked"]
                req = required[hd["tier"]]
                o4_path = o4_paths[hd["tier"]]
                o5.execute(
                    "INSERT INTO handoffs (tier, o4_path, o4_file_sha256, o4_locked_receipt_id, o4_locked_receipt_sha256, "
                    "o4_config_version, split_plan_id, selected_model_id, selected_decision_id, runner_up_model_id, "
                    "runner_up_decision_id, required_selected, required_runner_up, match_status, improvement_status, "
                    "delta_brier, delta_brier_ci_low, delta_brier_ci_high, selected_fold_consistency, created_utc) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (hd["tier"], rel(o4_path), sha256_file(o4_path), lk["receipt_id"], lk["receipt_sha256"],
                     lk["config_version"], lk["split_plan_id"], hd["selected"], sel_row["decision_id"], hd["runner_up"],
                     hd["ru_decision_id"], req["selected"], req["runner_up"], hd["match_status"],
                     sel_row["improvement_status"], sel_row["delta_brier"], sel_row["ci_low"], sel_row["ci_high"],
                     sel_row["fold_consistency"], now))
                for p in hd["pooled"]:
                    role = "SELECTED" if p["model_id"] == hd["selected"] else "RUNNER_UP"
                    o5.execute(
                        "INSERT INTO carried_validation (tier, role, model_id, metric_id, weighting, value, status, n, "
                        "n_positive) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (hd["tier"], role, p["model_id"], p["metric_id"], p["weighting"], p["value"], p["status"],
                         p["n"], p["n_positive"]))
            o5.execute(
                "INSERT INTO downhole_variogram (check_id, o2_fit_id, o2_experiment_id, o2_config_version, model, "
                "objective_value, nugget, structured_sill, practical_range_m, expected_model, expected_nugget, "
                "expected_structured_sill, expected_practical_range_m, tolerance, max_abs_difference, status) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (downhole["fit_id"], downhole["experiment_id"], downhole["config_version"], downhole["model"],
                 downhole["objective_value"], downhole["nugget"], downhole["structured_sill"],
                 downhole["practical_range_m"], exp["model"], exp["nugget"], exp["structured_sill"],
                 exp["practical_range_m"], tol, worst, downhole["status"]))
            o5.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ? WHERE run_id = ?",
                       (utc_now(), run_id))
            o5.execute("COMMIT")
        except Exception:
            if o5.in_transaction:
                o5.execute("ROLLBACK")
            raise
        return {"receipt_id": receipt_id, "run_id": run_id, "intervals": len(obs), "binary": n_binary,
                "holes": len(holes_obs), "collars": len(collars), "fronts": len(fronts), "prevalence": prevalence,
                "handoffs": {h["tier"]: {"selected": h["selected"], "runner_up": h["runner_up"],
                                         "match": h["match_status"]} for h in handoffs},
                "downhole": {k: downhole[k] for k in ("fit_id", "model", "nugget", "structured_sill",
                                                       "practical_range_m", "max_abs_difference")},
                "o3_receipt_id": receipt["receipt_id"]}
    finally:
        o5.close()

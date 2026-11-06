"""Gate runner for Objective 4 (specification 03)."""

from __future__ import annotations

import json
from pathlib import Path

from kambale.objective_4.config import (O3_DB_PATH, O4_CONFIG_PATH, O4_DB_PATH, O4_FIGURE_DIR, PROJECT_ROOT,
                                        code_commit, load_config, sha256_bytes, sha256_file, sha256_text, utc_now)
from kambale.objective_4.db import connect_o4, connect_readonly


def _g(gate_id, name, status, scope, detail):
    return {"gate_id": gate_id, "gate_name": name, "status": status, "scope": scope, "detail": detail}


def _o3_prediction_hash(o3, split_plan_id):
    rows = [dict(r) for r in o3.execute(
        "SELECT training_run_id, split_plan_id, fold_id, observation_id, hole_id, line_code, family_id, candidate_run_id, "
        "true_label, p_raw, p_calibrated, clipped_calibrated, predicted_class, threshold FROM predictions_oof "
        "WHERE split_plan_id = ? ORDER BY family_id, observation_id", (split_plan_id,))]
    canon = "\n".join(json.dumps({
        "model_id": r["family_id"], "observation_id": r["observation_id"], "fold_id": r["fold_id"],
        "true_label": r["true_label"], "p_raw": round(float(r["p_raw"]), 15),
        "p_calibrated": round(float(r["p_calibrated"]), 15), "threshold": round(float(r["threshold"]), 15),
        "predicted_class": r["predicted_class"], "clipped": r["clipped_calibrated"]},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    return sha256_text(canon), rows


def run(o4_path=None, o3_path=O3_DB_PATH, config_path=None) -> dict:
    config, config_sha = load_config(config_path or O4_CONFIG_PATH)
    conn = connect_o4(o4_path or O4_DB_PATH)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise RuntimeError("no receipt: run the import first")
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, started_utc, status, "
            "code_commit, note) VALUES ('VERIFY', ?, ?, ?, ?, 'RUNNING', ?, 'gate runner')",
            (config["config_version"], config_sha, receipt["receipt_id"], utc_now(), code_commit())).lastrowid
        created = utc_now()
        gates = []
        o3 = connect_readonly(o3_path)
        try:
            o3_receipt = dict(o3.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone())
            split = dict(o3.execute("SELECT * FROM spatial_split_plans WHERE primary_plan = 1").fetchone())
            target = dict(o3.execute("SELECT * FROM target_registries WHERE receipt_id = ? LIMIT 1",
                                     (o3_receipt["receipt_id"],)).fetchone())
            geom = dict(o3.execute("SELECT * FROM geometry_versions WHERE receipt_id = ? LIMIT 1",
                                   (o3_receipt["receipt_id"],)).fetchone())
            snap_sha, o3_preds = _o3_prediction_hash(o3, split["split_plan_id"])
            o3_thr = {(r["family_id"], r["fold_id"]): float(r["threshold"]) for r in o3_preds}
            m3_bad = 0
            rf = {(r["observation_id"]): r["p_calibrated"] for r in o3_preds if r["family_id"] == "M2_RF"}
            for r in o3_preds:
                if r["family_id"] == "M3_HYBRID":
                    m3_bad += abs(float(r["p_calibrated"]) - float(rf.get(r["observation_id"], -1))) > 1e-12
        finally:
            o3.close()

        gates.append(_g("G01", "Objective 3 snapshot receipt", "PASS" if
                       snap_sha == receipt["o3_prediction_snapshot_sha256"] and
                       o3_receipt["receipt_id"] == receipt["o3_receipt_id"] else "STOP", "input",
                       f"recomputed snapshot {snap_sha[:16]} vs receipt {receipt['o3_prediction_snapshot_sha256'][:16]}; "
                       f"O3 receipt {o3_receipt['receipt_id']}"))
        gates.append(_g("G02", "Frozen split plan", "PASS" if split["split_plan_id"] == receipt["o3_split_plan_id"] and
                       split["plan_sha256"] == receipt["o3_split_plan_sha256"] else "STOP", "input",
                       f"{split['split_plan_id']} hash {split['plan_sha256'][:16]}"))
        gates.append(_g("G03", "Target, label and geometry reference", "PASS" if
                       target["label_rule_id"] == receipt["o1_label_rule_id"] and
                       geom["geometry_version_id"] == receipt["geometry_version_id"] and
                       geom["geometry_status"] == "PROVISIONAL_RELATIVE" else "STOP", "input",
                       f"rule {target['label_rule_id']}; geometry {geom['geometry_version_id']} "
                       f"{geom['geometry_status']}"))
        bad_prob = conn.execute("SELECT COUNT(*) FROM prediction_snapshot WHERE p_raw < 0 OR p_raw > 1 OR "
                                "p_calibrated < 0 OR p_calibrated > 1").fetchone()[0]
        dup = conn.execute("SELECT COUNT(*) FROM (SELECT model_id, observation_id, COUNT(*) c FROM prediction_snapshot "
                           "GROUP BY model_id, observation_id HAVING c > 1)").fetchone()[0]
        gates.append(_g("G04", "Prediction snapshot integrity", "PASS" if bad_prob == 0 and dup == 0 else "STOP",
                       "input", f"{bad_prob} out-of-bounds probabilities; {dup} duplicate model/observation pairs"))
        feasible = list(config["evaluation"]["models"]["feasible"])
        common = {r[0] for r in conn.execute("SELECT observation_id FROM evaluation_population WHERE in_common_cohort = 1")}
        missing = 0
        for m in feasible:
            ids = {r[0] for r in conn.execute("SELECT observation_id FROM prediction_snapshot WHERE model_id = ?", (m,))}
            missing += len(common - ids)
        gates.append(_g("G05", "Common cohort identical across models", "PASS" if missing == 0 and common else "STOP",
                       "cohort", f"{len(common)} common observations; {missing} missing model IDs"))
        m1 = conn.execute("SELECT * FROM prediction_coverage WHERE model_id = 'M1_IK'").fetchone()
        m1_dec = conn.execute("SELECT role, improvement_status FROM comparison_decisions WHERE model_id = 'M1_IK'").fetchone()
        gates.append(_g("G06", "M1 coverage reported and not ranked", "PASS" if m1 and m1["n_predicted"] == 0 and
                       m1_dec and m1_dec["role"] == "NOT_COMPARABLE" else "STOP", "model",
                       f"M1 predicted {m1['n_predicted'] if m1 else '?'}, failed {m1['n_failed'] if m1 else '?'}; "
                       f"decision {m1_dec['improvement_status'] if m1_dec else 'MISSING'}"))
        m3 = conn.execute("SELECT * FROM candidate_registry WHERE model_id = 'M3_HYBRID'").fetchone()
        m3_dec = conn.execute("SELECT role, improvement_status FROM comparison_decisions WHERE model_id = 'M3_HYBRID'").fetchone()
        gates.append(_g("G07", "M3 fallback identity and not ranked", "PASS" if m3 and m3["fallback_identical_to"] == "M2_RF"
                       and m3_bad == 0 and m3_dec and m3_dec["role"] == "NOT_COMPARABLE" else "STOP", "model",
                       f"fallback {m3['fallback_identical_to'] if m3 else '?'}; {m3_bad} predictions differ from M2_RF; "
                       f"decision {m3_dec['improvement_status'] if m3_dec else 'MISSING'}"))
        thr_bad = 0
        for r in conn.execute("SELECT model_id, fold_id, threshold FROM prediction_snapshot").fetchall():
            if abs(float(r["threshold"]) - o3_thr.get((r["model_id"], r["fold_id"]), -1)) > 1e-12:
                thr_bad += 1
        gates.append(_g("G08", "Thresholds frozen from O3", "PASS" if thr_bad == 0 else "STOP", "prediction",
                       f"{thr_bad} snapshot thresholds differ from the O3 training-only thresholds"))
        model_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        gates.append(_g("G09", "No model refit in O4", "PASS" if not ({"training_runs", "model_artifacts"} & model_tables)
                       else "STOP", "model", "O4 contains no training or model-artifact table"))
        plan = conn.execute("SELECT * FROM evaluation_plan").fetchone()
        gates.append(_g("G10", "Evaluation plan declared", "PASS" if plan and plan["primary_endpoint"] == "BRIER" and
                       plan["primary_weighting"] == "INTERVAL" else "STOP", "plan",
                       f"primary {plan['primary_endpoint'] if plan else 'MISSING'} / "
                       f"{plan['primary_weighting'] if plan else 'MISSING'}"))
        weights_bad = conn.execute("SELECT COUNT(*) FROM evaluation_population WHERE weight_interval <= 0 OR "
                                   "weight_equal_hole <= 0").fetchone()[0]
        gates.append(_g("G11", "Cohort and weights declared", "PASS" if weights_bad == 0 and common else "STOP", "cohort",
                       f"{weights_bad} non-positive weights; {len(common)} common observations"))
        designs = {r[0]: r[1] for r in conn.execute("SELECT design_id, method FROM resampling_designs")}
        gates.append(_g("G12", "Bootstrap uses spatial units", "PASS" if "HOLE_CLUSTER" in designs.values() and
                       "LINE_CLUSTER" in designs.values() else "STOP", "uncertainty",
                       "designs: " + (", ".join(f"{k}={v}" for k, v in sorted(designs.items())) or "none")))
        audit = {r[0]: r[1] for r in conn.execute("SELECT check_name, status FROM evaluation_audit_log")}
        gates.append(_g("G13", "Metric numerical cross-check", "PASS" if audit.get("BRIER_NUMERICAL_CROSS_CHECK") == "PASS"
                       else "STOP", "metric", "Brier vector vs independent loop"))
        cal_rows = conn.execute("SELECT COUNT(*) FROM calibration_diagnostics").fetchone()[0]
        columns = [c[1].lower() for c in conn.execute("PRAGMA table_info(prediction_snapshot)")]
        gates.append(_g("G14", "Calibration is diagnostic only", "PASS" if cal_rows > 0 and
                       not any("recalibrat" in c for c in columns) else "STOP", "calibration",
                       f"{cal_rows} diagnostic rows; no recalibrated prediction column"))
        bad_undef = conn.execute("SELECT COUNT(*) FROM pooled_metrics WHERE status = 'UNDEFINED' AND value IS NOT NULL"
                                 ).fetchone()[0]
        bad_undef += conn.execute("SELECT COUNT(*) FROM fold_metrics WHERE status = 'UNDEFINED' AND value IS NOT NULL"
                                  ).fetchone()[0]
        gates.append(_g("G15", "Undefined metrics are not coerced", "PASS" if bad_undef == 0 else "STOP", "metric",
                       f"{bad_undef} undefined metrics carry a value"))
        brier = {r["model_id"]: r["value"] for r in conn.execute(
            "SELECT model_id, value FROM pooled_metrics WHERE weighting = 'INTERVAL' AND metric_id = 'BRIER' "
            "AND status = 'DEFINED'")}
        feasible_brier = {m: brier[m] for m in feasible if m in brier}
        selected = conn.execute("SELECT model_id, delta_brier, ci_low, ci_high FROM comparison_decisions WHERE "
                                "role = 'SELECTED'").fetchone()
        min_model = min(feasible_brier, key=lambda m: feasible_brier[m]) if feasible_brier else None
        gates.append(_g("G16", "Decision rule followed", "PASS" if selected and selected["model_id"] == min_model
                       else "STOP", "decision",
                       f"selected {selected['model_id'] if selected else 'MISSING'}; lowest Brier {min_model}"))
        handoff = conn.execute("SELECT * FROM locked_handoff_receipts").fetchone()
        gates.append(_g("G17", "Locked handoff receipt", "PASS" if handoff and selected and
                       handoff["selected_model_id"] == selected["model_id"] and handoff["receipt_sha256"] else "STOP",
                       "decision", f"selected {handoff['selected_model_id'] if handoff else 'MISSING'}; receipt hash present"))
        fig_bad = 0
        for r in conn.execute("SELECT figure_id, status FROM figure_registry").fetchall():
            n = conn.execute("SELECT COUNT(*) FROM figure_sql_registry WHERE figure_id = ?", (r["figure_id"],)).fetchone()[0]
            if r["status"] == "GENERATED" and n == 0:
                fig_bad += 1
            for q in conn.execute("SELECT sql_path, sql_sha256 FROM figure_sql_registry WHERE figure_id = ?",
                                  (r["figure_id"],)).fetchall():
                p = Path(q["sql_path"])
                if not p.exists() or sha256_bytes(p.read_bytes()) != q["sql_sha256"]:
                    fig_bad += 1
        tab_bad = 0
        for r in conn.execute("SELECT table_id, status FROM table_registry").fetchall():
            n = conn.execute("SELECT COUNT(*) FROM table_sql_registry WHERE table_id = ?", (r["table_id"],)).fetchone()[0]
            if r["status"] == "GENERATED" and n == 0:
                tab_bad += 1
            for q in conn.execute("SELECT sql_path, sql_sha256 FROM table_sql_registry WHERE table_id = ?",
                                  (r["table_id"],)).fetchall():
                p = Path(q["sql_path"])
                if not p.exists() or sha256_bytes(p.read_bytes()) != q["sql_sha256"]:
                    tab_bad += 1
        gates.append(_g("G18", "Figure and table query provenance", "PASS" if fig_bad == 0 and tab_bad == 0 else "STOP",
                       "export", f"{fig_bad} figure and {tab_bad} table entries are unregistered or changed"))
        man_bad = 0
        for r in conn.execute("SELECT artifact_path, sha256 FROM export_manifests").fetchall():
            p = Path(r["artifact_path"])
            if not p.exists() or sha256_file(p) != r["sha256"]:
                man_bad += 1
        gates.append(_g("G19", "Export hashes", "PASS" if man_bad == 0 else "STOP", "export",
                       f"{man_bad} manifest entries are missing or differ from the file"))
        geometry_ok = (receipt["geometry_status"] == "PROVISIONAL_RELATIVE" and
                       receipt["vertical_basis"] == "RELATIVE_TO_COLLAR")
        gates.append(_g("G20", "Relative geometry only", "PASS" if geometry_ok else "STOP", "geometry",
                       f"{receipt['geometry_status']}; {receipt['vertical_basis']}"))
        absolute_cols = []
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
            for col in conn.execute(f"PRAGMA table_info({table})").fetchall():
                if "absolute" in col["name"].lower():
                    absolute_cols.append(f"{table}.{col['name']}")
        gates.append(_g("G21", "No absolute-elevation product", "PASS" if not absolute_cols else "STOP", "geometry",
                       "absolute columns: " + (", ".join(absolute_cols) or "none")))
        grade_cols = []
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
            for col in conn.execute(f"PRAGMA table_info({table})").fetchall():
                if any(word in col["name"].lower() for word in ("grade", "tonnage", "resource", "tgc")):
                    grade_cols.append(f"{table}.{col['name']}")
        gates.append(_g("G22", "No grade, tonnage or resource product", "PASS" if not grade_cols else "STOP", "scope",
                       "grade-like columns: " + (", ".join(grade_cols) or "none")))
        synthetic = conn.execute("SELECT COUNT(*) FROM source_receipts WHERE o3_logical_name <> 'obj3_models'").fetchone()[0]
        gates.append(_g("G23", "No synthetic data", "PASS" if synthetic == 0 else "STOP", "input",
                       f"{synthetic} receipts reference a non-Objective-3 source"))
        cov_n = conn.execute("SELECT COUNT(*) FROM prediction_coverage").fetchone()[0]
        gates.append(_g("G24", "Coverage reported for every candidate", "PASS" if cov_n >= 6 else "STOP", "coverage",
                       f"{cov_n} coverage rows"))
        gates.append(_g("G25", "Cluster uncertainty for decisions", "PASS" if "HOLE_CLUSTER" in designs.values() and
                       selected and selected["ci_low"] is not None and selected["ci_high"] is not None else "STOP",
                       "uncertainty", "selected decision carries a hole-cluster interval"))
        gates.append(_g("G26", "External validity not claimed", "PASS" if handoff and "not an external" in handoff["caveats"]
                       else "WARN", "decision", "handoff caveat states internal held-out validation"))
        gates.append(_g("G27", "Objective 3 prediction snapshot", "PASS" if snap_sha == receipt["o3_prediction_snapshot_sha256"]
                       else "STOP", "input", f"snapshot {snap_sha[:16]}"))
        stopped = any(g["status"] == "STOP" for g in gates)
        conn.execute("DELETE FROM gate_results WHERE run_id = ?", (run_id,))
        conn.executemany("INSERT INTO gate_results (run_id, gate_id, gate_name, status, scope, detail, created_utc) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?)",
                         [(run_id, g["gate_id"], g["gate_name"], g["status"], g["scope"], g["detail"], created)
                          for g in gates])
        conn.execute("UPDATE stage_runs SET status = ?, finished_utc = ? WHERE run_id = ?",
                     ("STOPPED" if stopped else "COMPLETED", utc_now(), run_id))
        return {"run_id": run_id, "stopped": stopped, "gates": gates}
    finally:
        conn.close()

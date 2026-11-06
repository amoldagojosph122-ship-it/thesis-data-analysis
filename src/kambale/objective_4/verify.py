"""Gate runner for Objective 4 (specification 03). Gates are generic: they read the tier's config and recompute what they
check. Nothing is loosened: a gate that fails is STOP unless it was already a WARN by design (G26)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from kambale.objective_4.config import (O3_DB_PATH, O4_CONFIG_PATH, O4_DB_PATH, O4_FIGURE_DIR, PROJECT_ROOT,
                                        code_commit, load_config, sha256_bytes, sha256_file, sha256_text, utc_now)
from kambale.objective_4.db import connect_o4, connect_readonly

IDENTITY_TOLERANCE = 1e-12
FOLD_UNIT_METHOD = {"HELD_OUT_LINE": "LEAVE_ONE_DRILL_LINE_OUT", "INTERLEAVED_HOLE_FOLD": "INTERLEAVED_HOLES_WITHIN_LINE"}


def _g(gate_id, name, status, scope, detail):
    return {"gate_id": gate_id, "gate_name": name, "status": status, "scope": scope, "detail": detail}


def _o3_prediction_hash(o3, split_plan_id):
    rows = [dict(r) for r in o3.execute(
        "SELECT training_run_id, split_plan_id, fold_id, observation_id, hole_id, line_code, family_id, candidate_run_id, "
        "true_label, p_raw, p_calibrated, clipped_calibrated, predicted_class, threshold FROM predictions_oof "
        "WHERE split_plan_id = ? ORDER BY candidate_run_id, observation_id", (split_plan_id,))]
    canon = "\n".join(json.dumps({
        "model_id": r["candidate_run_id"], "observation_id": r["observation_id"], "fold_id": r["fold_id"],
        "true_label": r["true_label"], "p_raw": round(float(r["p_raw"]), 15),
        "p_calibrated": round(float(r["p_calibrated"]), 15), "threshold": round(float(r["threshold"]), 15),
        "predicted_class": r["predicted_class"], "clipped": r["clipped_calibrated"]},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    return sha256_text(canon), rows


def _recomputed_identities(conn, order, common):
    """Pairwise identity recomputed from the stored O4 snapshot on the common cohort (numpy, independent of the importer)."""
    snap = {}
    for r in conn.execute("SELECT p.model_id, p.observation_id, p.p_calibrated FROM prediction_snapshot p "
                          "JOIN evaluation_population e ON e.receipt_id = p.receipt_id AND e.observation_id = p.observation_id "
                          "WHERE e.in_common_cohort = 1"):
        snap.setdefault(r["model_id"], {})[r["observation_id"]] = float(r["p_calibrated"])
    result = {}
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            if a not in snap or b not in snap or not common:
                result[(a, b)] = (None, False)
                continue
            ids = sorted(common)
            va = np.array([snap[a][o] for o in ids])
            vb = np.array([snap[b][o] for o in ids])
            diff = float(np.max(np.abs(va - vb)))
            result[(a, b)] = (diff, diff <= IDENTITY_TOLERANCE)
    return result


def run(o4_path=None, o3_path=O3_DB_PATH, config_path=None) -> dict:
    config, config_sha = load_config(config_path or O4_CONFIG_PATH)
    ev = config["evaluation"]
    feasible = list(ev["models"]["feasible"])
    split_plan_id = config["paths"]["o3_split_plan_id"]
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
            split_row = o3.execute("SELECT * FROM spatial_split_plans WHERE split_plan_id = ?", (split_plan_id,)).fetchone()
            split = dict(split_row) if split_row else {"split_plan_id": None, "plan_sha256": "", "method": None}
            target = dict(o3.execute("SELECT * FROM target_registries WHERE receipt_id = ? LIMIT 1",
                                     (o3_receipt["receipt_id"],)).fetchone())
            geom = dict(o3.execute("SELECT * FROM geometry_versions WHERE receipt_id = ? LIMIT 1",
                                   (o3_receipt["receipt_id"],)).fetchone())
            snap_sha, o3_preds = _o3_prediction_hash(o3, split_plan_id)
            o3_thr = {(r["candidate_run_id"], r["fold_id"]): float(r["threshold"]) for r in o3_preds}
        finally:
            o3.close()

        gates.append(_g("G01", "Objective 3 snapshot receipt", "PASS" if
                        snap_sha == receipt["o3_prediction_snapshot_sha256"] and
                        o3_receipt["receipt_id"] == receipt["o3_receipt_id"] else "STOP", "input",
                        f"recomputed snapshot {snap_sha[:16]} vs receipt {receipt['o3_prediction_snapshot_sha256'][:16]}; "
                        f"O3 receipt {o3_receipt['receipt_id']}"))
        method_ok = split.get("method") == FOLD_UNIT_METHOD[ev["fold_unit"]]
        gates.append(_g("G02", "Frozen split plan", "PASS" if split["split_plan_id"] == receipt["o3_split_plan_id"] and
                        split["plan_sha256"] == receipt["o3_split_plan_sha256"] and method_ok and
                        receipt["o3_split_plan_id"] == split_plan_id else "STOP", "input",
                        f"{split['split_plan_id']} hash {str(split['plan_sha256'])[:16]}; method {split.get('method')} "
                        f"for fold unit {ev['fold_unit']}; config plan {split_plan_id}"))
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
        full = [r[0] for r in conn.execute("SELECT model_id FROM prediction_coverage WHERE status = 'FULL' AND model_id IN "
                                           "(%s)" % ",".join("?" * len(feasible)), tuple(feasible))]
        common = {r[0] for r in conn.execute("SELECT observation_id FROM evaluation_population WHERE in_common_cohort = 1")}
        missing = 0
        for m in full:
            ids = {r[0] for r in conn.execute("SELECT observation_id FROM prediction_snapshot WHERE model_id = ?", (m,))}
            missing += len(common - ids)
        gates.append(_g("G05", "Common cohort identical across full-coverage models", "PASS" if
                        missing == 0 and common and full else "STOP", "cohort",
                        f"{len(common)} common observations; {len(full)} full-coverage feasible models; "
                        f"{missing} missing model IDs"))
        # G06: every candidate's coverage matches the snapshot, and a model below the coverage threshold is NOT_COMPARABLE.
        cov_rows = [dict(r) for r in conn.execute(
            "SELECT c.model_id, c.n_predicted, c.coverage, COUNT(p.snapshot_id) AS n_rows, d.role "
            "FROM prediction_coverage c LEFT JOIN prediction_snapshot p ON p.model_id = c.model_id "
            "LEFT JOIN comparison_decisions d ON d.model_id = c.model_id GROUP BY c.model_id")]
        cov_bad = [r["model_id"] for r in cov_rows if r["n_predicted"] != r["n_rows"] or (
            r["coverage"] < float(ev["coverage_threshold"]) and r["role"] != "NOT_COMPARABLE")]
        gates.append(_g("G06", "Coverage recorded for every candidate and matched to the snapshot", "PASS" if not cov_bad
                        else "STOP", "model",
                        f"{len(cov_rows)} candidates; " + ("all coverage rows match the snapshot" if not cov_bad else
                                                           "mismatch or unreported low coverage: " + ", ".join(cov_bad))))
        # G07: identities recorded match a recomputation, and no identical model is ranked.
        order = feasible
        recomputed = _recomputed_identities(conn, order, common)
        stored = {(r["model_a"], r["model_b"]): dict(r) for r in conn.execute("SELECT * FROM model_identities")}
        id_bad = []
        for (a, b), (diff, same) in recomputed.items():
            rec = stored.get((a, b))
            if rec is None or bool(rec["identical"]) != same:
                id_bad.append(f"{a}/{b}")
        ref_bad = []
        for j, m in enumerate(order):
            reg = conn.execute("SELECT identity_status, identical_to FROM candidate_registry WHERE model_id = ?", (m,)).fetchone()
            ref = None
            for cand in order[:j]:
                if recomputed.get((cand, m), (None, False))[1]:
                    ref = cand
            expected = "IDENTICAL_TO" if ref else "DISTINCT"
            if reg is None or reg["identity_status"] != expected or reg["identical_to"] != ref:
                ref_bad.append(m)
            dec = conn.execute("SELECT role, reason FROM comparison_decisions WHERE model_id = ?", (m,)).fetchone()
            if ref and (dec is None or dec["role"] != "NOT_COMPARABLE" or f"identical to {ref}" not in dec["reason"]):
                ref_bad.append(f"{m} ranked despite identity")
        gates.append(_g("G07", "Identities recorded match a recomputation", "PASS" if not id_bad and not ref_bad else "STOP",
                        "model", f"{len(recomputed)} feasible pairs recomputed; "
                                 f"{len([1 for v in recomputed.values() if v[1]])} identical; differences: "
                                 + (", ".join(id_bad + ref_bad) or "none")))
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
        audit_rows = conn.execute("SELECT check_name, status, detail FROM evaluation_audit_log").fetchall()
        audit = {}
        for r in audit_rows:
            audit.setdefault(r["check_name"], []).append(r["status"])
        brier_checks = audit.get("BRIER_NUMERICAL_CROSS_CHECK", [])
        n_checked = len(brier_checks)
        n_feasible_with_rows = len([m for m in feasible if conn.execute(
            "SELECT COUNT(*) FROM prediction_snapshot WHERE model_id = ?", (m,)).fetchone()[0]])
        gates.append(_g("G13", "Metric numerical cross-check on every feasible model", "PASS" if brier_checks and
                        all(s == "PASS" for s in brier_checks) and n_checked == n_feasible_with_rows else "STOP", "metric",
                        f"Brier vector vs independent loop for {n_checked} of {n_feasible_with_rows} feasible models"))
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
        # G16: the selected model is the lowest-Brier distinct full-coverage model; the comparator is the next lowest.
        eligible = {}
        for m in feasible:
            reg = conn.execute("SELECT identity_status FROM candidate_registry WHERE model_id = ?", (m,)).fetchone()
            cov = conn.execute("SELECT status FROM prediction_coverage WHERE model_id = ?", (m,)).fetchone()
            b = conn.execute("SELECT value FROM pooled_metrics WHERE model_id = ? AND weighting = 'INTERVAL' AND "
                             "metric_id = 'BRIER' AND status = 'DEFINED'", (m,)).fetchone()
            if reg and cov and b and reg["identity_status"] == "DISTINCT" and cov["status"] == "FULL":
                eligible[m] = b["value"]
        ranked = sorted(eligible, key=lambda m: (eligible[m], m))
        selected = conn.execute("SELECT model_id FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()
        comp = conn.execute("SELECT model_id FROM comparison_decisions WHERE role = 'COMPARATOR'").fetchone()
        ok16 = bool(ranked) and selected is not None and selected["model_id"] == ranked[0] and (
            len(ranked) < 2 or (comp is not None and comp["model_id"] == ranked[1]))
        gates.append(_g("G16", "Decision rule followed", "PASS" if ok16 else "STOP", "decision",
                        f"selected {selected['model_id'] if selected else 'MISSING'}; lowest distinct Brier "
                        f"{ranked[0] if ranked else 'none'}; comparator {ranked[1] if len(ranked) > 1 else 'none'}"))
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
            p = Path(r["artifact_path"]) if Path(r["artifact_path"]).is_absolute() else PROJECT_ROOT / r["artifact_path"]
            if not p.exists() or sha256_file(p) != r["sha256"]:
                man_bad += 1
        gates.append(_g("G19", "Export hashes", "PASS" if man_bad == 0 else "STOP", "export",
                        f"{man_bad} manifest entries are missing or differ from the file"))
        geometry_ok = (receipt["geometry_status"] == "PROVISIONAL_RELATIVE" and
                       receipt["vertical_basis"] == "RELATIVE_TO_COLLAR")
        gates.append(_g("G20", "Relative geometry only", "PASS" if geometry_ok else "STOP", "geometry",
                        f"{receipt['geometry_status']}; {receipt['vertical_basis']}"))
        absolute_cols, grade_cols = [], []
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
            for col in conn.execute(f"PRAGMA table_info({table})").fetchall():
                if "absolute" in col["name"].lower():
                    absolute_cols.append(f"{table}.{col['name']}")
                if any(word in col["name"].lower() for word in ("grade", "tonnage", "resource", "tgc")):
                    grade_cols.append(f"{table}.{col['name']}")
        gates.append(_g("G21", "No absolute-elevation product", "PASS" if not absolute_cols else "STOP", "geometry",
                        "absolute columns: " + (", ".join(absolute_cols) or "none")))
        gates.append(_g("G22", "No grade, tonnage or resource product", "PASS" if not grade_cols else "STOP", "scope",
                        "grade-like columns: " + (", ".join(grade_cols) or "none")))
        synthetic = conn.execute("SELECT COUNT(*) FROM source_receipts WHERE o3_logical_name <> 'obj3_models'").fetchone()[0]
        gates.append(_g("G23", "No synthetic data", "PASS" if synthetic == 0 else "STOP", "input",
                        f"{synthetic} receipts reference a non-Objective-3 source"))
        cov_n = conn.execute("SELECT COUNT(*) FROM prediction_coverage").fetchone()[0]
        reg_n = conn.execute("SELECT COUNT(*) FROM candidate_registry").fetchone()[0]
        cov_feasible = conn.execute("SELECT COUNT(*) FROM prediction_coverage WHERE model_id IN (%s)" %
                                    ",".join("?" * len(feasible)), tuple(feasible)).fetchone()[0]
        gates.append(_g("G24", "Coverage reported for every candidate", "PASS" if cov_n == reg_n and
                        cov_feasible == len(feasible) else "STOP", "coverage",
                        f"{cov_n} coverage rows for {reg_n} candidates; {cov_feasible} of {len(feasible)} feasible models"))
        selected_row = conn.execute("SELECT * FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()
        gates.append(_g("G25", "Cluster uncertainty for decisions", "PASS" if "HOLE_CLUSTER" in designs.values() and
                        selected_row and selected_row["ci_low"] is not None and selected_row["ci_high"] is not None
                        else "STOP", "uncertainty", "selected decision carries a hole-cluster interval"))
        gates.append(_g("G26", "External validity not claimed", "PASS" if handoff and "not an external" in handoff["caveats"]
                        else "WARN", "decision", "handoff caveat states internal held-out validation"))
        gates.append(_g("G27", "Objective 3 prediction snapshot", "PASS" if snap_sha == receipt["o3_prediction_snapshot_sha256"]
                        else "STOP", "input", f"snapshot {snap_sha[:16]}"))
        claim_ok = handoff is not None and handoff["claim"] == config["claim"].strip()
        gates.append(_g("G28", "Handoff matches the tier configuration", "PASS" if handoff and claim_ok and
                        handoff["tier"] == config["tier"] and handoff["config_version"] == config["config_version"] and
                        handoff["split_plan_id"] == split_plan_id and receipt["tier"] == config["tier"] else "STOP",
                        "decision", f"tier {handoff['tier'] if handoff else 'MISSING'}; split "
                                    f"{handoff['split_plan_id'] if handoff else 'MISSING'} vs config {split_plan_id}; "
                                    f"claim {'matches' if claim_ok else 'differs'}"))
        power = audit.get("POWER_LABELS_MATCH_INTERVALS", [])
        gates.append(_g("G29", "Power labels follow the intervals", "PASS" if power == ["PASS"] else "STOP", "uncertainty",
                        "each configured pair is RESOLVED, UNRESOLVED or IDENTICAL from its interval"
                        if power == ["PASS"] else "power label audit missing or failed"))
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

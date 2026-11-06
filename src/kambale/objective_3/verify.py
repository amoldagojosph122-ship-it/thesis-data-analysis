"""Gate runner for Objective 3 (specification 03).

Each VERIFY run writes one gate_results row per gate. A STOP marks the run STOPPED and the `all` command ends before the
next export. Gates that need a figure or table registry are PASS when the registry is empty (the first verify runs before
the exports); the post-export verify re-checks them against the files on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from kambale.objective_3.config import (O2_DB_PATH, O3_CONFIG_PATH, O3_DB_PATH, O3_FIGURE_DIR,
                                        UPSTREAM_DB_PATH, code_commit, load_config, sha256_bytes, sha256_file,
                                        sha256_text, utc_now)
from kambale.objective_3.db import connect_o3, connect_readonly
from kambale.objective_3.importer import IMPORT_QUERY


def _g(gate_id, name, status, scope, detail):
    return {"gate_id": gate_id, "gate_name": name, "status": status, "scope": scope, "detail": detail}


def _recompute_upstream(upstream) -> tuple[str, str, int]:
    rows = [dict(r) for r in upstream.execute(IMPORT_QUERY)]
    canonical = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    return sha256_text(canonical), sha256_text("\n".join(r["interval_key"] for r in rows)), len(rows)


def _test_ids(conn, split_plan_id, fold_id):
    return {r[0] for r in conn.execute(
        "SELECT observation_id FROM split_membership WHERE split_plan_id = ? AND fold_id = ? AND role = 'TEST'",
        (split_plan_id, fold_id))}


def _files_for(figure_id, stem):
    exts = ("svg", "pdf", "png")
    return [O3_FIGURE_DIR / f"{stem}.{ext}" for ext in exts]


def run(o3_path=None, upstream=UPSTREAM_DB_PATH, o2_path=O2_DB_PATH, config_path=None) -> dict:
    config, config_sha = load_config(config_path or O3_CONFIG_PATH)
    conn = connect_o3(o3_path or O3_DB_PATH)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise RuntimeError("no receipt: run the import first")
        rid = receipt["receipt_id"]
        primary = config["splits"]["primary"]["split_plan_id"]
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, split_plan_id, started_utc, "
            "status, code_commit, note) VALUES ('VERIFY', ?, ?, ?, ?, ?, 'RUNNING', ?, 'gate runner')",
            (config["config_version"], config_sha, rid, primary, utc_now(), code_commit())).lastrowid
        created = utc_now()
        gates = []

        up = connect_readonly(upstream)
        try:
            version = up.execute("SELECT dataset_version_key FROM v_active_version").fetchone()[0]
            rule = up.execute("SELECT status, definition_sha256 FROM graphite_label_rules WHERE rule_id = ?",
                              (receipt["label_rule_id"],)).fetchone()
            absolute = up.execute("SELECT COUNT(*) FROM v_interval_geometry WHERE z_absolute_m IS NOT NULL").fetchone()[0]
            lines = up.execute("SELECT COUNT(*) AS n, SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) AS a "
                               "FROM v_drill_lines").fetchone()
            content_sha, ordered_digest, n_rows = _recompute_upstream(up)
        finally:
            up.close()
        o2 = connect_readonly(o2_path)
        try:
            o2_receipt = o2.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
            o2_handoff = o2.execute("SELECT * FROM continuity_handoff_decisions WHERE receipt_id = ? "
                                    "ORDER BY handoff_id DESC LIMIT 1", (o2_receipt["receipt_id"],)).fetchone()
        finally:
            o2.close()

        gates.append(_g("G01", "Receipt match", "PASS" if (content_sha == receipt["content_sha256"] and
                       version == receipt["upstream_dataset_version_key"] and n_rows == receipt["row_count"])
                       else "STOP", "input",
                       f"recomputed content {content_sha[:12]} vs receipt {receipt['content_sha256'][:12]}; "
                       f"rows {n_rows} vs receipt {receipt['row_count']}; version {version[:12]}"))
        gates.append(_g("G02", "Approved label rule", "PASS" if rule and rule["status"] == "APPROVED" and
                       rule["definition_sha256"] == receipt["label_rule_definition_sha256"] else "STOP", "input",
                       f"{receipt['label_rule_id']} {receipt['label_rule_status']}; definition hash matches: "
                       f"{bool(rule and rule['definition_sha256'] == receipt['label_rule_definition_sha256'])}"))
        gates.append(_g("G03", "Relative geometry only", "PASS" if absolute == 0 and
                       receipt["geometry_status"] == "PROVISIONAL_RELATIVE" and receipt["vertical_basis"] ==
                       "RELATIVE_TO_COLLAR" else "STOP", "input",
                       f"z_absolute_m non-null upstream rows = {absolute}; vertical basis {receipt['vertical_basis']}"))
        gates.append(_g("G04", "Coordinate pair, datum and lines", "PASS" if
                       receipt["coordinate_pair_status"] == "APPROVED" and receipt["crs_datum_status"] == "VERIFIED"
                       and receipt["drill_line_status"] == "APPROVED" and lines["n"] == lines["a"] and lines["n"] > 0
                       else "STOP", "input",
                       f"pair {receipt['coordinate_pair_status']}; datum {receipt['crs_datum_status']}; "
                       f"{lines['a']} of {lines['n']} lines approved"))
        primary_row = conn.execute("SELECT * FROM spatial_split_plans WHERE split_plan_id = ?", (primary,)).fetchone()
        plans = conn.execute("SELECT split_plan_id, method, primary_plan, n_folds FROM spatial_split_plans").fetchall()
        primary_ok = primary_row is not None and primary_row["primary_plan"] == 1 and \
            primary_row["method"] == "LEAVE_ONE_DRILL_LINE_OUT"
        n_primary = sum(1 for p in plans if p["primary_plan"] == 1)
        gates.append(_g("G21", "Primary split plan is line-blocked", "PASS" if primary_ok and n_primary == 1 else "STOP",
                       "split", f"{n_primary} primary plans; {primary} uses "
                                 f"{primary_row['method'] if primary_row else 'MISSING'}"))
        duplicate = conn.execute(
            "SELECT COUNT(*) FROM (SELECT split_plan_id, fold_id, observation_id, COUNT(*) c FROM split_membership "
            "GROUP BY split_plan_id, fold_id, observation_id HAVING c > 1)").fetchone()[0]
        missing = conn.execute(
            "SELECT COUNT(*) FROM split_membership WHERE split_plan_id = ?", (primary,)).fetchone()[0]
        expected = conn.execute("SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = ? AND in_binary_target = 1",
                                (rid,)).fetchone()[0] * max(1, int(primary_row["n_folds"]) if primary_row else 1)
        disjoint_bad = 0
        for p in plans:
            for f in range(1, int(p["n_folds"]) + 1):
                tr = {r[0] for r in conn.execute(
                    "SELECT observation_id FROM split_membership WHERE split_plan_id = ? AND fold_id = ? AND role = 'TRAIN'",
                    (p["split_plan_id"], f))}
                te = _test_ids(conn, p["split_plan_id"], f)
                disjoint_bad += len(tr & te)
        gates.append(_g("G05", "Split integrity", "PASS" if disjoint_bad == 0 and duplicate == 0 and missing == expected
                       else "STOP", "split",
                       f"{missing} of {expected} expected membership rows; {duplicate} duplicates; "
                       f"{disjoint_bad} train/test overlaps"))
        audits = conn.execute("SELECT status, COUNT(*) n FROM split_audit WHERE split_plan_id = ? GROUP BY status",
                              (primary,)).fetchall()
        warn_audit = conn.execute("SELECT COUNT(*) FROM split_audit WHERE split_plan_id = ? AND status <> 'PASS'",
                                  (primary,)).fetchone()[0]
        gates.append(_g("G06", "Fold class and spatial support", "WARN" if warn_audit else "PASS", "split",
                       ", ".join(f"{r['status']} {r['n']}" for r in audits) + f" for {primary}"))
        deployed = conn.execute("SELECT name, leakage_designation, available_at_prediction FROM feature_registry "
                                "WHERE name IN ('easting_m','northing_m','z_relative_m')").fetchall()
        leakage_bad = sum(1 for r in deployed if r["leakage_designation"] != "SAFE" or r["available_at_prediction"] != 1)
        forbidden_used = conn.execute(
            "SELECT COUNT(*) FROM feature_registry WHERE leakage_designation IN ('TARGET_DERIVED','FORBIDDEN') "
            "AND name IN ('easting_m','northing_m','z_relative_m')").fetchone()[0]
        gates.append(_g("G07", "Predictor leakage", "PASS" if leakage_bad == 0 and forbidden_used == 0 else "STOP",
                       "model", f"{leakage_bad} deployed predictors are not SAFE/available; "
                                f"{forbidden_used} forbidden features are deployed"))
        targets = conn.execute("SELECT COUNT(DISTINCT target_id) n, SUM(binary_n) b FROM target_registries "
                               "WHERE receipt_id = ?", (rid,)).fetchone()
        observed_binary = conn.execute("SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = ? "
                                       "AND in_binary_target = 1", (rid,)).fetchone()[0]
        gates.append(_g("G08", "Target consistency", "PASS" if targets["n"] == 1 and targets["b"] == observed_binary
                       else "STOP", "target",
                       f"{targets['n']} target registries; registered binary {targets['b']} vs observations "
                       f"{observed_binary}"))
        runs = conn.execute("SELECT * FROM training_runs WHERE split_plan_id = ?", (primary,)).fetchall()
        incomplete = 0
        for r in runs:
            test_ids = _test_ids(conn, primary, r["fold_id"])
            pred = {x[0] for x in conn.execute(
                "SELECT observation_id FROM predictions_oof WHERE training_run_id = ?", (r["training_run_id"],))}
            fail = {x[0] for x in conn.execute(
                "SELECT observation_id FROM prediction_failures WHERE training_run_id = ?", (r["training_run_id"],))}
            incomplete += len(test_ids - pred - fail)
        gates.append(_g("G09", "OOF completeness", "PASS" if incomplete == 0 and runs else "STOP", "prediction",
                       f"{incomplete} test observations lack a prediction or a failure record across {len(runs)} runs"))
        clip = conn.execute(
            "SELECT family_id, AVG(clipped_calibrated) f, COUNT(*) n FROM predictions_oof WHERE split_plan_id = ? "
            "GROUP BY family_id", (primary,)).fetchall()
        max_clip = float(config["gates"]["maximum_clipped_fraction"])
        over = [r for r in clip if r["f"] is not None and r["f"] > max_clip]
        out_of_bounds = conn.execute("SELECT COUNT(*) FROM predictions_oof WHERE p_raw < 0 OR p_raw > 1 OR "
                                     "p_calibrated < 0 OR p_calibrated > 1").fetchone()[0]
        gates.append(_g("G10", "Probability bounds and clipping", "WARN" if over else ("STOP" if out_of_bounds else "PASS"),
                       "prediction", f"{out_of_bounds} out-of-bounds probabilities; " +
                       (", ".join(f"{r['family_id']} clipped {r['f']:.3f}" for r in clip) or "no predictions")))
        bad_var = conn.execute(
            "SELECT COUNT(*) FROM variogram_training_fits v JOIN training_runs t ON t.training_run_id = v.training_run_id "
            "WHERE t.split_plan_id = ? AND (t.fold_id <> v.fold_id OR t.family_id <> v.family_id)", (primary,)).fetchone()[0]
        test_in_manifest = conn.execute(
            "SELECT COUNT(*) FROM training_sample_manifest m JOIN training_runs t ON t.training_run_id = m.training_run_id "
            "JOIN split_membership s ON s.split_plan_id = t.split_plan_id AND s.fold_id = t.fold_id "
            "AND s.observation_id = m.observation_id AND s.role = 'TEST' WHERE t.split_plan_id = ?",
            (primary,)).fetchone()[0]
        gates.append(_g("G11", "Training-only indicator variograms", "PASS" if bad_var == 0 and test_in_manifest == 0
                       else "STOP", "variogram",
                       f"{bad_var} variogram rows reference another fold or family; {test_in_manifest} test rows are in "
                       "a training manifest"))
        bad_res = conn.execute(
            "SELECT COUNT(*) FROM hybrid_residual_variogram v JOIN training_runs t ON t.training_run_id = v.training_run_id "
            "WHERE t.split_plan_id = ? AND (t.fold_id <> v.fold_id OR t.family_id <> 'M3_HYBRID')", (primary,)).fetchone()[0]
        gates.append(_g("G12", "Training-only residual variograms", "PASS" if bad_res == 0 else "STOP", "variogram",
                       f"{bad_res} residual variogram rows reference another fold or family"))
        bad_cal = conn.execute(
            "SELECT COUNT(*) FROM calibration_fits c JOIN training_runs t ON t.training_run_id = c.training_run_id "
            "WHERE t.split_plan_id = ? AND (c.n_inner > t.training_n OR "
            "(t.family_id NOT IN ('M2_RF','M2_HGB') AND c.method <> 'NONE'))",
            (primary,)).fetchone()[0]
        gates.append(_g("G13", "Calibration uses inner data only", "PASS" if bad_cal == 0 else "STOP", "calibration",
                       f"{bad_cal} calibration rows exceed the training fold or belong to an uncalibrated family"))
        final_run = conn.execute("SELECT COUNT(*) FROM final_refits WHERE status = 'RUN'").fetchone()[0]
        gates.append(_g("G14", "No full-data parameters for test folds", "PASS" if final_run == 0 else "STOP", "model",
                       f"{final_run} final full-data refits are marked RUN before Objective 4 selection"))
        artifact_bad = 0
        for r in conn.execute("SELECT artifact_path, artifact_sha256 FROM model_artifacts").fetchall():
            from pathlib import Path
            p = Path(r["artifact_path"])
            if not p.exists() or sha256_file(p) != r["artifact_sha256"]:
                artifact_bad += 1
        gates.append(_g("G15", "Model artifact hashes", "PASS" if artifact_bad == 0 else "STOP", "model",
                       f"{artifact_bad} artifact files are missing or differ from their hash"))
        fig_bad = 0
        for r in conn.execute("SELECT figure_id, status FROM figure_registry").fetchall():
            n = conn.execute("SELECT COUNT(*) FROM figure_sql_registry WHERE figure_id = ?", (r["figure_id"],)).fetchone()[0]
            if r["status"] == "GENERATED" and n == 0:
                fig_bad += 1
            for q in conn.execute("SELECT sql_path, sql_sha256 FROM figure_sql_registry WHERE figure_id = ?",
                                  (r["figure_id"],)).fetchall():
                from pathlib import Path
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
                from pathlib import Path
                p = Path(q["sql_path"])
                if not p.exists() or sha256_bytes(p.read_bytes()) != q["sql_sha256"]:
                    tab_bad += 1
        gates.append(_g("G16", "Figure and table query provenance", "PASS" if fig_bad == 0 and tab_bad == 0 else "STOP",
                       "export", f"{fig_bad} figure and {tab_bad} table registry entries are unregistered or changed"))
        manifest_bad = 0
        for r in conn.execute("SELECT artifact_path, sha256 FROM export_manifests").fetchall():
            from pathlib import Path
            p = Path(r["artifact_path"])
            if not p.exists() or sha256_file(p) != r["sha256"]:
                manifest_bad += 1
        gates.append(_g("G17", "Export hashes", "PASS" if manifest_bad == 0 else "STOP", "export",
                       f"{manifest_bad} manifest entries are missing or differ from the file on disk"))
        bad_inner = conn.execute(
            "SELECT COUNT(*) FROM training_runs WHERE split_plan_id = ? AND status = 'COMPLETED' "
            "AND family_id IN ('BASE_PREVALENCE','BASE_LOGISTIC','M2_RF','M2_HGB') AND inner_cv_score IS NULL",
            (primary,)).fetchone()[0]
        gates.append(_g("G18", "Tuning uses inner folds only", "PASS" if bad_inner == 0 else "STOP", "model",
                       f"{bad_inner} completed candidates have no inner-CV score"))
        m1_bad = conn.execute(
            "SELECT COUNT(*) FROM training_runs t WHERE t.split_plan_id = ? AND t.family_id = 'M1_IK' AND "
            "t.status = 'NOT_ESTIMABLE' AND EXISTS (SELECT 1 FROM predictions_oof p WHERE p.training_run_id = t.training_run_id)",
            (primary,)).fetchone()[0]
        m1_bad += conn.execute(
            "SELECT COUNT(*) FROM variogram_training_fits v WHERE v.family_id = 'M1_IK' AND v.fit_status <> 'FITTED' "
            "AND NOT (v.nugget IS NULL AND v.structured_sill IS NULL AND v.range_m IS NULL)").fetchone()[0]
        gates.append(_g("G19", "M1 status honesty", "PASS" if m1_bad == 0 else "STOP", "model",
                       f"{m1_bad} M1 rows claim a prediction or parameters without an identified variogram"))
        m3_bad = conn.execute(
            "SELECT COUNT(*) FROM training_runs t WHERE t.split_plan_id = ? AND t.family_id = 'M3_HYBRID' AND "
            "t.status = 'FALLBACK' AND NOT EXISTS (SELECT 1 FROM hybrid_residual_variogram v WHERE "
            "v.training_run_id = t.training_run_id AND v.fallback_status = 'FALLBACK_ML_ONLY')", (primary,)).fetchone()[0]
        m3_bad += conn.execute(
            "SELECT COUNT(*) FROM training_runs t WHERE t.split_plan_id = ? AND t.family_id = 'M3_HYBRID' AND "
            "t.status = 'COMPLETED' AND EXISTS (SELECT 1 FROM hybrid_residual_variogram v WHERE "
            "v.training_run_id = t.training_run_id AND v.fallback_status <> 'HYBRID_USED')", (primary,)).fetchone()[0]
        gates.append(_g("G20", "M3 fallback is labelled", "PASS" if m3_bad == 0 else "STOP", "model",
                       f"{m3_bad} hybrid runs carry an inconsistent fallback label"))
        bad_status = conn.execute(
            "SELECT COUNT(*) FROM predictions_oof WHERE split_plan_id = ? AND (geometry_status <> 'PROVISIONAL_RELATIVE' "
            "OR label_rule_id <> ?)", (primary, receipt["label_rule_id"])).fetchone()[0]
        gates.append(_g("G22", "Geometry and label status on predictions", "PASS" if bad_status == 0 else "STOP",
                       "prediction", f"{bad_status} predictions carry a different geometry or label status"))
        absolute_cols = []
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
            for col in conn.execute(f"PRAGMA table_info({table})").fetchall():
                if "absolute" in col["name"].lower() and table not in ("geometry_versions",):
                    absolute_cols.append(f"{table}.{col['name']}")
        gates.append(_g("G23", "No absolute-elevation product", "PASS" if not absolute_cols else "STOP", "geometry",
                       "absolute-elevation columns: " + (", ".join(absolute_cols) or "none")))
        synthetic = conn.execute("SELECT COUNT(*) FROM source_receipts WHERE upstream_logical_name <> 'obj1_master' "
                                 "OR o2_logical_name <> 'obj2_spatial'").fetchone()[0]
        gates.append(_g("G24", "No synthetic data in exports", "PASS" if synthetic == 0 else "STOP", "export",
                       f"{synthetic} receipts reference a non-Kambale source"))
        handoff_ok = (o2_handoff is not None and o2_receipt is not None
                      and o2_receipt["content_sha256"] == receipt["o2_content_sha256"]
                      and o2_receipt["receipt_id"] == receipt["o2_receipt_id"]
                      and o2_handoff["handoff_id"] == receipt["o2_handoff_id"]
                      and o2_handoff["decision_status"] == "NOT_IDENTIFIABLE"
                      and o2_handoff["candidate_family"] == "NONE")
        gates.append(_g("G25", "Objective 2 handoff recorded", "PASS" if handoff_ok else "STOP", "input",
                       f"handoff {o2_handoff['decision_status'] if o2_handoff else 'MISSING'}; candidate family "
                       f"{o2_handoff['candidate_family'] if o2_handoff else 'MISSING'}"))
        bad_members = conn.execute(
            "SELECT COUNT(*) FROM predictions_oof p LEFT JOIN split_membership s ON s.split_plan_id = p.split_plan_id "
            "AND s.fold_id = p.fold_id AND s.observation_id = p.observation_id AND s.role = 'TEST' "
            "WHERE p.split_plan_id = ? AND s.observation_id IS NULL", (primary,)).fetchone()[0]
        gates.append(_g("G26", "Predictions are held-out members", "PASS" if bad_members == 0 else "STOP", "prediction",
                       f"{bad_members} predictions are not test members of their fold"))
        audit_n = conn.execute("SELECT COUNT(*) FROM leakage_audit_log").fetchone()[0]
        audit_fail = conn.execute("SELECT COUNT(*) FROM leakage_audit_log WHERE status = 'FAIL'").fetchone()[0]
        gates.append(_g("G27", "Leakage audit log", "PASS" if audit_fail == 0 else "STOP", "model",
                       f"{audit_n} audit rows; {audit_fail} failed"))

        stopped = any(g["status"] == "STOP" for g in gates)
        conn.execute("DELETE FROM gate_results WHERE run_id = ?", (run_id,))
        conn.executemany(
            "INSERT INTO gate_results (run_id, gate_id, gate_name, status, scope, detail, created_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(run_id, g["gate_id"], g["gate_name"], g["status"], g["scope"], g["detail"], created) for g in gates])
        conn.execute("UPDATE stage_runs SET status = ?, finished_utc = ? WHERE run_id = ?",
                     ("STOPPED" if stopped else "COMPLETED", utc_now(), run_id))
        return {"run_id": run_id, "stopped": stopped, "gates": gates}
    finally:
        conn.close()

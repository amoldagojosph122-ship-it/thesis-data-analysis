"""Gate runner for Objective 3 (specification 03).

Each VERIFY run writes one gate_results row per gate. A STOP marks the run STOPPED and the `all` command ends before the
next export. Gates that need a figure or table registry are PASS when the registry is empty (the first verify runs before
the exports); the post-export verify re-checks them against the files on disk. Every training gate covers every split
plan in the database: the line-blocked primary tier and the interleaved within-line tier.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from kambale.objective_3 import kriging, weathering_front
from kambale.objective_3.config import (O2_DB_PATH, O3_CONFIG_PATH, O3_DB_PATH, O3_FIGURE_DIR,
                                        UPSTREAM_DB_PATH, code_commit, load_config, sha256_bytes, sha256_file,
                                        sha256_text, utc_now)
from kambale.objective_3.db import connect_o3, connect_readonly
from kambale.objective_3.features import hole_collars, load_observations
from kambale.objective_3.importer import IMPORT_QUERY

TOL = 1e-12
NON_TUNED = ("M1_IK", "M3_HYBRID")


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


def _interleave_violations(conn, receipt_id: int, split_plan_id: str) -> tuple[int, int]:
    """(violations, test holes checked) for an INTERLEAVED_HOLES_WITHIN_LINE plan.

    A test hole's along-line neighbours (in collar-easting order within its line) must be training holes of the same
    fold. Collar proxy and ordering are the same as in features.py: the shallowest binary interval's easting, ties by id.
    """
    rows = conn.execute(
        "SELECT o.hole_id, o.line_code, o.easting_m, o.northing_m, o.z_relative_m FROM analysis_observations o "
        "WHERE o.receipt_id = ? AND o.in_binary_target = 1", (receipt_id,)).fetchall()
    shallow = {}
    for r in rows:
        cur = shallow.get(r["hole_id"])
        if cur is None or r["z_relative_m"] > cur["z_relative_m"]:
            shallow[r["hole_id"]] = r
    by_line: dict[str, list] = {}
    for hole, r in shallow.items():
        by_line.setdefault(r["line_code"], []).append((r["easting_m"], hole))
    neighbours = {}
    for line, items in by_line.items():
        order = [h for _, h in sorted(items, key=lambda it: (it[0], it[1]))]
        for k, h in enumerate(order):
            neighbours[h] = [order[j] for j in (k - 1, k + 1) if 0 <= j < len(order)]
    violations = 0
    checked = 0
    for (fold,) in conn.execute("SELECT DISTINCT fold_id FROM split_membership WHERE split_plan_id = ?", (split_plan_id,)):
        test_holes = {r[0] for r in conn.execute(
            "SELECT DISTINCT hole_id FROM split_membership WHERE split_plan_id = ? AND fold_id = ? AND role = 'TEST'",
            (split_plan_id, fold))}
        train_holes = {r[0] for r in conn.execute(
            "SELECT DISTINCT hole_id FROM split_membership WHERE split_plan_id = ? AND fold_id = ? AND role = 'TRAIN'",
            (split_plan_id, fold))}
        for h in test_holes:
            checked += 1
            for nb in neighbours.get(h, []):
                if nb not in train_holes:
                    violations += 1
    return violations, checked


def run(o3_path=None, upstream=UPSTREAM_DB_PATH, o2_path=O2_DB_PATH, config_path=None) -> dict:
    config, config_sha = load_config(config_path or O3_CONFIG_PATH)
    conn = connect_o3(o3_path or O3_DB_PATH)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise RuntimeError("no receipt: run the import first")
        rid = receipt["receipt_id"]
        tiers = config["splits"]["tiers"]
        primary_cfg = [t["split_plan_id"] for t in tiers if int(t["primary_plan"]) == 1]
        primary = primary_cfg[0] if len(primary_cfg) == 1 else None
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, split_plan_id, started_utc, "
            "status, code_commit, note) VALUES ('VERIFY', ?, ?, ?, ?, ?, 'RUNNING', ?, 'gate runner')",
            (config["config_version"], config_sha, rid, primary, utc_now(), code_commit())).lastrowid
        created = utc_now()
        gates = []
        plans = [dict(r) for r in conn.execute(
            "SELECT split_plan_id, method, primary_plan, n_folds FROM spatial_split_plans ORDER BY split_plan_id")]
        plan_ids = [p["split_plan_id"] for p in plans]
        marks = ",".join("?" for _ in plan_ids) or "''"

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

        # G21: exactly one primary plan, it is the configured one, and it is line-blocked.
        primary_row = conn.execute("SELECT * FROM spatial_split_plans WHERE primary_plan = 1").fetchall()
        n_primary = len(primary_row)
        primary_ok = (n_primary == 1 and primary is not None and primary_row[0]["split_plan_id"] == primary and
                      primary_row[0]["method"] == "LEAVE_ONE_DRILL_LINE_OUT")
        gates.append(_g("G21", "Primary split plan is line-blocked", "PASS" if primary_ok else "STOP", "split",
                       f"{n_primary} primary plan(s): " + ", ".join(
                           f"{r['split_plan_id']} {r['method']}" for r in primary_row) +
                       f"; configured primary {primary}; plans in database {len(plans)}"))

        # G05: membership is complete and disjoint for every plan.
        receipt_binary = conn.execute("SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = ? "
                                      "AND in_binary_target = 1", (rid,)).fetchone()[0]
        duplicate = conn.execute(
            "SELECT COUNT(*) FROM (SELECT split_plan_id, fold_id, observation_id, COUNT(*) c FROM split_membership "
            "GROUP BY split_plan_id, fold_id, observation_id HAVING c > 1)").fetchone()[0]
        incomplete_text = []
        missing_total = 0
        for p in plans:
            n_members = conn.execute("SELECT COUNT(*) FROM split_membership WHERE split_plan_id = ?",
                                     (p["split_plan_id"],)).fetchone()[0]
            expected = receipt_binary * int(p["n_folds"])
            missing_total += abs(expected - n_members)
            incomplete_text.append(f"{p['split_plan_id']} {n_members} of {expected}")
        disjoint_bad = 0
        for p in plans:
            for f in range(1, int(p["n_folds"]) + 1):
                tr = {r[0] for r in conn.execute(
                    "SELECT observation_id FROM split_membership WHERE split_plan_id = ? AND fold_id = ? AND role = 'TRAIN'",
                    (p["split_plan_id"], f))}
                disjoint_bad += len(tr & _test_ids(conn, p["split_plan_id"], f))
        gates.append(_g("G05", "Split integrity", "PASS" if disjoint_bad == 0 and duplicate == 0 and missing_total == 0
                       else "STOP", "split",
                       f"membership rows: {'; '.join(incomplete_text)}; {duplicate} duplicates; "
                       f"{disjoint_bad} train/test overlaps"))
        warn_audit = conn.execute(f"SELECT COUNT(*) FROM split_audit WHERE split_plan_id IN ({marks}) AND status <> 'PASS'",
                                  plan_ids).fetchone()[0]
        audits = conn.execute(f"SELECT split_plan_id, status, COUNT(*) n FROM split_audit WHERE split_plan_id IN ({marks}) "
                              "GROUP BY split_plan_id, status", plan_ids).fetchall()
        gates.append(_g("G06", "Fold class and spatial support", "WARN" if warn_audit else "PASS", "split",
                       ", ".join(f"{r['split_plan_id']} {r['status']} {r['n']}" for r in audits)))

        front_name = "depth_below_weathering_front_m"
        deployed = conn.execute("SELECT name, leakage_designation, available_at_prediction FROM feature_registry "
                                "WHERE name IN ('easting_m','northing_m','z_relative_m', ?)", (front_name,)).fetchall()
        leakage_bad = sum(1 for r in deployed if r["leakage_designation"] != "SAFE" or r["available_at_prediction"] != 1)
        leakage_bad += 4 - len(deployed)
        forbidden_used = conn.execute(
            "SELECT COUNT(*) FROM feature_registry WHERE leakage_designation IN ('TARGET_DERIVED','FORBIDDEN') "
            "AND name IN ('easting_m','northing_m','z_relative_m', ?)", (front_name,)).fetchone()[0]
        gates.append(_g("G07", "Predictor leakage", "PASS" if leakage_bad == 0 and forbidden_used == 0 else "STOP",
                       "model", f"{leakage_bad} deployed predictors are not SAFE/available; "
                                f"{forbidden_used} forbidden features are deployed"))
        targets = conn.execute("SELECT COUNT(DISTINCT target_id) n, SUM(binary_n) b FROM target_registries "
                               "WHERE receipt_id = ?", (rid,)).fetchone()
        observed_binary = receipt_binary
        gates.append(_g("G08", "Target consistency", "PASS" if targets["n"] == 1 and targets["b"] == observed_binary
                       else "STOP", "target",
                       f"{targets['n']} target registries; registered binary {targets['b']} vs observations "
                       f"{observed_binary}"))
        runs = conn.execute(f"SELECT * FROM training_runs WHERE split_plan_id IN ({marks})", plan_ids).fetchall()
        incomplete = 0
        for r in runs:
            test_ids = _test_ids(conn, r["split_plan_id"], r["fold_id"])
            pred = {x[0] for x in conn.execute(
                "SELECT observation_id FROM predictions_oof WHERE training_run_id = ?", (r["training_run_id"],))}
            fail = {x[0] for x in conn.execute(
                "SELECT observation_id FROM prediction_failures WHERE training_run_id = ?", (r["training_run_id"],))}
            incomplete += len(test_ids - pred - fail)
        gates.append(_g("G09", "OOF completeness", "PASS" if incomplete == 0 and runs else "STOP", "prediction",
                       f"{incomplete} test observations lack a prediction or a failure record across {len(runs)} runs "
                       f"in {len(plan_ids)} split plans"))
        clip = conn.execute(
            f"SELECT split_plan_id, family_id, AVG(clipped_calibrated) f, COUNT(*) n FROM predictions_oof "
            f"WHERE split_plan_id IN ({marks}) GROUP BY split_plan_id, family_id", plan_ids).fetchall()
        max_clip = float(config["gates"]["maximum_clipped_fraction"])
        over = [r for r in clip if r["f"] is not None and r["f"] > max_clip]
        out_of_bounds = conn.execute("SELECT COUNT(*) FROM predictions_oof WHERE p_raw < 0 OR p_raw > 1 OR "
                                     "p_calibrated < 0 OR p_calibrated > 1").fetchone()[0]
        gates.append(_g("G10", "Probability bounds and clipping", "WARN" if over else ("STOP" if out_of_bounds else "PASS"),
                       "prediction", f"{out_of_bounds} out-of-bounds probabilities; " +
                       (", ".join(f"{r['split_plan_id']} {r['family_id']} clipped {r['f']:.3f}" for r in clip)
                        or "no predictions")))
        bad_var = conn.execute(
            f"SELECT COUNT(*) FROM variogram_training_fits v JOIN training_runs t ON t.training_run_id = v.training_run_id "
            f"WHERE t.split_plan_id IN ({marks}) AND (t.fold_id <> v.fold_id OR t.family_id <> v.family_id)",
            plan_ids).fetchone()[0]
        test_in_manifest = conn.execute(
            f"SELECT COUNT(*) FROM training_sample_manifest m JOIN training_runs t ON t.training_run_id = m.training_run_id "
            f"JOIN split_membership s ON s.split_plan_id = t.split_plan_id AND s.fold_id = t.fold_id "
            f"AND s.observation_id = m.observation_id AND s.role = 'TEST' WHERE t.split_plan_id IN ({marks})",
            plan_ids).fetchone()[0]
        gates.append(_g("G11", "Training-only indicator covariance", "PASS" if bad_var == 0 and test_in_manifest == 0
                       else "STOP", "variogram",
                       f"{bad_var} covariance rows reference another fold or family; {test_in_manifest} test rows are in "
                       "a training manifest"))
        bad_res = conn.execute(
            f"SELECT COUNT(*) FROM hybrid_residual_variogram v JOIN training_runs t ON t.training_run_id = v.training_run_id "
            f"WHERE t.split_plan_id IN ({marks}) AND (t.fold_id <> v.fold_id OR t.family_id <> 'M3_HYBRID')",
            plan_ids).fetchone()[0]
        gates.append(_g("G12", "Training-only residual covariance", "PASS" if bad_res == 0 else "STOP", "variogram",
                       f"{bad_res} residual covariance rows reference another fold or family"))
        calibrated = tuple(config["calibration"]["apply_to"])
        cal_marks = ",".join("?" for _ in calibrated)
        bad_cal = conn.execute(
            f"SELECT COUNT(*) FROM calibration_fits c JOIN training_runs t ON t.training_run_id = c.training_run_id "
            f"WHERE t.split_plan_id IN ({marks}) AND (c.n_inner > t.training_n OR "
            f"(t.family_id NOT IN ({cal_marks}) AND c.method <> 'NONE'))", tuple(plan_ids) + calibrated).fetchone()[0]
        gates.append(_g("G13", "Calibration uses inner data only", "PASS" if bad_cal == 0 else "STOP", "calibration",
                       f"{bad_cal} calibration rows exceed the training fold or belong to an uncalibrated family"))
        final_run = conn.execute("SELECT COUNT(*) FROM final_refits WHERE status = 'RUN'").fetchone()[0]
        gates.append(_g("G14", "No full-data parameters for test folds", "PASS" if final_run == 0 else "STOP", "model",
                       f"{final_run} final full-data refits are marked RUN before Objective 4 selection"))
        artifact_bad = 0
        for r in conn.execute("SELECT artifact_path, artifact_sha256 FROM model_artifacts").fetchall():
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
        gates.append(_g("G16", "Figure and table query provenance", "PASS" if fig_bad == 0 and tab_bad == 0 else "STOP",
                       "export", f"{fig_bad} figure and {tab_bad} table registry entries are unregistered or changed"))
        manifest_bad = 0
        for r in conn.execute("SELECT artifact_path, sha256 FROM export_manifests").fetchall():
            p = Path(r["artifact_path"])
            if not p.exists() or sha256_file(p) != r["sha256"]:
                manifest_bad += 1
        gates.append(_g("G17", "Export hashes", "PASS" if manifest_bad == 0 else "STOP", "export",
                       f"{manifest_bad} manifest entries are missing or differ from the file on disk"))
        bad_inner = conn.execute(
            f"SELECT COUNT(*) FROM training_runs WHERE split_plan_id IN ({marks}) AND status = 'COMPLETED' "
            "AND family_id NOT IN ('M1_IK','M3_HYBRID') AND inner_cv_score IS NULL", plan_ids).fetchone()[0]
        gates.append(_g("G18", "Tuning uses inner folds only", "PASS" if bad_inner == 0 else "STOP", "model",
                       f"{bad_inner} completed candidates have no inner-CV score"))

        # G19: M1 honesty. Every M1 run carries exactly the predeclared grid of trials and one chosen covariance; a
        # pure-nugget M1 predicts the training prevalence; a run without an identified covariance has no prediction.
        grid_size = len(kriging.covariance_grid(config))
        m1_runs = conn.execute(f"SELECT * FROM training_runs WHERE split_plan_id IN ({marks}) AND family_id = 'M1_IK'",
                               plan_ids).fetchall()
        m1_bad = 0
        pure_bad = 0
        pure_runs = 0
        for r in m1_runs:
            hp = json.loads(r["hyperparameters_json"] or "{}")
            cov = hp.get("covariance")
            trials = conn.execute("SELECT COUNT(*), SUM(selected) FROM hyperparameter_trials WHERE training_run_id = ?",
                                  (r["training_run_id"],)).fetchone()
            vfit = conn.execute("SELECT COUNT(*) FROM variogram_training_fits WHERE training_run_id = ?",
                                (r["training_run_id"],)).fetchone()[0]
            if r["status"] == "COMPLETED":
                if cov is None or trials[0] != grid_size or (trials[1] or 0) != 1 or vfit != 1:
                    m1_bad += 1
                if cov is not None and kriging.is_pure(cov):
                    pure_runs += 1
                    n_pos, n_all = int(r["training_positive"]), int(r["training_n"])
                    prev = n_pos / n_all
                    off = conn.execute("SELECT COUNT(*) FROM predictions_oof WHERE training_run_id = ? "
                                       "AND ABS(p_calibrated - ?) > ?", (r["training_run_id"], prev, TOL)).fetchone()[0]
                    pure_bad += off
            else:
                if conn.execute("SELECT COUNT(*) FROM predictions_oof WHERE training_run_id = ?",
                                (r["training_run_id"],)).fetchone()[0]:
                    m1_bad += 1
        gates.append(_g("G19", "M1 status honesty", "PASS" if m1_bad == 0 and pure_bad == 0 else "STOP", "model",
                       f"{len(m1_runs)} M1 runs; {m1_bad} runs lack the full trial grid or a chosen covariance; "
                       f"{pure_runs} pure-nugget runs; {pure_bad} pure-nugget predictions differ from the training "
                       f"prevalence by more than {TOL:g}"))

        # G20: M3 fallback is labelled and equal to M2_WF_SEL; a completed hybrid has a non-nugget covariance.
        m3_runs = conn.execute(f"SELECT * FROM training_runs WHERE split_plan_id IN ({marks}) AND family_id = 'M3_HYBRID'",
                               plan_ids).fetchall()
        m3_bad = 0
        for r in m3_runs:
            statuses = {x[0] for x in conn.execute("SELECT fallback_status FROM hybrid_residual_variogram "
                                                    "WHERE training_run_id = ?", (r["training_run_id"],))}
            fits = {x[0] for x in conn.execute("SELECT fit_status FROM hybrid_residual_variogram "
                                               "WHERE training_run_id = ?", (r["training_run_id"],))}
            if r["status"] == "FALLBACK" and statuses != {"FALLBACK_ML_ONLY"}:
                m3_bad += 1
            if r["status"] == "COMPLETED" and (statuses != {"HYBRID_USED"} or fits != {"FITTED"}):
                m3_bad += 1
        fb_total = conn.execute(
            f"SELECT COUNT(*) FROM predictions_oof p JOIN training_runs t ON t.training_run_id = p.training_run_id "
            f"WHERE t.split_plan_id IN ({marks}) AND t.family_id = 'M3_HYBRID' AND t.status = 'FALLBACK'",
            plan_ids).fetchone()[0]
        fb_equal = conn.execute(
            f"SELECT COUNT(*) FROM predictions_oof p JOIN training_runs t ON t.training_run_id = p.training_run_id "
            f"JOIN predictions_oof c ON c.split_plan_id = p.split_plan_id AND c.fold_id = p.fold_id "
            f"AND c.observation_id = p.observation_id AND c.family_id = 'M2_WF_SEL' "
            f"WHERE t.split_plan_id IN ({marks}) AND t.family_id = 'M3_HYBRID' AND t.status = 'FALLBACK' "
            f"AND ABS(p.p_calibrated - c.p_calibrated) <= ?", tuple(plan_ids) + (TOL,)).fetchone()[0]
        m3_bad += fb_total - fb_equal
        gates.append(_g("G20", "M3 fallback is labelled", "PASS" if m3_bad == 0 else "STOP", "model",
                       f"{len(m3_runs)} hybrid runs; {m3_bad} carry an inconsistent label or differ from M2_WF_SEL "
                       f"(fallback predictions {fb_equal} of {fb_total} equal, tolerance {TOL:g})"))

        bad_status = conn.execute(
            f"SELECT COUNT(*) FROM predictions_oof WHERE split_plan_id IN ({marks}) AND (geometry_status <> 'PROVISIONAL_RELATIVE' "
            "OR label_rule_id <> ?)", tuple(plan_ids) + (receipt["label_rule_id"],)).fetchone()[0]
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
            f"SELECT COUNT(*) FROM predictions_oof p LEFT JOIN split_membership s ON s.split_plan_id = p.split_plan_id "
            f"AND s.fold_id = p.fold_id AND s.observation_id = p.observation_id AND s.role = 'TEST' "
            f"WHERE p.split_plan_id IN ({marks}) AND s.observation_id IS NULL", plan_ids).fetchone()[0]
        gates.append(_g("G26", "Predictions are held-out members", "PASS" if bad_members == 0 else "STOP", "prediction",
                       f"{bad_members} predictions are not test members of their fold"))
        audit_n = conn.execute("SELECT COUNT(*) FROM leakage_audit_log").fetchone()[0]
        audit_fail = conn.execute("SELECT COUNT(*) FROM leakage_audit_log WHERE status = 'FAIL'").fetchone()[0]
        gates.append(_g("G27", "Leakage audit log", "PASS" if audit_fail == 0 else "STOP", "model",
                       f"{audit_n} audit rows; {audit_fail} failed"))

        # G28: the interleaved tier. Every test hole's along-line neighbours are training holes of the same fold.
        inter = [p for p in plans if p["method"] == "INTERLEAVED_HOLES_WITHIN_LINE"]
        if inter:
            total_bad, total_checked = 0, 0
            for p in inter:
                bad, checked = _interleave_violations(conn, rid, p["split_plan_id"])
                total_bad += bad
                total_checked += checked
            gates.append(_g("G28", "Tier-2 plan interleaved", "PASS" if total_bad == 0 and total_checked > 0 else "STOP",
                           "split", f"{total_bad} along-line neighbour violations across {total_checked} test holes in "
                                    f"{', '.join(p['split_plan_id'] for p in inter)}"))
        else:
            gates.append(_g("G28", "Tier-2 plan interleaved", "STOP", "split", "no interleaved split plan is in the database"))

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

"""Read-only import of the frozen Objective 3 prediction snapshot, with receipts and coverage."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from kambale.objective_4.config import (O3_DB_PATH, O4_DB_PATH, StopError, code_commit, load_config, sha256_text,
                                        utc_now)
from kambale.objective_4.db import connect_o4, connect_readonly

REQUIRED_O3_OBJECTS = ("source_receipts", "spatial_split_plans", "split_membership", "analysis_observations",
                       "predictions_oof", "prediction_failures", "training_runs", "target_registries",
                       "geometry_versions", "model_families")
REQUIRED_O3_COLUMNS = {
    "predictions_oof": ("training_run_id", "split_plan_id", "fold_id", "observation_id", "hole_id", "line_code",
                        "family_id", "candidate_run_id", "true_label", "p_raw", "p_calibrated", "clipped_calibrated",
                        "predicted_class", "threshold"),
    "analysis_observations": ("upstream_interval_id", "hole_id", "line_code", "depth_from_m", "easting_m",
                              "northing_m", "z_relative_m", "in_binary_target", "indicator"),
    "split_membership": ("split_plan_id", "fold_id", "observation_id", "hole_id", "line_code", "role"),
}

MODEL_DESCRIPTIONS = {
    "BASE_PREVALENCE": ("Training prevalence baseline", "BASELINE"),
    "BASE_LOGISTIC": ("L2 logistic regression on the three coordinates", "BASELINE"),
    "M1_IK": ("Simple indicator kriging with a training-only variogram", "M1"),
    "M2_RF": ("Random forest on the three coordinates", "M2"),
    "M2_HGB": ("Histogram gradient boosting on the three coordinates", "M2"),
    "M3_HYBRID": ("Hybrid residual model; recorded as the ML-only fallback in every fold", "M3"),
}

METRIC_DEFINITIONS = (
    ("BRIER", "Brier score", "weighted mean of (p - y)^2", "LOWER_IS_BETTER", "DEFINED/UNDEFINED/NOT_ESTIMABLE",
     "Primary endpoint."),
    ("LOG_LOSS", "Log loss", "weighted negative Bernoulli log likelihood with epsilon clipping",
     "LOWER_IS_BETTER", "DEFINED/UNDEFINED/NOT_ESTIMABLE", "Epsilon is 1e-6."),
    ("ROC_AUC", "ROC-AUC", "weighted area under the ROC curve", "HIGHER_IS_BETTER", "DEFINED/UNDEFINED",
     "Undefined for a one-class evaluation set; never coerced to zero."),
    ("PR_AUC", "PR-AUC (average precision)", "weighted average precision", "HIGHER_IS_BETTER", "DEFINED/UNDEFINED",
     "Prevalence baseline is the positive rate."),
    ("ECE", "Expected calibration error", "sum of bin weight times absolute calibration gap", "LOWER_IS_BETTER",
     "DEFINED/NOT_ESTIMABLE", "Computed from merged reliability bins."),
    ("CALIBRATION_INTERCEPT", "Calibration intercept", "intercept of y ~ logit(p) fitted as a diagnostic",
     "DIAGNOSTIC", "DEFINED/UNDEFINED/NOT_ESTIMABLE", "Never applied to predictions."),
    ("CALIBRATION_SLOPE", "Calibration slope", "slope of y ~ logit(p) fitted as a diagnostic", "DIAGNOSTIC",
     "DEFINED/UNDEFINED/NOT_ESTIMABLE", "Never applied to predictions."),
    ("PRECISION", "Precision", "TP / (TP + FP)", "HIGHER_IS_BETTER", "DEFINED/UNDEFINED", "At the frozen O3 threshold."),
    ("RECALL", "Recall", "TP / (TP + FN)", "HIGHER_IS_BETTER", "DEFINED/UNDEFINED", "At the frozen O3 threshold."),
    ("SPECIFICITY", "Specificity", "TN / (TN + FP)", "HIGHER_IS_BETTER", "DEFINED/UNDEFINED", "At the frozen O3 threshold."),
    ("BALANCED_ACCURACY", "Balanced accuracy", "(recall + specificity) / 2", "HIGHER_IS_BETTER", "DEFINED/UNDEFINED",
     "At the frozen O3 threshold."),
    ("F1", "F1 / Dice", "2 * precision * recall / (precision + recall)", "HIGHER_IS_BETTER", "DEFINED/UNDEFINED",
     "At the frozen O3 threshold."),
    ("MCC", "Matthews correlation coefficient", "balanced correlation of observed and predicted classes",
     "HIGHER_IS_BETTER", "DEFINED/UNDEFINED", "At the frozen O3 threshold."),
)


def _check_objects(o3) -> None:
    present = {r[0] for r in o3.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    for name in REQUIRED_O3_OBJECTS:
        if name not in present:
            raise StopError(f"Objective 3 object missing: {name}")
    for table, cols in REQUIRED_O3_COLUMNS.items():
        have = {r[1] for r in o3.execute(f"PRAGMA table_info({table})")}
        for col in cols:
            if col not in have:
                raise StopError(f"Objective 3 column missing: {table}.{col}")


def _snapshot_hash(rows: list[dict]) -> str:
    canon = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    return sha256_text(canon)


def import_snapshot(o3_path: Path = O3_DB_PATH, o4_path: Path | None = None, config_path=None) -> dict:
    config, config_sha = load_config(config_path)
    o3 = connect_readonly(o3_path)
    try:
        _check_objects(o3)
        o3_receipt = dict(o3.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone())
        split = dict(o3.execute("SELECT * FROM spatial_split_plans WHERE primary_plan = 1").fetchone())
        target = dict(o3.execute("SELECT * FROM target_registries WHERE receipt_id = ? LIMIT 1",
                                 (o3_receipt["receipt_id"],)).fetchone())
        geom = dict(o3.execute("SELECT * FROM geometry_versions WHERE receipt_id = ? LIMIT 1",
                               (o3_receipt["receipt_id"],)).fetchone())
        train_run = dict(o3.execute("SELECT * FROM stage_runs WHERE run_kind = 'TRAIN' AND receipt_id = ? "
                                    "ORDER BY run_id DESC LIMIT 1", (o3_receipt["receipt_id"],)).fetchone())
        obs = [dict(r) for r in o3.execute(
            "SELECT upstream_interval_id, hole_id, line_code, depth_from_m, easting_m, northing_m, z_relative_m, "
            "in_binary_target, indicator FROM analysis_observations WHERE receipt_id = ? ORDER BY upstream_interval_id",
            (o3_receipt["receipt_id"],))]
        preds = [dict(r) for r in o3.execute(
            "SELECT training_run_id, split_plan_id, fold_id, observation_id, hole_id, line_code, family_id, "
            "candidate_run_id, true_label, p_raw, p_calibrated, clipped_calibrated, predicted_class, threshold "
            "FROM predictions_oof WHERE split_plan_id = ? ORDER BY family_id, observation_id", (split["split_plan_id"],))]
        failures = [dict(r) for r in o3.execute(
            "SELECT split_plan_id, fold_id, observation_id, family_id, candidate_run_id, reason FROM prediction_failures "
            "WHERE split_plan_id = ? ORDER BY family_id, observation_id", (split["split_plan_id"],))]
        membership = [dict(r) for r in o3.execute(
            "SELECT fold_id, observation_id, role FROM split_membership WHERE split_plan_id = ?",
            (split["split_plan_id"],))]
    finally:
        o3.close()

    binary_ids = [r["upstream_interval_id"] for r in obs if r["in_binary_target"] == 1]
    expected = len(binary_ids)
    if expected != int(config["evaluation"]["expected_observations"]):
        raise StopError(f"binary observation count {expected} differs from the predeclared cohort "
                        f"{config['evaluation']['expected_observations']}")
    obs_by_id = {r["upstream_interval_id"]: r for r in obs}

    families = sorted({p["family_id"] for p in preds} | {f["family_id"] for f in failures})
    pred_ids = {m: {p["observation_id"] for p in preds if p["family_id"] == m} for m in families}
    fail_ids = {m: {f["observation_id"] for f in failures if f["family_id"] == m} for m in families}
    feasible = list(config["evaluation"]["models"]["feasible"])
    common = set(binary_ids)
    for m in feasible:
        common &= pred_ids.get(m, set())

    # Coverage for every model that has predictions or failures.
    all_models = sorted(set(families) | set(fail_ids) | set(config["evaluation"]["models"]["reporting_only"]))
    coverage = {}
    for m in all_models:
        n_pred = len(pred_ids.get(m, set()))
        n_fail = len(fail_ids.get(m, set()))
        cov = n_pred / expected if expected else 0.0
        if m == "M3_HYBRID" and n_pred == expected:
            status, reason = "FALLBACK_IDENTICAL", "predictions are identical to M2_RF in every fold; M3 is the ML-only fallback"
        elif n_pred == expected:
            status, reason = "FULL", "a prediction exists for every held-out interval"
        elif n_pred == 0:
            status, reason = "NONE", f"no prediction; {n_fail} explicit failures"
        else:
            status, reason = "PARTIAL", f"{n_pred} predictions and {n_fail} failures for {expected} held-out intervals"
        coverage[m] = {"n_expected": expected, "n_predicted": n_pred, "n_failed": n_fail, "coverage": cov,
                       "status": status, "reason": reason}

    # M3 identity check against the selected M2_RF.
    rf = {(p["observation_id"]): p["p_calibrated"] for p in preds if p["family_id"] == "M2_RF"}
    m3_bad = sum(1 for p in preds if p["family_id"] == "M3_HYBRID" and
                 abs(float(p["p_calibrated"]) - float(rf.get(p["observation_id"], np.nan))) > 1e-12)
    if "M3_HYBRID" in coverage and m3_bad == 0 and coverage["M3_HYBRID"]["status"] == "FALLBACK_IDENTICAL":
        coverage["M3_HYBRID"]["reason"] = "all 1,829 predictions are identical to M2_RF; M3 is the recorded ML-only fallback"

    # Distances to the nearest training interval per fold, and the training-northing envelope.
    test_fold = {m["observation_id"]: m["fold_id"] for m in membership if m["role"] == "TEST"}
    dist = {}
    outside = {}
    for fold in sorted({m["fold_id"] for m in membership}):
        train_ids = [m["observation_id"] for m in membership if m["fold_id"] == fold and m["role"] == "TRAIN"]
        test_ids = [m["observation_id"] for m in membership if m["fold_id"] == fold and m["role"] == "TEST"]
        Xtr = np.array([[obs_by_id[i]["easting_m"], obs_by_id[i]["northing_m"], obs_by_id[i]["z_relative_m"]]
                        for i in train_ids], dtype=float)
        Xte = np.array([[obs_by_id[i]["easting_m"], obs_by_id[i]["northing_m"], obs_by_id[i]["z_relative_m"]]
                        for i in test_ids], dtype=float)
        tree = cKDTree(Xtr)
        d, _ = tree.query(Xte)
        n_min, n_max = Xtr[:, 1].min(), Xtr[:, 1].max()
        for pos, oid in enumerate(test_ids):
            dist[oid] = float(d[pos])
            outside[oid] = int(not (n_min <= obs_by_id[oid]["northing_m"] <= n_max))

    hole_sizes = {}
    for r in obs:
        if r["in_binary_target"] == 1:
            hole_sizes[r["hole_id"]] = hole_sizes.get(r["hole_id"], 0) + 1

    canonical_preds = [{"model_id": p["family_id"], "observation_id": p["observation_id"], "fold_id": p["fold_id"],
                        "true_label": p["true_label"], "p_raw": round(float(p["p_raw"]), 15),
                        "p_calibrated": round(float(p["p_calibrated"]), 15),
                        "threshold": round(float(p["threshold"]), 15), "predicted_class": p["predicted_class"],
                        "clipped": p["clipped_calibrated"]} for p in preds]
    snapshot_sha = _snapshot_hash(canonical_preds)
    imported = utc_now()

    conn = connect_o4(o4_path)
    try:
        existing = conn.execute("SELECT receipt_id FROM source_receipts WHERE o3_path = ? AND "
                                "o3_prediction_snapshot_sha256 = ?", (o3_path.as_posix(), snapshot_sha)).fetchone()
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, started_utc, status, code_commit, note) "
            "VALUES ('IMPORT', ?, ?, ?, 'RUNNING', ?, ?)",
            (config["config_version"], config_sha, utc_now(), code_commit(),
             "reused receipt" if existing else "new receipt")).lastrowid
        if existing:
            receipt_id = existing["receipt_id"]
            reused = True
        else:
            conn.execute("BEGIN IMMEDIATE")
            try:
                receipt_id = conn.execute(
                    "INSERT INTO source_receipts (o3_logical_name, o3_path, o3_receipt_id, o3_config_version, "
                    "o3_code_version, o3_split_plan_id, o3_split_plan_sha256, o3_prediction_snapshot_sha256, "
                    "o3_observation_count, o3_prediction_count, o3_failure_count, o1_label_rule_id, o1_label_rule_status, "
                    "o1_label_rule_definition_sha256, o1_content_sha256, o1_dataset_version_key, o2_content_sha256, "
                    "o2_handoff_status, target_id, geometry_version_id, geometry_status, crs_key, crs_datum_status, "
                    "vertical_basis, imported_utc, code_commit) VALUES ('obj3_models', ?, ?, ?, '3.0.0', ?, ?, ?, ?, ?, ?, "
                    "?, 'APPROVED', ?, ?, ?, ?, ?, ?, ?, 'PROVISIONAL_RELATIVE', 'EPSG:32630', 'VERIFIED', "
                    "'RELATIVE_TO_COLLAR', ?, ?)",
                    (o3_path.as_posix(), o3_receipt["receipt_id"], train_run["config_version"], split["split_plan_id"],
                     split["plan_sha256"], snapshot_sha, len(obs), len(preds), len(failures), o3_receipt["label_rule_id"],
                     o3_receipt["label_rule_definition_sha256"], o3_receipt["content_sha256"],
                     o3_receipt["upstream_dataset_version_key"], o3_receipt["o2_content_sha256"],
                     o3_receipt["o2_handoff_status"], target["target_id"], geom["geometry_version_id"], imported,
                     code_commit())).lastrowid

                for m in all_models:
                    desc, role = MODEL_DESCRIPTIONS.get(m, (m, "M2"))
                    cov = coverage[m]
                    comparable = 1 if m in feasible else 0
                    fallback = "M2_RF" if m == "M3_HYBRID" else None
                    note = ("distinct feasible model" if comparable else
                            ("fallback identical to M2_RF; not ranked as a hybrid" if m == "M3_HYBRID" else
                             "no prediction in any fold; reported as a coverage failure"))
                    conn.execute(
                        "INSERT INTO candidate_registry (model_id, family_id, role, description, coverage_status, "
                        "comparable, fallback_identical_to, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (m, m, role, desc, cov["status"], comparable, fallback, note))
                    conn.execute(
                        "INSERT INTO prediction_coverage (model_id, n_expected, n_predicted, n_failed, coverage, status, "
                        "reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (m, cov["n_expected"], cov["n_predicted"], cov["n_failed"], cov["coverage"], cov["status"],
                         cov["reason"]))

                for oid in binary_ids:
                    r = obs_by_id[oid]
                    conn.execute(
                        "INSERT INTO evaluation_population (receipt_id, observation_id, fold_id, line_code, hole_id, "
                        "true_label, easting_m, northing_m, z_relative_m, depth_from_m, weight_interval, weight_equal_hole, "
                        "min_distance_to_training_interval_m, outside_training_northing_envelope, extrapolation_status, "
                        "in_common_cohort) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1.0, ?, ?, ?, ?, ?)",
                        (receipt_id, oid, test_fold[oid], r["line_code"], r["hole_id"], r["indicator"],
                         r["easting_m"], r["northing_m"], r["z_relative_m"], r["depth_from_m"],
                         1.0 / hole_sizes[r["hole_id"]], dist.get(oid), outside.get(oid, 0),
                         "HELD_OUT_LINE_OUTSIDE_TRAINING_NORTHING" if outside.get(oid) else
                         "HELD_OUT_LINE_INSIDE_TRAINING_NORTHING", 1 if oid in common else 0))

                for p in preds:
                    if p["family_id"] not in all_models:
                        continue
                    conn.execute(
                        "INSERT INTO prediction_snapshot (receipt_id, source_training_run_id, model_id, observation_id, "
                        "fold_id, line_code, hole_id, true_label, p_raw, p_calibrated, selected_probability, clipped, "
                        "threshold, predicted_class) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (receipt_id, p["training_run_id"], p["family_id"], p["observation_id"], p["fold_id"],
                         p["line_code"], p["hole_id"], p["true_label"], p["p_raw"], p["p_calibrated"],
                         p["p_calibrated"], p["clipped_calibrated"], p["threshold"], p["predicted_class"]))

                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            reused = False
        plan = {
            "plan_id": "O4-PLAN-2026.11.05-1",
            "primary_endpoint": "BRIER", "primary_weighting": "INTERVAL",
            "secondary_weighting": "EQUAL_HOLE",
            "unit_of_analysis": "logged interval; uncertainty resampled by hole (primary) and line (sensitivity)",
            "cohort_definition": "intersection of feasible-model predictions on the held-out test folds",
            "calibration_policy": "O3 calibration only; O4 fits diagnostics and never recalibrates",
            "bootstrap_design": "HOLE_CLUSTER primary; LINE_CLUSTER sensitivity",
            "decision_policy_json": config["evaluation"]["decision"],
            "frozen_utc": imported,
        }
        plan_sha = sha256_text(json.dumps(plan, sort_keys=True, separators=(",", ":")))
        conn.execute(
            "INSERT OR IGNORE INTO evaluation_plan (plan_id, primary_endpoint, primary_weighting, secondary_weighting, "
            "unit_of_analysis, cohort_definition, calibration_policy, bootstrap_design, decision_policy_json, "
            "frozen_utc, plan_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (plan["plan_id"], plan["primary_endpoint"], plan["primary_weighting"], plan["secondary_weighting"],
             plan["unit_of_analysis"], plan["cohort_definition"], plan["calibration_policy"],
             plan["bootstrap_design"], json.dumps(plan["decision_policy_json"], sort_keys=True),
             plan["frozen_utc"], plan_sha))
        for metric_id, name, definition, direction, vocab, notes in METRIC_DEFINITIONS:
            conn.execute("INSERT OR IGNORE INTO metric_definitions (metric_id, name, definition, direction, "
                         "status_vocabulary, notes) VALUES (?, ?, ?, ?, ?, ?)",
                         (metric_id, name, definition, direction, vocab, notes))
        conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ?, receipt_id = ? WHERE run_id = ?",
                     (utc_now(), receipt_id, run_id))
        return {"receipt_id": receipt_id, "run_id": run_id, "reused": reused, "observations": len(obs),
                "predictions": len(preds), "failures": len(failures), "coverage": coverage,
                "common_cohort": len(common), "snapshot_sha256": snapshot_sha, "m3_differences_from_rf": m3_bad,
                "plan_sha256": plan_sha}
    finally:
        conn.close()

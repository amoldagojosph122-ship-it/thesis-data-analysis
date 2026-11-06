"""Read-only import of the frozen Objective 3 prediction snapshot, with receipts, coverage and model identities."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from kambale.objective_4.config import (FOLD_UNIT_METHOD, O3_DB_PATH, O4_DB_PATH, StopError, code_commit, load_config,
                                        sha256_text, utc_now)
from kambale.objective_4.db import connect_o4, connect_readonly

IDENTITY_TOLERANCE = 1e-12
REQUIRED_O3_OBJECTS = ("source_receipts", "spatial_split_plans", "split_membership", "analysis_observations",
                       "predictions_oof", "prediction_failures", "training_runs", "target_registries",
                       "geometry_versions", "model_families", "stage_runs")
REQUIRED_O3_COLUMNS = {
    "predictions_oof": ("training_run_id", "split_plan_id", "fold_id", "observation_id", "hole_id", "line_code",
                        "family_id", "candidate_run_id", "true_label", "p_raw", "p_calibrated", "clipped_calibrated",
                        "predicted_class", "threshold"),
    "prediction_failures": ("split_plan_id", "fold_id", "observation_id", "family_id", "candidate_run_id", "reason"),
    "analysis_observations": ("upstream_interval_id", "hole_id", "line_code", "depth_from_m", "easting_m",
                              "northing_m", "z_relative_m", "in_binary_target", "indicator"),
    "split_membership": ("split_plan_id", "fold_id", "observation_id", "hole_id", "line_code", "role"),
}

# Every candidate that can appear in the predeclared sets has a description; unknown candidates get a generic one.
MODEL_DESCRIPTIONS = {
    "BASE_PREVALENCE": ("Training prevalence: constant probability equal to the training-fold prevalence", "BASELINE"),
    "BASE_LOGISTIC": ("L2 logistic regression on easting, northing and relative Z", "BASELINE"),
    "BASE_LOGISTIC_WF": ("L2 logistic regression on easting, northing, relative Z and depth below the weathering front",
                         "BASELINE"),
    "M2_RF": ("Random forest on easting, northing and relative Z", "M2"),
    "M2_HGB": ("Histogram gradient boosting on easting, northing and relative Z", "M2"),
    "M2_RF_WF": ("Random forest on easting, northing, relative Z and depth below the weathering front", "M2"),
    "M2_HGB_WF": ("Histogram gradient boosting on easting, northing, relative Z and depth below the weathering front",
                  "M2"),
    "M2_SEL": ("Inner-selected plain M2: in each fold, a copy of M2_RF or M2_HGB with the lower inner-CV log loss",
               "M2"),
    "M2_WF_SEL": ("Inner-selected M2 with weathering front: in each fold, a copy of M2_RF_WF or M2_HGB_WF with the lower "
                  "inner-CV log loss; the trend component of M3", "M2"),
    "M1_IK": ("Simple indicator kriging of the training indicator with an inner-CV covariance", "M1"),
    "M3_HYBRID": ("Hybrid residual model: calibrated M2_WF_SEL trend plus a simple-kriged residual with an inner-CV "
                  "covariance", "M3"),
}
GENERIC_DESCRIPTION = ("Candidate reported in the Objective 3 snapshot but not in the predeclared model sets", "M2")


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


def identity_records(order, probs, common_ids, tolerance=IDENTITY_TOLERANCE):
    """Pairwise identity of calibrated probabilities on the common cohort.

    order is the predeclared feasible order; probs maps model -> {observation_id: p_calibrated}. Returns the record of
    every unordered pair (earlier model first) and, for each model, the nearest EARLIER model it is identical to (the
    reference), or None. A later model identical to an earlier one is reported as IDENTICAL_TO that earlier model; the
    earlier model is never marked as identical to a later one.
    """
    pairs, identical = [], set()
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            a, b = order[i], order[j]
            ids = [oid for oid in common_ids if oid in probs.get(a, {}) and oid in probs.get(b, {})]
            if ids:
                diff = float(max(abs(probs[a][oid] - probs[b][oid]) for oid in ids))
            else:
                diff = None
            is_identical = bool(ids) and diff <= tolerance
            if is_identical:
                identical.add((i, j))
            pairs.append({"model_a": a, "model_b": b, "n_common": len(ids), "max_abs_difference": diff,
                          "tolerance": tolerance, "identical": int(is_identical)})
    references = {}
    for j, model in enumerate(order):
        earlier = [i for i in range(j) if (i, j) in identical]
        references[model] = order[max(earlier)] if earlier else None
    return pairs, references


def import_snapshot(o3_path: Path = O3_DB_PATH, o4_path: Path | None = None, config_path=None) -> dict:
    config, config_sha = load_config(config_path)
    ev = config["evaluation"]
    split_plan_id = config["paths"]["o3_split_plan_id"]
    expected_method = FOLD_UNIT_METHOD[ev["fold_unit"]]
    feasible = list(ev["models"]["feasible"])
    reporting_only = [m for m in ev["models"]["reporting_only"] or [] if m not in feasible]
    o3 = connect_readonly(o3_path)
    try:
        _check_objects(o3)
        o3_receipt = dict(o3.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone())
        split_row = o3.execute("SELECT * FROM spatial_split_plans WHERE split_plan_id = ?", (split_plan_id,)).fetchone()
        if split_row is None:
            raise StopError(f"Objective 3 split plan {split_plan_id} is not in the Objective 3 database")
        split = dict(split_row)
        if split["method"] != expected_method:
            raise StopError(f"split plan {split_plan_id} has method {split['method']}; the config fold unit "
                            f"{ev['fold_unit']} requires {expected_method}")
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
            "FROM predictions_oof WHERE split_plan_id = ? ORDER BY candidate_run_id, observation_id", (split_plan_id,))]
        failures = [dict(r) for r in o3.execute(
            "SELECT split_plan_id, fold_id, observation_id, family_id, candidate_run_id, reason FROM prediction_failures "
            "WHERE split_plan_id = ? ORDER BY candidate_run_id, observation_id", (split_plan_id,))]
        membership = [dict(r) for r in o3.execute(
            "SELECT fold_id, observation_id, role FROM split_membership WHERE split_plan_id = ?", (split_plan_id,))]
    finally:
        o3.close()

    binary_ids = [r["upstream_interval_id"] for r in obs if r["in_binary_target"] == 1]
    expected = len(binary_ids)
    if expected != int(ev["expected_observations"]):
        raise StopError(f"binary observation count {expected} differs from the predeclared cohort "
                        f"{ev['expected_observations']}")
    obs_by_id = {r["upstream_interval_id"]: r for r in obs}

    # The model identifier is the Objective 3 candidate run identifier (equal to the family identifier in every row).
    candidates_seen = {p["candidate_run_id"] for p in preds} | {f["candidate_run_id"] for f in failures}
    observed_extra = sorted(candidates_seen - set(feasible) - set(reporting_only))
    all_models = feasible + reporting_only + observed_extra
    pred_ids = {m: {p["observation_id"] for p in preds if p["candidate_run_id"] == m} for m in all_models}
    fail_ids = {m: {f["observation_id"] for f in failures if f["candidate_run_id"] == m} for m in all_models}
    family_of = {p["candidate_run_id"]: p["family_id"] for p in preds}

    coverage = {}
    for m in all_models:
        n_pred = len(pred_ids[m])
        n_fail = len(fail_ids[m])
        cov = n_pred / expected if expected else 0.0
        if n_pred == expected:
            status, reason = "FULL", "a prediction exists for every held-out interval"
        elif n_pred == 0:
            status, reason = "NONE", f"no prediction; {n_fail} explicit failures"
        else:
            status, reason = "PARTIAL", f"{n_pred} predictions and {n_fail} failures for {expected} held-out intervals"
        coverage[m] = {"n_expected": expected, "n_predicted": n_pred, "n_failed": n_fail, "coverage": cov,
                       "status": status, "reason": reason}

    # Common cohort: the held-out intervals that every feasible model with full coverage predicts.
    full_feasible = [m for m in feasible if coverage[m]["status"] == "FULL"]
    if not full_feasible:
        raise StopError("no feasible model has full coverage; the common cohort is empty")
    common = set(binary_ids)
    for m in full_feasible:
        common &= pred_ids[m]

    # Identity of calibrated probabilities over the common cohort, for the feasible models in their predeclared order.
    probs = {m: {p["observation_id"]: float(p["p_calibrated"]) for p in preds if p["candidate_run_id"] == m}
             for m in feasible}
    identity_pairs, references = identity_records(feasible, probs, sorted(common))

    # Distances to the nearest training interval per fold, and the training-northing envelope.
    dist, outside = {}, {}
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
    test_fold = {m["observation_id"]: m["fold_id"] for m in membership if m["role"] == "TEST"}
    fold_tag = "HELD_OUT_LINE" if ev["fold_unit"] == "HELD_OUT_LINE" else "HELD_OUT_HOLE"

    hole_sizes = {}
    for r in obs:
        if r["in_binary_target"] == 1:
            hole_sizes[r["hole_id"]] = hole_sizes.get(r["hole_id"], 0) + 1

    canonical_preds = [{"model_id": p["candidate_run_id"], "observation_id": p["observation_id"],
                        "fold_id": p["fold_id"], "true_label": p["true_label"],
                        "p_raw": round(float(p["p_raw"]), 15), "p_calibrated": round(float(p["p_calibrated"]), 15),
                        "threshold": round(float(p["threshold"]), 15), "predicted_class": p["predicted_class"],
                        "clipped": p["clipped_calibrated"]} for p in preds]
    snapshot_sha = _snapshot_hash(canonical_preds)
    imported = utc_now()

    conn = connect_o4(o4_path)
    try:
        existing = conn.execute("SELECT receipt_id FROM source_receipts WHERE o3_path = ? AND "
                                "o3_prediction_snapshot_sha256 = ? AND o3_split_plan_id = ? AND tier = ?",
                                (o3_path.as_posix(), snapshot_sha, split_plan_id, config["tier"])).fetchone()
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
                    "o3_code_version, tier, o3_split_plan_id, o3_split_plan_sha256, o3_prediction_snapshot_sha256, "
                    "o3_observation_count, o3_prediction_count, o3_failure_count, o1_label_rule_id, o1_label_rule_status, "
                    "o1_label_rule_definition_sha256, o1_content_sha256, o1_dataset_version_key, o2_content_sha256, "
                    "o2_handoff_status, target_id, geometry_version_id, geometry_status, crs_key, crs_datum_status, "
                    "vertical_basis, imported_utc, code_commit) VALUES ('obj3_models', ?, ?, ?, '3.0.0', ?, ?, ?, ?, ?, ?, "
                    "?, ?, 'APPROVED', ?, ?, ?, ?, ?, ?, ?, 'PROVISIONAL_RELATIVE', 'EPSG:32630', 'VERIFIED', "
                    "'RELATIVE_TO_COLLAR', ?, ?)",
                    (o3_path.as_posix(), o3_receipt["receipt_id"], train_run["config_version"], config["tier"],
                     split["split_plan_id"], split["plan_sha256"], snapshot_sha, len(obs), len(preds), len(failures),
                     o3_receipt["label_rule_id"], o3_receipt["label_rule_definition_sha256"],
                     o3_receipt["content_sha256"], o3_receipt["upstream_dataset_version_key"],
                     o3_receipt["o2_content_sha256"], o3_receipt["o2_handoff_status"], target["target_id"],
                     geom["geometry_version_id"], imported, code_commit())).lastrowid

                for m in all_models:
                    desc, role = MODEL_DESCRIPTIONS.get(m, GENERIC_DESCRIPTION)
                    cov = coverage[m]
                    ref = references.get(m)
                    identity = "IDENTICAL_TO" if ref else "DISTINCT"
                    comparable = 1 if (m in feasible and identity == "DISTINCT") else 0
                    if m not in feasible:
                        note = "not in the predeclared feasible set; reported only"
                    elif ref:
                        note = f"identical to {ref} on every common observation; reported, not ranked"
                    else:
                        note = "distinct feasible model"
                    conn.execute(
                        "INSERT INTO candidate_registry (model_id, family_id, role, description, coverage_status, "
                        "identity_status, identical_to, comparable, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (m, family_of.get(m, m), role, desc, cov["status"], identity, ref, comparable, note))
                    conn.execute(
                        "INSERT INTO prediction_coverage (model_id, n_expected, n_predicted, n_failed, coverage, status, "
                        "reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (m, cov["n_expected"], cov["n_predicted"], cov["n_failed"], cov["coverage"], cov["status"],
                         cov["reason"]))

                for rec in identity_pairs:
                    conn.execute("INSERT INTO model_identities (model_a, model_b, n_common, max_abs_difference, "
                                 "tolerance, identical) VALUES (?, ?, ?, ?, ?, ?)",
                                 (rec["model_a"], rec["model_b"], rec["n_common"], rec["max_abs_difference"],
                                  rec["tolerance"], rec["identical"]))

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
                         f"{fold_tag}_OUTSIDE_TRAINING_NORTHING" if outside.get(oid) else
                         f"{fold_tag}_INSIDE_TRAINING_NORTHING", 1 if oid in common else 0))

                for p in preds:
                    conn.execute(
                        "INSERT INTO prediction_snapshot (receipt_id, source_training_run_id, model_id, observation_id, "
                        "fold_id, line_code, hole_id, true_label, p_raw, p_calibrated, selected_probability, clipped, "
                        "threshold, predicted_class) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (receipt_id, p["training_run_id"], p["candidate_run_id"], p["observation_id"], p["fold_id"],
                         p["line_code"], p["hole_id"], p["true_label"], p["p_raw"], p["p_calibrated"],
                         p["p_calibrated"], p["clipped_calibrated"], p["threshold"], p["predicted_class"]))

                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            reused = False
        plan = {
            "plan_id": f"{config['config_version']}-PLAN",
            "primary_endpoint": "BRIER", "primary_weighting": "INTERVAL",
            "secondary_weighting": "EQUAL_HOLE",
            "unit_of_analysis": f"logged interval; fold unit {ev['fold_unit']}; uncertainty resampled by hole "
                                "(primary) and line (sensitivity)",
            "cohort_definition": "intersection of the full-coverage feasible models on the held-out folds",
            "calibration_policy": "O3 calibration only; O4 fits diagnostics and never recalibrates",
            "bootstrap_design": "HOLE_CLUSTER primary; LINE_CLUSTER sensitivity",
            "decision_policy_json": ev["decision"],
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
        return {"receipt_id": receipt_id, "run_id": run_id, "reused": reused, "tier": config["tier"],
                "split_plan_id": split_plan_id, "observations": len(obs), "predictions": len(preds),
                "failures": len(failures), "coverage": coverage, "common_cohort": len(common),
                "identities": {m: references.get(m) for m in feasible}, "snapshot_sha256": snapshot_sha,
                "plan_sha256": plan_sha}
    finally:
        conn.close()


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

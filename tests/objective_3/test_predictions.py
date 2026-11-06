"""Out-of-fold completeness and probability checks on the built database."""

import pytest


def test_every_completed_run_covers_every_test_interval(o3_ro, split_plan_id):  # G09
    for r in o3_ro.execute("SELECT training_run_id, fold_id FROM training_runs WHERE split_plan_id = ?",
                           (split_plan_id,)).fetchall():
        test_ids = {x[0] for x in o3_ro.execute(
            "SELECT observation_id FROM split_membership WHERE split_plan_id = ? AND fold_id = ? AND role = 'TEST'",
            (split_plan_id, r["fold_id"]))}
        pred = {x[0] for x in o3_ro.execute(
            "SELECT observation_id FROM predictions_oof WHERE training_run_id = ?", (r["training_run_id"],))}
        fail = {x[0] for x in o3_ro.execute(
            "SELECT observation_id FROM prediction_failures WHERE training_run_id = ?", (r["training_run_id"],))}
        assert test_ids - pred - fail == set()


def test_no_duplicate_predictions(o3_ro):
    bad = o3_ro.execute("SELECT COUNT(*) FROM (SELECT training_run_id, observation_id, COUNT(*) c FROM predictions_oof "
                        "GROUP BY training_run_id, observation_id HAVING c > 1)").fetchone()[0]
    assert bad == 0


def test_probabilities_are_bounded(o3_ro):  # schema CHECK, re-checked here
    bad = o3_ro.execute("SELECT COUNT(*) FROM predictions_oof WHERE p_raw < 0 OR p_raw > 1 OR p_calibrated < 0 "
                        "OR p_calibrated > 1").fetchone()[0]
    assert bad == 0


def test_predicted_class_follows_the_recorded_threshold(o3_ro):
    bad = o3_ro.execute("SELECT COUNT(*) FROM predictions_oof WHERE predicted_class <> "
                        "(CASE WHEN p_calibrated >= threshold THEN 1 ELSE 0 END)").fetchone()[0]
    assert bad == 0


def test_selected_m2_is_one_run_per_fold(o3_ro, split_plan_id):
    for (fold,) in o3_ro.execute("SELECT DISTINCT fold_id FROM training_runs WHERE split_plan_id = ?",
                                 (split_plan_id,)):
        n = o3_ro.execute("SELECT COUNT(*) FROM training_runs WHERE split_plan_id = ? AND fold_id = ? AND selected = 1",
                          (split_plan_id, fold)).fetchone()[0]
        assert n == 1


def test_no_outer_performance_column_is_stored(o3_ro):
    """Objective 3 stores training-only diagnostics; no table holds an outer-test metric."""
    columns = {r[1] for table in ("training_runs", "hyperparameter_trials", "predictions_oof")
               for r in o3_ro.execute(f"PRAGMA table_info({table})")}
    for forbidden in ("auc", "roc_auc", "brier", "outer_log_loss", "outer_score"):
        assert forbidden not in columns

"""Gate outcomes and structural checks on the built Objective 3 database."""

import pytest

from kambale.objective_3.config import O2_DB_PATH, UPSTREAM_DB_PATH

EXIT_GATES = ("G01", "G02", "G03", "G05", "G08", "G09", "G10", "G11", "G12", "G13", "G15", "G16", "G17", "G19",
              "G20", "G21", "G22", "G25", "G26", "G28")
needs_upstream = pytest.mark.skipif(not UPSTREAM_DB_PATH.exists(), reason="Objective 1 database is required")
needs_o2 = pytest.mark.skipif(not O2_DB_PATH.exists(), reason="Objective 2 database is required")

FRONT = "depth_below_weathering_front_m"


def _latest_verify(o3_ro):
    return o3_ro.execute("SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'VERIFY'").fetchone()[0]


def test_latest_verify_meets_exit_conditions(o3_ro):
    rows = o3_ro.execute("SELECT gate_id, status FROM gate_results WHERE run_id = ?", (_latest_verify(o3_ro),)).fetchall()
    status = {r["gate_id"]: r["status"] for r in rows}
    assert [g for g in EXIT_GATES if status.get(g) != "PASS"] == []


def test_split_membership_is_disjoint(o3_ro):  # G05
    bad = 0
    for plan, fold in o3_ro.execute("SELECT DISTINCT split_plan_id, fold_id FROM split_membership").fetchall():
        tr = {r[0] for r in o3_ro.execute("SELECT observation_id FROM split_membership WHERE split_plan_id = ? "
                                          "AND fold_id = ? AND role = 'TRAIN'", (plan, fold))}
        te = {r[0] for r in o3_ro.execute("SELECT observation_id FROM split_membership WHERE split_plan_id = ? "
                                          "AND fold_id = ? AND role = 'TEST'", (plan, fold))}
        bad += len(tr & te)
    assert bad == 0


def test_no_test_observation_in_training_manifest(o3_ro):  # G11
    bad = o3_ro.execute(
        "SELECT COUNT(*) FROM training_sample_manifest m JOIN training_runs t ON t.training_run_id = m.training_run_id "
        "JOIN split_membership s ON s.split_plan_id = t.split_plan_id AND s.fold_id = t.fold_id "
        "AND s.observation_id = m.observation_id AND s.role = 'TEST'").fetchone()[0]
    assert bad == 0


def test_predictions_are_held_out_members(o3_ro):  # G26
    bad = o3_ro.execute(
        "SELECT COUNT(*) FROM predictions_oof p LEFT JOIN split_membership s ON s.split_plan_id = p.split_plan_id "
        "AND s.fold_id = p.fold_id AND s.observation_id = p.observation_id AND s.role = 'TEST' "
        "WHERE s.observation_id IS NULL").fetchone()[0]
    assert bad == 0


def test_m1_runs_carry_the_full_grid_and_a_chosen_covariance(o3_ro):  # G19
    rows = o3_ro.execute("SELECT training_run_id, status FROM training_runs WHERE family_id = 'M1_IK'").fetchall()
    assert rows
    for r in rows:
        assert o3_ro.execute("SELECT COUNT(*) FROM hyperparameter_trials WHERE training_run_id = ?",
                             (r["training_run_id"],)).fetchone()[0] == 16
        assert o3_ro.execute("SELECT COUNT(*) FROM hyperparameter_trials WHERE training_run_id = ? AND selected = 1",
                             (r["training_run_id"],)).fetchone()[0] == 1


def test_m1_not_estimable_has_no_prediction_and_has_failures(o3_ro):  # G19 (status unused in configuration 2)
    for r in o3_ro.execute("SELECT training_run_id, split_plan_id, fold_id FROM training_runs "
                           "WHERE family_id = 'M1_IK' AND status = 'NOT_ESTIMABLE'").fetchall():
        assert o3_ro.execute("SELECT COUNT(*) FROM predictions_oof WHERE training_run_id = ?",
                             (r["training_run_id"],)).fetchone()[0] == 0


def test_m3_fallback_is_labelled(o3_ro):  # G20
    rows = o3_ro.execute("SELECT training_run_id, status FROM training_runs WHERE family_id = 'M3_HYBRID'").fetchall()
    assert rows
    for r in rows:
        statuses = {x[0] for x in o3_ro.execute("SELECT fallback_status FROM hybrid_residual_variogram "
                                                 "WHERE training_run_id = ?", (r["training_run_id"],))}
        if r["status"] == "FALLBACK":
            assert statuses == {"FALLBACK_ML_ONLY"}
        elif r["status"] == "COMPLETED":
            assert statuses == {"HYBRID_USED"}


def test_m3_fallback_predictions_equal_m2_wf_sel(o3_ro):  # G20
    bad = o3_ro.execute(
        "SELECT COUNT(*) FROM predictions_oof p JOIN training_runs t ON t.training_run_id = p.training_run_id "
        "JOIN predictions_oof c ON c.split_plan_id = p.split_plan_id AND c.fold_id = p.fold_id "
        "AND c.observation_id = p.observation_id AND c.family_id = 'M2_WF_SEL' "
        "WHERE t.family_id = 'M3_HYBRID' AND t.status = 'FALLBACK' AND ABS(p.p_calibrated - c.p_calibrated) > 1e-12"
    ).fetchone()[0]
    assert bad == 0


def test_final_refit_waits_for_objective_4(o3_ro):  # G14
    rows = o3_ro.execute("SELECT status FROM final_refits").fetchall()
    assert rows and all(r["status"] == "PENDING_O4" for r in rows)
    assert o3_ro.execute("SELECT COUNT(*) FROM final_refits WHERE status = 'RUN'").fetchone()[0] == 0


def test_deployed_predictors_are_safe(o3_ro):  # G07
    rows = o3_ro.execute("SELECT name, leakage_designation, available_at_prediction FROM feature_registry "
                         "WHERE name IN ('easting_m','northing_m','z_relative_m', ?)", (FRONT,)).fetchall()
    assert len(rows) == 4
    assert all(r["leakage_designation"] == "SAFE" and r["available_at_prediction"] == 1 for r in rows)


def test_leakage_audit_has_no_failure(o3_ro):  # G27
    assert o3_ro.execute("SELECT COUNT(*) FROM leakage_audit_log WHERE status = 'FAIL'").fetchone()[0] == 0


def test_front_feature_is_fold_safe_in_every_fold(o3_ro):  # FRONT_FEATURE_FOLD_SAFE
    rows = o3_ro.execute("SELECT status FROM leakage_audit_log WHERE check_name = 'FRONT_FEATURE_FOLD_SAFE'").fetchall()
    assert len(rows) == 2 and all(r[0] == "PASS" for r in rows)


@needs_o2
def test_objective_2_handoff_is_recorded(o3_ro, receipt_id):  # G25
    row = o3_ro.execute("SELECT o2_handoff_status, o2_candidate_family FROM source_receipts WHERE receipt_id = ?",
                        (receipt_id,)).fetchone()
    assert row["o2_handoff_status"] == "NOT_IDENTIFIABLE"
    assert row["o2_candidate_family"] == "NONE"

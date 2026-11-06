"""Gate outcomes and structural checks on the built Objective 3 database."""

import pytest

from kambale.objective_3.config import O2_DB_PATH, UPSTREAM_DB_PATH

EXIT_GATES = ("G01", "G02", "G03", "G05", "G08", "G09", "G10", "G11", "G12", "G13", "G15", "G16", "G17", "G19",
              "G20", "G25", "G26")
needs_upstream = pytest.mark.skipif(not UPSTREAM_DB_PATH.exists(), reason="Objective 1 database is required")
needs_o2 = pytest.mark.skipif(not O2_DB_PATH.exists(), reason="Objective 2 database is required")


def _latest_verify(o3_ro):
    return o3_ro.execute("SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'VERIFY'").fetchone()[0]


def test_latest_verify_meets_exit_conditions(o3_ro):
    rows = o3_ro.execute("SELECT gate_id, status FROM gate_results WHERE run_id = ?", (_latest_verify(o3_ro),)).fetchall()
    status = {r["gate_id"]: r["status"] for r in rows}
    assert [g for g in EXIT_GATES if status.get(g) != "PASS"] == []


def test_split_membership_is_disjoint(o3_ro, split_plan_id):  # G05
    bad = 0
    for (fold,) in o3_ro.execute("SELECT DISTINCT fold_id FROM split_membership WHERE split_plan_id = ?",
                                 (split_plan_id,)):
        tr = {r[0] for r in o3_ro.execute("SELECT observation_id FROM split_membership WHERE split_plan_id = ? "
                                          "AND fold_id = ? AND role = 'TRAIN'", (split_plan_id, fold))}
        te = {r[0] for r in o3_ro.execute("SELECT observation_id FROM split_membership WHERE split_plan_id = ? "
                                          "AND fold_id = ? AND role = 'TEST'", (split_plan_id, fold))}
        bad += len(tr & te)
    assert bad == 0


def test_no_test_observation_in_training_manifest(o3_ro, split_plan_id):  # G11
    bad = o3_ro.execute(
        "SELECT COUNT(*) FROM training_sample_manifest m JOIN training_runs t ON t.training_run_id = m.training_run_id "
        "JOIN split_membership s ON s.split_plan_id = t.split_plan_id AND s.fold_id = t.fold_id "
        "AND s.observation_id = m.observation_id AND s.role = 'TEST' WHERE t.split_plan_id = ?",
        (split_plan_id,)).fetchone()[0]
    assert bad == 0


def test_predictions_are_held_out_members(o3_ro, split_plan_id):  # G26
    bad = o3_ro.execute(
        "SELECT COUNT(*) FROM predictions_oof p LEFT JOIN split_membership s ON s.split_plan_id = p.split_plan_id "
        "AND s.fold_id = p.fold_id AND s.observation_id = p.observation_id AND s.role = 'TEST' "
        "WHERE p.split_plan_id = ? AND s.observation_id IS NULL", (split_plan_id,)).fetchone()[0]
    assert bad == 0


def test_m1_not_estimable_has_no_prediction_and_has_failures(o3_ro, split_plan_id):  # G19
    rows = o3_ro.execute("SELECT training_run_id, fold_id, status FROM training_runs WHERE split_plan_id = ? "
                         "AND family_id = 'M1_IK'", (split_plan_id,)).fetchall()
    assert rows
    for r in rows:
        if r["status"] != "NOT_ESTIMABLE":
            continue
        assert o3_ro.execute("SELECT COUNT(*) FROM predictions_oof WHERE training_run_id = ?",
                             (r["training_run_id"],)).fetchone()[0] == 0
        expected = o3_ro.execute("SELECT COUNT(*) FROM split_membership WHERE split_plan_id = ? AND fold_id = ? "
                                 "AND role = 'TEST'", (split_plan_id, r["fold_id"])).fetchone()[0]
        assert o3_ro.execute("SELECT COUNT(*) FROM prediction_failures WHERE training_run_id = ?",
                             (r["training_run_id"],)).fetchone()[0] == expected


def test_m3_fallback_is_labelled(o3_ro, split_plan_id):  # G20
    rows = o3_ro.execute("SELECT training_run_id, status FROM training_runs WHERE split_plan_id = ? "
                         "AND family_id = 'M3_HYBRID'", (split_plan_id,)).fetchall()
    assert rows
    for r in rows:
        statuses = {x[0] for x in o3_ro.execute("SELECT fallback_status FROM hybrid_residual_variogram "
                                                 "WHERE training_run_id = ?", (r["training_run_id"],))}
        if r["status"] == "FALLBACK":
            assert statuses == {"FALLBACK_ML_ONLY"}
        elif r["status"] == "COMPLETED":
            assert statuses == {"HYBRID_USED"}


def test_final_refit_waits_for_objective_4(o3_ro):  # G14
    rows = o3_ro.execute("SELECT status FROM final_refits").fetchall()
    assert rows and all(r["status"] == "PENDING_O4" for r in rows)
    assert o3_ro.execute("SELECT COUNT(*) FROM final_refits WHERE status = 'RUN'").fetchone()[0] == 0


def test_deployed_predictors_are_safe(o3_ro):  # G07
    rows = o3_ro.execute("SELECT name, leakage_designation, available_at_prediction FROM feature_registry "
                         "WHERE name IN ('easting_m','northing_m','z_relative_m')").fetchall()
    assert len(rows) == 3
    assert all(r["leakage_designation"] == "SAFE" and r["available_at_prediction"] == 1 for r in rows)


def test_leakage_audit_has_no_failure(o3_ro):  # G27
    assert o3_ro.execute("SELECT COUNT(*) FROM leakage_audit_log WHERE status = 'FAIL'").fetchone()[0] == 0


@needs_o2
def test_objective_2_handoff_is_recorded(o3_ro, receipt_id):  # G25
    row = o3_ro.execute("SELECT o2_handoff_status, o2_candidate_family FROM source_receipts WHERE receipt_id = ?",
                        (receipt_id,)).fetchone()
    assert row["o2_handoff_status"] == "NOT_IDENTIFIABLE"
    assert row["o2_candidate_family"] == "NONE"

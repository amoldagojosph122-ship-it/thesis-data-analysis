"""Gate and structural checks on the built Objective 4 database."""

import pytest

from kambale.objective_4.config import O3_DB_PATH

EXIT_GATES = ("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G10", "G11", "G12", "G13", "G15", "G16",
              "G17", "G18", "G19", "G20", "G21", "G24", "G25")
needs_o3 = pytest.mark.skipif(not O3_DB_PATH.exists(), reason="Objective 3 database is required")


def _latest_verify(o4_ro):
    return o4_ro.execute("SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'VERIFY'").fetchone()[0]


def test_latest_verify_meets_exit_conditions(o4_ro):
    rows = o4_ro.execute("SELECT gate_id, status FROM gate_results WHERE run_id = ?", (_latest_verify(o4_ro),)).fetchall()
    status = {r["gate_id"]: r["status"] for r in rows}
    assert [g for g in EXIT_GATES if status.get(g) != "PASS"] == []


def test_common_cohort_is_identical(o4_ro):
    common = {r[0] for r in o4_ro.execute("SELECT observation_id FROM evaluation_population WHERE in_common_cohort = 1")}
    assert len(common) == 1829
    for m in ("BASE_PREVALENCE", "BASE_LOGISTIC", "M2_RF", "M2_HGB"):
        ids = {r[0] for r in o4_ro.execute("SELECT observation_id FROM prediction_snapshot WHERE model_id = ?", (m,))}
        assert ids == common


def test_m1_coverage_is_reported(o4_ro):
    row = o4_ro.execute("SELECT n_predicted, n_failed, coverage, status FROM prediction_coverage WHERE model_id = 'M1_IK'").fetchone()
    assert row["n_predicted"] == 0
    assert row["n_failed"] == 1829
    assert row["coverage"] == 0.0
    decision = o4_ro.execute("SELECT role, improvement_status FROM comparison_decisions WHERE model_id = 'M1_IK'").fetchone()
    assert decision["role"] == "NOT_COMPARABLE"
    assert decision["improvement_status"] == "NOT_COMPARABLE"


def test_m3_is_recorded_as_fallback(o4_ro):
    row = o4_ro.execute("SELECT fallback_identical_to, comparable FROM candidate_registry WHERE model_id = 'M3_HYBRID'").fetchone()
    assert row["fallback_identical_to"] == "M2_RF"
    assert row["comparable"] == 0
    bad = o4_ro.execute(
        "SELECT COUNT(*) FROM prediction_snapshot a JOIN prediction_snapshot b "
        "ON a.observation_id = b.observation_id AND b.model_id = 'M2_RF' "
        "WHERE a.model_id = 'M3_HYBRID' AND ABS(a.selected_probability - b.selected_probability) > 1e-12").fetchone()[0]
    assert bad == 0


def test_selected_model_has_lowest_brier(o4_ro):
    brier = {r["model_id"]: r["value"] for r in o4_ro.execute(
        "SELECT model_id, value FROM pooled_metrics WHERE metric_id = 'BRIER' AND weighting = 'INTERVAL' "
        "AND status = 'DEFINED'")}
    feasible = ("BASE_PREVALENCE", "BASE_LOGISTIC", "M2_RF", "M2_HGB")
    best = min((brier[m], m) for m in feasible)[1]
    selected = o4_ro.execute("SELECT model_id FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()[0]
    assert selected == best


def test_decision_has_cluster_interval(o4_ro):
    row = o4_ro.execute("SELECT ci_low, ci_high FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()
    assert row["ci_low"] is not None and row["ci_high"] is not None
    designs = {r[0] for r in o4_ro.execute("SELECT method FROM resampling_designs")}
    assert {"HOLE_CLUSTER", "LINE_CLUSTER"} <= designs


def test_handoff_matches_selected(o4_ro):
    selected = o4_ro.execute("SELECT model_id FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()[0]
    handoff = o4_ro.execute("SELECT selected_model_id, receipt_sha256 FROM locked_handoff_receipts").fetchone()
    assert handoff["selected_model_id"] == selected
    assert handoff["receipt_sha256"]


def test_no_model_refit_tables(o4_ro):
    tables = {r[0] for r in o4_ro.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "training_runs" not in tables
    assert "model_artifacts" not in tables


def test_audit_has_no_failure(o4_ro):
    assert o4_ro.execute("SELECT COUNT(*) FROM evaluation_audit_log WHERE status = 'FAIL'").fetchone()[0] == 0


def test_thresholds_match_o3(o4_ro):
    assert o4_ro.execute("SELECT COUNT(*) FROM prediction_snapshot WHERE threshold IS NULL").fetchone()[0] == 0

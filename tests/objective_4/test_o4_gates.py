"""Gate, identity and decision checks on each built tier database (skipped when a database has not been built)."""

import yaml

EXIT_GATES = ("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08", "G10", "G11", "G12", "G13", "G15", "G16",
              "G17", "G18", "G19", "G20", "G21", "G24", "G25", "G28", "G29")


def _config(tier_paths):
    return yaml.safe_load(tier_paths["config_path"].read_text(encoding="utf-8"))


def _latest_verify(o4_ro):
    return o4_ro.execute("SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'VERIFY'").fetchone()[0]


def test_latest_verify_meets_exit_conditions(o4_ro):
    rows = o4_ro.execute("SELECT gate_id, status FROM gate_results WHERE run_id = ?", (_latest_verify(o4_ro),)).fetchall()
    status = {r["gate_id"]: r["status"] for r in rows}
    assert [g for g in EXIT_GATES if status.get(g) != "PASS"] == []


def test_common_cohort_is_contained_in_every_full_model(o4_ro, tier_paths):
    common = {r[0] for r in o4_ro.execute("SELECT observation_id FROM evaluation_population WHERE in_common_cohort = 1")}
    assert len(common) == 1829
    for m in _config(tier_paths)["evaluation"]["models"]["feasible"]:
        if o4_ro.execute("SELECT status FROM prediction_coverage WHERE model_id = ?", (m,)).fetchone()[0] != "FULL":
            continue
        ids = {r[0] for r in o4_ro.execute("SELECT observation_id FROM prediction_snapshot WHERE model_id = ?", (m,))}
        assert common <= ids


def test_identities_are_recorded_and_not_ranked(o4_ro):
    rows = o4_ro.execute("SELECT model_id, identical_to, comparable FROM candidate_registry "
                         "WHERE identity_status = 'IDENTICAL_TO'").fetchall()
    for r in rows:
        assert r["identical_to"] is not None and r["comparable"] == 0
        dec = o4_ro.execute("SELECT role, reason FROM comparison_decisions WHERE model_id = ?", (r["model_id"],)).fetchone()
        assert dec["role"] == "NOT_COMPARABLE"
        assert f"identical to {r['identical_to']}" in dec["reason"]


def test_selected_is_lowest_distinct_brier(o4_ro, tier_paths):
    feasible = _config(tier_paths)["evaluation"]["models"]["feasible"]
    distinct = {r[0] for r in o4_ro.execute("SELECT model_id FROM candidate_registry WHERE identity_status = 'DISTINCT' "
                                            "AND coverage_status = 'FULL'")}
    brier = {r["model_id"]: r["value"] for r in o4_ro.execute(
        "SELECT model_id, value FROM pooled_metrics WHERE metric_id = 'BRIER' AND weighting = 'INTERVAL' AND status = 'DEFINED'")}
    best = min((brier[m], m) for m in feasible if m in distinct)[1]
    selected = o4_ro.execute("SELECT model_id FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()[0]
    assert selected == best


def test_handoff_matches_tier_config(o4_ro, tier_paths):
    cfg = _config(tier_paths)
    h = o4_ro.execute("SELECT * FROM locked_handoff_receipts").fetchone()
    assert h["tier"] == cfg["tier"]
    assert h["split_plan_id"] == cfg["paths"]["o3_split_plan_id"]
    assert h["claim"] == cfg["claim"].strip()
    assert h["receipt_sha256"]


def test_decision_has_cluster_interval_and_both_designs(o4_ro):
    row = o4_ro.execute("SELECT ci_low, ci_high FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()
    assert row["ci_low"] is not None and row["ci_high"] is not None
    designs = {r[0] for r in o4_ro.execute("SELECT method FROM resampling_designs")}
    assert {"HOLE_CLUSTER", "LINE_CLUSTER"} <= designs


def test_power_labels_follow_intervals(o4_ro):
    rows = o4_ro.execute("SELECT pair_id, power_label, ci_low, ci_high, detectable_half_width FROM paired_differences "
                         "WHERE scope = 'POOLED' AND weighting = 'INTERVAL'").fetchall()
    for r in rows:
        label = r["power_label"]
        assert label in ("RESOLVED", "UNRESOLVED", "IDENTICAL")
        if label == "IDENTICAL":
            assert r["ci_low"] is None
        elif label == "RESOLVED":
            assert r["ci_low"] > 0 or r["ci_high"] < 0
        else:
            assert r["ci_low"] <= 0 <= r["ci_high"]
            assert abs(r["detectable_half_width"] - (r["ci_high"] - r["ci_low"]) / 2) < 1e-12


def test_no_model_refit_tables(o4_ro):
    tables = {r[0] for r in o4_ro.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "training_runs" not in tables and "model_artifacts" not in tables


def test_audit_has_no_failure(o4_ro):
    assert o4_ro.execute("SELECT COUNT(*) FROM evaluation_audit_log WHERE status = 'FAIL'").fetchone()[0] == 0

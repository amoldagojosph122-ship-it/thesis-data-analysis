"""Handoff contract (specification 02, section 11; specification 03, G25 to G27)."""


def test_handoff_forbids_full_data_parameters(o2_ro, receipt_id):
    rows = o2_ro.execute("SELECT full_data_parameters_for_test_folds FROM continuity_handoff_decisions WHERE receipt_id = ?",
                         (receipt_id,)).fetchall()
    assert rows
    assert all(r[0] == 0 for r in rows)


def test_handoff_status_vocabulary(o2_ro, receipt_id):
    rows = o2_ro.execute("SELECT decision_status, candidate_family FROM continuity_handoff_decisions WHERE receipt_id = ?",
                         (receipt_id,)).fetchall()
    assert all(r["decision_status"] in ("PROVISIONAL", "NOT_IDENTIFIABLE", "REJECTED") for r in rows)
    assert all(r["candidate_family"] in ("LATERAL_BETWEEN", "NONE") for r in rows)


def test_all_data_fit_labelled(o2_ro, receipt_id):
    for r in o2_ro.execute("SELECT decision_status, rationale FROM continuity_handoff_decisions WHERE receipt_id = ?",
                           (receipt_id,)).fetchall():
        if r["decision_status"] == "PROVISIONAL":
            assert "exploratory" in r["rationale"]


def test_not_identifiable_handoff_carries_no_parameters(o2_ro, receipt_id):
    for r in o2_ro.execute("SELECT fit_id FROM continuity_handoff_decisions WHERE receipt_id = ? "
                           "AND decision_status = 'NOT_IDENTIFIABLE'", (receipt_id,)).fetchall():
        assert r["fit_id"] is None

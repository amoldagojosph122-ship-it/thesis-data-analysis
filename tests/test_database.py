"""Database contract: source hash, raw immutability, referential integrity, idempotent rebuild, Stage B blocking."""

import hashlib
import sqlite3

import pytest

from kambale import lithology
from kambale.build import build
from kambale.config import RAW_COPY_PATH, SOURCE_PATH


def _conn(path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def test_raw_copy_matches_workbook_hash():
    assert hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest() == hashlib.sha256(RAW_COPY_PATH.read_bytes()).hexdigest()


def test_stored_source_hash_and_counts_match_workbook(built_db):
    conn = _conn(built_db)
    try:
        sha = conn.execute("SELECT sha256 FROM source_files").fetchone()[0]
        assert sha == hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()
        assert conn.execute("SELECT COUNT(*) FROM raw_collars").fetchone()[0] == 71
        assert conn.execute("SELECT COUNT(*) FROM raw_surveys").fetchone()[0] == 71
        assert conn.execute("SELECT COUNT(*) FROM raw_logging").fetchone()[0] == 1910
        assert conn.execute("SELECT COUNT(*) FROM logging_intervals").fetchone()[0] == 1910
        assert conn.execute("SELECT COUNT(*) FROM dataset_versions WHERE status = 'ACTIVE'").fetchone()[0] == 1
    finally:
        conn.close()


def test_integrity_and_foreign_keys(built_db):
    conn = _conn(built_db)
    try:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        orphans = conn.execute("SELECT COUNT(*) FROM logging_intervals li LEFT JOIN holes h "
                               "ON h.dataset_version_id = li.dataset_version_id AND h.hole_id = li.hole_id "
                               "WHERE h.hole_id IS NULL").fetchone()[0]
        assert orphans == 0
    finally:
        conn.close()


@pytest.mark.parametrize("statement", [
    "UPDATE raw_collars SET HoleID = 'X' WHERE raw_collars_id = 1",
    "DELETE FROM raw_logging WHERE raw_logging_id = 1",
    "UPDATE raw_surveys SET dip = 0 WHERE raw_surveys_id = 1",
])
def test_raw_tables_reject_update_and_delete(db_copy, statement):
    conn = _conn(db_copy)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(statement)
    finally:
        conn.close()


def test_identical_rebuild_is_a_noop(built_db):
    tables = ("logging_intervals", "interval_labels", "interval_coordinates", "qaqc_findings")
    conn = _conn(built_db)
    before = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    conn.close()
    summary = build(db_path=built_db, source_path=RAW_COPY_PATH, raw_copy=RAW_COPY_PATH)
    assert summary["status"] == "NOOP_IDENTICAL"
    conn = _conn(built_db)
    try:
        after = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        assert after == before
        assert conn.execute("SELECT COUNT(*) FROM dataset_versions").fetchone()[0] == 1
    finally:
        conn.close()


def test_graphite_rule_cannot_be_approved_without_review(db_copy):
    conn = _conn(db_copy)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="APPROVE_RULE"):
            conn.execute("UPDATE graphite_label_rules SET status = 'APPROVED', approved_by = 'x', "
                         "approved_utc = '2026-11-05T00:00:00Z' WHERE rule_id = 'STRICT_SGS_v1'")
    finally:
        conn.close()


def test_stage_b_contract_tables_reject_inserts(db_copy):
    conn = _conn(db_copy)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="Stage B"):
            conn.execute("INSERT INTO spatial_folds (split_plan_id, fold_label, held_out_group, role) "
                         "VALUES ('p', 'f', 'g', 'OUTER_TEST')")
    finally:
        conn.close()


def test_no_collar_rl_and_all_label_rules_proposed(built_db):
    conn = _conn(built_db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM holes WHERE rl_status = 'PRESENT'").fetchone()[0] == 0
        statuses = {r[0] for r in conn.execute("SELECT status FROM graphite_label_rules")}
        assert statuses == {"PROPOSED"}
    finally:
        conn.close()


def _active_intervals(conn):
    return conn.execute(
        "SELECT interval_key, hole_id, depth_from_m, depth_to_m, rock_code_raw, comment_raw FROM logging_intervals "
        "WHERE dataset_version_id = (SELECT dataset_version_id FROM v_active_version)").fetchall()


def test_lithology_rows_round_trip_the_module(built_db):
    conn = _conn(built_db)
    try:
        legend = dict(conn.execute(
            "SELECT code, description FROM geological_code_dictionary WHERE code_domain = 'RockType' "
            "AND dataset_version_id = (SELECT dataset_version_id FROM v_active_version)").fetchall())
        intervals = [{"interval_key": k, "hole_id": h, "depth_from": f, "depth_to": t, "rock_code": c,
                      "comment": (cm or "").strip()} for k, h, f, t, c, cm in _active_intervals(conn)]
        expected = {r["interval_key"]: r for r in lithology.compute(legend, intervals)["interval_rows"]}
        stored = conn.execute("SELECT interval_key, refinement_status, refined_code, base_code, comment_normalised "
                              "FROM v_lithology_refinement").fetchall()
        assert len(stored) == len(expected) == 1910
        for key, status, refined, base, norm in stored:
            e = expected[key]
            assert status == e["refinement_status"], key
            assert (refined or "") == e["refined_code"], key
            assert (base or "") == e["base_code"], key
            assert norm == e["comment_normalised"], key
    finally:
        conn.close()


def test_lithology_counts_and_label_targets_are_unchanged(built_db):
    conn = _conn(built_db)
    try:
        counts = dict(conn.execute(
            "SELECT refinement_status, COUNT(*) FROM v_lithology_refinement GROUP BY refinement_status").fetchall())
        assert sum(counts.values()) == 1910
        assert counts["REFINED"] == 230
        assert counts["REFINED_GENERAL"] == 284
        assert counts["CONFLICT_REVIEW"] == 17
        assert conn.execute("SELECT COUNT(*) FROM v_label_evidence WHERE is_sgs = 1").fetchone()[0] == 529
    finally:
        conn.close()


def test_blank_comments_are_warning_findings_that_need_review(built_db):
    conn = _conn(built_db)
    try:
        active = "(SELECT dataset_version_id FROM v_active_version)"
        rows = conn.execute(
            "SELECT f.severity, r.action FROM qaqc_findings f "
            "JOIN qaqc_resolutions r ON r.finding_id = f.finding_id "
            "WHERE f.check_id = 'QC-COMMENT-MISSING' AND f.entity_type = 'INTERVAL' "
            f"AND f.dataset_version_id = {active}").fetchall()
        assert len(rows) == 6
        assert {r[0] for r in rows} == {"WARNING"}
        assert {r[1] for r in rows} == {"REVIEW_REQUIRED"}
        aggregate = conn.execute(
            "SELECT severity FROM qaqc_findings WHERE check_id = 'QC-COMMENT-MISSING' "
            f"AND entity_type = 'DATASET' AND dataset_version_id = {active}").fetchone()
        assert aggregate[0] == "WARNING"
    finally:
        conn.close()


def test_lithology_rows_carry_the_convention_digest(built_db):
    conn = _conn(built_db)
    try:
        digests = {r[0] for r in conn.execute(
            "SELECT convention_sha256 FROM lithology_refinements "
            "WHERE dataset_version_id = (SELECT dataset_version_id FROM v_active_version)")}
        assert digests == {lithology.convention_sha256()}
    finally:
        conn.close()


def test_design_rule_counts_match_the_review_form_and_earlier_rules_are_unchanged(built_db):
    conn = _conn(built_db)
    try:
        def counts(rule_id):
            return dict(conn.execute(
                "SELECT label_state, COUNT(*) FROM v_label_candidates WHERE rule_id = ? GROUP BY label_state",
                (rule_id,)).fetchall())
        assert counts("DESIGN_8_2_v1") == {"POSITIVE": 524, "NEGATIVE": 1289, "AMBIGUOUS": 81, "UNRESOLVED": 16}
        assert counts("STRICT_SGS_v1") == {"POSITIVE": 529, "NEGATIVE": 1368, "UNRESOLVED": 13}
        assert counts("RECON_2OF3_v1") == {"POSITIVE": 562, "NEGATIVE": 1289, "UNRESOLVED": 59}
        ambiguous_rules = {r[0] for r in conn.execute(
            "SELECT DISTINCT rule_id FROM v_label_candidates WHERE label_state = 'AMBIGUOUS'")}
        assert ambiguous_rules == {"DESIGN_8_2_v1"}
        approved = conn.execute("SELECT COUNT(*) FROM graphite_label_rules WHERE status <> 'PROPOSED'").fetchone()[0]
        assert approved == 0
    finally:
        conn.close()


def test_target_b_outputs_use_the_design_rule(built_db):
    conn = _conn(built_db)
    try:
        totals = ("SELECT ROUND(SUM(design_pos_m), 3), ROUND(SUM(design_ambiguous_m), 3), "
                  "ROUND(SUM(design_unresolved_m), 3) FROM ")
        assert conn.execute(totals + "v_hole_design").fetchone() == (524.0, 81.0, 16.0)
        assert conn.execute(totals + "v_line_design").fetchone() == (524.0, 81.0, 16.0)
        assert conn.execute("SELECT ROUND(SUM(recon_pos_m), 3) FROM v_hole_graphite").fetchone()[0] == 562.0
    finally:
        conn.close()

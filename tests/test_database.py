"""Database contract: source hash, raw immutability, referential integrity, idempotent rebuild, Stage B blocking."""

import hashlib
import sqlite3

import pytest

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
    summary = build(db_path=built_db, source_path=SOURCE_PATH, raw_copy=RAW_COPY_PATH)
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

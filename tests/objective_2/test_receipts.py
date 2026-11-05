"""Receipts, input gates and the read-only upstream (specification 03, G01 to G03; specification 06, section 7)."""

import json
import shutil
import sqlite3

import pytest

from kambale.objective_2 import verify
from kambale.objective_2.config import O2_DB_PATH, UPSTREAM_DB_PATH, sha256_text
from kambale.objective_2.db import connect_upstream_readonly
from kambale.objective_2.importer import IMPORT_QUERY

needs_db = pytest.mark.skipif(not O2_DB_PATH.exists() or not UPSTREAM_DB_PATH.exists(),
                              reason="Objective 1 and Objective 2 databases are required")


@needs_db
def test_receipt_content_hash_matches_upstream(o2_ro, receipt_id):
    stored = o2_ro.execute("SELECT content_sha256, upstream_dataset_version_key FROM source_receipts WHERE receipt_id = ?",
                           (receipt_id,)).fetchone()
    up = connect_upstream_readonly(UPSTREAM_DB_PATH)
    try:
        rows = [dict(r) for r in up.execute(IMPORT_QUERY)]
        version = up.execute("SELECT dataset_version_key FROM v_active_version").fetchone()[0]
    finally:
        up.close()
    canon = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    assert sha256_text(canon) == stored["content_sha256"]
    assert version == stored["upstream_dataset_version_key"]


@needs_db
def test_receipt_mismatch_stops(tmp_path):
    copy = tmp_path / "o2_copy.sqlite"
    shutil.copy(O2_DB_PATH, copy)
    con = sqlite3.connect(copy)
    con.execute("UPDATE source_receipts SET content_sha256 = 'deadbeef'")
    con.commit()
    con.close()
    result = verify.run(o2_path=copy)
    assert result["stopped"]
    assert {g["gate_id"]: g["status"] for g in result["gates"]}["G01"] == "STOP"


@needs_db
def test_unapproved_label_stops(tmp_path):
    copy = tmp_path / "o2_copy.sqlite"
    shutil.copy(O2_DB_PATH, copy)
    con = sqlite3.connect(copy)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE source_receipts SET label_rule_status = 'PROPOSED'")
    con.close()


@needs_db
def test_support_is_one_metre(tmp_path):
    copy = tmp_path / "o2_copy.sqlite"
    shutil.copy(O2_DB_PATH, copy)
    con = sqlite3.connect(copy)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE analysis_observations SET support_length_m = 2.0 WHERE rowid = 1")
    con.close()


@needs_db
def test_absolute_elevation_not_used():
    up = connect_upstream_readonly(UPSTREAM_DB_PATH)
    try:
        assert up.execute("SELECT COUNT(*) FROM v_interval_geometry WHERE z_absolute_m IS NOT NULL").fetchone()[0] == 0
    finally:
        up.close()

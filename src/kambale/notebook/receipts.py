"""Upstream input receipts: the hashes each downstream database recorded when it imported its inputs.

Recorded hashes come from these tables (all read-only):
  O5  input_files(role, path, sha256)             file bytes of the O2, O3, O4 tier 1 and tier 2, thesis and config files
  O2  source_receipts.content_sha256              canonical hash of the Objective 1 interval rows (IMPORT_QUERY)
  O3  source_receipts.content_sha256              same canonical hash of the Objective 1 rows
  O3  source_receipts.o2_content_sha256           content hash of the O2 receipt named by o2_receipt_id
  O4  source_receipts.o1_content_sha256           Objective 1 content hash, equal to the O3 receipt's content hash

Current values: file rows are hashed from the file; content rows are recomputed from the Objective 1 database with the
same query and serialisation the importer used (O2 and O3 query objects are imported from their modules, which do not
touch any database at import time). Objective 4 prediction-snapshot hashes are not recomputed here; they need the full
Objective 4 import logic, and are verified by the Objective 4 gates instead.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pandas as pd

from kambale.config import PROJECT_ROOT
from kambale.notebook.env import sha256_file
from kambale.notebook.paths import DB_PATHS
from kambale.notebook.readonly import connect_ro

COLUMNS = ["objective", "role", "path", "recorded_sha256", "current_sha256", "status", "basis"]


def _content_hash(rows: list[dict]) -> str:
    canonical = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _o1_rows(query: str) -> list[dict]:
    conn = connect_ro(DB_PATHS["o1"])
    try:
        return [dict(r) for r in conn.execute(query)]
    finally:
        conn.close()


def _status(recorded: str | None, current: str | None) -> str:
    if not recorded or not current:
        return "MISSING"
    return "MATCH" if recorded == current else "MISMATCH"


def _row(objective, role, path, recorded, current, basis) -> dict:
    return {"objective": objective, "role": role, "path": path, "recorded_sha256": recorded or "",
            "current_sha256": current or "", "status": _status(recorded, current), "basis": basis}


def _single(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row is not None else None


def _o5_file_rows() -> list[dict]:
    rows = []
    conn = connect_ro(DB_PATHS["o5"])
    try:
        for r in conn.execute("SELECT role, path, sha256 FROM input_files ORDER BY role"):
            path = PROJECT_ROOT / r["path"]
            current = sha256_file(path) if path.exists() else None
            rows.append(_row("O5", r["role"], r["path"], r["sha256"], current, "file bytes"))
    except Exception:
        rows.append(_row("O5", "input_files", DB_PATHS["o5"].name, None, None, "table input_files unreadable"))
    finally:
        conn.close()
    return rows


def _o2_rows() -> list[dict]:
    from kambale.objective_2.importer import IMPORT_QUERY as O2_QUERY
    rows = []
    conn = connect_ro(DB_PATHS["o2"])
    try:
        receipt = _single(conn, "SELECT receipt_id, upstream_path, content_sha256 FROM source_receipts "
                                "ORDER BY receipt_id DESC LIMIT 1")
    finally:
        conn.close()
    if receipt is None:
        return [_row("O2", "o1_snapshot_rows", DB_PATHS["o2"].name, None, None, "no source receipt")]
    current = _content_hash(_o1_rows(O2_QUERY))
    rows.append(_row("O2", "o1_snapshot_rows", receipt["upstream_path"], receipt["content_sha256"], current,
                     "canonical JSON of IMPORT_QUERY rows, recomputed from the Objective 1 database"))
    return rows


def _o3_rows() -> list[dict]:
    from kambale.objective_3.importer import IMPORT_QUERY as O3_QUERY
    rows = []
    conn = connect_ro(DB_PATHS["o3"])
    try:
        receipt = _single(conn, "SELECT receipt_id, upstream_path, content_sha256, o2_receipt_id, o2_content_sha256 "
                                "FROM source_receipts ORDER BY receipt_id DESC LIMIT 1")
    finally:
        conn.close()
    if receipt is None:
        return [_row("O3", "o1_snapshot_rows", DB_PATHS["o3"].name, None, None, "no source receipt")]
    current = _content_hash(_o1_rows(O3_QUERY))
    rows.append(_row("O3", "o1_snapshot_rows", receipt["upstream_path"], receipt["content_sha256"], current,
                     "canonical JSON of IMPORT_QUERY rows, recomputed from the Objective 1 database"))
    conn2 = connect_ro(DB_PATHS["o2"])
    try:
        o2 = _single(conn2, "SELECT content_sha256 FROM source_receipts WHERE receipt_id = ?",
                     (receipt["o2_receipt_id"],))
    except Exception:
        o2 = None
    finally:
        conn2.close()
    rows.append(_row("O3", "o2_receipt_content", DB_PATHS["o2"].name, receipt["o2_content_sha256"],
                     o2["content_sha256"] if o2 else None,
                     f"O2 receipt {receipt['o2_receipt_id']} content hash in the Objective 2 database"))
    return rows


def _o4_rows(key: str, label: str) -> list[dict]:
    conn = connect_ro(DB_PATHS[key])
    try:
        receipt = _single(conn, "SELECT o3_receipt_id, o1_content_sha256 FROM source_receipts "
                                "ORDER BY receipt_id DESC LIMIT 1")
    except Exception:
        receipt = None
    finally:
        conn.close()
    if receipt is None:
        return [_row(label, "o3_receipt_o1_content", DB_PATHS[key].name, None, None, "no source receipt")]
    conn3 = connect_ro(DB_PATHS["o3"])
    try:
        o3 = _single(conn3, "SELECT content_sha256 FROM source_receipts WHERE receipt_id = ?",
                     (receipt["o3_receipt_id"],))
    finally:
        conn3.close()
    return [_row(label, "o3_receipt_o1_content", DB_PATHS["o3"].name, receipt["o1_content_sha256"],
                 o3["content_sha256"] if o3 else None,
                 f"O3 receipt {receipt['o3_receipt_id']} content hash in the Objective 3 database")]


def receipt_check() -> pd.DataFrame:
    """Recorded versus current upstream hashes for every downstream objective. Read-only.

    A MISMATCH means the upstream database or file changed after the downstream stage imported it (for example after
    a later verify run rewrote it). Re-running the downstream import would record the new hash.
    """
    builders = [
        ("O2", _o2_rows),
        ("O3", _o3_rows),
        ("O5", _o5_file_rows),
        ("O4 tier 1", lambda: _o4_rows("o4_t1", "O4 tier 1")),
        ("O4 tier 2", lambda: _o4_rows("o4_t2", "O4 tier 2")),
    ]
    rows: list[dict] = []
    for label, builder in builders:
        try:
            rows.extend(builder())
        except Exception as exc:  # report the failure in the table instead of hiding it
            rows.append(_row(label, "error", "", None, None, f"{type(exc).__name__}: {exc}"))
    return pd.DataFrame(rows, columns=COLUMNS)

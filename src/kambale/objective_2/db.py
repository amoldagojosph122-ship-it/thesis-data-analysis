"""Connections to the Objective 2 database and to the Objective 1 database (read only)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kambale.objective_2 import O2_SCHEMA_VERSION
from kambale.objective_2.config import O2_DB_PATH, O2_SCHEMA_PATH, utc_now


def connect_o2(path: Path = O2_DB_PATH) -> sqlite3.Connection:
    """Open (and create when missing) the Objective 2 database with the schema applied."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_schema(conn)
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Apply the DDL (idempotent: every statement uses IF NOT EXISTS)."""
    conn.executescript(O2_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT OR IGNORE INTO schema_version (version_id, schema_name, applied_utc) VALUES (1, ?, ?)",
                 (O2_SCHEMA_VERSION, utc_now()))


def connect_upstream_readonly(path: Path) -> sqlite3.Connection:
    """Open the Objective 1 database with a read-only URI. No write is possible through this connection."""
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn

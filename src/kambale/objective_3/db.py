"""Connections to the Objective 3 database and to the read-only Objective 1 and Objective 2 databases."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kambale.objective_3 import O3_SCHEMA_VERSION
from kambale.objective_3.config import O3_DB_PATH, O3_SCHEMA_PATH, utc_now


def connect_o3(path: Path | None = None) -> sqlite3.Connection:
    """Open (and create when missing) the Objective 3 database with the schema applied."""
    path = path or O3_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_schema(conn)
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Apply the DDL (idempotent: every statement uses IF NOT EXISTS)."""
    conn.executescript(O3_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT OR IGNORE INTO schema_version (version_id, schema_name, applied_utc) VALUES (1, ?, ?)",
                 (O3_SCHEMA_VERSION, utc_now()))


def connect_readonly(path: Path) -> sqlite3.Connection:
    """Open a database with a read-only URI. No write is possible through this connection."""
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn

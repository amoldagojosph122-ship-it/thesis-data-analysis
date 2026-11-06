"""Connections to the Objective 4 database and to the read-only upstream databases."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kambale.objective_4 import O4_SCHEMA_VERSION
from kambale.objective_4.config import O4_DB_PATH, O4_SCHEMA_PATH, utc_now


def connect_o4(path: Path | None = None) -> sqlite3.Connection:
    path = path or O4_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    apply_schema(conn)
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(O4_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT OR IGNORE INTO schema_version (version_id, schema_name, applied_utc) VALUES (1, ?, ?)",
                 (O4_SCHEMA_VERSION, utc_now()))


def connect_readonly(path: Path) -> sqlite3.Connection:
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn

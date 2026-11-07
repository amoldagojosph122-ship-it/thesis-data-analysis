"""Read-only access to the analysis databases.

Connections use a file: URI with mode=ro, so SQLite refuses every write. The notebook reads results through these
helpers only.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from kambale.notebook.paths import key_to_path


def connect_ro(key_or_path) -> sqlite3.Connection:
    """Open a database read-only (URI mode=ro, immutable=0) with sqlite3.Row rows."""
    path = key_to_path(key_or_path).resolve()
    uri = path.as_uri() + "?mode=ro&immutable=0"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def query(key, sql: str, params=()) -> pd.DataFrame:
    """Run a SELECT against a database key or path and return the result as a DataFrame."""
    conn = connect_ro(key)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def list_tables(key) -> list[str]:
    """Names of the ordinary tables in a database, sorted."""
    conn = connect_ro(key)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
        return [r["name"] for r in rows]
    finally:
        conn.close()


def sqlite_file_exists(key_or_path) -> bool:
    return Path(key_to_path(key_or_path)).exists()

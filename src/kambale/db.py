"""SQLite connection handling and forward-only migrations.

Every connection enables foreign keys. Migrations are applied in filename order, each inside one
transaction, and each applied file's SHA-256 is recorded so that an edited applied migration is detected.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from kambale.config import DB_PATH, MIGRATIONS_DIR


class MigrationError(RuntimeError):
    """Raised when a migration cannot be applied or an applied migration has changed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def connect(path: Path | str = DB_PATH, *, read_only: bool = False) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced and autocommit disabled (explicit transactions)."""
    path = Path(path)
    if read_only:
        uri = f"file:{path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=60, isolation_level=None)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=60, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations. Returns the list of versions applied in this call."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version TEXT PRIMARY KEY, name TEXT NOT NULL, sha256 TEXT NOT NULL, applied_utc TEXT NOT NULL)"
    )
    applied_now: list[str] = []
    recorded = {r["version"]: r["sha256"] for r in conn.execute("SELECT version, sha256 FROM schema_migrations")}
    for path in sorted(Path(migrations_dir).glob("[0-9][0-9][0-9][0-9]_*.sql")):
        version = path.name[:4]
        text = path.read_text(encoding="utf-8")
        digest = sha256_text(text)
        if version in recorded:
            if recorded[version] != digest:
                raise MigrationError(f"applied migration {path.name} has changed since it was recorded")
            continue
        script = (
            "BEGIN;\n"
            + text
            + f"\nINSERT INTO schema_migrations (version, name, sha256, applied_utc) VALUES "
            f"('{version}', '{path.name}', '{digest}', '{utc_now()}');\nCOMMIT;"
        )
        try:
            conn.executescript(script)
        except sqlite3.Error as exc:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise MigrationError(f"{path.name} failed: {exc}") from exc
        applied_now.append(version)
    return applied_now


def fk_violations(conn: sqlite3.Connection) -> list[tuple]:
    return [tuple(r) for r in conn.execute("PRAGMA foreign_key_check").fetchall()]


def integrity(conn: sqlite3.Connection) -> str:
    return conn.execute("PRAGMA integrity_check").fetchone()[0]

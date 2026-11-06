"""Paths, predeclared configuration and small helpers shared by the Objective 4 modules."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from kambale.config import CONFIG_DIR, PROJECT_ROOT, DB_PATH as O1_DB_PATH

O4_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj4_validation.sqlite"
O4_CONFIG_PATH = CONFIG_DIR / "objective_4" / "evaluation_config.yaml"
O4_SCHEMA_PATH = PROJECT_ROOT / "sql" / "objective_4" / "schema.sql"
O4_SQL_DIR = PROJECT_ROOT / "sql" / "objective_4"
O4_REPORT_DIR = PROJECT_ROOT / "reports" / "objective_4"
O4_FIGURE_DIR = PROJECT_ROOT / "figures" / "objective_4"
O4_TABLE_DIR = PROJECT_ROOT / "tables" / "objective_4"
O3_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj3_models.sqlite"
O2_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj2_spatial.sqlite"
UPSTREAM_DB_PATH = O1_DB_PATH


class StopError(RuntimeError):
    """A STOP gate failed. The run is halted and nothing past the failing gate is written."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_config(path: Path | None = None) -> tuple[dict, str]:
    raw = (path or O4_CONFIG_PATH).read_bytes()
    return yaml.safe_load(raw.decode("utf-8")), sha256_bytes(raw)


def code_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
                             text=True, timeout=30, check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None

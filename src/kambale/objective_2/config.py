"""Paths, predeclared configuration and small helpers shared by the Objective 2 modules."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from kambale.config import CONFIG_DIR, PROJECT_ROOT, DB_PATH as O1_DB_PATH

O2_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj2_spatial.sqlite"
O2_CONFIG_PATH = CONFIG_DIR / "objective_2" / "variogram_config.yaml"
O2_SCHEMA_PATH = PROJECT_ROOT / "sql" / "objective_2" / "schema.sql"
O2_REPORT_DIR = PROJECT_ROOT / "reports" / "objective_2"
O2_FIGURE_DIR = PROJECT_ROOT / "figures" / "objective_2"
O2_TABLE_DIR = PROJECT_ROOT / "tables" / "objective_2"
O2_SQL_DIR = PROJECT_ROOT / "sql" / "objective_2"
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


def load_config(path: Path = O2_CONFIG_PATH) -> tuple[dict, str]:
    """Return the parsed configuration and the SHA-256 of its exact bytes."""
    raw = path.read_bytes()
    return yaml.safe_load(raw.decode("utf-8")), sha256_bytes(raw)


def code_commit() -> str | None:
    """Short git commit of the checkout, or None when git is unavailable."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
                             text=True, timeout=30, check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None

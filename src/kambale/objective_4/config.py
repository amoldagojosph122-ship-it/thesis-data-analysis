"""Paths, predeclared configuration and small helpers shared by the Objective 4 modules.

The active evaluation tier is read from the environment variable KAMBALE_O4_TIER. The command-line entry point sets it
from --tier before any stage module is imported, so every module resolves the same config file, database and output
directories. Tier 1 is TIER_1_EXTRAPOLATION (leave one drill line out); tier 2 is TIER_2_INTERPOLATION (interleaved holes).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from kambale.config import CONFIG_DIR, PROJECT_ROOT, DB_PATH as O1_DB_PATH

TIER_ENV = "KAMBALE_O4_TIER"
TIER_FILES = {"1": "evaluation_config.yaml", "2": "evaluation_config_tier2.yaml"}
TIER_TOKENS = {"1": "TIER_1_EXTRAPOLATION", "2": "TIER_2_INTERPOLATION"}
# The fold unit declared in each config must be produced by the matching Objective 3 split method.
FOLD_UNIT_METHOD = {"HELD_OUT_LINE": "LEAVE_ONE_DRILL_LINE_OUT", "INTERLEAVED_HOLE_FOLD": "INTERLEAVED_HOLES_WITHIN_LINE"}

O3_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj3_models.sqlite"
O2_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj2_spatial.sqlite"
UPSTREAM_DB_PATH = O1_DB_PATH
O4_SCHEMA_PATH = PROJECT_ROOT / "sql" / "objective_4" / "schema.sql"
O4_SQL_DIR = PROJECT_ROOT / "sql" / "objective_4"


class StopError(RuntimeError):
    """A STOP gate failed. The run is halted and nothing past the failing gate is written."""


def active_tier() -> str:
    tier = (os.environ.get(TIER_ENV) or "1").strip()
    if tier not in TIER_FILES:
        raise StopError(f"unknown evaluation tier {tier!r}; expected 1 or 2")
    return tier


def resolve_paths(tier: str) -> dict:
    """Config file, database and output directories for one tier, read from the config's paths block."""
    if tier not in TIER_FILES:
        raise StopError(f"unknown evaluation tier {tier!r}; expected 1 or 2")
    config_path = CONFIG_DIR / "objective_4" / TIER_FILES[tier]
    config = yaml.safe_load(config_path.read_bytes().decode("utf-8"))
    if config.get("tier") != TIER_TOKENS[tier]:
        raise StopError(f"{config_path.name} declares tier {config.get('tier')!r}, expected {TIER_TOKENS[tier]!r}")
    paths = config["paths"]
    subdir = str(paths.get("output_subdir") or "").strip()
    return {
        "tier": tier,
        "config_path": config_path,
        "config_version": config["config_version"],
        "split_plan_id": paths["o3_split_plan_id"],
        "database": PROJECT_ROOT / paths["database"],
        "output_subdir": subdir,
        "figure_dir": PROJECT_ROOT / "figures" / "objective_4" / subdir,
        "table_dir": PROJECT_ROOT / "tables" / "objective_4" / subdir,
        "report_dir": PROJECT_ROOT / "reports" / "objective_4" / subdir,
    }


TIER = active_tier()
_RESOLVED = resolve_paths(TIER)
O4_CONFIG_PATH = _RESOLVED["config_path"]
O4_DB_PATH = _RESOLVED["database"]
O4_REPORT_DIR = _RESOLVED["report_dir"]
O4_FIGURE_DIR = _RESOLVED["figure_dir"]
O4_TABLE_DIR = _RESOLVED["table_dir"]
O4_SPLIT_PLAN_ID = _RESOLVED["split_plan_id"]


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

"""Paths, predeclared configuration and helpers shared by the Objective 5 modules."""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from kambale.config import CONFIG_DIR, PROJECT_ROOT, DB_PATH as THESIS_DB_PATH

O5_CONFIG_PATH = CONFIG_DIR / "objective_5" / "uncertainty_config.yaml"
O3_CONFIG_PATH = CONFIG_DIR / "objective_3" / "model_config.yaml"
O5_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj5_uncertainty.sqlite"
O3_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj3_models.sqlite"
O2_DB_PATH = PROJECT_ROOT / "database" / "kambale_obj2_spatial.sqlite"
O5_SCHEMA_PATH = PROJECT_ROOT / "sql" / "objective_5" / "schema.sql"
O5_SQL_DIR = PROJECT_ROOT / "sql" / "objective_5"
O5_REPORT_DIR = PROJECT_ROOT / "reports" / "objective_5"
O5_ARTIFACT_DIR = O5_REPORT_DIR / "artifacts"
O5_FIGURE_DIR = PROJECT_ROOT / "figures" / "objective_5"
O5_TABLE_DIR = PROJECT_ROOT / "tables" / "objective_5"

# The grid origin rule in the configuration says "expanded by 100 m on every side". The configuration has no numeric key for
# it, so the value is held here and reported as a deviation.
GRID_MARGIN_M = 100.0

INTERPOLATION = "INTERPOLATION"
EXTRAPOLATION = "EXTRAPOLATION"
NO_SUPPORT = "NO_SUPPORT"
TIER_OF_ZONE = {INTERPOLATION: "TIER_2_INTERPOLATION", EXTRAPOLATION: "TIER_1_EXTRAPOLATION", NO_SUPPORT: None}

CLASS_PRESENT = "CONFIDENT_PRESENT"
CLASS_ABSENT = "CONFIDENT_ABSENT"
CLASS_UNCERTAIN = "UNCERTAIN"
CLASS_NO_SUPPORT = "NO_SUPPORT"


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
    """Parsed configuration and the SHA-256 of its exact bytes."""
    raw = (path or O5_CONFIG_PATH).read_bytes()
    return yaml.safe_load(raw.decode("utf-8")), sha256_bytes(raw)


def rel(path: Path) -> str:
    return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()


def code_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, capture_output=True,
                             text=True, timeout=30, check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def zone_limits(cfg: dict) -> dict:
    """Maximum lateral distance per zone, from the configuration's support_zones block (NO_SUPPORT is open ended)."""
    out = {}
    for z in cfg["support_zones"]["zones"]:
        out[z["zone"]] = None if z["max_distance_m"] is None else float(z["max_distance_m"])
    return out

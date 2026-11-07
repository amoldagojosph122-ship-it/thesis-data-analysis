"""Locations of the six analysis databases, the per-objective output folders and the live configuration files.

Objective 1 outputs: figures F01-F04 are in figures/objective_1, figures F05-F09 are in figures/objective_2
(the Objective 1 registry renders them there); tables T01, T02 and T04 are in tables/objective_1 and T03 is in
tables/objective_2. Objective 4 writes tier outputs to tier_1 and tier_2 subfolders.
"""

from __future__ import annotations

from pathlib import Path

from kambale.config import CONFIG_DIR, FIGURES_DIR, PROJECT_ROOT, REPORTS_DIR, TABLES_DIR

DATABASE_DIR = PROJECT_ROOT / "database"

DB_PATHS: dict[str, Path] = {
    "o1": DATABASE_DIR / "kambale_thesis.sqlite",
    "o2": DATABASE_DIR / "kambale_obj2_spatial.sqlite",
    "o3": DATABASE_DIR / "kambale_obj3_models.sqlite",
    "o4_t1": DATABASE_DIR / "kambale_obj4_validation.sqlite",
    "o4_t2": DATABASE_DIR / "kambale_obj4_validation_tier2.sqlite",
    "o5": DATABASE_DIR / "kambale_obj5_uncertainty.sqlite",
}

OUTPUT_DIRS: dict[str, dict[str, Path]] = {
    "o1": {"figures": FIGURES_DIR / "objective_1", "tables": TABLES_DIR / "objective_1", "reports": REPORTS_DIR},
    "o2": {"figures": FIGURES_DIR / "objective_2", "tables": TABLES_DIR / "objective_2",
           "reports": REPORTS_DIR / "objective_2"},
    "o3": {"figures": FIGURES_DIR / "objective_3", "tables": TABLES_DIR / "objective_3",
           "reports": REPORTS_DIR / "objective_3"},
    "o4_t1": {"figures": FIGURES_DIR / "objective_4" / "tier_1", "tables": TABLES_DIR / "objective_4" / "tier_1",
              "reports": REPORTS_DIR / "objective_4" / "tier_1"},
    "o4_t2": {"figures": FIGURES_DIR / "objective_4" / "tier_2", "tables": TABLES_DIR / "objective_4" / "tier_2",
              "reports": REPORTS_DIR / "objective_4" / "tier_2"},
    "o5": {"figures": FIGURES_DIR / "objective_5", "tables": TABLES_DIR / "objective_5",
           "reports": REPORTS_DIR / "objective_5"},
}

# Objective 1 writes into two figure folders and two table folders (see module docstring).
O1_FIGURE_FOLDERS = (FIGURES_DIR / "objective_1", FIGURES_DIR / "objective_2")
O1_TABLE_FOLDERS = (TABLES_DIR / "objective_1", TABLES_DIR / "objective_2")

CONFIG_FILES: dict[str, list[Path]] = {
    "o1": [],
    "o2": [
        CONFIG_DIR / "objective_2" / "variogram_config.yaml",
        CONFIG_DIR / "objective_2" / "extension_config_O2-CFG-2026.11.05-3.yaml",
        CONFIG_DIR / "objective_2" / "weathering_config_O2-CFG-2026.11.06-5.yaml",
        CONFIG_DIR / "objective_2" / "structural_config_O2-CFG-2026.11.06-6.yaml",
    ],
    "o3": [CONFIG_DIR / "objective_3" / "model_config.yaml"],
    "o4_t1": [CONFIG_DIR / "objective_4" / "evaluation_config.yaml"],
    "o4_t2": [CONFIG_DIR / "objective_4" / "evaluation_config_tier2.yaml"],
    "o5": [CONFIG_DIR / "objective_5" / "uncertainty_config.yaml"],
}

OBJECTIVE_LABELS: dict[str, str] = {
    "o1": "O1", "o2": "O2", "o3": "O3", "o4_t1": "O4 tier 1", "o4_t2": "O4 tier 2", "o5": "O5",
}


def key_to_path(key_or_path) -> Path:
    """Database path for a key such as 'o2', or the path itself when a Path or other string is given."""
    if isinstance(key_or_path, str) and key_or_path in DB_PATHS:
        return DB_PATHS[key_or_path]
    return Path(key_or_path)

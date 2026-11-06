"""Tier path resolution and command-line tier handling (no database)."""

import pytest

from kambale.objective_4 import __main__ as entry
from kambale.objective_4.config import PROJECT_ROOT, StopError, resolve_paths, tier_stem


def test_tier_1_paths_are_separate():
    p = resolve_paths("1")
    assert p["database"] == PROJECT_ROOT / "database" / "kambale_obj4_validation.sqlite"
    assert p["figure_dir"] == PROJECT_ROOT / "figures" / "objective_4" / "tier_1"
    assert p["table_dir"] == PROJECT_ROOT / "tables" / "objective_4" / "tier_1"
    assert p["report_dir"] == PROJECT_ROOT / "reports" / "objective_4" / "tier_1"
    assert p["split_plan_id"] == "O3-SPLIT-LODO-1"
    assert p["config_path"].name == "evaluation_config.yaml"
    assert p["config_version"] == "O4-CFG-2026.11.06-3"


def test_tier_stem_is_suffixed_by_tier():
    assert tier_stem("O4_F01_holdout_coverage", "1") == "O4_F01_holdout_coverage_tier1"
    assert tier_stem("O4_T01_evaluation_summary", "2") == "O4_T01_evaluation_summary_tier2"


def test_tier_2_paths_are_separate():
    p = resolve_paths("2")
    assert p["database"] == PROJECT_ROOT / "database" / "kambale_obj4_validation_tier2.sqlite"
    assert p["figure_dir"] == PROJECT_ROOT / "figures" / "objective_4" / "tier_2"
    assert p["table_dir"] == PROJECT_ROOT / "tables" / "objective_4" / "tier_2"
    assert p["report_dir"] == PROJECT_ROOT / "reports" / "objective_4" / "tier_2"
    assert p["split_plan_id"] == "O3-SPLIT-HOLE-IL-2"
    assert p["config_version"] == "O4-CFG-2026.11.06-2T2"


def test_unknown_tier_is_rejected():
    with pytest.raises(StopError):
        resolve_paths("3")


def test_cli_rejects_unknown_tier_before_touching_environment(monkeypatch):
    monkeypatch.delenv("KAMBALE_O4_TIER", raising=False)
    with pytest.raises(SystemExit):
        entry.main(["all", "--tier", "3"])
    import os
    assert "KAMBALE_O4_TIER" not in os.environ

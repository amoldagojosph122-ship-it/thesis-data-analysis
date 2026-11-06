"""Fast tests for kambale.notebook helpers. The full gates and reproduce pipelines are not run here."""

import sqlite3

import pandas as pd
import pytest

from kambale.notebook import env, gates, paths, readonly, receipts
from kambale.notebook._copy import is_excluded
from kambale.notebook.reproduce import compare_tables, is_volatile


def test_db_paths_keys_and_names():
    assert set(paths.DB_PATHS) == {"o1", "o2", "o3", "o4_t1", "o4_t2", "o5"}
    assert paths.DB_PATHS["o1"].name == "kambale_thesis.sqlite"
    assert paths.DB_PATHS["o2"].name == "kambale_obj2_spatial.sqlite"
    assert paths.DB_PATHS["o3"].name == "kambale_obj3_models.sqlite"
    assert paths.DB_PATHS["o4_t1"].name == "kambale_obj4_validation.sqlite"
    assert paths.DB_PATHS["o4_t2"].name == "kambale_obj4_validation_tier2.sqlite"
    assert paths.DB_PATHS["o5"].name == "kambale_obj5_uncertainty.sqlite"


def test_output_dirs_and_config_files_cover_every_objective():
    assert set(paths.OUTPUT_DIRS) == set(paths.DB_PATHS)
    for key, folders in paths.OUTPUT_DIRS.items():
        assert set(folders) == {"figures", "tables", "reports"}, key
    assert paths.OUTPUT_DIRS["o4_t1"]["figures"].name == "tier_1"
    assert paths.OUTPUT_DIRS["o4_t2"]["tables"].name == "tier_2"
    assert paths.CONFIG_FILES["o1"] == []
    assert len(paths.CONFIG_FILES["o2"]) == 4
    assert paths.CONFIG_FILES["o4_t2"][0].name == "evaluation_config_tier2.yaml"


def test_connect_ro_refuses_writes(tmp_path):
    target = tmp_path / "small.sqlite"
    conn = sqlite3.connect(target)
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.commit()
    conn.close()
    ro = readonly.connect_ro(target)
    try:
        with pytest.raises(sqlite3.OperationalError):
            ro.execute("INSERT INTO t (x) VALUES (1)")
    finally:
        ro.close()


def test_query_returns_dataframe_and_lists_tables():
    frame = readonly.query("o1", "SELECT 1 AS x")
    assert isinstance(frame, pd.DataFrame)
    assert frame["x"].tolist() == [1]
    assert "validation_test_results" in readonly.list_tables("o1")


def test_config_receipts_one_row_per_live_config():
    frame = env.config_receipts()
    expected = sum(len(files) for files in paths.CONFIG_FILES.values())
    assert len(frame) == expected
    assert (frame["config_version"].astype(str).str.len() > 0).all()
    assert set(frame["objective"]) == {"O2", "O3", "O4 tier 1", "O4 tier 2", "O5"}


def test_environment_summary_has_items():
    frame = env.environment_summary()
    assert list(frame.columns) == ["item", "value"]
    assert "python version" in set(frame["item"])


def test_manifest_parser_reads_table_rows():
    text = ("| File | Role | Bytes | SHA-256 |\n|---|---|---:|---|\n"
            "| kambale_obj3_models.sqlite | Objective 3 | 26488832 | abc123 |\n"
            "| kambale_thesis.sqlite.bak | Stage A | 10 | def456 |\n"
            "| Not a row | text | x | y |\n")
    rows = env._parse_manifest(text)
    assert [r["file"] for r in rows] == ["kambale_obj3_models.sqlite", "kambale_thesis.sqlite.bak"]
    assert rows[0]["bytes"] == 26488832


def test_manifest_check_covers_every_listed_file():
    frame = env.database_manifest_check()
    assert len(frame) >= 6
    assert set(frame["status"]) <= {"MATCH", "CHANGED_SINCE_MANIFEST", "MISSING"}


def test_receipt_check_runs_and_has_expected_columns():
    frame = receipts.receipt_check()
    assert list(frame.columns) == ["objective", "role", "path", "recorded_sha256", "current_sha256", "status", "basis"]
    assert len(frame) > 0
    assert set(frame["status"]) <= {"MATCH", "MISMATCH", "MISSING"}


def test_volatile_classifier():
    assert is_volatile("created_utc")
    assert is_volatile("sha256")
    assert is_volatile("run_path")
    assert is_volatile("elapsed_seconds")
    assert not is_volatile("estimate")
    assert not is_volatile("probability")


def test_compare_tables_identical_volatile_and_different():
    base = pd.DataFrame({"hole": ["H1", "H2"], "estimate": [0.1234567890123, 0.5], "created_utc": ["a", "b"]})
    same = base.copy()
    assert compare_tables(base, same) == ("IDENTICAL", [])

    stamp = base.assign(created_utc=["x", "y"])
    assert compare_tables(base, stamp) == ("IDENTICAL_EXCEPT_VOLATILE", ["created_utc"])

    shifted = base.assign(estimate=[0.1234567890123, 0.6])
    status, columns = compare_tables(base, shifted)
    assert status == "DIFFERENT" and columns == ["estimate"]

    tiny = base.assign(estimate=[0.1234567890123 * (1 + 1e-12), 0.5])
    assert compare_tables(base, tiny)[0] == "IDENTICAL"

    fewer = base.iloc[:1]
    assert compare_tables(base, fewer) == ("DIFFERENT", ["ROW_COUNT"])

    renamed = base.rename(columns={"hole": "hole_id"})
    status, columns = compare_tables(base, renamed)
    assert status == "DIFFERENT" and "hole" in columns and "hole_id" in columns


def test_copy_exclusion_rules():
    assert is_excluded(".git")
    assert is_excluded(".git/HEAD")
    assert is_excluded("graphify-out/GRAPH_REPORT.md")
    assert is_excluded("src/kambale/__pycache__/cli.cpython-314.pyc")
    assert is_excluded(".pytest_cache/v/cache")
    assert is_excluded("notebooks/output/results.html")
    assert is_excluded("minerals-16-01060-v2.pdf")
    assert is_excluded("minerals-16-01060-s001.zip")
    assert not is_excluded("notebooks/results.ipynb")
    assert not is_excluded("figures/objective_1/F01_collar_plan.pdf")
    assert not is_excluded("database/kambale_thesis.sqlite")


def test_parse_json_finds_the_result_object():
    stdout = "warning line\n{\n  \"verify\": {\"run_id\": 7, \"stopped\": false}\n}\n"
    assert gates._parse_json(stdout) == {"verify": {"run_id": 7, "stopped": False}}
    assert gates._parse_json("no json here") is None

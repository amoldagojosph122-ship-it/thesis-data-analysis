"""Figure and table renderers, registries and formatting (specification 06, sections 4 and 5; gates G28, G29)."""

import pytest

from kambale.objective_2 import figures, tables


def test_not_supported_entries():
    with pytest.raises(figures.NotSupported):
        figures._pair_support({"pair_support": [], "minimum_pairs": []}, {"receipt_id": 1})
    with pytest.raises(figures.NotSupported):
        figures._azimuth({"azimuth_bins": [], "marginal_variance": []}, {"receipt_id": 1})


def test_not_supported_registry_rows_state_a_reason(o2_ro):
    rows = o2_ro.execute("SELECT figure_id, reason FROM figure_registry WHERE status = 'NOT_SUPPORTED'").fetchall()
    assert all(r["reason"] for r in rows)


def test_query_names_are_parsed(tmp_path):
    path = tmp_path / "query.sql"
    path.write_text("-- header comment\n-- name: first\nSELECT 1;\n-- name: second\nSELECT 2;\n", encoding="utf-8")
    queries = figures.load_queries(path)
    assert list(queries) == ["first", "second"]
    assert "SELECT 1" in queries["first"]


def test_table_cells_are_formatted_deterministically():
    assert tables._cell(0.2870) == "0.287"
    assert tables._cell(1111930.0) == "1111930"
    assert tables._cell(None) == ""
    assert tables._cell(3) == "3"


def test_query_registry_complete(o2_ro):
    missing_fig = o2_ro.execute("SELECT COUNT(*) FROM figure_registry f WHERE NOT EXISTS (SELECT 1 FROM figure_query_registry q "
                                "WHERE q.figure_id = f.figure_id)").fetchone()[0]
    missing_tab = o2_ro.execute("SELECT COUNT(*) FROM table_registry t WHERE NOT EXISTS (SELECT 1 FROM table_query_registry q "
                                "WHERE q.table_id = t.table_id)").fetchone()[0]
    assert missing_fig == 0 and missing_tab == 0

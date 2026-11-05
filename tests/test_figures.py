"""Figure provenance: SQL-only rendering, manifest hashes match files on disk, reruns are byte-identical."""

import hashlib
import re
import sqlite3

from kambale.config import DB_PATH, PROJECT_ROOT, SQL_FIGURES_DIR

SRC = PROJECT_ROOT / "src" / "kambale"


def test_figure_code_never_touches_the_workbook_or_shapefile():
    text = (SRC / "figures.py").read_text(encoding="utf-8") + (SRC / "registry.py").read_text(encoding="utf-8")
    for forbidden in ("openpyxl", "read_workbook", "geopandas", "read_file", "REGIONAL_SHP", "RAW_COPY"):
        assert forbidden not in text, forbidden


def test_figure_sql_has_no_select_star_and_no_raw_logging_joins():
    for path in SQL_FIGURES_DIR.glob("*.sql"):
        body = re.sub(r"--.*", "", path.read_text(encoding="utf-8"))
        assert not re.search(r"SELECT\s+\*", body, re.IGNORECASE), path.name
        if path.name != "F05_missing_codes.sql":
            assert not re.search(r"\blogging_intervals\b", body), path.name


def test_manifest_hashes_match_files():
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("SELECT figure_id, output_path, output_sha256 FROM figure_export_manifest").fetchall()
    finally:
        conn.close()
    assert rows, "no figure outputs registered; run `kambale plot --all` first"
    for figure_id, rel, digest in rows:
        path = PROJECT_ROOT / rel
        assert path.exists(), rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (figure_id, rel)


def test_rerender_is_byte_identical(built_db, tmp_path, monkeypatch):
    from kambale import registry
    from kambale.registry import render_figures

    # Render into a temporary folder, so the test never rewrites tracked figures in the project tree.
    monkeypatch.setattr(registry, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(registry, "FIGURES_DIR", tmp_path / "figures")

    def manifest_hashes():
        conn = sqlite3.connect(built_db)
        try:
            return dict(conn.execute("SELECT output_path, output_sha256 FROM figure_export_manifest "
                                     "WHERE figure_id = 'F06'").fetchall())
        finally:
            conn.close()

    render_figures(built_db, ["F06"])
    first = manifest_hashes()
    render_figures(built_db, ["F06"])
    second = manifest_hashes()
    assert first and first == second


def test_deferred_items_have_no_outputs():
    conn = sqlite3.connect(DB_PATH)
    try:
        deferred = conn.execute("SELECT COUNT(*) FROM figure_registry WHERE stage_status = 'DEFERRED'").fetchone()[0]
        deferred_out = conn.execute("SELECT COUNT(*) FROM figure_export_manifest m JOIN figure_registry f "
                                    "ON f.figure_id = m.figure_id WHERE f.stage_status = 'DEFERRED'").fetchone()[0]
    finally:
        conn.close()
    assert deferred >= 10
    assert deferred_out == 0

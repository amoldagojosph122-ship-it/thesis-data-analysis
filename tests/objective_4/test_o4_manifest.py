"""Manifest, artifact and SQL provenance checks on the built Objective 4 database."""

import sqlite3
from pathlib import Path

from kambale.objective_4.config import O4_FIGURE_DIR, O4_TABLE_DIR, PROJECT_ROOT, sha256_file
from kambale.objective_4.figures import FIGURES
from kambale.objective_4.tables import TABLES


def test_figures_and_tables_exist(o4_ro):
    for r in o4_ro.execute("SELECT figure_id, status FROM figure_registry").fetchall():
        if r["status"] != "GENERATED":
            continue
        stem = FIGURES[r["figure_id"]][1]
        for ext in ("svg", "pdf", "png"):
            assert (O4_FIGURE_DIR / f"{stem}.{ext}").exists()
        assert o4_ro.execute("SELECT COUNT(*) FROM figure_sql_registry WHERE figure_id = ?",
                             (r["figure_id"],)).fetchone()[0] > 0
    for r in o4_ro.execute("SELECT table_id, status FROM table_registry").fetchall():
        if r["status"] != "GENERATED":
            continue
        stem = TABLES[r["table_id"]][1]
        for ext in ("csv", "md", "tex"):
            assert (O4_TABLE_DIR / f"{stem}.{ext}").exists()
        assert o4_ro.execute("SELECT COUNT(*) FROM table_sql_registry WHERE table_id = ?",
                             (r["table_id"],)).fetchone()[0] > 0


def test_registered_sql_hashes(o4_ro):
    for table in ("figure_sql_registry", "table_sql_registry"):
        for r in o4_ro.execute(f"SELECT sql_path, sql_sha256 FROM {table}").fetchall():
            path = Path(r["sql_path"])
            assert path.exists() and sha256_file(path) == r["sql_sha256"]


def test_export_manifest_hashes(o4_ro):
    rows = o4_ro.execute("SELECT artifact_path, sha256 FROM export_manifests").fetchall()
    assert rows
    for r in rows:
        path = Path(r["artifact_path"])
        assert path.exists() and sha256_file(path) == r["sha256"]


def test_manifest_lists_generated_figures():
    from kambale.objective_4.config import O4_REPORT_DIR
    manifest = O4_REPORT_DIR / "FIGURE_MANIFEST.csv"
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    for fid in ("O4-F01", "O4-F02", "O4-F03", "O4-F04", "O4-F05", "O4-F06", "O4-F07"):
        assert fid in text

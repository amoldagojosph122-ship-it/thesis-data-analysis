"""Manifest, artifact and query-provenance checks on the built database."""

from pathlib import Path

from kambale.objective_3.config import O3_FIGURE_DIR, O3_TABLE_DIR, PROJECT_ROOT, sha256_file
from kambale.objective_3.figures import FIGURES
from kambale.objective_3.tables import TABLES


def test_model_artifacts_match_files(o3_ro):  # G15
    rows = o3_ro.execute("SELECT artifact_path, artifact_sha256 FROM model_artifacts").fetchall()
    assert rows
    for r in rows:
        path = PROJECT_ROOT / r["artifact_path"]
        assert path.exists() and sha256_file(path) == r["artifact_sha256"]


def test_generated_figures_exist(o3_ro):  # G16
    rows = o3_ro.execute("SELECT figure_id, status FROM figure_registry").fetchall()
    assert rows
    for r in rows:
        if r["status"] != "GENERATED":
            continue
        stem = FIGURES[r["figure_id"]][1]
        for ext in ("svg", "pdf", "png"):
            assert (O3_FIGURE_DIR / f"{stem}.{ext}").exists()
        assert o3_ro.execute("SELECT COUNT(*) FROM figure_sql_registry WHERE figure_id = ?",
                             (r["figure_id"],)).fetchone()[0] > 0


def test_generated_tables_exist(o3_ro):  # G16
    rows = o3_ro.execute("SELECT table_id, status FROM table_registry").fetchall()
    assert rows
    for r in rows:
        if r["status"] != "GENERATED":
            continue
        stem = TABLES[r["table_id"]][1]
        for ext in ("csv", "md", "tex"):
            assert (O3_TABLE_DIR / f"{stem}.{ext}").exists()
        assert o3_ro.execute("SELECT COUNT(*) FROM table_sql_registry WHERE table_id = ?",
                             (r["table_id"],)).fetchone()[0] > 0


def test_registered_sql_hashes_match(o3_ro):  # G16
    for table, key in (("figure_sql_registry", "figure_id"), ("table_sql_registry", "table_id")):
        for r in o3_ro.execute(f"SELECT sql_path, sql_sha256 FROM {table}").fetchall():
            path = Path(r["sql_path"])
            assert path.exists() and sha256_file(path) == r["sql_sha256"]


def test_export_manifest_hashes_match(o3_ro):  # G17
    rows = o3_ro.execute("SELECT artifact_path, sha256 FROM export_manifests").fetchall()
    assert rows
    for r in rows:
        path = Path(r["artifact_path"])
        assert path.exists() and sha256_file(path) == r["sha256"]


def test_figure_manifest_lists_every_generated_figure(o3_ro):
    from kambale.objective_3.config import O3_REPORT_DIR
    manifest = O3_REPORT_DIR / "FIGURE_MANIFEST.csv"
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    for r in o3_ro.execute("SELECT figure_id FROM figure_registry WHERE status = 'GENERATED'").fetchall():
        assert r["figure_id"] in text

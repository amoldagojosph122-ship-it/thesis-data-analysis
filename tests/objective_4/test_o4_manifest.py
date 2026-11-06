"""Manifest, artifact and SQL provenance checks on each built tier database."""

from kambale.objective_4.config import PROJECT_ROOT, sha256_file
from kambale.objective_4.figures import FIGURES
from kambale.objective_4.tables import TABLES


def test_figures_and_tables_exist(o4_ro, tier_paths):
    for r in o4_ro.execute("SELECT figure_id, status FROM figure_registry").fetchall():
        if r["status"] != "GENERATED":
            continue
        stem = FIGURES[r["figure_id"]][1]
        for ext in ("svg", "pdf", "png"):
            assert (tier_paths["figure_dir"] / f"{stem}.{ext}").exists()
    for r in o4_ro.execute("SELECT table_id, status FROM table_registry").fetchall():
        if r["status"] != "GENERATED":
            continue
        stem = TABLES[r["table_id"]][1]
        for ext in ("csv", "md", "tex"):
            assert (tier_paths["table_dir"] / f"{stem}.{ext}").exists()


def test_registered_sql_hashes(o4_ro):
    for table in ("figure_sql_registry", "table_sql_registry"):
        for r in o4_ro.execute(f"SELECT sql_path, sql_sha256 FROM {table}").fetchall():
            path = PROJECT_ROOT / r["sql_path"]
            assert path.exists() and sha256_file(path) == r["sql_sha256"]


def test_export_manifest_hashes(o4_ro):
    rows = o4_ro.execute("SELECT artifact_path, sha256 FROM export_manifests").fetchall()
    assert rows
    for r in rows:
        assert sha256_file(PROJECT_ROOT / r["artifact_path"]) == r["sha256"]


def test_manifest_lists_generated_figures(tier_paths):
    manifest = tier_paths["report_dir"] / "FIGURE_MANIFEST.csv"
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    for fid in ("O4-F01", "O4-F02", "O4-F03", "O4-F04", "O4-F05", "O4-F06", "O4-F07"):
        assert fid in text

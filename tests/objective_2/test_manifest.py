"""Export manifests and hashes (specification 06, section 7; gate G30)."""

import csv
import hashlib

from kambale.objective_2.config import O2_REPORT_DIR, PROJECT_ROOT


def test_manifest_hashes_match_files(o2_ro):
    rows = o2_ro.execute("SELECT artifact_path, artifact_sha256 FROM export_manifests").fetchall()
    assert rows
    for row in rows:
        path = PROJECT_ROOT / row["artifact_path"]
        assert path.exists(), row["artifact_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["artifact_sha256"], row["artifact_path"]


def test_figure_manifest_csv_matches_files():
    manifest = O2_REPORT_DIR / "FIGURE_MANIFEST.csv"
    assert manifest.exists()
    with open(manifest, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    for row in rows:
        path = PROJECT_ROOT / row["artifact_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"], row["artifact_path"]

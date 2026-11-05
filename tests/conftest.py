"""Shared fixtures. A fresh obj1_master is built once per session in a temporary folder, from the real workbook."""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kambale.build import build  # noqa: E402
from kambale.config import RAW_COPY_PATH, SOURCE_PATH  # noqa: E402


@pytest.fixture(scope="session")
def built_db(tmp_path_factory):
    folder = tmp_path_factory.mktemp("obj1")
    db = folder / "kambale_thesis.sqlite"
    summary = build(db_path=db, source_path=SOURCE_PATH, raw_copy=RAW_COPY_PATH)
    assert summary["status"] == "VERIFIED_NEW_VERSION", summary
    return db


@pytest.fixture
def db_copy(built_db, tmp_path):
    target = tmp_path / "copy.sqlite"
    shutil.copy2(built_db, target)
    return target

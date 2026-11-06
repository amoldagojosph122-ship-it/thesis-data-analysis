"""Shared fixtures for the Objective 4 tests."""

import sqlite3

import pytest

from kambale.objective_4.config import O4_DB_PATH


@pytest.fixture(scope="session")
def o4_ro():
    if not O4_DB_PATH.exists():
        pytest.skip("Objective 4 database has not been built")
    conn = sqlite3.connect(f"{O4_DB_PATH.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def receipt_id(o4_ro):
    return o4_ro.execute("SELECT MAX(receipt_id) FROM source_receipts").fetchone()[0]

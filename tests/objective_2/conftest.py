"""Shared fixtures for the Objective 2 tests. Database-backed tests open the Objective 2 database read-only and skip when it
has not been built. Synthetic data appears only inside unit tests and is never written to a database or an export."""

import sqlite3

import pytest

from kambale.objective_2.config import O2_DB_PATH


@pytest.fixture(scope="session")
def o2_ro():
    if not O2_DB_PATH.exists():
        pytest.skip("Objective 2 database has not been built")
    conn = sqlite3.connect(f"{O2_DB_PATH.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def receipt_id(o2_ro):
    return o2_ro.execute("SELECT MAX(receipt_id) FROM source_receipts").fetchone()[0]

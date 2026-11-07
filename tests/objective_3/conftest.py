"""Shared fixtures for the Objective 3 tests. Database-backed tests open the Objective 3 database read-only and skip
when it has not been built. Synthetic data appears only inside unit tests and is never written to a database or export."""

import sqlite3

import pytest

from kambale.objective_3.config import O3_DB_PATH


@pytest.fixture(scope="session")
def o3_ro():
    if not O3_DB_PATH.exists():
        pytest.skip("Objective 3 database has not been built")
    conn = sqlite3.connect(f"{O3_DB_PATH.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def receipt_id(o3_ro):
    return o3_ro.execute("SELECT MAX(receipt_id) FROM source_receipts").fetchone()[0]


@pytest.fixture(scope="session")
def split_plan_id(o3_ro):
    return o3_ro.execute("SELECT split_plan_id FROM spatial_split_plans WHERE primary_plan = 1").fetchone()[0]

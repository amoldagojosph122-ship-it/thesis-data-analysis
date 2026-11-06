"""Shared fixtures for the Objective 4 tests. Integration tests read the built database of one tier; unit tests use
synthetic data and temporary paths only."""

import sqlite3

import pytest

from kambale.objective_4.config import resolve_paths

TIERS = ("1", "2")


@pytest.fixture(params=TIERS, scope="module")
def tier(request):
    return request.param


@pytest.fixture(scope="module")
def tier_paths(tier):
    return resolve_paths(tier)


@pytest.fixture(scope="module")
def o4_ro(tier_paths):
    path = tier_paths["database"]
    if not path.exists():
        pytest.skip(f"Objective 4 tier {tier_paths['tier']} database has not been built")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()

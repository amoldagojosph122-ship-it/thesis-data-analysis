"""Pair accumulation, variogram fitting and simple kriging on controlled synthetic cases (unit tests only)."""

import math

import numpy as np
import pytest

from kambale.objective_3 import kriging, variography
from kambale.objective_2.pairs import bin_edges


def _synthetic(n=80, seed=7):
    rng = np.random.default_rng(seed)
    X = np.column_stack([rng.uniform(0, 300, n), rng.uniform(0, 100, n), rng.uniform(-40, -1, n)])
    hole = rng.integers(0, 12, n)
    values = rng.integers(0, 2, n).astype(float)
    return X, hole, values


def test_accumulate_sq_matches_bruteforce():
    X, hole, values = _synthetic()
    edges = bin_edges(10.0, 80.0)
    res = variography.accumulate_sq(values, X, hole, edges, max_abs_dz=5.0)
    brute = np.zeros(len(edges) - 1, dtype=np.int64)
    sums = np.zeros(len(edges) - 1, dtype=float)
    for i in range(values.size):
        for j in range(i + 1, values.size):
            if hole[i] == hole[j]:
                continue
            if abs(X[i, 2] - X[j, 2]) > 5.0:
                continue
            lag = math.hypot(X[i, 0] - X[j, 0], X[i, 1] - X[j, 1])
            if lag <= 1e-6 or not (edges[0] <= lag < edges[-1]):
                continue
            k = int(np.searchsorted(edges, lag, side="right")) - 1
            brute[k] += 1
            sums[k] += (values[i] - values[j]) ** 2
    assert np.array_equal(res["n_pairs"], brute)
    assert np.allclose(res["sum_sq"], sums)


def test_fit_recovers_known_spherical():
    h = np.arange(10.0, 400.0, 20.0)
    truth = (0.05, 0.10, 150.0)
    from kambale.objective_2.fitting import gamma_model
    g = gamma_model(h, "spherical", *truth)
    res = variography.fit(h, g, np.full(h.size, 500.0), "spherical", 0.25, a_min=10.0, a_max=500.0, min_bins=5,
                          min_sill_fraction=0.05, sill_factor=1.5)
    assert res["status"] == "FITTED"
    assert res["params"] == pytest.approx(truth, rel=2e-2)


def test_pure_nugget_not_identifiable():
    h = np.arange(10.0, 500.0, 20.0)
    res = variography.fit(h, np.full(h.size, 0.15), np.full(h.size, 300.0), "spherical", 0.25, a_min=10.0,
                          a_max=500.0, min_bins=5, min_sill_fraction=0.05, sill_factor=1.5)
    assert res["status"] == "NOT_IDENTIFIABLE"
    assert "sill" in res["reason"] or "range" in res["reason"]


def test_stability_rule():
    base = {"status": "FITTED", "params": (0.05, 0.10, 100.0)}
    inside = [{"status": "FITTED", "params": (0.05, 0.10, r)} for r in (80.0, 120.0, 190.0)]
    outside = inside[:2] + [{"status": "FITTED", "params": (0.05, 0.10, 300.0)}]
    assert variography._stability(base, inside, 0.5, 2.0)["status"] == "STABLE"
    assert variography._stability(base, outside, 0.5, 2.0)["status"] == "UNSTABLE"
    assert variography._stability({"status": "NOT_IDENTIFIABLE"}, inside, 0.5, 2.0)["status"] == "NOT_ASSESSED"


def _kriging_config():
    return {"variogram": {"max_abs_dz_m": 5.0, "kriging": {"min_neighbours": 2, "max_neighbours": 50,
                                                          "jitter_fraction_of_sill": 1e-10,
                                                          "clip_to_unit_interval": True,
                                                          "fallback_when_unsupported": "TRAINING_MEAN"}}}


def test_kriging_reproduces_a_training_value_without_nugget():
    """At a training location, simple kriging with c0=0 is exact for the observed value."""
    X = np.array([[0.0, 0.0, -5.0], [10.0, 0.0, -5.0], [20.0, 0.0, -5.0], [5.0, 0.0, -5.0]])
    values = np.array([0.2, 0.8, 0.4, 0.5])
    out = kriging.simple_kriging(X, values, X[:1], "spherical", (0.0, 0.2, 30.0), _kriging_config(), mean=0.0)
    assert out["p"][0] == pytest.approx(values[0], abs=1e-6)
    assert not out["fallback"][0]


def test_kriging_falls_back_outside_the_depth_band():
    X = np.array([[0.0, 0.0, -5.0], [10.0, 0.0, -5.0], [20.0, 0.0, -5.0]])
    values = np.array([0.2, 0.8, 0.4])
    test = np.array([[5.0, 0.0, -50.0]])
    out = kriging.simple_kriging(X, values, test, "spherical", (0.0, 0.2, 30.0), _kriging_config(), mean=0.37)
    assert out["fallback"][0]
    assert out["p"][0] == pytest.approx(0.37)


def test_kriging_clips_and_counts():
    X = np.array([[0.0, 0.0, -5.0], [10.0, 0.0, -5.0]])
    values = np.array([1.0, 1.0])
    out = kriging.simple_kriging(X, values, np.array([[5.0, 0.0, -5.0]]), "spherical", (0.0, 0.2, 30.0),
                                  _kriging_config(), mean=0.0)
    assert 0.0 <= out["p"][0] <= 1.0

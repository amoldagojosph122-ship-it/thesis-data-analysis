"""Pair generation and binning (specification 06, sections 3.1 and 7)."""

import math

import numpy as np
import pytest

from kambale.objective_2.pairs import accumulate, bin_edges, integer_lag_edges


def _brute(X, I, hole, edges, within, horizontal, max_abs_dz, zero_tol=1e-6):
    n_pairs = np.zeros(len(edges) - 1, dtype=np.int64)
    n_diff = np.zeros(len(edges) - 1, dtype=np.int64)
    for i in range(len(X)):
        for j in range(i + 1, len(X)):
            same = hole[i] == hole[j]
            if (within == "EXCLUDED" and same) or (within == "ONLY" and not same):
                continue
            dx, dy, dz = X[j] - X[i]
            d = math.hypot(dx, dy) if horizontal else math.sqrt(dx * dx + dy * dy + dz * dz)
            if d <= zero_tol or (max_abs_dz is not None and abs(dz) > max_abs_dz):
                continue
            if not (edges[0] <= d < edges[-1]):
                continue
            k = int(np.searchsorted(edges, d, side="right")) - 1
            n_pairs[k] += 1
            n_diff[k] += int(I[i] != I[j])
    return n_pairs, n_diff


@pytest.fixture
def cloud():
    rng = np.random.default_rng(7)
    n = 150
    X = np.column_stack([rng.uniform(0, 400, n), rng.uniform(0, 300, n), -rng.uniform(0, 60, n)])
    hole = rng.integers(0, 6, n)
    I = rng.integers(0, 2, n)
    return X, I, hole, np.bincount(hole, minlength=6).astype(float)


@pytest.mark.parametrize("within", ["EXCLUDED", "INCLUDED", "ONLY"])
@pytest.mark.parametrize("horizontal, max_abs_dz", [(False, None), (True, 3.0)])
def test_pairs_match_bruteforce(cloud, within, horizontal, max_abs_dz):
    X, I, hole, n_per_hole = cloud
    edges = bin_edges(25.0, 400.0)
    acc = accumulate(X, I, hole, n_per_hole, edges, within=within, horizontal=horizontal, max_abs_dz=max_abs_dz)
    n_pairs, n_diff = _brute(X, I, hole, edges, within, horizontal, max_abs_dz)
    assert np.array_equal(acc["n_pairs"], n_pairs)
    assert np.array_equal(acc["n_diff"], n_diff)


def test_no_self_or_zero_pairs():
    X = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [10.0, 0.0, 0.0]])
    I = np.array([1, 0, 0])
    hole = np.array([0, 1, 2])
    acc = accumulate(X, I, hole, np.ones(3), bin_edges(20.0, 40.0), within="EXCLUDED")
    # The duplicate-coordinate pair (0, 1) has zero distance and never reaches a bin; no self-pair can form.
    assert acc["n_pairs"].sum() == 2


def test_within_hole_distance_identity():
    # A straight hole dipping -60 degrees at azimuth 090 advances 0.5 m east and 0.866 m down per metre along the hole,
    # so the three-dimensional distance between consecutive intervals is the along-hole distance.
    step = np.array([math.cos(math.radians(60)), 0.0, -math.sin(math.radians(60))])
    X = np.array([k * step for k in range(6)])
    I = np.array([1, 1, 0, 0, 1, 1])
    acc = accumulate(X, I, np.zeros(6, dtype=int), np.array([6.0]), integer_lag_edges(3), within="ONLY")
    assert acc["n_pairs"].tolist() == [5, 4, 3]
    assert acc["n_diff"][0] == 2


def test_bin_edges_require_whole_multiple():
    assert len(bin_edges(20.0, 500.0)) == 26
    with pytest.raises(ValueError):
        bin_edges(15.0, 500.0)


def test_integer_lag_edges_centre_on_integer_lags():
    edges = integer_lag_edges(30)
    assert np.allclose(0.5 * (edges[:-1] + edges[1:]), np.arange(1, 31))

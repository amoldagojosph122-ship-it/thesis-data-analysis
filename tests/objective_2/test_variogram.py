"""Experimental semivariogram estimators (specification 02, section 3; specification 06, section 3.2)."""

import dataclasses

import numpy as np
import pytest

from kambale.objective_2.pairs import bin_edges, integer_lag_edges
from kambale.objective_2.variogram import ExperimentSpec, Observations, compute


def _obs(X, I, hole):
    X = np.asarray(X, dtype=np.float64)
    I = np.asarray(I, dtype=np.int64)
    holes = sorted(set(np.asarray(hole).tolist()))
    hole_idx = np.array([holes.index(h) for h in np.asarray(hole).tolist()], dtype=np.int64)
    return Observations(X=X, I=I, hole=hole_idx, line=np.zeros(len(I), dtype=np.int64), holes=holes, lines=["SYNTHETIC"],
                        n_per_hole=np.bincount(hole_idx).astype(np.float64), upstream_ids=list(range(len(I))))


def _omni(width, maximum, **kwargs):
    return ExperimentSpec(name="SYNTHETIC", family="OMNI_BETWEEN", within="EXCLUDED", edges=bin_edges(width, maximum),
                          lag_width_m=width, lag_max_m=maximum, min_pairs=1, min_hole_pairs=1, **kwargs)


def test_equal_pair_estimator_by_hand():
    X = [[0, 0, 0], [0, 0, -1], [10, 0, 0], [10, 0, -1]]
    obs = _obs(X, [1, 0, 0, 0], [0, 0, 1, 1])
    res = compute(obs, _omni(20.0, 40.0))
    # Four between-hole pairs fall in the first bin and two of them differ: gamma = 2 / (2 * 4).
    assert res["n_pairs"][0] == 4 and res["n_diff"][0] == 2
    assert res["gamma"][0] == pytest.approx(0.25)
    assert bool(res["supported"][0])


def test_variogram_formula_on_synthetic():
    # Unit-test-only data: four holes of three intervals each, all inside one lag bin. Two holes are positive and two
    # negative. Of the six hole pairs, four differ, so the equal-pair estimator gives 36 / (2 * 54) = 1/3.
    coords, I, hole = [], [], []
    classes = [1, 1, 0, 0]
    for k, c in enumerate(classes):
        for j in range(3):
            coords.append([float(k), 0.0, -float(j)])
            I.append(c)
            hole.append(k)
    res = compute(_obs(coords, I, hole), _omni(20.0, 40.0))
    assert res["gamma"][0] == pytest.approx(1.0 / 3.0)


def test_equal_hole_weighting_matches_definition():
    rng = np.random.default_rng(3)
    X = rng.uniform(0, 60, (30, 3))
    X[:, 2] = -rng.uniform(0, 20, 30)
    hole = np.repeat(np.arange(6), 5)
    I = rng.integers(0, 2, 30)
    spec = _omni(20.0, 80.0, weighting="EQUAL_HOLE")
    res = compute(_obs(X, I, hole), spec)
    num = den = 0.0
    for i in range(30):
        for j in range(i + 1, 30):
            if hole[i] == hole[j]:
                continue
            d = float(np.linalg.norm(X[j] - X[i]))
            if d <= 1e-6 or d >= 20.0:
                continue
            w = 1.0 / 25.0  # 1 / (n_i * n_j) with five intervals per hole
            num += w * float(I[i] != I[j])
            den += w
    assert res["gamma"][0] == pytest.approx(num / (2.0 * den))


def test_downhole_lag_one_gamma():
    X = [[0, 0, 0], [0, 0, -1], [0, 0, -2], [0, 0, -3], [0, 0, -4]]
    spec = ExperimentSpec(name="DOWNHOLE_WITHIN", family="WITHIN_HOLE", within="ONLY", edges=integer_lag_edges(4),
                          lag_width_m=1.0, lag_max_m=4.0, min_pairs=1, min_hole_pairs=1)
    res = compute(_obs(X, [1, 1, 0, 0, 1], [0] * 5), spec)
    # Four consecutive pairs at lag 1, two of which change class: gamma = 2 / (2 * 4).
    assert res["n_pairs"][0] == 4
    assert res["gamma"][0] == pytest.approx(0.25)


def test_bin_support_threshold():
    obs = _obs([[0, 0, 0], [0, 0, -1], [10, 0, 0], [10, 0, -1]], [1, 0, 0, 0], [0, 0, 1, 1])
    res = compute(obs, dataclasses.replace(_omni(20.0, 40.0), min_pairs=5))
    assert not bool(res["supported"][0])
    assert np.isnan(res["gamma"][0])

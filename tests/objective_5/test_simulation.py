"""Scenario simulation (part 2): vertical range, correlogram, simple kriging, neighbourhoods, connectivity and seeds."""

import numpy as np
import pytest

from kambale.objective_5 import simulate as S

A_D = 23.5297
C0 = 0.012760
C1 = 0.213132


def test_vertical_range_matches_expected_values_and_bracket():
    for a_h, expected in ((15.0, 32.85), (25.0, 23.09), (50.0, 20.97), (100.0, 20.52), (200.0, 20.41)):
        a_v, bracket, feas = S.vertical_range(A_D, a_h)
        assert feas == "FEASIBLE" and bracket > 0
        assert abs(a_v - expected) <= 0.01
        # along the hole (plunge 60 degrees) the scaled distance of a unit step equals 1 / a_d
        h = np.sqrt(np.cos(np.radians(60)) ** 2 / a_h ** 2 + np.sin(np.radians(60)) ** 2 / a_v ** 2)
        assert h == pytest.approx(1.0 / A_D, rel=1e-9)


def test_vertical_range_infeasible_below_a_d_cos_dip():
    limit = A_D * np.cos(np.radians(60))
    a_v, bracket, feas = S.vertical_range(A_D, limit * 0.95)
    assert feas == "INFEASIBLE" and a_v is None and bracket <= 0
    a_v, bracket, feas = S.vertical_range(A_D, limit * 1.05)
    assert feas == "FEASIBLE" and a_v is not None and bracket > 0


def test_correlogram_origin_and_nugget_jump():
    assert float(S.correlogram(0.0, C0, C1)) == 1.0
    tail = C1 / (C0 + C1)
    assert float(S.correlogram(1e-12, C0, C1)) == pytest.approx(tail, rel=1e-9)
    assert float(S.correlogram(1.0, C0, C1)) == pytest.approx(tail * np.exp(-3.0), rel=1e-12)
    # the jump at the origin is the nugget fraction
    assert 1.0 - float(S.correlogram(1e-12, C0, C1)) == pytest.approx(C0 / (C0 + C1), rel=1e-9)


def test_simple_kriging_single_datum_at_distance_zero_plus_gives_nugget_weight():
    m = 0.3
    s = np.sqrt(m * (1 - m))
    lam, lstsq = S.sk_weights(np.array([[1e-9, 0.0, 0.0]]), np.array([s]), np.array([0.0, 0.0, 0.0]), s, C0, C1)
    assert not lstsq
    assert lam[0] == pytest.approx(C1 / (C0 + C1), abs=1e-6)


def test_node_with_no_neighbours_takes_its_local_mean():
    node_xyz = np.array([[0.0, 0.0, -10.0], [1000.0, 0.0, -10.0]])
    node_m = np.array([0.23, 0.61])
    ctx = S.build_context(node_xyz, node_m, np.zeros((0, 3)), np.zeros(0), np.zeros(0), 15.0, 32.85, C0, C1)
    assert all(nb.size == 0 for nb in ctx["data_nb"])
    sim, pstar, stats = S.simulate_realisation(ctx, np.random.default_rng(3))
    assert stats["sk_neighbourless_nodes"] == 2
    np.testing.assert_allclose(pstar, node_m, rtol=0, atol=0)


def test_connectivity_counts_26_neighbour_components():
    arr = np.zeros((5, 5, 5), dtype=bool)
    arr[1, 1, 1] = True
    arr[2, 2, 2] = True          # diagonal to (1,1,1): one component under 26-connectivity
    arr[4, 0, 0] = True          # isolated
    ncomp, largest = S.connectivity(arr)
    assert ncomp == 2 and largest == 2
    flat = np.zeros((1, 3, 3), dtype=bool)
    flat[0, 0, 0] = True
    flat[0, 1, 1] = True         # diagonal in the plane: connected
    assert S.connectivity(flat) == (1, 2)
    assert S.connectivity(np.zeros((2, 2, 2), dtype=bool)) == (0, 0)


def _synthetic_context(seed=7):
    rng = np.random.default_rng(seed)
    xs, ys, zs = np.meshgrid(np.arange(6) * 10.0, np.arange(6) * 10.0, -np.arange(4) * 2.0 - 1.0)
    node_xyz = np.column_stack([xs.ravel(), ys.ravel(), zs.ravel()])
    node_m = rng.uniform(0.15, 0.6, node_xyz.shape[0])
    data_xyz = np.column_stack([rng.uniform(0, 50, 20), rng.uniform(0, 50, 20), -rng.uniform(0.5, 7, 20)])
    data_m = rng.uniform(0.15, 0.6, 20)
    data_y = (rng.uniform(size=20) < data_m).astype(float)
    return S.build_context(node_xyz, node_m, data_xyz, data_m, data_y, 15.0, 32.85, C0, C1)


def test_same_seed_gives_identical_realisation():
    ctx = _synthetic_context()
    a, _, _ = S.simulate_realisation(ctx, S.realisation_rng(S.SEED, 0, 1))
    b, _, _ = S.simulate_realisation(ctx, S.realisation_rng(S.SEED, 0, 1))
    np.testing.assert_array_equal(a, b)
    c, _, _ = S.simulate_realisation(ctx, S.realisation_rng(S.SEED, 0, 2))
    assert not np.array_equal(a, c)
    d, _, _ = S.simulate_realisation(ctx, S.realisation_rng(S.SEED, 1, 1))
    assert not np.array_equal(a, d)


def test_neighbour_limits_are_respected():
    ctx = _synthetic_context()
    assert max(nb.size for nb in ctx["data_nb"]) <= S.MAX_DATA
    rng = S.realisation_rng(S.SEED, 0, 1)
    _, _, stats = S.simulate_realisation(ctx, rng)
    assert stats["sk_fallbacks"] == 0

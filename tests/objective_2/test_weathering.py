"""Configuration 5 (weathering front, fresh-rock variography): unit tests on synthetic data only.

No test here opens the Objective 2 database. The stage itself is exercised by the all-command run and by the gate checks.
"""

import numpy as np
import pytest

from kambale.objective_2 import variogram, weathering
from kambale.objective_2.pairs import bin_edges


def _interval(hole, line, uid, depth_from, z, code, east=0.0, north=0.0):
    return {"hole_id": hole, "line_code": line, "upstream_interval_id": uid, "depth_from_m": float(depth_from),
            "midpoint_m": float(depth_from) + 0.5, "z_relative_m": float(z), "weathering_code": code,
            "easting_m": east, "northing_m": north}


def test_front_is_shallowest_front_code_with_interpolated_depth_and_reversals():
    # Hole H1: z = -0.5 * midpoint exactly, so the least-squares slope through the origin is -0.5.
    h1 = [_interval("H1", "L1", 1, 0, -0.25, "fr", 10.0, 20.0),
          _interval("H1", "L1", 2, 1, -0.75, "mw", 10.0, 20.0),
          _interval("H1", "L1", 3, 2, -1.25, "cw", 10.0, 20.0),
          _interval("H1", "L1", 4, 3, -1.75, "hw", 10.0, 20.0)]
    # Hole H2: no front-code interval, so it has no front.
    h2 = [_interval("H2", "L1", 5, 0, -0.25, "fr", 30.0, 20.0), _interval("H2", "L1", 6, 1, -0.75, "cw", 30.0, 20.0)]
    # Hole H3: front at 4 m with no reversal below it.
    h3 = [_interval("H3", "L2", 7, 2, -1.25, "fr", 50.0, 60.0), _interval("H3", "L2", 8, 4, -2.25, "sw", 50.0, 60.0),
          _interval("H3", "L2", 9, 6, -3.25, "mw", 50.0, 60.0)]
    fronts, no_front = weathering.extract_fronts(h1 + h2 + h3, ("mw", "sw"), ("cw", "hw"))
    by_hole = {f["hole_id"]: f for f in fronts}
    assert no_front == ["H2"]
    assert set(by_hole) == {"H1", "H3"}
    assert by_hole["H1"]["front_depth_m"] == pytest.approx(1.0)
    assert by_hole["H1"]["front_z_relative_m"] == pytest.approx(-0.5)      # a * depth_from = -0.5 * 1.0
    assert by_hole["H1"]["n_reversal_intervals"] == 2                      # cw at 2 m and hw at 3 m lie below the front
    assert (by_hole["H1"]["easting_m"], by_hole["H1"]["northing_m"]) == (10.0, 20.0)
    assert by_hole["H3"]["front_depth_m"] == pytest.approx(4.0)
    assert by_hole["H3"]["front_z_relative_m"] == pytest.approx(-2.0)      # the slope fitted on H3 alone is -0.5
    assert by_hole["H3"]["n_reversal_intervals"] == 0


def test_front_slope_uses_every_interval_of_the_hole():
    # Non-proportional depths: the slope is the through-origin least-squares value, not the value at one interval.
    rows = [_interval("H", "L", 1, 0, -1.0, "fr"), _interval("H", "L", 2, 1, -1.0, "mw"),
            _interval("H", "L", 3, 2, -4.0, "fr")]
    mid = np.array([0.5, 1.5, 2.5])
    z = np.array([-1.0, -1.0, -4.0])
    slope = float(np.sum(mid * z) / np.sum(mid * mid))
    fronts, _ = weathering.extract_fronts(rows, ("mw", "sw"), ("cw", "hw"))
    assert fronts[0]["front_z_relative_m"] == pytest.approx(slope * 1.0)


def test_idw_predicts_by_inverse_squared_distance():
    xy = np.array([[0.0, 0.0], [10.0, 0.0]])
    z = np.array([1.0, 3.0])
    assert weathering.idw_predict(xy, z, (5.0, 0.0), power=2.0, n_neighbours=8) == pytest.approx(2.0)
    expected = (0.25 * 1.0 + (1.0 / 64.0) * 3.0) / (0.25 + 1.0 / 64.0)
    assert weathering.idw_predict(xy, z, (2.0, 0.0), power=2.0, n_neighbours=8) == pytest.approx(expected)
    # A training hole within 0.001 m takes all the weight.
    assert weathering.idw_predict(xy, z, (0.0, 0.0005), power=2.0, n_neighbours=8) == pytest.approx(1.0)


def test_leave_one_hole_out_toy_set_gives_known_skill():
    # Three collinear holes with a linear front. Leave-one-out IDW errors are +2.4, 0 and -2.4 m, so the IDW RMSE is
    # sqrt(3.84) m and the training-mean RMSE is sqrt(6) m: the skill ratio is exactly 0.8.
    xy = np.array([[0.0, 0.0], [10.0, 0.0], [20.0, 0.0]])
    z = np.array([1.0, 3.0, 5.0])
    line = np.array(["L", "L", "L"])
    res = weathering.interpolation_check(xy, z, line, "LEAVE_ONE_HOLE_OUT", power=2.0, n_neighbours=8)
    assert res["n_predicted"] == 3 and res["n_folds"] == 3
    assert res["rmse_idw"] == pytest.approx(np.sqrt(3.84))
    assert res["rmse_training_mean"] == pytest.approx(np.sqrt(6.0))
    assert res["skill_ratio"] == pytest.approx(0.8)


def test_leave_one_line_out_uses_other_lines_only():
    xy = np.array([[0.0, 0.0], [10.0, 0.0], [0.0, 500.0], [10.0, 500.0]])
    z = np.array([1.0, 1.0, 4.0, 4.0])
    line = np.array(["A", "A", "B", "B"])
    res = weathering.interpolation_check(xy, z, line, "LEAVE_ONE_LINE_OUT", power=2.0, n_neighbours=8)
    assert res["n_folds"] == 2 and res["n_predicted"] == 4
    # Each line is predicted from the other line alone, so every prediction is 3 or 1 m away from the truth.
    assert res["rmse_idw"] == pytest.approx(3.0)


def _random_observations(seed=7, n=120, n_holes=12, n_lines=3):
    rng = np.random.default_rng(seed)
    hole = rng.integers(0, n_holes, size=n).astype(np.int64)
    line = (hole % n_lines).astype(np.int64)
    X = np.column_stack([rng.uniform(0, 300, n), rng.uniform(0, 300, n), rng.uniform(-5.0, 0.0, n)])
    I = rng.integers(0, 2, size=n).astype(np.int64)
    present = np.unique(hole)
    hole = np.searchsorted(present, hole).astype(np.int64)
    line_present = np.unique(line)
    line = np.searchsorted(line_present, line).astype(np.int64)
    n_per_hole = np.bincount(hole).astype(np.float64)
    return variogram.Observations(X=X, I=I, hole=hole, line=line, holes=[f"H{k}" for k in present],
                                  lines=[f"L{k}" for k in line_present], n_per_hole=n_per_hole,
                                  upstream_ids=list(range(n)))


def test_unit_multiplicities_reproduce_plain_semivariance():
    obs = _random_observations()
    spec = variogram.ExperimentSpec(name="T", family="LATERAL_BETWEEN", within="EXCLUDED", horizontal=True,
                                    edges=bin_edges(20.0, 500.0), lag_width_m=20.0, lag_max_m=500.0, max_abs_dz=3.0,
                                    min_pairs=1, min_hole_pairs=1, variant="SENSITIVITY")
    res = variogram.compute(obs, spec)
    pairs = weathering.between_hole_pairs(obs.X, obs.I, obs.hole, spec.edges, horizontal=True, max_abs_dz=3.0)
    assert np.array_equal(np.bincount(pairs["bin"], minlength=pairs["nb"]), res["n_pairs"])
    weighted = weathering.weighted_gamma(pairs, np.ones(len(obs.holes)))
    sup = res["supported"]
    assert sup.any()
    assert np.allclose(weighted[sup], res["gamma"][sup], rtol=1e-12, atol=1e-12)


def test_pairs_between_copies_of_the_same_hole_are_never_formed():
    # Hole 0 has three intervals 5 m and 10 m apart (within-hole pairs); hole 1 is 100 m away. Only the three
    # between-hole pairs may reach a bin.
    X = np.array([[0.0, 0.0, -1.0], [5.0, 0.0, -1.0], [10.0, 0.0, -1.0], [100.0, 0.0, -1.0]])
    I = np.array([1, 0, 1, 0], dtype=np.int64)
    hole = np.array([0, 0, 0, 1], dtype=np.int64)
    edges = bin_edges(20.0, 500.0)
    pairs = weathering.between_hole_pairs(X, I, hole, edges, horizontal=True, max_abs_dz=3.0)
    assert pairs["hi"].size == 3
    assert np.all(pairs["hi"] != pairs["hj"])
    # Resampling hole 0 twice weights each cross pair by 2 and never adds a within-hole term.
    gamma_twice = weathering.weighted_gamma(pairs, np.array([2.0, 1.0]))
    gamma_once = weathering.weighted_gamma(pairs, np.array([1.0, 1.0]))
    assert np.allclose(gamma_twice[~np.isnan(gamma_twice)], gamma_once[~np.isnan(gamma_once)])
    # A hole that is not drawn in a replicate contributes no pair to that replicate.
    assert np.all(np.isnan(weathering.weighted_gamma(pairs, np.array([1.0, 0.0]))))


def test_bootstrap_is_reproducible_and_bands_bracket_the_median():
    obs = _random_observations(seed=11)
    edges = bin_edges(20.0, 500.0)
    pairs = weathering.between_hole_pairs(obs.X, obs.I, obs.hole, edges, horizontal=True, max_abs_dz=3.0)
    a = weathering.hole_bootstrap(pairs, len(obs.holes), n_replicates=50, seed=20261106, confidence=0.95)
    b = weathering.hole_bootstrap(pairs, len(obs.holes), n_replicates=50, seed=20261106, confidence=0.95)
    for key in ("lower", "upper", "median", "n_used"):
        assert np.array_equal(a[key], b[key], equal_nan=True)
    ok = a["n_used"] > 0
    assert np.all(a["lower"][ok] <= a["median"][ok] + 1e-12)
    assert np.all(a["median"][ok] <= a["upper"][ok] + 1e-12)

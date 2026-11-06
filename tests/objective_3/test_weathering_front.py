"""Weathering-front predictor: front extraction, IDW surface and fold safety on controlled synthetic cases.

The database-backed check uses an in-memory SQLite table with the analysis_observations columns; no project data is read.
"""

import sqlite3

import numpy as np
import pytest

from kambale.objective_3 import weathering_front as wf
from kambale.objective_3.features import Observations


def _obs_four_holes():
    """Four holes on one line. Hole 'A' and 'B' train, 'C' train, 'D' test. One row per hole, z = -depth."""
    holes = ["A", "B", "C", "D"]
    E = {"A": 0.0, "B": 10.0, "C": 20.0, "D": 5.0}
    rows = [("A", 0.0, -2.0), ("A", 0.0, -4.0), ("B", 10.0, -3.0), ("C", 20.0, -6.0), ("D", 5.0, -5.0)]
    X = np.array([[E[h], 0.0, z] for h, _, z in rows], dtype=float)
    hole = np.array([holes.index(h) for h, _, _ in rows], dtype=np.int64)
    y = np.array([0, 1, 0, 1, 0], dtype=np.int64)
    return Observations(ids=np.arange(1, 6), X=X, y=y, hole=hole, line=np.zeros(5, dtype=np.int64), holes=holes,
                        lines=["L"], feature_names=["easting_m", "northing_m", "z_relative_m"])


FRONTS = {"A": (0.0, 0.0, -4.0), "B": (10.0, 0.0, -6.0), "C": (20.0, 0.0, -9.0), "D": (5.0, 0.0, -2.0)}


def test_idw_exact_at_a_point_and_weights_by_inverse_square_distance():
    pts = np.array([[0.0, 0.0], [10.0, 0.0]])
    vals = np.array([1.0, 3.0])
    out = wf.idw(pts, vals, np.array([[0.0, 0.0], [5.0, 0.0], [2.0, 0.0]]))
    assert out[0] == pytest.approx(1.0)
    assert out[1] == pytest.approx(2.0)
    assert out[2] == pytest.approx((1.0 / 4 * 1.0 + 1.0 / 64 * 3.0) / (1.0 / 4 + 1.0 / 64))


def test_idw_keeps_only_the_k_nearest():
    pts = np.array([[0.0, 0.0], [1.0, 0.0], [100.0, 0.0]])
    vals = np.array([1.0, 1.0, 1000.0])
    assert wf.idw(pts, vals, np.array([[0.5, 0.0]]), k=2)[0] == pytest.approx(1.0)


def test_own_hole_is_excluded_for_training_rows():
    obs = _obs_four_holes()
    train_idx = np.array([0, 1, 2, 3])
    test_idx = np.array([4])
    out = wf.feature_for_fold(obs, train_idx, test_idx, FRONTS)
    # Rows of hole A (indices 0 and 1) must use only B and C as the surface.
    pts = np.array([[10.0, 0.0], [20.0, 0.0]])
    vals = np.array([-6.0, -9.0])
    for i in (0, 1):
        surface = wf.idw(pts, vals, obs.X[i:i + 1, :2])[0]
        assert out["train"][i] == pytest.approx(surface - obs.X[i, 2])
    assert set(out["surface_holes"]) == {"A", "B", "C"}


def test_test_holes_never_contribute_to_the_surface():
    obs = _obs_four_holes()
    train_idx = np.array([0, 1, 2, 3])
    test_idx = np.array([4])
    base = wf.feature_for_fold(obs, train_idx, test_idx, FRONTS)
    changed = dict(FRONTS)
    changed["D"] = (5.0, 0.0, -50.0)
    other = wf.feature_for_fold(obs, train_idx, test_idx, changed)
    assert "D" not in base["surface_holes"]
    assert np.array_equal(base["train"], other["train"])
    assert np.array_equal(base["test"], other["test"])


def test_test_rows_use_all_training_holes():
    obs = _obs_four_holes()
    out = wf.feature_for_fold(obs, np.array([0, 1, 2, 3]), np.array([4]), FRONTS)
    pts = np.array([FRONTS[h][:2] for h in ("A", "B", "C")])
    vals = np.array([FRONTS[h][2] for h in ("A", "B", "C")])
    surface = wf.idw(pts, vals, obs.X[4:5, :2])[0]
    assert out["test"][0] == pytest.approx(surface - obs.X[4, 2])


def test_hole_front_is_the_shallowest_front_interval_with_a_least_squares_slope():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE analysis_observations (receipt_id INT, upstream_interval_id INT, hole_id TEXT, "
                 "depth_from_m REAL, midpoint_m REAL, z_relative_m REAL, easting_m REAL, northing_m REAL, "
                 "weathering_code TEXT)")
    # Hole H: slope through origin of z on midpoint is -0.5 exactly; front at depth 6 (code 'sw') and deeper 'mw' at 9.
    data = [(1, "H", 0.0, 0.5, -0.25, 100.0, 200.0, "hw"), (2, "H", 2.0, 2.5, -1.25, 100.0, 200.0, "cw"),
            (3, "H", 6.0, 6.5, -3.25, 101.0, 201.0, "sw"), (4, "H", 9.0, 9.5, -4.75, 101.0, 201.0, "mw"),
            (5, "G", 0.0, 0.5, -0.5, 300.0, 400.0, "cw"), (6, "G", 3.0, 3.5, -1.75, 300.0, 400.0, "cw")]
    conn.executemany("INSERT INTO analysis_observations VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)", data)
    fronts = wf.hole_fronts(conn, 1, ["mw", "sw"])
    assert set(fronts) == {"H"}
    easting, northing, front_z = fronts["H"]
    assert (easting, northing) == (101.0, 201.0)
    slope = sum(d[3] * d[4] for d in data[:4]) / sum(d[3] ** 2 for d in data[:4])
    assert front_z == pytest.approx(slope * 6.0)
    overridden = wf.hole_fronts(conn, 1, ["mw", "sw"], override_codes={"H": None})
    assert overridden == {}


def test_fold_safety_check_passes_on_a_consistent_fold():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE analysis_observations (receipt_id INT, upstream_interval_id INT, hole_id TEXT, "
                 "depth_from_m REAL, midpoint_m REAL, z_relative_m REAL, easting_m REAL, northing_m REAL, "
                 "weathering_code TEXT)")
    obs = _obs_four_holes()
    rows = [(1, "A", 0.0, 0.5, -0.5, 0.0, 0.0, "sw"), (2, "A", 1.0, 1.5, -1.5, 0.0, 0.0, "cw"),
            (3, "B", 2.0, 2.5, -2.5, 10.0, 0.0, "mw"), (4, "C", 4.0, 4.5, -4.5, 20.0, 0.0, "sw"),
            (5, "D", 3.0, 3.5, -3.5, 5.0, 0.0, "sw")]
    conn.executemany("INSERT INTO analysis_observations VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    check = wf.fold_safety_check(conn, 1, obs, np.array([0, 1, 2, 3]), np.array([4]), ["mw", "sw"])
    assert check["status"] == "PASS"
    assert "D" not in check["surface_holes"]

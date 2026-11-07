"""Hole bootstrap resampling, own-hole exclusion from the front surface, and the uint8 storage."""

import numpy as np
import pytest

from kambale.objective_3.weathering_front import idw
from kambale.objective_5.bootstrap import (dequantise, interval_from_replicates, own_hole_positions,
                                           quantise, replicate_training_rows)
from kambale.objective_5.config import StopError
from kambale.objective_5.front import idw_vectorised
from kambale.objective_5.importer import check_handoff_match


def _synthetic_rows():
    # Four holes with 3, 2, 4 and 1 intervals.
    hole = np.array([0, 0, 0, 1, 1, 2, 2, 2, 2, 3])
    rows_of_hole = [np.where(hole == h)[0] for h in range(4)]
    return hole, rows_of_hole


def test_drawn_hole_keeps_all_of_its_intervals_and_copies_are_kept():
    hole, rows_of_hole = _synthetic_rows()
    draw = np.array([2, 2, 0, 3])
    rows = replicate_training_rows(draw, rows_of_hole)
    # Hole 2 drawn twice contributes its four intervals twice; hole 0 its three; hole 3 its one.
    assert rows.size == 4 + 4 + 3 + 1
    assert np.sum(hole[rows] == 2) == 8
    assert np.sum(hole[rows] == 0) == 3
    assert np.sum(hole[rows] == 1) == 0


def test_training_row_excludes_all_copies_of_its_own_hole_from_the_front():
    usable = np.array([0, 2, 3])                        # holes with a front among the drawn holes
    rows_hole = np.array([2, 2, 0, 3, 1])               # hole 1 has no front among the drawn holes
    own = own_hole_positions(rows_hole, usable, n_holes=4)
    assert list(own) == [1, 1, 0, 2, -1]


def test_vectorised_idw_with_own_hole_excluded_equals_reference_without_that_point():
    rng = np.random.default_rng(3)
    pts = rng.uniform(0, 300, size=(9, 2))
    vals = rng.normal(-20, 5, size=9)
    q = rng.uniform(0, 300, size=(40, 2))
    own = rng.integers(0, 9, size=40)
    fast = idw_vectorised(pts, vals, q, exclude=own, power=2.0, k=8, coincident=0.001)
    for i in range(q.shape[0]):
        keep = np.arange(9) != own[i]
        ref = idw(pts[keep], vals[keep], q[i:i + 1], 2.0, 8, 0.001)[0]
        assert fast[i] == pytest.approx(ref, abs=1e-9)


def test_vectorised_idw_matches_objective_3_on_full_point_set():
    rng = np.random.default_rng(7)
    pts = rng.uniform(0, 500, size=(71, 2))
    vals = rng.normal(-15, 3, size=71)
    q = rng.uniform(0, 500, size=(60, 2))
    fast = idw_vectorised(pts, vals, q, exclude=None)
    ref = idw(pts, vals, q, 2.0, 8, 0.001)
    assert np.max(np.abs(fast - ref)) <= 1e-9


def test_uint8_round_trip_error_within_one_over_510():
    rng = np.random.default_rng(11)
    p = rng.uniform(0, 1, 100000)
    err = np.abs(dequantise(quantise(p)) - p)
    assert err.max() <= 1.0 / 510.0 + 1e-15


def test_percentile_interval_uses_only_successful_replicates():
    q = np.array([[0, 255], [255, 0], [128, 128]], dtype=np.uint8)
    success = np.array([True, True, False])
    lo, hi = interval_from_replicates(q, success)
    assert lo.shape == (2,) and hi.shape == (2,)
    assert lo[0] == pytest.approx(0.05, abs=1e-9) and hi[0] == pytest.approx(0.95, abs=1e-9)


def test_handoff_mismatch_raises_stop():
    required = {"TIER_2_INTERPOLATION": {"selected": "M2_HGB_WF", "runner_up": "M2_HGB"}}
    assert check_handoff_match("TIER_2_INTERPOLATION", "M2_HGB_WF", "M2_HGB", required) == "MATCH"
    with pytest.raises(StopError):
        check_handoff_match("TIER_2_INTERPOLATION", "M2_HGB_WF", "M2_RF", required)
    with pytest.raises(StopError):
        check_handoff_match("TIER_2_INTERPOLATION", "M2_HGB", "M2_HGB_WF", required)

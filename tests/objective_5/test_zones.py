"""Support zones and depth support on synthetic collars (no database)."""

import numpy as np
import pytest
from scipy.spatial import cKDTree

from kambale.objective_5.config import EXTRAPOLATION, INTERPOLATION, NO_SUPPORT
from kambale.objective_5.grid import (DEPTH_EXTRAPOLATED, SUPPORTED, depth_support_labels, deepest_sampled_z,
                                      zone_from_distance)

LIMITS = {INTERPOLATION: 25.0, EXTRAPOLATION: 560.0, NO_SUPPORT: None}


def test_zone_boundaries_are_inclusive_at_the_limits():
    d = np.array([0.0, 24.99, 25.0, 25.01, 559.99, 560.0, 560.01])
    zones = list(zone_from_distance(d, LIMITS))
    assert zones == [INTERPOLATION, INTERPOLATION, INTERPOLATION, EXTRAPOLATION, EXTRAPOLATION, EXTRAPOLATION,
                     NO_SUPPORT]


def test_nearest_collar_distance_on_synthetic_collars_gives_expected_zones():
    collars = np.array([[0.0, 0.0], [100.0, 0.0], [0.0, 1000.0]])
    cells = np.array([[10.0, 0.0],      # 10 m from collar 0 -> INTERPOLATION
                      [0.0, 40.0],      # 40 m -> EXTRAPOLATION
                      [0.0, 590.0],     # 590 m from collar 0 but 410 m from collar 2 -> EXTRAPOLATION
                      [0.0, 1600.0],    # 600 m from collar 2 -> NO_SUPPORT
                      [50.0, 500.0]])   # about 500 m from the nearest collar -> EXTRAPOLATION
    d, _ = cKDTree(collars).query(cells)
    zones = list(zone_from_distance(d, LIMITS))
    assert zones[0] == INTERPOLATION
    assert zones[1] == EXTRAPOLATION
    assert zones[2] == EXTRAPOLATION
    assert zones[3] == NO_SUPPORT
    assert zones[4] == EXTRAPOLATION


def test_depth_support_uses_holes_within_radius():
    # Two holes 50 m apart and one hole 300 m away; deepest samples -40 (near), -20 (near), -55 (far).
    holes = np.array([[0.0, 0.0], [50.0, 0.0], [300.0, 0.0]])
    deep = np.array([-40.0, -20.0, -55.0])
    cells = np.array([[10.0, 0.0]])
    D = np.sqrt(((cells[:, None, :] - holes[None, :, :]) ** 2).sum(axis=2))
    deepest = deepest_sampled_z(D, deep, radius=100.0)
    assert deepest[0] == -40.0            # the far hole does not count
    assert depth_support_labels([-41.0], deepest)[0] == DEPTH_EXTRAPOLATED
    assert depth_support_labels([-40.0], deepest)[0] == SUPPORTED   # equal to the deepest sample is supported


def test_depth_support_falls_back_to_nearest_hole_when_none_within_radius():
    holes = np.array([[0.0, 0.0], [500.0, 0.0]])
    deep = np.array([-30.0, -50.0])
    cells = np.array([[400.0, 0.0]])
    D = np.sqrt(((cells[:, None, :] - holes[None, :, :]) ** 2).sum(axis=2))
    deepest = deepest_sampled_z(D, deep, radius=100.0)
    assert deepest[0] == -50.0            # nearest hole is the second one
    assert depth_support_labels([-49.0], deepest)[0] == SUPPORTED
    assert depth_support_labels([-51.0], deepest)[0] == DEPTH_EXTRAPOLATED

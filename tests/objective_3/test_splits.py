"""Spatial split construction on controlled synthetic cases."""

import numpy as np
import pytest

from kambale.objective_3.features import Observations, fold_membership


def _obs():
    ids = np.arange(1, 31)
    hole = np.repeat(np.arange(6), 5)
    line = np.repeat(np.arange(3), 10)
    X = np.column_stack([np.repeat(np.arange(3) * 100.0, 10), np.repeat([0.0, 50.0], 15), -np.arange(30) * 0.87])
    y = np.tile([0, 0, 0, 1, 0], 6)
    return Observations(ids=ids, X=X, y=y, hole=hole, line=line,
                         holes=[f"H{i}" for i in range(6)], lines=[f"L{i}" for i in range(3)],
                         feature_names=["easting_m", "northing_m", "z_relative_m"])


def test_lodo_partitions_every_observation_and_holds_out_one_line():
    obs = _obs()
    folds = fold_membership(obs, {"method": "LEAVE_ONE_DRILL_LINE_OUT", "n_folds": 3})
    assert len(folds) == 3
    tested = np.zeros(obs.n, dtype=int)
    for fold in folds:
        assert int(fold["test"].sum()) == 10
        assert len(set(obs.line[fold["test"]].tolist())) == 1
        tested += fold["test"].astype(int)
    assert np.all(tested == 1)


def test_group_folds_keep_whole_holes():
    obs = _obs()
    folds = fold_membership(obs, {"method": "GROUP_K_FOLD_BY_HOLE", "n_folds": 3})
    assert len(folds) == 3
    for fold in folds:
        tr = ~fold["test"]
        assert not (set(obs.hole[tr].tolist()) & set(obs.hole[fold["test"]].tolist()))
    tested = np.zeros(obs.n, dtype=int)
    for fold in folds:
        tested += fold["test"].astype(int)
    assert np.all(tested == 1)

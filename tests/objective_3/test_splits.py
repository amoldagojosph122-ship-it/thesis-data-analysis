"""Spatial split construction on controlled synthetic cases."""

import numpy as np
import pytest

from kambale.objective_3.features import Observations, fold_membership, interleaved_assignment


def _obs():
    ids = np.arange(1, 31)
    hole = np.repeat(np.arange(6), 5)
    line = np.repeat(np.arange(3), 10)
    X = np.column_stack([np.repeat(np.arange(3) * 100.0, 10), np.repeat([0.0, 50.0], 15), -np.arange(30) * 0.87])
    y = np.tile([0, 0, 0, 1, 0], 6)
    return Observations(ids=ids, X=X, y=y, hole=hole, line=line,
                        holes=[f"H{i}" for i in range(6)], lines=[f"L{i}" for i in range(3)],
                        feature_names=["easting_m", "northing_m", "z_relative_m"])


def _interleave_obs():
    """Two lines. Line L0 has seven holes, given here in shuffled order, with collar eastings 0 to 60. Line L1 has two
    holes whose eastings tie at 5.0, so the hole identifier decides the order. Each hole has two intervals; the shallow
    one is the collar proxy."""
    spec = [("L0", "H03", 20.0), ("L0", "H00", 0.0), ("L0", "H06", 60.0), ("L0", "H01", 10.0), ("L0", "H05", 50.0),
            ("L0", "H02", 30.0), ("L0", "H04", 40.0), ("L1", "K02", 5.0), ("L1", "K01", 5.0)]
    holes = [h for _, h, _ in spec]
    lines = ["L0", "L1"]
    X, hole, line, y = [], [], [], []
    for i, (ln, _h, e) in enumerate(spec):
        for z in (-1.0, -4.0):
            X.append([e, 0.0, z])
            hole.append(i)
            line.append(lines.index(ln))
            y.append(len(X) % 2)
    return Observations(ids=np.arange(1, len(X) + 1), X=np.array(X), y=np.array(y), hole=np.array(hole),
                        line=np.array(line), holes=holes, lines=lines,
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


def test_interleaved_assignment_follows_collar_easting_within_line():
    obs = _interleave_obs()
    assign = interleaved_assignment(obs, 5)
    by_name = {obs.holes[h]: f for h, f in assign.items()}
    # L0 by easting: H00 (0), H01 (10), H03 (20), H02 (30), H04 (40), H05 (50), H06 (60). The k-th hole goes to k mod 5 + 1.
    expected_l0 = {"H00": 1, "H01": 2, "H03": 3, "H02": 4, "H04": 5, "H05": 1, "H06": 2}
    assert {k: by_name[k] for k in expected_l0} == expected_l0
    # L1: the eastings tie at 5.0, so K01 precedes K02 by identifier.
    assert by_name["K01"] == 1 and by_name["K02"] == 2


def test_interleaved_folds_partition_and_keep_whole_holes():
    obs = _interleave_obs()
    folds = fold_membership(obs, {"method": "INTERLEAVED_HOLES_WITHIN_LINE", "n_folds": 5})
    assert len(folds) == 5
    tested = np.zeros(obs.n, dtype=int)
    for fold in folds:
        tr = ~fold["test"]
        assert not (set(obs.hole[tr].tolist()) & set(obs.hole[fold["test"]].tolist()))
        tested += fold["test"].astype(int)
    assert np.all(tested == 1)


def test_interleaved_test_holes_have_training_neighbours_along_the_line():
    obs = _interleave_obs()
    folds = fold_membership(obs, {"method": "INTERLEAVED_HOLES_WITHIN_LINE", "n_folds": 5})
    order = {"L0": ["H00", "H01", "H03", "H02", "H04", "H05", "H06"], "L1": ["K01", "K02"]}
    checked = 0
    for fold in folds:
        test_holes = {obs.holes[int(h)] for h in obs.hole[fold["test"]]}
        train_holes = {obs.holes[int(h)] for h in obs.hole[~fold["test"]]}
        for seq in order.values():
            for k, h in enumerate(seq):
                if h not in test_holes:
                    continue
                checked += 1
                for j in (k - 1, k + 1):
                    if 0 <= j < len(seq):
                        assert seq[j] in train_holes
    assert checked == 9

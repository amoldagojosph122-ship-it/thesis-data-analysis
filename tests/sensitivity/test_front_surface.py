"""Unit tests for the weathering-front surface sensitivity analysis. Synthetic data only; no database is opened."""

import numpy as np
import pytest

from kambale.objective_3 import weathering_front
from kambale.objective_3.config import StopError
from kambale.objective_3.features import Observations
from kambale.sensitivity import front_surface as fs

CONSTANT = {"variant_id": "TRAINING_MEAN", "method": "CONSTANT_MEAN", "role": "ALTERNATIVE"}
IDW_BASE = {"variant_id": "IDW_P2_K8", "method": "INVERSE_DISTANCE", "power": 2.0, "n_neighbours": 8,
            "role": "BASELINE"}


def _toy():
    """Four holes on two lines; three intervals per hole; z_relative_m = -1, -2, -3 in every hole."""
    holes = ["H1", "H2", "H3", "H4"]
    lines = ["L1", "L2"]
    line_of = [0, 0, 1, 1]
    coords = [(0.0, 0.0), (10.0, 0.0), (0.0, 20.0), (10.0, 20.0)]
    X, hole, line = [], [], []
    for h in range(4):
        for z in (-1.0, -2.0, -3.0):
            X.append([coords[h][0], coords[h][1], z])
            hole.append(h)
            line.append(line_of[h])
    obs = Observations(ids=np.arange(len(X), dtype=np.int64), X=np.array(X), y=np.array([0, 1, 0] * 4),
                       hole=np.array(hole), line=np.array(line), holes=holes, lines=lines,
                       feature_names=["easting_m", "northing_m", "z_relative_m"])
    fronts = {"H1": (0.0, 0.0, -1.5), "H2": (10.0, 0.0, -2.5), "H3": (0.0, 20.0, -3.5), "H4": (10.0, 20.0, -4.5)}
    return obs, fronts


def test_constant_mean_is_leave_own_hole_out_and_uses_training_holes_only():
    obs, fronts = _toy()
    train_idx = np.arange(0, 9)          # holes H1, H2, H3
    test_idx = np.arange(9, 12)          # hole H4
    feat = fs.variant_feature(obs, train_idx, test_idx, fronts, CONSTANT, 0.001)
    Z = obs.X[:, 2]
    # Training row of H1: mean of the other training fronts H2, H3 = (-2.5 - 3.5) / 2 = -3.0
    assert np.allclose(feat["train"][0:3], -3.0 - Z[0:3])
    # Training row of H2: mean of H1, H3 = (-1.5 - 3.5) / 2 = -2.5
    assert np.allclose(feat["train"][3:6], -2.5 - Z[3:6])
    # Training row of H3: mean of H1, H2 = (-1.5 - 2.5) / 2 = -2.0
    assert np.allclose(feat["train"][6:9], -2.0 - Z[6:9])
    # Test rows: mean of all usable training fronts = (-1.5 - 2.5 - 3.5) / 3 = -2.5
    assert np.allclose(feat["test"], -2.5 - Z[9:12])
    assert feat["training_holes"] == ["H1", "H2", "H3"]


def test_constant_mean_never_reads_test_hole_fronts():
    obs, fronts = _toy()
    train_idx = np.arange(0, 9)
    test_idx = np.arange(9, 12)
    base = fs.variant_feature(obs, train_idx, test_idx, fronts, CONSTANT, 0.001)
    altered = dict(fronts)
    altered["H4"] = (10.0, 20.0, -99.0)  # a test hole's front changed drastically
    again = fs.variant_feature(obs, train_idx, test_idx, altered, CONSTANT, 0.001)
    assert np.array_equal(base["train"], again["train"])
    assert np.array_equal(base["test"], again["test"])
    assert "H4" not in again["surface_holes"]


def test_inverse_distance_variant_equals_feature_for_fold():
    obs, fronts = _toy()
    train_idx = np.arange(0, 9)
    test_idx = np.arange(9, 12)
    via_variant = fs.variant_feature(obs, train_idx, test_idx, fronts, IDW_BASE, 0.001)
    direct = weathering_front.feature_for_fold(obs, train_idx, test_idx, fronts, power=2.0, k=8, coincident=0.001)
    assert np.array_equal(via_variant["train"], direct["train"])
    assert np.array_equal(via_variant["test"], direct["test"])
    assert via_variant["surface_holes"] == direct["surface_holes"]


def test_paired_bootstrap_identical_inputs_gives_zero_interval():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, size=60).astype(float)
    p = rng.uniform(0.05, 0.95, size=60)
    hole = np.repeat(np.arange(12), 5)
    reps = fs.draw_replicates(hole, 200, np.random.default_rng(7))
    res = fs.paired_interval(y, p, p, reps)
    assert res["diff"] == 0.0
    assert res["ci_low"] == 0.0 and res["ci_high"] == 0.0
    assert res["status"] == "UNRESOLVED"


def test_paired_bootstrap_resolves_a_clear_difference():
    y = np.array([0.0, 1.0] * 40)
    good = np.where(y == 1, 0.9, 0.1)
    bad = np.full(80, 0.5)
    hole = np.repeat(np.arange(16), 5)
    reps = fs.draw_replicates(hole, 300, np.random.default_rng(3))
    res = fs.paired_interval(y, bad, good, reps)
    assert res["diff"] > 0
    assert res["ci_low"] > 0
    assert res["status"] == "RESOLVED"


def test_replicates_draw_whole_holes_with_replacement():
    hole = np.repeat(np.arange(5), [2, 3, 4, 1, 5])
    reps = fs.draw_replicates(hole, 20, np.random.default_rng(0))
    assert len(reps) == 20
    for idx in reps:
        # every interval of a drawn hole appears with that hole's full count
        counts = np.bincount(hole[idx], minlength=5)
        per_hole = np.bincount(hole, minlength=5)
        assert np.all(counts % per_hole == 0)


def test_constant_mean_front_skill_ratio_is_one():
    _, fronts = _toy()
    line_of = {"H1": "L1", "H2": "L1", "H3": "L2", "H4": "L2"}
    rows = fs.front_skill_rows(fronts, line_of, [CONSTANT], 0.001)
    assert {r["scheme"] for r in rows} == set(fs.SCHEMES)
    for r in rows:
        assert r["skill_ratio"] == pytest.approx(1.0)


def test_conclusion_rule_mapping():
    assert fs.conclusion_for(0, 0) == "ROBUST"
    assert fs.conclusion_for(0, 1) == "SELECTION_SENSITIVE"
    assert fs.conclusion_for(1, 0) == "PERFORMANCE_SENSITIVE"
    assert fs.conclusion_for(3, 4) == "PERFORMANCE_SENSITIVE"


def test_acceptance_passes_for_identical_and_stops_for_a_difference():
    n = 10
    vec = {c: np.linspace(0.1, 0.9, n) for c in fs.REFITTED}
    stored = {c: vec[c].copy() for c in fs.REFITTED}
    maxima = fs.acceptance_check("TEST-PLAN", vec, stored)
    assert all(v == 0.0 for v in maxima.values())
    stored["M2_RF_WF"][3] += 1e-6
    with pytest.raises(StopError, match="M2_RF_WF"):
        fs.acceptance_check("TEST-PLAN", vec, stored)


def test_specification_parses_as_written():
    spec, sha, repaired = fs.load_spec()
    assert repaired is False
    assert len(sha) == 64
    assert spec["surface_variants_options"]["coincident_distance_m"] == pytest.approx(0.001)
    variants = fs.ordered_variants(spec, quick=False)
    assert variants[0]["role"] == "BASELINE" and len(variants) == 7
    assert [v["variant_id"] for v in fs.ordered_variants(spec, quick=True)] == ["IDW_P2_K8"]

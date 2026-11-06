"""Model grids, inner spatial tuning, threshold selection and calibration on controlled synthetic cases."""

import numpy as np
import pytest

from kambale.objective_3 import models
from kambale.objective_3.config import O3_CONFIG_PATH, load_config


@pytest.fixture(scope="module")
def config():
    cfg, _ = load_config(O3_CONFIG_PATH)
    return cfg


def test_grids_match_declared_configuration(config):
    assert models.grid("BASE_PREVALENCE", config) == [{}]
    assert len(models.grid("M2_RF", config)) == 4
    assert len(models.grid("M2_HGB", config)) == 8
    assert len(models.grid("BASE_LOGISTIC", config)) == 3


def _synthetic(n=180, seed=11):
    rng = np.random.default_rng(seed)
    hole = rng.integers(0, 20, n)
    X = np.column_stack([rng.uniform(0, 300, n), rng.uniform(0, 100, n), rng.uniform(-40, -1, n)])
    logit = -1.0 + 0.012 * X[:, 0] - 0.02 * np.abs(X[:, 2] + 20.0)
    p = 1.0 / (1.0 + np.exp(-logit))
    y = (rng.uniform(size=n) < p).astype(int)
    return X, y, hole


def test_inner_cv_is_complete_and_bounded(config):
    X, y, hole = _synthetic()
    res = models.inner_cv(X, y, hole, "BASE_LOGISTIC", {"C": 0.1, "class_weight": None, "max_iter": 500}, config, 7)
    assert res["status"] == "COMPLETED"
    assert np.all(np.isfinite(res["p"]))
    assert np.all((res["p"] > 0) & (res["p"] < 1))
    assert len(res["scores"]) == config["inner_cv"]["n_folds"]


def test_inner_cv_uses_whole_holes(config):
    X, y, hole = _synthetic()
    splits = models.inner_folds(hole, config["inner_cv"]["n_folds"], 7)
    for tr, te in splits:
        assert not (set(hole[tr].tolist()) & set(hole[te].tolist()))


def test_youden_threshold_separates_the_classes():
    y = np.array([0] * 90 + [1] * 10)
    p = np.concatenate([np.full(90, 0.10), np.full(10, 0.45)])
    out = models.youden_threshold(y, p, config_thresholds(), 1e-6)
    assert 0.10 < out["threshold"] <= 0.45
    assert out["youden_j"] == pytest.approx(1.0)
    assert out["source"] == "INNER_CV_MAX_YOUDEN_J_TIE_CLOSEST_TO_HALF"


def test_youden_threshold_breaks_flat_ties_at_half():
    y = np.array([0] * 70 + [1] * 30)
    p = np.full(100, 0.30)
    out = models.youden_threshold(y, p, config_thresholds(), 1e-6)
    assert out["threshold"] == 0.5


def config_thresholds():
    return [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


def test_platt_fit_is_bounded_and_monotone(config):
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 200)
    p = np.clip(0.1 + 0.7 * y + rng.normal(0, 0.05, 200), 1e-4, 1 - 1e-4)
    fit = models.platt_fit(y, p, config)
    assert fit["status"] == "FITTED"
    out = models.platt_apply(np.array([0.1, 0.5, 0.9]), fit, 1e-6)
    assert np.all((out > 0) & (out < 1))
    assert out[0] < out[1] < out[2]
    assert fit["slope"] > 0


def test_platt_skips_single_class(config):
    fit = models.platt_fit(np.zeros(50, dtype=int), np.full(50, 0.2), config)
    assert fit["status"] == "SKIPPED"

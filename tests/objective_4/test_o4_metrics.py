"""Probability metrics and calibration diagnostics on controlled synthetic cases."""

import numpy as np
import pytest

from kambale.objective_4 import metrics


def test_brier_matches_independent_loop():
    y = np.array([0, 1, 1, 0, 1], dtype=float)
    p = np.array([0.1, 0.8, 0.6, 0.3, 0.9])
    w = np.array([1.0, 2.0, 1.0, 0.5, 1.0])
    assert metrics.brier(y, p, w) == pytest.approx(metrics.independent_brier(y, p, w))


def test_log_loss_known_value():
    y = np.array([0, 1], dtype=float)
    p = np.array([0.25, 0.75])
    w = np.ones(2)
    expected = -(np.log(0.75) + np.log(0.75)) / 2.0
    assert metrics.log_loss(y, p, w) == pytest.approx(expected)


def test_auc_undefined_for_one_class():
    y = np.zeros(10, dtype=float)
    p = np.linspace(0, 1, 10)
    w = np.ones(10)
    value, status, reason = metrics.roc_auc(y, p, w)
    assert value is None and status == "UNDEFINED" and "one class" in reason
    value, status, reason = metrics.pr_auc(y, p, w)
    assert value is None and status == "UNDEFINED"


def test_confusion_zero_denominators_are_undefined():
    c = metrics.confusion(np.zeros(5, dtype=int), np.full(5, 0.2), 0.5)
    assert c["tp"] == 0 and c["fp"] == 0 and c["tn"] == 5 and c["fn"] == 0
    assert c["precision"] is None
    assert c["status"] == "UNDEFINED"


def test_calibration_fit_recovers_reasonable_slope():
    rng = np.random.default_rng(4)
    n = 500
    p = rng.uniform(0.05, 0.95, n)
    y = (rng.uniform(size=n) < p).astype(int)
    out = metrics.calibration_fit(y, p, np.ones(n))
    assert out["status"] == "DEFINED"
    assert 0.5 < out["slope"] < 2.0
    assert abs(out["intercept"]) < 0.5


def test_wilson_interval_bounds():
    lo, hi = metrics.wilson_interval(0, 10)
    assert lo == pytest.approx(0.0)
    assert 0.0 < hi < 0.35
    lo, hi = metrics.wilson_interval(10, 10)
    assert 0.65 < lo < 1.0
    assert hi == pytest.approx(1.0)


def test_reliability_bins_merge_small_bins():
    rng = np.random.default_rng(5)
    n = 120
    p = rng.uniform(0, 1, n)
    y = (rng.uniform(size=n) < p).astype(int)
    bins = metrics.reliability_bins(y, p, np.ones(n), [i / 10 for i in range(11)], min_n=20)
    assert bins
    assert sum(b["n"] for b in bins) == n
    assert all(b["n"] >= 20 or b is bins[-1] for b in bins)


def test_ece_from_bins():
    bins = [{"n": 50, "mean_p": 0.2, "observed_rate": 0.3}, {"n": 50, "mean_p": 0.8, "observed_rate": 0.7}]
    value, status = metrics.ece_from_bins(bins)
    assert value == pytest.approx(0.1)
    assert status == "DEFINED"

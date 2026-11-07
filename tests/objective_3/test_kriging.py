"""Covariance grid, tie rule, pure-nugget kriging and neighbourhoods on controlled synthetic cases (unit tests only)."""

import numpy as np
import pytest

from kambale.objective_3 import kriging
from kambale.objective_3.config import O3_CONFIG_PATH, load_config


@pytest.fixture(scope="module")
def config():
    cfg, _ = load_config(O3_CONFIG_PATH)
    return cfg


def test_covariance_grid_is_the_predeclared_grid(config):
    grid = kriging.covariance_grid(config)
    assert len(grid) == 3 * 5 + 1
    assert kriging.is_pure(grid[-1])
    assert all(g["covariance"] == "EXPONENTIAL" and g["model"] == "exponential" for g in grid[:-1])
    assert {g["range_m"] for g in grid[:-1]} == {25.0, 50.0, 100.0, 200.0, 400.0}
    assert {g["nugget_fraction"] for g in grid[:-1]} == {0.25, 0.5, 0.75}


def test_tie_rule_prefers_pure_then_larger_nugget_then_shorter_range():
    pure = {"covariance": kriging.PURE_NUGGET}
    a = {"covariance": "EXPONENTIAL", "model": "exponential", "range_m": 50.0, "nugget_fraction": 0.5}
    b = {"covariance": "EXPONENTIAL", "model": "exponential", "range_m": 50.0, "nugget_fraction": 0.75}
    c = {"covariance": "EXPONENTIAL", "model": "exponential", "range_m": 25.0, "nugget_fraction": 0.75}
    tied = [{"params": a, "mean": 0.4}, {"params": b, "mean": 0.4}, {"params": c, "mean": 0.4}]
    assert kriging.select_covariance(tied)["params"] is c
    assert kriging.select_covariance(tied + [{"params": pure, "mean": 0.4}])["params"] is pure
    assert kriging.select_covariance([{"params": a, "mean": 0.41}, {"params": b, "mean": 0.40}])["params"] is b


def test_no_usable_trial_gives_no_choice():
    assert kriging.select_covariance([{"params": {"covariance": "PURE_NUGGET"}, "mean": None}]) is None


def test_pure_nugget_returns_the_known_mean_exactly(config):
    X = np.array([[0.0, 0.0, -5.0], [10.0, 0.0, -5.0], [20.0, 0.0, -5.0], [5.0, 3.0, -6.0]])
    values = np.array([1.0, 0.0, 1.0, 0.0])
    test = np.array([[7.0, 1.0, -5.5], [30.0, 0.0, -5.0]])
    out = kriging.simple_kriging(X, values, test, {"covariance": kriging.PURE_NUGGET}, 0.25, config, mean=0.37)
    assert np.all(out["p"] == 0.37)


def test_exponential_with_zero_nugget_reproduces_training_values(config):
    # Six points so that the configured minimum of five neighbours is met at every training location.
    X = np.array([[0.0, 0.0, -5.0], [10.0, 0.0, -5.0], [20.0, 0.0, -5.0], [5.0, 4.0, -5.0], [12.0, 6.0, -5.0],
                  [2.0, 9.0, -5.0]])
    values = np.array([0.2, 0.8, 0.4, 0.5, 0.6, 0.3])
    cov = {"covariance": "EXPONENTIAL", "model": "exponential", "range_m": 30.0, "nugget_fraction": 0.0}
    out = kriging.simple_kriging(X, values, X, cov, 0.25, config, mean=0.0)
    assert np.allclose(out["p"], values, atol=1e-5)


def test_kriging_falls_back_outside_the_depth_band(config):
    X = np.array([[0.0, 0.0, -5.0], [10.0, 0.0, -5.0], [20.0, 0.0, -5.0], [5.0, 0.0, -5.5], [6.0, 0.0, -6.0]])
    values = np.array([0.2, 0.8, 0.4, 0.3, 0.6])
    test = np.array([[5.0, 0.0, -50.0]])
    cov = {"covariance": "EXPONENTIAL", "model": "exponential", "range_m": 100.0, "nugget_fraction": 0.5}
    out = kriging.simple_kriging(X, values, test, cov, 0.25, config, mean=0.37)
    assert out["fallback"][0]
    assert out["p"][0] == pytest.approx(0.37)


def test_neighbourhoods_respect_band_and_cap(config):
    rng = np.random.default_rng(5)
    train = np.column_stack([rng.uniform(0, 300, 400), rng.uniform(0, 100, 400), rng.uniform(-40, -1, 400)])
    test = train[:3]
    neigh = kriging.neighbourhoods(train, test, config)
    for nb, point in zip(neigh, test):
        idx, d2 = nb
        assert idx.size <= config["kriging"]["max_neighbours"]
        assert np.all(np.abs(train[idx, 2] - point[2]) <= config["kriging"]["depth_band_m"])
        if idx.size == config["kriging"]["max_neighbours"]:
            kept = set(idx.tolist())
            band = np.nonzero(np.abs(train[:, 2] - point[2]) <= config["kriging"]["depth_band_m"])[0]
            d2_all = (train[band, 0] - point[0]) ** 2 + (train[band, 1] - point[1]) ** 2
            nearest = set(band[np.argsort(d2_all, kind="stable")[:config["kriging"]["max_neighbours"]]].tolist())
            assert kept == nearest

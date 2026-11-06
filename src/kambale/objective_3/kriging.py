"""Simple kriging for the indicator (M1) and the residual (M3) fields, with covariance chosen by inner cross-validation.

Covariance model: exponential, C(h) = c1 * exp(-3h / a) for h > 0 and C(0) = c0 + c1 = sill, with the practical range a
(the same convention as the Objective 2 exponential model). The predeclared grid is range a x nugget fraction, plus
PURE_NUGGET, for which c1 = 0: the field has no spatial correlation and simple kriging returns the known mean exactly.

Neighbourhoods depend only on coordinates, so they are computed once per (training set, prediction set) and reused across
every covariance grid point. A prediction point with fewer than min_neighbours training values in its depth band falls
back to the mean, and the fallback is recorded.
"""

from __future__ import annotations

import math

import numpy as np

PURE_NUGGET = "PURE_NUGGET"


def covariance_grid(config: dict) -> list[dict]:
    """Every predeclared covariance, in declaration order: exponential grid points, then PURE_NUGGET when included."""
    kc = config["kriging"]
    grid = []
    for nf in kc["grid"]["nugget_fraction"]:
        for a in kc["grid"]["range_m"]:
            grid.append({"covariance": "EXPONENTIAL", "model": kc["model"], "range_m": float(a),
                         "nugget_fraction": float(nf)})
    if kc.get("include_pure_nugget", False):
        grid.append({"covariance": PURE_NUGGET, "model": None, "range_m": None, "nugget_fraction": None})
    return grid


def is_pure(covariance: dict) -> bool:
    return covariance["covariance"] == PURE_NUGGET


def structure(covariance: dict, sill: float) -> tuple[float, float, float | None]:
    """(nugget c0, structured sill c1, range a) for a total sill. PURE_NUGGET gives c1 = 0 and no range."""
    if is_pure(covariance):
        return float(sill), 0.0, None
    c0 = float(covariance["nugget_fraction"]) * float(sill)
    return c0, float(sill) - c0, float(covariance["range_m"])


def tie_key(covariance: dict) -> tuple:
    """Tie rule when two covariances have the same inner score: PURE_NUGGET first, then the larger nugget fraction,
    then the shorter range."""
    if is_pure(covariance):
        return (0, 0.0, 0.0)
    return (1, -float(covariance["nugget_fraction"]), float(covariance["range_m"]))


def select_covariance(trials: list[dict]) -> dict | None:
    """The trial with the lowest inner mean log loss, ties broken by tie_key. Trials carry 'params' and 'mean'."""
    usable = [t for t in trials if t.get("mean") is not None and math.isfinite(t["mean"])]
    if not usable:
        return None
    return min(usable, key=lambda t: (round(float(t["mean"]), 12), tie_key(t["params"])))


def neighbourhoods(train_xyz: np.ndarray, test_xyz: np.ndarray, config: dict) -> list:
    """Per prediction point: None when too few training values lie in the depth band, else (indices, squared lateral
    distances) of the nearest max_neighbours training values inside the band."""
    kc = config["kriging"]
    band = float(kc["depth_band_m"])
    min_n = int(kc["min_neighbours"])
    max_n = int(kc["max_neighbours"])
    out = []
    for point in test_xyz:
        idx = np.nonzero(np.abs(train_xyz[:, 2] - point[2]) <= band)[0]
        if idx.size < min_n:
            out.append(None)
            continue
        d2 = (train_xyz[idx, 0] - point[0]) ** 2 + (train_xyz[idx, 1] - point[1]) ** 2
        if idx.size > max_n:
            order = np.argsort(d2, kind="stable")[:max_n]
            idx, d2 = idx[order], d2[order]
        out.append((idx, d2))
    return out


def _cov(h: np.ndarray, c1: float, a: float | None, sill: float) -> np.ndarray:
    out = np.zeros_like(h, dtype=np.float64)
    if c1 > 0.0 and a is not None:
        out = c1 * np.exp(-3.0 * h / a)
    out[h <= 0.0] = sill
    return out


def simple_kriging(train_xyz: np.ndarray, train_values: np.ndarray, test_xyz: np.ndarray, covariance: dict,
                   sill: float, config: dict, *, mean: float, neigh: list | None = None) -> dict:
    """Simple kriging of `train_values` at `test_xyz` with the given covariance and total sill.

    Returns predictions before any clipping by the caller, together with the fallback and the out-of-[0,1] flags.
    A PURE_NUGGET covariance returns the mean exactly.
    """
    kc = config["kriging"]
    if neigh is None:
        neigh = neighbourhoods(train_xyz, test_xyz, config)
    c0, c1, a = structure(covariance, sill)
    jitter = float(kc["jitter_fraction_of_sill"]) * max(float(sill), 1e-12)
    n_test = test_xyz.shape[0]
    pred = np.full(n_test, float(mean), dtype=np.float64)
    fallback = np.zeros(n_test, dtype=bool)
    outside = np.zeros(n_test, dtype=bool)
    neighbours = np.zeros(n_test, dtype=np.int64)
    pure = is_pure(covariance)
    for i, nb in enumerate(neigh):
        if nb is None:
            fallback[i] = True
            continue
        idx, d2 = nb
        neighbours[i] = idx.size
        if pure:
            continue
        h_train = np.sqrt((train_xyz[idx, 0][:, None] - train_xyz[idx, 0][None, :]) ** 2 +
                          (train_xyz[idx, 1][:, None] - train_xyz[idx, 1][None, :]) ** 2)
        K = _cov(h_train, c1, a, sill)
        np.fill_diagonal(K, sill + jitter)
        k_vec = _cov(np.sqrt(d2), c1, a, sill)
        try:
            w = np.linalg.solve(K, k_vec)
        except np.linalg.LinAlgError:
            fallback[i] = True
            continue
        value = float(mean) + float(w @ (train_values[idx] - float(mean)))
        if value < 0.0 or value > 1.0:
            outside[i] = True
        pred[i] = value
    return {"p": pred, "fallback": fallback, "outside": outside, "neighbours": neighbours, "mean": float(mean)}

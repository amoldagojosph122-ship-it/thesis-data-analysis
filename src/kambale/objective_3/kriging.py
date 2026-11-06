"""Simple kriging for the indicator (M1) and residual (M3) models.

The equations are implemented here, not delegated to a continuous-variable kriging package: a binary indicator and a
residual are both treated as a zero-mean (or known-mean) random field with covariance C(h) = total sill - gamma(h).
The covariance matrix is solved with a small jitter on the diagonal. Every prediction is clipped to the unit interval
and every clipped value is counted. A test point with too few training neighbours inside the variogram's depth band
falls back to the training mean, and the fallback is recorded.
"""

from __future__ import annotations

import numpy as np

from kambale.objective_2.fitting import gamma_model


def _covariance(h: np.ndarray, model: str, c0: float, c1: float, a: float) -> np.ndarray:
    total = c0 + c1
    h = np.asarray(h, dtype=np.float64)
    out = total - gamma_model(h, model, c0, c1, a)
    return np.maximum(out, 0.0)


def simple_kriging(train_xyz: np.ndarray, train_values: np.ndarray, test_xyz: np.ndarray, model: str,
                   params, config: dict, *, mean: float) -> dict:
    """Krige `train_values` to `test_xyz`. Returns predictions, clipping and fallback flags, and neighbour counts."""
    c0, c1, a = (float(x) for x in params)
    total = c0 + c1
    kcfg = config["variogram"]["kriging"]
    band = float(config["variogram"]["max_abs_dz_m"])
    min_n = int(kcfg["min_neighbours"])
    max_n = int(kcfg["max_neighbours"])
    jitter = float(kcfg["jitter_fraction_of_sill"]) * max(total, 1e-12)
    pred = np.full(test_xyz.shape[0], mean, dtype=np.float64)
    fallback = np.zeros(test_xyz.shape[0], dtype=bool)
    clipped = np.zeros(test_xyz.shape[0], dtype=bool)
    neighbours = np.zeros(test_xyz.shape[0], dtype=np.int64)
    variance = np.full(test_xyz.shape[0], total, dtype=np.float64)
    for i, point in enumerate(test_xyz):
        in_band = np.abs(train_xyz[:, 2] - point[2]) <= band
        idx = np.nonzero(in_band)[0]
        if idx.size < min_n:
            fallback[i] = True
            continue
        d2 = (train_xyz[idx, 0] - point[0]) ** 2 + (train_xyz[idx, 1] - point[1]) ** 2
        if idx.size > max_n:
            idx = idx[np.argsort(d2, kind="stable")[:max_n]]
            d2 = (train_xyz[idx, 0] - point[0]) ** 2 + (train_xyz[idx, 1] - point[1]) ** 2
        neighbours[i] = idx.size
        h_train = np.sqrt(
            (train_xyz[idx, 0][:, None] - train_xyz[idx, 0][None, :]) ** 2 +
            (train_xyz[idx, 1][:, None] - train_xyz[idx, 1][None, :]) ** 2)
        cov = _covariance(h_train, model, c0, c1, a)
        np.fill_diagonal(cov, total + jitter)
        h_test = np.sqrt(d2)
        c_vec = _covariance(h_test, model, c0, c1, a)
        try:
            w = np.linalg.solve(cov, c_vec)
        except np.linalg.LinAlgError:
            fallback[i] = True
            continue
        value = mean + float(w @ (train_values[idx] - mean))
        variance[i] = max(total - float(w @ c_vec), 0.0)
        if value < 0.0 or value > 1.0:
            clipped[i] = True
            value = min(max(value, 0.0), 1.0)
        pred[i] = value
    return {"p": pred, "fallback": fallback, "clipped": clipped, "neighbours": neighbours,
            "variance": variance, "mean": mean}

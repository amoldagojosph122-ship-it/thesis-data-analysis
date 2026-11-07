"""Vectorised weathering-front surface and design matrices, equal to the Objective 3 rule.

The Objective 3 inverse-distance function (weathering_front.idw) loops over query points in Python. Objective 5 evaluates the
same rule for whole arrays at once. The equality with the Objective 3 function is tested (tests/objective_5) and gated
(verify, tolerance 1e-9). Own-hole exclusion is expressed by an index per query row; a row whose hole is not among the
front points is not excluded.
"""

from __future__ import annotations

import numpy as np

COLUMN_SOURCE = {"easting_m", "northing_m", "z_relative_m", "depth_below_weathering_front_m"}


def idw_vectorised(points_xy, values, query_xy, exclude=None, power: float = 2.0, k: int = 8,
                   coincident: float = 0.001) -> np.ndarray:
    """Inverse-distance-weighted values at the query points from the k nearest front points.

    exclude: optional integer array (one per query row). A value >= 0 is the index of a front point that must not be used
    for that row (the row's own hole). A value of -1 excludes nothing.
    """
    pts = np.asarray(points_xy, dtype=np.float64).reshape(-1, 2)
    vals = np.asarray(values, dtype=np.float64).ravel()
    q = np.asarray(query_xy, dtype=np.float64).reshape(-1, 2)
    nq = q.shape[0]
    out = np.full(nq, np.nan)
    if pts.shape[0] == 0 or nq == 0:
        return out
    if pts.shape[0] != vals.size:
        raise ValueError("idw: one value per front point is required")
    d = np.sqrt(((q[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2))
    if exclude is not None:
        ex = np.asarray(exclude, dtype=np.int64).ravel()
        rows = np.where(ex >= 0)[0]
        d[rows, ex[rows]] = np.inf
    kk = min(int(k), pts.shape[0])
    order = np.argsort(d, axis=1, kind="stable")[:, :kk]
    dk = np.take_along_axis(d, order, axis=1)
    vk = vals[order]
    finite = np.isfinite(dk)
    safe = np.where(dk > 0.0, dk, 1.0)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        w = np.where(finite, 1.0 / safe ** float(power), 0.0)
    wsum = w.sum(axis=1)
    num = (w * np.where(finite, vk, 0.0)).sum(axis=1)
    ok = wsum > 0.0
    out[ok] = num[ok] / wsum[ok]
    coinc = dk[:, 0] < coincident
    out[coinc] = vk[coinc, 0]
    return out


def front_surface(front_xy, front_z, query_xy, exclude=None, power: float = 2.0, k: int = 8,
                  coincident: float = 0.001) -> np.ndarray:
    """Front height (z_relative of the front, negative below collar) at query points."""
    return idw_vectorised(front_xy, front_z, query_xy, exclude=exclude, power=power, k=k, coincident=coincident)


def depth_below_front(surface_z, z_relative) -> np.ndarray:
    """depth_below_weathering_front_m = front_z_hat - z_relative_m; positive below the modelled front."""
    return np.asarray(surface_z, dtype=np.float64) - np.asarray(z_relative, dtype=np.float64)


def design_matrix(columns, *, easting, northing, z, dbf=None) -> np.ndarray:
    """Columns in the order given by the predictor set. Only the four predictors of Objective 3 may appear."""
    unknown = set(columns) - COLUMN_SOURCE
    if unknown:
        raise ValueError(f"predictors outside the Objective 3 set: {sorted(unknown)}")
    source = {"easting_m": easting, "northing_m": northing, "z_relative_m": z,
              "depth_below_weathering_front_m": dbf}
    cols = []
    for name in columns:
        if source[name] is None:
            raise ValueError(f"predictor {name} requested without a front feature")
        cols.append(np.asarray(source[name], dtype=np.float64))
    return np.column_stack(cols)

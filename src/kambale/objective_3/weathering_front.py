"""Fold-safe depth-below-weathering-front predictor.

For every hole, the front is the shallowest logged interval whose weathering code is in the configured front codes. Its
height is front_z = a * depth_from, with a the least-squares slope through the origin of z_relative_m on midpoint_m over
all logged intervals of that hole, and its location is that interval's easting and northing.

A surface of front heights is interpolated by inverse-distance weighting from the fronts of the outer-training holes.
A training row takes the surface built from the other training holes (its own hole is left out); a test row takes the
surface built from all training holes. Test holes never contribute to any value. The predictor is
depth_below_weathering_front_m = front_z_hat(E, N) - z_relative_m, positive below the modelled front.
"""

from __future__ import annotations

import numpy as np

from kambale.objective_3.config import StopError

FRONT_NAME = "depth_below_weathering_front_m"


def hole_fronts(conn, receipt_id: int, front_codes, override_codes: dict | None = None) -> dict:
    """Front of every hole that has one: hole_id -> (easting_m, northing_m, front_z_m).

    The query reads every interval of the receipt, binary or not. `override_codes` replaces the weathering code of all
    intervals of the named holes before the front is found; it exists so that the fold-safety audit can alter the codes
    of test holes and confirm that no training value moves.
    """
    codes = set(front_codes)
    rows = conn.execute(
        "SELECT hole_id, depth_from_m, midpoint_m, z_relative_m, easting_m, northing_m, weathering_code "
        "FROM analysis_observations WHERE receipt_id = ? ORDER BY hole_id, upstream_interval_id", (receipt_id,)).fetchall()
    per_hole: dict[str, list] = {}
    for r in rows:
        code = r["weathering_code"]
        if override_codes is not None and r["hole_id"] in override_codes:
            code = override_codes[r["hole_id"]]
        per_hole.setdefault(r["hole_id"], []).append(
            (float(r["depth_from_m"]), float(r["midpoint_m"]), float(r["z_relative_m"]), float(r["easting_m"]),
             float(r["northing_m"]), code))
    out = {}
    for hole, items in per_hole.items():
        front = [it for it in items if it[5] in codes]
        if not front:
            continue
        mid = np.array([it[1] for it in items], dtype=np.float64)
        zrel = np.array([it[2] for it in items], dtype=np.float64)
        den = float(np.sum(mid * mid))
        if den <= 0.0:
            raise StopError(f"hole {hole} has no non-zero midpoint for the front slope")
        slope = float(np.sum(mid * zrel) / den)
        depth, _, _, easting, northing, _ = min(front, key=lambda it: it[0])
        out[hole] = (easting, northing, slope * depth)
    return out


def idw(points_xy, values, query_xy, power: float = 2.0, k: int = 8, coincident: float = 0.001) -> np.ndarray:
    """Inverse-distance-weighted interpolation from the k nearest points.

    A query closer than `coincident` metres to a point returns that point's value exactly.
    """
    pts = np.asarray(points_xy, dtype=np.float64).reshape(-1, 2)
    vals = np.asarray(values, dtype=np.float64).ravel()
    qry = np.asarray(query_xy, dtype=np.float64).reshape(-1, 2)
    if pts.shape[0] == 0:
        return np.full(qry.shape[0], np.nan)
    if pts.shape[0] != vals.size:
        raise ValueError("idw: one value per point is required")
    kk = min(int(k), pts.shape[0])
    dist = np.sqrt(((qry[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2))
    out = np.empty(qry.shape[0], dtype=np.float64)
    for i in range(qry.shape[0]):
        order = np.argsort(dist[i], kind="stable")[:kk]
        d = dist[i, order]
        if d[0] < coincident:
            out[i] = vals[order[0]]
            continue
        w = 1.0 / d ** float(power)
        out[i] = float(np.sum(w * vals[order]) / np.sum(w))
    return out


def feature_for_fold(obs, train_idx, test_idx, fronts: dict, *, power: float = 2.0, k: int = 8,
                     coincident: float = 0.001) -> dict:
    """Per-fold values of depth_below_weathering_front_m for the training and test rows of one outer fold.

    Returns {"train": array aligned with train_idx, "test": array aligned with test_idx, "surface_holes": hole ids that
    supplied a front to the test surface, "training_holes": hole ids of the outer-training fold}. Test holes cannot
    appear in the surface because the surface is built only from training holes.
    """
    train_idx = np.asarray(train_idx, dtype=np.int64)
    test_idx = np.asarray(test_idx, dtype=np.int64)
    training_holes = sorted({obs.holes[int(h)] for h in obs.hole[train_idx]})
    usable = [h for h in training_holes if h in fronts]
    if not usable:
        raise StopError("no training hole has a weathering front in this outer fold")
    xy = {h: (fronts[h][0], fronts[h][1]) for h in usable}
    fz = {h: fronts[h][2] for h in usable}
    E, N, Z = obs.X[:, 0], obs.X[:, 1], obs.X[:, 2]

    train_vals = np.full(train_idx.size, np.nan, dtype=np.float64)
    train_hole_of = np.array([obs.holes[int(h)] for h in obs.hole[train_idx]], dtype=object)
    for h in set(train_hole_of.tolist()):
        others = [g for g in usable if g != h]
        rows = np.where(train_hole_of == h)[0]
        if not others:
            raise StopError(f"no other training front to interpolate for hole {h}")
        pts = np.array([xy[g] for g in others])
        vals = np.array([fz[g] for g in others])
        surface = idw(pts, vals, np.column_stack([E[train_idx[rows]], N[train_idx[rows]]]), power, k, coincident)
        train_vals[rows] = surface - Z[train_idx[rows]]

    pts = np.array([xy[g] for g in usable])
    vals = np.array([fz[g] for g in usable])
    test_surface = idw(pts, vals, np.column_stack([E[test_idx], N[test_idx]]), power, k, coincident)
    test_vals = test_surface - Z[test_idx]
    if not (np.all(np.isfinite(train_vals)) and np.all(np.isfinite(test_vals))):
        raise StopError("the weathering-front surface is undefined for some rows")
    return {"train": train_vals, "test": test_vals, "surface_holes": usable, "training_holes": training_holes}


def fold_safety_check(conn, receipt_id: int, obs, train_idx, test_idx, front_codes, *, power: float = 2.0,
                      k: int = 8, coincident: float = 0.001) -> dict:
    """Recompute the fold's feature after the test holes' weathering codes are altered; report PASS or FAIL.

    PASS requires (a) no test hole supplies a front to the surface, and (b) the training and test values are unchanged
    when every test hole's weathering codes are replaced by a non-front code.
    """
    test_holes = sorted({obs.holes[int(h)] for h in obs.hole[np.asarray(test_idx, dtype=np.int64)]})
    fronts = hole_fronts(conn, receipt_id, front_codes)
    base = feature_for_fold(obs, train_idx, test_idx, fronts, power=power, k=k, coincident=coincident)
    altered_fronts = hole_fronts(conn, receipt_id, front_codes,
                                 override_codes={h: None for h in test_holes})
    altered = feature_for_fold(obs, train_idx, test_idx, altered_fronts, power=power, k=k, coincident=coincident)
    contributing_test = sorted(set(base["surface_holes"]) & set(test_holes))
    same_test = np.allclose(base["test"], altered["test"], rtol=0.0, atol=1e-12)
    same_train = np.allclose(base["train"], altered["train"], rtol=0.0, atol=1e-12)
    ok = not contributing_test and same_test and same_train
    detail = (f"{len(test_holes)} test holes altered; {len(base['surface_holes'])} surface holes; "
              f"test holes contributing to the surface: {len(contributing_test)}; test values unchanged: {same_test}; "
              f"training values unchanged: {same_train}")
    return {"status": "PASS" if ok else "FAIL", "detail": detail,
            "surface_holes": base["surface_holes"], "test_holes": test_holes}

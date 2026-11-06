"""Relative grid, support zones, depth support, weathering-front feature and full-data probabilities.

The grid spans the collar bounding box expanded by GRID_MARGIN_M and snapped outward to the cell size (10 x 10 m). The
vertical axis is depth relative to collar (z_relative_m, -56 to 0 m, 2 m cells; cell centres). Each cell takes the zone of
its horizontal centre by lateral distance to the nearest collar. INTERPOLATION cells are predicted by the tier-2 models,
EXTRAPOLATION cells by the tier-1 models, and NO_SUPPORT cells carry no probability.
"""

from __future__ import annotations

import json

import joblib
import numpy as np
from scipy.spatial import cKDTree

from kambale.objective_5.config import (EXTRAPOLATION, GRID_MARGIN_M, INTERPOLATION, NO_SUPPORT, PROJECT_ROOT,
                                        StopError, TIER_OF_ZONE, O3_CONFIG_PATH, sha256_file, utc_now, zone_limits)
from kambale.objective_5.front import depth_below_front, design_matrix, front_surface
from kambale.objective_5.refit import front_settings, load_fronts
from kambale.objective_3.config import load_config as load_o3_config

DEPTH_BAND_M = 10.0          # depth bands for the summary tables (the configuration's O5-T01 wording: "10 m depth band")
SUPPORTED = "SUPPORTED"
DEPTH_EXTRAPOLATED = "DEPTH_EXTRAPOLATED"
INSERT_CHUNK = 100_000


def grid_axes(collars_xy: np.ndarray, cfg: dict) -> dict:
    cs = cfg["grid"]["cell_size_m"]
    ce, cn, cz = float(cs["easting"]), float(cs["northing"]), float(cs["z"])
    zlo, zhi = (float(v) for v in cfg["grid"]["z_range_m"])
    e_min, n_min = collars_xy.min(axis=0)
    e_max, n_max = collars_xy.max(axis=0)
    e0 = np.floor((e_min - GRID_MARGIN_M) / ce) * ce
    e1 = np.ceil((e_max + GRID_MARGIN_M) / ce) * ce
    n0 = np.floor((n_min - GRID_MARGIN_M) / cn) * cn
    n1 = np.ceil((n_max + GRID_MARGIN_M) / cn) * cn
    nE, nN = int(round((e1 - e0) / ce)), int(round((n1 - n0) / cn))
    nZ = int(round((zhi - zlo) / cz))
    if abs(nZ * cz - (zhi - zlo)) > 1e-9:
        raise StopError("the z range is not a whole number of cells")
    return {"e0": float(e0), "n0": float(n0), "nE": nE, "nN": nN, "ce": ce, "cn": cn, "cz": cz, "zlo": zlo,
            "zhi": zhi, "nZ": nZ, "xc": e0 + (np.arange(nE) + 0.5) * ce, "yc": n0 + (np.arange(nN) + 0.5) * cn,
            "zc": zlo + (np.arange(nZ) + 0.5) * cz}


def xy_grid(axes: dict) -> tuple[np.ndarray, np.ndarray]:
    """Horizontal centres in row order: index = iy * nE + ix."""
    XX, YY = np.meshgrid(axes["xc"], axes["yc"])
    return XX.ravel(), YY.ravel()


def deepest_per_hole(o5) -> dict:
    rows = o5.execute("SELECT hole_id, MIN(z_relative_m) AS zmin FROM observations WHERE in_binary_target = 1 "
                      "GROUP BY hole_id ORDER BY hole_id").fetchall()
    return {r["hole_id"]: float(r["zmin"]) for r in rows}


def zone_from_distance(nearest_collar_m, limits: dict) -> np.ndarray:
    """INTERPOLATION when the lateral distance is at most its limit, EXTRAPOLATION at most its limit, else NO_SUPPORT."""
    d = np.asarray(nearest_collar_m, dtype=np.float64)
    zone = np.full(d.shape, NO_SUPPORT, dtype=object)
    zone[d <= limits[EXTRAPOLATION]] = EXTRAPOLATION
    zone[d <= limits[INTERPOLATION]] = INTERPOLATION
    return zone


def deepest_sampled_z(distance_matrix, hole_deepest, radius: float) -> np.ndarray:
    """Per horizontal cell: the deepest sampled z among holes within the radius, or of the nearest hole when none is."""
    D = np.asarray(distance_matrix, dtype=np.float64)
    hd = np.asarray(hole_deepest, dtype=np.float64)
    within = D <= float(radius)
    min_within = np.where(within, hd[None, :], np.inf).min(axis=1)
    nearest = hd[np.argmin(D, axis=1)]
    return np.where(within.any(axis=1), min_within, nearest)


def depth_support_labels(z, deepest) -> np.ndarray:
    """DEPTH_EXTRAPOLATED when z lies strictly below the deepest sampled z of the neighbourhood."""
    z = np.asarray(z, dtype=np.float64)
    deepest = np.asarray(deepest, dtype=np.float64)
    return np.where(z < deepest, DEPTH_EXTRAPOLATED, SUPPORTED)


def xy_level_fields(o5, cfg: dict, axes: dict) -> dict:
    """Zone, nearest-collar distance, deepest sampled z within the neighbourhood, and the front surface per horizontal cell."""
    collars = o5.execute("SELECT hole_id, easting_m, northing_m FROM collars ORDER BY hole_id").fetchall()
    cxy = np.array([[c["easting_m"], c["northing_m"]] for c in collars], dtype=np.float64)
    ids = [c["hole_id"] for c in collars]
    xs, ys = xy_grid(axes)
    xy = np.column_stack([xs, ys])
    tree = cKDTree(cxy)
    nearest_d, _ = tree.query(xy)
    zone = zone_from_distance(nearest_d, zone_limits(cfg))

    deep = deepest_per_hole(o5)
    hole_deep = np.array([deep[h] for h in ids])
    radius = float(cfg["support_zones"]["depth_support"]["neighbourhood_m"])
    D = np.sqrt(((xy[:, None, :] - cxy[None, :, :]) ** 2).sum(axis=2))
    deepest_xy = deepest_sampled_z(D, hole_deep, radius)

    fronts = load_fronts(o5)
    o3_cfg, _ = load_o3_config(O3_CONFIG_PATH)
    fs = front_settings(o3_cfg)
    surf = front_surface(fronts["xy"], fronts["z"], xy, exclude=None, power=fs["power"], k=fs["k"],
                         coincident=fs["coincident"])
    if not np.all(np.isfinite(surf)):
        raise StopError("the grid weathering-front surface is undefined for some cells")
    return {"xy": xy, "nearest": nearest_d, "zone": zone, "deepest": deepest_xy, "surface": surf,
            "collar_ids": ids, "collar_xy": cxy}


def load_refit(o5, tier: str, role: str) -> dict:
    """Fitted model of one tier and role, with its artifact hash checked against the recorded refit."""
    rec = o5.execute("SELECT * FROM final_refits WHERE tier = ? AND role = ?", (tier, role)).fetchone()
    if rec is None:
        raise StopError(f"no final refit for {tier} {role}; run the refit stage first")
    path = PROJECT_ROOT / rec["artifact_path"]
    if sha256_file(path) != rec["artifact_sha256"]:
        raise StopError(f"artifact {rec['artifact_path']} differs from its recorded SHA-256")
    payload = joblib.load(path)
    return {"model": payload["model"], "predictors": list(payload["predictors"]), "model_id": rec["model_id"],
            "record": dict(rec), "artifact": rec["artifact_path"], "sha256": rec["artifact_sha256"]}


def entropy_bits(p) -> np.ndarray:
    p = np.asarray(p, dtype=np.float64)
    out = np.zeros(p.shape, dtype=np.float64)
    inner = (p > 0.0) & (p < 1.0)
    q = p[inner]
    out[inner] = -(q * np.log2(q) + (1.0 - q) * np.log2(1.0 - q))
    return out


def build_cells(o5, cfg: dict) -> dict:
    """Write the grid cells (all zones) and the layer and metadata tables. Probability columns are filled here for
    INTERPOLATION and EXTRAPOLATION cells; bootstrap and classification fill the rest."""
    o3_cfg, _ = load_o3_config(O3_CONFIG_PATH)
    axes = None
    collars = o5.execute("SELECT easting_m, northing_m FROM collars ORDER BY hole_id").fetchall()
    collars_xy = np.array([[c["easting_m"], c["northing_m"]] for c in collars], dtype=np.float64)
    axes = grid_axes(collars_xy, cfg)
    f = xy_level_fields(o5, cfg, axes)
    nxy = f["xy"].shape[0]
    nE, nZ = axes["nE"], axes["nZ"]
    n_cells = nxy * nZ

    # Cell order: iz major, then iy, then ix. Index within the xy arrays is iy * nE + ix.
    xy_index = np.tile(np.arange(nxy), nZ)
    iz = np.repeat(np.arange(nZ), nxy)
    ix = xy_index % nE
    iy = xy_index // nE
    z = axes["zc"][iz]
    E = f["xy"][xy_index, 0]
    N = f["xy"][xy_index, 1]
    zone = f["zone"][xy_index]
    dbf = depth_below_front(f["surface"][xy_index], z)
    above = (dbf < 0.0).astype(np.int64)
    deepest = f["deepest"][xy_index]
    depth_support = depth_support_labels(z, deepest)
    depth_below_collar = -z
    band_top = (np.floor(depth_below_collar / DEPTH_BAND_M) * DEPTH_BAND_M).astype(np.int64)

    p_sel = np.full(n_cells, np.nan)
    p_ru = np.full(n_cells, np.nan)
    sel_id = np.full(n_cells, None, dtype=object)
    ru_id = np.full(n_cells, None, dtype=object)
    model_tier = np.full(n_cells, None, dtype=object)
    for z_name in (INTERPOLATION, EXTRAPOLATION):
        tier = TIER_OF_ZONE[z_name]
        mask = zone == z_name
        if not mask.any():
            continue
        sel = load_refit(o5, tier, "SELECTED")
        ru = load_refit(o5, tier, "RUNNER_UP")
        Xc = design_matrix(sel["predictors"], easting=E[mask], northing=N[mask], z=z[mask], dbf=dbf[mask])
        Xr = design_matrix(ru["predictors"], easting=E[mask], northing=N[mask], z=z[mask], dbf=dbf[mask])
        p_sel[mask] = sel["model"].predict(Xc)
        p_ru[mask] = ru["model"].predict(Xr)
        sel_id[mask] = sel["model_id"]
        ru_id[mask] = ru["model_id"]
        model_tier[mask] = tier
    supported = zone != NO_SUPPORT
    if np.any(p_sel[supported] < 0) or np.any(p_sel[supported] > 1) or np.any(~np.isfinite(p_sel[supported])):
        raise StopError("a supported cell has a missing or out-of-range selected probability")
    entropy = np.where(supported, entropy_bits(np.nan_to_num(p_sel, nan=0.0)), np.nan)
    disagreement = np.where(supported, np.abs(p_sel - p_ru), np.nan)

    o5.execute("BEGIN IMMEDIATE")
    try:
        o5.execute("DELETE FROM grid_cells")
        o5.execute("DELETE FROM grid_layers")
        o5.execute("DELETE FROM grid_meta")
        o5.executemany("INSERT INTO grid_layers (iz, z_relative_m, depth_below_collar_m) VALUES (?, ?, ?)",
                       [(k, float(axes["zc"][k]), float(-axes["zc"][k])) for k in range(nZ)])
        meta = {"origin_easting_m": axes["e0"], "origin_northing_m": axes["n0"], "n_easting": nE,
                "n_northing": axes["nN"], "n_z": nZ, "cell_easting_m": axes["ce"], "cell_northing_m": axes["cn"],
                "cell_z_m": axes["cz"], "cell_volume_m3": axes["ce"] * axes["cn"] * axes["cz"],
                "z_range_m": [axes["zlo"], axes["zhi"]], "n_cells": int(n_cells), "n_horizontal": int(nxy),
                "margin_m": GRID_MARGIN_M, "depth_band_m": DEPTH_BAND_M,
                "collars": len(f["collar_ids"]), "grid_created_utc": utc_now()}
        o5.executemany("INSERT INTO grid_meta (meta_key, meta_value) VALUES (?, ?)",
                       [(k, json.dumps(v)) for k, v in meta.items()])
        rows = []
        for c in range(n_cells):
            rows.append((c, int(ix[c]), int(iy[c]), int(iz[c]), float(E[c]), float(N[c]), float(z[c]),
                         float(depth_below_collar[c]), int(band_top[c]), float(f["nearest"][xy_index[c]]),
                         str(zone[c]), None if model_tier[c] is None else str(model_tier[c]),
                         None if sel_id[c] is None else str(sel_id[c]), None if ru_id[c] is None else str(ru_id[c]),
                         float(deepest[c]), str(depth_support[c]), float(dbf[c]), int(above[c]),
                         None if np.isnan(p_sel[c]) else float(p_sel[c]),
                         None if np.isnan(p_ru[c]) else float(p_ru[c]),
                         None if np.isnan(entropy[c]) else float(entropy[c]),
                         None if np.isnan(disagreement[c]) else float(disagreement[c])))
            if len(rows) >= INSERT_CHUNK:
                _insert_cells(o5, rows)
                rows = []
        if rows:
            _insert_cells(o5, rows)
        o5.execute("COMMIT")
    except Exception:
        if o5.in_transaction:
            o5.execute("ROLLBACK")
        raise
    counts = {z_name: int(np.sum(zone == z_name)) for z_name in (INTERPOLATION, EXTRAPOLATION, NO_SUPPORT)}
    return {"cells": int(n_cells), "horizontal_cells": int(nxy), "nE": nE, "nN": axes["nN"], "nZ": nZ,
            "zone_cells": counts, "depth_extrapolated_interpolation": int(np.sum(
                (zone == INTERPOLATION) & (depth_support == DEPTH_EXTRAPOLATED)))}


def _insert_cells(o5, rows) -> None:
    o5.executemany(
        "INSERT INTO grid_cells (cell_id, ix, iy, iz, centre_easting_m, centre_northing_m, z_relative_m, "
        "depth_below_collar_m, depth_band_top_m, nearest_collar_m, zone, model_tier, selected_model_id, "
        "runner_up_model_id, deepest_sampled_z_m, depth_support, depth_below_weathering_front_m, "
        "above_weathering_front, p_selected, p_runner_up, entropy_bits, disagreement) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

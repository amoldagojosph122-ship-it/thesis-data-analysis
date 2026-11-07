"""Hole cluster bootstrap of each zone's selected model.

Per replicate: draw the holes with replacement (all intervals of a drawn hole are kept; a hole drawn twice contributes two
copies that share one group for the inner cross-fit). Hyperparameters stay at the full-data selection. The estimator, the
weathering-front surface (built from the drawn holes; a training row leaves out all copies of its own hole) and the Platt
calibration are refitted. The zone's cells are predicted and the probability quantised to 1/255 in memory. Only per-cell
5th and 95th percentiles, width and the success count are written. The same seed is used for each zone, so the two zones
see the same draws.
"""

from __future__ import annotations

import time

import numpy as np

from kambale.objective_3.config import load_config as load_o3_config
from kambale.objective_5.config import (EXTRAPOLATION, INTERPOLATION, O3_CONFIG_PATH, StopError, TIER_OF_ZONE,
                                        utc_now)
from kambale.objective_5.fitting import FitError, fit_candidate
from kambale.objective_5.front import depth_below_front, design_matrix, front_surface
from kambale.objective_5.grid import load_refit
from kambale.objective_5.refit import front_settings, load_binary_training, load_fronts

QUANT = 255
PERCENTILE_LO = 5.0
PERCENTILE_HI = 95.0
PERCENTILE_CHUNK = 50_000


def quantise(p) -> np.ndarray:
    return np.rint(np.asarray(p, dtype=np.float64) * QUANT).astype(np.uint8)


def dequantise(q) -> np.ndarray:
    return np.asarray(q, dtype=np.float64) / QUANT


def replicate_training_rows(draw: np.ndarray, rows_of_hole: list) -> np.ndarray:
    """Training row indices of the drawn holes, copies included (order follows the draw)."""
    return np.concatenate([rows_of_hole[int(h)] for h in draw])


def own_hole_positions(rows_hole: np.ndarray, usable_holes: np.ndarray, n_holes: int) -> np.ndarray:
    """For each training row, the position of its own hole among the usable front holes, or -1 when that hole has none."""
    pos = np.full(n_holes, -1, dtype=np.int64)
    pos[usable_holes] = np.arange(usable_holes.size)
    return pos[rows_hole]


def interval_from_replicates(matrix_q: np.ndarray, success: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """5th and 95th percentile per cell over the successful replicates, computed in column chunks."""
    kept = matrix_q[success]
    n_cells = kept.shape[1]
    lo = np.empty(n_cells)
    hi = np.empty(n_cells)
    for a in range(0, n_cells, PERCENTILE_CHUNK):
        b = min(a + PERCENTILE_CHUNK, n_cells)
        block = dequantise(kept[:, a:b])
        q = np.percentile(block, [PERCENTILE_LO, PERCENTILE_HI], axis=0, method="linear")
        lo[a:b] = q[0]
        hi[a:b] = q[1]
    return lo, hi


def run_zone(o5, zone: str, *, data: dict, fronts: dict, settings: dict, o3_cfg: dict, n_rep: int, seed: int,
             fit_seed: int, min_fraction: float) -> dict:
    tier = TIER_OF_ZONE[zone]
    sel = load_refit(o5, tier, "SELECTED")
    predictors = sel["predictors"]
    candidate = sel["model_id"]
    params = sel["model"].params
    cells = o5.execute("SELECT cell_id, ix, iy, centre_easting_m, centre_northing_m, z_relative_m, "
                       "selected_model_id FROM grid_cells WHERE zone = ? ORDER BY cell_id", (zone,)).fetchall()
    if not cells:
        raise StopError(f"no cells in zone {zone}")
    if any(c["selected_model_id"] != candidate for c in cells):
        raise StopError(f"zone {zone} cells name a different selected model than the final refit")
    cell_id = np.array([c["cell_id"] for c in cells], dtype=np.int64)
    key = np.array([c["iy"] * 10_000_000 + c["ix"] for c in cells], dtype=np.int64)
    _, first, inv = np.unique(key, return_index=True, return_inverse=True)
    xy_q = np.column_stack([[cells[i]["centre_easting_m"] for i in first], [cells[i]["centre_northing_m"] for i in first]])
    E_c = np.array([c["centre_easting_m"] for c in cells])
    N_c = np.array([c["centre_northing_m"] for c in cells])
    Z_c = np.array([c["z_relative_m"] for c in cells])

    n_holes = len(data["holes"])
    rows_of_hole = [np.where(data["hole"] == h)[0] for h in range(n_holes)]
    hole_front_pos = np.array([fronts["index"].get(h, -1) for h in data["holes"]], dtype=np.int64)
    E, N, Z, y, hole = data["E"], data["N"], data["Z"], data["y"], data["hole"]

    rng = np.random.default_rng(seed)
    matrix = np.zeros((n_rep, cell_id.size), dtype=np.uint8)
    success = np.zeros(n_rep, dtype=bool)
    rep_rows = []
    started = time.time()
    for r in range(n_rep):
        draw = rng.integers(0, n_holes, size=n_holes)
        uniq = np.unique(draw)
        usable = uniq[hole_front_pos[uniq] >= 0]
        rows = replicate_training_rows(draw, rows_of_hole)
        try:
            if usable.size == 0:
                raise FitError("no drawn hole carries a weathering front")
            pts_xy = fronts["xy"][hole_front_pos[usable]]
            pts_z = fronts["z"][hole_front_pos[usable]]
            own = own_hole_positions(hole[rows], usable, n_holes)
            surf_rows = front_surface(pts_xy, pts_z, np.column_stack([E[rows], N[rows]]), exclude=own,
                                      power=settings["power"], k=settings["k"], coincident=settings["coincident"])
            if not np.all(np.isfinite(surf_rows)):
                raise FitError("front surface undefined for a training row")
            dbf_rows = depth_below_front(surf_rows, Z[rows])
            X_tr = design_matrix(predictors, easting=E[rows], northing=N[rows], z=Z[rows], dbf=dbf_rows)
            fm = fit_candidate(candidate, X_tr, y[rows], hole[rows], o3_cfg, fit_seed, predictors,
                               fixed_params=params)
            surf_q = front_surface(pts_xy, pts_z, xy_q, exclude=None, power=settings["power"], k=settings["k"],
                                   coincident=settings["coincident"])
            dbf_c = depth_below_front(surf_q[inv], Z_c)
            X_c = design_matrix(predictors, easting=E_c, northing=N_c, z=Z_c, dbf=dbf_c)
            matrix[r] = quantise(fm.predict(X_c))
            success[r] = True
            status, reason = "SUCCESS", "refitted; predictions stored"
        except (FitError, ValueError, np.linalg.LinAlgError) as exc:
            status, reason = "FAILED", f"{type(exc).__name__}: {exc}"
        rep_rows.append((zone, r + 1, candidate, status, reason, int(usable.size), int(rows.size)))
    runtime = time.time() - started
    n_success = int(success.sum())
    fraction = n_success / n_rep
    gate = "PASS" if fraction >= min_fraction else "STOP"
    lo, hi = interval_from_replicates(matrix, success) if n_success else (np.full(cell_id.size, np.nan),) * 2
    return {"zone": zone, "model_id": candidate, "n_replicates": n_rep, "n_success": n_success,
            "success_fraction": fraction, "status": gate, "runtime_s": runtime, "seed": seed, "cell_id": cell_id,
            "p_lo": lo, "p_hi": hi, "replicate_rows": rep_rows, "minimum_fraction": min_fraction}


def write_zone(o5, result: dict) -> None:
    o5.execute("BEGIN IMMEDIATE")
    try:
        o5.execute("DELETE FROM bootstrap_replicates WHERE zone = ?", (result["zone"],))
        o5.execute("DELETE FROM bootstrap_summary WHERE zone = ?", (result["zone"],))
        o5.executemany("INSERT INTO bootstrap_replicates (zone, replicate_index, model_id, status, reason, n_unique_holes, "
                       "n_rows) VALUES (?, ?, ?, ?, ?, ?, ?)", result["replicate_rows"])
        o5.execute("INSERT INTO bootstrap_summary (zone, model_id, n_replicates, n_success, success_fraction, seed, "
                   "runtime_s, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (result["zone"], result["model_id"], result["n_replicates"], result["n_success"],
                    result["success_fraction"], result["seed"], result["runtime_s"], result["status"]))
        if result["status"] == "PASS":
            width = result["p_hi"] - result["p_lo"]
            o5.executemany("UPDATE grid_cells SET p_lo = ?, p_hi = ?, interval_width = ?, bootstrap_successes = ? "
                           "WHERE cell_id = ?",
                           [(float(result["p_lo"][k]), float(result["p_hi"][k]), float(width[k]),
                             result["n_success"], int(result["cell_id"][k])) for k in range(result["cell_id"].size)])
        o5.execute("COMMIT")
    except Exception:
        if o5.in_transaction:
            o5.execute("ROLLBACK")
        raise


def run_bootstrap(o5, cfg: dict) -> dict:
    bcfg = cfg["uncertainty_measures"]["hole_bootstrap"]
    n_rep = int(bcfg["n_replicates"])
    seed = int(bcfg["seed"])
    min_fraction = float(bcfg["min_successful_fraction"])
    o3_cfg, _ = load_o3_config(O3_CONFIG_PATH)
    fit_seed = int(o3_cfg["seeds"][0])
    settings = front_settings(o3_cfg)
    data = load_binary_training(o5)
    fronts = load_fronts(o5)
    summary = {}
    for zone in (INTERPOLATION, EXTRAPOLATION):
        result = run_zone(o5, zone, data=data, fronts=fronts, settings=settings, o3_cfg=o3_cfg, n_rep=n_rep,
                          seed=seed, fit_seed=fit_seed, min_fraction=min_fraction)
        write_zone(o5, result)
        summary[zone] = {k: result[k] for k in ("model_id", "n_replicates", "n_success", "success_fraction", "status",
                                                "runtime_s")}
        if result["status"] != "PASS":
            raise StopError(f"{zone}: bootstrap success fraction {result['success_fraction']:.3f} is below "
                            f"{min_fraction}")
    summary["completed_utc"] = utc_now()
    return summary

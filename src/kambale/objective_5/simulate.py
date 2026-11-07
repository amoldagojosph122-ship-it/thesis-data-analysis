"""Scenario simulation: sequential indicator simulation (SIS) with a locally varying mean (Objective 5, part 2).

SCENARIO ANALYSIS. The lateral range of every scenario is ASSUMED, never estimated, and the results are reported per scenario
and never pooled. The simulation does not change the headline classes.

Model. The local mean m(u) at a node is the calibrated tier-2 selected probability (grid_cells.p_selected). The conditioning
data are the DESIGN_8_2_v1 binary intervals at their midpoints, each with its own local mean from the final tier-2 refit
(weathering-front feature with the own hole left out). Residuals r = i - m are simulated with simple kriging under the
residual covariance C(u, v) = sqrt(m_u (1 - m_u) m_v (1 - m_v)) rho(h), where rho is the down-hole exponential correlogram
in anisotropy-scaled distance h.

Random streams. Realisation r of scenario k uses numpy default_rng(SeedSequence(20261109, spawn_key=(k, r))), so every
realisation is reproducible on its own and independent of the order in which scenarios run.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from kambale.objective_2.pairs import integer_lag_edges
from kambale.objective_3.config import load_config as load_o3_config
from kambale.objective_5.config import (INTERPOLATION, O2_DB_PATH, O3_CONFIG_PATH, StopError, utc_now)
from kambale.objective_5.db import connect_readonly
from kambale.objective_5.grid import SUPPORTED, load_refit
from kambale.objective_5.refit import front_settings, load_binary_training, load_fronts, training_features

# Values from config/objective_5/uncertainty_config.yaml (scenario_simulation). The config is the authority; these
# constants are checked against it by check_config and a mismatch is a STOP.
SCENARIOS = (("SIS_AH015", 15.0), ("SIS_AH025", 25.0), ("SIS_AH050", 50.0), ("SIS_AH100", 100.0), ("SIS_AH200", 200.0))
N_REALISATIONS = 100
SEED = 20261109
MAX_DATA = 24
MAX_SIMULATED = 12
CANDIDATE_CAP = 512          # nearest nodes within the search radius stored per node (exact fallback beyond the cap)
SEARCH_RADIUS = 1.0          # anisotropy-scaled distance (the practical range in every direction)
JITTER_FRACTION = 1e-8
DIP_DEG = 60.0               # the down-hole direction: plunge 60 degrees (config inputs.downhole_variogram.lag_direction)
# Expected vertical practical ranges stated in the predeclaration of the scenario analysis (not in the YAML; see report).
EXPECTED_VERTICAL_RANGE_M = {15.0: 32.85, 25.0: 23.09, 50.0: 20.97, 100.0: 20.52, 200.0: 20.41}
VERTICAL_TOLERANCE_M = 0.01
MEAN_FREQUENCY_TOLERANCE = 0.05
REPRODUCTION_LAGS = (1.0, 5.0, 10.0, 20.0, 30.0)
VARIOGRAM_REALISATIONS = 5
FULL_REALISATIONS = (1, 2)
MIN_PAIRS_PER_BIN = 50       # Objective 2 DOWNHOLE_WITHIN min_pairs_per_bin
MIN_HOLE_PAIRS_PER_BIN = 5   # Objective 2 min_independent_hole_pairs_per_bin
ZERO_LAG_TOLERANCE_M = 1e-6
CELL_VOLUME_FALLBACK_M3 = 200.0
STRUCTURE_26 = np.ones((3, 3, 3), dtype=int)


# ----------------------------------------------------------------------------------------------------------------------
# Pure functions (unit tested)
# ----------------------------------------------------------------------------------------------------------------------

def vertical_range(a_d: float, a_h: float, dip_deg: float = DIP_DEG) -> tuple[float | None, float, str]:
    """Vertical practical range a_v such that the range along the hole direction equals a_d.

    1 / a_v^2 = (1 / a_d^2 - cos^2(dip) / a_h^2) / sin^2(dip). The scenario is INFEASIBLE when the bracket is <= 0,
    which happens for a_h <= a_d cos(dip).
    """
    c2 = np.cos(np.radians(dip_deg)) ** 2
    s2 = np.sin(np.radians(dip_deg)) ** 2
    bracket = 1.0 / float(a_d) ** 2 - c2 / float(a_h) ** 2
    if bracket <= 0.0:
        return None, float(bracket), "INFEASIBLE"
    return float(np.sqrt(s2 / bracket)), float(bracket), "FEASIBLE"


def correlogram(h, c0: float, c1: float) -> np.ndarray:
    """rho(0) = 1; rho(h) = c1 / (c0 + c1) exp(-3 h) for h > 0 (the nugget jump at the origin)."""
    h = np.asarray(h, dtype=np.float64)
    tail = (c1 / (c0 + c1)) * np.exp(-3.0 * h)
    return np.where(h > 0.0, tail, 1.0)


def scaled_coordinates(E, N, Z, a_h: float, a_v: float) -> np.ndarray:
    return np.column_stack([np.asarray(E, float) / a_h, np.asarray(N, float) / a_h, np.asarray(Z, float) / a_v])


def sk_weights(P, s, S_u, s_u: float, c0: float, c1: float, jitter: float = JITTER_FRACTION):
    """Simple kriging weights of the residuals. Returns (lambda, used_lstsq)."""
    P = np.asarray(P, float)
    s = np.asarray(s, float)
    H = np.sqrt(((P[:, None, :] - P[None, :, :]) ** 2).sum(axis=2))
    C = np.outer(s, s) * correlogram(H, c0, c1)
    C[np.diag_indices_from(C)] += jitter * s * s
    Hu = np.sqrt(((P - np.asarray(S_u, float)) ** 2).sum(axis=1))
    b = float(s_u) * s * correlogram(Hu, c0, c1)
    try:
        return np.linalg.solve(C, b), False
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(C, b, rcond=None)[0], True


def build_context(node_xyz, node_m, data_xyz, data_m, data_y, a_h: float, a_v: float, c0: float, c1: float) -> dict:
    """Neighbourhoods for one scenario. Points are indexed: data 0..nd-1, then nodes nd..nd+n-1 (global index)."""
    node_xyz = np.asarray(node_xyz, float)
    data_xyz = np.asarray(data_xyz, float)
    node_m = np.asarray(node_m, float)
    data_m = np.asarray(data_m, float)
    n, nd = node_xyz.shape[0], data_xyz.shape[0]
    Sn = scaled_coordinates(node_xyz[:, 0], node_xyz[:, 1], node_xyz[:, 2], a_h, a_v)
    Sd = scaled_coordinates(data_xyz[:, 0], data_xyz[:, 1], data_xyz[:, 2], a_h, a_v)
    S_all = np.vstack([Sd, Sn])
    m_all = np.concatenate([data_m, node_m])
    s_all = np.sqrt(m_all * (1.0 - m_all))
    bound = SEARCH_RADIUS * (1.0 + 1e-9)

    dd, di = cKDTree(Sd).query(Sn, k=MAX_DATA, distance_upper_bound=bound)
    data_nb = [di[u][dd[u] <= SEARCH_RADIUS].astype(np.int64) for u in range(n)]

    cd, ci = cKDTree(Sn).query(Sn, k=CANDIDATE_CAP + 1, distance_upper_bound=bound)
    cand_nb, cand_full = [], np.zeros(n, dtype=bool)
    for u in range(n):
        valid = (ci[u] != u) & (ci[u] < n) & (cd[u] <= SEARCH_RADIUS)
        cand = ci[u][valid].astype(np.int64)
        cand_full[u] = cand.size >= CANDIDATE_CAP
        cand_nb.append(cand[:CANDIDATE_CAP])
    return {"n": n, "nd": nd, "S_all": S_all, "m_all": m_all, "s_all": s_all, "data_nb": data_nb,
            "cand_nb": cand_nb, "cand_full": cand_full, "y_data": np.asarray(data_y, float), "c0": float(c0),
            "c1": float(c1), "a_h": float(a_h), "a_v": float(a_v)}


def simulate_realisation(ctx: dict, rng: np.random.Generator):
    """One SIS realisation along a random path. Returns (indicator array, p* array, stats dict)."""
    n, nd = ctx["n"], ctx["nd"]
    S_all, m_all, s_all = ctx["S_all"], ctx["m_all"], ctx["s_all"]
    c0, c1 = ctx["c0"], ctx["c1"]
    path = rng.permutation(n)
    U = rng.random(n)
    val = np.empty(nd + n)
    val[:nd] = ctx["y_data"]
    done = np.zeros(n, dtype=bool)
    sim = np.zeros(n, dtype=np.int8)
    pstar = np.empty(n)
    Sn = S_all[nd:]
    stats = {"sk_fallbacks": 0, "sk_neighbourless_nodes": 0, "exact_neighbour_searches": 0}
    empty = np.zeros(0, dtype=np.int64)
    for u in path:
        cand = ctx["cand_nb"][u]
        if cand.size:
            cand = cand[done[cand]]
        if ctx["cand_full"][u] and cand.size < MAX_SIMULATED:
            # The stored list was capped before reaching MAX_SIMULATED simulated nodes: search the simulated nodes
            # exactly, so that the twelve nearest previously simulated nodes within the radius are always used.
            stats["exact_neighbour_searches"] += 1
            done_idx = np.flatnonzero(done)
            if done_idx.size:
                d = np.sqrt(((Sn[done_idx] - Sn[u]) ** 2).sum(axis=1))
                ok = d <= SEARCH_RADIUS
                cand = done_idx[ok][np.argsort(d[ok], kind="stable")].astype(np.int64)
            else:
                cand = empty
        cand = cand[:MAX_SIMULATED]
        dn = ctx["data_nb"][u]
        idx = np.concatenate([dn, nd + cand]) if (dn.size or cand.size) else empty
        gu = nd + int(u)
        if idx.size == 0:
            p = float(m_all[gu])
            stats["sk_neighbourless_nodes"] += 1
        else:
            lam, lstsq = sk_weights(S_all[idx], s_all[idx], S_all[gu], s_all[gu], c0, c1)
            if lstsq:
                stats["sk_fallbacks"] += 1
            p = float(m_all[gu] + lam @ (val[idx] - m_all[idx]))
            p = min(max(p, 0.0), 1.0)
        pstar[u] = p
        v = 1 if U[u] < p else 0
        sim[u] = v
        val[gu] = v
        done[u] = True
    return sim, pstar, stats


def connectivity(positive: np.ndarray) -> tuple[int, int]:
    """26-neighbour connected components of a 3D boolean array. Returns (components, largest size in cells)."""
    lab, ncomp = ndimage.label(np.asarray(positive, dtype=bool), structure=STRUCTURE_26)
    if ncomp == 0:
        return 0, 0
    sizes = np.bincount(lab.ravel())[1:]
    return int(ncomp), int(sizes.max())


def realisation_rng(seed: int, scenario_index: int, realisation: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(int(scenario_index), int(realisation))))


def gamma_by_bin(values, pi, pj, pbin, nbins: int):
    """EQUAL_PAIR semivariance per lag bin for the given pairs: gamma = sum (v_a - v_b)^2 / (2 n)."""
    v = np.asarray(values, float)
    d2 = (v[pi] - v[pj]) ** 2
    n = np.bincount(pbin, minlength=nbins).astype(np.float64)
    s = np.bincount(pbin, weights=d2, minlength=nbins)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(n > 0, s / (2.0 * n), np.nan)
    return g, n


def within_hole_pairs(hole, xyz, edges):
    """Within-hole pairs with 3D lag inside the Objective 2 DOWNHOLE_WITHIN bins (the same pair rule as objective_2.pairs)."""
    pi, pj, pb, ph = [], [], [], []
    xyz = np.asarray(xyz, float)
    _, hole_int = np.unique(np.asarray(hole), return_inverse=True)
    for h in np.unique(hole_int):
        idx = np.where(hole_int == h)[0]
        if idx.size < 2:
            continue
        ii, jj = np.triu_indices(idx.size, 1)
        a, b = idx[ii], idx[jj]
        lag = np.sqrt(((xyz[a] - xyz[b]) ** 2).sum(axis=1))
        keep = (lag > ZERO_LAG_TOLERANCE_M) & (lag >= edges[0]) & (lag < edges[-1])
        a, b, lag = a[keep], b[keep], lag[keep]
        pi.append(a)
        pj.append(b)
        pb.append(np.searchsorted(edges, lag, side="right") - 1)
        ph.append(np.full(a.size, h))
    if not pi:
        empty = np.zeros(0, dtype=np.int64)
        return empty, empty, empty, empty
    return (np.concatenate(pi).astype(np.int64), np.concatenate(pj).astype(np.int64),
            np.concatenate(pb).astype(np.int64), np.concatenate(ph).astype(np.int64))


def bin_hole_counts(pbin, phole, nbins: int) -> np.ndarray:
    """Number of distinct holes with at least one pair in each bin."""
    out = np.zeros(nbins, dtype=np.int64)
    if pbin.size == 0:
        return out
    key = np.unique(np.column_stack([pbin, phole]), axis=0)
    out = np.bincount(key[:, 0], minlength=nbins).astype(np.int64)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Scenario worker (runs in a separate process per scenario)
# ----------------------------------------------------------------------------------------------------------------------

def run_scenario(job: dict) -> dict:
    sid, k, a_h = job["scenario_id"], job["index"], job["horizontal_range_m"]
    a_v, bracket, feas = vertical_range(job["a_d"], a_h)
    out = {"scenario_id": sid, "index": k, "horizontal_range_m": a_h, "feasibility": feas, "vertical_bracket": bracket,
           "vertical_range_m": a_v, "realisations": [], "counts": None, "full": {}, "variogram": None}
    if feas == "INFEASIBLE":
        return out
    t0 = time.time()
    node_xyz = job["node_xyz"]
    ctx = build_context(node_xyz, job["node_m"], job["data_xyz"], job["data_m"], job["data_y"], a_h, a_v,
                        job["c0"], job["c1"])
    n = ctx["n"]
    counts = np.zeros(n, dtype=np.int64)
    lo_bins = job["pbin_nbins"]
    var_sims = []
    for r in range(1, job["n_realisations"] + 1):
        rng = realisation_rng(job["seed"], k, r)
        sim, _, st = simulate_realisation(ctx, rng)
        counts += sim
        pos = np.zeros(job["grid_shape"], dtype=bool)
        pos[job["node_iz"], job["node_iy"], job["node_ix"]] = sim.astype(bool)
        ncomp, big = connectivity(pos)
        npos = int(sim.sum())
        out["realisations"].append({"realisation": r, "n_positive": npos, "volume_m3": npos * job["cell_volume_m3"],
                                    "n_components": ncomp, "largest_cells": big,
                                    "largest_share": (big / npos) if npos else None, **st})
        if r in FULL_REALISATIONS:
            out["full"][r] = sim.copy()
        if r <= VARIOGRAM_REALISATIONS:
            var_sims.append(sim[job["datum_node"]].astype(float))
        if r % 10 == 0:
            print(f"[simulate] {sid} realisation {r}/{job['n_realisations']} ({time.time() - t0:.0f} s)",
                  file=sys.stderr, flush=True)
    gammas = np.array([gamma_by_bin(v, job["pi"], job["pj"], job["pbin"], lo_bins)[0] for v in var_sims])
    out["variogram"] = {"sim_mean": np.nanmean(gammas, axis=0), "sim_min": np.nanmin(gammas, axis=0),
                        "sim_max": np.nanmax(gammas, axis=0), "n_realisations": len(var_sims)}
    out["counts"] = counts
    out["runtime_s"] = time.time() - t0
    out["ctx_stats"] = {"n_nodes": n, "mean_data_neighbours": float(np.mean([len(x) for x in ctx["data_nb"]])),
                        "mean_candidates": float(np.mean([len(x) for x in ctx["cand_nb"]]))}
    print(f"[simulate] {sid} done in {out['runtime_s']:.0f} s", file=sys.stderr, flush=True)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# Inputs, checks, orchestration and storage
# ----------------------------------------------------------------------------------------------------------------------

def check_config(cfg: dict) -> None:
    s = cfg["scenario_simulation"]
    got = [(x["scenario_id"], float(x["horizontal_range_m"])) for x in s["scenarios"]]
    if got != list(SCENARIOS):
        raise StopError(f"scenario set {got} differs from the predeclared set {list(SCENARIOS)}")
    if int(s["n_realisations"]) != N_REALISATIONS:
        raise StopError(f"realisation count {s['n_realisations']} differs from {N_REALISATIONS}")
    if int(s["seed"]) != SEED:
        raise StopError(f"seed {s['seed']} differs from {SEED}")
    k = s["kriging"]
    if int(k["max_conditioning_data"]) != MAX_DATA or int(k["max_previously_simulated"]) != MAX_SIMULATED:
        raise StopError("neighbour limits differ from the configuration")
    if "1.0" not in str(k["search_radius"]):
        raise StopError("search radius differs from the configuration")
    if abs(float(k["jitter_fraction"]) - JITTER_FRACTION) > 0:
        raise StopError("jitter fraction differs from the configuration")
    if k["type"] != "SIMPLE_KRIGING_OF_RESIDUALS":
        raise StopError("kriging type differs from the configuration")
    if "plunge 60" not in cfg["inputs"]["downhole_variogram"]["lag_direction"]:
        raise StopError("down-hole direction differs from plunge 60 degrees")


def load_inputs(o5, cfg: dict) -> dict:
    dh = o5.execute("SELECT * FROM downhole_variogram WHERE check_id = 1").fetchone()
    if dh is None or dh["model"] != "exponential":
        raise StopError("the down-hole variogram record is missing or not exponential")
    c0, c1, a_d = float(dh["nugget"]), float(dh["structured_sill"]), float(dh["practical_range_m"])
    meta = {r["meta_key"]: json.loads(r["meta_value"]) for r in o5.execute("SELECT * FROM grid_meta")}
    vol = float(meta.get("cell_volume_m3", CELL_VOLUME_FALLBACK_M3))
    if abs(vol - CELL_VOLUME_FALLBACK_M3) > 1e-9:
        raise StopError("cell volume differs from 200 m3")
    shape = (int(meta["n_z"]), int(meta["n_northing"]), int(meta["n_easting"]))
    nodes = o5.execute(
        "SELECT cell_id, ix, iy, iz, centre_easting_m AS e, centre_northing_m AS n, z_relative_m AS z, p_selected AS m, "
        "zone, depth_support FROM grid_cells WHERE zone = ? AND depth_support = ? ORDER BY cell_id",
        (INTERPOLATION, SUPPORTED)).fetchall()
    if not nodes:
        raise StopError("no simulation nodes")
    if any(r["zone"] != INTERPOLATION or r["depth_support"] != SUPPORTED for r in nodes):
        raise StopError("a simulation node is outside the simulation domain")
    if any(r["m"] is None or not (0.0 < r["m"] < 1.0) for r in nodes):
        raise StopError("a simulation node has a missing or degenerate local mean")
    sel_rec = o5.execute("SELECT model_id, in_sample_brier FROM final_refits WHERE tier = 'TIER_2_INTERPOLATION' "
                         "AND role = 'SELECTED'").fetchone()
    if sel_rec is None or sel_rec["model_id"] != "M2_HGB_WF":
        raise StopError("the tier-2 selected model is not M2_HGB_WF")
    data = load_binary_training(o5)
    sel = load_refit(o5, "TIER_2_INTERPOLATION", "SELECTED")
    if sel["model_id"] != "M2_HGB_WF":
        raise StopError("the tier-2 artifact is not M2_HGB_WF")
    o3_cfg, _ = load_o3_config(O3_CONFIG_PATH)
    fronts = load_fronts(o5)
    X = training_features(data, fronts, sel["predictors"], front_settings(o3_cfg))
    m_d = np.asarray(sel["model"].predict(X), dtype=np.float64)
    y = data["y"].astype(np.float64)
    brier = float(np.mean((m_d - y) ** 2))
    if abs(brier - float(sel_rec["in_sample_brier"])) > 1e-9:
        raise StopError(f"datum local means do not reproduce the recorded tier-2 fit ({brier} vs "
                        f"{sel_rec['in_sample_brier']})")
    node_xyz = np.array([[r["e"], r["n"], r["z"]] for r in nodes], dtype=np.float64)
    data_xyz = np.column_stack([data["E"], data["N"], data["Z"]])
    dist, nearest = cKDTree(node_xyz).query(data_xyz)
    edges = integer_lag_edges(30)
    pi, pj, pb, ph = within_hole_pairs(data["hole_name"], data_xyz, edges)
    nbins = len(edges) - 1
    return {"c0": c0, "c1": c1, "a_d": a_d, "dh": dict(dh), "meta": meta, "cell_volume_m3": vol, "shape": shape,
            "nodes": nodes, "node_xyz": node_xyz, "node_m": np.array([r["m"] for r in nodes], float),
            "node_cell_id": np.array([r["cell_id"] for r in nodes], dtype=np.int64),
            "node_ix": np.array([r["ix"] for r in nodes], dtype=np.int64),
            "node_iy": np.array([r["iy"] for r in nodes], dtype=np.int64),
            "node_iz": np.array([r["iz"] for r in nodes], dtype=np.int64),
            "data": data, "data_xyz": data_xyz, "data_m": m_d, "data_y": y, "datum_node": nearest,
            "datum_node_distance": dist, "pi": pi, "pj": pj, "pbin": pb, "pholes": ph, "nbins": nbins, "edges": edges,
            "data_gamma": gamma_by_bin(y, pi, pj, pb, nbins), "bin_holes": bin_hole_counts(pb, ph, nbins)}


def _o2_downhole_gamma(dh: dict) -> np.ndarray:
    o2 = connect_readonly(O2_DB_PATH)
    try:
        rows = o2.execute("SELECT bin_index, gamma FROM variogram_lag_bins WHERE experiment_id = ? ORDER BY bin_index",
                          (dh["o2_experiment_id"],)).fetchall()
    finally:
        o2.close()
    return np.array([np.nan if r["gamma"] is None else r["gamma"] for r in rows], dtype=float)


def run_all(o5, cfg: dict, n_workers: int | None = None) -> dict:
    """Run every scenario, then store the results in the scenario tables. STOP gates raise StopError."""
    check_config(cfg)
    ctx = load_inputs(o5, cfg)
    o2_gamma = _o2_downhole_gamma(ctx["dh"])
    g_data, n_data_pairs = ctx["data_gamma"]
    supported_data = (n_data_pairs >= MIN_PAIRS_PER_BIN) & (ctx["bin_holes"] >= MIN_HOLE_PAIRS_PER_BIN)
    with np.errstate(invalid="ignore"):
        both = supported_data & np.isfinite(o2_gamma)
        data_vs_o2 = float(np.max(np.abs(g_data[both] - o2_gamma[both]))) if both.any() else float("nan")
    jobs = []
    for k, (sid, a_h) in enumerate(SCENARIOS):
        jobs.append({"scenario_id": sid, "index": k, "horizontal_range_m": a_h, "a_d": ctx["a_d"], "c0": ctx["c0"],
                     "c1": ctx["c1"], "seed": SEED, "n_realisations": N_REALISATIONS,
                     "node_xyz": ctx["node_xyz"], "node_m": ctx["node_m"], "data_xyz": ctx["data_xyz"],
                     "data_m": ctx["data_m"], "data_y": ctx["data_y"], "datum_node": ctx["datum_node"],
                     "pi": ctx["pi"], "pj": ctx["pj"], "pbin": ctx["pbin"], "pbin_nbins": ctx["nbins"],
                     "node_iz": ctx["node_iz"], "node_iy": ctx["node_iy"], "node_ix": ctx["node_ix"],
                     "grid_shape": ctx["shape"], "cell_volume_m3": ctx["cell_volume_m3"]})
    workers = n_workers or min(len(jobs), max(1, os.cpu_count() or 1))
    t0 = time.time()
    print(f"[simulate] {len(jobs)} scenarios, {N_REALISATIONS} realisations each, {workers} workers, "
          f"{len(ctx['nodes'])} nodes, {ctx['data_xyz'].shape[0]} data", file=sys.stderr, flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(run_scenario, jobs))
    wall = time.time() - t0
    summary = write_results(o5, ctx, results, cfg, o2_gamma, data_vs_o2, wall)
    return summary


def _pct(values, q):
    v = np.array([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    return float(np.percentile(v, q)) if v.size else None


def _scenario_row(res: dict, ctx: dict, cfg: dict, created: str) -> dict:
    sid = res["scenario_id"]
    row = {"scenario_id": sid, "scenario_index": res["index"], "horizontal_range_m": res["horizontal_range_m"],
           "feasibility": res["feasibility"], "vertical_bracket": res["vertical_bracket"],
           "vertical_range_m": res["vertical_range_m"],
           "expected_vertical_range_m": EXPECTED_VERTICAL_RANGE_M[res["horizontal_range_m"]],
           "downhole_practical_range_m": ctx["a_d"], "dip_deg": DIP_DEG, "n_domain_nodes": len(ctx["nodes"]),
           "n_data": int(ctx["data_xyz"].shape[0]), "n_realisations": 0, "seed": SEED,
           "max_conditioning": MAX_DATA, "max_simulated": MAX_SIMULATED, "search_radius": SEARCH_RADIUS,
           "jitter_fraction": JITTER_FRACTION, "expected_volume_m3": float(np.sum(ctx["node_m"]) * ctx["cell_volume_m3"]),
           "config_version": cfg["config_version"], "created_utc": created}
    if res["feasibility"] == "INFEASIBLE":
        row.update({"status": "INFEASIBLE_NOT_RUN", "runtime_s": None})
        return row
    reals = res["realisations"]
    vols = [r["volume_m3"] for r in reals]
    comps = [r["n_components"] for r in reals]
    shares = [r["largest_share"] for r in reals]
    counts = res["counts"]
    n_real = len(reals)
    freq = counts / n_real
    mean_freq = float(np.mean(freq))
    mean_m = float(np.mean(ctx["node_m"]))
    diff = mean_freq - mean_m
    gam = res["variogram"]
    sup = (ctx["data_gamma"][1] >= MIN_PAIRS_PER_BIN) & (ctx["bin_holes"] >= MIN_HOLE_PAIRS_PER_BIN)
    dd = np.abs(gam["sim_mean"] - ctx["data_gamma"][0])
    dd = dd[sup & np.isfinite(dd)]
    fallbacks = sum(r["sk_fallbacks"] for r in reals)
    status = "COMPLETED"
    row.update({
        "n_realisations": n_real, "vertical_range_m": res["vertical_range_m"],
        "volume_p10_m3": _pct(vols, 10), "volume_p50_m3": _pct(vols, 50), "volume_p90_m3": _pct(vols, 90),
        "components_p10": _pct(comps, 10), "components_p50": _pct(comps, 50), "components_p90": _pct(comps, 90),
        "largest_share_p10": _pct(shares, 10), "largest_share_p50": _pct(shares, 50),
        "largest_share_p90": _pct(shares, 90),
        "mean_local_mean": mean_m, "mean_frequency": mean_freq, "mean_frequency_diff": diff,
        "frequency_status": "WARN" if abs(diff) > MEAN_FREQUENCY_TOLERANCE else "PASS",
        "sk_fallbacks": int(fallbacks), "sk_neighbourless_nodes": int(sum(r["sk_neighbourless_nodes"] for r in reals)),
        "exact_neighbour_searches": int(sum(r["exact_neighbour_searches"] for r in reals)),
        "downhole_max_abs_diff": float(dd.max()) if dd.size else None,
        "downhole_mean_abs_diff": float(dd.mean()) if dd.size else None,
        "runtime_s": res["runtime_s"], "status": status,
    })
    return row


def write_results(o5, ctx: dict, results: list[dict], cfg: dict, o2_gamma, data_vs_o2: float, wall: float) -> dict:
    created = utc_now()
    scen_rows, real_rows, freq_rows, full_rows, var_rows, summary = [], [], [], [], [], {}
    for res in results:
        row = _scenario_row(res, ctx, cfg, created)
        if res["feasibility"] == "FEASIBLE":
            if len(res["realisations"]) != N_REALISATIONS:
                raise StopError(f"{res['scenario_id']}: {len(res['realisations'])} realisations, expected {N_REALISATIONS}")
            for r in res["realisations"]:
                real_rows.append((res["scenario_id"], r["realisation"], r["n_positive"], r["volume_m3"],
                                  r["n_components"], r["largest_cells"] * ctx["cell_volume_m3"], r["largest_share"],
                                  r["sk_fallbacks"], r["sk_neighbourless_nodes"], r["exact_neighbour_searches"]))
            counts = res["counts"]
            for k in range(counts.size):
                freq_rows.append((res["scenario_id"], int(ctx["node_cell_id"][k]), int(counts[k]),
                                  float(counts[k] / N_REALISATIONS), float(ctx["node_m"][k])))
            for r in FULL_REALISATIONS:
                for k in range(counts.size):
                    full_rows.append((res["scenario_id"], r, int(ctx["node_cell_id"][k]), int(res["full"][r][k])))
            gam = res["variogram"]
            for b in range(ctx["nbins"]):
                is_sup = int(ctx["data_gamma"][1][b] >= MIN_PAIRS_PER_BIN and ctx["bin_holes"][b] >= MIN_HOLE_PAIRS_PER_BIN)
                var_rows.append((res["scenario_id"], b, float(ctx["edges"][b] + 0.5), int(ctx["data_gamma"][1][b]),
                                 int(ctx["bin_holes"][b]), is_sup, int(gam["n_realisations"]),
                                 float(ctx["data_gamma"][0][b]) if np.isfinite(ctx["data_gamma"][0][b]) else None,
                                 float(o2_gamma[b]) if b < o2_gamma.size and np.isfinite(o2_gamma[b]) else None,
                                 _f(gam["sim_mean"][b]), _f(gam["sim_min"][b]), _f(gam["sim_max"][b])))
            summary[res["scenario_id"]] = {k: row[k] for k in ("feasibility", "vertical_range_m", "volume_p50_m3",
                                                                "frequency_status", "mean_frequency_diff",
                                                                "sk_fallbacks", "runtime_s")}
        else:
            summary[res["scenario_id"]] = {"feasibility": res["feasibility"], "vertical_bracket": res["vertical_bracket"]}
        scen_rows.append(row)
    stop = [r["scenario_id"] for r in scen_rows if r["feasibility"] == "FEASIBLE" and r.get("n_realisations") != N_REALISATIONS]
    if stop:
        raise StopError(f"realisation count differs from {N_REALISATIONS} for {stop}")
    o5.execute("BEGIN IMMEDIATE")
    try:
        for t in ("sim_downhole_variogram", "sim_cell_realisation", "sim_cell_frequency", "sim_realisations",
                  "sim_datum", "sim_scenarios", "sim_run_meta"):
            o5.execute(f"DELETE FROM {t}")
        o5.executemany(
            "INSERT INTO sim_scenarios (scenario_id, scenario_index, horizontal_range_m, feasibility, vertical_bracket, "
            "vertical_range_m, expected_vertical_range_m, downhole_practical_range_m, dip_deg, n_domain_nodes, n_data, "
            "n_realisations, seed, max_conditioning, max_simulated, search_radius, jitter_fraction, expected_volume_m3, "
            "volume_p10_m3, volume_p50_m3, volume_p90_m3, components_p10, components_p50, components_p90, "
            "largest_share_p10, largest_share_p50, largest_share_p90, mean_local_mean, mean_frequency, "
            "mean_frequency_diff, frequency_status, sk_fallbacks, sk_neighbourless_nodes, exact_neighbour_searches, "
            "downhole_max_abs_diff, downhole_mean_abs_diff, runtime_s, status, config_version, created_utc) "
            "VALUES (:scenario_id, :scenario_index, :horizontal_range_m, :feasibility, :vertical_bracket, "
            ":vertical_range_m, :expected_vertical_range_m, :downhole_practical_range_m, :dip_deg, :n_domain_nodes, "
            ":n_data, :n_realisations, :seed, :max_conditioning, :max_simulated, :search_radius, :jitter_fraction, "
            ":expected_volume_m3, :volume_p10_m3, :volume_p50_m3, :volume_p90_m3, :components_p10, :components_p50, "
            ":components_p90, :largest_share_p10, :largest_share_p50, :largest_share_p90, :mean_local_mean, "
            ":mean_frequency, :mean_frequency_diff, :frequency_status, :sk_fallbacks, :sk_neighbourless_nodes, "
            ":exact_neighbour_searches, :downhole_max_abs_diff, :downhole_mean_abs_diff, :runtime_s, :status, "
            ":config_version, :created_utc)", [_named(r) for r in scen_rows])
        o5.executemany("INSERT INTO sim_realisations (scenario_id, realisation, n_positive, volume_m3, n_components, "
                       "largest_volume_m3, largest_share, sk_fallbacks, sk_neighbourless_nodes, exact_neighbour_searches) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", real_rows)
        o5.executemany("INSERT INTO sim_cell_frequency (scenario_id, cell_id, n_positive, frequency, local_mean) "
                       "VALUES (?, ?, ?, ?, ?)", freq_rows)
        o5.executemany("INSERT INTO sim_cell_realisation (scenario_id, realisation, cell_id, value) VALUES (?, ?, ?, ?)",
                       full_rows)
        o5.executemany("INSERT INTO sim_downhole_variogram (scenario_id, bin_index, lag_centre_m, n_pairs, n_hole_pairs, "
                       "supported, n_realisations_sampled, data_gamma, data_o2_gamma, sim_gamma_mean, sim_gamma_min, "
                       "sim_gamma_max) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", var_rows)
        # Datum records: local mean and nearest node (distance in metres).
        d = ctx["data"]
        o5.executemany("INSERT INTO sim_datum (upstream_interval_id, hole_id, easting_m, northing_m, z_relative_m, "
                       "indicator, local_mean, nearest_node_cell_id, nearest_node_distance_m) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       [(int(d["ids"][i]), d["hole_name"][i], float(ctx["data_xyz"][i, 0]), float(ctx["data_xyz"][i, 1]),
                         float(ctx["data_xyz"][i, 2]), int(ctx["data_y"][i]), float(ctx["data_m"][i]),
                         int(ctx["node_cell_id"][ctx["datum_node"][i]]), float(ctx["datum_node_distance"][i]))
                        for i in range(ctx["data_xyz"].shape[0])])
        meta_rows = {"config_version": cfg["config_version"], "seed": SEED, "c0": ctx["c0"], "c1": ctx["c1"],
                     "downhole_practical_range_m": ctx["a_d"], "n_domain_nodes": len(ctx["nodes"]),
                     "n_data": int(ctx["data_xyz"].shape[0]), "data_vs_o2_max_abs_diff": data_vs_o2,
                     "data_mean_local_mean": float(np.mean(ctx["data_m"])), "wall_clock_s": wall,
                     "datum_max_nearest_node_distance_m": float(np.max(ctx["datum_node_distance"])),
                     "created_utc": created}
        o5.executemany("INSERT INTO sim_run_meta (meta_key, meta_value) VALUES (?, ?)",
                       [(k, json.dumps(v)) for k, v in meta_rows.items()])
        o5.execute("COMMIT")
    except Exception:
        if o5.in_transaction:
            o5.execute("ROLLBACK")
        raise
    summary["_wall_clock_s"] = wall
    summary["_data_vs_o2_max_abs_diff"] = data_vs_o2
    return summary


def _f(x):
    return None if x is None or not np.isfinite(x) else float(x)


SCENARIO_COLUMNS = ("scenario_id", "scenario_index", "horizontal_range_m", "feasibility", "vertical_bracket",
                    "vertical_range_m", "expected_vertical_range_m", "downhole_practical_range_m", "dip_deg",
                    "n_domain_nodes", "n_data", "n_realisations", "seed", "max_conditioning", "max_simulated",
                    "search_radius", "jitter_fraction", "expected_volume_m3", "volume_p10_m3", "volume_p50_m3",
                    "volume_p90_m3", "components_p10", "components_p50", "components_p90", "largest_share_p10",
                    "largest_share_p50", "largest_share_p90", "mean_local_mean", "mean_frequency",
                    "mean_frequency_diff", "frequency_status", "sk_fallbacks", "sk_neighbourless_nodes",
                    "exact_neighbour_searches", "downhole_max_abs_diff", "downhole_mean_abs_diff", "runtime_s", "status",
                    "config_version", "created_utc")


def _named(row: dict) -> dict:
    return {c: row.get(c) for c in SCENARIO_COLUMNS}


# ----------------------------------------------------------------------------------------------------------------------
# Gates for verify (recomputed from the stored scenario tables and the configuration)
# ----------------------------------------------------------------------------------------------------------------------

def verify_gates(o5, cfg: dict) -> list[dict]:
    def g(gid, name, status, scope, detail):
        return {"gate_id": gid, "gate_name": name, "status": status, "scope": scope, "detail": detail}

    rows = o5.execute("SELECT * FROM sim_scenarios ORDER BY scenario_index").fetchall()
    if not rows:
        return [g("S00", "Scenario simulation run", "WARN", "simulation", "the scenario simulation has not been run")]
    out = []
    got = [(r["scenario_id"], float(r["horizontal_range_m"])) for r in rows]
    out.append(g("S01", "Scenario set matches configuration", "PASS" if got == list(SCENARIOS) else "STOP", "simulation",
                 f"{got}"))
    counts = {r["scenario_id"]: o5.execute("SELECT COUNT(*) FROM sim_realisations WHERE scenario_id = ?",
                                           (r["scenario_id"],)).fetchone()[0] for r in rows}
    bad = []
    for r in rows:
        expected = N_REALISATIONS if r["feasibility"] == "FEASIBLE" else 0
        if counts[r["scenario_id"]] != expected or (r["feasibility"] == "FEASIBLE" and r["n_realisations"] != expected):
            bad.append(r["scenario_id"])
    limits_ok = all(r["max_conditioning"] == MAX_DATA and r["max_simulated"] == MAX_SIMULATED and
                    abs(r["search_radius"] - SEARCH_RADIUS) < 1e-12 and r["seed"] == SEED for r in rows)
    out.append(g("S02", "Realisation count, neighbour limits and seed", "PASS" if not bad and limits_ok else "STOP",
                 "simulation", f"realisations per scenario {counts}; neighbour limits {MAX_DATA}/{MAX_SIMULATED}; "
                               f"seed {SEED}; mismatches {bad}"))
    bad_v = []
    for r in rows:
        av, _, feas = vertical_range(float(r["downhole_practical_range_m"]), float(r["horizontal_range_m"]))
        if feas != r["feasibility"]:
            bad_v.append(f"{r['scenario_id']} feasibility")
        elif feas == "FEASIBLE":
            exp = EXPECTED_VERTICAL_RANGE_M[float(r["horizontal_range_m"])]
            if abs(av - exp) > VERTICAL_TOLERANCE_M or abs(av - float(r["vertical_range_m"])) > 1e-9:
                bad_v.append(f"{r['scenario_id']} a_v {av:.4f} vs expected {exp}")
        elif r["vertical_range_m"] is not None:
            bad_v.append(f"{r['scenario_id']} infeasible but a_v stored")
    out.append(g("S03", "Vertical ranges match the expected values", "PASS" if not bad_v else "STOP", "simulation",
                 "; ".join(bad_v) if bad_v else "a_v within 0.01 of the expected values; infeasibility recorded"))
    outside = o5.execute("SELECT COUNT(*) FROM sim_cell_frequency f LEFT JOIN grid_cells g ON g.cell_id = f.cell_id "
                         "WHERE g.cell_id IS NULL OR g.zone <> 'INTERPOLATION' OR g.depth_support <> 'SUPPORTED'"
                         ).fetchone()[0]
    out.append(g("S04", "Simulation nodes inside the domain", "PASS" if outside == 0 else "STOP", "simulation",
                 f"{outside} simulated cells outside INTERPOLATION and SUPPORTED"))
    warn = [r["scenario_id"] for r in rows if r["frequency_status"] == "WARN"]
    out.append(g("W03", "Mean simulated frequency against mean local mean", "WARN" if warn else "PASS", "simulation",
                 f"|difference| above {MEAN_FREQUENCY_TOLERANCE} in {warn}" if warn else
                 f"all scenarios within {MEAN_FREQUENCY_TOLERANCE}"))
    return out

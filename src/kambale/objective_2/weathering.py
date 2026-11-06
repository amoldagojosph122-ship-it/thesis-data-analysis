"""Configuration 5: weathering front as a geological control, and fresh-rock indicator variography.

The predeclared file config/objective_2/weathering_config_O2-CFG-2026.11.06-5.yaml defines the run. The stage adds rows
under its own SENSITIVITY stage run and never writes a continuity handoff row. The weathering front is the shallowest
interval of each hole whose weathering code is in front_codes. Its continuity is tested along lines, by leave-one-out
inverse-distance interpolation and by an experimental semivariogram between holes. The fresh-rock indicator
variography repeats the DESIGN_8_2_v1 lateral analysis inside the moderately and slightly weathered binary intervals,
with a hole bootstrap band. Decisions are reported per experiment and do not change the configuration-2 handoff.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np

from kambale.config import CONFIG_DIR
from kambale.objective_2 import fitting, variogram
from kambale.objective_2.analysis import _direction_status, _fits_for, _store_fit
from kambale.objective_2.config import O2_CONFIG_PATH, O2_DB_PATH, StopError, code_commit, load_config, utc_now
from kambale.objective_2.db import connect_o2
from kambale.objective_2.pairs import bin_edges

WEATHERING_CONFIG_PATH = CONFIG_DIR / "objective_2" / "weathering_config_O2-CFG-2026.11.06-5.yaml"
FIT_MODELS = ("spherical", "exponential")
LOO_LINE = "LEAVE_ONE_LINE_OUT"
ZERO_TOLERANCE_M = 1e-6
IDW_COINCIDENT_M = 0.001         # a training hole this close to the target takes all the weight
SKILL_THRESHOLD = 0.8            # INTERPOLABLE when the IDW RMSE is at most 0.8 times the training-mean RMSE
STAGE_NOTE = "configuration 5: weathering front and fresh-rock variography"


def _not_assessed(reason: str) -> dict:
    return {"status": "NOT_ASSESSED", "reason": reason, "envelope": None}


def _num(x) -> float | None:
    x = float(x)
    return None if math.isnan(x) else x


# ---------------------------------------------------------------------------------------------------------------------
# Weathering front
# ---------------------------------------------------------------------------------------------------------------------

def extract_fronts(rows: list[dict], front_codes, reversal_codes) -> tuple[list[dict], list[str]]:
    """The weathering front of each hole, from every logged interval of the receipt (binary or not).

    rows: dicts with hole_id, line_code, upstream_interval_id, depth_from_m, midpoint_m, z_relative_m, weathering_code,
    easting_m and northing_m. The vertical position of the front is z = a * depth_from_m, where a is the least-squares
    slope of z_relative_m on midpoint_m through the origin, fitted on all intervals of the hole. Returns the fronts and
    the holes that carry no front-code interval.
    """
    by_hole: dict[str, list[dict]] = {}
    for r in rows:
        by_hole.setdefault(r["hole_id"], []).append(r)
    fronts, no_front = [], []
    for hole in sorted(by_hole):
        items = sorted(by_hole[hole], key=lambda r: (r["depth_from_m"], r["upstream_interval_id"]))
        mid = np.array([r["midpoint_m"] for r in items], dtype=np.float64)
        z = np.array([r["z_relative_m"] for r in items], dtype=np.float64)
        candidates = [r for r in items if r["weathering_code"] in front_codes]
        if not candidates:
            no_front.append(hole)
            continue
        slope = float(np.sum(mid * z) / np.sum(mid * mid))
        front = candidates[0]
        reversals = sum(1 for r in items if r["weathering_code"] in reversal_codes and r["depth_from_m"] > front["depth_from_m"])
        fronts.append({
            "hole_id": hole, "line_code": front["line_code"], "easting_m": float(front["easting_m"]),
            "northing_m": float(front["northing_m"]), "front_depth_m": float(front["depth_from_m"]),
            "front_z_relative_m": slope * float(front["depth_from_m"]), "n_reversal_intervals": int(reversals),
            "slope": slope,
        })
    return fronts, no_front


# ---------------------------------------------------------------------------------------------------------------------
# Continuity: along-line differences, inverse-distance leave-out checks, front semivariogram
# ---------------------------------------------------------------------------------------------------------------------

def along_line_adjacent(fronts: list[dict], collars: dict) -> list[tuple[float, float]]:
    """Consecutive holes by collar easting within each line: (absolute front difference, collar distance) pairs."""
    out = []
    for line in sorted({f["line_code"] for f in fronts}):
        members = sorted((f for f in fronts if f["line_code"] == line), key=lambda f: collars[f["hole_id"]][0])
        for a, b in zip(members, members[1:]):
            dist = math.hypot(collars[a["hole_id"]][0] - collars[b["hole_id"]][0],
                              collars[a["hole_id"]][1] - collars[b["hole_id"]][1])
            out.append((abs(a["front_z_relative_m"] - b["front_z_relative_m"]), dist))
    return out


def idw_predict(xy_train: np.ndarray, z_train: np.ndarray, xy_target, *, power: float, n_neighbours: int) -> float:
    """Inverse-distance weighting over the n nearest training holes. A training hole closer than IDW_COINCIDENT_M takes
    all the weight (the mean of such holes when several coincide)."""
    d = np.hypot(xy_train[:, 0] - xy_target[0], xy_train[:, 1] - xy_target[1])
    near = d < IDW_COINCIDENT_M
    if near.any():
        return float(np.mean(z_train[near]))
    order = np.argsort(d, kind="stable")[:n_neighbours]
    w = 1.0 / d[order] ** power
    return float(np.sum(w * z_train[order]) / np.sum(w))


def interpolation_check(xy: np.ndarray, z: np.ndarray, line: np.ndarray, scheme: str, *, power: float,
                        n_neighbours: int) -> dict:
    """Pooled RMSE of the inverse-distance prediction and of the fold's own training mean, over all held-out holes."""
    n = z.size
    if scheme == "LEAVE_ONE_HOLE_OUT":
        folds = [np.array([i]) for i in range(n)]
    elif scheme == "LEAVE_ONE_LINE_OUT":
        folds = [np.nonzero(line == ln)[0] for ln in np.unique(line)]
    else:
        raise StopError(f"unknown interpolation scheme {scheme}")
    err_idw, err_mean = [], []
    for targets in folds:
        mask = np.ones(n, dtype=bool)
        mask[targets] = False
        train = np.nonzero(mask)[0]
        if train.size == 0:
            raise StopError(f"{scheme}: a fold leaves no training hole")
        mean = float(np.mean(z[train]))
        for t in targets:
            pred = idw_predict(xy[train], z[train], xy[t], power=power, n_neighbours=n_neighbours)
            err_idw.append(pred - z[t])
            err_mean.append(mean - z[t])
    rmse_idw = float(np.sqrt(np.mean(np.square(err_idw))))
    rmse_mean = float(np.sqrt(np.mean(np.square(err_mean))))
    skill = rmse_idw / rmse_mean if rmse_mean > 0 else float("nan")
    return {"rmse_idw": rmse_idw, "rmse_training_mean": rmse_mean, "skill_ratio": skill,
            "interpolable": 1.0 if (not math.isnan(skill) and skill <= SKILL_THRESHOLD) else 0.0,
            "n_predicted": len(err_idw), "n_folds": len(folds)}


def front_semivariogram(xy: np.ndarray, z: np.ndarray, edges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pair counts and semivariance of the front between distinct holes, by horizontal lag bin."""
    i, j = np.triu_indices(z.size, k=1)
    d = np.hypot(xy[j, 0] - xy[i, 0], xy[j, 1] - xy[i, 1])
    keep = (d > ZERO_TOLERANCE_M) & (d >= edges[0]) & (d < edges[-1])
    b = np.searchsorted(edges, d[keep], side="right") - 1
    sq = 0.5 * (z[i[keep]] - z[j[keep]]) ** 2
    nb = len(edges) - 1
    n = np.bincount(b, minlength=nb).astype(np.int64)
    sums = np.bincount(b, weights=sq, minlength=nb)
    gamma = np.where(n > 0, sums / np.maximum(n, 1), np.nan)
    return n, gamma


# ---------------------------------------------------------------------------------------------------------------------
# Fresh-rock indicator variography: pairs, weights, hole bootstrap
# ---------------------------------------------------------------------------------------------------------------------

def subset_observations(obs: variogram.Observations, mask: np.ndarray) -> variogram.Observations:
    """Observations restricted to mask, with hole and line indices renumbered so that n_per_hole is consistent."""
    idx = np.nonzero(mask)[0]
    hole_keep = np.unique(obs.hole[idx])
    line_keep = np.unique(obs.line[idx])
    hole_new = np.searchsorted(hole_keep, obs.hole[idx]).astype(np.int64)
    line_new = np.searchsorted(line_keep, obs.line[idx]).astype(np.int64)
    return variogram.Observations(
        X=obs.X[idx].copy(), I=obs.I[idx].copy(), hole=hole_new, line=line_new,
        holes=[obs.holes[k] for k in hole_keep], lines=[obs.lines[k] for k in line_keep],
        n_per_hole=np.bincount(hole_new, minlength=len(hole_keep)).astype(np.float64),
        upstream_ids=[obs.upstream_ids[k] for k in idx])


def between_hole_pairs(X: np.ndarray, I: np.ndarray, hole: np.ndarray, edges: np.ndarray, *, horizontal: bool,
                       max_abs_dz: float | None) -> dict:
    """Every unordered pair of intervals in two different holes that passes the lag and relative-Z filters.

    Pairs of intervals in the same hole are never formed, so a hole never pairs with itself. Returns the lag bin, the
    indicator difference (0 or 1) and the two hole indices of each pair.
    """
    i, j = np.triu_indices(X.shape[0], k=1)
    different = hole[i] != hole[j]
    dxy = np.hypot(X[j, 0] - X[i, 0], X[j, 1] - X[i, 1])
    dz = X[j, 2] - X[i, 2]
    lag = dxy if horizontal else np.sqrt(dxy * dxy + dz * dz)
    keep = different & (lag > ZERO_TOLERANCE_M) & (lag >= edges[0]) & (lag < edges[-1])
    if max_abs_dz is not None:
        keep &= np.abs(dz) <= max_abs_dz
    i, j, lag = i[keep], j[keep], lag[keep]
    return {"bin": np.searchsorted(edges, lag, side="right").astype(np.int64) - 1,
            "diff": (I[i] != I[j]).astype(np.float64), "hi": hole[i].astype(np.int64),
            "hj": hole[j].astype(np.int64), "nb": len(edges) - 1}


def weighted_gamma(pairs: dict, mult: np.ndarray) -> np.ndarray:
    """gamma_b = sum(w * diff) / (2 * sum(w)) per bin, with w = mult[hole_i] * mult[hole_j]. NaN where the weight is zero."""
    nb = pairs["nb"]
    w = mult[pairs["hi"]] * mult[pairs["hj"]]
    sw = np.bincount(pairs["bin"], weights=w, minlength=nb)
    swd = np.bincount(pairs["bin"], weights=w * pairs["diff"], minlength=nb)
    return np.where(sw > 0, swd / (2.0 * np.where(sw > 0, sw, 1.0)), np.nan)


def hole_bootstrap(pairs: dict, n_holes: int, *, n_replicates: int, seed: int, confidence: float) -> dict:
    """Percentile band of the bin semivariance over hole resamples. A bin with zero weight in a replicate is skipped
    for that replicate."""
    rng = np.random.default_rng(seed)
    nb = pairs["nb"]
    draws = np.full((n_replicates, nb), np.nan)
    for r in range(n_replicates):
        idx = rng.integers(0, n_holes, size=n_holes)
        mult = np.bincount(idx, minlength=n_holes).astype(np.float64)
        draws[r] = weighted_gamma(pairs, mult)
    alpha = 100.0 * (1.0 - confidence) / 2.0
    lower, upper, median, used = (np.full(nb, np.nan) for _ in range(4))
    for k in range(nb):
        vals = draws[:, k][~np.isnan(draws[:, k])]
        used[k] = vals.size
        if vals.size:
            lower[k], upper[k], median[k] = np.percentile(vals, [alpha, 100.0 - alpha, 50.0])
    return {"lower": lower, "upper": upper, "median": median, "n_used": used}


# ---------------------------------------------------------------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------------------------------------------------------------

def _write_fronts(conn, rid: int, fronts: list[dict], version: str) -> None:
    for f in fronts:
        conn.execute("INSERT INTO weathering_front_observations (receipt_id, hole_id, line_code, easting_m, northing_m, "
                     "front_depth_m, front_z_relative_m, n_reversal_intervals, config_version) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (rid, f["hole_id"], f["line_code"], f["easting_m"], f["northing_m"], f["front_depth_m"],
                      f["front_z_relative_m"], f["n_reversal_intervals"], version))


def _diagnostic(conn, rid: int, version: str, group: str, name: str, value, unit: str, n_basis: int) -> None:
    conn.execute("INSERT INTO weathering_front_diagnostics (receipt_id, config_version, stat_group, stat_name, stat_value, "
                 "unit, n_basis) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (rid, version, group, name, None if value is None else _num(value), unit, n_basis))


def _write_diagnostics(conn, rid: int, version: str, fronts: list[dict], no_front: list[str], collars: dict,
                       cfg: dict) -> dict:
    out = {}
    adj = along_line_adjacent(fronts, collars)
    diffs = np.array([a[0] for a in adj])
    dists = np.array([a[1] for a in adj])
    n_adj = len(adj)
    along = {"n_adjacent_pairs": n_adj,
             "median_abs_front_difference_m": float(np.median(diffs)),
             "p90_abs_front_difference_m": float(np.percentile(diffs, 90)),
             "max_abs_front_difference_m": float(np.max(diffs)),
             "median_collar_distance_m": float(np.median(dists))}
    units = {"n_adjacent_pairs": "count"}
    for name, value in along.items():
        _diagnostic(conn, rid, version, "ALONG_LINE_ADJACENT", name, value, units.get(name, "m"), n_adj)
    out["along_line"] = along

    z = np.array([f["front_z_relative_m"] for f in fronts])
    n = z.size
    n_rev = sum(1 for f in fronts if f["n_reversal_intervals"] > 0)
    summary = {"n_holes": n, "mean_front_z_relative_m": float(np.mean(z)),
               "sd_front_z_relative_m": float(np.std(z, ddof=1)) if n > 1 else None,
               "min_front_z_relative_m": float(np.min(z)), "max_front_z_relative_m": float(np.max(z)),
               "n_holes_with_reversals": n_rev, "n_holes_without_front": len(no_front)}
    for name, value in summary.items():
        unit = "count" if name.startswith("n_") else "m"
        _diagnostic(conn, rid, version, "FRONT_SUMMARY", name, value, unit, n)
    out["front"] = summary

    xy = np.array([[f["easting_m"], f["northing_m"]] for f in fronts])
    line = np.array([f["line_code"] for f in fronts])
    fc = cfg["weathering_front"]["continuity"]["interpolation_check"]
    out["interpolation"] = {}
    for scheme in fc["schemes"]:
        res = interpolation_check(xy, z, line, scheme, power=float(fc["power"]), n_neighbours=int(fc["n_neighbours"]))
        group = f"INTERPOLATION_{scheme}"
        _diagnostic(conn, rid, version, group, "rmse_idw_m", res["rmse_idw"], "m", res["n_predicted"])
        _diagnostic(conn, rid, version, group, "rmse_training_mean_m", res["rmse_training_mean"], "m", res["n_predicted"])
        _diagnostic(conn, rid, version, group, "skill_ratio", res["skill_ratio"], "ratio", res["n_predicted"])
        _diagnostic(conn, rid, version, group, "interpolable", res["interpolable"], "flag", res["n_predicted"])
        out["interpolation"][scheme] = res

    sv = cfg["weathering_front"]["continuity"]["semivariogram"]
    edges = bin_edges(float(sv["lag_width_m"]), float(sv["lag_max_m"]))
    counts, gamma = front_semivariogram(xy, z, edges)
    min_pairs = int(sv["min_hole_pairs_per_bin"])
    supported = 0
    for k in range(len(edges) - 1):
        ok = bool(counts[k] >= min_pairs)
        supported += int(ok)
        conn.execute("INSERT INTO weathering_front_variogram (receipt_id, config_version, bin_index, lag_from_m, lag_to_m, "
                     "n_hole_pairs, gamma, supported) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (rid, version, k, float(edges[k]), float(edges[k + 1]), int(counts[k]),
                      _num(gamma[k]) if ok else None, int(ok)))
    out["front_variogram_supported_bins"] = supported
    return out


def _write_bands(conn, exp_id: int, bands: dict) -> None:
    for k in range(bands["n_used"].size):
        if bands["n_used"][k] == 0:
            continue
        conn.execute("INSERT INTO bootstrap_gamma_bands (experiment_id, bin_index, n_replicates, gamma_lower, gamma_upper, "
                     "gamma_median) VALUES (?, ?, ?, ?, ?, ?)",
                     (exp_id, k, int(bands["n_used"][k]), _num(bands["lower"][k]), _num(bands["upper"][k]),
                      _num(bands["median"][k])))


def _check_pairs(pairs: dict, res: dict, n_holes: int) -> None:
    """The explicit pair enumeration must reproduce the blockwise counts and the EQUAL_PAIR semivariance."""
    counts = np.bincount(pairs["bin"], minlength=pairs["nb"])
    if not np.array_equal(counts, res["n_pairs"]):
        raise StopError("the explicit between-hole pair enumeration disagrees with the blockwise pair counts")
    plain = weighted_gamma(pairs, np.ones(n_holes))
    sup = res["supported"]
    if not np.allclose(plain[sup], res["gamma"][sup], rtol=1e-9, atol=1e-12):
        raise StopError("the weighted semivariance with unit multiplicities differs from the plain semivariance")


def _fresh_experiment(conn, run_id: int, rid: int, cfg: dict, fit_cfg: dict, fresh: dict, spec, obs, pairing: str,
                      created: str) -> dict:
    """One fresh-rock experiment: the semivariogram, its hole bootstrap band, both fits, leave-one-line-out refits and
    stability. Every row is written under the configuration-5 stage run."""
    version, label = cfg["config_version"], cfg["label_rule"]["id"]
    res = variogram.compute(obs, spec)
    pairs = between_hole_pairs(obs.X, obs.I, obs.hole, spec.edges, horizontal=True, max_abs_dz=spec.max_abs_dz)
    _check_pairs(pairs, res, len(obs.holes))
    exp_id = variogram.store(conn, run_id, rid, res, config_version=version, label_rule_id=label, created_utc=created)
    bh = fresh["hole_bootstrap"]
    bands = hole_bootstrap(pairs, len(obs.holes), n_replicates=int(bh["n_replicates"]), seed=int(bh["seed"]),
                           confidence=float(bh["confidence"]))
    _write_bands(conn, exp_id, bands)

    fits = _fits_for(res, obs.p, fit_cfg)
    low, high = cfg["model_fitting"]["stable_if_range_ratio_between"]
    loo_runs = []
    for li in range(len(obs.lines)):
        loo_res = variogram.compute(obs, spec, allowed=obs.line != li)
        loo_runs.append((li, loo_res, _fits_for(loo_res, obs.p, fit_cfg)))
    stabs = {m: fitting.stability(fits[m], [f[m] for _, _, f in loo_runs], low=low, high=high) for m in FIT_MODELS}
    fit_ids = {m: _store_fit(conn, exp_id, fits[m], stabs[m], created) for m in FIT_MODELS}
    for li, loo_res, loo_fits in loo_runs:
        loo_exp = variogram.store(conn, run_id, rid, loo_res, config_version=version, label_rule_id=label, created_utc=created)
        for m in FIT_MODELS:
            loo_fit = _store_fit(conn, loo_exp, loo_fits[m], _not_assessed("leave-one-line-out refit"), created)
            conn.execute("INSERT INTO sensitivity_runs (run_id, base_experiment_id, variant_name, changed_factor, "
                         "changed_value, status, reason, experiment_id, fit_id) VALUES (?, NULL, ?, 'excluded_line', ?, "
                         "'COMPLETED', ?, ?, ?)",
                         (run_id, f"{label}:{spec.name}:{LOO_LINE}:{m}", obs.lines[li],
                          f"{loo_fits[m]['status']}; {loo_fits[m]['reason']}", loo_exp, loo_fit))

    supported = int(res["supported"].sum())
    fitted_stable = [m for m in FIT_MODELS if fits[m]["status"] == "FITTED" and stabs[m]["status"] == "STABLE"]
    decision = "PROVISIONAL (fresh rock)" if fitted_stable else "NOT_IDENTIFIABLE (fresh rock)"
    best = min((m for m in FIT_MODELS if fits[m]["status"] == "FITTED"), key=lambda m: fits[m]["objective"], default=None)
    reason = (f"{supported} supported bins; {len(obs.lines)} lines in the sample; " + "; ".join(
        f"{m} {fits[m]['status']}, stability {stabs[m]['status']}" for m in FIT_MODELS) + f"; decision {decision}")
    conn.execute("INSERT INTO sensitivity_runs (run_id, base_experiment_id, variant_name, changed_factor, changed_value, "
                 "status, reason, experiment_id, fit_id) VALUES (?, NULL, ?, 'sample_and_vertical_pairing', ?, 'COMPLETED', "
                 "?, ?, ?)",
                 (run_id, f"{label}:{spec.name}", f"{'+'.join(cfg['weathering_front']['front_codes'])};{pairing}",
                  reason, exp_id,
                  fit_ids[best] if best else None))
    return {"exp_id": exp_id, "supported": supported, "n_pairs": int(res["n_pairs"].sum()),
            "n_binary": int(obs.I.size), "p": obs.p, "n_lines": len(obs.lines), "n_holes": len(obs.holes),
            "fits": {m: {"status": fits[m]["status"], "reason": fits[m]["reason"]} for m in FIT_MODELS},
            "stability": {m: stabs[m]["status"] for m in FIT_MODELS}, "decision": decision, "bands": bands,
            "gamma": res["gamma"], "centres": res["centres"], "supported_mask": res["supported"]}


# ---------------------------------------------------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------------------------------------------------

def run(o2_path=O2_DB_PATH, config_path=WEATHERING_CONFIG_PATH, base_config_path=O2_CONFIG_PATH) -> dict:
    cfg, cfg_sha = load_config(config_path)
    base_cfg, _ = load_config(base_config_path)
    if cfg.get("extends") != base_cfg["config_version"]:
        raise StopError(f"{cfg['config_version']} extends {cfg.get('extends')}, not the base configuration "
                        f"{base_cfg['config_version']}")
    version = cfg["config_version"]
    wf = cfg["weathering_front"]
    fr = cfg["fresh_rock_variography"]
    conn = connect_o2(o2_path)
    try:
        rid = conn.execute("SELECT MAX(receipt_id) FROM source_receipts").fetchone()[0]
        if rid is None:
            raise StopError("no receipt: run the import first")
        done = conn.execute("SELECT COUNT(*) FROM weathering_front_observations WHERE receipt_id = ? AND config_version = ?",
                            (rid, version)).fetchone()[0]
        done += conn.execute("SELECT COUNT(*) FROM variogram_experiments WHERE receipt_id = ? AND config_version = ?",
                             (rid, version)).fetchone()[0]
        if done:
            raise StopError(f"configuration {version} has already run on receipt {rid}")

        rows = [dict(r) for r in conn.execute(
            "SELECT upstream_interval_id, hole_id, line_code, depth_from_m, midpoint_m, z_relative_m, weathering_code, "
            "easting_m, northing_m FROM analysis_observations WHERE receipt_id = ? ORDER BY upstream_interval_id", (rid,))]
        fronts, no_front = extract_fronts(rows, tuple(wf["front_codes"]), tuple(wf["weathered_codes"]))
        if not fronts:
            raise StopError("no weathering front-code interval in the receipt")
        collars = {r["hole_id"]: (r["utm_easting_m"], r["utm_northing_m"]) for r in conn.execute(
            "SELECT hole_id, utm_easting_m, utm_northing_m FROM collar_locations WHERE receipt_id = ?", (rid,))}
        missing = [f["hole_id"] for f in fronts if f["hole_id"] not in collars]
        if missing:
            raise StopError(f"{len(missing)} holes have no collar location")

        # Fresh-rock sample: binary intervals in the front codes, with the observation order of variogram.load_observations.
        obs_all = variogram.load_observations(conn, rid)
        codes = {r["upstream_interval_id"]: r["weathering_code"] for r in conn.execute(
            "SELECT upstream_interval_id, weathering_code FROM analysis_observations WHERE receipt_id = ? "
            "AND in_binary_target = 1", (rid,))}
        mask = np.array([codes[u] in wf["front_codes"] for u in obs_all.upstream_ids], dtype=bool)
        if not mask.any():
            raise StopError("no binary interval in the front codes")
        front_by_hole = {f["hole_id"]: f for f in fronts}
        sub = subset_observations(obs_all, mask)
        if any(h not in front_by_hole for h in sub.holes):
            raise StopError("a fresh-rock hole has no observed front")
        front_z_sub = np.array([front_by_hole[h]["front_z_relative_m"] for h in sub.holes])[sub.hole]

        fit_cfg = {"model_fitting": cfg["model_fitting"],
                   "lateral_between_hole": {"min_supported_bins_for_fit": fr["min_supported_bins_for_fit"]}}
        exp_specs = []
        for e in fr["experiments"]:
            exp_specs.append((e["direction_id"], e["vertical_pairing"]))

        conn.execute("BEGIN IMMEDIATE")
        try:
            run_id = conn.execute("INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, started_utc, "
                                  "status, code_commit, note) VALUES ('SENSITIVITY', ?, ?, ?, ?, 'RUNNING', ?, ?)",
                                  (version, cfg_sha, rid, utc_now(), code_commit(), STAGE_NOTE)).lastrowid
            created = utc_now()
            _write_fronts(conn, rid, fronts, version)
            diag = _write_diagnostics(conn, rid, version, fronts, no_front, collars, cfg)

            lat_edges = bin_edges(float(fr["lag_width_m"]), float(fr["lag_max_m"]))
            fresh_out = {}
            for direction, pairing in exp_specs:
                if pairing == "z_relative_m":
                    X2 = sub.X
                elif pairing == "depth_below_observed_front_m":
                    X2 = sub.X.copy()
                    X2[:, 2] = sub.X[:, 2] - front_z_sub
                else:
                    raise StopError(f"unknown vertical pairing {pairing}")
                obs_e = dataclasses.replace(sub, X=X2)
                spec = variogram.ExperimentSpec(
                    name=direction, family="LATERAL_BETWEEN", within="EXCLUDED", horizontal=True, edges=lat_edges,
                    lag_width_m=float(fr["lag_width_m"]), lag_max_m=float(fr["lag_max_m"]),
                    max_abs_dz=float(fr["max_abs_dz_m"]), min_pairs=int(fr["min_pairs_per_bin"]),
                    min_hole_pairs=int(fr["min_independent_hole_pairs_per_bin"]), variant="SENSITIVITY")
                probe = variogram.compute(obs_e, spec)
                status, reason = _direction_status(probe, int(fr["min_supported_bins_for_fit"]))
                if pairing == "z_relative_m":
                    basis = ("between-hole pairs of binary intervals with weathering code in front_codes; horizontal lag; "
                             "absolute relative-Z difference at most 3 m (pairs at similar depth below collar)")
                else:
                    basis = ("between-hole pairs of binary intervals with weathering code in front_codes; horizontal lag; "
                             "absolute difference of (z_relative_m minus the hole's observed front) at most 3 m (pairs at "
                             "similar depth below their own weathering front)")
                conn.execute("INSERT INTO direction_registry (receipt_id, direction_id, family, azimuth_deg, "
                             "angular_tolerance_deg, geometry_basis, status, reason) VALUES (?, ?, 'LATERAL_BETWEEN', NULL, "
                             "NULL, ?, ?, ?)", (rid, direction, basis, status, reason))
                fresh_out[direction] = _fresh_experiment(conn, run_id, rid, cfg, fit_cfg, fr, spec, obs_e, pairing, created)
                fresh_out[direction]["registry_status"] = status

            decisions = {d: v["decision"] for d, v in fresh_out.items()}
            note = STAGE_NOTE + "; fresh-rock decisions: " + "; ".join(f"{d} {v}" for d, v in decisions.items()) + \
                "; no handoff row written"
            conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ?, note = ? WHERE run_id = ?",
                         (utc_now(), note, run_id))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    fresh_summary = {d: {"registry_status": v["registry_status"], "n_holes": v["n_holes"], "n_lines": v["n_lines"],
                         "n_binary": v["n_binary"], "p_binary": v["p"], "supported_bins": v["supported"],
                         "n_pairs": v["n_pairs"], "fits": v["fits"], "stability": v["stability"],
                         "decision": v["decision"]} for d, v in fresh_out.items()}
    return {
        "run_id": run_id, "receipt_id": rid, "config_version": version, "config_sha256": cfg_sha,
        "front": diag["front"], "along_line": diag["along_line"],
        "interpolation": {s: {k: _num(v) if isinstance(v, float) else v for k, v in r.items()}
                          for s, r in diag["interpolation"].items()},
        "front_variogram_supported_bins": diag["front_variogram_supported_bins"],
        "fresh_rock": fresh_summary, "decisions": decisions,
        "handoff_rows_written": 0,
    }

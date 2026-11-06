"""Training-only indicator and residual variography for Objective 3.

The pair counter and the model functions are the audited Objective 2 implementations. The only change is that the
physical reference variance is passed explicitly, so the same code fits an indicator (variance p(1-p)) and a residual
(variance var(r)). A variogram is stored only for the outer training fold that produced it; no test label enters.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares

from kambale.objective_2.fitting import gamma_model
from kambale.objective_2.pairs import bin_edges

BLOCK = 512
SEEDS = (
    (0.5, 0.5, 0.25),
    (0.5, 1.0, 0.5),
    (0.1, 0.8, 0.8),
)


def accumulate_sq(values: np.ndarray, X: np.ndarray, hole: np.ndarray, edges: np.ndarray, *,
                   allowed: np.ndarray | None = None, max_abs_dz: float | None = None,
                   zero_tolerance_m: float = 1e-6) -> dict:
    """Between-hole pair counts and the sum of squared value differences per lag bin.

    This is the continuous form of the Objective 2 pair counter: for a 0/1 indicator the squared difference is the
    different-class count, so the same routine serves the indicator and the residual. Self-pairs and zero-distance
    pairs never reach a bin. The lag is horizontal; pairs must lie within `max_abs_dz` if it is given.
    """
    n = values.shape[0]
    nb = len(edges) - 1
    K = int(hole.max()) + 1
    n_pairs = np.zeros(nb, np.int64)
    sum_sq = np.zeros(nb)
    code_bin, code_val = [], []
    all_idx = np.arange(n)
    for a0 in range(0, n, BLOCK):
        a1 = min(a0 + BLOCK, n)
        ii = all_idx[a0:a1]
        dx = X[None, :, 0] - X[ii, None, 0]
        dy = X[None, :, 1] - X[ii, None, 1]
        dz = X[None, :, 2] - X[ii, None, 2]
        lag = np.sqrt(dx * dx + dy * dy)
        valid = (all_idx[None, :] > ii[:, None]) & (lag > zero_tolerance_m) & (lag >= edges[0]) & (lag < edges[-1])
        if max_abs_dz is not None:
            valid &= np.abs(dz) <= max_abs_dz
        if allowed is not None:
            valid &= allowed[ii][:, None] & allowed[None, :]
        valid &= hole[ii][:, None] != hole[None, :]
        r, c = np.nonzero(valid)
        if r.size == 0:
            continue
        b = np.searchsorted(edges, lag[r, c], side="right") - 1
        gi = ii[r]
        gj = c
        sq = (values[gi] - values[gj]) ** 2
        n_pairs += np.bincount(b, minlength=nb)
        sum_sq += np.bincount(b, weights=sq, minlength=nb)
        lo = np.minimum(hole[gi], hole[gj])
        hi = np.maximum(hole[gi], hole[gj])
        code_bin.append(b.astype(np.int64))
        code_val.append((lo * K + hi).astype(np.int64))
    n_hole_pairs = np.zeros(nb, np.int64)
    if code_bin:
        bins = np.concatenate(code_bin)
        codes = np.concatenate(code_val)
        unique_keys = np.unique(bins * (K * K) + codes)
        n_hole_pairs = np.bincount(unique_keys // (K * K), minlength=nb).astype(np.int64)
    return {"n_pairs": n_pairs, "sum_sq": sum_sq, "n_hole_pairs": n_hole_pairs}


def _edges(config: dict) -> np.ndarray:
    v = config["variogram"]
    return bin_edges(float(v["lag_width_m"]), float(v["lag_max_m"]))


def experimental(values: np.ndarray, X: np.ndarray, hole: np.ndarray, config: dict,
                 allowed: np.ndarray | None = None) -> dict:
    """Experimental lateral between-hole semivariogram of one value vector."""
    v = config["variogram"]
    edges = _edges(config)
    acc = accumulate_sq(values, X, hole, edges, allowed=allowed, max_abs_dz=float(v["max_abs_dz_m"]))
    n = acc["n_pairs"]
    with np.errstate(divide="ignore", invalid="ignore"):
        gamma = acc["sum_sq"] / (2.0 * n)
    supported = (n >= int(v["min_pairs_per_bin"])) & (acc["n_hole_pairs"] >= int(v["min_independent_hole_pairs_per_bin"]))
    return {"edges": edges, "centres": 0.5 * (edges[:-1] + edges[1:]), "n_pairs": n, "n_hole_pairs": acc["n_hole_pairs"],
            "gamma": np.where(supported, gamma, np.nan), "supported": supported}


def fit(centres, gamma, n_pairs, model: str, variance: float, *, a_min: float, a_max: float, min_bins: int,
        min_sill_fraction: float, sill_factor: float) -> dict:
    """Constrained Cressie-weighted least squares with the Objective 2 identifiability rules."""
    keep = np.isfinite(gamma) & (n_pairs > 0)
    h = np.asarray(centres, dtype=np.float64)[keep]
    g = np.asarray(gamma, dtype=np.float64)[keep]
    n = np.asarray(n_pairs, dtype=np.float64)[keep]
    base = {"model": model, "n_bins": int(h.size), "params": None, "objective": None, "admissible": None,
            "lower_bounds": None, "upper_bounds": None}
    if h.size < min_bins:
        return {**base, "status": "NOT_IDENTIFIABLE", "reason": f"{h.size} supported bins; {min_bins} required"}
    v = max(float(variance), 1e-12)
    lower = np.array([0.0, 0.0, float(a_min)])
    upper = np.array([v, sill_factor * v, float(a_max)])
    if upper[2] <= lower[2]:
        return {**base, "status": "NOT_IDENTIFIABLE", "reason": "no supported lag range"}
    base["lower_bounds"], base["upper_bounds"] = lower, upper
    weights = np.sqrt(n / np.maximum(g, 1e-6) ** 2)
    best = None
    for f_nug, f_sill, f_range in SEEDS:
        x0 = np.array([f_nug * max(g.min(), 1e-6), f_sill * v, f_range * a_max])
        eps = 1e-9 * (upper - lower)
        x0 = np.clip(x0, lower + eps, upper - eps)

        def residuals(x):
            return weights * (g - gamma_model(h, model, x[0], x[1], x[2]))

        res = least_squares(residuals, x0, bounds=(lower, upper), method="trf", max_nfev=5000)
        if np.isfinite(res.cost) and (best is None or res.cost < best.cost):
            best = res
    if best is None:
        return {**base, "status": "NOT_IDENTIFIABLE", "reason": "no seed converged"}
    c0, c1, a = (float(x) for x in best.x)
    reasons = []
    if a <= a_min * (1.0 + 1e-3):
        reasons.append("range at the smallest supported lag: no dependence beyond the nugget")
    if a >= 0.95 * a_max:
        reasons.append("range at the upper bound: not identified inside the supported lags")
    if c1 < min_sill_fraction * v:
        reasons.append(f"structured sill below {min_sill_fraction:.0%} of the reference variance")
    if c1 >= 0.99 * upper[1]:
        reasons.append("structured sill at the upper bound")
    ok = all(math.isfinite(x) for x in (c0, c1, a)) and c0 >= 0 and c1 >= 0 and a > 0
    status = "FITTED" if ok and not reasons else ("INADMISSIBLE" if not ok else "NOT_IDENTIFIABLE")
    return {**base, "status": status, "reason": "; ".join(reasons) or "converged inside bounds", "params": (c0, c1, a),
            "objective": float(2.0 * best.cost), "admissible": ok}


def _stability(base: dict, leave_out: list[dict], low: float, high: float) -> dict:
    if base["status"] != "FITTED":
        return {"status": "NOT_ASSESSED", "reason": "base fit is not FITTED", "envelope": None}
    if not leave_out:
        return {"status": "NOT_ASSESSED", "reason": "no leave-one-line-out fits", "envelope": None}
    if any(r["status"] != "FITTED" for r in leave_out):
        bad = sorted({r["status"] for r in leave_out if r["status"] != "FITTED"})
        return {"status": "UNSTABLE", "reason": f"a leave-one-line-out refit was {', '.join(bad)}", "envelope": None}
    a0 = base["params"][2]
    ratios = np.array([r["params"][2] for r in leave_out]) / a0
    inside = bool(np.all((ratios >= low) & (ratios <= high)))
    return {"status": "STABLE" if inside else "UNSTABLE",
            "reason": f"range ratios {ratios.min():.2f} to {ratios.max():.2f} "
                      f"{'inside' if inside else ' outside'} [{low:g}, {high:g}]",
            "envelope": None}


def fit_family(values: np.ndarray, X: np.ndarray, hole: np.ndarray, line: np.ndarray, config: dict) -> dict:
    """Both candidate models, training-only leave-one-line-out stability, and a handoff model when one is supported."""
    v = config["variogram"]
    variance = float(np.var(values))
    result = experimental(values, X, hole, config)
    kept = result["supported"]
    a_min = float(result["centres"][kept][0]) if kept.any() else float(v["lag_width_m"])
    lows, highs = v["stable_if_range_ratio_between"]
    fits, stabs, loo = {}, {}, {}
    for model in v["models"]:
        fits[model] = fit(result["centres"], result["gamma"], result["n_pairs"], model, variance, a_min=a_min,
                          a_max=float(v["lag_max_m"]), min_bins=int(v["min_supported_bins_for_fit"]),
                          min_sill_fraction=float(v["min_structured_sill_fraction"]),
                          sill_factor=float(v["sill_factor"]))
        refits = []
        for li in sorted(set(int(x) for x in line)):
            r = experimental(values, X, hole, config, allowed=line != li)
            keep = r["supported"]
            amin = float(r["centres"][keep][0]) if keep.any() else float(v["lag_width_m"])
            refits.append(fit(r["centres"], r["gamma"], r["n_pairs"], model, variance, a_min=amin,
                              a_max=float(v["lag_max_m"]), min_bins=int(v["min_supported_bins_for_fit"]),
                              min_sill_fraction=float(v["min_structured_sill_fraction"]),
                              sill_factor=float(v["sill_factor"])))
        loo[model] = refits
        stabs[model] = _stability(fits[model], refits, float(lows), float(highs))
    candidates = [m for m in v["models"] if fits[m]["status"] == "FITTED" and
                  (not v["require_stability_for_kriging"] or stabs[m]["status"] == "STABLE")]
    if not candidates:
        status = "NOT_ESTIMABLE"
        reason = "; ".join(f"{m}: {fits[m]['status']} ({fits[m]['reason']}); stability {stabs[m]['status']} "
                           f"({stabs[m]['reason']})" for m in v["models"])
        chosen = None
    else:
        chosen = min(candidates, key=lambda m: fits[m]["objective"])
        status = "FITTED"
        reason = f"{chosen} selected with objective {fits[chosen]['objective']:.6g} and stability {stabs[chosen]['status']}"
    return {"bins": result, "fits": fits, "stability": stabs, "leave_out": loo, "variance": variance,
            "chosen_model": chosen, "chosen_params": fits[chosen]["params"] if chosen else None,
            "status": status, "reason": reason}

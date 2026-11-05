"""Indicator semivariogram models, constrained weighted least squares, identifiability and leave-one-line-out stability
(specification 02, sections 5 to 7). A fit that cannot be identified is reported as such, with no invented parameter.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares

SEEDS = (  # (nugget, structured sill, range) as fractions of (min gamma, p(1-p), lag maximum); clipped to bounds
    (0.5, 0.5, 0.25),
    (0.5, 1.0, 0.5),
    (0.1, 0.8, 0.8),
)


def gamma_model(h, model: str, c0: float, c1: float, a: float):
    h = np.asarray(h, dtype=np.float64)
    if model == "spherical":
        u = np.minimum(h / a, 1.0)
        return c0 + c1 * (1.5 * u - 0.5 * u ** 3)
    if model == "exponential":
        return c0 + c1 * (1.0 - np.exp(-3.0 * h / a))
    raise ValueError(f"unknown model {model}")


def admissible(c0: float, c1: float, a: float) -> bool:
    """Non-negative nugget and sill, positive range, all values finite. Both families are valid in three dimensions."""
    return all(math.isfinite(v) for v in (c0, c1, a)) and c0 >= 0.0 and c1 >= 0.0 and a > 0.0


def fit(centres, gamma, n_pairs, model: str, p: float, *, a_min: float, a_max: float, min_bins: int,
        min_sill_fraction: float = 0.05, sill_factor: float = 1.5) -> dict:
    """Constrained Cressie-weighted least squares on the supported bins, followed by the identifiability rules."""
    pq = p * (1.0 - p)
    keep = np.isfinite(gamma) & (n_pairs > 0)
    h = np.asarray(centres, dtype=np.float64)[keep]
    g = np.asarray(gamma, dtype=np.float64)[keep]
    n = np.asarray(n_pairs, dtype=np.float64)[keep]
    base = {"model": model, "n_bins": int(h.size), "params": None, "objective": None, "admissible": None,
            "marginal_departure": None, "lower_bounds": None, "upper_bounds": None}
    if h.size < min_bins:
        return {**base, "status": "NOT_IDENTIFIABLE", "reason": f"{h.size} supported bins; {min_bins} required"}
    lower = np.array([0.0, 0.0, a_min])
    upper = np.array([pq, sill_factor * pq, a_max])
    base["lower_bounds"], base["upper_bounds"] = lower, upper
    weights = np.sqrt(n / np.maximum(g, 1e-6) ** 2)
    best = None
    for f_nug, f_sill, f_range in SEEDS:
        x0 = np.array([f_nug * max(g.min(), 1e-6), f_sill * pq, f_range * a_max])
        eps = 1e-9 * (upper - lower)
        x0 = np.clip(x0, lower + eps, upper - eps)

        def residuals(x):
            return weights * (g - gamma_model(h, model, x[0], x[1], x[2]))

        res = least_squares(residuals, x0, bounds=(lower, upper), method="trf", max_nfev=5000)
        if np.isfinite(res.cost) and (best is None or res.cost < best.cost):
            best = res
    if best is None:
        return {**base, "status": "NOT_IDENTIFIABLE", "reason": "no seed converged"}
    c0, c1, a = (float(v) for v in best.x)
    reasons = []
    if a <= a_min * (1.0 + 1e-3):
        reasons.append("range at the smallest supported lag: no spatial dependence beyond the nugget")
    if a >= 0.95 * a_max:
        reasons.append("range at the upper bound: not identified inside the supported lags")
    if c1 < min_sill_fraction * pq:
        reasons.append(f"structured sill below {min_sill_fraction:.0%} of p(1-p): no structure beyond the nugget")
    if c1 >= 0.99 * upper[1]:
        reasons.append("structured sill at the upper bound")
    ok = admissible(c0, c1, a)
    status = "FITTED" if ok and not reasons else ("INADMISSIBLE" if not ok else "NOT_IDENTIFIABLE")
    return {**base, "status": status, "reason": "; ".join(reasons) or "converged inside bounds",
            "params": (c0, c1, a), "objective": float(2.0 * best.cost), "admissible": ok,
            "marginal_departure": (c0 + c1) / pq - 1.0 if pq > 0 else None}


def stability(base: dict, leave_out: list[dict], low: float = 0.5, high: float = 2.0) -> dict:
    """Leave-one-line-out envelope. A fit is STABLE only if every refit is FITTED and every range ratio is inside."""
    if base["status"] != "FITTED":
        return {"status": "NOT_ASSESSED", "reason": "base fit is not FITTED", "envelope": None}
    if not leave_out:
        return {"status": "NOT_ASSESSED", "reason": "no leave-one-line-out fits", "envelope": None}
    a0 = base["params"][2]
    if any(r["status"] != "FITTED" for r in leave_out):
        bad = sorted({r["status"] for r in leave_out if r["status"] != "FITTED"})
        return {"status": "UNSTABLE", "reason": f"a leave-one-line-out refit was {', '.join(bad)}", "envelope": None}
    ranges = np.array([r["params"][2] for r in leave_out])
    ratios = ranges / a0
    envelope = {k: (float(min(r["params"][i] for r in leave_out)), float(max(r["params"][i] for r in leave_out)))
                for i, k in enumerate(("nugget", "structured_sill", "range_m"))}
    if np.all((ratios >= low) & (ratios <= high)):
        return {"status": "STABLE", "reason": f"range ratios {ratios.min():.2f} to {ratios.max():.2f} inside [{low}, {high}]",
                "envelope": envelope}
    return {"status": "UNSTABLE", "reason": f"range ratios {ratios.min():.2f} to {ratios.max():.2f} outside [{low}, {high}]",
            "envelope": envelope}

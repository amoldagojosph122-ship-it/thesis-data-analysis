"""Blockwise pair accumulation with exact integer counts (specification 06, section 3.1).

Self-pairs and duplicate-coordinate pairs never reach a bin. Within-hole and between-hole pairs are separated by the
`within` argument. The lag is either the three-dimensional distance or the horizontal distance; the horizontal lag is
used with an absolute relative-Z limit so that the comparison is made between intervals at similar depth. Azimuth
classes are taken modulo 180 degrees, measured clockwise from grid north, on the horizontal difference.
"""

from __future__ import annotations

import numpy as np

BLOCK = 512


def accumulate(X, I, hole, n_per_hole, edges, *, within="EXCLUDED", horizontal=False, max_abs_dz=None,
               azimuth_deg=None, tolerance_deg=None, allowed=None, zero_tolerance_m=1e-6):
    """Count pairs per lag bin.

    X: (n, 3) array of E, N and relative Z in metres.  I: (n,) indicator 0/1.  hole: (n,) integer hole index.
    n_per_hole: (K,) binary intervals per hole, used by the equal-hole weights.  edges: monotone bin edges.
    within: EXCLUDED (between-hole pairs only), INCLUDED (both), ONLY (within-hole pairs only).
    horizontal: bin on the horizontal distance instead of the three-dimensional distance.
    max_abs_dz: keep only pairs whose relative-Z difference is at most this many metres (None keeps all).
    Returns per-bin arrays for pair counts, different-class counts, within-hole counts, weight sums and the number of
    independent hole pairs (distinct unordered hole pairs, or distinct holes for within-hole pairs).
    """
    n = X.shape[0]
    nb = len(edges) - 1
    K = int(hole.max()) + 1
    n_pairs = np.zeros(nb, np.int64)
    n_diff = np.zeros(nb, np.int64)
    n_within = np.zeros(nb, np.int64)
    sum_w = np.zeros(nb)
    sum_w_diff = np.zeros(nb)
    code_bin, code_val = [], []
    all_idx = np.arange(n)
    for a0 in range(0, n, BLOCK):
        a1 = min(a0 + BLOCK, n)
        ii = all_idx[a0:a1]
        dx = X[None, :, 0] - X[ii, None, 0]
        dy = X[None, :, 1] - X[ii, None, 1]
        dz = X[None, :, 2] - X[ii, None, 2]
        dxy = np.sqrt(dx * dx + dy * dy)
        lag = dxy if horizontal else np.sqrt(dxy * dxy + dz * dz)
        valid = (all_idx[None, :] > ii[:, None]) & (lag > zero_tolerance_m) & (lag >= edges[0]) & (lag < edges[-1])
        if max_abs_dz is not None:
            valid &= np.abs(dz) <= max_abs_dz
        if allowed is not None:
            valid &= allowed[ii][:, None] & allowed[None, :]
        same = hole[ii][:, None] == hole[None, :]
        if within == "EXCLUDED":
            valid &= ~same
        elif within == "ONLY":
            valid &= same
        if azimuth_deg is not None:
            theta = np.degrees(np.arctan2(dx, dy)) % 180.0
            diff_deg = np.abs(theta - azimuth_deg)
            diff_deg = np.minimum(diff_deg, 180.0 - diff_deg)
            valid &= diff_deg <= tolerance_deg
        r, c = np.nonzero(valid)
        if r.size == 0:
            continue
        dist = lag[r, c]
        b = np.searchsorted(edges, dist, side="right") - 1
        gi = ii[r]
        gj = c
        is_diff = (I[gi] != I[gj]).astype(np.float64)
        same_pair = same[r, c].astype(np.float64)
        w = 1.0 / (n_per_hole[hole[gi]] * n_per_hole[hole[gj]])
        n_pairs += np.bincount(b, minlength=nb)
        n_diff += np.bincount(b, weights=is_diff, minlength=nb).astype(np.int64)
        n_within += np.bincount(b, weights=same_pair, minlength=nb).astype(np.int64)
        sum_w += np.bincount(b, weights=w, minlength=nb)
        sum_w_diff += np.bincount(b, weights=w * is_diff, minlength=nb)
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
    return {
        "n_pairs": n_pairs,
        "n_diff": n_diff,
        "n_equal": n_pairs - n_diff,
        "n_within": n_within,
        "n_between": n_pairs - n_within,
        "sum_w": sum_w,
        "sum_w_diff": sum_w_diff,
        "n_hole_pairs": n_hole_pairs,
    }


def bin_edges(width: float, maximum: float) -> np.ndarray:
    """Equal-width edges from 0 to maximum. The number of bins is round(maximum / width)."""
    n = int(round(maximum / width))
    if n < 1 or abs(n * width - maximum) > 1e-9:
        raise ValueError("maximum must be a whole multiple of the lag width")
    return np.linspace(0.0, maximum, n + 1)


def integer_lag_edges(maximum: int) -> np.ndarray:
    """Edges centred on integer lags 1..maximum, so that adjacent 1 m intervals fall in the lag-1 bin."""
    return np.arange(0.5, maximum + 1.0, 1.0)

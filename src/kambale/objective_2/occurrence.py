"""Occurrence summaries by hole, line, depth bin and weathering class, and spatial support statistics
(specification 02, section 4 and specification 04, section 5). Denominators are stated in every table."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

STATES = ("POSITIVE", "NEGATIVE", "AMBIGUOUS", "UNRESOLVED")


def _runs(rows) -> int:
    """Number of maximal runs of POSITIVE intervals that are contiguous in depth."""
    count, prev = 0, None
    for r in rows:
        is_pos = r["label_state"] == "POSITIVE"
        if is_pos and not (prev is not None and prev["label_state"] == "POSITIVE" and prev["depth_to_m"] == r["depth_from_m"]):
            count += 1
        prev = r
    return count


def _counts(rows) -> dict:
    c = {s: 0 for s in STATES}
    for r in rows:
        c[r["label_state"]] += 1
    binary = c["POSITIVE"] + c["NEGATIVE"]
    return {"n": len(rows), "binary_n": binary, "positive_n": c["POSITIVE"], "negative_n": c["NEGATIVE"],
            "ambiguous_n": c["AMBIGUOUS"], "unresolved_n": c["UNRESOLVED"],
            "positive_m": float(sum(r["support_length_m"] for r in rows if r["label_state"] == "POSITIVE")),
            "logged_m": float(sum(r["support_length_m"] for r in rows)),
            "fraction": (c["POSITIVE"] / binary) if binary else None}


def summaries(conn, receipt_id: int) -> dict:
    """Hole, line, depth-lithology and weathering summaries computed from analysis_observations of one receipt."""
    rows = [dict(r) for r in conn.execute(
        "SELECT hole_id, line_code, depth_from_m, depth_to_m, support_length_m, label_state, rock_code_raw, "
        "weathering_code FROM analysis_observations WHERE receipt_id = ? ORDER BY hole_id, depth_from_m", (receipt_id,))]
    by_hole = defaultdict(list)
    for r in rows:
        by_hole[r["hole_id"]].append(r)
    hole_rows = []
    for hole, hr in sorted(by_hole.items()):
        c = _counts(hr)
        hole_rows.append({"hole_id": hole, "line_code": hr[0]["line_code"], **c,
                          "intersections": _runs(hr)})
    by_line = defaultdict(list)
    for r in rows:
        by_line[r["line_code"]].append(r)
    line_rows = []
    for line, lr in sorted(by_line.items()):
        c = _counts(lr)
        n_holes = len({r["hole_id"] for r in lr})
        line_rows.append({"line_code": line, "n_holes": n_holes, **c,
                          "intersections": sum(h["intersections"] for h in hole_rows if h["line_code"] == line)})
    depth_rows = defaultdict(lambda: {"binary_n": 0, "positive_n": 0})
    for r in rows:
        if r["label_state"] not in ("POSITIVE", "NEGATIVE"):
            continue
        lo = int(r["depth_from_m"] // 10) * 10
        code = r["rock_code_raw"] or "MISSING"
        key = (float(lo), float(lo + 10), code)
        depth_rows[key]["binary_n"] += 1
        depth_rows[key]["positive_n"] += 1 if r["label_state"] == "POSITIVE" else 0
    depth_out = [{"depth_bin_from_m": k[0], "depth_bin_to_m": k[1], "rock_code_raw": k[2], **v,
                  "prevalence": (v["positive_n"] / v["binary_n"]) if v["binary_n"] else None}
                 for k, v in sorted(depth_rows.items())]
    weather = defaultdict(int)
    for r in rows:
        weather[(r["weathering_code"] or "MISSING", r["label_state"])] += 1
    weather_out = [{"weathering_code": k[0], "label_state": k[1], "n_intervals": v} for k, v in sorted(weather.items())]
    return {"holes": hole_rows, "lines": line_rows, "depth": depth_out, "weathering": weather_out}


def support_statistics(conn, receipt_id: int) -> list[dict]:
    """Collar spacing statistics from collar_locations: nearest neighbour and all collar pairs (UTM metres)."""
    collars = [dict(r) for r in conn.execute(
        "SELECT hole_id, line_code, utm_easting_m, utm_northing_m FROM collar_locations WHERE receipt_id = ? ORDER BY hole_id",
        (receipt_id,))]
    E = np.array([c["utm_easting_m"] for c in collars])
    N = np.array([c["utm_northing_m"] for c in collars])
    D = np.hypot(E[:, None] - E[None, :], N[:, None] - N[None, :])
    np.fill_diagonal(D, np.inf)
    nearest = D.min(axis=1)
    upper = D[np.triu_indices(len(collars), 1)]
    out = []

    def add(group, name, value, unit, n):
        out.append({"stat_group": group, "stat_name": name, "stat_value": float(value), "unit": unit, "n_basis": int(n)})

    for name, fn in (("min", np.min), ("p05", lambda x: np.quantile(x, 0.05)), ("median", np.median),
                     ("p95", lambda x: np.quantile(x, 0.95)), ("max", np.max)):
        add("COLLAR_NEAREST", name, fn(nearest), "m", nearest.size)
        add("COLLAR_PAIR", name, fn(upper), "m", upper.size)
    add("COLLAR_NEAREST", "n", nearest.size, "count", nearest.size)
    add("COLLAR_PAIR", "n", upper.size, "count", upper.size)
    for line in sorted({c["line_code"] for c in collars}):
        add("LINE", f"holes_{line}", sum(1 for c in collars if c["line_code"] == line), "count", 1)
    return out

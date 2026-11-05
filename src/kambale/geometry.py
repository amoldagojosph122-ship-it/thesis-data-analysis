"""Straight-hole geometry, coordinate-pair statistics and provisional drill-line grouping.

Convention (config/coordinate_decisions.yaml, status PROVISIONAL):
  dip d is signed from horizontal, negative downward; azimuth a is clockwise from north.
  delta_E = m * cos(d) * sin(a); delta_N = m * cos(d) * cos(a); delta_Z = m * sin(d)
  with m = (DEPTH_FROM + DEPTH_TO) / 2 and angles in radians.
Vertical values are relative to the collar. Absolute elevation is never produced here.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

ROUND_DECIMALS = 4  # 0.1 mm; removes floating-point residue such as cos(90 deg) ~ 6e-17


@dataclass(frozen=True)
class Offsets:
    delta_e: float
    delta_n: float
    delta_z: float


def straight_hole_offsets(midpoint_m: float, dip_deg: float, azimuth_deg: float) -> Offsets:
    if not (-90.0 <= dip_deg <= 0.0):
        raise ValueError(f"dip {dip_deg} outside adopted convention [-90, 0]")
    if not (0.0 <= azimuth_deg < 360.0):
        raise ValueError(f"azimuth {azimuth_deg} outside adopted convention [0, 360)")
    dip = math.radians(dip_deg)
    azimuth = math.radians(azimuth_deg)
    delta_e = midpoint_m * math.cos(dip) * math.sin(azimuth)
    delta_n = midpoint_m * math.cos(dip) * math.cos(azimuth)
    delta_z = midpoint_m * math.sin(dip)
    return Offsets(round(delta_e, ROUND_DECIMALS) + 0.0,
                   round(delta_n, ROUND_DECIMALS) + 0.0,
                   round(delta_z, ROUND_DECIMALS) + 0.0)


def line_code_for(nominal_northing_m: float) -> str:
    return f"NOM_N{int(round(nominal_northing_m))}"


def assign_drill_lines(collars: list[dict]) -> dict[str, dict]:
    """Group holes by their nominal (Easting/Northing column) Northing. Returns hole_id -> line info."""
    groups: dict[float, list[str]] = {}
    for collar in collars:
        groups.setdefault(collar["northing_alt_m"], []).append(collar["hole_id"])
    assignment = {}
    for nominal, hole_ids in sorted(groups.items()):
        code = line_code_for(nominal)
        for hole_id in sorted(hole_ids):
            assignment[hole_id] = {"line_code": code, "nominal_northing_m": float(nominal)}
    return assignment


def pair_discrepancies(collars: list[dict]) -> list[dict]:
    """Horizontal distance between the UTM pair and the Easting/Northing pair for each hole."""
    rows = []
    for collar in collars:
        d_e = collar["utm_easting_m"] - collar["easting_alt_m"]
        d_n = collar["utm_northing_m"] - collar["northing_alt_m"]
        rows.append({"hole_id": collar["hole_id"], "d_e": d_e, "d_n": d_n,
                     "horizontal_m": math.hypot(d_e, d_n)})
    return rows


def pair_statistics(rows: list[dict]) -> dict:
    distances = [r["horizontal_m"] for r in rows]
    return {
        "n": len(distances),
        "median_m": round(statistics.median(distances), 4),
        "max_m": round(max(distances), 4),
        "n_over_5m": sum(1 for d in distances if d > 5.0),
        "mean_d_e_m": round(statistics.fmean(r["d_e"] for r in rows), 4),
        "mean_d_n_m": round(statistics.fmean(r["d_n"] for r in rows), 4),
        "sd_d_e_m": round(statistics.pstdev([r["d_e"] for r in rows]), 4),
        "sd_d_n_m": round(statistics.pstdev([r["d_n"] for r in rows]), 4),
    }


def on_five_metre_grid(value: float) -> bool:
    return abs(value / 5.0 - round(value / 5.0)) < 1e-9


def nearest_neighbour_spacing(points: list[tuple[float, float]]) -> list[float]:
    """Nearest-neighbour distance per point (pure Python; sufficient for 71 collars)."""
    out = []
    for i, (xi, yi) in enumerate(points):
        best = math.inf
        for j, (xj, yj) in enumerate(points):
            if i == j:
                continue
            best = min(best, math.hypot(xi - xj, yi - yj))
        out.append(best)
    return out

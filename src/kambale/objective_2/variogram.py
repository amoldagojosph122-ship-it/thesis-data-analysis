"""Experimental indicator semivariograms (specification 02, section 3) and their storage."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from kambale.objective_2.pairs import accumulate, bin_edges, integer_lag_edges


@dataclass
class ExperimentSpec:
    name: str                       # DIRECTION_ID stored in direction_registry
    family: str                     # OMNI_BETWEEN, LATERAL_BETWEEN, WITHIN_HOLE or HORIZONTAL_AZIMUTH
    within: str                     # EXCLUDED, INCLUDED or ONLY
    edges: np.ndarray
    lag_width_m: float
    lag_max_m: float
    horizontal: bool = False        # True: lag is the horizontal distance
    max_abs_dz: float | None = None # relative-Z limit for the pair (None keeps all pairs)
    azimuth_deg: float | None = None
    tolerance_deg: float | None = None
    weighting: str = "EQUAL_PAIR"   # EQUAL_PAIR or EQUAL_HOLE
    min_pairs: int = 100
    min_hole_pairs: int = 10
    variant: str = "BASE"
    notes: list[str] = field(default_factory=list)


@dataclass
class Observations:
    X: np.ndarray
    I: np.ndarray
    hole: np.ndarray
    line: np.ndarray
    holes: list
    lines: list
    n_per_hole: np.ndarray
    upstream_ids: list

    @property
    def p(self) -> float:
        return float(self.I.mean())


def load_observations(conn, receipt_id: int) -> Observations:
    """Binary observations of one receipt, in upstream interval order."""
    rows = conn.execute(
        "SELECT upstream_interval_id, hole_id, line_code, easting_m, northing_m, z_relative_m, indicator "
        "FROM analysis_observations WHERE receipt_id = ? AND in_binary_target = 1 ORDER BY upstream_interval_id",
        (receipt_id,)).fetchall()
    holes = sorted({r["hole_id"] for r in rows})
    lines = sorted({r["line_code"] for r in rows})
    hole_index = {h: i for i, h in enumerate(holes)}
    line_index = {ln: i for i, ln in enumerate(lines)}
    X = np.array([[r["easting_m"], r["northing_m"], r["z_relative_m"]] for r in rows], dtype=np.float64)
    I = np.array([r["indicator"] for r in rows], dtype=np.int64)
    hole = np.array([hole_index[r["hole_id"]] for r in rows], dtype=np.int64)
    line = np.array([line_index[r["line_code"]] for r in rows], dtype=np.int64)
    n_per_hole = np.bincount(hole, minlength=len(holes)).astype(np.float64)
    return Observations(X=X, I=I, hole=hole, line=line, holes=holes, lines=lines, n_per_hole=n_per_hole,
                        upstream_ids=[r["upstream_interval_id"] for r in rows])


def compute(obs: Observations, spec: ExperimentSpec, allowed: np.ndarray | None = None) -> dict:
    """Experimental semivariogram for one spec. gamma is NaN in bins that are not supported."""
    acc = accumulate(obs.X, obs.I, obs.hole, obs.n_per_hole, spec.edges, within=spec.within,
                     horizontal=spec.horizontal, max_abs_dz=spec.max_abs_dz, azimuth_deg=spec.azimuth_deg,
                     tolerance_deg=spec.tolerance_deg, allowed=allowed)
    n = acc["n_pairs"]
    with np.errstate(divide="ignore", invalid="ignore"):
        if spec.weighting == "EQUAL_HOLE":
            gamma_raw = acc["sum_w_diff"] / (2.0 * acc["sum_w"])
        else:
            gamma_raw = acc["n_diff"] / (2.0 * n)
        equal_fraction = acc["n_equal"] / n
    supported = (n >= spec.min_pairs) & (acc["n_hole_pairs"] >= spec.min_hole_pairs) & (n > 0)
    gamma = np.where(supported, gamma_raw, np.nan)
    equal_fraction = np.where(n > 0, equal_fraction, np.nan)
    centres = 0.5 * (spec.edges[:-1] + spec.edges[1:])
    return {
        "spec": spec, "edges": spec.edges, "centres": centres, "n_pairs": n, "n_diff": acc["n_diff"],
        "n_equal": acc["n_equal"], "n_within": acc["n_within"], "n_between": acc["n_between"],
        "n_hole_pairs": acc["n_hole_pairs"], "gamma": gamma, "equal_fraction": equal_fraction,
        "supported": supported,
    }


def base_specs(config: dict) -> list[ExperimentSpec]:
    """The base experiments, built only from the predeclared configuration."""
    lat = config["lateral_between_hole"]
    omni3 = config["omnidirectional_3d_between_hole"]
    down = config["downhole_within_hole"]
    horiz = config["horizontal_azimuth_directions"]
    specs = [
        ExperimentSpec(name="LATERAL_BETWEEN", family="LATERAL_BETWEEN", within="EXCLUDED", horizontal=True,
                       edges=bin_edges(lat["lag_width_m"], lat["lag_max_m"]), lag_width_m=lat["lag_width_m"],
                       lag_max_m=lat["lag_max_m"], max_abs_dz=lat["max_abs_dz_m"], min_pairs=lat["min_pairs_per_bin"],
                       min_hole_pairs=lat["min_independent_hole_pairs_per_bin"]),
        ExperimentSpec(name="OMNI_3D_BETWEEN", family="OMNI_BETWEEN", within="EXCLUDED",
                       edges=bin_edges(omni3["lag_width_m"], omni3["lag_max_m"]), lag_width_m=omni3["lag_width_m"],
                       lag_max_m=omni3["lag_max_m"], min_pairs=omni3["min_pairs_per_bin"],
                       min_hole_pairs=omni3["min_independent_hole_pairs_per_bin"]),
        ExperimentSpec(name="DOWNHOLE_WITHIN", family="WITHIN_HOLE", within="ONLY",
                       edges=integer_lag_edges(int(down["lag_max_m"])), lag_width_m=down["lag_width_m"],
                       lag_max_m=down["lag_max_m"], min_pairs=down["min_pairs_per_bin"],
                       min_hole_pairs=down["min_independent_hole_pairs_per_bin"]),
    ]
    for az in horiz["azimuths_deg"]:
        specs.append(ExperimentSpec(
            name=f"LAT_AZ_{int(az):03d}", family="HORIZONTAL_AZIMUTH", within="EXCLUDED", horizontal=True,
            edges=bin_edges(horiz["lag_width_m"], horiz["lag_max_m"]), lag_width_m=horiz["lag_width_m"],
            lag_max_m=horiz["lag_max_m"], max_abs_dz=horiz["max_abs_dz_m"], azimuth_deg=float(az),
            tolerance_deg=horiz["angular_tolerance_deg"], min_pairs=horiz["min_pairs_per_bin"],
            min_hole_pairs=horiz["min_independent_hole_pairs_per_bin"]))
    return specs


def store(conn, run_id: int, receipt_id: int, result: dict, *, config_version: str, label_rule_id: str,
          created_utc: str) -> int:
    """Write one experiment and its lag bins. The direction must already exist in direction_registry."""
    spec: ExperimentSpec = result["spec"]
    cur = conn.execute(
        "INSERT INTO variogram_experiments (run_id, receipt_id, direction_id, variant, lag_width_m, lag_max_m, "
        "angular_tolerance_deg, within_hole_pairs, pair_weighting, min_pairs_per_bin, label_rule_id, config_version, "
        "status, created_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPUTED', ?)",
        (run_id, receipt_id, spec.name, spec.variant, spec.lag_width_m, spec.lag_max_m, spec.tolerance_deg,
         spec.within, spec.weighting, spec.min_pairs, label_rule_id, config_version, created_utc))
    experiment_id = cur.lastrowid
    for k, centre in enumerate(result["centres"]):
        g = result["gamma"][k]
        e = result["equal_fraction"][k]
        conn.execute(
            "INSERT INTO variogram_lag_bins (experiment_id, bin_index, lag_from_m, lag_to_m, lag_centre_m, n_pairs, "
            "n_independent_hole_pairs, gamma, equal_class_fraction, supported) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (experiment_id, k, float(result["edges"][k]), float(result["edges"][k + 1]), float(centre),
             int(result["n_pairs"][k]), int(result["n_hole_pairs"][k]),
             None if np.isnan(g) else float(g), None if np.isnan(e) else float(e),
             1 if result["supported"][k] else 0))
    return experiment_id


def store_diagnostics(conn, receipt_id: int, result: dict) -> None:
    """Pair-sampling diagnostics for a base experiment, one row per lag bin."""
    spec: ExperimentSpec = result["spec"]
    for k in range(len(result["centres"])):
        n = int(result["n_pairs"][k])
        conn.execute(
            "INSERT INTO pair_sampling_diagnostics (receipt_id, direction_id, lag_bin_index, lag_from_m, lag_to_m, "
            "n_pairs, n_equal_class, n_different_class, n_within_hole_pairs, n_between_hole_pairs, "
            "n_independent_hole_pairs, support_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (receipt_id, spec.name, k, float(result["edges"][k]), float(result["edges"][k + 1]), n,
             int(result["n_equal"][k]), int(result["n_diff"][k]), int(result["n_within"][k]),
             int(result["n_between"][k]), int(result["n_hole_pairs"][k]),
             "SUPPORTED" if result["supported"][k] else "SKIPPED"))

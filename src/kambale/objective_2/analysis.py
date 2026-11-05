"""Objective 2 analysis of one imported receipt (specification 06, sections 3.2 to 3.5).

Order of work: occurrence summaries; base experiments (the lateral between-hole family is the handoff basis; the
three-dimensional omnidirectional family is reported only; downhole within-hole; four horizontal azimuth classes);
fits, with leave-one-line-out refits of the lateral family; one-factor sensitivity variants; anisotropy comparison;
handoff decision.

Analysis rows are written once per receipt. A receipt that already has analysis rows is refused (STOP): earlier results
are never overwritten, and a new upstream version creates a new receipt.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from kambale.objective_2 import fitting, variogram
from kambale.objective_2.config import O2_CONFIG_PATH, O2_DB_PATH, StopError, code_commit, load_config, utc_now
from kambale.objective_2.db import connect_o2
from kambale.objective_2.handoff import BASE_FAMILY, decide
from kambale.objective_2.occurrence import summaries, support_statistics
from kambale.objective_2.pairs import bin_edges

FIT_MODELS = ("spherical", "exponential")
ANISOTROPY_PAIRS = (("LAT_AZ_000", "LAT_AZ_090"), ("LAT_AZ_045", "LAT_AZ_135"))
LOLO_VARIANT = "LEAVE_ONE_LINE_OUT"


def _receipt(conn, receipt_id: int | None) -> int:
    if receipt_id is None:
        row = conn.execute("SELECT receipt_id FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if row is None:
            raise StopError("no receipt: run the import first")
        receipt_id = row["receipt_id"]
    if conn.execute("SELECT COUNT(*) FROM variogram_experiments WHERE receipt_id = ?", (receipt_id,)).fetchone()[0]:
        raise StopError(f"analysis rows already exist for receipt {receipt_id}; a new upstream version is needed to re-run")
    return receipt_id


def _basis(family: str, config: dict) -> str:
    lat_dz = config["lateral_between_hole"]["max_abs_dz_m"]
    az_dz = config["horizontal_azimuth_directions"]["max_abs_dz_m"]
    return {
        "LATERAL_BETWEEN": f"between-hole pairs; horizontal lag; absolute relative-Z difference at most {lat_dz:g} m (handoff basis)",
        "OMNI_BETWEEN": "between-hole pairs; geometric three-dimensional lag (reported only; vertical separation included)",
        "WITHIN_HOLE": "same-hole pairs; along-hole lag (equal to the three-dimensional distance on a straight hole)",
        "HORIZONTAL_AZIMUTH": f"between-hole pairs; horizontal azimuth class; absolute relative-Z difference at most {az_dz:g} m (exploratory)",
    }[family]


def _min_bins(config: dict, spec) -> int:
    if spec.family == "LATERAL_BETWEEN":
        return config["lateral_between_hole"]["min_supported_bins_for_fit"]
    if spec.family == "OMNI_BETWEEN":
        return config["omnidirectional_3d_between_hole"]["min_supported_bins_for_fit"]
    if spec.family == "WITHIN_HOLE":
        return config["downhole_within_hole"]["min_supported_bins_for_fit"]
    return config["horizontal_azimuth_directions"]["min_supported_bins"]


def _not_assessed(reason: str) -> dict:
    return {"status": "NOT_ASSESSED", "reason": reason, "envelope": None}


def _write_summaries(conn, receipt_id: int, occ: dict, stats: list[dict]) -> None:
    for h in occ["holes"]:
        conn.execute(
            "INSERT INTO hole_occurrence_summaries (receipt_id, hole_id, line_code, n_intervals, logged_m, binary_n, "
            "positive_n, negative_n, ambiguous_n, unresolved_n, positive_apparent_m, graphitic_fraction_binary, "
            "n_distinct_intersections) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (receipt_id, h["hole_id"], h["line_code"], h["n"], h["logged_m"], h["binary_n"], h["positive_n"],
             h["negative_n"], h["ambiguous_n"], h["unresolved_n"], h["positive_m"], h["fraction"], h["intersections"]))
    for ln in occ["lines"]:
        conn.execute(
            "INSERT INTO line_occurrence_summaries (receipt_id, line_code, n_holes, n_intervals, logged_m, binary_n, "
            "positive_n, negative_n, ambiguous_n, unresolved_n, positive_apparent_m, graphitic_fraction_binary, "
            "n_distinct_intersections) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (receipt_id, ln["line_code"], ln["n_holes"], ln["n"], ln["logged_m"], ln["binary_n"], ln["positive_n"],
             ln["negative_n"], ln["ambiguous_n"], ln["unresolved_n"], ln["positive_m"], ln["fraction"],
             ln["intersections"]))
    for d in occ["depth"]:
        conn.execute(
            "INSERT INTO depth_lithology_summaries (receipt_id, depth_bin_from_m, depth_bin_to_m, rock_code_raw, binary_n, "
            "positive_n, prevalence) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (receipt_id, d["depth_bin_from_m"], d["depth_bin_to_m"], d["rock_code_raw"], d["binary_n"], d["positive_n"],
             d["prevalence"]))
    for w in occ["weathering"]:
        conn.execute("INSERT INTO weathering_cross_tabs (receipt_id, weathering_code, label_state, n_intervals) "
                     "VALUES (?, ?, ?, ?)", (receipt_id, w["weathering_code"], w["label_state"], w["n_intervals"]))
    for s in stats:
        conn.execute("INSERT INTO spatial_support_statistics (receipt_id, stat_group, stat_name, stat_value, unit, n_basis) "
                     "VALUES (?, ?, ?, ?, ?, ?)",
                     (receipt_id, s["stat_group"], s["stat_name"], s["stat_value"], s["unit"], s["n_basis"]))


def _direction_status(res: dict, min_bins: int) -> tuple[str, str]:
    n_supported = int(res["supported"].sum())
    if n_supported < min_bins:
        return "SKIPPED", f"{n_supported} supported bins; {min_bins} required"
    return "SUPPORTED", f"{n_supported} supported bins"


def _store_fit(conn, experiment_id: int, fit: dict, stab: dict, created: str) -> int:
    cur = conn.execute(
        "INSERT INTO variogram_fits (experiment_id, model, fit_status, weighting, objective_value, n_bins_used, admissible, "
        "marginal_departure, stability_status, reason, created_utc) VALUES (?, ?, ?, 'CRESSIE_N_OVER_GAMMA2', ?, ?, ?, ?, ?, ?, ?)",
        (experiment_id, fit["model"], fit["status"], fit.get("objective"), fit["n_bins"],
         None if fit.get("admissible") is None else int(fit["admissible"]), fit.get("marginal_departure"),
         stab["status"], f"{fit['reason']}; stability: {stab['reason']}", created))
    fit_id = cur.lastrowid
    if fit["status"] == "FITTED":
        names = ("nugget", "structured_sill", "range_m")
        units = ("indicator_variance", "indicator_variance", "m")
        env = stab.get("envelope") or {}
        for i, name in enumerate(names):
            lo, hi = (env.get(name) or (None, None))
            conn.execute(
                "INSERT INTO variogram_fit_parameters (fit_id, parameter, estimate, lower_bound, upper_bound, units, "
                "leave_one_line_min, leave_one_line_max) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (fit_id, name, float(fit["params"][i]), float(fit["lower_bounds"][i]), float(fit["upper_bounds"][i]),
                 units[i], lo, hi))
    return fit_id


def _fits_for(res: dict, p: float, config: dict) -> dict:
    """Both models fitted to one experiment. The range floor is the first supported lag centre."""
    spec = res["spec"]
    supported = res["supported"]
    a_min = float(res["centres"][supported][0]) if supported.any() else spec.lag_width_m
    mf = config["model_fitting"]
    return {model: fitting.fit(res["centres"], res["gamma"], res["n_pairs"], model, p, a_min=a_min,
                               a_max=spec.lag_max_m, min_bins=_min_bins(config, spec),
                               min_sill_fraction=mf["min_structured_sill_fraction"])
            for model in FIT_MODELS}


def _variant(spec, entry: dict):
    """The single-factor change named by a sensitivity entry."""
    factor, value = entry["factor"], entry["value"]
    if factor == "lag_width_m":
        width = float(value)
        return replace(spec, variant="SENSITIVITY", lag_width_m=width, edges=bin_edges(width, spec.lag_max_m))
    if factor == "angular_tolerance_deg":
        return replace(spec, variant="SENSITIVITY", tolerance_deg=float(value))
    if factor == "within_hole_pairs":
        return replace(spec, variant="SENSITIVITY", within=str(value))
    if factor == "pair_weighting":
        return replace(spec, variant="SENSITIVITY", weighting=str(value))
    if factor == "min_pairs_per_bin":
        return replace(spec, variant="SENSITIVITY", min_pairs=int(value))
    raise StopError(f"sensitivity factor {factor} has no variant definition")


def _lines_with_three_holes(obs) -> int:
    return sum(1 for li in range(len(obs.lines)) if np.unique(obs.hole[obs.line == li]).size >= 3)


def _write_base(conn, run_id: int, receipt_id: int, specs: dict, base: dict, config: dict, lines_with_3: int,
                created: str) -> dict:
    """Direction registry rows and base experiments. Returns the experiment id of each base direction."""
    for name, res in base.items():
        spec = specs[name]
        status, reason = _direction_status(res, _min_bins(config, spec))
        if spec.family == "HORIZONTAL_AZIMUTH" and lines_with_3 < config["horizontal_azimuth_directions"]["min_lines_with_holes"]:
            reason += f"; WARN: only {lines_with_3} lines carry three or more holes"
        azimuth = spec.azimuth_deg if spec.family == "HORIZONTAL_AZIMUTH" else None
        tolerance = spec.tolerance_deg if spec.family == "HORIZONTAL_AZIMUTH" else None
        conn.execute("INSERT INTO direction_registry (receipt_id, direction_id, family, azimuth_deg, angular_tolerance_deg, "
                     "geometry_basis, status, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (receipt_id, name, spec.family, azimuth, tolerance, _basis(spec.family, config), status, reason))
    base_ids = {}
    for name, res in base.items():
        base_ids[name] = variogram.store(conn, run_id, receipt_id, res, config_version=config["config_version"],
                                         label_rule_id=config["label_rule"]["id"], created_utc=created)
        variogram.store_diagnostics(conn, receipt_id, res)
    return base_ids


def _write_base_fits(conn, run_id: int, receipt_id: int, obs, p: float, specs: dict, base: dict, base_ids: dict,
                     config: dict, created: str):
    """Fits for every base experiment. The lateral family also gets one refit per left-out line, stored as sensitivity
    rows so that every stability result can be traced to the line removed."""
    low, high = config["model_fitting"]["stable_if_range_ratio_between"]
    fit_ids, fit_objects = {}, {}
    for name, res in base.items():
        spec = specs[name]
        fits = _fits_for(res, p, config)
        stabs = {m: _not_assessed("leave-one-line-out is applied to the lateral handoff basis only") for m in FIT_MODELS}
        loo_runs = []
        if name == BASE_FAMILY:
            for li in range(len(obs.lines)):
                loo_res = variogram.compute(obs, replace(spec, variant="SENSITIVITY"), allowed=obs.line != li)
                loo_runs.append((li, loo_res, _fits_for(loo_res, p, config)))
            for m in FIT_MODELS:
                stabs[m] = fitting.stability(fits[m], [loo_fits[m] for _, _, loo_fits in loo_runs], low=low, high=high)
        for m in FIT_MODELS:
            fit_ids[(name, m)] = _store_fit(conn, base_ids[name], fits[m], stabs[m], created)
            fit_objects[(name, m)] = fits[m]
        for li, loo_res, loo_fits in loo_runs:
            exp_id = variogram.store(conn, run_id, receipt_id, loo_res, config_version=config["config_version"],
                                     label_rule_id=config["label_rule"]["id"], created_utc=created)
            for m in FIT_MODELS:
                loo_fit_id = _store_fit(conn, exp_id, loo_fits[m], _not_assessed("leave-one-line-out refit"), created)
                conn.execute("INSERT INTO sensitivity_runs (run_id, base_experiment_id, variant_name, changed_factor, "
                             "changed_value, status, reason, experiment_id, fit_id) "
                             "VALUES (?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?)",
                             (run_id, base_ids[name], f"{LOLO_VARIANT}:{m}", "excluded_line", obs.lines[li],
                              f"{loo_fits[m]['status']}; {loo_fits[m]['reason']}", exp_id, loo_fit_id))
    return fit_ids, fit_objects


def _write_sensitivity(conn, run_id: int, receipt_id: int, obs, p: float, specs: dict, base_ids: dict, config: dict,
                       created: str) -> None:
    for entry in config["sensitivity"]:
        name, factor, value = entry["name"], entry["factor"], str(entry["value"])
        if entry.get("status_if_run"):
            conn.execute("INSERT INTO sensitivity_runs (run_id, base_experiment_id, variant_name, changed_factor, "
                         "changed_value, status, reason) VALUES (?, ?, ?, ?, ?, 'SKIPPED', ?)",
                         (run_id, base_ids.get(entry["applies_to"]), name, factor, value,
                          f"{entry['status_if_run']}: not run"))
            continue
        targets = [s for s in specs.values() if entry["applies_to"] in (s.name, s.family)]
        if not targets:
            raise StopError(f"sensitivity entry {name} applies to no base direction")
        for target in targets:
            spec = _variant(target, entry)
            res = variogram.compute(obs, spec)
            exp_id = variogram.store(conn, run_id, receipt_id, res, config_version=config["config_version"],
                                     label_rule_id=config["label_rule"]["id"], created_utc=created)
            fits = _fits_for(res, p, config)
            fit_ids = {m: _store_fit(conn, exp_id, fits[m], _not_assessed("sensitivity fit: stability not tested"), created)
                       for m in FIT_MODELS}
            fitted = [m for m in FIT_MODELS if fits[m]["status"] == "FITTED"]
            best = min(fitted, key=lambda m: fits[m]["objective"]) if fitted else None
            reason = (f"{int(res['supported'].sum())} supported bins; "
                      + "; ".join(f"{m} {fits[m]['status']}" for m in FIT_MODELS))
            conn.execute("INSERT INTO sensitivity_runs (run_id, base_experiment_id, variant_name, changed_factor, "
                         "changed_value, status, reason, experiment_id, fit_id) VALUES (?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?)",
                         (run_id, base_ids[target.name], name, factor, value, reason, exp_id,
                          fit_ids[best] if best else None))


def _write_anisotropy(conn, receipt_id: int, fit_objects: dict) -> None:
    """Range comparison between opposite azimuth classes. Azimuth fits are not leave-one-line-out tested, so the
    decision is NOT_EVALUATED whatever the ratio; anisotropy is never claimed at this stage."""
    for a, b in ANISOTROPY_PAIRS:
        ranges = {}
        for d in (a, b):
            fitted = [(fit_objects[(d, m)]["objective"], fit_objects[(d, m)]["params"][2])
                      for m in FIT_MODELS if fit_objects[(d, m)]["status"] == "FITTED"]
            ranges[d] = min(fitted)[1] if fitted else None
        ra, rb = ranges[a], ranges[b]
        if ra is None or rb is None:
            conn.execute("INSERT INTO anisotropy_diagnostics (receipt_id, direction_a, direction_b, range_a_m, range_b_m, "
                         "range_ratio, support_status, decision, reason) VALUES (?, ?, ?, ?, ?, NULL, 'SKIPPED', "
                         "'NOT_EVALUATED', 'no FITTED model in one direction')", (receipt_id, a, b, ra, rb))
        else:
            ratio = max(ra, rb) / min(ra, rb)
            conn.execute("INSERT INTO anisotropy_diagnostics (receipt_id, direction_a, direction_b, range_a_m, range_b_m, "
                         "range_ratio, support_status, decision, reason) VALUES (?, ?, ?, ?, ?, ?, 'SUPPORTED', "
                         "'NOT_EVALUATED', ?)",
                         (receipt_id, a, b, ra, rb, ratio,
                          f"range ratio {ratio:.2f} reported; azimuth fits are not leave-one-line-out tested, "
                          "so anisotropy is not evaluated"))


def run(receipt_id: int | None = None, o2_path=O2_DB_PATH, config_path=O2_CONFIG_PATH) -> dict:
    config, config_sha = load_config(config_path)
    conn = connect_o2(o2_path)
    conn.execute("BEGIN IMMEDIATE")
    try:
        receipt_id = _receipt(conn, receipt_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    run_id = conn.execute("INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, started_utc, status, "
                          "code_commit, note) VALUES ('ANALYSE', ?, ?, ?, ?, 'RUNNING', ?, ?)",
                          (config["config_version"], config_sha, receipt_id, utc_now(), code_commit(),
                           "lateral between-hole basis; three-dimensional omnidirectional reported; downhole; azimuth; "
                           "leave-one-line-out; sensitivity")).lastrowid
    created = utc_now()
    try:
        conn.execute("BEGIN IMMEDIATE")
        occ = summaries(conn, receipt_id)
        _write_summaries(conn, receipt_id, occ, support_statistics(conn, receipt_id))
        conn.execute("COMMIT")

        obs = variogram.load_observations(conn, receipt_id)
        p = obs.p
        specs = {s.name: s for s in variogram.base_specs(config)}
        base = {name: variogram.compute(obs, spec) for name, spec in specs.items()}

        conn.execute("BEGIN IMMEDIATE")
        base_ids = _write_base(conn, run_id, receipt_id, specs, base, config, _lines_with_three_holes(obs), created)
        conn.execute("COMMIT")

        conn.execute("BEGIN IMMEDIATE")
        fit_ids, fit_objects = _write_base_fits(conn, run_id, receipt_id, obs, p, specs, base, base_ids, config, created)
        conn.execute("COMMIT")

        conn.execute("BEGIN IMMEDIATE")
        _write_sensitivity(conn, run_id, receipt_id, obs, p, specs, base_ids, config, created)
        _write_anisotropy(conn, receipt_id, fit_objects)
        decision = decide(conn, receipt_id, fit_ids, base_ids, obs, p, config, created)
        conn.execute("COMMIT")
        conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ? WHERE run_id = ?", (utc_now(), run_id))
    except Exception as exc:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        conn.execute("UPDATE stage_runs SET status = 'FAILED', finished_utc = ?, note = ? WHERE run_id = ?",
                     (utc_now(), str(exc)[:500], run_id))
        raise
    finally:
        conn.close()
    return {"run_id": run_id, "receipt_id": receipt_id, "p_binary": p, "binary_n": int(obs.I.size),
            "decision": decision, "config_version": config["config_version"]}

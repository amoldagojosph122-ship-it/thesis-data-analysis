"""Configuration 3: exploratory lateral extension and the STRICT_SGS_v1 label comparator (specification 06, section 3.7).

The predeclared file config/objective_2/extension_config_O2-CFG-2026.11.05-3.yaml defines the run. It adds sensitivity
rows to the Objective 2 database under its own stage run, and it never writes a handoff row. The extension uses the
configuration-2 pair, support, identifiability and stability rules unchanged. The STRICT comparator labels are copied
from the Objective 1 database for the active dataset version and used only on the DESIGN binary intervals.
"""

from __future__ import annotations

import dataclasses

import numpy as np

from kambale.config import CONFIG_DIR
from kambale.objective_2 import fitting, variogram
from kambale.objective_2.analysis import _fits_for, _store_fit
from kambale.objective_2.config import (O2_CONFIG_PATH, O2_DB_PATH, UPSTREAM_DB_PATH, StopError, code_commit, load_config,
                                        utc_now)
from kambale.objective_2.db import connect_o2, connect_upstream_readonly
from kambale.objective_2.pairs import bin_edges

EXT_CONFIG_PATH = CONFIG_DIR / "objective_2" / "extension_config_O2-CFG-2026.11.05-3.yaml"
COMPARATOR = "STRICT_SGS_v1"
DESIGN = "DESIGN_8_2_v1"
FIT_MODELS = ("spherical", "exponential")
LOO = "LEAVE_ONE_LINE_OUT"


def _not_assessed(reason: str) -> dict:
    return {"status": "NOT_ASSESSED", "reason": reason, "envelope": None}


def _import_comparator(conn, receipt_id: int) -> int:
    """Copy the comparator label of every interval from the Objective 1 database. Runs once per receipt."""
    have = conn.execute("SELECT COUNT(*) FROM comparator_observations WHERE receipt_id = ? AND rule_id = ?",
                        (receipt_id, COMPARATOR)).fetchone()[0]
    if have:
        return have
    up = connect_upstream_readonly(UPSTREAM_DB_PATH)
    try:
        labels = up.execute("SELECT interval_id, label_state FROM v_label_candidates WHERE rule_id = ?",
                            (COMPARATOR,)).fetchall()
    finally:
        up.close()
    if not labels:
        raise StopError(f"no {COMPARATOR} labels in the Objective 1 database")
    for interval_id, state in labels:
        binary = state in ("POSITIVE", "NEGATIVE")
        indicator = (1 if state == "POSITIVE" else 0) if binary else None
        conn.execute("INSERT INTO comparator_observations (receipt_id, upstream_interval_id, rule_id, label_state, "
                     "in_binary_target, indicator) VALUES (?, ?, ?, ?, ?, ?)",
                     (receipt_id, interval_id, COMPARATOR, state, int(binary), indicator))
    return len(labels)


def _comparator_indicator(conn, receipt_id: int, upstream_ids: list[int]) -> np.ndarray:
    """Comparator indicator of the DESIGN binary intervals, in the order of the analysis observations."""
    lookup = {r[0]: r[1] for r in conn.execute(
        "SELECT upstream_interval_id, indicator FROM comparator_observations WHERE receipt_id = ? AND rule_id = ? "
        "AND in_binary_target = 1", (receipt_id, COMPARATOR)).fetchall()}
    missing = [i for i in upstream_ids if i not in lookup]
    if missing:
        raise StopError(f"{len(missing)} DESIGN intervals have no binary {COMPARATOR} label")
    return np.array([lookup[i] for i in upstream_ids], dtype=np.int64)


def _experiment_with_fits(conn, run_id: int, receipt_id: int, obs, spec, cfg: dict, label_rule: str, created: str,
                          *, loo: bool, base_experiment_id: int) -> dict:
    """Store one experiment, its two fits and, when requested, the leave-one-line-out refits of every line."""
    res = variogram.compute(obs, spec)
    exp_id = variogram.store(conn, run_id, receipt_id, res, config_version=cfg["config_version"],
                             label_rule_id=label_rule, created_utc=created)
    fits = _fits_for(res, obs.p, cfg)
    stabs = {m: _not_assessed("leave-one-line-out not run for this comparison") for m in FIT_MODELS}
    loo_runs = []
    if loo:
        for li in range(len(obs.lines)):
            loo_res = variogram.compute(obs, spec, allowed=obs.line != li)
            loo_runs.append((li, loo_res, _fits_for(loo_res, obs.p, cfg)))
        low, high = cfg["model_fitting"]["stable_if_range_ratio_between"]
        for m in FIT_MODELS:
            stabs[m] = fitting.stability(fits[m], [f[m] for _, _, f in loo_runs], low=low, high=high)
    fit_ids = {m: _store_fit(conn, exp_id, fits[m], stabs[m], created) for m in FIT_MODELS}
    for li, loo_res, loo_fits in loo_runs:
        loo_exp = variogram.store(conn, run_id, receipt_id, loo_res, config_version=cfg["config_version"],
                                  label_rule_id=label_rule, created_utc=created)
        for m in FIT_MODELS:
            loo_fit = _store_fit(conn, loo_exp, loo_fits[m], _not_assessed("leave-one-line-out refit"), created)
            conn.execute("INSERT INTO sensitivity_runs (run_id, base_experiment_id, variant_name, changed_factor, "
                         "changed_value, status, reason, experiment_id, fit_id) "
                         "VALUES (?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?)",
                         (run_id, exp_id, f"{LOO}:{m}", "excluded_line", obs.lines[li],
                          f"{loo_fits[m]['status']}; {loo_fits[m]['reason']}", loo_exp, loo_fit))
    best = min((m for m in FIT_MODELS if fits[m]["status"] == "FITTED"), key=lambda m: fits[m]["objective"], default=None)
    supported = int(res["supported"].sum())
    reason = f"{supported} supported bins; " + "; ".join(
        f"{m} {fits[m]['status']}, stability {stabs[m]['status']}" for m in FIT_MODELS)
    conn.execute("INSERT INTO sensitivity_runs (run_id, base_experiment_id, variant_name, changed_factor, changed_value, "
                 "status, reason, experiment_id, fit_id) VALUES (?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?)",
                 (run_id, base_experiment_id, f"{label_rule}:LATERAL_{int(spec.lag_max_m)}M", "lag_width_m;lag_max_m",
                  f"{spec.lag_width_m:g};{spec.lag_max_m:g}", reason, exp_id, fit_ids[best] if best else None))
    stable = [m for m in FIT_MODELS if fits[m]["status"] == "FITTED" and stabs[m]["status"] == "STABLE"]
    return {"exp_id": exp_id, "fits": fits, "stabs": stabs, "stable": stable, "supported": supported}


def run(o2_path=O2_DB_PATH, config_path=EXT_CONFIG_PATH, base_config_path=O2_CONFIG_PATH) -> dict:
    cfg, cfg_sha = load_config(config_path)
    base_cfg, _ = load_config(base_config_path)
    conn = connect_o2(o2_path)
    try:
        rid = conn.execute("SELECT MAX(receipt_id) FROM source_receipts").fetchone()[0]
        if rid is None:
            raise StopError("no receipt: run the import first")
        if conn.execute("SELECT COUNT(*) FROM variogram_experiments WHERE receipt_id = ? AND config_version = ?",
                        (rid, cfg["config_version"])).fetchone()[0]:
            raise StopError(f"configuration {cfg['config_version']} has already run on receipt {rid}")
        base_exp = conn.execute("SELECT experiment_id FROM variogram_experiments WHERE receipt_id = ? AND variant = 'BASE' "
                                "AND direction_id = 'LATERAL_BETWEEN' ORDER BY experiment_id DESC LIMIT 1", (rid,)).fetchone()[0]
        conn.execute("BEGIN IMMEDIATE")
        try:
            n_labels = _import_comparator(conn, rid)
            run_id = conn.execute("INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, started_utc, "
                                  "status, code_commit, note) VALUES ('SENSITIVITY', ?, ?, ?, ?, 'RUNNING', ?, ?)",
                                  (cfg["config_version"], cfg_sha, rid, utc_now(), code_commit(),
                                   "configuration 3: lateral extension and STRICT comparator (exploratory)")).lastrowid
            created = utc_now()
            obs = variogram.load_observations(conn, rid)
            strict_obs = dataclasses.replace(obs, I=_comparator_indicator(conn, rid, obs.upstream_ids))
            lat = cfg["lateral_between_hole"]
            ext_spec = variogram.ExperimentSpec(
                name="LATERAL_BETWEEN", family="LATERAL_BETWEEN", within="EXCLUDED", horizontal=True,
                edges=bin_edges(lat["lag_width_m"], lat["lag_max_m"]), lag_width_m=lat["lag_width_m"],
                lag_max_m=lat["lag_max_m"], max_abs_dz=lat["max_abs_dz_m"], min_pairs=lat["min_pairs_per_bin"],
                min_hole_pairs=lat["min_independent_hole_pairs_per_bin"], variant="SENSITIVITY")
            v2_spec = dataclasses.replace(next(s for s in variogram.base_specs(base_cfg) if s.name == "LATERAL_BETWEEN"),
                                          variant="SENSITIVITY")
            ext = _experiment_with_fits(conn, run_id, rid, obs, ext_spec, cfg, DESIGN, created, loo=True,
                                        base_experiment_id=base_exp)
            for spec in (v2_spec, ext_spec):
                _experiment_with_fits(conn, run_id, rid, strict_obs, spec, cfg, COMPARATOR, created, loo=False,
                                      base_experiment_id=base_exp)
            decision = "PROVISIONAL (extension)" if ext["stable"] else "NOT_IDENTIFIABLE (extension)"
            conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ?, note = ? WHERE run_id = ?",
                         (utc_now(), f"configuration 3: lateral extension and STRICT comparator (exploratory); extension "
                                     f"decision: {decision}; STRICT labels imported: {n_labels}", run_id))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return {"run_id": run_id, "receipt_id": rid, "config_version": cfg["config_version"], "config_sha256": cfg_sha,
            "decision": decision, "design_p": obs.p, "strict_p": strict_obs.p, "comparator_labels_imported": n_labels}

"""Handoff decision for Objective 3 (specification 02, section 11). The rule is fixed here, not chosen per result.

The basis is the lateral base family (horizontal lag, similar depth). The three-dimensional family is reported only.
- A stable, FITTED, admissible lateral model gives PROVISIONAL, with its search ranges and leave-one-line-out envelope.
  Full-data parameters are never supplied for test folds.
- An inadmissible lateral fit, with no stable FITTED alternative, gives REJECTED.
- Otherwise, with no stable FITTED lateral model, the result is NOT_IDENTIFIABLE.
APPROVED is not produced in this stage.
"""

from __future__ import annotations

import json

BASE_FAMILY = "LATERAL_BETWEEN"


def _clause(reason: str) -> str:
    """The identifiability part of a fit reason, without the stability text the analysis appends to it."""
    return reason.split("; stability:")[0]


def decide(conn, receipt_id: int, fits: dict, base_ids: dict, obs, p: float, config: dict, created_utc: str) -> dict:
    fitted, described, rejected = [], [], False
    for model in ("spherical", "exponential"):
        fit_id = fits.get((BASE_FAMILY, model))
        if fit_id is None:
            continue
        row = conn.execute("SELECT fit_status, stability_status, objective_value, reason FROM variogram_fits WHERE fit_id = ?",
                           (fit_id,)).fetchone()
        described.append(f"{model} {row['fit_status']} ({_clause(row['reason'])})")
        if row["fit_status"] == "INADMISSIBLE":
            rejected = True
        if row["fit_status"] == "FITTED":
            fitted.append((model, fit_id, row["stability_status"], row["objective_value"]))
    stable = [f for f in fitted if f[2] == "STABLE"]
    if stable:
        family, fit_id, _, _ = min(stable, key=lambda f: f[3])
        status = "PROVISIONAL"
        rationale = ("Exploratory result on the lateral base family (horizontal lag, relative-Z difference at most "
                     "3 m), fitted on all holes. Relative geometry only (no surveyed RL); one orientation for all holes; "
                     "leave-one-line-out stable. Objective 3 must refit or select the variogram inside every outer "
                     "training fold. The all-data parameters are not a leakage-free estimate and are not supplied for "
                     "test folds.")
    elif rejected:
        family, fit_id, status = None, None, "REJECTED"
        rationale = (f"A lateral fit is inadmissible and no lateral model is stable: {'; '.join(described)}. "
                     "No handoff parameters are supplied.")
    else:
        family, fit_id, status = None, None, "NOT_IDENTIFIABLE"
        rationale = (f"No lateral model is both FITTED and stable under leave-one-line-out: {'; '.join(described)}. "
                     "Lateral continuity is not identified at this support. Objective 3 must not use a between-hole "
                     "continuity model whose parameters come from these fits; models without a geostatistical "
                     "continuity term may proceed without a continuity claim.")
    search = {}
    if fit_id is not None:
        params = conn.execute("SELECT parameter, lower_bound, upper_bound, leave_one_line_min, leave_one_line_max "
                              "FROM variogram_fit_parameters WHERE fit_id = ?", (fit_id,)).fetchall()
        search = {r["parameter"]: {"bounds": [r["lower_bound"], r["upper_bound"]],
                                   "leave_one_line_envelope": [r["leave_one_line_min"], r["leave_one_line_max"]]}
                  for r in params}
    lat = config["lateral_between_hole"]
    lags = {"family": BASE_FAMILY, "lag_width_m": lat["lag_width_m"], "lag_max_m": lat["lag_max_m"],
            "max_abs_dz_m": lat["max_abs_dz_m"], "min_pairs_per_bin": lat["min_pairs_per_bin"],
            "min_independent_hole_pairs_per_bin": lat["min_independent_hole_pairs_per_bin"]}
    conn.execute("INSERT INTO continuity_handoff_decisions (receipt_id, fit_id, decision_status, candidate_family, "
                 "parameter_search_json, lag_setting_json, full_data_parameters_for_test_folds, rationale, created_utc) "
                 "VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)",
                 (receipt_id, fit_id, status, family or "NONE", json.dumps(search, sort_keys=True),
                  json.dumps(lags, sort_keys=True), rationale, created_utc))
    return {"status": status, "candidate_family": family, "fit_id": fit_id}

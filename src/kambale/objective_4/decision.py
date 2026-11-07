"""Predeclared model-comparison decision and the locked Objective 5 handoff, per evaluation tier.

Eligible models are the DISTINCT feasible models with FULL coverage and a defined pooled interval Brier score. The lowest
is selected; the next lowest is the comparator. Any model identical to an earlier feasible model is reported as
NOT_COMPARABLE with its identity, never ranked. The improvement rule is applied exactly as predeclared in the config.
"""

from __future__ import annotations

import json

import numpy as np

from kambale.objective_4.config import StopError, sha256_text

TIER_TEXT = {
    "TIER_1_EXTRAPOLATION": {
        "domain": ("held-out intervals of a whole undrilled drill line predicted from the other drill lines; relative "
                   "geometry only; not a distant prospect beyond the sampled lines and not an absolute-elevation volume"),
        "caveat": ("Internal spatially held-out validation on five drill lines: extrapolation to an unseen line, not an "
                   "external prospective campaign."),
    },
    "TIER_2_INTERPOLATION": {
        "domain": ("held-out intervals inside drilled holes of an approved line, predicted from neighbouring holes at about "
                   "one hole spacing; relative geometry only; not a different line, not a distant prospect and not an "
                   "absolute-elevation volume"),
        "caveat": ("Internal spatially held-out validation between drilled holes: interpolation at one hole spacing, not an "
                   "external prospective campaign."),
    },
}


def improvement_status(point, lo, hi, folds_better, fold_min, calibration_ok, discrimination_ok, coverage_ok):
    """Predeclared rule for the selected model against its comparator; the difference is selected minus comparator.

    Returns (status, reason). SUPPORTED_IMPROVEMENT needs every condition. NO_IMPROVEMENT when the point estimate is
    non-negative or the interval lies above zero. INCONCLUSIVE otherwise (interval includes zero, fold consistency below
    the minimum, or a secondary criterion fails), with the failed criteria named.
    """
    if point is None or lo is None or hi is None:
        return "INCONCLUSIVE", "no hole-cluster bootstrap interval for the selected pair"
    if point >= 0:
        return "NO_IMPROVEMENT", "point estimate non-negative"
    failed = []
    if not hi < 0:
        failed.append("interval includes zero")
    if folds_better < fold_min:
        failed.append(f"selected better in {folds_better} of 5 folds (minimum {fold_min})")
    if not calibration_ok:
        failed.append("calibration slope or intercept outside the acceptable range")
    if not discrimination_ok:
        failed.append("ROC-AUC worse than the comparator by more than the margin")
    if not coverage_ok:
        failed.append("coverage below the threshold")
    if not failed:
        return "SUPPORTED_IMPROVEMENT", "every predeclared condition is met"
    if lo > 0:
        return "NO_IMPROVEMENT", "interval entirely above zero"
    return "INCONCLUSIVE", "; ".join(failed)


def comparator_status(lo, hi):
    """Status of a non-selected eligible model against the selected model (difference is model minus selected)."""
    if lo is None or hi is None:
        return "INCONCLUSIVE", "no hole-cluster bootstrap interval"
    if lo > 0:
        return "NO_IMPROVEMENT", "resolved: the selected model has the lower Brier (interval above zero)"
    return "INCONCLUSIVE", "unresolved: the interval includes zero"


def _metric(conn, model, metric_id, weighting="INTERVAL"):
    row = conn.execute("SELECT value, status, n, n_positive FROM pooled_metrics WHERE model_id = ? AND weighting = ? "
                       "AND metric_id = ?", (model, weighting, metric_id)).fetchone()
    return dict(row) if row else {"value": None, "status": "NOT_ESTIMABLE", "n": 0, "n_positive": 0}


def _fold_brier(conn, model, fold):
    row = conn.execute("SELECT value FROM fold_metrics WHERE model_id = ? AND fold_id = ? AND weighting = 'INTERVAL' "
                       "AND metric_id = 'BRIER'", (model, fold)).fetchone()
    return row["value"] if row else None


def _brier_interval(conn, config, a, b):
    """Point difference and hole-cluster interval for Brier(b) minus Brier(a), from the stored replicates."""
    va, vb = _metric(conn, a, "BRIER")["value"], _metric(conn, b, "BRIER")["value"]
    point = (vb - va) if va is not None and vb is not None else None
    rows = conn.execute("SELECT model_a, model_b, delta_brier_interval FROM bootstrap_replicates "
                        "WHERE design_id = 'O4-BOOT-HOLE' AND ((model_a = ? AND model_b = ?) OR "
                        "(model_a = ? AND model_b = ?))", (a, b, b, a)).fetchall()
    if not rows:
        return point, None, None
    # Stored replicates are Brier(stored b) minus Brier(stored a); flip the sign when the stored order is reversed.
    sign = 1.0 if rows[0]["model_a"] == a else -1.0
    deltas = np.array([sign * r["delta_brier_interval"] for r in rows], dtype=float)
    lo = (1.0 - float(config["evaluation"]["bootstrap"]["confidence"])) / 2.0 * 100.0
    return point, float(np.percentile(deltas, lo)), float(np.percentile(deltas, 100.0 - lo))


def _calibration(conn, config, model):
    row = conn.execute("SELECT intercept, slope, status FROM calibration_diagnostics WHERE model_id = ?",
                       (model,)).fetchone()
    if row is None or row["status"] != "DEFINED" or row["slope"] is None or row["intercept"] is None:
        return "UNDEFINED", False
    lo, hi = config["evaluation"]["calibration_slope_acceptable"]
    ok = (lo <= row["slope"] <= hi) and abs(row["intercept"]) <= float(
        config["evaluation"]["calibration_intercept_abs_max"])
    return ("ACCEPTABLE" if ok else "NOT_ACCEPTABLE"), ok


def _discrimination(conn, config, model, other):
    a = _metric(conn, model, "ROC_AUC")
    b = _metric(conn, other, "ROC_AUC")
    if a["status"] != "DEFINED" or b["status"] != "DEFINED":
        return "UNDEFINED", False
    margin = float(config["evaluation"]["discrimination_margin_auc"])
    ok = a["value"] >= b["value"] - margin
    return ("NOT_WORSE" if ok else "WORSE"), ok


def _fmt(value, digits=6):
    return "n/a" if value is None else f"{value:.{digits}f}"


def write(conn, config, receipt, created):
    ev = config["evaluation"]
    feasible = list(ev["models"]["feasible"])
    threshold = float(ev["coverage_threshold"])
    fold_min = int(ev["fold_consistency_min"])
    tier = config["tier"]
    if receipt["o3_split_plan_id"] != config["paths"]["o3_split_plan_id"]:
        raise StopError(f"receipt split plan {receipt['o3_split_plan_id']} differs from the config split plan "
                        f"{config['paths']['o3_split_plan_id']}")
    reg = {r["model_id"]: dict(r) for r in conn.execute("SELECT * FROM candidate_registry")}
    cov = {r["model_id"]: dict(r) for r in conn.execute("SELECT * FROM prediction_coverage")}
    brier = {m: _metric(conn, m, "BRIER") for m in reg}
    eligible = [m for m in feasible if m in reg and reg[m]["identity_status"] == "DISTINCT"
                and cov[m]["status"] == "FULL" and brier[m]["status"] == "DEFINED" and brier[m]["value"] is not None]
    if len(eligible) < 2:
        raise RuntimeError("fewer than two distinct full-coverage feasible models have a defined Brier score")
    ranked = sorted(eligible, key=lambda m: (brier[m]["value"], m))
    selected, comparator = ranked[0], ranked[1]
    sel_brier_fold_better = None

    order = ranked + [m for m in feasible if m in reg and m not in ranked] + sorted(m for m in reg if m not in feasible)
    rows = []
    for m in order:
        r = reg[m]
        cal_status, cal_ok = _calibration(conn, config, m)
        coverage = float(cov[m]["coverage"]) if m in cov else 0.0
        if m not in ranked:
            if r["identity_status"] == "IDENTICAL_TO":
                reason = f"identical to {r['identical_to']} on every common observation; reported, not ranked"
                disc = f"IDENTICAL_TO_{r['identical_to']}"
            elif m not in feasible:
                reason = "not in the predeclared feasible set; reported only"
                disc = "UNDEFINED"
            elif cov[m]["status"] != "FULL" or coverage < threshold:
                reason = f"coverage {coverage:.3f} ({cov[m]['status']}) is not full coverage"
                disc = "UNDEFINED"
            else:
                reason = "no defined pooled Brier score"
                disc = "UNDEFINED"
            rows.append((m, "NOT_COMPARABLE", None, "NOT_COMPARABLE", "NOT_RANKED", None, None, None, None, cal_status,
                         disc, coverage, reason))
            continue
        rank = ranked.index(m) + 1
        if m == selected:
            role = "SELECTED"
            point, lo, hi = _brier_interval(conn, config, comparator, selected)
            folds_better = sum(1 for f in range(1, 6) if _fold_brier(conn, selected, f) is not None and
                               _fold_brier(conn, comparator, f) is not None and
                               _fold_brier(conn, selected, f) < _fold_brier(conn, comparator, f))
            sel_brier_fold_better = folds_better
            disc_status, disc_ok = _discrimination(conn, config, selected, comparator)
            status, why = improvement_status(point, lo, hi, folds_better, fold_min, cal_ok, disc_ok,
                                             coverage >= threshold)
            basis = "SUPPORTED" if status == "SUPPORTED_IMPROVEMENT" else "POINT_ESTIMATE_WITH_CAVEAT"
            reason = (f"lowest pooled interval Brier among distinct full-coverage models; against comparator "
                      f"{comparator}: delta Brier (selected minus comparator) {_fmt(point)}, 95% hole-cluster interval "
                      f"[{_fmt(lo)}, {_fmt(hi)}], selected better in {folds_better} of 5 folds; calibration "
                      f"{cal_status}; discrimination {disc_status}; {why}")
            rows.append((m, role, rank, status, basis, point, lo, hi, folds_better, cal_status, disc_status, coverage,
                         reason))
            continue
        role = "COMPARATOR" if m == comparator else "REJECTED"
        point, lo, hi = _brier_interval(conn, config, selected, m)
        status, why = comparator_status(lo, hi)
        disc_status, _ = _discrimination(conn, config, m, selected)
        reason = (f"vs selected {selected}: delta Brier (model minus selected) {_fmt(point)}, 95% hole-cluster interval "
                  f"[{_fmt(lo)}, {_fmt(hi)}]; {why}")
        rows.append((m, role, rank, status, "NOT_SELECTED", point, lo, hi, None, cal_status, disc_status, coverage,
                     reason))

    for r in rows:
        conn.execute("INSERT INTO comparison_decisions (model_id, role, rank, improvement_status, selection_basis, "
                     "delta_brier, ci_low, ci_high, fold_consistency, calibration_status, discrimination_status, coverage, "
                     "reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", r)
    selected_row = conn.execute("SELECT decision_id, improvement_status FROM comparison_decisions WHERE model_id = ? AND "
                                "role = 'SELECTED'", (selected,)).fetchone()
    text = TIER_TEXT[tier]
    m3 = reg.get("M3_HYBRID")
    if m3 is None:
        hybrid_note = ""
    elif m3["identity_status"] == "IDENTICAL_TO":
        hybrid_note = (f" M3_HYBRID is identical to {m3['identical_to']} on every common observation, so its residual "
                       "kriging adds no skill in this evaluation; no hybrid advantage is claimed.")
    else:
        hybrid_note = " M3_HYBRID is distinct from its trend component on the common cohort."
    handoff = {
        "tier": tier,
        "config_version": config["config_version"],
        "claim": config["claim"].strip(),
        "selected_model_id": selected,
        "decision_id": selected_row["decision_id"],
        "target_receipt_id": receipt["receipt_id"],
        "split_plan_id": receipt["o3_split_plan_id"],
        "split_plan_sha256": receipt["o3_split_plan_sha256"],
        "metric_reference": "pooled interval-weighted Brier is the primary endpoint; see the tier's O4-T01, O4-T02 and "
                            "O4-T05 tables",
        "calibration_policy": "Objective 3 calibration only; Objective 4 diagnostics are not applied",
        "allowed_domain": text["domain"],
        "caveats": text["caveat"] + " Only easting, northing and relative Z are predictors. No grade, tonnage or "
                   "resource is estimated." + hybrid_note,
        "created_utc": created,
    }
    handoff_sha = sha256_text(json.dumps(handoff, sort_keys=True, separators=(",", ":")))
    conn.execute("INSERT INTO locked_handoff_receipts (tier, config_version, claim, selected_model_id, decision_id, "
                 "target_receipt_id, split_plan_id, split_plan_sha256, metric_reference, calibration_policy, "
                 "allowed_domain, caveats, created_utc, receipt_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (handoff["tier"], handoff["config_version"], handoff["claim"], handoff["selected_model_id"],
                  handoff["decision_id"], handoff["target_receipt_id"], handoff["split_plan_id"],
                  handoff["split_plan_sha256"], handoff["metric_reference"], handoff["calibration_policy"],
                  handoff["allowed_domain"], handoff["caveats"], handoff["created_utc"], handoff_sha))
    return {"selected_model_id": selected, "comparator": comparator, "ranked": ranked,
            "brier": {m: brier[m]["value"] for m in ranked}, "status": selected_row["improvement_status"],
            "folds_better": sel_brier_fold_better, "handoff_sha256": handoff_sha}

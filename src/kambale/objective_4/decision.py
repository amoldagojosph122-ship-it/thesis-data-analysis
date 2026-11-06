"""Predeclared model-comparison decision and the locked Objective 5 handoff."""

from __future__ import annotations

import json

import numpy as np

from kambale.objective_4.config import sha256_text, utc_now


def _metric(conn, model, metric_id, weighting="INTERVAL"):
    row = conn.execute("SELECT value, status, n, n_positive FROM pooled_metrics WHERE model_id = ? AND weighting = ? "
                       "AND metric_id = ?", (model, weighting, metric_id)).fetchone()
    return dict(row) if row else {"value": None, "status": "NOT_ESTIMABLE", "n": 0, "n_positive": 0}


def _fold_brier(conn, model, fold):
    row = conn.execute("SELECT value FROM fold_metrics WHERE model_id = ? AND fold_id = ? AND weighting = 'INTERVAL' "
                       "AND metric_id = 'BRIER'", (model, fold)).fetchone()
    return row["value"] if row else None


def _ci(conn, config, selected, comparator):
    rows = conn.execute("SELECT model_a, model_b, delta_brier_interval FROM bootstrap_replicates "
                        "WHERE design_id = 'O4-BOOT-HOLE' AND ((model_a = ? AND model_b = ?) OR "
                        "(model_a = ? AND model_b = ?))", (selected, comparator, comparator, selected)).fetchall()
    if not rows:
        return None, None, None
    flip = rows[0]["model_a"] != selected
    deltas = np.array([(-1.0 if flip else 1.0) * r["delta_brier_interval"] for r in rows], dtype=float)
    lo = (1.0 - float(config["evaluation"]["bootstrap"]["confidence"])) / 2.0 * 100.0
    hi = 100.0 - lo
    return float(np.percentile(deltas, lo)), float(np.percentile(deltas, hi)), int(deltas.size)


def _calibration(conn, config, model):
    row = conn.execute("SELECT intercept, slope, status FROM calibration_diagnostics WHERE model_id = ?",
                       (model,)).fetchone()
    if row is None or row["status"] != "DEFINED" or row["slope"] is None or row["intercept"] is None:
        return "UNDEFINED", False
    lo, hi = config["evaluation"]["calibration_slope_acceptable"]
    ok = (lo <= row["slope"] <= hi) and abs(row["intercept"]) <= float(
        config["evaluation"]["calibration_intercept_abs_max"])
    return ("ACCEPTABLE" if ok else "NOT_ACCEPTABLE"), ok


def _discrimination(conn, config, selected, comparator):
    a = _metric(conn, selected, "ROC_AUC")
    b = _metric(conn, comparator, "ROC_AUC")
    if a["status"] != "DEFINED" or b["status"] != "DEFINED":
        return "UNDEFINED", False
    margin = float(config["evaluation"]["discrimination_margin_auc"])
    ok = a["value"] >= b["value"] - margin
    return ("NOT_WORSE" if ok else "WORSE"), ok


def _status(conn, config, model, selected, comparator, is_selected):
    cov = conn.execute("SELECT coverage FROM prediction_coverage WHERE model_id = ?", (model,)).fetchone()
    coverage = float(cov["coverage"]) if cov else 0.0
    if coverage < float(config["evaluation"]["coverage_threshold"]):
        return "NOT_COMPARABLE", None, None, None, None, coverage, "coverage below the threshold"
    if is_selected:
        delta = _metric(conn, selected, "BRIER")["value"] - _metric(conn, comparator, "BRIER")["value"]
        fold_better = sum(1 for f in range(1, 6)
                          if (_fold_brier(conn, selected, f) is not None and _fold_brier(conn, comparator, f) is not None
                              and _fold_brier(conn, selected, f) < _fold_brier(conn, comparator, f)))
        cal_status, cal_ok = _calibration(conn, config, selected)
        disc_status, disc_ok = _discrimination(conn, config, selected, comparator)
        lo, hi, n = _ci(conn, config, selected, comparator)
        if lo is None:
            return "INCONCLUSIVE", delta, None, None, fold_better, coverage, "no bootstrap replicates for the selected pair"
        if hi < 0 and fold_better >= int(config["evaluation"]["fold_consistency_min"]) and cal_ok and disc_ok:
            status = "SUPPORTED_IMPROVEMENT"
        elif lo <= 0 <= hi or fold_better < int(config["evaluation"]["fold_consistency_min"]):
            status = "INCONCLUSIVE"
        else:
            status = "NO_IMPROVEMENT"
        return status, delta, lo, hi, fold_better, coverage, (
            f"selected vs comparator: delta Brier {delta:.6f}; 95% hole-bootstrap [{lo:.6f}, {hi:.6f}]; "
            f"selected better in {fold_better}/5 lines; calibration {cal_status}; discrimination {disc_status}")
    # Comparator or rejected model: compare against the selected model.
    delta = _metric(conn, model, "BRIER")["value"] - _metric(conn, selected, "BRIER")["value"]
    lo, hi, n = _ci(conn, config, model, selected)
    cal_status, _ = _calibration(conn, config, model)
    disc_status, _ = _discrimination(conn, config, model, selected)
    if lo is None:
        status = "INCONCLUSIVE"
    elif lo > 0:
        status = "NO_IMPROVEMENT"
    elif lo <= 0 <= hi:
        status = "INCONCLUSIVE"
    else:
        status = "NO_IMPROVEMENT"
    return status, delta, lo, hi, None, coverage, (
        f"compared with selected {selected}: delta Brier {delta:.6f}; calibration {cal_status}; "
        f"discrimination {disc_status}")


def write(conn, config, receipt, created):
    feasible = list(config["evaluation"]["decision"]["feasible_models"])
    brier = {m: _metric(conn, m, "BRIER") for m in feasible}
    usable = [m for m in feasible if brier[m]["status"] == "DEFINED" and brier[m]["value"] is not None]
    if len(usable) < 2:
        raise RuntimeError("fewer than two feasible models have a defined Brier score")
    ranked = sorted(usable, key=lambda m: (brier[m]["value"], m))
    selected, comparator = ranked[0], ranked[1]
    rows = []
    for rank, m in enumerate(ranked, start=1):
        role = "SELECTED" if m == selected else "COMPARATOR" if m == comparator else "REJECTED"
        status, delta, lo, hi, consistency, coverage, reason = _status(
            conn, config, m, selected, comparator, m == selected)
        cal_status, _ = _calibration(conn, config, m)
        disc_status, _ = _discrimination(conn, config, m, comparator if m == selected else selected)
        basis = ("SUPPORTED" if status == "SUPPORTED_IMPROVEMENT" else
                 "POINT_ESTIMATE_WITH_CAVEAT" if m == selected else "NOT_SELECTED")
        rows.append((m, role, rank, status, basis, delta, lo, hi, consistency, cal_status, disc_status, coverage, reason))
    for m in ("M1_IK", "M3_HYBRID"):
        cov = conn.execute("SELECT coverage FROM prediction_coverage WHERE model_id = ?", (m,)).fetchone()
        coverage = float(cov["coverage"]) if cov else 0.0
        reason = ("M1 has no prediction in any fold; it is reported as a coverage failure and is not comparable"
                  if m == "M1_IK" else
                  "M3 is the recorded ML-only fallback and its predictions are identical to M2_RF; it is not a "
                  "separate hybrid candidate")
        if m == "M3_HYBRID":
            cal_status, _ = _calibration(conn, config, m)
            disc_status = "IDENTICAL_TO_M2_RF"
        else:
            cal_status, disc_status = "UNDEFINED", "UNDEFINED"
        rows.append((m, "NOT_COMPARABLE", None, "NOT_COMPARABLE", "NOT_RANKED", None, None, None, None,
                     cal_status, disc_status, coverage, reason))
    for r in rows:
        conn.execute("INSERT INTO comparison_decisions (model_id, role, rank, improvement_status, selection_basis, "
                     "delta_brier, ci_low, ci_high, fold_consistency, calibration_status, discrimination_status, coverage, "
                     "reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", r)
    selected_row = conn.execute("SELECT decision_id FROM comparison_decisions WHERE model_id = ? AND role = 'SELECTED'",
                                (selected,)).fetchone()
    handoff = {
        "selected_model_id": selected,
        "decision_id": selected_row["decision_id"],
        "target_receipt_id": receipt["receipt_id"],
        "split_plan_id": receipt["o3_split_plan_id"],
        "split_plan_sha256": receipt["o3_split_plan_sha256"],
        "metric_reference": "O4-T01 and O4-T02; pooled interval-weighted Brier is the primary endpoint",
        "calibration_policy": "Objective 3 calibration only; Objective 4 diagnostics are not applied",
        "allowed_domain": "held-out intervals in existing holes on an approved drill line; relative geometry; "
                          "not a distant prospect and not an absolute-elevation volume",
        "caveats": "Internal spatially held-out validation on five drill lines, not an external prospective campaign. "
                   "Only easting, northing and relative Z are predictors. M1 is not estimable; M3 is the ML-only "
                   "fallback. No grade, tonnage or resource is estimated.",
        "created_utc": created,
    }
    handoff_sha = sha256_text(json.dumps(handoff, sort_keys=True, separators=(",", ":")))
    conn.execute("INSERT INTO locked_handoff_receipts (selected_model_id, decision_id, target_receipt_id, split_plan_id, "
                 "split_plan_sha256, metric_reference, calibration_policy, allowed_domain, caveats, created_utc, "
                 "receipt_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (handoff["selected_model_id"], handoff["decision_id"], handoff["target_receipt_id"],
                  handoff["split_plan_id"], handoff["split_plan_sha256"], handoff["metric_reference"],
                  handoff["calibration_policy"], handoff["allowed_domain"], handoff["caveats"],
                  handoff["created_utc"], handoff_sha))
    return {"selected_model_id": selected, "comparator": comparator, "ranked": ranked,
            "brier": {m: brier[m]["value"] for m in ranked}, "handoff_sha256": handoff_sha}

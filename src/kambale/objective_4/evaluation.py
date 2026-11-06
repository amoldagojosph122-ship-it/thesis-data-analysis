"""Metric computation, calibration diagnostics, paired comparisons and hole-level resampling for Objective 4.

The module reads the frozen snapshot and writes only derived evaluation rows. It never changes a prediction and never
recalibrates on held-out labels.

Sign convention for every paired difference: delta = metric(model_b) - metric(model_a). A negative Brier difference means
model_b has the lower Brier score.
"""

from __future__ import annotations

import numpy as np

from kambale.objective_4 import metrics
from kambale.objective_4.config import O4_CONFIG_PATH, O4_DB_PATH, StopError, code_commit, load_config, utc_now
from kambale.objective_4.db import connect_o4

METRICS = ("BRIER", "LOG_LOSS", "ROC_AUC", "PR_AUC", "ECE")
WEIGHTINGS = ("INTERVAL", "EQUAL_HOLE")
IDENTITY_TOLERANCE = 1e-12


def power_label(ci_low, ci_high, identical: bool):
    """RESOLVED when the hole-cluster interval excludes zero; UNRESOLVED when it includes zero, with the half-width as
    the smallest difference the design could have detected; IDENTICAL when the two models are the same predictions."""
    if identical:
        return "IDENTICAL", None
    if ci_low is None or ci_high is None:
        return "NOT_ESTIMABLE", None
    if ci_low > 0 or ci_high < 0:
        return "RESOLVED", None
    return "UNRESOLVED", (ci_high - ci_low) / 2.0


def _identical_keys(conn):
    return {frozenset((r["model_a"], r["model_b"])) for r in conn.execute(
        "SELECT model_a, model_b FROM model_identities WHERE identical = 1")}


def _arrays(conn):
    pop = [dict(r) for r in conn.execute(
        "SELECT * FROM evaluation_population WHERE in_common_cohort = 1 ORDER BY observation_id")]
    ids = [r["observation_id"] for r in pop]
    y = np.array([r["true_label"] for r in pop], dtype=float)
    w_int = np.array([r["weight_interval"] for r in pop], dtype=float)
    w_hole = np.array([r["weight_equal_hole"] for r in pop], dtype=float)
    fold = np.array([r["fold_id"] for r in pop], dtype=int)
    line = np.array([r["line_code"] for r in pop], dtype=object)
    hole = np.array([r["hole_id"] for r in pop], dtype=object)
    depth = np.array([r["depth_from_m"] for r in pop], dtype=float)
    idx = {oid: i for i, oid in enumerate(ids)}
    models = [r["model_id"] for r in conn.execute("SELECT model_id FROM candidate_registry ORDER BY model_id")]
    coverage = {r["model_id"]: dict(r) for r in conn.execute("SELECT * FROM prediction_coverage")}
    candidates = {r["model_id"]: dict(r) for r in conn.execute("SELECT * FROM candidate_registry")}
    data, no_eval_reason = {}, {}
    for m in models:
        rows = [dict(r) for r in conn.execute(
            "SELECT observation_id, p_raw, p_calibrated, selected_probability, threshold, predicted_class, fold_id "
            "FROM prediction_snapshot WHERE model_id = ? ORDER BY observation_id", (m,))]
        local = {r["observation_id"]: r for r in rows}
        if not rows or any(oid not in local for oid in ids):
            # A model without a prediction for every common interval is not evaluated on the common cohort.
            data[m] = {"n": 0, "ids": [], "p": np.array([]), "threshold": {}}
            no_eval_reason[m] = (f"no common-cohort predictions ({coverage[m]['n_predicted']} of "
                                 f"{coverage[m]['n_expected']} held-out intervals; {coverage[m]['status']})")
            continue
        p = np.array([local[oid]["selected_probability"] for oid in ids], dtype=float)
        thr = {}
        for r in rows:
            thr[r["fold_id"]] = float(r["threshold"])
        data[m] = {"n": len(rows), "ids": ids, "p": p, "threshold": thr}
    return {"pop": pop, "ids": ids, "y": y, "w_int": w_int, "w_hole": w_hole, "fold": fold, "line": line,
            "hole": hole, "depth": depth, "index": idx, "models": models, "coverage": coverage,
            "candidates": candidates, "data": data, "no_eval_reason": no_eval_reason}


def _metric_value(metric_id, y, p, w, threshold, eps):
    if metric_id == "BRIER":
        return metrics.brier(y, p, w), "DEFINED", "weighted Brier score"
    if metric_id == "LOG_LOSS":
        return metrics.log_loss(y, p, w, eps), "DEFINED", f"weighted log loss with epsilon {eps:g}"
    if metric_id == "ROC_AUC":
        return metrics.roc_auc(y, p, w)
    if metric_id == "PR_AUC":
        return metrics.pr_auc(y, p, w)
    if metric_id == "ECE":
        bins = metrics.reliability_bins(y, p, w, [i / 10.0 for i in range(11)], 20)
        value, status = metrics.ece_from_bins(bins)
        return value, status, "ECE from merged reliability bins"
    raise ValueError(metric_id)


def _write_metrics(conn, cfg, arr):
    eps = float(cfg["evaluation"]["epsilon"])
    edges = [float(x) for x in cfg["evaluation"]["calibration_bins"]]
    min_n = int(cfg["evaluation"]["calibration_min_bin_n"])
    y = arr["y"]
    folds = sorted(set(arr["fold"].tolist()))
    for m in arr["models"]:
        d = arr["data"][m]
        if d["n"] == 0:
            reason = arr["no_eval_reason"].get(m, "no prediction")
            for weighting in WEIGHTINGS:
                for metric_id in METRICS:
                    conn.execute("INSERT INTO pooled_metrics (model_id, weighting, metric_id, value, status, n, n_positive, "
                                 "reason) VALUES (?, ?, ?, NULL, 'NOT_ESTIMABLE', 0, 0, ?)",
                                 (m, weighting, metric_id, reason))
                for fold in folds:
                    for metric_id in METRICS:
                        conn.execute("INSERT INTO fold_metrics (model_id, fold_id, weighting, metric_id, value, status, n, "
                                     "n_positive, reason) VALUES (?, ?, ?, ?, NULL, 'NOT_ESTIMABLE', 0, 0, ?)",
                                     (m, fold, weighting, metric_id, reason))
            conn.execute("INSERT INTO calibration_diagnostics (model_id, n, intercept, slope, status, reason) "
                         "VALUES (?, 0, NULL, NULL, 'NOT_ESTIMABLE', ?)", (m, reason))
            continue
        p = d["p"]
        for weighting in WEIGHTINGS:
            w = arr["w_int"] if weighting == "INTERVAL" else arr["w_hole"]
            for metric_id in METRICS:
                value, status, reason = _metric_value(metric_id, y, p, w, 0.5, eps)
                conn.execute("INSERT INTO pooled_metrics (model_id, weighting, metric_id, value, status, n, n_positive, "
                             "reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (m, weighting, metric_id, value, status, int(y.size), int(y.sum()), reason))
            for fold in folds:
                mask = arr["fold"] == fold
                for metric_id in METRICS:
                    value, status, reason = _metric_value(metric_id, y[mask], p[mask], w[mask], 0.5, eps)
                    conn.execute("INSERT INTO fold_metrics (model_id, fold_id, weighting, metric_id, value, status, n, "
                                 "n_positive, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                 (m, fold, weighting, metric_id, value, status, int(mask.sum()),
                                  int(y[mask].sum()), reason))
        cal = metrics.calibration_fit(y, p, arr["w_int"], eps)
        conn.execute("INSERT INTO calibration_diagnostics (model_id, n, intercept, slope, status, reason) "
                     "VALUES (?, ?, ?, ?, ?, ?)",
                     (m, cal["n"], cal["intercept"], cal["slope"], cal["status"], cal["reason"]))
        bins = metrics.reliability_bins(y, p, arr["w_int"], edges, min_n)
        for b in bins:
            conn.execute("INSERT INTO calibration_bins (model_id, bin_index, bin_lower, bin_upper, n, mean_p, "
                         "observed_rate, wilson_low, wilson_high, merged) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (m, b["bin_index"], b["bin_lower"], b["bin_upper"], b["n"], b["mean_p"], b["observed_rate"],
                          b["wilson_low"], b["wilson_high"], b["merged"]))


def _confusion_from_counts(tp, fp, tn, fn):
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    balanced = (recall + specificity) / 2 if recall is not None and specificity is not None else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall and (precision + recall) else None
    denom = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    mcc = (tp * tn - fp * fn) / (denom ** 0.5) if denom else None
    undefined = [name for name, value in (("precision", precision), ("recall", recall), ("specificity", specificity),
                                          ("balanced_accuracy", balanced), ("f1", f1), ("mcc", mcc)) if value is None]
    return {"precision": precision, "recall": recall, "specificity": specificity, "balanced_accuracy": balanced,
            "f1": f1, "mcc": mcc, "status": "DEFINED" if not undefined else "UNDEFINED",
            "reason": "all rates defined" if not undefined else "undefined rates: " + ", ".join(undefined)}


def _write_confusions(conn, arr):
    for m in arr["models"]:
        d = arr["data"][m]
        if d["n"] == 0:
            conn.execute("INSERT INTO class_confusion_matrices (model_id, scope, fold_id, threshold, threshold_source, "
                         "tp, fp, tn, fn, precision, recall, specificity, balanced_accuracy, f1, mcc, status, reason) "
                         "VALUES (?, 'POOLED', 0, NULL, 'NO_COMMON_COHORT_PREDICTION', 0, 0, 0, 0, NULL, NULL, NULL, NULL, "
                         "NULL, NULL, 'UNDEFINED', ?)", (m, arr["no_eval_reason"].get(m, "no prediction")))
            continue
        totals = [0, 0, 0, 0]
        for fold in sorted(set(arr["fold"].tolist())):
            mask = arr["fold"] == fold
            thr = d["threshold"].get(int(fold), 0.5)
            c = metrics.confusion(arr["y"][mask], d["p"][mask], thr)
            totals[0] += c["tp"]
            totals[1] += c["fp"]
            totals[2] += c["tn"]
            totals[3] += c["fn"]
            conn.execute("INSERT INTO class_confusion_matrices (model_id, scope, fold_id, threshold, threshold_source, "
                         "tp, fp, tn, fn, precision, recall, specificity, balanced_accuracy, f1, mcc, status, reason) "
                         "VALUES (?, 'FOLD', ?, ?, 'O3_TRAINING_ONLY_THRESHOLD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (m, fold, thr, c["tp"], c["fp"], c["tn"], c["fn"], c["precision"], c["recall"],
                          c["specificity"], c["balanced_accuracy"], c["f1"], c["mcc"], c["status"], c["reason"]))
        tp, fp, tn, fn = totals
        c = _confusion_from_counts(tp, fp, tn, fn)
        conn.execute("INSERT INTO class_confusion_matrices (model_id, scope, fold_id, threshold, threshold_source, "
                     "tp, fp, tn, fn, precision, recall, specificity, balanced_accuracy, f1, mcc, status, reason) "
                     "VALUES (?, 'POOLED', 0, NULL, 'O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (m, tp, fp, tn, fn, c["precision"], c["recall"], c["specificity"], c["balanced_accuracy"],
                      c["f1"], c["mcc"], c["status"], c["reason"]))


def _write_curve_points(conn, arr):
    for m in arr["models"]:
        d = arr["data"][m]
        if d["n"] == 0:
            continue
        for k, pt in enumerate(metrics.roc_points(arr["y"], d["p"], arr["w_int"])):
            conn.execute("INSERT INTO metric_curve_points (model_id, curve, point_index, threshold, tpr, fpr, precision, "
                         "recall, n) VALUES (?, 'ROC', ?, ?, ?, ?, NULL, NULL, ?)",
                         (m, k, pt["threshold"], pt["tpr"], pt["fpr"], pt["n"]))
        for k, pt in enumerate(metrics.pr_points(arr["y"], d["p"], arr["w_int"])):
            conn.execute("INSERT INTO metric_curve_points (model_id, curve, point_index, threshold, tpr, fpr, precision, "
                         "recall, n) VALUES (?, 'PR', ?, ?, NULL, NULL, ?, ?, ?)",
                         (m, k, pt["threshold"], pt["precision"], pt["recall"], pt["n"]))


def _write_spatial_errors(conn, arr, cfg):
    width = float(cfg["evaluation"]["depth_bin_width_m"])
    for m in arr["models"]:
        d = arr["data"][m]
        if d["n"] == 0:
            continue
        for i, oid in enumerate(arr["ids"]):
            fold = int(arr["fold"][i])
            thr = d["threshold"].get(fold, 0.5)
            pred = 1 if d["p"][i] >= thr else 0
            y = int(arr["y"][i])
            kind = "TP" if pred == 1 and y == 1 else "FP" if pred == 1 and y == 0 else "TN" if pred == 0 and y == 0 else "FN"
            lo = width * int(arr["depth"][i] // width)
            hi = lo + width
            key = (m, arr["line"][i], lo, hi, kind)
            rec = conn.execute("SELECT n, mean_residual FROM spatial_error_summaries WHERE model_id = ? AND line_code = ? "
                               "AND depth_bin_from_m = ? AND depth_bin_to_m = ? AND error_type = ?", key).fetchone()
            residual = float(y - d["p"][i])
            if rec is None:
                conn.execute("INSERT INTO spatial_error_summaries (model_id, line_code, depth_bin_from_m, depth_bin_to_m, "
                             "error_type, n, mean_residual) VALUES (?, ?, ?, ?, ?, 1, ?)", (*key, residual))
            else:
                n = rec["n"] + 1
                mean = (rec["mean_residual"] * rec["n"] + residual) / n
                conn.execute("UPDATE spatial_error_summaries SET n = ?, mean_residual = ? WHERE model_id = ? AND "
                             "line_code = ? AND depth_bin_from_m = ? AND depth_bin_to_m = ? AND error_type = ?",
                             (n, mean, *key))


def _pair_rows(conn, arr, pair, mask, scope, fold_id, line_code, identical, status_override=None):
    a, b = pair["model_a"], pair["model_b"]
    da, db = arr["data"][a], arr["data"][b]
    if da["n"] == 0 or db["n"] == 0 or not np.any(mask):
        return
    y = arr["y"][mask]
    for weighting in WEIGHTINGS:
        w = (arr["w_int"] if weighting == "INTERVAL" else arr["w_hole"])[mask]
        pa, pb = da["p"][mask], db["p"][mask]
        ba, bb = metrics.brier(y, pa, w), metrics.brier(y, pb, w)
        la, lb = metrics.log_loss(y, pa, w), metrics.log_loss(y, pb, w)
        auca, sa, _ = metrics.roc_auc(y, pa, w)
        aucb, sb, _ = metrics.roc_auc(y, pb, w)
        apa, spa, _ = metrics.pr_auc(y, pa, w)
        apb, spb, _ = metrics.pr_auc(y, pb, w)
        reason = []
        if sa != "DEFINED" or sb != "DEFINED":
            reason.append("ROC-AUC undefined in this subset")
        if spa != "DEFINED" or spb != "DEFINED":
            reason.append("PR-AUC undefined in this subset")
        status = "DEFINED" if not reason else "UNDEFINED"
        note = "both models defined on this subset"
        if identical:
            status, note = "IDENTICAL", "identical predictions on every common observation; no interval"
        elif reason:
            note = "; ".join(reason)
        conn.execute("INSERT INTO paired_differences (pair_id, model_a, model_b, scope, fold_id, line_code, weighting, "
                     "delta_brier, delta_log_loss, delta_roc_auc, delta_pr_auc, n, status, reason) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (pair["pair_id"], a, b, scope, fold_id, line_code, weighting, bb - ba, lb - la,
                      (aucb - auca) if auca is not None and aucb is not None else None,
                      (apb - apa) if apa is not None and apb is not None else None,
                      int(np.sum(mask)), status_override or status, note))


def _write_pairs(conn, cfg, arr):
    identical = _identical_keys(conn)
    for pair in cfg["evaluation"]["pairs"]:
        if arr["data"][pair["model_a"]]["n"] == 0 or arr["data"][pair["model_b"]]["n"] == 0:
            reason = "; ".join(f"{m}: {arr['no_eval_reason'][m]}" for m in (pair["model_a"], pair["model_b"])
                               if m in arr["no_eval_reason"])
            for weighting in WEIGHTINGS:
                conn.execute("INSERT INTO paired_differences (pair_id, model_a, model_b, scope, fold_id, line_code, weighting, "
                             "delta_brier, delta_log_loss, delta_roc_auc, delta_pr_auc, n, status, reason) "
                             "VALUES (?, ?, ?, 'POOLED', 0, '', ?, NULL, NULL, NULL, NULL, 0, 'NOT_ESTIMABLE', ?)",
                             (pair["pair_id"], pair["model_a"], pair["model_b"], weighting, reason))
            continue
        same = frozenset((pair["model_a"], pair["model_b"])) in identical
        override = "IDENTICAL" if same else None
        _pair_rows(conn, arr, pair, np.ones(arr["y"].size, dtype=bool), "POOLED", 0, "", same, override)
        for fold in sorted(set(arr["fold"].tolist())):
            _pair_rows(conn, arr, pair, arr["fold"] == fold, "FOLD", int(fold), "", same, override)
        for line in sorted(set(arr["line"].tolist())):
            _pair_rows(conn, arr, pair, arr["line"] == line, "LINE", 0, str(line), same, override)


def _bootstrap_pairs(conn, cfg):
    """Every configured pair that is not an identity, then every other pair of distinct full-coverage feasible models
    (auxiliary pairs), so that the decision's comparator interval is available whichever model is second."""
    identical = _identical_keys(conn)
    feasible = list(cfg["evaluation"]["models"]["feasible"])
    status = {r["model_id"]: r["status"] for r in conn.execute("SELECT model_id, status FROM prediction_coverage")}
    ident = {r["model_id"]: r["identity_status"] for r in conn.execute("SELECT model_id, identity_status FROM candidate_registry")}
    out, seen = [], set()
    for pair in cfg["evaluation"]["pairs"]:
        key = frozenset((pair["model_a"], pair["model_b"]))
        if key in identical or pair["model_a"] == pair["model_b"] or key in seen:
            continue
        out.append(dict(pair))
        seen.add(key)
    distinct = [m for m in feasible if status.get(m) == "FULL" and ident.get(m) == "DISTINCT"]
    for i, a in enumerate(distinct):
        for b in distinct[i + 1:]:
            key = frozenset((a, b))
            if key in identical or key in seen:
                continue
            out.append({"pair_id": f"AUX_{a}__{b}", "model_a": a, "model_b": b, "auxiliary": True})
            seen.add(key)
    return out


def _bootstrap(conn, cfg, arr):
    n_rep = int(cfg["evaluation"]["bootstrap"]["n_replicates"])
    seed = int(cfg["evaluation"]["bootstrap"]["seed"])
    pairs = _bootstrap_pairs(conn, cfg)
    designs = (("O4-BOOT-HOLE", "HOLE_CLUSTER", arr["hole"], seed),
               ("O4-BOOT-LINE", "LINE_CLUSTER", arr["line"], seed + 1))
    for design_id, method, units, design_seed in designs:
        uniq = sorted(set(units.tolist()))
        idx_by_unit = {u: np.where(units == u)[0] for u in uniq}
        conn.execute("INSERT INTO resampling_designs (design_id, method, unit, n_units, n_replicates, seed, notes) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (design_id, method, "hole" if method == "HOLE_CLUSTER" else "line", len(uniq), n_rep, design_seed,
                      "resample units with replacement; keep all intervals of a unit and the same observations for both "
                      "models; differences are model_b minus model_a"))
        rng = np.random.default_rng(design_seed)
        y = arr["y"]
        w_hole = arr["w_hole"]
        models = [m for m in arr["models"] if arr["data"][m]["n"] > 0]
        rows = []
        for rep in range(1, n_rep + 1):
            sample = rng.choice(len(uniq), size=len(uniq), replace=True)
            idx = np.concatenate([idx_by_unit[uniq[k]] for k in sample])
            yb = y[idx]
            b_int, b_hole, l_int = {}, {}, {}
            wb = w_hole[idx]
            for m in models:
                pb = arr["data"][m]["p"][idx]
                b_int[m] = float(np.mean((pb - yb) ** 2))
                b_hole[m] = float(np.sum(wb * (pb - yb) ** 2) / np.sum(wb))
                l_int[m] = metrics.log_loss(yb, pb, np.ones_like(pb), float(cfg["evaluation"]["epsilon"]))
            for pair in pairs:
                a, b = pair["model_a"], pair["model_b"]
                if a not in b_int or b not in b_int:
                    continue
                rows.append((design_id, pair["pair_id"], rep, a, b, b_int[b] - b_int[a], b_hole[b] - b_hole[a],
                             l_int[b] - l_int[a], int(idx.size)))
        conn.executemany("INSERT INTO bootstrap_replicates (design_id, pair_id, replicate_index, model_a, model_b, "
                         "delta_brier_interval, delta_brier_equal_hole, delta_log_loss_interval, n_obs) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)


def _update_pair_ci(conn, cfg):
    """Attach the interval and the power label to each configured pair (interval weighting)."""
    lo_q = (1.0 - float(cfg["evaluation"]["bootstrap"]["confidence"])) / 2.0 * 100.0
    hi_q = 100.0 - lo_q
    identical = _identical_keys(conn)
    for pair in cfg["evaluation"]["pairs"]:
        key = frozenset((pair["model_a"], pair["model_b"]))
        if key in identical:
            conn.execute("UPDATE paired_differences SET power_label = 'IDENTICAL', ci_low = NULL, ci_high = NULL, "
                         "ci_low_line = NULL, ci_high_line = NULL, detectable_half_width = NULL, status = 'IDENTICAL', "
                         "ci_design = 'not applicable: identical predictions' WHERE pair_id = ?", (pair["pair_id"],))
            continue
        intervals = {}
        for design_id, prefix in (("O4-BOOT-HOLE", "ci"), ("O4-BOOT-LINE", "ci_line")):
            rows = conn.execute("SELECT delta_brier_interval FROM bootstrap_replicates WHERE design_id = ? AND pair_id = ?",
                                (design_id, pair["pair_id"])).fetchall()
            if rows:
                values = np.array([r[0] for r in rows], dtype=float)
                intervals[design_id] = (float(np.percentile(values, lo_q)), float(np.percentile(values, hi_q)))
        hole = intervals.get("O4-BOOT-HOLE", (None, None))
        line = intervals.get("O4-BOOT-LINE", (None, None))
        label, half = power_label(hole[0], hole[1], False)
        conn.execute("UPDATE paired_differences SET ci_low = ?, ci_high = ?, ci_low_line = ?, ci_high_line = ?, "
                     "power_label = ?, detectable_half_width = ?, ci_design = ? "
                     "WHERE pair_id = ? AND scope = 'POOLED' AND weighting = 'INTERVAL'",
                     (hole[0], hole[1], line[0], line[1], label, half,
                      "HOLE_CLUSTER primary; LINE_CLUSTER sensitivity in ci_low_line/ci_high_line",
                      pair["pair_id"]))
        conn.execute("UPDATE paired_differences SET power_label = NULL WHERE pair_id = ? AND weighting = 'EQUAL_HOLE'",
                     (pair["pair_id"],))


def _audit(conn, run_id, arr, config, receipt, created):
    checks = []
    ev = config["evaluation"]
    checks.append({"check_name": "O3_SNAPSHOT_HASH_RECORDED",
                   "status": "PASS" if receipt["o3_prediction_snapshot_sha256"] else "FAIL",
                   "detail": f"snapshot {receipt['o3_prediction_snapshot_sha256'][:16]}"})
    common = {r["observation_id"] for r in conn.execute("SELECT observation_id FROM evaluation_population "
                                                        "WHERE in_common_cohort = 1")}
    full = [r["model_id"] for r in conn.execute("SELECT model_id FROM prediction_coverage WHERE status = 'FULL' "
                                                "AND model_id IN (%s)" % ",".join("?" * len(ev["models"]["feasible"])),
                                                tuple(ev["models"]["feasible"]))]
    missing = 0
    for m in full:
        ids = {r["observation_id"] for r in conn.execute("SELECT observation_id FROM prediction_snapshot WHERE model_id = ?", (m,))}
        missing += len(common - ids)
    checks.append({"check_name": "COMMON_COHORT_IDENTICAL_ACROSS_FULL_FEASIBLE_MODELS",
                   "status": "PASS" if missing == 0 else "FAIL",
                   "detail": f"{len(common)} common observations; {len(full)} full-coverage feasible models; "
                             f"{missing} missing model IDs"})
    mismatch = []
    for r in conn.execute("SELECT c.model_id, c.n_predicted, COUNT(p.snapshot_id) AS n_rows FROM prediction_coverage c "
                          "LEFT JOIN prediction_snapshot p ON p.model_id = c.model_id GROUP BY c.model_id"):
        if r["n_predicted"] != r["n_rows"]:
            mismatch.append(r["model_id"])
    checks.append({"check_name": "COVERAGE_MATCHES_SNAPSHOT", "status": "PASS" if not mismatch else "FAIL",
                   "detail": "coverage rows match snapshot rows" if not mismatch else "mismatch: " + ", ".join(mismatch)})
    # Identities recomputed from the stored probabilities on the common cohort, independently of the importer.
    rec_bad = []
    snap = {}
    for r in conn.execute("SELECT p.model_id, p.observation_id, p.p_calibrated FROM prediction_snapshot p "
                          "JOIN evaluation_population e ON e.receipt_id = p.receipt_id AND e.observation_id = p.observation_id "
                          "WHERE e.in_common_cohort = 1"):
        snap.setdefault(r["model_id"], {})[r["observation_id"]] = float(r["p_calibrated"])
    order = list(ev["models"]["feasible"])
    stored = {(r["model_a"], r["model_b"]): r for r in conn.execute("SELECT * FROM model_identities")}
    n_pairs = 0
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            if a not in snap or b not in snap or set(snap[a]) != set(snap[b]):
                continue
            n_pairs += 1
            diff = max(abs(snap[a][o] - snap[b][o]) for o in snap[a]) if snap[a] else None
            ident = diff is not None and diff <= IDENTITY_TOLERANCE
            rec = stored.get((a, b))
            if rec is None or bool(rec["identical"]) != bool(ident):
                rec_bad.append(f"{a}/{b}")
    for m in order:
        row = conn.execute("SELECT identity_status, identical_to FROM candidate_registry WHERE model_id = ?", (m,)).fetchone()
        if row is None:
            rec_bad.append(m)
            continue
        ref = None
        for j, cand in enumerate(order):
            if cand == m:
                break
            rec = stored.get((cand, m))
            if rec is not None and rec["identical"]:
                ref = cand
        expected = "IDENTICAL_TO" if ref else "DISTINCT"
        if row["identity_status"] != expected or row["identical_to"] != ref:
            rec_bad.append(f"registry {m}")
    checks.append({"check_name": "IDENTITY_RECORDED_MATCHES_RECOMPUTATION", "status": "PASS" if not rec_bad else "FAIL",
                   "detail": f"{n_pairs} feasible pairs recomputed" + ("" if not rec_bad else "; differences: " +
                                                                        ", ".join(rec_bad))})
    bad_prob = conn.execute("SELECT COUNT(*) FROM prediction_snapshot WHERE p_raw < 0 OR p_raw > 1 OR p_calibrated < 0 "
                            "OR p_calibrated > 1").fetchone()[0]
    checks.append({"check_name": "PROBABILITY_BOUNDS", "status": "PASS" if bad_prob == 0 else "FAIL",
                   "detail": f"{bad_prob} out-of-bounds probabilities"})
    thr = conn.execute("SELECT COUNT(*) FROM prediction_snapshot").fetchone()[0]
    checks.append({"check_name": "THRESHOLDS_FROZEN_FROM_O3", "status": "PASS" if thr > 0 else "FAIL",
                   "detail": f"{thr} snapshot rows carry the O3 threshold"})
    iid = conn.execute("SELECT COUNT(*) FROM resampling_designs WHERE method = 'HOLE_CLUSTER'").fetchone()[0]
    checks.append({"check_name": "BOOTSTRAP_USES_SPATIAL_UNITS", "status": "PASS" if iid == 1 else "FAIL",
                   "detail": "hole-cluster design present" if iid == 1 else "hole-cluster design missing"})
    # Numerical cross-check of the pooled interval Brier, one row per feasible model with predictions.
    checked = 0
    for m in order:
        rows = [dict(r) for r in conn.execute(
            "SELECT e.true_label, p.selected_probability, e.weight_interval FROM prediction_snapshot p "
            "JOIN evaluation_population e ON e.receipt_id = p.receipt_id AND e.observation_id = p.observation_id "
            "WHERE p.model_id = ? AND e.in_common_cohort = 1", (m,))]
        if not rows:
            continue
        checked += 1
        y = np.array([r["true_label"] for r in rows], dtype=float)
        p = np.array([r["selected_probability"] for r in rows], dtype=float)
        w = np.array([r["weight_interval"] for r in rows], dtype=float)
        fast = metrics.brier(y, p, w)
        slow = metrics.independent_brier(y, p, w)
        checks.append({"check_name": "BRIER_NUMERICAL_CROSS_CHECK",
                       "status": "PASS" if abs(fast - slow) < 1e-12 else "FAIL",
                       "detail": f"{m}: vector {fast:.12f}; loop {slow:.12f}"})
    if checked == 0:
        checks.append({"check_name": "BRIER_NUMERICAL_CROSS_CHECK", "status": "FAIL", "detail": "no model cross-checked"})
    checks.append({"check_name": "BRIER_CROSS_CHECK_COVERS_FEASIBLE_MODELS",
                   "status": "PASS" if checked == len([m for m in order if arr["data"].get(m, {}).get("n", 0) > 0])
                   else "FAIL", "detail": f"{checked} feasible models cross-checked"})
    # Power labels recomputed from the stored intervals.
    label_bad = []
    for pair in ev["pairs"]:
        row = conn.execute("SELECT power_label, ci_low, ci_high, detectable_half_width FROM paired_differences "
                           "WHERE pair_id = ? AND scope = 'POOLED' AND weighting = 'INTERVAL'", (pair["pair_id"],)).fetchone()
        if row is None:
            label_bad.append(pair["pair_id"] + " missing")
            continue
        key = frozenset((pair["model_a"], pair["model_b"]))
        same = stored.get(tuple(sorted((pair["model_a"], pair["model_b"]), key=order.index)))
        identical = same is not None and bool(same["identical"])
        expected, half = power_label(row["ci_low"], row["ci_high"], identical)
        ok = row["power_label"] == expected and (
            (half is None and row["detectable_half_width"] is None) or
            (half is not None and row["detectable_half_width"] is not None and abs(half - row["detectable_half_width"]) < 1e-12))
        if not ok:
            label_bad.append(pair["pair_id"])
    checks.append({"check_name": "POWER_LABELS_MATCH_INTERVALS", "status": "PASS" if not label_bad else "FAIL",
                   "detail": "all configured pairs labelled from their intervals" if not label_bad else
                   "mismatch: " + ", ".join(label_bad)})
    model_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    checks.append({"check_name": "NO_MODEL_REFIT", "status": "PASS" if not ({"training_runs", "model_artifacts"} & model_tables)
                   else "FAIL", "detail": "Objective 4 contains no training or model-artifact table"})
    checks.append({"check_name": "CALIBRATION_DIAGNOSTIC_ONLY", "status": "PASS",
                   "detail": "calibration intercept and slope are diagnostics; no recalibrated probability column exists"})
    for c in checks:
        conn.execute("INSERT INTO evaluation_audit_log (run_id, check_name, status, detail, created_utc) "
                     "VALUES (?, ?, ?, ?, ?)", (run_id, c["check_name"], c["status"], c["detail"], created))
    return checks


def run(receipt_id: int | None = None, config_path=None, o4_path=None) -> dict:
    config, config_sha = load_config(config_path or O4_CONFIG_PATH)
    conn = connect_o4(o4_path or O4_DB_PATH)
    try:
        if receipt_id is None:
            row = conn.execute("SELECT receipt_id FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
            if row is None:
                raise StopError("no receipt: run the import first")
            receipt_id = row["receipt_id"]
        receipt = conn.execute("SELECT * FROM source_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
        if conn.execute("SELECT COUNT(*) FROM pooled_metrics").fetchone()[0]:
            raise StopError("evaluation rows already exist; rebuild from an empty database to re-run")
        conn.execute("BEGIN IMMEDIATE")
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, started_utc, status, "
            "code_commit, note) VALUES ('EVALUATE', ?, ?, ?, ?, 'RUNNING', ?, 'frozen OOF metrics and paired resampling')",
            (config["config_version"], config_sha, receipt_id, utc_now(), code_commit())).lastrowid
        created = utc_now()
        arr = _arrays(conn)
        _write_metrics(conn, config, arr)
        _write_confusions(conn, arr)
        _write_curve_points(conn, arr)
        _write_spatial_errors(conn, arr, config)
        _write_pairs(conn, config, arr)
        _bootstrap(conn, config, arr)
        _update_pair_ci(conn, config)
        from kambale.objective_4 import decision
        decision.write(conn, config, receipt, created)
        audits = _audit(conn, run_id, arr, config, receipt, created)
        conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ? WHERE run_id = ?",
                     (utc_now(), run_id))
        conn.execute("COMMIT")
        return {"run_id": run_id, "receipt_id": receipt_id, "models": arr["models"],
                "common_cohort": len(arr["ids"]), "audits": audits}
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

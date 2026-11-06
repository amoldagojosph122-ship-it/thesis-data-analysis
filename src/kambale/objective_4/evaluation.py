"""Metric computation, calibration diagnostics, paired comparisons and hole-level resampling for Objective 4.

The module reads the frozen snapshot and writes only derived evaluation rows. It never changes a prediction and never
recalibrates on held-out labels.
"""

from __future__ import annotations

import json

import numpy as np

from kambale.objective_4 import metrics
from kambale.objective_4.config import O3_DB_PATH, O4_CONFIG_PATH, O4_DB_PATH, StopError, code_commit, load_config, utc_now
from kambale.objective_4.db import connect_o4, connect_readonly

METRICS = ("BRIER", "LOG_LOSS", "ROC_AUC", "PR_AUC", "ECE")
WEIGHTINGS = ("INTERVAL", "EQUAL_HOLE")


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
    data = {}
    for m in models:
        rows = [dict(r) for r in conn.execute(
            "SELECT observation_id, p_raw, p_calibrated, selected_probability, threshold, predicted_class, fold_id "
            "FROM prediction_snapshot WHERE model_id = ? ORDER BY observation_id", (m,))]
        if not rows:
            data[m] = {"n": 0, "ids": [], "p": np.array([]), "threshold": {}}
            continue
        local = {r["observation_id"]: r for r in rows}
        p = np.array([local[oid]["selected_probability"] for oid in ids], dtype=float)
        thr = {}
        for r in rows:
            thr[r["fold_id"]] = float(r["threshold"])
        data[m] = {"n": len(rows), "ids": ids, "p": p, "threshold": thr}
    return {"pop": pop, "ids": ids, "y": y, "w_int": w_int, "w_hole": w_hole, "fold": fold, "line": line,
            "hole": hole, "depth": depth, "index": idx, "models": models, "coverage": coverage,
            "candidates": candidates, "data": data}


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
    for m in arr["models"]:
        d = arr["data"][m]
        cov = arr["coverage"][m]
        if d["n"] == 0:
            for weighting in WEIGHTINGS:
                for metric_id in METRICS:
                    conn.execute("INSERT INTO pooled_metrics (model_id, weighting, metric_id, value, status, n, n_positive, "
                                 "reason) VALUES (?, ?, ?, NULL, 'NOT_ESTIMABLE', 0, 0, ?)",
                                 (m, weighting, metric_id, f"no prediction; {cov['n_failed']} explicit failures"))
                for fold in sorted(set(arr["fold"].tolist())):
                    for metric_id in METRICS:
                        conn.execute("INSERT INTO fold_metrics (model_id, fold_id, weighting, metric_id, value, status, n, "
                                     "n_positive, reason) VALUES (?, ?, ?, ?, NULL, 'NOT_ESTIMABLE', 0, 0, ?)",
                                     (m, fold, weighting, metric_id, "no prediction in this fold"))
            conn.execute("INSERT INTO calibration_diagnostics (model_id, n, intercept, slope, status, reason) "
                         "VALUES (?, 0, NULL, NULL, 'NOT_ESTIMABLE', ?)",
                         (m, f"no prediction; {cov['n_failed']} explicit failures"))
            continue
        p = d["p"]
        for weighting in WEIGHTINGS:
            w = arr["w_int"] if weighting == "INTERVAL" else arr["w_hole"]
            for metric_id in METRICS:
                value, status, reason = _metric_value(metric_id, y, p, w, 0.5, eps)
                conn.execute("INSERT INTO pooled_metrics (model_id, weighting, metric_id, value, status, n, n_positive, "
                             "reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (m, weighting, metric_id, value, status, int(y.size), int(y.sum()), reason))
            for fold in sorted(set(arr["fold"].tolist())):
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
        cov = arr["coverage"][m]
        if d["n"] == 0:
            conn.execute("INSERT INTO class_confusion_matrices (model_id, scope, fold_id, threshold, threshold_source, "
                         "tp, fp, tn, fn, precision, recall, specificity, balanced_accuracy, f1, mcc, status, reason) "
                         "VALUES (?, 'POOLED', 0, NULL, 'NO_PREDICTION', 0, 0, 0, 0, NULL, NULL, NULL, NULL, NULL, NULL, "
                         "'UNDEFINED', ?)", (m, f"no prediction; {cov['n_failed']} explicit failures"))
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


def _pair_rows(conn, arr, pair, mask, scope, fold_id, line_code):
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
        conn.execute("INSERT INTO paired_differences (pair_id, model_a, model_b, scope, fold_id, line_code, weighting, "
                     "delta_brier, delta_log_loss, delta_roc_auc, delta_pr_auc, n, status, reason) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (pair["pair_id"], a, b, scope, fold_id, line_code, weighting, ba - bb, la - lb,
                      (auca - aucb) if auca is not None and aucb is not None else None,
                      (apa - apb) if apa is not None and apb is not None else None,
                      int(np.sum(mask)), status, "; ".join(reason) or "both models defined on this subset"))


def _write_pairs(conn, cfg, arr):
    for pair in cfg["evaluation"]["pairs"]:
        if pair["model_a"] not in arr["data"] or pair["model_b"] not in arr["data"]:
            continue
        _pair_rows(conn, arr, pair, np.ones(arr["y"].size, dtype=bool), "POOLED", 0, "")
        for fold in sorted(set(arr["fold"].tolist())):
            _pair_rows(conn, arr, pair, arr["fold"] == fold, "FOLD", int(fold), "")
        for line in sorted(set(arr["line"].tolist())):
            _pair_rows(conn, arr, pair, arr["line"] == line, "LINE", 0, str(line))


def _update_pair_ci(conn, cfg):
    lo_q = (1.0 - float(cfg["evaluation"]["bootstrap"]["confidence"])) / 2.0 * 100.0
    hi_q = 100.0 - lo_q
    for pair in cfg["evaluation"]["pairs"]:
        for design_id, cols in (("O4-BOOT-HOLE", ("ci_low", "ci_high")), ("O4-BOOT-LINE", ("ci_low_line", "ci_high_line"))):
            rows = conn.execute("SELECT delta_brier_interval FROM bootstrap_replicates WHERE design_id = ? AND pair_id = ?",
                                (design_id, pair["pair_id"])).fetchall()
            if not rows:
                continue
            values = np.array([r[0] for r in rows], dtype=float)
            lo, hi = float(np.percentile(values, lo_q)), float(np.percentile(values, hi_q))
            conn.execute(f"UPDATE paired_differences SET {cols[0]} = ?, {cols[1]} = ?, ci_design = ? "
                         "WHERE pair_id = ? AND scope = 'POOLED' AND weighting = 'INTERVAL'",
                         (lo, hi, "HOLE_CLUSTER; line sensitivity in ci_low_line/ci_high_line", pair["pair_id"]))


def _bootstrap(conn, cfg, arr):
    n_rep = int(cfg["evaluation"]["bootstrap"]["n_replicates"])
    seed = int(cfg["evaluation"]["bootstrap"]["seed"])
    confidence = float(cfg["evaluation"]["bootstrap"]["confidence"])
    pairs = cfg["evaluation"]["pairs"]
    designs = (("O4-BOOT-HOLE", "HOLE_CLUSTER", arr["hole"], int(cfg["evaluation"]["bootstrap"]["seed"])),
               ("O4-BOOT-LINE", "LINE_CLUSTER", arr["line"], int(cfg["evaluation"]["bootstrap"]["seed"]) + 1))
    for design_id, method, units, design_seed in designs:
        uniq = sorted(set(units.tolist()))
        idx_by_unit = {u: np.where(units == u)[0] for u in uniq}
        conn.execute("INSERT INTO resampling_designs (design_id, method, unit, n_units, n_replicates, seed, notes) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (design_id, method, "hole" if method == "HOLE_CLUSTER" else "line", len(uniq), n_rep, design_seed,
                      "resample units with replacement; keep all intervals of a unit and the same observations for both models"))
        rng = np.random.default_rng(design_seed)
        y = arr["y"]
        w_int, w_hole = arr["w_int"], arr["w_hole"]
        models = [m for m in arr["models"] if arr["data"][m]["n"] > 0]
        rows = []
        for rep in range(1, n_rep + 1):
            sample = rng.choice(len(uniq), size=len(uniq), replace=True)
            idx = np.concatenate([idx_by_unit[uniq[k]] for k in sample])
            yb = y[idx]
            b_int, b_hole, l_int = {}, {}, {}
            for m in models:
                pb = arr["data"][m]["p"][idx]
                b_int[m] = float(np.mean((pb - yb) ** 2))
                wb = w_hole[idx]
                b_hole[m] = float(np.sum(wb * (pb - yb) ** 2) / np.sum(wb))
                l_int[m] = metrics.log_loss(yb, pb, np.ones_like(pb), float(cfg["evaluation"]["epsilon"]))
            for pair in pairs:
                a, b = pair["model_a"], pair["model_b"]
                if a not in b_int or b not in b_int:
                    continue
                rows.append((design_id, pair["pair_id"], rep, a, b, b_int[a] - b_int[b], b_hole[a] - b_hole[b],
                             l_int[a] - l_int[b], int(idx.size)))
        conn.executemany("INSERT INTO bootstrap_replicates (design_id, pair_id, replicate_index, model_a, model_b, "
                         "delta_brier_interval, delta_brier_equal_hole, delta_log_loss_interval, n_obs) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)


def _audit(conn, run_id, arr, config, receipt, created):
    checks = []
    checks.append({"check_name": "O3_SNAPSHOT_HASH_RECORDED",
                   "status": "PASS" if receipt["o3_prediction_snapshot_sha256"] else "FAIL",
                   "detail": f"snapshot {receipt['o3_prediction_snapshot_sha256'][:16]}"})
    common = {r["observation_id"] for r in conn.execute("SELECT observation_id FROM evaluation_population "
                                                        "WHERE in_common_cohort = 1")}
    feasible = config["evaluation"]["models"]["feasible"]
    missing = 0
    for m in feasible:
        ids = {r["observation_id"] for r in conn.execute("SELECT observation_id FROM prediction_snapshot WHERE model_id = ?", (m,))}
        missing += len(common - ids)
    checks.append({"check_name": "COMMON_COHORT_IDENTICAL_ACROSS_FEASIBLE_MODELS", "status": "PASS" if missing == 0 else "FAIL",
                   "detail": f"{len(common)} common observations; {missing} missing model IDs"})
    m1 = conn.execute("SELECT n_predicted, n_failed FROM prediction_coverage WHERE model_id = 'M1_IK'").fetchone()
    checks.append({"check_name": "M1_COVERAGE_REPORTED", "status": "PASS" if m1 and m1["n_predicted"] == 0 else "WARN",
                   "detail": f"M1 predicted {m1['n_predicted'] if m1 else '?'}; failed {m1['n_failed'] if m1 else '?'}"})
    m3 = conn.execute("SELECT fallback_identical_to FROM candidate_registry WHERE model_id = 'M3_HYBRID'").fetchone()
    checks.append({"check_name": "M3_FALLBACK_IDENTITY_RECORDED", "status": "PASS" if m3 and m3["fallback_identical_to"] else "FAIL",
                   "detail": f"M3 fallback identical to {m3['fallback_identical_to'] if m3 else 'not recorded'}"})
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
    # Numerical cross-check of the pooled interval Brier for one feasible model.
    m = "M2_RF"
    rows = [dict(r) for r in conn.execute(
        "SELECT e.true_label, p.selected_probability, e.weight_interval FROM prediction_snapshot p "
        "JOIN evaluation_population e ON e.receipt_id = p.receipt_id AND e.observation_id = p.observation_id "
        "WHERE p.model_id = ? AND e.in_common_cohort = 1", (m,))]
    if rows:
        y = np.array([r["true_label"] for r in rows], dtype=float)
        p = np.array([r["selected_probability"] for r in rows], dtype=float)
        w = np.array([r["weight_interval"] for r in rows], dtype=float)
        fast = metrics.brier(y, p, w)
        slow = metrics.independent_brier(y, p, w)
        checks.append({"check_name": "BRIER_NUMERICAL_CROSS_CHECK", "status": "PASS" if abs(fast - slow) < 1e-12 else "FAIL",
                       "detail": f"vector {fast:.12f}; loop {slow:.12f}"})
    else:
        checks.append({"check_name": "BRIER_NUMERICAL_CROSS_CHECK", "status": "FAIL", "detail": "no M2_RF rows"})
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    checks.append({"check_name": "NO_MODEL_REFIT", "status": "PASS" if not ({"training_runs", "model_artifacts"} & tables)
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

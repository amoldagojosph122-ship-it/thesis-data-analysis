"""Fold-specific model training and out-of-fold prediction.

Order of work inside each outer fold: prevalence and logistic baselines; random forest and gradient boosting (M2);
selection of the single M2 trend by inner CV; indicator kriging (M1) with a training-only variogram; hybrid residual
model (M3) with an inner cross-fitted residual variogram, or its explicit ML-only fallback. Every training run,
hyperparameter trial, calibration, variogram fit, residual, prediction and failure is written to the Objective 3
database. Outer test labels are used only to record the true label beside a prediction.
"""

from __future__ import annotations

import importlib.metadata
import json
import platform
from pathlib import Path

import numpy as np

from kambale.objective_3 import models, kriging, variography
from kambale.objective_3.config import (O3_ARTIFACT_DIR, O3_DB_PATH, O3_CONFIG_PATH, PROJECT_ROOT, StopError,
                                        code_commit, load_config, sha256_file, sha256_text, utc_now)
from kambale.objective_3.db import connect_o3
from kambale.objective_3.features import load_observations

STANDARD_CANDIDATES = ("BASE_PREVALENCE", "BASE_LOGISTIC", "M2_RF", "M2_HGB")
M2_CANDIDATES = ("M2_RF", "M2_HGB")
FAMILY_OF = {"BASE_PREVALENCE": "BASE_PREVALENCE", "BASE_LOGISTIC": "BASE_LOGISTIC", "M2_RF": "M2_RF",
             "M2_HGB": "M2_HGB", "M1_IK": "M1_IK", "M3_HYBRID": "M3_HYBRID"}


def _json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(ids) -> str:
    return sha256_text("\n".join(str(int(i)) for i in sorted(int(x) for x in ids)))


def _software() -> dict:
    out = {"python": platform.python_version()}
    for pkg in ("numpy", "scipy", "scikit-learn"):
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            out[pkg] = "not installed"
    return out


def _membership(conn, split_plan_id: str) -> list[dict]:
    rows = conn.execute("SELECT fold_id, observation_id, role FROM split_membership WHERE split_plan_id = ? "
                        "ORDER BY fold_id, observation_id", (split_plan_id,)).fetchall()
    folds: dict[int, dict] = {}
    for r in rows:
        f = folds.setdefault(r["fold_id"], {"fold_id": r["fold_id"], "train": [], "test": []})
        f["train" if r["role"] == "TRAIN" else "test"].append(int(r["observation_id"]))
    return [folds[k] for k in sorted(folds)]


def _index_of(obs) -> dict:
    return {int(v): i for i, v in enumerate(obs.ids)}


def _write_run(conn, *, run_id, receipt_id, split_plan_id, fold_id, family_id, candidate_run_id, model_class,
               hyperparameters, inner_cv_method, inner_cv_folds, selection_metric, inner_score, inner_sd,
               train_y, train_idx, test_y, selected, threshold, threshold_source, status, reason, seed, created) -> int:
    return conn.execute(
        "INSERT INTO training_runs (run_id, receipt_id, split_plan_id, fold_id, family_id, candidate_run_id, model_class, "
        "hyperparameters_json, inner_cv_method, inner_cv_folds, selection_metric, inner_cv_score, inner_cv_score_sd, "
        "training_n, training_positive, training_negative, training_holes, training_lines, test_n, test_positive, "
        "test_negative, selected, threshold, threshold_source, status, reason, seed, created_utc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, receipt_id, split_plan_id, fold_id, family_id, candidate_run_id, model_class, _json(hyperparameters),
         inner_cv_method, inner_cv_folds, selection_metric, inner_score, inner_sd, int(train_idx.size),
         int(train_y.sum()), int(train_idx.size - train_y.sum()), 0, 0, int(test_y.size), int(test_y.sum()),
         int(test_y.size - test_y.sum()), int(selected), float(threshold), threshold_source, status, reason, int(seed),
         created)).lastrowid


def _update_run_counts(conn, training_run_id: int, train_hole, train_line) -> None:
    conn.execute("UPDATE training_runs SET training_holes = ?, training_lines = ? WHERE training_run_id = ?",
                 (int(np.unique(train_hole).size), int(np.unique(train_line).size), training_run_id))


def _write_manifest(conn, training_run_id: int, obs, idx) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO training_sample_manifest (training_run_id, observation_id, hole_id, line_code, true_label, "
        "role) VALUES (?, ?, ?, ?, ?, 'TRAIN')",
        [(training_run_id, int(obs.ids[i]), obs.holes[int(obs.hole[i])], obs.lines[int(obs.line[i])], int(obs.y[i]))
         for i in idx])


def _write_trials(conn, training_run_id: int, candidate: str, trials: list[dict], selected_trial: dict | None) -> None:
    ranked = sorted([t for t in trials if t["status"] == "COMPLETED"], key=lambda t: t["mean"])
    rank_of = {id(t): k + 1 for k, t in enumerate(ranked)}
    for t in trials:
        conn.execute(
            "INSERT INTO hyperparameter_trials (training_run_id, candidate_run_id, hyperparameters_json, inner_cv_score, "
            "inner_cv_score_sd, inner_fold_scores_json, rank, selected, status, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (training_run_id, candidate, _json(t["params"]), t.get("mean"), t.get("sd"), _json(t.get("scores", [])),
             rank_of.get(id(t)), 1 if selected_trial is not None and t is selected_trial else 0, t["status"],
             t["reason"]))


def _write_artifact(conn, training_run_id: int, candidate: str, fold_id: int, payload: dict, created: str) -> int:
    O3_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = O3_ARTIFACT_DIR / f"{candidate}_fold{fold_id}.json"
    body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(body, encoding="utf-8")
    sha = sha256_file(path)
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    artifact_id = conn.execute(
        "INSERT INTO model_artifacts (training_run_id, artifact_path, artifact_sha256, artifact_kind, bytes, created_utc) "
        "VALUES (?, ?, ?, 'MODEL_PARAMETER_RECORD', ?, ?)",
        (training_run_id, rel, sha, path.stat().st_size, created)).lastrowid
    conn.execute(
        "INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_id, sha256, bytes, created_utc) "
        "VALUES (?, 'MODEL_ARTIFACT', ?, ?, ?, ?)",
        (rel, str(artifact_id), sha, path.stat().st_size, created))
    return artifact_id


def _write_predictions(conn, *, training_run_id, split_plan_id, fold_id, obs, idx, family_id, candidate, p_raw, p_cal,
                       clip_raw, clip_cal, threshold, threshold_source, created, geometry_status, label_rule_id) -> None:
    conn.executemany(
        "INSERT INTO predictions_oof (training_run_id, split_plan_id, fold_id, observation_id, hole_id, line_code, "
        "family_id, candidate_run_id, true_label, p_raw, p_calibrated, clipped_raw, clipped_calibrated, predicted_class, "
        "threshold, threshold_source, geometry_status, label_rule_id, created_utc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(training_run_id, split_plan_id, fold_id, int(obs.ids[i]), obs.holes[int(obs.hole[i])],
          obs.lines[int(obs.line[i])], family_id, candidate, int(obs.y[i]), float(p_raw[k]), float(p_cal[k]),
          int(clip_raw[k]), int(clip_cal[k]), 1 if float(p_cal[k]) >= float(threshold) else 0, float(threshold),
          threshold_source, geometry_status, label_rule_id, created) for k, i in enumerate(idx)])


def _write_lag_bins(conn, training_run_id: int, family_id: str, bins: dict) -> None:
    conn.executemany(
        "INSERT INTO training_lag_bins (training_run_id, family_id, bin_index, lag_from_m, lag_to_m, lag_centre_m, "
        "n_pairs, n_independent_hole_pairs, gamma, supported) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(training_run_id, family_id, k, float(bins["edges"][k]), float(bins["edges"][k + 1]),
          float(bins["centres"][k]), int(bins["n_pairs"][k]), int(bins["n_hole_pairs"][k]),
          None if not np.isfinite(bins["gamma"][k]) else float(bins["gamma"][k]),
          1 if bins["supported"][k] else 0) for k in range(len(bins["centres"]))])


def _write_failures(conn, *, split_plan_id, fold_id, obs, idx, family_id, candidate, training_run_id, reason,
                    created) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO prediction_failures (split_plan_id, fold_id, observation_id, family_id, candidate_run_id, "
        "training_run_id, reason, created_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(split_plan_id, fold_id, int(obs.ids[i]), family_id, candidate, training_run_id, reason, created) for i in idx])


def _standard_candidate(conn, *, run_id, receipt_id, split_plan_id, fold_id, obs, train_idx, test_idx, candidate,
                        config, created, geometry_status, label_rule_id, seed) -> dict:
    """Inner tuning, outer refit, optional Platt calibration and OOF predictions for one candidate family."""
    y_train, y_test = obs.y[train_idx], obs.y[test_idx]
    X_train, X_test = obs.X[train_idx], obs.X[test_idx]
    eps = float(config["calibration"]["clip_epsilon"])
    trials = []
    for params in models.grid(candidate, config):
        cv = models.inner_cv(X_train, y_train, obs.hole[train_idx], candidate, params, config, seed)
        trials.append({"params": params, **cv})
    selection = models.select_trials(trials)
    if selection["status"] != "COMPLETED":
        training_run_id = _write_run(
            conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id,
            family_id=FAMILY_OF[candidate], candidate_run_id=candidate,
            model_class={"BASE_PREVALENCE": "TrainingPrevalence", "BASE_LOGISTIC": "LogisticRegression",
                         "M2_RF": "RandomForestClassifier", "M2_HGB": "HistGradientBoostingClassifier"}[candidate],
            hyperparameters={}, inner_cv_method=config["inner_cv"]["method"], inner_cv_folds=config["inner_cv"]["n_folds"],
            selection_metric=config["inner_cv"]["selection_metric"], inner_score=None, inner_sd=None,
            train_y=y_train, train_idx=train_idx, test_y=y_test, selected=0, threshold=0.5,
            threshold_source="NOT_SELECTED", status="FAILED", reason=selection["reason"], seed=seed, created=created)
        _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
        _write_trials(conn, training_run_id, candidate, trials, None)
        _write_manifest(conn, training_run_id, obs, train_idx)
        _write_failures(conn, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs, idx=test_idx,
                        family_id=FAMILY_OF[candidate], candidate=candidate, training_run_id=training_run_id,
                        reason=selection["reason"], created=created)
        return {"training_run_id": training_run_id, "candidate": candidate, "status": "FAILED",
                "inner_score": None, "params": None, "p_raw": None, "p_cal": None}

    chosen = selection["trial"]
    params = chosen["params"]
    estimator = models.make_estimator(candidate, params, config, seed)
    estimator.fit(X_train, y_train)
    raw_test = np.clip(models.predict_positive(estimator, X_test), eps, 1.0 - eps)
    raw_inner = np.clip(chosen["p"], eps, 1.0 - eps)
    thr = models.youden_threshold(y_train, raw_inner, config["inner_cv"]["threshold_grid"], eps)

    apply_calibration = candidate in config["calibration"]["apply_to"]
    cal = (models.platt_fit(y_train, raw_inner, config) if apply_calibration else
           {"status": "SKIPPED", "method": "NONE", "n_inner": int(y_train.size), "inner_positive": int(y_train.sum()),
            "inner_negative": int(y_train.size - y_train.sum()), "intercept": None, "slope": None,
            "clip_epsilon": eps, "reason": "calibration is not configured for this family"})
    calibrated_test = (models.platt_apply(raw_test, cal, eps) if cal["status"] == "FITTED" else raw_test.copy())
    clip_raw = (raw_test <= eps) | (raw_test >= 1.0 - eps)
    # Platt output is inside (eps, 1-eps) by construction; count a scientific clip only when it is absent and raw is 0/1.
    clip_cal = np.zeros(raw_test.shape[0], dtype=bool) if cal["status"] == "FITTED" else clip_raw.copy()

    training_run_id = _write_run(
        conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id,
        family_id=FAMILY_OF[candidate], candidate_run_id=candidate,
        model_class={"BASE_PREVALENCE": "TrainingPrevalence", "BASE_LOGISTIC": "LogisticRegression",
                     "M2_RF": "RandomForestClassifier", "M2_HGB": "HistGradientBoostingClassifier"}[candidate],
        hyperparameters=params, inner_cv_method=config["inner_cv"]["method"],
        inner_cv_folds=config["inner_cv"]["n_folds"], selection_metric=config["inner_cv"]["selection_metric"],
        inner_score=chosen["mean"], inner_sd=chosen["sd"], train_y=y_train, train_idx=train_idx, test_y=y_test,
        selected=0, threshold=thr["threshold"], threshold_source=thr["source"], status="COMPLETED",
        reason=f"{len(trials)} inner trials; {selection['reason']}", seed=seed, created=created)
    _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
    _write_trials(conn, training_run_id, candidate, trials, chosen)
    _write_manifest(conn, training_run_id, obs, train_idx)
    conn.execute(
        "INSERT INTO calibration_fits (training_run_id, method, n_inner, inner_positive, inner_negative, intercept, slope, "
        "clip_epsilon, status, reason, created_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (training_run_id, cal["method"], cal["n_inner"], cal["inner_positive"], cal["inner_negative"],
         cal.get("intercept"), cal.get("slope"), eps, cal["status"], cal["reason"], created))
    _write_predictions(conn, training_run_id=training_run_id, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs,
                       idx=test_idx, family_id=FAMILY_OF[candidate], candidate=candidate, p_raw=raw_test,
                       p_cal=calibrated_test, clip_raw=clip_raw, clip_cal=clip_cal, threshold=thr["threshold"],
                       threshold_source=thr["source"], created=created, geometry_status=geometry_status,
                       label_rule_id=label_rule_id)
    _write_artifact(conn, training_run_id, candidate, fold_id, {
        "candidate_run_id": candidate, "family_id": FAMILY_OF[candidate], "fold_id": fold_id,
        "model_class": {"BASE_PREVALENCE": "TrainingPrevalence", "BASE_LOGISTIC": "LogisticRegression",
                        "M2_RF": "RandomForestClassifier", "M2_HGB": "HistGradientBoostingClassifier"}[candidate],
        "hyperparameters": params, "inner_cv_score": chosen["mean"], "inner_cv_score_sd": chosen["sd"],
        "selection_metric": config["inner_cv"]["selection_metric"], "threshold": thr,
        "calibration": {k: cal[k] for k in ("method", "status", "intercept", "slope", "reason")},
        "feature_names": obs.feature_names, "training_n": int(train_idx.size),
        "training_id_digest": _digest(obs.ids[train_idx]), "seed": seed, "software": _software(),
    }, created)
    return {"training_run_id": training_run_id, "candidate": candidate, "status": "COMPLETED",
            "inner_score": chosen["mean"], "params": params, "p_raw": raw_test, "p_cal": calibrated_test,
            "clip_raw": clip_raw, "clip_cal": clip_cal, "threshold": thr["threshold"],
            "threshold_source": thr["source"], "calibration": cal}


def _m1(conn, *, run_id, receipt_id, split_plan_id, fold_id, obs, train_idx, test_idx, config, created,
        geometry_status, label_rule_id, seed) -> dict:
    y_train = obs.y[train_idx]
    fit = variography.fit_family(y_train.astype(np.float64), obs.X[train_idx], obs.hole[train_idx],
                                 obs.line[train_idx], config)
    p_train = float(y_train.mean())
    status = "COMPLETED" if fit["chosen_model"] else "NOT_ESTIMABLE"
    reason = fit["reason"]
    training_run_id = _write_run(
        conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id, family_id="M1_IK",
        candidate_run_id="M1_IK", model_class="SimpleIndicatorKriging", hyperparameters={
            "variogram": {m: {"status": fit["fits"][m]["status"], "params": fit["fits"][m]["params"],
                              "stability": fit["stability"][m]["status"]} for m in config["variogram"]["models"]},
            "chosen_model": fit["chosen_model"]}, inner_cv_method="TRAINING_ONLY_VARIOGRAM", inner_cv_folds=0,
        selection_metric="VARIOGRAM_IDENTIFIABILITY", inner_score=None, inner_sd=None, train_y=y_train,
        train_idx=train_idx, test_y=obs.y[test_idx], selected=0, threshold=(p_train if 0 < p_train < 1 else 0.5),
        threshold_source="TRAINING_PREVALENCE", status=status, reason=reason, seed=seed, created=created)
    _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
    _write_manifest(conn, training_run_id, obs, train_idx)
    _write_lag_bins(conn, training_run_id, "M1_IK", fit["bins"])
    for model in config["variogram"]["models"]:
        f = fit["fits"][model]
        st = fit["stability"][model]
        conn.execute(
            "INSERT INTO variogram_training_fits (training_run_id, fold_id, family_id, direction_id, model, fit_status, "
            "objective_value, n_bins_used, admissible, marginal_variance, nugget, structured_sill, range_m, "
            "stability_status, stable, reason, created_utc) VALUES (?, ?, 'M1_IK', 'LATERAL_BETWEEN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (training_run_id, fold_id, model, f["status"], f.get("objective"), f["n_bins"],
             None if f.get("admissible") is None else int(f["admissible"]), fit["variance"],
             f["params"][0] if f["params"] and f["status"] == "FITTED" else None,
             f["params"][1] if f["params"] and f["status"] == "FITTED" else None,
             f["params"][2] if f["params"] and f["status"] == "FITTED" else None, st["status"],
             1 if st["status"] == "STABLE" else 0, f"{f['reason']}; stability: {st['reason']}", created))
    if fit["chosen_model"] is None:
        _write_failures(conn, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs, idx=test_idx, family_id="M1_IK",
                        candidate="M1_IK", training_run_id=training_run_id, reason=reason, created=created)
        p = None
    else:
        k = kriging.simple_kriging(obs.X[train_idx], y_train.astype(np.float64), obs.X[test_idx],
                                   fit["chosen_model"], fit["chosen_params"], config, mean=p_train)
        p = k["p"]
        thr = p_train if 0 < p_train < 1 else 0.5
        _write_predictions(conn, training_run_id=training_run_id, split_plan_id=split_plan_id, fold_id=fold_id,
                           obs=obs, idx=test_idx, family_id="M1_IK", candidate="M1_IK", p_raw=p, p_cal=p,
                           clip_raw=k["clipped"], clip_cal=k["clipped"], threshold=thr,
                           threshold_source="TRAINING_PREVALENCE", created=created, geometry_status=geometry_status,
                           label_rule_id=label_rule_id)
    _write_artifact(conn, training_run_id, "M1_IK", fold_id, {
        "candidate_run_id": "M1_IK", "fold_id": fold_id, "variogram": {
            m: {"status": fit["fits"][m]["status"], "params": fit["fits"][m]["params"],
                "objective": fit["fits"][m]["objective"], "stability": fit["stability"][m]["status"]}
            for m in config["variogram"]["models"]}, "chosen_model": fit["chosen_model"],
        "chosen_params": fit["chosen_params"], "kriging": config["variogram"]["kriging"],
        "feature_names": obs.feature_names, "training_n": int(train_idx.size),
        "training_id_digest": _digest(obs.ids[train_idx]), "seed": seed, "software": _software(),
    }, created)
    return {"training_run_id": training_run_id, "status": status, "chosen_model": fit["chosen_model"],
            "params": fit["chosen_params"], "p": p}


def _m3(conn, *, run_id, receipt_id, split_plan_id, fold_id, obs, train_idx, test_idx, config, created,
        geometry_status, label_rule_id, seed, selected_m2: dict | None) -> dict:
    y_train, y_test = obs.y[train_idx], obs.y[test_idx]
    X_train, X_test = obs.X[train_idx], obs.X[test_idx]
    eps = float(config["calibration"]["clip_epsilon"])
    if selected_m2 is None or selected_m2.get("status") != "COMPLETED":
        reason = "no M2 candidate completed in this fold"
        training_run_id = _write_run(
            conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id,
            family_id="M3_HYBRID", candidate_run_id="M3_HYBRID", model_class="HybridResidualKriging",
            hyperparameters={}, inner_cv_method="INNER_GROUP_K_FOLD_BY_HOLE", inner_cv_folds=0,
            selection_metric="NONE", inner_score=None, inner_sd=None, train_y=y_train, train_idx=train_idx,
            test_y=y_test, selected=0, threshold=0.5, threshold_source="NOT_SELECTED", status="FAILED",
            reason=reason, seed=seed, created=created)
        _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
        _write_manifest(conn, training_run_id, obs, train_idx)
        _write_failures(conn, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs, idx=test_idx, family_id="M3_HYBRID",
                        candidate="M3_HYBRID", training_run_id=training_run_id, reason=reason, created=created)
        return {"training_run_id": training_run_id, "status": "FAILED"}

    candidate = selected_m2["candidate"]
    params = selected_m2["params"]
    # Inner cross-fitted trend on the outer training fold only.
    inner_splits = models.inner_folds(obs.hole[train_idx], config["inner_cv"]["n_folds"], seed)
    trend_inner = np.full(train_idx.size, np.nan, dtype=np.float64)
    for tr, te in inner_splits:
        est = models.make_estimator(candidate, params, config, seed)
        est.fit(X_train[tr], y_train[tr])
        trend_inner[te] = models.predict_positive(est, X_train[te])
    if not np.all(np.isfinite(trend_inner)):
        raise StopError("M3 inner cross-fitted trend is incomplete")
    residuals = y_train.astype(np.float64) - trend_inner

    fit = variography.fit_family(residuals, X_train, obs.hole[train_idx], obs.line[train_idx], config)
    hybrid_supported = fit["chosen_model"] is not None
    fallback_status = "HYBRID_USED" if hybrid_supported else "FALLBACK_ML_ONLY"
    status = "COMPLETED" if hybrid_supported else "FALLBACK"
    reason = (f"residual variogram {fit['chosen_model']} supported and stable" if hybrid_supported else
              f"residual covariance unsupported: {fit['reason']}; ML-only fallback")
    training_run_id = _write_run(
        conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id, family_id="M3_HYBRID",
        candidate_run_id="M3_HYBRID", model_class="HybridResidualKriging", hyperparameters={
            "trend_candidate": candidate, "trend_hyperparameters": params,
            "residual_variogram": {m: {"status": fit["fits"][m]["status"], "params": fit["fits"][m]["params"],
                                        "stability": fit["stability"][m]["status"]} for m in config["variogram"]["models"]},
            "chosen_model": fit["chosen_model"], "fallback": fallback_status},
        inner_cv_method="INNER_GROUP_K_FOLD_BY_HOLE", inner_cv_folds=len(inner_splits),
        selection_metric="RESIDUAL_VARIOGRAM_IDENTIFIABILITY", inner_score=selected_m2.get("inner_score"), inner_sd=None,
        train_y=y_train, train_idx=train_idx, test_y=y_test, selected=0,
        threshold=selected_m2["threshold"], threshold_source="M2_SELECTED_THRESHOLD", status=status, reason=reason,
        seed=seed, created=created)
    _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
    _write_manifest(conn, training_run_id, obs, train_idx)
    _write_lag_bins(conn, training_run_id, "M3_HYBRID", fit["bins"])
    for model in config["variogram"]["models"]:
        f = fit["fits"][model]
        st = fit["stability"][model]
        conn.execute(
            "INSERT INTO hybrid_residual_variogram (training_run_id, fold_id, model, fit_status, objective_value, "
            "n_bins_used, admissible, residual_variance, nugget, structured_sill, range_m, stability_status, supported, "
            "fallback_status, reason, created_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (training_run_id, fold_id, model, f["status"], f.get("objective"), f["n_bins"],
             None if f.get("admissible") is None else int(f["admissible"]), fit["variance"],
             f["params"][0] if f["params"] and f["status"] == "FITTED" else None,
             f["params"][1] if f["params"] and f["status"] == "FITTED" else None,
             f["params"][2] if f["params"] and f["status"] == "FITTED" else None, st["status"],
             1 if (f["status"] == "FITTED" and st["status"] == "STABLE") else 0, fallback_status,
             f"{f['reason']}; stability: {st['reason']}", created))
    if hybrid_supported:
        est = models.make_estimator(candidate, params, config, seed)
        est.fit(X_train, y_train)
        trend_test = models.predict_positive(est, X_test)
        k = kriging.simple_kriging(X_train, residuals, X_test, fit["chosen_model"], fit["chosen_params"], config,
                                   mean=0.0)
        combined = trend_test + k["p"]
        clipped = (combined < 0.0) | (combined > 1.0) | k["clipped"]
        p = np.clip(combined, 0.0, 1.0)
        clip_raw = clip_cal = clipped
        p_raw = p
    else:
        p_raw = selected_m2["p_cal"].copy()
        p = p_raw.copy()
        clip_raw = selected_m2["clip_cal"].copy()
        clip_cal = clip_raw.copy()
        trend_test = np.full(test_idx.size, np.nan)
    _write_predictions(conn, training_run_id=training_run_id, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs,
                       idx=test_idx, family_id="M3_HYBRID", candidate="M3_HYBRID", p_raw=p_raw, p_cal=p,
                       clip_raw=clip_raw, clip_cal=clip_cal, threshold=selected_m2["threshold"],
                       threshold_source="M2_SELECTED_THRESHOLD", created=created, geometry_status=geometry_status,
                       label_rule_id=label_rule_id)
    conn.executemany(
        "INSERT OR IGNORE INTO residual_diagnostics (training_run_id, observation_id, role, fold_id, trend_probability, "
        "residual, created_utc) VALUES (?, ?, 'INNER_OOF', ?, ?, ?, ?)",
        [(training_run_id, int(obs.ids[i]), fold_id, float(trend_inner[k]), float(residuals[k]), created)
         for k, i in enumerate(train_idx)])
    conn.executemany(
        "INSERT OR IGNORE INTO residual_diagnostics (training_run_id, observation_id, role, fold_id, trend_probability, "
        "residual, created_utc) VALUES (?, ?, 'TEST', ?, ?, ?, ?)",
        [(training_run_id, int(obs.ids[i]), fold_id,
          float(trend_test[k]) if np.isfinite(trend_test[k]) else float(p[k]),
          float(y_test[k] - p[k]), created) for k, i in enumerate(test_idx)])
    _write_artifact(conn, training_run_id, "M3_HYBRID", fold_id, {
        "candidate_run_id": "M3_HYBRID", "fold_id": fold_id, "trend_candidate": candidate,
        "trend_hyperparameters": params, "residual_variogram": {
            m: {"status": fit["fits"][m]["status"], "params": fit["fits"][m]["params"],
                "objective": fit["fits"][m]["objective"], "stability": fit["stability"][m]["status"]}
            for m in config["variogram"]["models"]}, "chosen_model": fit["chosen_model"],
        "chosen_params": fit["chosen_params"], "fallback": fallback_status,
        "feature_names": obs.feature_names, "training_n": int(train_idx.size),
        "training_id_digest": _digest(obs.ids[train_idx]), "seed": seed, "software": _software(),
    }, created)
    return {"training_run_id": training_run_id, "status": status, "fallback_status": fallback_status,
            "chosen_model": fit["chosen_model"], "params": fit["chosen_params"], "p": p}


def _leakage_audit(conn, run_id: int, split_plan_id: str, created: str) -> list[dict]:
    checks = []
    train_runs = conn.execute("SELECT training_run_id, fold_id, family_id FROM training_runs WHERE split_plan_id = ?",
                              (split_plan_id,)).fetchall()
    bad_manifest = 0
    for r in train_runs:
        overlap = conn.execute(
            "SELECT COUNT(*) FROM training_sample_manifest m JOIN split_membership s "
            "ON s.split_plan_id = ? AND s.fold_id = ? AND s.observation_id = m.observation_id AND s.role = 'TEST' "
            "WHERE m.training_run_id = ?", (split_plan_id, r["fold_id"], r["training_run_id"])).fetchone()[0]
        bad_manifest += overlap
    checks.append({"check_name": "OUTER_TEST_NOT_IN_TRAINING_MANIFEST", "status": "PASS" if bad_manifest == 0 else "FAIL",
                   "detail": f"{bad_manifest} test observations appear in a training manifest of the same fold"})
    bad_pred = conn.execute(
        "SELECT COUNT(*) FROM predictions_oof p JOIN split_membership s "
        "ON s.split_plan_id = p.split_plan_id AND s.fold_id = p.fold_id AND s.observation_id = p.observation_id "
        "WHERE p.split_plan_id = ? AND s.role <> 'TEST'", (split_plan_id,)).fetchone()[0]
    checks.append({"check_name": "PREDICTIONS_ARE_TEST_MEMBERS", "status": "PASS" if bad_pred == 0 else "FAIL",
                   "detail": f"{bad_pred} predictions are not test members of their fold"})
    bad_features = conn.execute(
        "SELECT COUNT(*) FROM feature_registry WHERE name IN ('easting_m','northing_m','z_relative_m') "
        "AND (available_at_prediction <> 1 OR leakage_designation <> 'SAFE')").fetchone()[0]
    checks.append({"check_name": "PREDICTORS_SAFE_AND_AVAILABLE", "status": "PASS" if bad_features == 0 else "FAIL",
                   "detail": f"{bad_features} deployed predictors are not SAFE and available"})
    bad_var = conn.execute(
        "SELECT COUNT(*) FROM variogram_training_fits v JOIN training_runs t ON t.training_run_id = v.training_run_id "
        "WHERE t.split_plan_id = ? AND t.fold_id <> v.fold_id", (split_plan_id,)).fetchone()[0]
    bad_var += conn.execute(
        "SELECT COUNT(*) FROM hybrid_residual_variogram v JOIN training_runs t ON t.training_run_id = v.training_run_id "
        "WHERE t.split_plan_id = ? AND t.fold_id <> v.fold_id", (split_plan_id,)).fetchone()[0]
    checks.append({"check_name": "VARIOGRAMS_BELONG_TO_THEIR_TRAINING_FOLD", "status": "PASS" if bad_var == 0 else "FAIL",
                   "detail": f"{bad_var} variogram rows reference a different fold"})
    bad_cal = conn.execute(
        "SELECT COUNT(*) FROM calibration_fits c JOIN training_runs t ON t.training_run_id = c.training_run_id "
        "WHERE t.split_plan_id = ? AND c.n_inner > t.training_n", (split_plan_id,)).fetchone()[0]
    checks.append({"check_name": "CALIBRATION_USES_INNER_DATA_ONLY", "status": "PASS" if bad_cal == 0 else "FAIL",
                   "detail": f"{bad_cal} calibration fits use more rows than the outer training fold"})
    full = conn.execute("SELECT COUNT(*) FROM final_refits WHERE status = 'RUN'").fetchone()[0]
    checks.append({"check_name": "NO_FINAL_FULL_FIT_IN_OOF", "status": "PASS" if full == 0 else "FAIL",
                   "detail": f"{full} final full-data refits exist before Objective 4 selection"})
    for c in checks:
        conn.execute("INSERT INTO leakage_audit_log (run_id, check_name, status, detail, created_utc) "
                     "VALUES (?, ?, ?, ?, ?)", (run_id, c["check_name"], c["status"], c["detail"], created))
    return checks


def run(receipt_id: int | None = None, config_path=None, o3_path=None) -> dict:
    config, config_sha = load_config(config_path or O3_CONFIG_PATH)
    conn = connect_o3(o3_path or O3_DB_PATH)
    try:
        if receipt_id is None:
            row = conn.execute("SELECT receipt_id FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
            if row is None:
                raise StopError("no receipt: run the import first")
            receipt_id = row["receipt_id"]
        receipt = conn.execute("SELECT * FROM source_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
        split_plan_id = config["splits"]["primary"]["split_plan_id"]
        if conn.execute("SELECT COUNT(*) FROM spatial_split_plans WHERE split_plan_id = ?",
                        (split_plan_id,)).fetchone()[0] == 0:
            raise StopError("split plan is not frozen: run the splits stage first")
        if conn.execute("SELECT COUNT(*) FROM training_runs WHERE split_plan_id = ?", (split_plan_id,)).fetchone()[0]:
            raise StopError("training rows already exist for this split plan; a new receipt is needed to re-run")
        obs = load_observations(conn, receipt_id, config)
        # One transaction for every training write: autocommit per row is prohibitively slow, and a partial fold must
        # not survive a failure. All later reads in this function use the same connection and see the uncommitted rows.
        conn.execute("BEGIN IMMEDIATE")
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, split_plan_id, started_utc, "
            "status, code_commit, note) VALUES ('TRAIN', ?, ?, ?, ?, ?, 'RUNNING', ?, 'outer line folds; inner whole-hole tuning')",
            (config["config_version"], config_sha, receipt_id, split_plan_id, utc_now(), code_commit())).lastrowid
        seed = int(config["seeds"][0])
        created = utc_now()
        index = _index_of(obs)
        folds = _membership(conn, split_plan_id)
        fold_results = []
        for fold in folds:
            train_idx = np.array([index[i] for i in fold["train"]], dtype=np.int64)
            test_idx = np.array([index[i] for i in fold["test"]], dtype=np.int64)
            outcome = {}
            for candidate in STANDARD_CANDIDATES:
                outcome[candidate] = _standard_candidate(
                    conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold["fold_id"],
                    obs=obs, train_idx=train_idx, test_idx=test_idx, candidate=candidate, config=config, created=created,
                    geometry_status=receipt["geometry_status"], label_rule_id=receipt["label_rule_id"], seed=seed)
            usable = [outcome[c] for c in M2_CANDIDATES if outcome[c]["status"] == "COMPLETED"]
            selected_m2 = min(usable, key=lambda r: r["inner_score"]) if usable else None
            if selected_m2 is not None:
                conn.execute("UPDATE training_runs SET selected = 1 WHERE training_run_id = ?",
                             (selected_m2["training_run_id"],))
                selected_m2["selected"] = 1
            outcome["M1_IK"] = _m1(
                conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold["fold_id"],
                obs=obs, train_idx=train_idx, test_idx=test_idx, config=config, created=created,
                geometry_status=receipt["geometry_status"], label_rule_id=receipt["label_rule_id"], seed=seed)
            outcome["M3_HYBRID"] = _m3(
                conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold["fold_id"],
                obs=obs, train_idx=train_idx, test_idx=test_idx, config=config, created=created,
                geometry_status=receipt["geometry_status"], label_rule_id=receipt["label_rule_id"], seed=seed,
                selected_m2=selected_m2)
            fold_results.append({"fold_id": fold["fold_id"], "n_train": int(train_idx.size), "n_test": int(test_idx.size),
                                 "selected_m2": selected_m2["candidate"] if selected_m2 else None,
                                 "m2_inner_score": selected_m2["inner_score"] if selected_m2 else None,
                                 "m1_status": outcome["M1_IK"]["status"],
                                 "m3_status": outcome["M3_HYBRID"]["status"],
                                 "m3_fallback": outcome["M3_HYBRID"].get("fallback_status")})
        conn.execute(
            "INSERT OR IGNORE INTO final_refits (family_id, candidate_run_id, selection_decision_id, status, reason, "
            "created_utc) VALUES ('M3_HYBRID', 'TO_BE_SELECTED_BY_O4', NULL, 'PENDING_O4', "
            "'Objective 4 locks model selection; Objective 3 does not refit on all data', ?)", (created,))
        audits = _leakage_audit(conn, run_id, split_plan_id, created)
        conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ? WHERE run_id = ?", (utc_now(), run_id))
        conn.execute("COMMIT")
        return {"run_id": run_id, "receipt_id": receipt_id, "split_plan_id": split_plan_id, "folds": fold_results,
                "leakage_audits": audits}
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

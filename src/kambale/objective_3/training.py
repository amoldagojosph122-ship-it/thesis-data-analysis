"""Fold-specific model training and out-of-fold prediction for every split plan (both validation tiers).

Order of work inside each outer fold: the TREND candidates (prevalence, logistic, random forest, gradient boosting); the
TREND_WF candidates (the same estimators with the fold-safe weathering-front column); the two inner-selected composites
M2_SEL and M2_WF_SEL; indicator kriging (M1) with an inner-CV-selected covariance; and the hybrid (M3) on the calibrated
M2_WF_SEL trend with an inner-CV-selected residual covariance. Every training run, hyperparameter trial, calibration,
variogram or covariance record, residual, prediction and failure is written to the Objective 3 database. Outer test labels
are used only to record the true label beside a prediction and in the leakage audit's record comparison.
"""

from __future__ import annotations

import importlib.metadata
import json
import platform

import numpy as np
from sklearn.metrics import log_loss

from kambale.objective_3 import kriging, models, weathering_front
from kambale.objective_3.config import (O3_ARTIFACT_DIR, O3_DB_PATH, O3_CONFIG_PATH, PROJECT_ROOT, StopError,
                                        code_commit, load_config, sha256_file, sha256_text, utc_now)
from kambale.objective_3.db import connect_o3
from kambale.objective_3.features import load_observations, predictor_sets

M1_NAME = "M1_IK"
M3_NAME = "M3_HYBRID"
COMPOSITE_NAMES = ("M2_SEL", "M2_WF_SEL")


def _json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=float)


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


def covariance_label(cov: dict) -> str:
    if kriging.is_pure(cov):
        return "PURE_NUGGET"
    return f"exponential range {cov['range_m']:g} m, nugget fraction {cov['nugget_fraction']:g}"


def _candidate_plan(config: dict) -> dict:
    m = config["models"]
    plain = [m["prevalence"]["candidate_run_id"], m["logistic"]["candidate_run_id"],
             m["random_forest"]["candidate_run_id"], m["gradient_boosting"]["candidate_run_id"]]
    wf = [v["candidate_run_id"] for v in m["weathering_variants"]]
    composites = {c["candidate_run_id"]: list(c["choose_from"]) for c in m["selected_composites"]}
    if tuple(composites) != COMPOSITE_NAMES:
        raise StopError(f"the selected composites must be {COMPOSITE_NAMES}")
    return {"plain": plain, "wf": wf, "composites": composites}


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
    ranked = sorted([t for t in trials if t["status"] == "COMPLETED" and t.get("mean") is not None],
                    key=lambda t: t["mean"])
    rank_of = {id(t): k + 1 for k, t in enumerate(ranked)}
    for t in trials:
        conn.execute(
            "INSERT INTO hyperparameter_trials (training_run_id, candidate_run_id, hyperparameters_json, inner_cv_score, "
            "inner_cv_score_sd, inner_fold_scores_json, rank, selected, status, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (training_run_id, candidate, _json(t["params"]), t.get("mean"), t.get("sd"), _json(t.get("scores", [])),
             rank_of.get(id(t)), 1 if selected_trial is not None and t is selected_trial else 0, t["status"],
             t["reason"]))


def _write_artifact(conn, training_run_id: int, candidate: str, split_plan_id: str, fold_id: int, payload: dict,
                    created: str) -> int:
    O3_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = O3_ARTIFACT_DIR / f"{candidate}_{split_plan_id}_fold{fold_id}.json"
    body = json.dumps(payload, indent=2, sort_keys=True, default=float) + "\n"
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


def _write_failures(conn, *, split_plan_id, fold_id, obs, idx, family_id, candidate, training_run_id, reason,
                    created) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO prediction_failures (split_plan_id, fold_id, observation_id, family_id, candidate_run_id, "
        "training_run_id, reason, created_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(split_plan_id, fold_id, int(obs.ids[i]), family_id, candidate, training_run_id, reason, created) for i in idx])


def _failed_candidate(conn, *, run_id, receipt_id, split_plan_id, fold_id, obs, train_idx, test_idx, candidate,
                      model_class, config, created, seed, reason, trials, hyperparameters, geometry_status,
                      label_rule_id) -> dict:
    training_run_id = _write_run(
        conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id,
        family_id=candidate, candidate_run_id=candidate, model_class=model_class, hyperparameters=hyperparameters,
        inner_cv_method=config["inner_cv"]["method"], inner_cv_folds=config["inner_cv"]["n_folds"],
        selection_metric=config["inner_cv"]["selection_metric"], inner_score=None, inner_sd=None,
        train_y=obs.y[train_idx], train_idx=train_idx, test_y=obs.y[test_idx], selected=0, threshold=0.5,
        threshold_source="NOT_SELECTED", status="FAILED", reason=reason, seed=seed, created=created)
    _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
    if trials:
        _write_trials(conn, training_run_id, candidate, trials, None)
    _write_manifest(conn, training_run_id, obs, train_idx)
    _write_failures(conn, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs, idx=test_idx, family_id=candidate,
                    candidate=candidate, training_run_id=training_run_id, reason=reason, created=created)
    return {"training_run_id": training_run_id, "candidate": candidate, "status": "FAILED", "inner_score": None,
            "inner_sd": None, "params": None, "p_raw": None, "p_cal": None, "clip_raw": None, "clip_cal": None,
            "threshold": 0.5, "threshold_source": "NOT_SELECTED", "calibration": None, "underlying": None}


def _standard_candidate(conn, *, run_id, receipt_id, split_plan_id, fold_id, obs, X_train, X_test, train_idx, test_idx,
                        candidate, predictor_set, config, created, geometry_status, label_rule_id, seed) -> dict:
    """Inner tuning, outer refit, optional Platt calibration and OOF predictions for one candidate."""
    y_train, y_test = obs.y[train_idx], obs.y[test_idx]
    hole_train = obs.hole[train_idx]
    eps = float(config["calibration"]["clip_epsilon"])
    mclass = models.model_class(candidate, config)
    trials = []
    for params in models.grid(candidate, config):
        cv = models.inner_cv(X_train, y_train, hole_train, candidate, params, config, seed)
        trials.append({"params": params, **cv})
    selection = models.select_trials(trials)
    if selection["status"] != "COMPLETED":
        return _failed_candidate(conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id,
                                 fold_id=fold_id, obs=obs, train_idx=train_idx, test_idx=test_idx, candidate=candidate,
                                 model_class=mclass, config=config, created=created, seed=seed,
                                 reason=selection["reason"], trials=trials, hyperparameters={},
                                 geometry_status=geometry_status, label_rule_id=label_rule_id)

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
    clip_cal = np.zeros(raw_test.shape[0], dtype=bool) if cal["status"] == "FITTED" else clip_raw.copy()

    training_run_id = _write_run(
        conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id,
        family_id=candidate, candidate_run_id=candidate, model_class=mclass, hyperparameters=params,
        inner_cv_method=config["inner_cv"]["method"], inner_cv_folds=config["inner_cv"]["n_folds"],
        selection_metric=config["inner_cv"]["selection_metric"], inner_score=chosen["mean"], inner_sd=chosen["sd"],
        train_y=y_train, train_idx=train_idx, test_y=y_test, selected=0, threshold=thr["threshold"],
        threshold_source=thr["source"], status="COMPLETED",
        reason=f"{len(trials)} inner trials; {selection['reason']}; predictor set {predictor_set}",
        seed=seed, created=created)
    _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
    _write_trials(conn, training_run_id, candidate, trials, chosen)
    _write_manifest(conn, training_run_id, obs, train_idx)
    conn.execute(
        "INSERT INTO calibration_fits (training_run_id, method, n_inner, inner_positive, inner_negative, intercept, slope, "
        "clip_epsilon, status, reason, created_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (training_run_id, cal["method"], cal["n_inner"], cal["inner_positive"], cal["inner_negative"],
         cal.get("intercept"), cal.get("slope"), eps, cal["status"], cal["reason"], created))
    _write_predictions(conn, training_run_id=training_run_id, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs,
                       idx=test_idx, family_id=candidate, candidate=candidate, p_raw=raw_test,
                       p_cal=calibrated_test, clip_raw=clip_raw, clip_cal=clip_cal, threshold=thr["threshold"],
                       threshold_source=thr["source"], created=created, geometry_status=geometry_status,
                       label_rule_id=label_rule_id)
    _write_artifact(conn, training_run_id, candidate, split_plan_id, fold_id, {
        "candidate_run_id": candidate, "family_id": candidate, "fold_id": fold_id, "split_plan_id": split_plan_id,
        "model_class": mclass, "predictor_set": predictor_set, "hyperparameters": params,
        "inner_cv_score": chosen["mean"], "inner_cv_score_sd": chosen["sd"],
        "selection_metric": config["inner_cv"]["selection_metric"], "threshold": thr,
        "calibration": {k: cal[k] for k in ("method", "status", "intercept", "slope", "reason")},
        "feature_names": obs.feature_names, "training_n": int(train_idx.size),
        "training_id_digest": _digest(obs.ids[train_idx]), "seed": seed, "software": _software(),
    }, created)
    return {"training_run_id": training_run_id, "candidate": candidate, "status": "COMPLETED",
            "inner_score": chosen["mean"], "inner_sd": chosen["sd"], "params": params, "p_raw": raw_test,
            "p_cal": calibrated_test, "clip_raw": clip_raw, "clip_cal": clip_cal, "threshold": thr["threshold"],
            "threshold_source": thr["source"], "calibration": cal, "underlying": candidate}


def _composite(conn, *, name, members, results, run_id, receipt_id, split_plan_id, fold_id, obs, train_idx, test_idx,
               config, created, geometry_status, label_rule_id, seed) -> dict:
    """Copy of the member with the lower inner-CV log loss, written as its own run and its own predictions."""
    usable = [results[m] for m in members if results[m]["status"] == "COMPLETED"]
    if not usable:
        return _failed_candidate(conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id,
                                 fold_id=fold_id, obs=obs, train_idx=train_idx, test_idx=test_idx, candidate=name,
                                 model_class="InnerSelectedCandidate", config=config, created=created, seed=seed,
                                 reason="no member candidate completed in this fold", trials=None,
                                 hyperparameters={"choose_from": members}, geometry_status=geometry_status,
                                 label_rule_id=label_rule_id)
    chosen = min(usable, key=lambda r: (r["inner_score"], members.index(r["candidate"])))
    reason = (f"selected {chosen['candidate']} from {', '.join(members)}: lowest inner-CV log loss "
              f"{chosen['inner_score']:.6f}")
    training_run_id = _write_run(
        conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id, family_id=name,
        candidate_run_id=name, model_class="InnerSelectedCandidate",
        hyperparameters={"selected_candidate": chosen["candidate"], "selected_hyperparameters": chosen["params"],
                         "choose_from": members},
        inner_cv_method=config["inner_cv"]["method"], inner_cv_folds=config["inner_cv"]["n_folds"],
        selection_metric=config["inner_cv"]["selection_metric"], inner_score=chosen["inner_score"],
        inner_sd=chosen["inner_sd"], train_y=obs.y[train_idx], train_idx=train_idx, test_y=obs.y[test_idx],
        selected=1, threshold=chosen["threshold"], threshold_source=chosen["threshold_source"], status="COMPLETED",
        reason=reason, seed=seed, created=created)
    _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
    _write_manifest(conn, training_run_id, obs, train_idx)
    _write_predictions(conn, training_run_id=training_run_id, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs,
                       idx=test_idx, family_id=name, candidate=name, p_raw=chosen["p_raw"], p_cal=chosen["p_cal"],
                       clip_raw=chosen["clip_raw"], clip_cal=chosen["clip_cal"], threshold=chosen["threshold"],
                       threshold_source=chosen["threshold_source"], created=created, geometry_status=geometry_status,
                       label_rule_id=label_rule_id)
    return {**chosen, "training_run_id": training_run_id, "candidate": name, "status": "COMPLETED",
            "underlying": chosen["candidate"], "selected_from": members, "reason": reason}


def _m1(conn, *, run_id, receipt_id, split_plan_id, fold_id, obs, X_train, X_test, train_idx, test_idx, config,
        created, geometry_status, label_rule_id, seed) -> dict:
    """Simple indicator kriging. Covariance chosen by inner whole-hole CV log loss; pure nugget equals the prevalence."""
    y_train = obs.y[train_idx].astype(np.float64)
    p_train = float(y_train.mean())
    sill = p_train * (1.0 - p_train)
    eps = float(config["calibration"]["clip_epsilon"])
    inner = models.inner_folds(obs.hole[train_idx], config["inner_cv"]["n_folds"], seed)
    inner_neigh = [kriging.neighbourhoods(X_train[tr], X_train[te], config) for tr, te in inner]
    trials = []
    for cov in kriging.covariance_grid(config):
        scores = []
        for (tr, te), neigh in zip(inner, inner_neigh):
            mean_in = float(y_train[tr].mean())
            if kriging.is_pure(cov):
                p = np.full(te.size, mean_in)
            else:
                p = kriging.simple_kriging(X_train[tr], y_train[tr], X_train[te], cov, sill, config, mean=mean_in,
                                           neigh=neigh)["p"]
            p = np.clip(p, eps, 1.0 - eps)
            scores.append(float(log_loss(y_train[te], p, labels=[0, 1])))
        mean = float(np.mean(scores))
        trials.append({"params": cov, "status": "COMPLETED", "mean": mean,
                       "sd": float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0, "scores": scores,
                       "reason": f"inner mean log loss {mean:.6f} over {len(scores)} inner folds"})
    chosen = kriging.select_covariance(trials)
    if chosen is None:
        raise StopError("no M1 covariance trial produced a finite inner score")
    cov = chosen["params"]
    pure = kriging.is_pure(cov)
    c0, c1, a = kriging.structure(cov, sill)
    if pure:
        p = np.full(test_idx.size, p_train, dtype=np.float64)
        clipped = np.zeros(test_idx.size, dtype=bool)
    else:
        k = kriging.simple_kriging(X_train, y_train, X_test, cov, sill, config, mean=p_train,
                                   neigh=kriging.neighbourhoods(X_train, X_test, config))
        p = np.clip(k["p"], 0.0, 1.0)
        clipped = k["outside"]
    thr = p_train if 0 < p_train < 1 else 0.5
    label = covariance_label(cov)
    reason = (f"covariance {label} selected by inner-CV log loss {chosen['mean']:.6f}"
              + ("; pure nugget: M1 reduces to the training prevalence" if pure else ""))
    training_run_id = _write_run(
        conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id, family_id=M1_NAME,
        candidate_run_id=M1_NAME, model_class="SimpleIndicatorKriging", hyperparameters={
            "covariance": cov, "covariance_label": label, "model": config["kriging"]["model"], "sill": sill,
            "mean": p_train, "nugget_c0": c0, "structured_c1": c1, "range_m": a,
            "neighbourhood": {"depth_band_m": config["kriging"]["depth_band_m"],
                              "min_neighbours": config["kriging"]["min_neighbours"],
                              "max_neighbours": config["kriging"]["max_neighbours"]}},
        inner_cv_method=config["inner_cv"]["method"], inner_cv_folds=len(inner),
        selection_metric="INNER_CV_LOG_LOSS", inner_score=chosen["mean"], inner_sd=chosen["sd"], train_y=y_train,
        train_idx=train_idx, test_y=obs.y[test_idx], selected=0, threshold=thr,
        threshold_source="TRAINING_PREVALENCE", status="COMPLETED", reason=reason, seed=seed, created=created)
    _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
    _write_manifest(conn, training_run_id, obs, train_idx)
    _write_trials(conn, training_run_id, M1_NAME, trials, chosen)
    conn.execute(
        "INSERT INTO variogram_training_fits (training_run_id, fold_id, family_id, direction_id, model, fit_status, "
        "objective_value, n_bins_used, admissible, marginal_variance, nugget, structured_sill, range_m, "
        "stability_status, stable, reason, created_utc) VALUES (?, ?, 'M1_IK', 'LATERAL_BETWEEN', ?, ?, ?, 0, NULL, ?, ?, ?, ?, "
        "'NOT_ASSESSED', 0, ?, ?)",
        (training_run_id, fold_id, config["kriging"]["model"], "NOT_IDENTIFIABLE" if pure else "FITTED",
         chosen["mean"], sill, None if pure else c0, None if pure else c1, None if pure else a,
         ("pure nugget selected by inner CV: no spatial covariance" if pure else
          f"exponential covariance selected by inner CV; {reason}"), created))
    _write_predictions(conn, training_run_id=training_run_id, split_plan_id=split_plan_id, fold_id=fold_id,
                       obs=obs, idx=test_idx, family_id=M1_NAME, candidate=M1_NAME, p_raw=p, p_cal=p,
                       clip_raw=clipped, clip_cal=clipped, threshold=thr, threshold_source="TRAINING_PREVALENCE",
                       created=created, geometry_status=geometry_status, label_rule_id=label_rule_id)
    _write_artifact(conn, training_run_id, M1_NAME, split_plan_id, fold_id, {
        "candidate_run_id": M1_NAME, "fold_id": fold_id, "split_plan_id": split_plan_id, "covariance": cov,
        "covariance_label": label, "sill": sill, "mean": p_train, "trials": len(trials),
        "kriging": config["kriging"], "training_n": int(train_idx.size),
        "training_id_digest": _digest(obs.ids[train_idx]), "seed": seed, "software": _software(),
    }, created)
    return {"training_run_id": training_run_id, "status": "COMPLETED", "covariance": cov, "label": label,
            "p": p, "threshold": thr}


def _m3(conn, *, run_id, receipt_id, split_plan_id, fold_id, obs, X_train, X_test, train_idx, test_idx, config,
        created, geometry_status, label_rule_id, seed, selected: dict | None) -> dict:
    """Hybrid residual model on the calibrated M2_WF_SEL trend. X_train and X_test are the TREND_WF matrices."""
    y_train, y_test = obs.y[train_idx].astype(np.float64), obs.y[test_idx]
    eps = float(config["calibration"]["clip_epsilon"])
    if selected is None or selected.get("status") != "COMPLETED":
        reason = "no M2_WF_SEL candidate completed in this fold"
        training_run_id = _write_run(
            conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id, family_id=M3_NAME,
            candidate_run_id=M3_NAME, model_class="HybridResidualKriging", hyperparameters={},
            inner_cv_method=config["inner_cv"]["method"], inner_cv_folds=0, selection_metric="NONE", inner_score=None,
            inner_sd=None, train_y=y_train, train_idx=train_idx, test_y=y_test, selected=0, threshold=0.5,
            threshold_source="NOT_SELECTED", status="FAILED", reason=reason, seed=seed, created=created)
        _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
        _write_manifest(conn, training_run_id, obs, train_idx)
        _write_failures(conn, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs, idx=test_idx, family_id=M3_NAME,
                        candidate=M3_NAME, training_run_id=training_run_id, reason=reason, created=created)
        return {"training_run_id": training_run_id, "status": "FAILED", "fallback_status": None, "covariance": None,
                "label": None}

    candidate = selected["underlying"]
    params = selected["params"]
    cal = selected["calibration"]
    hole_train = obs.hole[train_idx]
    inner = models.inner_folds(hole_train, config["inner_cv"]["n_folds"], seed)
    trend_raw = np.full(train_idx.size, np.nan, dtype=np.float64)
    for tr, te in inner:
        est = models.make_estimator(candidate, params, config, seed)
        est.fit(X_train[tr], y_train[tr])
        trend_raw[te] = models.predict_positive(est, X_train[te])
    if not np.all(np.isfinite(trend_raw)):
        raise StopError("M3 inner cross-fitted trend is incomplete")
    trend_inner = models.platt_apply(trend_raw, cal, eps)
    residuals = y_train - trend_inner
    sill = float(np.var(residuals))
    xyz_tr, xyz_te = X_train[:, :3], X_test[:, :3]

    inner_neigh = [kriging.neighbourhoods(xyz_tr[tr], xyz_tr[te], config) for tr, te in inner]
    trials = []
    for cov in kriging.covariance_grid(config):
        scores = []
        for (tr, te), neigh in zip(inner, inner_neigh):
            if kriging.is_pure(cov):
                kr = np.zeros(te.size)
            else:
                kr = kriging.simple_kriging(xyz_tr[tr], residuals[tr], xyz_tr[te], cov, sill, config, mean=0.0,
                                            neigh=neigh)["p"]
            combined = np.clip(trend_inner[te] + kr, eps, 1.0 - eps)
            scores.append(float(log_loss(y_train[te], combined, labels=[0, 1])))
        mean = float(np.mean(scores))
        trials.append({"params": cov, "status": "COMPLETED", "mean": mean,
                       "sd": float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0, "scores": scores,
                       "reason": f"inner mean log loss {mean:.6f} over {len(scores)} inner folds"})
    chosen = kriging.select_covariance(trials)
    if chosen is None:
        raise StopError("no M3 residual covariance trial produced a finite inner score")
    cov = chosen["params"]
    pure = kriging.is_pure(cov)
    c0, c1, a = kriging.structure(cov, sill)
    label = covariance_label(cov)

    trend_test = selected["p_cal"].copy()
    if pure:
        kr_test = np.zeros(test_idx.size)
    else:
        kr_test = kriging.simple_kriging(xyz_tr, residuals, xyz_te, cov, sill, config, mean=0.0,
                                         neigh=kriging.neighbourhoods(xyz_tr, xyz_te, config))["p"]
    combined = trend_test + kr_test
    if pure:
        status, fallback_status = "FALLBACK", "FALLBACK_ML_ONLY"
        reason = ("residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is "
                  "recorded as the ML-only fallback")
        p = np.clip(trend_test, 0.0, 1.0)
        p_raw = trend_test.copy()
        clip_raw = selected["clip_cal"].copy()
        clip_cal = selected["clip_cal"].copy()
    else:
        status, fallback_status = "COMPLETED", "HYBRID_USED"
        reason = (f"residual covariance {label} selected by inner-CV log loss {chosen['mean']:.6f}; kriged residual "
                  f"added to the calibrated trend")
        clipped = (combined < 0.0) | (combined > 1.0)
        p = np.clip(combined, 0.0, 1.0)
        p_raw = p.copy()
        clip_raw = clipped
        clip_cal = clipped
    thr = selected["threshold"]
    training_run_id = _write_run(
        conn, run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fold_id, family_id=M3_NAME,
        candidate_run_id=M3_NAME, model_class="HybridResidualKriging", hyperparameters={
            "trend_composite": "M2_WF_SEL", "trend_candidate": candidate, "trend_hyperparameters": params,
            "trend_calibration_status": cal["status"], "residual_covariance": cov, "residual_covariance_label": label,
            "residual_sill": sill, "fallback": fallback_status},
        inner_cv_method=config["inner_cv"]["method"], inner_cv_folds=len(inner), selection_metric="INNER_CV_LOG_LOSS",
        inner_score=selected.get("inner_score"), inner_sd=chosen["sd"], train_y=y_train, train_idx=train_idx,
        test_y=y_test, selected=0, threshold=thr, threshold_source="M2_WF_SEL_THRESHOLD", status=status,
        reason=reason, seed=seed, created=created)
    _update_run_counts(conn, training_run_id, obs.hole[train_idx], obs.line[train_idx])
    _write_manifest(conn, training_run_id, obs, train_idx)
    _write_trials(conn, training_run_id, M3_NAME, trials, chosen)
    conn.execute(
        "INSERT INTO hybrid_residual_variogram (training_run_id, fold_id, model, fit_status, objective_value, "
        "n_bins_used, admissible, residual_variance, nugget, structured_sill, range_m, stability_status, supported, "
        "fallback_status, reason, created_utc) VALUES (?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?, 'NOT_ASSESSED', ?, ?, ?, ?)",
        (training_run_id, fold_id, config["kriging"]["model"], "NOT_IDENTIFIABLE" if pure else "FITTED",
         chosen["mean"], sill, None if pure else c0, None if pure else c1, None if pure else a,
         0 if pure else 1, fallback_status,
         ("pure nugget selected by inner CV" if pure else f"exponential residual covariance; {reason}"), created))
    conn.executemany(
        "INSERT OR IGNORE INTO residual_diagnostics (training_run_id, observation_id, role, fold_id, trend_probability, "
        "residual, created_utc) VALUES (?, ?, 'INNER_OOF', ?, ?, ?, ?)",
        [(training_run_id, int(obs.ids[i]), fold_id, float(trend_inner[k]), float(residuals[k]), created)
         for k, i in enumerate(train_idx)])
    conn.executemany(
        "INSERT OR IGNORE INTO residual_diagnostics (training_run_id, observation_id, role, fold_id, trend_probability, "
        "residual, created_utc) VALUES (?, ?, 'TEST', ?, ?, ?, ?)",
        [(training_run_id, int(obs.ids[i]), fold_id, float(trend_test[k]), float(y_test[k] - p[k]), created)
         for k, i in enumerate(test_idx)])
    _write_predictions(conn, training_run_id=training_run_id, split_plan_id=split_plan_id, fold_id=fold_id, obs=obs,
                       idx=test_idx, family_id=M3_NAME, candidate=M3_NAME, p_raw=p_raw, p_cal=p,
                       clip_raw=clip_raw, clip_cal=clip_cal, threshold=thr, threshold_source="M2_WF_SEL_THRESHOLD",
                       created=created, geometry_status=geometry_status, label_rule_id=label_rule_id)
    _write_artifact(conn, training_run_id, M3_NAME, split_plan_id, fold_id, {
        "candidate_run_id": M3_NAME, "fold_id": fold_id, "split_plan_id": split_plan_id, "trend_composite": "M2_WF_SEL",
        "trend_candidate": candidate, "trend_hyperparameters": params, "residual_covariance": cov,
        "residual_covariance_label": label, "residual_sill": sill, "fallback": fallback_status,
        "training_n": int(train_idx.size), "training_id_digest": _digest(obs.ids[train_idx]), "seed": seed,
        "software": _software(),
    }, created)
    return {"training_run_id": training_run_id, "status": status, "fallback_status": fallback_status,
            "covariance": cov, "label": label, "p": p, "threshold": thr}


def _front_fold_checks_summary(front_checks: list[dict]) -> tuple[str, str]:
    bad = [c for c in front_checks if c["status"] != "PASS"]
    status = "PASS" if not bad else "FAIL"
    detail = (f"{len(front_checks)} outer folds recomputed with the test holes' weathering codes altered; "
              f"{len(bad)} failed; " + "; ".join(f"fold {c['fold_id']}: {c['detail']}" for c in front_checks[:5]))
    return status, detail


def _leakage_audit(conn, run_id: int, split_plan_id: str, created: str, front_checks: list[dict],
                   predictor_names: list[str]) -> list[dict]:
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
    marks = ",".join("?" for _ in predictor_names)
    bad_features = conn.execute(
        f"SELECT COUNT(*) FROM feature_registry WHERE name IN ({marks}) "
        "AND (available_at_prediction <> 1 OR leakage_designation <> 'SAFE')", tuple(predictor_names)).fetchone()[0]
    found = conn.execute(f"SELECT COUNT(*) FROM feature_registry WHERE name IN ({marks})",
                         tuple(predictor_names)).fetchone()[0]
    if found != len(predictor_names):
        bad_features += len(predictor_names) - found
    checks.append({"check_name": "PREDICTORS_SAFE_AND_AVAILABLE", "status": "PASS" if bad_features == 0 else "FAIL",
                   "detail": f"{bad_features} deployed predictors are not SAFE and available "
                             f"({', '.join(predictor_names)})"})
    front_status, front_detail = _front_fold_checks_summary(front_checks)
    checks.append({"check_name": "FRONT_FEATURE_FOLD_SAFE", "status": front_status, "detail": front_detail})
    bad_var = conn.execute(
        "SELECT COUNT(*) FROM variogram_training_fits v JOIN training_runs t ON t.training_run_id = v.training_run_id "
        "WHERE t.split_plan_id = ? AND t.fold_id <> v.fold_id", (split_plan_id,)).fetchone()[0]
    bad_var += conn.execute(
        "SELECT COUNT(*) FROM hybrid_residual_variogram v JOIN training_runs t ON t.training_run_id = v.training_run_id "
        "WHERE t.split_plan_id = ? AND t.fold_id <> v.fold_id", (split_plan_id,)).fetchone()[0]
    checks.append({"check_name": "VARIOGRAMS_BELONG_TO_THEIR_TRAINING_FOLD", "status": "PASS" if bad_var == 0 else "FAIL",
                   "detail": f"{bad_var} covariance rows reference a different fold"})
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


def _run_plan(conn, *, receipt, config: dict, config_sha: str, split_plan_id: str, obs, seed: int) -> dict:
    receipt_id = receipt["receipt_id"]
    geometry_status = receipt["geometry_status"]
    label_rule_id = receipt["label_rule_id"]
    derived = config["features"]["derived"]["depth_below_weathering_front_m"]
    front_codes = list(derived["front_codes"])
    surface = derived["surface"]
    power, k_nb, coincident = float(surface["power"]), int(surface["n_neighbours"]), float(surface["coincident_distance_m"])
    fronts = weathering_front.hole_fronts(conn, receipt_id, front_codes)
    cand = _candidate_plan(config)
    sets_names = predictor_sets(config)
    folds = _membership(conn, split_plan_id)
    index = _index_of(obs)
    conn.execute("BEGIN IMMEDIATE")
    try:
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, split_plan_id, started_utc, "
            "status, code_commit, note) VALUES ('TRAIN', ?, ?, ?, ?, ?, 'RUNNING', ?, ?)",
            (config["config_version"], config_sha, receipt_id, split_plan_id, utc_now(), code_commit(),
             f"outer folds of {split_plan_id}; inner whole-hole tuning; fold-safe weathering front")).lastrowid
        created = utc_now()
        fold_results, front_checks = [], []
        for fold in folds:
            fid = fold["fold_id"]
            train_idx = np.array([index[i] for i in fold["train"]], dtype=np.int64)
            test_idx = np.array([index[i] for i in fold["test"]], dtype=np.int64)
            feat = weathering_front.feature_for_fold(obs, train_idx, test_idx, fronts, power=power, k=k_nb,
                                                     coincident=coincident)
            check = weathering_front.fold_safety_check(conn, receipt_id, obs, train_idx, test_idx, front_codes,
                                                       power=power, k=k_nb, coincident=coincident)
            front_checks.append({"fold_id": fid, **check})
            matrices = {
                "TREND": (obs.X[train_idx], obs.X[test_idx]),
                "TREND_WF": (np.column_stack([obs.X[train_idx], feat["train"]]),
                             np.column_stack([obs.X[test_idx], feat["test"]])),
            }
            results = {}
            common = dict(run_id=run_id, receipt_id=receipt_id, split_plan_id=split_plan_id, fold_id=fid, obs=obs,
                          train_idx=train_idx, test_idx=test_idx, config=config, created=created,
                          geometry_status=geometry_status, label_rule_id=label_rule_id, seed=seed)
            for candidate in cand["plain"] + cand["wf"]:
                pset = models.predictor_set(candidate, config)
                if pset not in sets_names:
                    raise StopError(f"candidate {candidate} names an unknown predictor set {pset}")
                X_tr, X_te = matrices[pset]
                results[candidate] = _standard_candidate(
                    conn, X_train=X_tr, X_test=X_te, candidate=candidate, predictor_set=pset, **common)
            for name, members in cand["composites"].items():
                usable = [results[m] for m in members if results[m]["status"] == "COMPLETED"]
                if usable:
                    best = min(usable, key=lambda r: (r["inner_score"], members.index(r["candidate"])))
                    conn.execute("UPDATE training_runs SET selected = 1 WHERE training_run_id = ?",
                                 (best["training_run_id"],))
                    best["selected"] = 1
            for name, members in cand["composites"].items():
                results[name] = _composite(conn, name=name, members=members, results=results, **common)
            results[M1_NAME] = _m1(conn, X_train=matrices["TREND"][0], X_test=matrices["TREND"][1], **common)
            results[M3_NAME] = _m3(conn, X_train=matrices["TREND_WF"][0], X_test=matrices["TREND_WF"][1],
                                   selected=results["M2_WF_SEL"], **common)
            fold_results.append({
                "fold_id": fid, "split_plan_id": split_plan_id, "n_train": int(train_idx.size),
                "n_test": int(test_idx.size), "m2_selected": results["M2_SEL"].get("underlying"),
                "m2_selected_inner_score": results["M2_SEL"].get("inner_score"),
                "m2_wf_selected": results["M2_WF_SEL"].get("underlying"),
                "m2_wf_selected_inner_score": results["M2_WF_SEL"].get("inner_score"),
                "m1_status": results[M1_NAME]["status"], "m1_covariance": results[M1_NAME]["label"],
                "m3_status": results[M3_NAME]["status"], "m3_covariance": results[M3_NAME]["label"],
                "m3_fallback": results[M3_NAME].get("fallback_status"), "front_check": check["status"],
                "front_surface_holes": len(feat["surface_holes"]),
            })
        conn.execute(
            "INSERT OR IGNORE INTO final_refits (family_id, candidate_run_id, selection_decision_id, status, reason, "
            "created_utc) VALUES ('M3_HYBRID', 'TO_BE_SELECTED_BY_O4', NULL, 'PENDING_O4', "
            "'Objective 4 locks model selection; Objective 3 does not refit on all data', ?)", (created,))
        audits = _leakage_audit(conn, run_id, split_plan_id, created, front_checks,
                                sets_names["TREND_WF"])
        conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ? WHERE run_id = ?", (utc_now(), run_id))
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return {"run_id": run_id, "split_plan_id": split_plan_id, "folds": fold_results, "leakage_audits": audits}


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
        plan_ids = [t["split_plan_id"] for t in config["splits"]["tiers"]]
        for split_plan_id in plan_ids:
            if conn.execute("SELECT COUNT(*) FROM spatial_split_plans WHERE split_plan_id = ?",
                            (split_plan_id,)).fetchone()[0] == 0:
                raise StopError(f"split plan {split_plan_id} is not frozen: run the splits stage first")
            if conn.execute("SELECT COUNT(*) FROM training_runs WHERE split_plan_id = ?",
                            (split_plan_id,)).fetchone()[0]:
                raise StopError(f"training rows already exist for split plan {split_plan_id}; a new receipt is needed")
        obs = load_observations(conn, receipt_id, config)
        seed = int(config["seeds"][0])
        plans = [_run_plan(conn, receipt=receipt, config=config, config_sha=config_sha, split_plan_id=sp, obs=obs,
                           seed=seed) for sp in plan_ids]
        return {"receipt_id": receipt_id, "plans": plans}
    finally:
        conn.close()

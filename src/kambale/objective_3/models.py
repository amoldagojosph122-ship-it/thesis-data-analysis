"""Model definitions, inner spatial tuning, threshold selection and probability calibration.

Every hyperparameter choice is made inside the outer training fold, on whole-hole inner folds. The outer test labels
are not read by this module. The candidate families are the prevalence and logistic baselines, random forest and
histogram gradient boosting (M2), and the trend used by the hybrid (M3).
"""

from __future__ import annotations

import itertools
import math

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class PrevalenceModel:
    """Constant training prevalence. A sanity baseline that cannot overfit the test fold."""

    def __init__(self):
        self.p = 0.5

    def fit(self, X, y):
        self.p = float(np.mean(y))
        return self

    def predict_proba(self, X):
        return np.column_stack([np.full(X.shape[0], 1.0 - self.p), np.full(X.shape[0], self.p)])


PARENT_KEYS = ("prevalence", "logistic", "random_forest", "gradient_boosting")

MODEL_CLASS = {
    "BASE_PREVALENCE": "TrainingPrevalence",
    "BASE_LOGISTIC": "LogisticRegression",
    "M2_RF": "RandomForestClassifier",
    "M2_HGB": "HistGradientBoostingClassifier",
}


def base_candidate(candidate_run_id: str, config: dict) -> str:
    """The parent estimator of a weathering variant (same estimator and grid); other candidates map to themselves."""
    for variant in config["models"].get("weathering_variants", []):
        if variant["candidate_run_id"] == candidate_run_id:
            return variant["parent"]
    return candidate_run_id


def model_class(candidate_run_id: str, config: dict) -> str:
    return MODEL_CLASS[base_candidate(candidate_run_id, config)]


def predictor_set(candidate_run_id: str, config: dict) -> str:
    """Name of the predictor set (TREND or TREND_WF) a candidate is fitted on, from the configuration."""
    for variant in config["models"].get("weathering_variants", []):
        if variant["candidate_run_id"] == candidate_run_id:
            return variant["predictor_set"]
    for key in PARENT_KEYS:
        if config["models"][key]["candidate_run_id"] == candidate_run_id:
            return config["models"][key]["predictor_set"]
    raise ValueError(f"unknown candidate {candidate_run_id}")


def grid(candidate_run_id: str, config: dict) -> list[dict]:
    """Full Cartesian grid for one candidate, taken only from the predeclared configuration."""
    candidate_run_id = base_candidate(candidate_run_id, config)
    models = config["models"]
    if candidate_run_id == models["prevalence"]["candidate_run_id"]:
        return [{}]
    if candidate_run_id == models["logistic"]["candidate_run_id"]:
        g = models["logistic"]["grid"]
    elif candidate_run_id == models["random_forest"]["candidate_run_id"]:
        g = models["random_forest"]["grid"]
    elif candidate_run_id == models["gradient_boosting"]["candidate_run_id"]:
        g = models["gradient_boosting"]["grid"]
    else:
        raise ValueError(f"unknown candidate {candidate_run_id}")
    keys = sorted(g)
    return [dict(zip(keys, values)) for values in itertools.product(*(g[k] for k in keys))]


def make_estimator(candidate_run_id: str, params: dict, config: dict, seed: int):
    candidate_run_id = base_candidate(candidate_run_id, config)
    models = config["models"]
    if candidate_run_id == models["prevalence"]["candidate_run_id"]:
        return PrevalenceModel()
    if candidate_run_id == models["logistic"]["candidate_run_id"]:
        return Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=float(params["C"]), class_weight=params["class_weight"],
                                       max_iter=int(params["max_iter"]), solver="lbfgs")),
        ])
    if candidate_run_id == models["random_forest"]["candidate_run_id"]:
        return RandomForestClassifier(
            n_estimators=int(params["n_estimators"]), max_depth=params["max_depth"],
            min_samples_leaf=int(params["min_samples_leaf"]), max_features=params["max_features"],
            random_state=seed, n_jobs=1, class_weight=None)
    if candidate_run_id == models["gradient_boosting"]["candidate_run_id"]:
        return HistGradientBoostingClassifier(
            learning_rate=float(params["learning_rate"]), max_iter=int(params["max_iter"]),
            max_leaf_nodes=int(params["max_leaf_nodes"]), min_samples_leaf=int(params["min_samples_leaf"]),
            l2_regularization=float(params["l2_regularization"]), early_stopping=False, random_state=seed)
    raise ValueError(f"unknown candidate {candidate_run_id}")


def predict_positive(estimator, X) -> np.ndarray:
    p = estimator.predict_proba(X)
    return np.asarray(p[:, 1] if p.ndim == 2 else p, dtype=np.float64)


def _fold_count(hole: np.ndarray, requested: int) -> int:
    return max(2, min(int(requested), int(np.unique(hole).size)))


def inner_folds(hole: np.ndarray, requested: int, seed: int):
    """Whole-hole inner folds. GroupKFold is deterministic; the seed is recorded for provenance."""
    del seed  # GroupKFold has no shuffle; the declared seed documents the outer plan seed.
    k = _fold_count(hole, requested)
    dummy = np.zeros((hole.size, 1), dtype=np.float64)
    return list(GroupKFold(n_splits=k).split(dummy, hole, groups=hole))


def inner_cv(X, y, hole, candidate_run_id: str, params: dict, config: dict, seed: int) -> dict:
    """Inner out-of-fold probabilities and per-fold log losses for one candidate."""
    splits = inner_folds(hole, config["inner_cv"]["n_folds"], seed)
    p_inner = np.full(y.size, np.nan, dtype=np.float64)
    scores = []
    eps = float(config["calibration"]["clip_epsilon"])
    for tr, te in splits:
        if len(np.unique(y[tr])) < 2:
            return {"status": "FAILED", "reason": "an inner training fold carries one class", "p": None,
                    "scores": [], "mean": None, "sd": None}
        est = make_estimator(candidate_run_id, params, config, seed)
        est.fit(X[tr], y[tr])
        p = np.clip(predict_positive(est, X[te]), eps, 1.0 - eps)
        p_inner[te] = p
        scores.append(float(log_loss(y[te], p, labels=[0, 1])))
    complete = bool(np.all(np.isfinite(p_inner)))
    return {"status": "COMPLETED" if complete else "FAILED",
            "reason": "all inner observations predicted" if complete else "an inner observation was not predicted",
            "p": p_inner, "scores": scores,
            "mean": float(np.mean(scores)) if scores else None,
            "sd": float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0}


def select_trials(trials: list[dict]) -> dict:
    """The trial with the lowest inner mean log loss; ties go to the earliest declared grid point."""
    usable = [t for t in trials if t["status"] == "COMPLETED" and t["mean"] is not None]
    if not usable:
        return {"status": "FAILED", "reason": "no inner trial completed", "trial": None}
    best = min(enumerate(usable), key=lambda it: (it[1]["mean"], it[0]))[1]
    return {"status": "COMPLETED", "reason": f"lowest inner mean log loss {best['mean']:.6f}", "trial": best}


def youden_threshold(y: np.ndarray, p: np.ndarray, grid_values: list[float], eps: float) -> dict:
    """Training-only threshold maximising sensitivity + specificity - 1.

    Ties are broken toward the threshold closest to 0.5. With a constant or near-constant probability the Youden score
    is flat, and the lowest grid point would classify every interval positive; the tie-break avoids that artefact.
    """
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=np.float64), eps, 1.0 - eps)
    pos = int(y.sum())
    neg = int(y.size - pos)
    if pos == 0 or neg == 0:
        return {"threshold": 0.5, "source": "DEFAULT_BOTH_CLASSES_ABSENT", "youden_j": None}
    best_t, best_j, best_key = 0.5, -2.0, None
    for t in sorted(grid_values):
        pred = p >= float(t)
        tpr = float(np.sum(pred & (y == 1))) / pos
        fpr = float(np.sum(pred & (y == 0))) / neg
        j = tpr - fpr
        key = (j, -abs(float(t) - 0.5))
        if best_key is None or key > best_key:
            best_t, best_j, best_key = float(t), j, key
    return {"threshold": best_t, "source": "INNER_CV_MAX_YOUDEN_J_TIE_CLOSEST_TO_HALF", "youden_j": best_j}


def logit(p: np.ndarray, eps: float) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=np.float64), eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=np.float64)))


def platt_fit(y: np.ndarray, p: np.ndarray, config: dict) -> dict:
    """Platt scaling fitted on inner out-of-fold probabilities only."""
    c = config["calibration"]
    eps = float(c["clip_epsilon"])
    n = int(np.size(y))
    pos = int(np.sum(y))
    neg = n - pos
    base = {"method": "PLATT", "n_inner": n, "inner_positive": pos, "inner_negative": neg, "intercept": None,
            "slope": None, "clip_epsilon": eps}
    if n < int(c["minimum_inner_samples"]):
        return {**base, "status": "SKIPPED", "reason": f"{n} inner predictions; {c['minimum_inner_samples']} required"}
    if pos == 0 or neg == 0:
        return {**base, "status": "SKIPPED", "reason": "the inner predictions carry one class only"}
    x = logit(p, eps).reshape(-1, 1)
    clf = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    try:
        clf.fit(x, y)
    except Exception as exc:  # pragma: no cover - defensive
        return {**base, "status": "FAILED", "reason": f"Platt fit failed: {exc}"}
    return {**base, "status": "FITTED", "intercept": float(clf.intercept_[0]), "slope": float(clf.coef_[0, 0]),
            "reason": f"Platt scaling on {n} inner out-of-fold predictions"}


def platt_apply(p: np.ndarray, fit: dict, eps: float) -> np.ndarray:
    if fit["status"] != "FITTED":
        return np.clip(np.asarray(p, dtype=np.float64), eps, 1.0 - eps)
    return np.clip(sigmoid(fit["slope"] * logit(p, eps) + fit["intercept"]), eps, 1.0 - eps)


def finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))

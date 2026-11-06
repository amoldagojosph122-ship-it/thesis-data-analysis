"""Model fitting and prediction with the Objective 3 rules, called unchanged from kambale.objective_3.models.

full-data fit: hyperparameters by whole-hole inner cross-validation (log loss) over the Objective 3 grid, then one refit on all
rows, then Platt calibration from the inner cross-fitted predictions where Objective 3 applies it.
fixed-parameter fit (bootstrap): the hyperparameters are supplied; the inner cross-fit is run only when calibration applies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from kambale.objective_3 import models
from kambale.objective_5.config import StopError


class FitError(RuntimeError):
    """One fit failed. Bootstrap replicates record it; the final refits stop the run."""


@dataclass
class FittedModel:
    candidate: str
    predictors: list
    params: dict
    estimator: object
    calibration: dict
    eps: float
    inner_score: float | None
    inner_sd: float | None
    trial_summary: list = field(default_factory=list)
    seed: int = 0

    def predict(self, X) -> np.ndarray:
        """Calibrated probability of the positive class, clipped to the Objective 3 epsilon."""
        X = np.asarray(X, dtype=np.float64)
        raw = np.clip(models.predict_positive(self.estimator, X), self.eps, 1.0 - self.eps)
        if self.calibration.get("status") == "FITTED":
            return models.platt_apply(raw, self.calibration, self.eps)
        return raw


def fit_candidate(candidate: str, X, y, groups, config: dict, seed: int, predictors, fixed_params=None) -> FittedModel:
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64)
    groups = np.asarray(groups)
    eps = float(config["calibration"]["clip_epsilon"])
    apply_cal = candidate in config["calibration"]["apply_to"]
    trial_summary = []
    if fixed_params is None:
        trials = []
        for params in models.grid(candidate, config):
            cv = models.inner_cv(X, y, groups, candidate, params, config, seed)
            trials.append({"params": params, **cv})
            trial_summary.append({"params": params, "status": cv["status"], "mean": cv["mean"], "sd": cv["sd"]})
        sel = models.select_trials(trials)
        if sel["status"] != "COMPLETED":
            raise FitError(sel["reason"])
        chosen = sel["trial"]
        params = chosen["params"]
        inner_p = chosen["p"]
        inner_score, inner_sd = chosen["mean"], chosen["sd"]
    else:
        params = dict(fixed_params)
        inner_score = inner_sd = None
        inner_p = None
        if apply_cal:
            cv = models.inner_cv(X, y, groups, candidate, params, config, seed)
            if cv["status"] != "COMPLETED" or cv["p"] is None:
                raise FitError(f"inner cross-fit did not complete: {cv['reason']}")
            inner_p = cv["p"]
    estimator = models.make_estimator(candidate, params, config, seed)
    estimator.fit(X, y)
    if apply_cal:
        calibration = models.platt_fit(y, np.clip(inner_p, eps, 1.0 - eps), config)
    else:
        calibration = {"method": "NONE", "status": "SKIPPED", "n_inner": int(y.size),
                       "inner_positive": int(y.sum()), "inner_negative": int(y.size - y.sum()),
                       "intercept": None, "slope": None, "clip_epsilon": eps,
                       "reason": "calibration is not configured for this family"}
    return FittedModel(candidate=candidate, predictors=list(predictors), params=params, estimator=estimator,
                       calibration=calibration, eps=eps, inner_score=inner_score, inner_sd=inner_sd,
                       trial_summary=trial_summary, seed=seed)


def check_predictors(config: dict, candidate: str, predictors) -> None:
    """The predictor list of a candidate must equal the Objective 3 predictor set it is configured on."""
    pset = models.predictor_set(candidate, config)
    expected = config["features"]["predictor_sets"][pset]
    if list(predictors) != list(expected):
        raise StopError(f"{candidate} is configured on {pset} {expected}, not {list(predictors)}")

"""Probability metrics, calibration diagnostics and curve points for Objective 4.

All metrics are computed from the frozen Objective 3 snapshot. Nothing in this module changes a prediction or
recalibrates on held-out labels. A calibration intercept and slope are fitted only as diagnostics.
"""

from __future__ import annotations

import math

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, log_loss as sk_log_loss, roc_auc_score


def _arrays(y, p, w):
    y = np.asarray(y, dtype=np.float64)
    p = np.asarray(p, dtype=np.float64)
    w = np.asarray(w, dtype=np.float64)
    return y, p, w


def brier(y, p, w) -> float:
    y, p, w = _arrays(y, p, w)
    return float(np.sum(w * (p - y) ** 2) / np.sum(w))


def log_loss(y, p, w, eps: float = 1e-6) -> float:
    y, p, w = _arrays(y, p, w)
    q = np.clip(p, eps, 1.0 - eps)
    return float(-np.sum(w * (y * np.log(q) + (1.0 - y) * np.log(1.0 - q))) / np.sum(w))


def roc_auc(y, p, w) -> tuple[float | None, str, str]:
    y, p, w = _arrays(y, p, w)
    if len(np.unique(y)) < 2:
        return None, "UNDEFINED", "one class in the evaluation set"
    return float(roc_auc_score(y, p, sample_weight=w)), "DEFINED", "weighted ROC-AUC"


def pr_auc(y, p, w) -> tuple[float | None, str, str]:
    y, p, w = _arrays(y, p, w)
    if np.sum(y * w) <= 0:
        return None, "UNDEFINED", "no positive weight in the evaluation set"
    return float(average_precision_score(y, p, sample_weight=w)), "DEFINED", "weighted average precision"


def logit(p, eps: float = 1e-6):
    p = np.clip(np.asarray(p, dtype=np.float64), eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


def calibration_fit(y, p, w, eps: float = 1e-6) -> dict:
    """Diagnostic logistic fit y ~ logit(p). Never applied to the predictions."""
    y, p, w = _arrays(y, p, w)
    n = int(y.size)
    n_pos = int(y.sum())
    base = {"n": n, "n_positive": n_pos, "intercept": None, "slope": None}
    if n < 10:
        return {**base, "status": "NOT_ESTIMABLE", "reason": f"{n} observations; 10 required"}
    if n_pos == 0 or n_pos == n:
        return {**base, "status": "UNDEFINED", "reason": "one class in the evaluation set"}
    x = logit(p, eps).reshape(-1, 1)
    try:
        clf = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
        clf.fit(x, y.astype(int), sample_weight=w)
    except Exception as exc:  # pragma: no cover - defensive
        return {**base, "status": "NOT_ESTIMABLE", "reason": f"calibration fit failed: {exc}"}
    return {**base, "intercept": float(clf.intercept_[0]), "slope": float(clf.coef_[0, 0]),
            "status": "DEFINED", "reason": "diagnostic logistic fit on pooled held-out predictions"}


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def reliability_bins(y, p, w, edges, min_n: int) -> list[dict]:
    """Weighted reliability bins, merging upward from the lowest bin until the count reaches min_n."""
    y, p, w = _arrays(y, p, w)
    edges = [float(e) for e in edges]
    raw = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i == len(edges) - 2:
            mask = (p >= lo) & (p <= hi)
        else:
            mask = (p >= lo) & (p < hi)
        n = float(np.sum(w[mask]))
        raw.append({"lo": lo, "hi": hi, "mask": mask, "n": n})
    # Merge upward until each bin has at least min_n weighted observations; the final bin absorbs the remainder.
    merged = []
    current = None
    for b in raw:
        if current is None:
            current = {"lo": b["lo"], "hi": b["hi"], "mask": b["mask"].copy()}
        else:
            current["hi"] = b["hi"]
            current["mask"] |= b["mask"]
        if float(np.sum(w[current["mask"]])) >= min_n:
            merged.append(current)
            current = None
    if current is not None:
        if merged:
            merged[-1]["hi"] = current["hi"]
            merged[-1]["mask"] |= current["mask"]
        else:
            merged.append(current)
    out = []
    total = float(np.sum(w))
    for i, b in enumerate(merged):
        mask = b["mask"]
        n = float(np.sum(w[mask]))
        if n <= 0:
            continue
        mean_p = float(np.sum(w[mask] * p[mask]) / n)
        rate = float(np.sum(w[mask] * y[mask]) / n)
        k = int(round(rate * n))
        lo_ci, hi_ci = wilson_interval(k, int(round(n)))
        out.append({"bin_index": len(out), "bin_lower": b["lo"], "bin_upper": b["hi"], "n": int(round(n)),
                    "mean_p": mean_p, "observed_rate": rate, "wilson_low": lo_ci, "wilson_high": hi_ci,
                    "merged": 1 if (b["hi"] - b["lo"]) > (edges[1] - edges[0]) + 1e-12 else 0})
    return out


def ece_from_bins(bins: list[dict]) -> tuple[float | None, str]:
    total = sum(b["n"] for b in bins)
    if total <= 0:
        return None, "NOT_ESTIMABLE"
    return float(sum(b["n"] / total * abs(b["mean_p"] - b["observed_rate"]) for b in bins)), "DEFINED"


def confusion(y, p, threshold: float) -> dict:
    y, p = np.asarray(y, dtype=int), np.asarray(p, dtype=np.float64)
    pred = (p >= threshold).astype(int)
    tp = int(np.sum((pred == 1) & (y == 1)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    balanced = (recall + specificity) / 2.0 if recall is not None and specificity is not None else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall and (precision + recall) else None
    denom = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = ((tp * tn - fp * fn) / denom) if denom else None
    undefined = [name for name, value in (("precision", precision), ("recall", recall), ("specificity", specificity),
                                          ("balanced_accuracy", balanced), ("f1", f1), ("mcc", mcc)) if value is None]
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": precision, "recall": recall,
            "specificity": specificity, "balanced_accuracy": balanced, "f1": f1, "mcc": mcc,
            "status": "DEFINED" if not undefined else "UNDEFINED",
            "reason": "all rates defined" if not undefined else "undefined rates: " + ", ".join(undefined)}


def roc_points(y, p, w) -> list[dict]:
    """Weighted ROC points at every distinct predicted probability."""
    y, p, w = _arrays(y, p, w)
    order = np.argsort(-p, kind="stable")
    y, p, w = y[order], p[order], w[order]
    pos = float(np.sum(w * y))
    neg = float(np.sum(w * (1.0 - y)))
    if pos <= 0 or neg <= 0:
        return []
    pts, tp, fp = [{"threshold": None, "tpr": 0.0, "fpr": 0.0, "n": 0}], 0.0, 0.0
    for i in range(y.size):
        tp += w[i] * y[i]
        fp += w[i] * (1.0 - y[i])
        if i + 1 < y.size and p[i + 1] == p[i]:
            continue
        pts.append({"threshold": float(p[i]), "tpr": tp / pos, "fpr": fp / neg, "n": i + 1})
    pts.append({"threshold": 0.0, "tpr": 1.0, "fpr": 1.0, "n": int(y.size)})
    return pts


def pr_points(y, p, w) -> list[dict]:
    """Weighted precision-recall points at every distinct predicted probability."""
    y, p, w = _arrays(y, p, w)
    order = np.argsort(-p, kind="stable")
    y, p, w = y[order], p[order], w[order]
    pos = float(np.sum(w * y))
    if pos <= 0:
        return []
    pts, tp, fp = [], 0.0, 0.0
    for i in range(y.size):
        tp += w[i] * y[i]
        fp += w[i] * (1.0 - y[i])
        if i + 1 < y.size and p[i + 1] == p[i]:
            continue
        precision = tp / (tp + fp) if tp + fp else 1.0
        pts.append({"threshold": float(p[i]), "precision": precision, "recall": tp / pos, "n": i + 1})
    return pts


def metric_block(y, p, w, threshold, eps: float = 1e-6) -> dict:
    auc, auc_status, auc_reason = roc_auc(y, p, w)
    ap, ap_status, ap_reason = pr_auc(y, p, w)
    return {"brier": brier(y, p, w), "log_loss": log_loss(y, p, w, eps),
            "roc_auc": auc, "roc_auc_status": auc_status, "roc_auc_reason": auc_reason,
            "pr_auc": ap, "pr_auc_status": ap_status, "pr_auc_reason": ap_reason,
            "confusion": confusion(y, p, threshold)}


def independent_brier(y, p, w) -> float:
    """A direct loop used only by the numerical cross-check gate and tests."""
    total = 0.0
    denom = 0.0
    for yi, pi, wi in zip(y, p, w):
        total += float(wi) * (float(pi) - float(yi)) ** 2
        denom += float(wi)
    return total / denom

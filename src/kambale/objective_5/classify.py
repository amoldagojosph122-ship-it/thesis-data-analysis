"""Classification of every cell: CONFIDENT_PRESENT, CONFIDENT_ABSENT, UNCERTAIN or NO_SUPPORT.

CONFIDENT_PRESENT: p_lo >= threshold, disagreement < limit, not DEPTH_EXTRAPOLATED.
CONFIDENT_ABSENT:  p_hi <  threshold, disagreement < limit, not DEPTH_EXTRAPOLATED.
UNCERTAIN: every other cell with a probability. NO_SUPPORT: the NO_SUPPORT zone.
The same rule at the training-prevalence threshold is stored as a sensitivity classification (not used in the headline).
"""

from __future__ import annotations

import numpy as np

from kambale.objective_5.config import (CLASS_ABSENT, CLASS_NO_SUPPORT, CLASS_PRESENT, CLASS_UNCERTAIN, NO_SUPPORT,
                                        StopError, load_config)
from kambale.objective_5.config import utc_now
from kambale.objective_5.grid import DEPTH_EXTRAPOLATED


def classify_arrays(p_lo, p_hi, disagreement, zone, depth_support, threshold: float, limit: float) -> np.ndarray:
    """Class label for every cell. Pure function; the truth table is tested."""
    p_lo = np.asarray(p_lo, dtype=np.float64)
    p_hi = np.asarray(p_hi, dtype=np.float64)
    dis = np.asarray(disagreement, dtype=np.float64)
    zone = np.asarray(zone, dtype=object)
    dep_ext = np.asarray(depth_support, dtype=object) == DEPTH_EXTRAPOLATED
    supported = zone != NO_SUPPORT
    with np.errstate(invalid="ignore"):
        ok_dis = dis < float(limit)
        present = supported & (p_lo >= float(threshold)) & ok_dis & ~dep_ext
        absent = supported & (p_hi < float(threshold)) & ok_dis & ~dep_ext
    out = np.full(zone.shape, CLASS_UNCERTAIN, dtype=object)
    out[present] = CLASS_PRESENT
    out[absent] = CLASS_ABSENT
    out[~supported] = CLASS_NO_SUPPORT
    return out


def classify_all(o5, cfg: dict) -> dict:
    rules = cfg["classification"]
    threshold = float(rules["decision_threshold"])
    limit = float(rules["disagreement_limit"])
    prevalence = float(o5.execute("SELECT prevalence FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()[0])
    rows = o5.execute("SELECT cell_id, zone, depth_support, p_lo, p_hi, disagreement FROM grid_cells ORDER BY cell_id"
                      ).fetchall()
    cell_id = np.array([r["cell_id"] for r in rows], dtype=np.int64)
    zone = np.array([r["zone"] for r in rows], dtype=object)
    depth = np.array([r["depth_support"] for r in rows], dtype=object)
    p_lo = np.array([np.nan if r["p_lo"] is None else r["p_lo"] for r in rows], dtype=np.float64)
    p_hi = np.array([np.nan if r["p_hi"] is None else r["p_hi"] for r in rows], dtype=np.float64)
    dis = np.array([np.nan if r["disagreement"] is None else r["disagreement"] for r in rows], dtype=np.float64)
    labels = classify_arrays(p_lo, p_hi, dis, zone, depth, threshold, limit)
    sens = classify_arrays(p_lo, p_hi, dis, zone, depth, prevalence, limit)
    supported = zone != NO_SUPPORT
    if np.any(supported & ~np.isfinite(p_lo)) or np.any(supported & ~np.isfinite(p_hi)):
        raise StopError("a supported cell has no bootstrap interval; run the bootstrap stage first")
    o5.execute("BEGIN IMMEDIATE")
    try:
        o5.execute("DELETE FROM classification_rules")
        o5.execute("INSERT INTO classification_rules (rule_id, decision_threshold, prevalence_threshold, "
                   "disagreement_limit, statement) VALUES (?, ?, ?, ?, ?)",
                   (cfg["config_version"], threshold, prevalence,
                    limit, "CONFIDENT_PRESENT: p_lo >= threshold, disagreement < limit, not DEPTH_EXTRAPOLATED; "
                           "CONFIDENT_ABSENT: p_hi < threshold, disagreement < limit, not DEPTH_EXTRAPOLATED; "
                           "UNCERTAIN otherwise; NO_SUPPORT in the NO_SUPPORT zone. Sensitivity uses the training prevalence."))
        o5.executemany("UPDATE grid_cells SET class_label = ?, class_at_prevalence = ? WHERE cell_id = ?",
                       [(str(labels[k]), str(sens[k]), int(cell_id[k])) for k in range(cell_id.size)])
        o5.execute("COMMIT")
    except Exception:
        if o5.in_transaction:
            o5.execute("ROLLBACK")
        raise
    counts = {}
    for lab in (CLASS_PRESENT, CLASS_ABSENT, CLASS_UNCERTAIN, CLASS_NO_SUPPORT):
        counts[lab] = int(np.sum(labels == lab))
    return {"threshold": threshold, "prevalence_threshold": prevalence, "disagreement_limit": limit,
            "classes": counts, "sensitivity_classes": {lab: int(np.sum(sens == lab)) for lab in
                                                        (CLASS_PRESENT, CLASS_ABSENT, CLASS_UNCERTAIN, CLASS_NO_SUPPORT)},
            "completed_utc": utc_now()}

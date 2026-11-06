"""Final refits: each tier's selected and runner-up model, refitted once on all binary intervals with the Objective 3 rules.

The weathering-front feature of a training row uses the observed front surface of every other hole (its own hole is left
out), as in Objective 3. Fitted models are saved as joblib artifacts with SHA-256 records. In-sample Brier and AUC are fit
diagnostics only. The full-data hyperparameters are compared with the most frequent Objective 3 per-fold choice (WARN).
"""

from __future__ import annotations

import json
from collections import Counter

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

from kambale.objective_3 import models
from kambale.objective_3.config import load_config as load_o3_config
from kambale.objective_3.features import predictor_sets
from kambale.objective_5.config import (O3_CONFIG_PATH, O3_DB_PATH, O5_ARTIFACT_DIR, StopError, rel, sha256_file,
                                        utc_now)
from kambale.objective_5.db import connect_readonly
from kambale.objective_5.fitting import check_predictors, fit_candidate
from kambale.objective_5.front import depth_below_front, design_matrix, front_surface

def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=float)


def load_binary_training(o5) -> dict:
    rows = o5.execute("SELECT upstream_interval_id, hole_id, easting_m, northing_m, z_relative_m, indicator "
                      "FROM observations WHERE in_binary_target = 1 ORDER BY upstream_interval_id").fetchall()
    holes = sorted({r["hole_id"] for r in rows})
    index = {h: i for i, h in enumerate(holes)}
    return {
        "ids": np.array([r["upstream_interval_id"] for r in rows], dtype=np.int64),
        "hole_name": [r["hole_id"] for r in rows],
        "hole": np.array([index[r["hole_id"]] for r in rows], dtype=np.int64),
        "E": np.array([r["easting_m"] for r in rows], dtype=np.float64),
        "N": np.array([r["northing_m"] for r in rows], dtype=np.float64),
        "Z": np.array([r["z_relative_m"] for r in rows], dtype=np.float64),
        "y": np.array([r["indicator"] for r in rows], dtype=np.int64),
        "holes": holes,
    }


def load_fronts(o5) -> dict:
    rows = o5.execute("SELECT hole_id, easting_m, northing_m, front_z_m FROM hole_fronts ORDER BY hole_id").fetchall()
    names = [r["hole_id"] for r in rows]
    return {"names": names, "index": {h: i for i, h in enumerate(names)},
            "xy": np.array([[r["easting_m"], r["northing_m"]] for r in rows], dtype=np.float64).reshape(-1, 2),
            "z": np.array([r["front_z_m"] for r in rows], dtype=np.float64)}


def front_settings(o3_cfg: dict) -> dict:
    surf = o3_cfg["features"]["derived"]["depth_below_weathering_front_m"]["surface"]
    return {"power": float(surf["power"]), "k": int(surf["n_neighbours"]),
            "coincident": float(surf["coincident_distance_m"])}


def training_features(data: dict, fronts: dict, predictors, settings: dict) -> np.ndarray:
    """Design matrix for the binary intervals with the full-data front (own hole excluded)."""
    xy = np.column_stack([data["E"], data["N"]])
    own = np.array([fronts["index"].get(h, -1) for h in data["hole_name"]], dtype=np.int64)
    dbf = None
    if "depth_below_weathering_front_m" in predictors:
        surf = front_surface(fronts["xy"], fronts["z"], xy, exclude=own, power=settings["power"], k=settings["k"],
                             coincident=settings["coincident"])
        if not np.all(np.isfinite(surf)):
            raise StopError("the training weathering-front surface is undefined for some rows")
        dbf = depth_below_front(surf, data["Z"])
    return design_matrix(predictors, easting=data["E"], northing=data["N"], z=data["Z"], dbf=dbf)


def o3_selection_summary(o3, split_plan_id: str, candidate: str, full_params: dict) -> dict:
    rows = o3.execute("SELECT hyperparameters_json FROM training_runs WHERE split_plan_id = ? AND candidate_run_id = ? "
                      "AND status = 'COMPLETED'", (split_plan_id, candidate)).fetchall()
    counts = Counter(canonical(json.loads(r["hyperparameters_json"])) for r in rows)
    if not counts:
        return {"folds": 0, "mode": None, "count": 0, "tied": 0, "matches": False}
    top = max(counts.values())
    modes = sorted(k for k, v in counts.items() if v == top)
    full = canonical(full_params)
    tied = len(modes) > 1
    # A tie has no single most frequent choice, so the full-data choice is reported as not matching it.
    return {"folds": int(sum(counts.values())), "mode": modes[0], "count": int(top), "tied": int(tied),
            "matches": (not tied) and full == modes[0], "full": full, "all_modes": modes}


def refit_all(o5, config: dict, created: str | None = None) -> list[dict]:
    created = created or utc_now()
    o3_cfg, _ = load_o3_config(O3_CONFIG_PATH)
    settings = front_settings(o3_cfg)
    seed = int(o3_cfg["seeds"][0])
    data = load_binary_training(o5)
    fronts = load_fronts(o5)
    o5.execute("DELETE FROM final_refits")
    o3 = connect_readonly(O3_DB_PATH)
    results = []
    try:
        for hd in o5.execute("SELECT * FROM handoffs ORDER BY tier").fetchall():
            tier = hd["tier"]
            for role, candidate in (("SELECTED", hd["selected_model_id"]), ("RUNNER_UP", hd["runner_up_model_id"])):
                pset = models.predictor_set(candidate, o3_cfg)
                predictors = predictor_sets(o3_cfg)[pset]
                check_predictors(o3_cfg, candidate, predictors)
                X = training_features(data, fronts, predictors, settings)
                fm = fit_candidate(candidate, X, data["y"], data["hole"], o3_cfg, seed, predictors)
                p_in = fm.predict(X)
                brier = float(np.mean((p_in - data["y"]) ** 2))
                auc = float(roc_auc_score(data["y"], p_in)) if 0 < data["y"].sum() < data["y"].size else None
                O5_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
                tag = tier.split("_")[1]
                path = O5_ARTIFACT_DIR / f"tier{tag}_{role.lower()}_{candidate}.joblib"
                joblib.dump({"model": fm, "tier": tier, "role": role, "predictors": list(predictors),
                             "candidate": candidate, "config_version": config["config_version"],
                             "front_settings": settings, "seed": seed, "created_utc": created}, path)
                sha = sha256_file(path)
                o3sum = o3_selection_summary(o3, hd["split_plan_id"], candidate, fm.params)
                cal = fm.calibration
                o5.execute(
                    "INSERT INTO final_refits (tier, role, model_id, predictor_set, predictors_json, model_class, "
                    "hyperparameters_json, inner_cv_score, inner_cv_score_sd, calibration_status, calibration_intercept, "
                    "calibration_slope, calibration_n_inner, n_train, n_positive, in_sample_brier, in_sample_auc, "
                    "o3_split_plan_id, o3_folds_selected, o3_most_frequent_json, o3_most_frequent_count, o3_modes_tied, "
                    "full_data_matches_o3_mode, artifact_path, artifact_sha256, status, created_utc) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RUN', ?)",
                    (tier, role, candidate, pset, json.dumps(predictors), models.model_class(candidate, o3_cfg),
                     canonical(fm.params), fm.inner_score, fm.inner_sd, cal["status"], cal.get("intercept"),
                     cal.get("slope"), cal.get("n_inner"), int(data["y"].size), int(data["y"].sum()), brier, auc,
                     hd["split_plan_id"], o3sum["folds"], o3sum["mode"], o3sum["count"], o3sum["tied"],
                     int(bool(o3sum["matches"])), rel(path), sha, created))
                results.append({"tier": tier, "role": role, "model_id": candidate, "params": fm.params,
                                "calibration": {k: cal.get(k) for k in ("status", "intercept", "slope", "n_inner")},
                                "in_sample_brier": brier, "in_sample_auc": auc, "o3": o3sum,
                                "artifact": rel(path), "sha256": sha, "n_train": int(data["y"].size)})
    finally:
        o3.close()
    return results

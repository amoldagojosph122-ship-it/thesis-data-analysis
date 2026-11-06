-- O3-T02 split-by-split hyperparameters, variogram parameters, stability and calibration diagnostics.
-- name: split_hyperparameters_variograms_calibration
SELECT t.fold_id AS fold_id, t.family_id AS family_id, t.candidate_run_id AS candidate_run_id
     , 'HYPERPARAMETERS' AS record_type, '' AS model, t.status AS fit_status, 0 AS n_bins_used
     , NULL AS nugget, NULL AS structured_sill, NULL AS range_m, t.inner_cv_score AS inner_cv_score
     , t.inner_cv_score_sd AS inner_cv_sd, '' AS stability, t.threshold AS threshold
     , t.hyperparameters_json AS detail
FROM training_runs t
WHERE t.split_plan_id = :split_plan_id
UNION ALL
SELECT t.fold_id, t.family_id, t.candidate_run_id, 'INDICATOR_FIT', v.model, v.fit_status, v.n_bins_used
     , v.nugget, v.structured_sill, v.range_m, NULL, NULL, v.stability_status, NULL
     , v.reason
FROM variogram_training_fits v
JOIN training_runs t ON t.training_run_id = v.training_run_id
WHERE t.split_plan_id = :split_plan_id
UNION ALL
SELECT t.fold_id, t.family_id, t.candidate_run_id, 'RESIDUAL_FIT', v.model, v.fit_status, v.n_bins_used
     , v.nugget, v.structured_sill, v.range_m, NULL, NULL, v.stability_status, NULL
     , v.reason || '; fallback ' || v.fallback_status
FROM hybrid_residual_variogram v
JOIN training_runs t ON t.training_run_id = v.training_run_id
WHERE t.split_plan_id = :split_plan_id
UNION ALL
SELECT t.fold_id, t.family_id, t.candidate_run_id, 'CALIBRATION', c.method, c.status, c.n_inner
     , c.intercept, c.slope, NULL, NULL, NULL, '', NULL
     , c.reason
FROM calibration_fits c
JOIN training_runs t ON t.training_run_id = c.training_run_id
WHERE t.split_plan_id = :split_plan_id
ORDER BY fold_id, family_id, record_type, model;

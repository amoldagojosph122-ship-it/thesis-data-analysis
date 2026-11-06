-- O3-F04 M2 out-of-fold probability sections for held-out lines, Random Forest and gradient boosting.
-- name: m2_predictions
SELECT p.fold_id, p.family_id, p.candidate_run_id, p.observation_id, p.line_code, p.p_calibrated,
       p.clipped_calibrated, o.easting_m, o.northing_m, o.z_relative_m, o.depth_from_m
FROM predictions_oof p
JOIN training_runs t ON t.training_run_id = p.training_run_id
JOIN analysis_observations o ON o.receipt_id = t.receipt_id AND o.upstream_interval_id = p.observation_id
WHERE p.split_plan_id = :split_plan_id AND p.family_id IN ('M2_RF','M2_HGB')
ORDER BY p.fold_id, p.family_id, p.observation_id;
-- name: fold_lines
SELECT DISTINCT fold_id, line_code
FROM split_membership
WHERE split_plan_id = :split_plan_id AND role = 'TEST'
ORDER BY fold_id, line_code;
-- name: selected_m2
SELECT fold_id, json_extract(hyperparameters_json, '$.selected_candidate') AS candidate_run_id, inner_cv_score
FROM training_runs
WHERE split_plan_id = :split_plan_id AND family_id = 'M2_SEL'
ORDER BY fold_id;

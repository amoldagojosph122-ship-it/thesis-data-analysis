-- O3-F05 M3 hybrid out-of-fold probabilities, aligned with the selected M2 trend.
-- name: m3_predictions
SELECT p.fold_id, p.observation_id, p.line_code, p.p_calibrated, p.clipped_calibrated,
       o.easting_m, o.northing_m, o.z_relative_m, t.status, t.reason
FROM predictions_oof p
JOIN training_runs t ON t.training_run_id = p.training_run_id
JOIN analysis_observations o ON o.receipt_id = t.receipt_id AND o.upstream_interval_id = p.observation_id
WHERE p.split_plan_id = :split_plan_id AND p.family_id = 'M3_HYBRID'
ORDER BY p.fold_id, p.observation_id;
-- name: selected_m2_predictions
SELECT p.fold_id, p.observation_id, p.candidate_run_id, p.p_calibrated, p.clipped_calibrated,
       o.easting_m, o.northing_m, o.z_relative_m
FROM predictions_oof p
JOIN training_runs t ON t.training_run_id = p.training_run_id
JOIN analysis_observations o ON o.receipt_id = t.receipt_id AND o.upstream_interval_id = p.observation_id
WHERE p.split_plan_id = :split_plan_id AND t.selected = 1
ORDER BY p.fold_id, p.observation_id;
-- name: m2_predictions
SELECT p.fold_id, p.family_id, p.observation_id, p.line_code, p.p_calibrated, p.clipped_calibrated,
       o.easting_m, o.northing_m, o.z_relative_m
FROM predictions_oof p
JOIN training_runs t ON t.training_run_id = p.training_run_id
JOIN analysis_observations o ON o.receipt_id = t.receipt_id AND o.upstream_interval_id = p.observation_id
WHERE p.split_plan_id = :split_plan_id AND p.family_id IN ('M2_RF','M2_HGB')
ORDER BY p.fold_id, p.family_id, p.observation_id;
-- name: m3_status
SELECT fold_id, status, reason, hyperparameters_json
FROM training_runs
WHERE split_plan_id = :split_plan_id AND family_id = 'M3_HYBRID'
ORDER BY fold_id;

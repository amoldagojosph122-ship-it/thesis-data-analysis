-- O3-F03 M1 indicator-kriging out-of-fold probabilities, and the M1 status by fold.
-- name: m1_predictions
SELECT p.fold_id, p.observation_id, p.line_code, p.p_calibrated, p.clipped_calibrated,
       o.easting_m, o.northing_m, o.z_relative_m
FROM predictions_oof p
JOIN training_runs t ON t.training_run_id = p.training_run_id
JOIN analysis_observations o ON o.receipt_id = t.receipt_id AND o.upstream_interval_id = p.observation_id
WHERE p.split_plan_id = :split_plan_id AND p.family_id = 'M1_IK'
ORDER BY p.fold_id, p.observation_id;
-- name: m1_status
SELECT fold_id, status, reason, hyperparameters_json
FROM training_runs
WHERE split_plan_id = :split_plan_id AND family_id = 'M1_IK'
ORDER BY fold_id;

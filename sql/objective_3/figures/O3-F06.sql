-- O3-F06 inner-CV covariance selection for M1 and M3, one row per grid point and outer fold.
-- name: covariance_trials
SELECT t.fold_id, t.family_id, h.hyperparameters_json, h.inner_cv_score, h.inner_cv_score_sd, h.rank, h.selected,
       h.status
FROM hyperparameter_trials h
JOIN training_runs t ON t.training_run_id = h.training_run_id
WHERE t.split_plan_id = :split_plan_id AND t.family_id IN ('M1_IK', 'M3_HYBRID')
ORDER BY t.family_id, t.fold_id, h.trial_id;
-- name: selected_covariance
SELECT t.fold_id, t.family_id, t.status, t.reason, t.hyperparameters_json
FROM training_runs t
WHERE t.split_plan_id = :split_plan_id AND t.family_id IN ('M1_IK', 'M3_HYBRID')
ORDER BY t.family_id, t.fold_id;

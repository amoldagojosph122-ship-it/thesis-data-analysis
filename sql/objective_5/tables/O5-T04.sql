-- O5-T04 final-refit record: selected hyperparameters, calibration and in-sample fit (a fit diagnostic, not validation).
-- name: final_refit_record
SELECT tier, role, model_id, model_class, predictors_json, hyperparameters_json, inner_cv_score, inner_cv_score_sd,
       calibration_status, calibration_intercept, calibration_slope, calibration_n_inner, n_train, n_positive,
       in_sample_brier, in_sample_auc, o3_split_plan_id, o3_folds_selected, o3_most_frequent_json,
       o3_most_frequent_count, o3_modes_tied, full_data_matches_o3_mode, artifact_path, artifact_sha256
FROM final_refits
ORDER BY tier, CASE role WHEN 'SELECTED' THEN 0 ELSE 1 END;

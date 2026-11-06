-- O3-T04 fitted model-artifact registry and the pending Objective 5 final-refit contract.
-- name: artifact_registry_and_final_refit
SELECT 'ARTIFACT' AS record_type, t.fold_id AS fold_id, t.family_id AS family_id
     , t.candidate_run_id AS candidate_run_id, t.model_class AS model_class, t.status AS status
     , t.inner_cv_score AS inner_cv_score, a.artifact_path AS artifact_path, a.artifact_sha256 AS artifact_sha256
     , a.bytes AS bytes, a.created_utc AS created_utc, a.artifact_kind AS detail
FROM model_artifacts a
JOIN training_runs t ON t.training_run_id = a.training_run_id
WHERE t.split_plan_id = :split_plan_id
UNION ALL
SELECT 'FINAL_REFIT' AS record_type, NULL AS fold_id, f.family_id AS family_id, f.candidate_run_id AS candidate_run_id
     , '' AS model_class, f.status AS status, NULL AS inner_cv_score, COALESCE(f.artifact_path, '') AS artifact_path
     , COALESCE(f.artifact_sha256, '') AS artifact_sha256, 0 AS bytes, f.created_utc AS created_utc
     , f.reason AS detail
FROM final_refits f
ORDER BY record_type, fold_id, family_id;

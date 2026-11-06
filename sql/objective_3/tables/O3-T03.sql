-- O3-T03 out-of-fold completeness, class coverage and leakage auditing by family, fold and line.
-- name: completeness_and_leakage
SELECT 'FOLD_FAMILY' AS section, a.fold_id AS fold_id, '' AS line_code, f.family_id AS family_id
     , a.n_test AS expected, COALESCE(p.predicted, 0) AS predicted, COALESCE(q.failed, 0) AS failed
     , COALESCE(p.clipped, 0) AS clipped, a.test_positive AS positive_true
     , COALESCE(p.positive_pred, 0) AS positive_pred
     , CASE WHEN COALESCE(p.predicted, 0) + COALESCE(q.failed, 0) = a.n_test THEN 'COMPLETE' ELSE 'GAP' END AS status
     , 'minimum test-to-train collar distance ' || COALESCE(CAST(a.min_train_test_collar_distance_m AS TEXT), 'n/a') AS detail
FROM split_audit a
CROSS JOIN (SELECT DISTINCT family_id FROM training_runs WHERE split_plan_id = :split_plan_id) f
LEFT JOIN (
    SELECT fold_id, family_id, COUNT(*) AS predicted, SUM(clipped_calibrated) AS clipped,
           SUM(predicted_class) AS positive_pred
    FROM predictions_oof WHERE split_plan_id = :split_plan_id GROUP BY fold_id, family_id
) p ON p.fold_id = a.fold_id AND p.family_id = f.family_id
LEFT JOIN (
    SELECT fold_id, family_id, COUNT(*) AS failed
    FROM prediction_failures WHERE split_plan_id = :split_plan_id GROUP BY fold_id, family_id
) q ON q.fold_id = a.fold_id AND q.family_id = f.family_id
WHERE a.split_plan_id = :split_plan_id
UNION ALL
SELECT 'LINE_FAMILY' AS section, p.fold_id AS fold_id, p.line_code AS line_code, p.family_id AS family_id
     , COUNT(*) AS expected, COUNT(*) AS predicted, 0 AS failed, SUM(p.clipped_calibrated) AS clipped
     , SUM(p.true_label) AS positive_true, SUM(p.predicted_class) AS positive_pred
     , CASE WHEN SUM(p.clipped_calibrated) = 0 THEN 'COMPLETE' ELSE 'COMPLETE_WITH_CLIPPING' END AS status
     , 'observations in the held-out line; mean p ' || ROUND(AVG(p.p_calibrated), 4) AS detail
FROM predictions_oof p
WHERE p.split_plan_id = :split_plan_id
GROUP BY p.fold_id, p.line_code, p.family_id
UNION ALL
SELECT 'LEAKAGE' AS section, NULL AS fold_id, '' AS line_code, '' AS family_id
     , 0 AS expected, 0 AS predicted, 0 AS failed, 0 AS clipped, 0 AS positive_true, 0 AS positive_pred
     , status, check_name || ': ' || detail
FROM leakage_audit_log
ORDER BY section, fold_id, family_id, line_code;

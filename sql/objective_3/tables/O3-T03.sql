-- O3-T03 out-of-fold completeness, class coverage and leakage auditing by split plan, family, fold and line.
-- name: completeness_and_leakage
SELECT 'FOLD_FAMILY' AS section, a.split_plan_id AS split_plan_id, a.fold_id AS fold_id, '' AS line_code,
       f.family_id AS family_id, a.n_test AS expected, COALESCE(p.predicted, 0) AS predicted,
       COALESCE(q.failed, 0) AS failed, COALESCE(p.clipped, 0) AS clipped, a.test_positive AS positive_true,
       COALESCE(p.positive_pred, 0) AS positive_pred,
       CASE WHEN COALESCE(p.predicted, 0) + COALESCE(q.failed, 0) = a.n_test THEN 'COMPLETE' ELSE 'GAP' END AS status,
       'minimum test-to-train collar distance ' || COALESCE(CAST(a.min_train_test_collar_distance_m AS TEXT), 'n/a') AS detail
FROM split_audit a
JOIN (SELECT DISTINCT split_plan_id, family_id FROM training_runs) f ON f.split_plan_id = a.split_plan_id
LEFT JOIN (
    SELECT split_plan_id, fold_id, family_id, COUNT(*) AS predicted, SUM(clipped_calibrated) AS clipped,
           SUM(predicted_class) AS positive_pred
    FROM predictions_oof GROUP BY split_plan_id, fold_id, family_id
) p ON p.split_plan_id = a.split_plan_id AND p.fold_id = a.fold_id AND p.family_id = f.family_id
LEFT JOIN (
    SELECT split_plan_id, fold_id, family_id, COUNT(*) AS failed
    FROM prediction_failures GROUP BY split_plan_id, fold_id, family_id
) q ON q.split_plan_id = a.split_plan_id AND q.fold_id = a.fold_id AND q.family_id = f.family_id
UNION ALL
SELECT 'LINE_FAMILY' AS section, p.split_plan_id AS split_plan_id, p.fold_id AS fold_id, p.line_code AS line_code,
       p.family_id AS family_id, COUNT(*) AS expected, COUNT(*) AS predicted, 0 AS failed,
       SUM(p.clipped_calibrated) AS clipped, SUM(p.true_label) AS positive_true, SUM(p.predicted_class) AS positive_pred,
       CASE WHEN SUM(p.clipped_calibrated) = 0 THEN 'COMPLETE' ELSE 'COMPLETE_WITH_CLIPPING' END AS status,
       'observations in the held-out line; mean p ' || ROUND(AVG(p.p_calibrated), 4) AS detail
FROM predictions_oof p
GROUP BY p.split_plan_id, p.fold_id, p.line_code, p.family_id
UNION ALL
SELECT 'LEAKAGE' AS section, NULL AS split_plan_id, NULL AS fold_id, '' AS line_code, '' AS family_id,
       0 AS expected, 0 AS predicted, 0 AS failed, 0 AS clipped, 0 AS positive_true, 0 AS positive_pred,
       status, check_name || ': ' || detail AS detail
FROM leakage_audit_log
ORDER BY section, split_plan_id, fold_id, family_id, line_code;

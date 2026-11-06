-- O4-F03 ROC and precision-recall curves for the feasible models.
-- name: curve_points
SELECT p.model_id, p.curve, p.point_index, p.threshold, p.tpr, p.fpr, p.precision, p.recall, p.n
FROM metric_curve_points p JOIN candidate_registry r ON r.model_id = p.model_id
WHERE r.comparable = 1
ORDER BY p.model_id, p.curve, p.point_index;
-- name: discrimination
SELECT model_id, metric_id, value, status, n, n_positive
FROM pooled_metrics
WHERE weighting = 'INTERVAL' AND metric_id IN ('ROC_AUC', 'PR_AUC')
ORDER BY model_id, metric_id;
-- name: prevalence
SELECT AVG(true_label) AS prevalence, COUNT(*) AS n, SUM(true_label) AS n_positive
FROM evaluation_population WHERE in_common_cohort = 1;

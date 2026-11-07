-- O4-F02 Brier score by model and held-out line.
-- name: pooled_brier
SELECT m.model_id, m.value AS brier, m.n, m.n_positive, r.role
FROM pooled_metrics m JOIN candidate_registry r ON r.model_id = m.model_id
WHERE m.weighting = 'INTERVAL' AND m.metric_id = 'BRIER' AND r.comparable = 1
ORDER BY m.value;
-- name: line_brier
SELECT p.model_id, e.line_code,
       AVG((p.selected_probability - e.true_label) * (p.selected_probability - e.true_label)) AS brier,
       COUNT(*) AS n
FROM prediction_snapshot p
JOIN evaluation_population e ON e.receipt_id = p.receipt_id AND e.observation_id = p.observation_id
JOIN candidate_registry r ON r.model_id = p.model_id
WHERE e.in_common_cohort = 1 AND r.comparable = 1
GROUP BY p.model_id, e.line_code
ORDER BY p.model_id, e.line_code;
-- name: identities
SELECT model_id, identical_to, role
FROM candidate_registry
WHERE identity_status = 'IDENTICAL_TO'
ORDER BY model_id;

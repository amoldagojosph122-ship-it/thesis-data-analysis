-- O4-F07 coverage and missing-prediction plot.
-- name: coverage
SELECT c.model_id, c.n_expected, c.n_predicted, c.n_failed, c.coverage, c.status,
       r.role, r.comparable, r.fallback_identical_to
FROM prediction_coverage c JOIN candidate_registry r ON r.model_id = c.model_id
ORDER BY r.comparable DESC, c.coverage DESC, c.model_id;
-- name: coverage_by_line
SELECT m.model_id, l.line_code, l.n AS expected,
       (SELECT COUNT(*) FROM prediction_snapshot p
        JOIN evaluation_population e ON e.receipt_id = p.receipt_id AND e.observation_id = p.observation_id
        WHERE p.model_id = m.model_id AND e.line_code = l.line_code AND e.in_common_cohort = 1) AS predicted
FROM (SELECT DISTINCT model_id FROM candidate_registry) m
CROSS JOIN (SELECT line_code, COUNT(*) AS n FROM evaluation_population GROUP BY line_code) l
ORDER BY m.model_id, l.line_code;

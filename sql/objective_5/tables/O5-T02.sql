-- O5-T02 sensitivity of the class counts to the decision threshold: the headline threshold against the training prevalence.
-- name: threshold_sensitivity
WITH meta AS (SELECT (SELECT CAST(meta_value AS REAL) FROM grid_meta WHERE meta_key = 'cell_volume_m3') AS cell_m3),
rule AS (SELECT decision_threshold, prevalence_threshold FROM classification_rules LIMIT 1),
stacked AS (
    SELECT 'HEADLINE' AS threshold_use, g.zone AS zone, g.class_label AS class_label FROM grid_cells g
    UNION ALL
    SELECT 'SENSITIVITY_PREVALENCE', g.zone, g.class_at_prevalence FROM grid_cells g
)
SELECT s.threshold_use AS threshold_use,
       CASE s.threshold_use WHEN 'HEADLINE' THEN r.decision_threshold ELSE r.prevalence_threshold END AS threshold,
       s.zone AS zone,
       s.class_label AS class_label,
       COUNT(*) AS cells,
       ROUND(COUNT(*) * m.cell_m3, 1) AS relative_volume_m3
FROM stacked s CROSS JOIN rule r CROSS JOIN meta m
GROUP BY s.threshold_use, s.zone, s.class_label
ORDER BY s.threshold_use DESC,
         CASE s.zone WHEN 'INTERPOLATION' THEN 0 WHEN 'EXTRAPOLATION' THEN 1 ELSE 2 END,
         s.class_label;

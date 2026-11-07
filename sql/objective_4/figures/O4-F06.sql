-- O4-F06 spatial map of residuals on the withheld observations for the selected model.
-- name: selected
SELECT model_id, role, improvement_status, selection_basis, delta_brier, ci_low, ci_high, coverage
FROM comparison_decisions WHERE role = 'SELECTED';
-- name: selected_errors
SELECT e.line_code, e.fold_id, e.easting_m, e.northing_m, e.z_relative_m, e.true_label,
       p.selected_probability, p.predicted_class,
       (e.true_label - p.selected_probability) AS residual
FROM prediction_snapshot p
JOIN evaluation_population e ON e.receipt_id = p.receipt_id AND e.observation_id = p.observation_id
JOIN comparison_decisions d ON d.model_id = p.model_id AND d.role = 'SELECTED'
WHERE e.in_common_cohort = 1
ORDER BY e.line_code, e.depth_from_m;

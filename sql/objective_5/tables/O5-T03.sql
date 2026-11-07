-- O5-T03 validated skill carried from Objective 4 for the selected and runner-up models, beside the class counts of each zone.
-- name: validation_with_classes
SELECT h.tier AS validation_tier,
       g.zone AS zone,
       h.selected_model_id AS selected_model,
       (SELECT c.value FROM carried_validation c WHERE c.tier = h.tier AND c.role = 'SELECTED' AND c.metric_id = 'BRIER' AND c.weighting = 'INTERVAL') AS selected_pooled_brier,
       (SELECT c.value FROM carried_validation c WHERE c.tier = h.tier AND c.role = 'SELECTED' AND c.metric_id = 'ROC_AUC' AND c.weighting = 'INTERVAL') AS selected_pooled_roc_auc,
       h.runner_up_model_id AS runner_up_model,
       (SELECT c.value FROM carried_validation c WHERE c.tier = h.tier AND c.role = 'RUNNER_UP' AND c.metric_id = 'BRIER' AND c.weighting = 'INTERVAL') AS runner_up_pooled_brier,
       (SELECT c.value FROM carried_validation c WHERE c.tier = h.tier AND c.role = 'RUNNER_UP' AND c.metric_id = 'ROC_AUC' AND c.weighting = 'INTERVAL') AS runner_up_pooled_roc_auc,
       h.delta_brier AS delta_brier_selected_minus_runner_up,
       h.delta_brier_ci_low AS delta_ci_low,
       h.delta_brier_ci_high AS delta_ci_high,
       h.improvement_status AS improvement_status,
       SUM(CASE WHEN g.class_label = 'CONFIDENT_PRESENT' THEN 1 ELSE 0 END) AS confident_present_cells,
       SUM(CASE WHEN g.class_label = 'CONFIDENT_ABSENT' THEN 1 ELSE 0 END) AS confident_absent_cells,
       SUM(CASE WHEN g.class_label = 'UNCERTAIN' THEN 1 ELSE 0 END) AS uncertain_cells,
       COUNT(*) AS cells
FROM grid_cells g JOIN handoffs h ON h.tier = g.model_tier
WHERE g.zone IN ('INTERPOLATION', 'EXTRAPOLATION')
GROUP BY h.tier, g.zone
ORDER BY CASE g.zone WHEN 'INTERPOLATION' THEN 0 ELSE 1 END;

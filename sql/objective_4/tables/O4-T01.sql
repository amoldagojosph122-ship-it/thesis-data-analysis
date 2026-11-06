-- O4-T01 main evaluation summary.
-- name: evaluation_summary
SELECT r.model_id AS model_id, r.role AS role, r.comparable AS comparable,
       r.identity_status AS identity_status, r.identical_to AS identical_to,
       c.coverage AS coverage, c.n_predicted AS n_predicted, c.n_expected AS n_expected, c.n_failed AS n_failed,
       (SELECT value FROM pooled_metrics m WHERE m.model_id = r.model_id AND m.weighting = 'INTERVAL'
        AND m.metric_id = 'BRIER') AS brier_interval,
       (SELECT value FROM pooled_metrics m WHERE m.model_id = r.model_id AND m.weighting = 'EQUAL_HOLE'
        AND m.metric_id = 'BRIER') AS brier_equal_hole,
       (SELECT value FROM pooled_metrics m WHERE m.model_id = r.model_id AND m.weighting = 'INTERVAL'
        AND m.metric_id = 'LOG_LOSS') AS log_loss_interval,
       (SELECT value FROM pooled_metrics m WHERE m.model_id = r.model_id AND m.weighting = 'INTERVAL'
        AND m.metric_id = 'ROC_AUC') AS roc_auc,
       (SELECT value FROM pooled_metrics m WHERE m.model_id = r.model_id AND m.weighting = 'INTERVAL'
        AND m.metric_id = 'PR_AUC') AS pr_auc,
       (SELECT value FROM pooled_metrics m WHERE m.model_id = r.model_id AND m.weighting = 'INTERVAL'
        AND m.metric_id = 'ECE') AS ece,
       d.intercept AS calibration_intercept, d.slope AS calibration_slope, d.status AS calibration_status,
       dec.rank AS decision_rank, dec.improvement_status AS improvement_status,
       dec.selection_basis AS selection_basis
FROM candidate_registry r
JOIN prediction_coverage c ON c.model_id = r.model_id
LEFT JOIN calibration_diagnostics d ON d.model_id = r.model_id
LEFT JOIN comparison_decisions dec ON dec.model_id = r.model_id
ORDER BY CASE WHEN dec.rank IS NULL THEN 99 ELSE dec.rank END, r.model_id;

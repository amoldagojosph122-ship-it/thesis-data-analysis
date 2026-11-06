-- O4-T02 fold-by-fold scores.
-- name: fold_scores
WITH fm AS (
    SELECT model_id, fold_id,
           MAX(CASE WHEN metric_id = 'BRIER' THEN value END) AS brier,
           MAX(CASE WHEN metric_id = 'LOG_LOSS' THEN value END) AS log_loss,
           MAX(CASE WHEN metric_id = 'ROC_AUC' THEN value END) AS roc_auc,
           MAX(CASE WHEN metric_id = 'PR_AUC' THEN value END) AS pr_auc,
           MAX(CASE WHEN metric_id = 'ECE' THEN value END) AS ece,
           MAX(CASE WHEN metric_id = 'BRIER' THEN n END) AS n,
           MAX(CASE WHEN metric_id = 'BRIER' THEN n_positive END) AS n_positive,
           MAX(CASE WHEN metric_id = 'BRIER' THEN status END) AS status
    FROM fold_metrics WHERE weighting = 'INTERVAL'
    GROUP BY model_id, fold_id
), lines AS (
    SELECT DISTINCT fold_id, line_code FROM evaluation_population
)
SELECT fm.model_id AS model_id, fm.fold_id AS fold_id, l.line_code AS line_code, fm.n AS n,
       fm.n_positive AS n_positive, fm.brier AS brier, fm.log_loss AS log_loss, fm.roc_auc AS roc_auc,
       fm.pr_auc AS pr_auc, fm.ece AS ece, fm.status AS status
FROM fm JOIN lines l ON l.fold_id = fm.fold_id
ORDER BY fm.model_id, fm.fold_id;

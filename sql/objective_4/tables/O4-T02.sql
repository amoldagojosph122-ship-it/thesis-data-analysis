-- O4-T02 fold-by-fold scores. A fold is one held-out drill line (tier 1) or one interleaved hole fold (tier 2).
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
), folds AS (
    SELECT fold_id, COUNT(DISTINCT hole_id) AS n_holes, GROUP_CONCAT(DISTINCT line_code) AS lines_in_fold
    FROM evaluation_population GROUP BY fold_id
)
SELECT fm.model_id AS model_id, fm.fold_id AS fold_id, f.lines_in_fold AS lines_in_fold, f.n_holes AS n_holes,
       fm.n AS n, fm.n_positive AS n_positive, fm.brier AS brier, fm.log_loss AS log_loss, fm.roc_auc AS roc_auc,
       fm.pr_auc AS pr_auc, fm.ece AS ece, fm.status AS status
FROM fm JOIN folds f ON f.fold_id = fm.fold_id
ORDER BY fm.model_id, fm.fold_id;

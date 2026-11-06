-- O4-T03 confusion matrices and threshold provenance.
-- name: confusion
SELECT model_id, scope, fold_id, threshold, threshold_source, tp, fp, tn, fn,
       precision, recall, specificity, balanced_accuracy, f1, mcc, status, reason
FROM class_confusion_matrices
ORDER BY model_id, CASE WHEN scope = 'POOLED' THEN 0 ELSE 1 END, fold_id;

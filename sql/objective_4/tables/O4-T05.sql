-- O4-T05 final model-selection decision and handoff.
-- name: decision
SELECT d.rank AS rank, d.model_id AS model_id, d.role AS role, r.identity_status AS identity_status,
       r.identical_to AS identical_to, d.improvement_status AS improvement_status,
       d.selection_basis AS selection_basis, d.delta_brier AS delta_brier, d.ci_low AS ci_low, d.ci_high AS ci_high,
       d.fold_consistency AS fold_consistency, d.calibration_status AS calibration_status,
       d.discrimination_status AS discrimination_status, d.coverage AS coverage, d.reason AS reason,
       h.receipt_sha256 AS handoff_receipt_sha256
FROM comparison_decisions d
JOIN candidate_registry r ON r.model_id = d.model_id
LEFT JOIN locked_handoff_receipts h ON h.decision_id = d.decision_id
ORDER BY CASE WHEN d.rank IS NULL THEN 99 ELSE d.rank END, d.model_id;

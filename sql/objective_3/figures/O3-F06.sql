-- O3-F06 training-only residual variogram diagnostics by outer fold.
-- name: residual_bins
SELECT t.fold_id, b.bin_index, b.lag_centre_m, b.n_pairs, b.n_independent_hole_pairs, b.gamma, b.supported
FROM training_lag_bins b
JOIN training_runs t ON t.training_run_id = b.training_run_id
WHERE t.split_plan_id = :split_plan_id AND b.family_id = 'M3_HYBRID'
ORDER BY t.fold_id, b.bin_index;
-- name: residual_fits
SELECT t.fold_id, v.model, v.fit_status, v.n_bins_used, v.nugget, v.structured_sill, v.range_m,
       v.stability_status, v.supported, v.fallback_status, v.residual_variance, v.reason
FROM hybrid_residual_variogram v
JOIN training_runs t ON t.training_run_id = v.training_run_id
WHERE t.split_plan_id = :split_plan_id
ORDER BY t.fold_id, v.model;
-- name: fold_status
SELECT fold_id, status, reason
FROM training_runs
WHERE split_plan_id = :split_plan_id AND family_id = 'M3_HYBRID'
ORDER BY fold_id;

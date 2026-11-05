-- O2-F06 between-hole indicator semivariograms of one receipt: the lateral handoff basis and the three-dimensional
-- omnidirectional family (reported only). Fitted curves are drawn only for FITTED fits.
-- name: experimental_bins
SELECT e.direction_id, b.bin_index, b.lag_centre_m, b.n_pairs, b.n_independent_hole_pairs, b.gamma, b.supported
FROM variogram_lag_bins b
JOIN variogram_experiments e ON e.experiment_id = b.experiment_id
WHERE e.receipt_id = :receipt_id AND e.variant = 'BASE' AND e.direction_id IN ('LATERAL_BETWEEN', 'OMNI_3D_BETWEEN')
ORDER BY e.direction_id, b.bin_index;
-- name: marginal_variance
SELECT AVG(indicator) AS p, AVG(indicator) * (1.0 - AVG(indicator)) AS p_one_minus_p, COUNT(*) AS n_binary
FROM analysis_observations
WHERE receipt_id = :receipt_id AND in_binary_target = 1;
-- name: fit_status
SELECT e.direction_id, f.model, f.fit_status, f.stability_status, f.reason
FROM variogram_fits f
JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
WHERE e.receipt_id = :receipt_id AND e.variant = 'BASE' AND e.direction_id IN ('LATERAL_BETWEEN', 'OMNI_3D_BETWEEN')
ORDER BY e.direction_id, f.model;
-- name: fitted_parameters
SELECT e.direction_id, f.model, p.parameter, p.estimate
FROM variogram_fit_parameters p
JOIN variogram_fits f ON f.fit_id = p.fit_id
JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
WHERE e.receipt_id = :receipt_id AND e.variant = 'BASE' AND f.fit_status = 'FITTED'
  AND e.direction_id IN ('LATERAL_BETWEEN', 'OMNI_3D_BETWEEN')
ORDER BY e.direction_id, f.model, p.parameter;

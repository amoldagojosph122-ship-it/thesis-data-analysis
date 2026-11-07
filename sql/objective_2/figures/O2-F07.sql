-- O2-F07 horizontal azimuth semivariograms (exploratory). Supported bins carry a semivariance value; measured but
-- under-powered bins carry only their pair count. Direction status comes from direction_registry.
-- name: azimuth_bins
SELECT d.direction_id, d.azimuth_deg, d.angular_tolerance_deg, d.status AS direction_status,
       b.bin_index, b.lag_centre_m, b.n_pairs, b.n_independent_hole_pairs, b.gamma, b.supported, e.min_pairs_per_bin
FROM variogram_lag_bins b
JOIN variogram_experiments e ON e.experiment_id = b.experiment_id
JOIN direction_registry d ON d.receipt_id = e.receipt_id AND d.direction_id = e.direction_id
WHERE e.receipt_id = :receipt_id AND e.variant = 'BASE' AND d.family = 'HORIZONTAL_AZIMUTH'
ORDER BY d.azimuth_deg, b.bin_index;
-- name: marginal_variance
SELECT AVG(indicator) AS p, AVG(indicator) * (1.0 - AVG(indicator)) AS p_one_minus_p, COUNT(*) AS n_binary
FROM analysis_observations
WHERE receipt_id = :receipt_id AND in_binary_target = 1;

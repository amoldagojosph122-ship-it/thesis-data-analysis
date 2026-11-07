-- O2-F10 weathering front and fresh-rock indicator semivariograms (configuration 5, O2-CFG-2026.11.06-5). Rows come only from
-- the configuration-5 stage run. Leave-one-line-out refits are excluded here (they are summarised in O2-T03 and the report).
-- name: front_points
SELECT w.hole_id, w.line_code, w.easting_m, w.northing_m, w.front_z_relative_m, w.n_reversal_intervals
FROM weathering_front_observations w
WHERE w.receipt_id = :receipt_id AND w.config_version = 'O2-CFG-2026.11.06-5'
ORDER BY w.line_code, w.easting_m, w.hole_id;
-- name: fresh_bins
SELECT e.direction_id, b.bin_index, b.lag_centre_m, b.n_pairs, b.n_independent_hole_pairs, b.gamma, b.supported,
       g.gamma_lower, g.gamma_upper, g.gamma_median, g.n_replicates
FROM variogram_lag_bins b
JOIN variogram_experiments e ON e.experiment_id = b.experiment_id
LEFT JOIN bootstrap_gamma_bands g ON g.experiment_id = b.experiment_id AND g.bin_index = b.bin_index
WHERE e.receipt_id = :receipt_id AND e.config_version = 'O2-CFG-2026.11.06-5'
  AND e.direction_id IN ('LATERAL_FRESH_COLLAR', 'LATERAL_FRESH_FRONT')
  AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s WHERE s.experiment_id = e.experiment_id AND s.changed_factor = 'excluded_line')
ORDER BY e.direction_id, b.bin_index;
-- name: fresh_marginal
SELECT COUNT(*) AS n, AVG(indicator) AS p, AVG(indicator) * (1.0 - AVG(indicator)) AS p_one_minus_p
FROM analysis_observations
WHERE receipt_id = :receipt_id AND in_binary_target = 1 AND weathering_code IN ('mw', 'sw');
-- name: fitted_parameters
SELECT e.direction_id, f.model, p.parameter, p.estimate
FROM variogram_fit_parameters p
JOIN variogram_fits f ON f.fit_id = p.fit_id
JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
WHERE e.receipt_id = :receipt_id AND e.config_version = 'O2-CFG-2026.11.06-5'
  AND e.direction_id IN ('LATERAL_FRESH_COLLAR', 'LATERAL_FRESH_FRONT') AND f.fit_status = 'FITTED'
  AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s WHERE s.experiment_id = e.experiment_id AND s.changed_factor = 'excluded_line')
ORDER BY e.direction_id, f.model, p.parameter;
-- name: fit_status
SELECT e.direction_id, f.model, f.fit_status, f.stability_status
FROM variogram_fits f
JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
WHERE e.receipt_id = :receipt_id AND e.config_version = 'O2-CFG-2026.11.06-5'
  AND e.direction_id IN ('LATERAL_FRESH_COLLAR', 'LATERAL_FRESH_FRONT')
  AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s WHERE s.experiment_id = e.experiment_id AND s.changed_factor = 'excluded_line')
ORDER BY e.direction_id, f.model;

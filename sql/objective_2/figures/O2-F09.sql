-- O2-F09 configuration-3 exploratory lateral extension (50 m bins to 2000 m, relative-depth difference at most 3 m) with the
-- STRICT_SGS_v1 comparator. Rows come only from the configuration-3 stage run. Leave-one-line-out refits are excluded here;
-- their envelopes are summarised in the run report (RUN_REPORT.md section 5.7).
-- name: extension_bins
SELECT e.label_rule_id, b.bin_index, b.lag_centre_m, b.n_pairs, b.n_independent_hole_pairs, b.gamma, b.supported
FROM variogram_lag_bins b
JOIN variogram_experiments e ON e.experiment_id = b.experiment_id
WHERE e.receipt_id = :receipt_id AND e.config_version = 'O2-CFG-2026.11.05-3' AND e.direction_id = 'LATERAL_BETWEEN'
  AND e.lag_width_m = 50.0
  AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s WHERE s.experiment_id = e.experiment_id AND s.changed_factor = 'excluded_line')
ORDER BY e.label_rule_id, b.bin_index;
-- name: marginal_variance
SELECT 'DESIGN_8_2_v1' AS label_rule_id, AVG(indicator) AS p, AVG(indicator) * (1.0 - AVG(indicator)) AS p_one_minus_p,
       COUNT(*) AS n
FROM analysis_observations
WHERE receipt_id = :receipt_id AND in_binary_target = 1
UNION ALL
SELECT 'STRICT_SGS_v1', AVG(c.indicator), AVG(c.indicator) * (1.0 - AVG(c.indicator)), COUNT(*)
FROM comparator_observations c
JOIN analysis_observations a ON a.receipt_id = c.receipt_id AND a.upstream_interval_id = c.upstream_interval_id
WHERE c.receipt_id = :receipt_id AND c.rule_id = 'STRICT_SGS_v1' AND a.in_binary_target = 1;
-- name: fit_status
SELECT e.label_rule_id, f.model, f.fit_status, f.stability_status, f.reason
FROM variogram_fits f
JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
WHERE e.receipt_id = :receipt_id AND e.config_version = 'O2-CFG-2026.11.05-3' AND e.direction_id = 'LATERAL_BETWEEN'
  AND e.lag_width_m = 50.0
  AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s WHERE s.experiment_id = e.experiment_id AND s.changed_factor = 'excluded_line')
ORDER BY e.label_rule_id, f.model;
-- name: fitted_parameters
SELECT e.label_rule_id, f.model, p.parameter, p.estimate
FROM variogram_fit_parameters p
JOIN variogram_fits f ON f.fit_id = p.fit_id
JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
WHERE e.receipt_id = :receipt_id AND e.config_version = 'O2-CFG-2026.11.05-3' AND e.direction_id = 'LATERAL_BETWEEN'
  AND e.lag_width_m = 50.0 AND f.fit_status = 'FITTED'
  AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s WHERE s.experiment_id = e.experiment_id AND s.changed_factor = 'excluded_line')
ORDER BY e.label_rule_id, f.model, p.parameter;

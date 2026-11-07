-- O2-F08 sensitivity. Supported bins and fit status for each completed variant, and for each base experiment, of the
-- latest ANALYSE run of one receipt. Leave-one-line-out refits are excluded here (they appear in O2-T03).
-- name: sensitivity_rows
SELECT s.sensitivity_id, s.variant_name, s.changed_factor, s.changed_value, s.status, s.reason, e.direction_id,
       (SELECT COUNT(*) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS supported_bins,
       (SELECT f.fit_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'spherical') AS spherical_status,
       (SELECT f.fit_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'exponential') AS exponential_status
FROM sensitivity_runs s
LEFT JOIN variogram_experiments e ON e.experiment_id = s.experiment_id
WHERE s.run_id = (SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'ANALYSE' AND receipt_id = :receipt_id)
  AND s.changed_factor <> 'excluded_line'
ORDER BY s.sensitivity_id;
-- name: base_rows
SELECT e.direction_id,
       (SELECT COUNT(*) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS supported_bins,
       (SELECT f.fit_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'spherical') AS spherical_status,
       (SELECT f.fit_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'exponential') AS exponential_status
FROM variogram_experiments e
WHERE e.receipt_id = :receipt_id AND e.variant = 'BASE'
ORDER BY e.direction_id;

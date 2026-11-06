-- O2-T05 weathering front continuity and interpolation check (configuration 5, O2-CFG-2026.11.06-5): every diagnostic row of
-- weathering_front_diagnostics for the configuration-5 run. The interpolable flag is a decision row (1.0 = interpolable).
-- name: front_continuity
SELECT d.stat_group, d.stat_name, ROUND(d.stat_value, 4) AS stat_value, d.unit, d.n_basis
FROM weathering_front_diagnostics d
WHERE d.receipt_id = :receipt_id AND d.config_version = 'O2-CFG-2026.11.06-5'
ORDER BY d.stat_group, d.stat_name;

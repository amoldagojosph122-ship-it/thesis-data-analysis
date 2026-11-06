-- O4-F04 reliability diagrams for the feasible models.
-- name: bins
SELECT b.model_id, b.bin_index, b.bin_lower, b.bin_upper, b.n, b.mean_p, b.observed_rate,
       b.wilson_low, b.wilson_high, b.merged
FROM calibration_bins b JOIN candidate_registry r ON r.model_id = b.model_id
WHERE r.comparable = 1
ORDER BY b.model_id, b.bin_index;
-- name: diagnostics
SELECT d.model_id, d.n, d.intercept, d.slope, d.status,
       (SELECT value FROM pooled_metrics m WHERE m.model_id = d.model_id AND m.weighting = 'INTERVAL'
        AND m.metric_id = 'ECE') AS ece
FROM calibration_diagnostics d JOIN candidate_registry r ON r.model_id = d.model_id
WHERE r.comparable = 1
ORDER BY d.model_id;

-- O4-F05 paired Brier differences, model_b minus model_a, with the hole-cluster interval and their line-level pattern.
-- name: pooled_pairs
SELECT pair_id, model_a, model_b, delta_brier, ci_low, ci_high, ci_low_line, ci_high_line, power_label,
       detectable_half_width, n, status
FROM paired_differences
WHERE scope = 'POOLED' AND weighting = 'INTERVAL'
ORDER BY pair_id;
-- name: line_pairs
SELECT pair_id, line_code, delta_brier, n, status
FROM paired_differences
WHERE scope = 'LINE' AND weighting = 'INTERVAL' AND pair_id IN ('LOG_vs_LOGWF', 'RF_vs_RFWF', 'HGB_vs_HGBWF')
ORDER BY pair_id, line_code;

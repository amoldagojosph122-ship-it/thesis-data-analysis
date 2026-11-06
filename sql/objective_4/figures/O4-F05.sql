-- O4-F05 paired hybrid-versus-M2 and hybrid-versus-M1 contrasts by line.
-- name: line_pairs
SELECT pair_id, line_code, delta_brier, n, status
FROM paired_differences
WHERE scope = 'LINE' AND weighting = 'INTERVAL' AND pair_id IN ('M3_vs_M2_RF', 'M3_vs_M2_HGB')
ORDER BY pair_id, line_code;
-- name: pooled_pairs
SELECT pair_id, model_a, model_b, delta_brier, ci_low, ci_high, ci_low_line, ci_high_line, n, status
FROM paired_differences
WHERE scope = 'POOLED' AND weighting = 'INTERVAL' AND pair_id IN ('M3_vs_M2_RF', 'M3_vs_M2_HGB')
ORDER BY pair_id;
-- name: m1
SELECT model_id, n_expected, n_predicted, n_failed, coverage, status, reason
FROM prediction_coverage WHERE model_id = 'M1_IK';

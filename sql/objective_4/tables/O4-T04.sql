-- O4-T04 paired difference uncertainty and weighting sensitivity. Difference = Brier(model_b) minus Brier(model_a).
-- name: paired_uncertainty
SELECT p.pair_id AS pair_id, p.model_a AS model_a, p.model_b AS model_b, p.weighting AS weighting,
       p.delta_brier AS delta_brier_b_minus_a, p.delta_log_loss AS delta_log_loss_b_minus_a,
       p.ci_low AS ci_low_hole, p.ci_high AS ci_high_hole,
       p.ci_low_line AS ci_low_line, p.ci_high_line AS ci_high_line,
       CASE WHEN p.weighting = 'INTERVAL' THEN p.power_label END AS power_label,
       CASE WHEN p.weighting = 'INTERVAL' THEN p.detectable_half_width END AS detectable_half_width,
       (SELECT COUNT(*) FROM paired_differences f
        WHERE f.pair_id = p.pair_id AND f.scope = 'FOLD' AND f.weighting = p.weighting
          AND f.delta_brier < 0) AS folds_b_better,
       p.n AS n, p.status AS status, p.reason AS reason
FROM paired_differences p
WHERE p.scope = 'POOLED' AND p.weighting IN ('INTERVAL','EQUAL_HOLE')
ORDER BY p.pair_id, p.weighting;

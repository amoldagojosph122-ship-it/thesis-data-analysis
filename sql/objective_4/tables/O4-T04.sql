-- O4-T04 paired difference uncertainty and weighting sensitivity.
-- name: paired_uncertainty
SELECT p.pair_id AS pair_id, p.model_a AS model_a, p.model_b AS model_b, p.weighting AS weighting,
       p.delta_brier AS delta_brier, p.delta_log_loss AS delta_log_loss,
       p.ci_low AS ci_low_hole, p.ci_high AS ci_high_hole,
       p.ci_low_line AS ci_low_line, p.ci_high_line AS ci_high_line,
       (SELECT COUNT(*) FROM paired_differences f
        WHERE f.pair_id = p.pair_id AND f.scope = 'FOLD' AND f.weighting = p.weighting
          AND f.delta_brier < 0) AS folds_a_better,
       p.n AS n, p.status AS status, p.reason AS reason
FROM paired_differences p
WHERE p.scope = 'POOLED' AND p.weighting IN ('INTERVAL','EQUAL_HOLE')
ORDER BY p.pair_id, p.weighting;

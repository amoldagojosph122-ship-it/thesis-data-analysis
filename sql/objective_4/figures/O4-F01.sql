-- O4-F01 spatial holdout fold map and coverage overlay.
-- name: fold_map
WITH shallow AS (
    SELECT hole_id, line_code, fold_id, easting_m, northing_m, z_relative_m,
           ROW_NUMBER() OVER (PARTITION BY hole_id ORDER BY z_relative_m DESC) AS rn
    FROM evaluation_population
)
SELECT hole_id, line_code, fold_id, easting_m, northing_m
FROM shallow WHERE rn = 1
ORDER BY fold_id, hole_id;
-- name: fold_counts
SELECT fold_id, COUNT(*) AS n, SUM(true_label) AS positive, COUNT(DISTINCT hole_id) AS n_holes,
       COUNT(DISTINCT line_code) AS n_lines, GROUP_CONCAT(DISTINCT line_code) AS lines
FROM evaluation_population
GROUP BY fold_id
ORDER BY fold_id;
-- name: coverage
SELECT c.model_id, c.n_expected, c.n_predicted, c.n_failed, c.coverage, c.status, c.reason,
       r.role, r.comparable, r.identity_status, r.identical_to
FROM prediction_coverage c JOIN candidate_registry r ON r.model_id = c.model_id
ORDER BY r.comparable DESC, c.coverage DESC, c.model_id;

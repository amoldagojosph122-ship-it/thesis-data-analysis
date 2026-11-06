-- O3-F01 outer-fold spatial map and class support. Read-only queries against the Objective 3 database.
-- name: fold_audit
SELECT a.fold_id, a.n_train, a.n_test, a.train_positive, a.test_positive, a.train_lines, a.test_lines,
       a.min_train_test_collar_distance_m, a.status, a.reason
FROM split_audit a
JOIN spatial_split_plans p ON p.split_plan_id = a.split_plan_id
WHERE a.split_plan_id = :split_plan_id
ORDER BY a.fold_id;
-- name: fold_lines
SELECT DISTINCT fold_id, line_code
FROM split_membership
WHERE split_plan_id = :split_plan_id AND role = 'TEST'
ORDER BY fold_id, line_code;
-- name: collar_folds
WITH shallow AS (
    SELECT o.hole_id, o.line_code, o.easting_m, o.northing_m,
           ROW_NUMBER() OVER (PARTITION BY o.hole_id ORDER BY o.z_relative_m DESC) AS rn
    FROM analysis_observations o
    WHERE o.receipt_id = :receipt_id AND o.in_binary_target = 1
), line_fold AS (
    SELECT DISTINCT fold_id, line_code
    FROM split_membership
    WHERE split_plan_id = :split_plan_id AND role = 'TEST'
)
SELECT s.hole_id, s.line_code, f.fold_id, s.easting_m, s.northing_m
FROM shallow s
JOIN line_fold f ON f.line_code = s.line_code
WHERE s.rn = 1
ORDER BY f.fold_id, s.hole_id;

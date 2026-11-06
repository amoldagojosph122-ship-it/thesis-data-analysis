-- O3-T01 model definitions, deployed and forbidden features, target and geometry versions, and sample support.
-- name: model_feature_target_support
SELECT 'MODEL' AS item_type, family_id AS item_id, name AS item, role AS category,
       description AS detail, '' AS units, '' AS status, 0 AS n
FROM model_families
UNION ALL
SELECT 'FEATURE' AS item_type, feature_id AS item_id, name AS item,
       leakage_designation AS category, rationale AS detail, COALESCE(units, '') AS units,
       CASE available_at_prediction WHEN 1 THEN 'AVAILABLE_AT_PREDICTION' ELSE 'NOT_AVAILABLE' END AS status, 0 AS n
FROM feature_registry
UNION ALL
SELECT 'TARGET' AS item_type, target_id AS item_id, label_rule_id AS item, label_rule_status AS category,
       'positive=' || positive_state || '; negative=' || negative_state || '; excluded=' || excluded_states_json AS detail,
       'intervals' AS units, 'APPROVED' AS status, binary_n AS n
FROM target_registries
WHERE receipt_id = :receipt_id
UNION ALL
SELECT 'GEOMETRY' AS item_type, geometry_version_id AS item_id, CAST(geometry_build_id AS TEXT) AS item,
       geometry_status AS category,
       'CRS ' || crs_key || '; datum ' || datum_status || '; vertical ' || vertical_basis ||
       '; z_absolute_used=' || z_absolute_used AS detail, '' AS units, 'VERIFIED' AS status, 0 AS n
FROM geometry_versions
WHERE receipt_id = :receipt_id
UNION ALL
SELECT 'SAMPLE' AS item_type, split_plan_id || ':' || family_id AS item_id, candidate_run_id AS item, 'FOLD_SUMMARY' AS category,
       'training rows ' || MIN(training_n) || ' to ' || MAX(training_n) ||
       '; training positive ' || MIN(training_positive) || ' to ' || MAX(training_positive) ||
       '; test rows ' || MIN(test_n) || ' to ' || MAX(test_n) ||
       '; test positive ' || MIN(test_positive) || ' to ' || MAX(test_positive) ||
       '; folds ' || COUNT(*) AS detail,
       'rows' AS units, 'OBSERVED' AS status, SUM(training_n) AS n
FROM training_runs
WHERE split_plan_id IN (SELECT split_plan_id FROM spatial_split_plans)
GROUP BY split_plan_id, family_id, candidate_run_id
ORDER BY item_type, item_id, item;

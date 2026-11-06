-- O3-F02 predictor availability and three-dimensional observation support.
-- name: feature_availability
SELECT feature_id, name, units, available_at_prediction, leakage_designation, rationale
FROM feature_registry
ORDER BY available_at_prediction DESC, leakage_designation, name;
-- name: observation_points
SELECT easting_m, northing_m, z_relative_m, depth_from_m, indicator
FROM analysis_observations
WHERE receipt_id = :receipt_id AND in_binary_target = 1
ORDER BY upstream_interval_id;
-- name: class_counts
SELECT indicator, COUNT(*) AS n
FROM analysis_observations
WHERE receipt_id = :receipt_id AND in_binary_target = 1
GROUP BY indicator
ORDER BY indicator;

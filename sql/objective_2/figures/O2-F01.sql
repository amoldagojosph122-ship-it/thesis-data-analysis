-- O2-F01 plan view. Reads the collar table and the POSITIVE intervals of one receipt. Coordinates are UTM 30N metres
-- (EPSG:32630, datum WGS 84 verified). Depth is relative to collar; no collar elevation is used.
-- name: collars
SELECT hole_id, line_code, utm_easting_m AS easting_m, utm_northing_m AS northing_m, max_depth_m
FROM collar_locations
WHERE receipt_id = :receipt_id
ORDER BY line_code, hole_id;
-- name: positive_midpoints
SELECT hole_id, line_code, easting_m, northing_m, z_relative_m, depth_from_m, depth_to_m
FROM analysis_observations
WHERE receipt_id = :receipt_id AND label_state = 'POSITIVE'
ORDER BY hole_id, depth_from_m;

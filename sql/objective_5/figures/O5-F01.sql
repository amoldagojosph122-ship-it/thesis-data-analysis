-- O5-F01 support zones in plan with collars and drill lines.
-- name: plan_zones
SELECT centre_easting_m AS easting_m, centre_northing_m AS northing_m, zone
FROM grid_cells WHERE iz = :iz ORDER BY iy, ix;
-- name: collars
SELECT hole_id, line_code, easting_m, northing_m FROM collars ORDER BY line_code, hole_id;

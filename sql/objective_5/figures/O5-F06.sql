-- O5-F06 along-line sections: the cells nearest each line's northing, and the logged binary intervals of that line.
-- name: section_cells
SELECT ix, centre_easting_m AS easting_m, z_relative_m, depth_below_collar_m, p_selected, interval_width, class_label,
       zone, above_weathering_front AS above_front
FROM grid_cells WHERE iy = :iy ORDER BY ix, iz;
-- name: section_logged
SELECT hole_id, easting_m, z_relative_m, indicator, weathering_code
FROM observations WHERE line_code = :line AND in_binary_target = 1 ORDER BY hole_id, depth_from_m;

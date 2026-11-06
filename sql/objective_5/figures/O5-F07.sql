-- O5-F07 three-dimensional view: CONFIDENT_PRESENT and UNCERTAIN cells inside the INTERPOLATION zone (relative depth).
-- name: cells_3d
SELECT centre_easting_m AS easting_m, centre_northing_m AS northing_m, z_relative_m, class_label
FROM grid_cells
WHERE zone = 'INTERPOLATION' AND class_label IN ('CONFIDENT_PRESENT', 'UNCERTAIN')
ORDER BY cell_id;

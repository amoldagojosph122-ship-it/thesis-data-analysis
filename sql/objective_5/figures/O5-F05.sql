-- O5-F05 class in a depth slice, with the weathering-front tag.
-- name: slice_class
SELECT ix, iy, centre_easting_m AS easting_m, centre_northing_m AS northing_m, zone, class_label,
       above_weathering_front AS above_front
FROM grid_cells WHERE iz = :iz ORDER BY iy, ix;

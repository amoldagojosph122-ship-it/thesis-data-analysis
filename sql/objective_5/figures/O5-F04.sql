-- O5-F04 model disagreement |p_selected - p_runner_up| in a depth slice.
-- name: slice_disagreement
SELECT ix, iy, centre_easting_m AS easting_m, centre_northing_m AS northing_m, zone, disagreement AS value
FROM grid_cells WHERE iz = :iz ORDER BY iy, ix;

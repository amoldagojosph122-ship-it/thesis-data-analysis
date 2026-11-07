-- O5-F02 probability of the selected model in a depth slice (the cell layer nearest the requested depth).
-- name: slice_probability
SELECT ix, iy, centre_easting_m AS easting_m, centre_northing_m AS northing_m, zone, p_selected AS value
FROM grid_cells WHERE iz = :iz ORDER BY iy, ix;

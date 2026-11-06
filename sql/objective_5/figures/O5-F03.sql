-- O5-F03 bootstrap interval width (p_hi minus p_lo) in a depth slice.
-- name: slice_width
SELECT ix, iy, centre_easting_m AS easting_m, centre_northing_m AS northing_m, zone, interval_width AS value
FROM grid_cells WHERE iz = :iz ORDER BY iy, ix;

-- F08 labels: provisional drill-line groups (nominal Northing).
SELECT line_code, nominal_northing_m, n_holes, n_intervals, status
FROM v_drill_lines
ORDER BY nominal_northing_m;

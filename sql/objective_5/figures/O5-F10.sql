-- O5-F10 one realisation and the frequency map on the section of one drill line: the cells nearest the line's mean
-- northing, with the frequency of positive outcomes and realisation 1 of the scenario (NULL outside the domain).
-- name: section_scenario
SELECT g.ix, g.iz, g.centre_easting_m AS easting_m, g.depth_below_collar_m, g.zone, g.depth_support,
       f.frequency, f.local_mean, r.value AS realisation_1
FROM grid_cells g
LEFT JOIN sim_cell_frequency f ON f.cell_id = g.cell_id AND f.scenario_id = :scenario
LEFT JOIN sim_cell_realisation r ON r.cell_id = g.cell_id AND r.scenario_id = :scenario AND r.realisation = 1
WHERE g.iy = :iy
ORDER BY g.ix, g.iz;
-- name: section_line
SELECT AVG(northing_m) AS northing_m FROM collars WHERE line_code = :line;
-- name: section_logged
SELECT easting_m, z_relative_m, indicator FROM observations WHERE line_code = :line AND in_binary_target = 1;

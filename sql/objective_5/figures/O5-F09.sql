-- O5-F09 connectivity per realisation and scenario.
-- name: connectivity
SELECT r.scenario_id, r.realisation, r.n_components, r.largest_share, s.horizontal_range_m
FROM sim_realisations r JOIN sim_scenarios s ON s.scenario_id = r.scenario_id
ORDER BY s.horizontal_range_m, r.realisation;

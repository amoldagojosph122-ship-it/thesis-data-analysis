-- O5-F08 realisation volumes per scenario, with the expected volume.
-- name: volumes
SELECT r.scenario_id, r.realisation, r.volume_m3, s.expected_volume_m3, s.horizontal_range_m
FROM sim_realisations r JOIN sim_scenarios s ON s.scenario_id = r.scenario_id
ORDER BY s.horizontal_range_m, r.realisation;

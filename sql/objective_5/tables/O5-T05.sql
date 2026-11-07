-- O5-T05 scenario simulation summary. Scenario analysis: the lateral range is assumed, not estimated. Volumes are
-- relative grid volumes of the simulated domain (INTERPOLATION, SUPPORTED cells), not resources.
-- name: scenario_summary
SELECT scenario_id, horizontal_range_m AS a_h_m, feasibility, vertical_bracket, vertical_range_m AS a_v_m,
       expected_vertical_range_m AS a_v_expected_m, n_realisations, expected_volume_m3, volume_p10_m3, volume_p50_m3,
       volume_p90_m3, components_p10, components_p50, components_p90, largest_share_p10, largest_share_p50,
       largest_share_p90, sk_fallbacks, sk_neighbourless_nodes, exact_neighbour_searches, runtime_s, status
FROM sim_scenarios
ORDER BY horizontal_range_m;

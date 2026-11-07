-- O5-T06 scenario reproduction checks. Mean frequency is compared with the mean local mean over the domain; the
-- down-hole indicator semivariogram of realisations 1-5 (sampled at the node nearest each midpoint) is compared with the
-- data semivariogram on the Objective 2 lag bins. Reported, not gated, except the mean-frequency WARN.
-- name: reproduction_checks
SELECT scenario_id, 'MEAN_FREQUENCY_VS_MEAN_LOCAL_MEAN' AS check_id, mean_frequency AS simulated,
       mean_local_mean AS reference, mean_frequency_diff AS difference, frequency_status AS status,
       'domain nodes; WARN when the absolute difference exceeds 0.05' AS basis
FROM sim_scenarios WHERE feasibility = 'FEASIBLE'
UNION ALL
SELECT scenario_id, 'DOWNHOLE_GAMMA_LAG_' || CAST(CAST(lag_centre_m AS INTEGER) AS TEXT) AS check_id,
       sim_gamma_mean AS simulated, data_gamma AS reference, sim_gamma_mean - data_gamma AS difference,
       'REPORTED' AS status, 'mean over realisations 1-5; data semivariance of binary intervals' AS basis
FROM sim_downhole_variogram WHERE supported = 1 AND CAST(lag_centre_m AS INTEGER) IN (1, 5, 10, 20, 30)
UNION ALL
SELECT scenario_id, 'DOWNHOLE_MAX_ABS_DIFF_SUPPORTED_BINS' AS check_id, downhole_max_abs_diff AS simulated,
       NULL AS reference, NULL AS difference, 'REPORTED' AS status,
       'maximum over supported bins of |simulated mean - data|' AS basis
FROM sim_scenarios WHERE feasibility = 'FEASIBLE'
UNION ALL
SELECT 'DATA' AS scenario_id, 'DOWNHOLE_DATA_VS_O2_MAX_ABS_DIFF' AS check_id, CAST(meta_value AS REAL) AS simulated,
       NULL AS reference, NULL AS difference, 'REPORTED' AS status,
       'data semivariance recomputed here against the stored Objective 2 DOWNHOLE_WITHIN bins' AS basis
FROM sim_run_meta WHERE meta_key = 'data_vs_o2_max_abs_diff'
ORDER BY scenario_id, check_id;

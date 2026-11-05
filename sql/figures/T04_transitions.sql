-- T04 part A: Target B (RECON_2OF3_v1) against its trace-excluded sensitivity variant, by state pair.
SELECT recon_state, notrace_state, COUNT(*) AS n_intervals, ROUND(SUM(interval_length_m), 3) AS logged_m
FROM v_label_sensitivity
GROUP BY recon_state, notrace_state
ORDER BY recon_state, notrace_state;

-- F05: lithology code frequency and logged metres. Denominator: all 1-m intervals and logged metres.
SELECT code, legend_description, code_status, n_intervals, logged_m
FROM v_rock_code_usage
ORDER BY n_intervals DESC, code;

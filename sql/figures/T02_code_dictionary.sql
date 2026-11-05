-- T02 part A: lithological code dictionary with usage, including unsupported codes seen in the logging.
SELECT code, legend_description, code_status, n_intervals, logged_m
FROM v_rock_code_usage
ORDER BY code_status, n_intervals DESC, code;

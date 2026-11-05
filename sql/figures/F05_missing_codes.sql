-- F05 addendum: intervals with a blank rock_type1, shown separately from any code.
SELECT COUNT(*) AS n_intervals, ROUND(COALESCE(SUM(interval_length_m), 0), 3) AS logged_m
FROM v_intervals
WHERE rock_code_status = 'MISSING';

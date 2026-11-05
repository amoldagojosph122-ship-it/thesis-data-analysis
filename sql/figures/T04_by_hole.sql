-- T04 part B: intervals whose state changes when trace-qualified comments are excluded, by hole.
-- Denominator: logged metres per hole.
SELECT hole_id, line_code, ROUND(SUM(interval_length_m), 3) AS logged_m,
       SUM(CASE WHEN recon_state IS NOT notrace_state THEN 1 ELSE 0 END) AS n_changed,
       ROUND(SUM(CASE WHEN recon_state = 'POSITIVE' THEN interval_length_m ELSE 0 END), 3) AS recon_positive_m,
       ROUND(SUM(CASE WHEN notrace_state = 'POSITIVE' THEN interval_length_m ELSE 0 END), 3) AS notrace_positive_m
FROM v_label_sensitivity
GROUP BY hole_id, line_code
ORDER BY n_changed DESC, hole_id;

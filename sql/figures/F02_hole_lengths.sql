-- F02: drill-hole length distribution. Denominator: holes (n) and total drilled metres.
SELECT hole_id, line_code, max_depth_m
FROM v_holes
ORDER BY max_depth_m, hole_id;

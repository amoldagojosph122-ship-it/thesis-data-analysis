-- F08 points: collar plan coloured by strict graphitic fraction (Sgs metres / logged metres).
SELECT hole_id, line_code, easting_m, northing_m, logged_m, sgs_m, sgs_fraction
FROM v_collar_plan
ORDER BY line_code, hole_id;

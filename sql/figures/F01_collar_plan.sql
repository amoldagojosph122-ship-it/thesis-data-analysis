-- F01: collar plan. Source: v_collar_plan (active version). Denominator: all collars.
-- Coordinates are the adopted UTM pair (PROVISIONAL); the alternate pair is included for the caption.
SELECT hole_id, line_code, easting_m, northing_m, easting_alt_m, northing_alt_m, max_depth_m,
       logged_m, sgs_m, sgs_fraction
FROM v_collar_plan
ORDER BY line_code, hole_id;

-- F04 panel A: interval midpoints with RELATIVE Z (metres below collar; not elevation).
-- Source: v_interval_geometry (active version).
SELECT hole_id, line_code, interval_key, depth_from_m, depth_to_m, midpoint_m, easting_m, northing_m,
       z_relative_m, rock_code_raw, strict_state
FROM v_interval_geometry
ORDER BY hole_id, depth_from_m;

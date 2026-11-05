-- F09: relative-Z sections. Source: v_interval_geometry. Vertical axis = metres below collar (provisional).
-- Collar RL is absent, so a common collar elevation is assumed. No interpolation between holes.
SELECT g.line_code, g.hole_id, g.midpoint_m, g.easting_m, g.northing_m, g.z_relative_m,
       g.depth_from_m, g.depth_to_m, g.strict_state, g.recon_state, h.utm_northing_m, dl.nominal_northing_m
FROM v_interval_geometry g
JOIN v_holes h ON h.hole_id = g.hole_id
JOIN v_drill_lines dl ON dl.line_code = g.line_code
ORDER BY g.line_code, g.hole_id, g.depth_from_m;

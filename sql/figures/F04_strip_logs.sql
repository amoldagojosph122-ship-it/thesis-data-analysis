-- F04 panel B: 1-m interval strips per hole (measured depth). Source: v_interval_flags joined to v_holes.
SELECT f.hole_id, f.line_code, f.depth_from_m, f.depth_to_m, f.rock_code_raw, f.rock_code_status,
       f.strict_state, f.recon_state, h.max_depth_m
FROM v_interval_flags f
JOIN v_holes h ON h.hole_id = f.hole_id
ORDER BY f.line_code, f.hole_id, f.depth_from_m;

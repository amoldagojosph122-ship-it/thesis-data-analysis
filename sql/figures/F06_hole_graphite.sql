-- F06: strict graphitic (Sgs, Target A) apparent thickness and Target B (DESIGN_8_2_v1) graphitic metres by hole.
-- Denominator: logged metres per hole (1-m intervals). Thickness is apparent along-hole, not true thickness.
SELECT g.hole_id, g.line_code, g.logged_m, g.sgs_m, g.sgs_n, g.design_pos_m, g.design_unresolved_m,
       g.conflict_n, h.max_depth_m
FROM v_hole_design g
JOIN v_holes h ON h.hole_id = g.hole_id
ORDER BY g.sgs_m DESC, g.hole_id;

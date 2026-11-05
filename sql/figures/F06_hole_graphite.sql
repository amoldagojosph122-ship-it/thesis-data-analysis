-- F06: strict graphitic (Sgs, Target A) apparent thickness and reconciled-candidate metres by hole.
-- Denominator: logged metres per hole (1-m intervals). Thickness is apparent along-hole, not true thickness.
SELECT g.hole_id, g.line_code, g.logged_m, g.sgs_m, g.sgs_n, g.recon_pos_m, g.recon_unresolved_m,
       g.conflict_n, h.max_depth_m
FROM v_hole_graphite g
JOIN v_holes h ON h.hole_id = g.hole_id
ORDER BY g.sgs_m DESC, g.hole_id;

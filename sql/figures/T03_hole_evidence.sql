-- T03 part A: graphitic-domain evidence and ambiguity by hole. Denominator: logged metres per hole.
SELECT g.hole_id, g.line_code, g.logged_m, g.sgs_m, g.gr_mineral_m, g.comment_graphitic_m, g.comment_trace_m,
       g.recon_pos_m, g.recon_unresolved_m, g.conflict_n, g.unresolved_code_n
FROM v_hole_graphite g
ORDER BY g.line_code, g.hole_id;

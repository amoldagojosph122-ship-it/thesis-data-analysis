-- T03 part B: graphitic-domain evidence and ambiguity by provisional drill line.
SELECT l.line_code, d.nominal_northing_m, l.n_holes, l.n_intervals, l.logged_m, l.sgs_m, l.recon_pos_m,
       l.recon_unresolved_m, l.conflict_n, l.unresolved_code_n
FROM v_line_graphite l
JOIN v_drill_lines d ON d.line_code = l.line_code
ORDER BY d.nominal_northing_m;

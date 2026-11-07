-- 0013_design_views.sql
-- Target B outputs read the design rule DESIGN_8_2_v1 (ThesisDesign section 8.2). These views are additive:
-- the earlier views (v_interval_flags, v_hole_graphite, v_line_graphite) stay unchanged, because the collar
-- plan and the trace-excluded sensitivity table (T04) still read them.

CREATE VIEW v_interval_design AS
SELECT f.*, d.label AS design_label, d.label_state AS design_state
FROM v_interval_flags f
JOIN v_label_candidates d ON d.interval_id = f.interval_id AND d.rule_id = 'DESIGN_8_2_v1';

CREATE VIEW v_hole_design AS
SELECT f.hole_id, f.line_code,
       COUNT(*) AS n_intervals,
       ROUND(SUM(f.interval_length_m), 3) AS logged_m,
       ROUND(SUM(CASE WHEN f.is_sgs = 1 THEN f.interval_length_m ELSE 0 END), 3) AS sgs_m,
       SUM(CASE WHEN f.is_sgs = 1 THEN 1 ELSE 0 END) AS sgs_n,
       ROUND(SUM(CASE WHEN f.has_gr_mineral = 1 THEN f.interval_length_m ELSE 0 END), 3) AS gr_mineral_m,
       ROUND(SUM(CASE WHEN f.comment_graphitic = 1 THEN f.interval_length_m ELSE 0 END), 3) AS comment_graphitic_m,
       ROUND(SUM(CASE WHEN f.comment_trace_qualified = 1 THEN f.interval_length_m ELSE 0 END), 3) AS comment_trace_m,
       ROUND(SUM(CASE WHEN f.design_state = 'POSITIVE' THEN f.interval_length_m ELSE 0 END), 3) AS design_pos_m,
       ROUND(SUM(CASE WHEN f.design_state = 'AMBIGUOUS' THEN f.interval_length_m ELSE 0 END), 3) AS design_ambiguous_m,
       ROUND(SUM(CASE WHEN f.design_state = 'UNRESOLVED' THEN f.interval_length_m ELSE 0 END), 3) AS design_unresolved_m,
       SUM(CASE WHEN f.label_conflict = 1 THEN 1 ELSE 0 END) AS conflict_n,
       SUM(CASE WHEN f.rock_code_status <> 'VALID' THEN 1 ELSE 0 END) AS unresolved_code_n
FROM v_interval_design f
GROUP BY f.hole_id, f.line_code;

CREATE VIEW v_line_design AS
SELECT f.line_code,
       COUNT(DISTINCT f.hole_id) AS n_holes,
       COUNT(*) AS n_intervals,
       ROUND(SUM(f.interval_length_m), 3) AS logged_m,
       ROUND(SUM(CASE WHEN f.is_sgs = 1 THEN f.interval_length_m ELSE 0 END), 3) AS sgs_m,
       SUM(CASE WHEN f.is_sgs = 1 THEN 1 ELSE 0 END) AS sgs_n,
       ROUND(SUM(CASE WHEN f.design_state = 'POSITIVE' THEN f.interval_length_m ELSE 0 END), 3) AS design_pos_m,
       ROUND(SUM(CASE WHEN f.design_state = 'AMBIGUOUS' THEN f.interval_length_m ELSE 0 END), 3) AS design_ambiguous_m,
       ROUND(SUM(CASE WHEN f.design_state = 'UNRESOLVED' THEN f.interval_length_m ELSE 0 END), 3) AS design_unresolved_m,
       SUM(CASE WHEN f.label_conflict = 1 THEN 1 ELSE 0 END) AS conflict_n,
       SUM(CASE WHEN f.rock_code_status <> 'VALID' THEN 1 ELSE 0 END) AS unresolved_code_n
FROM v_interval_design f
GROUP BY f.line_code;

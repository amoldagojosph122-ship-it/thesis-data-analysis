-- 0009_sensitivity_views.sql
-- Sensitivity of Target B (RECON_2OF3_v1) to the trace-qualified comment rule.
-- Read-only views; no new tables. The comparison rule is RECON_2OF3_NOTRACE_v1 (config/label_rules.yaml).

CREATE VIEW v_label_sensitivity AS
SELECT f.interval_id, f.interval_key, f.hole_id, f.line_code, f.interval_length_m,
       f.comment_trace_qualified, f.recon_state, n.label_state AS notrace_state
FROM v_interval_flags f
JOIN v_label_candidates n ON n.interval_id = f.interval_id AND n.rule_id = 'RECON_2OF3_NOTRACE_v1';

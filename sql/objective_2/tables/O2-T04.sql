-- O2-T04 handoff contract for Objective 3, with the open items that remain: warning or skipped gates of the latest
-- VERIFY run, skipped directions, skipped sensitivity entries, and the geological questions the analysis leaves open.
-- name: handoff_contract
SELECT 'HANDOFF' AS item_type, 'O3-HANDOFF-' || h.handoff_id AS item_id, h.decision_status AS status,
       'candidate_family=' || h.candidate_family || '; full_data_parameters_for_test_folds='
           || h.full_data_parameters_for_test_folds || '; ' || h.rationale AS detail
FROM continuity_handoff_decisions h
WHERE h.receipt_id = :receipt_id
UNION ALL
SELECT 'GATE', g.gate_id, g.status, g.gate_name || ': ' || g.detail
FROM gate_results g
WHERE g.run_id = (SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'VERIFY')
  AND g.status IN ('WARN', 'SKIP', 'STOP', 'DOWNGRADE')
UNION ALL
SELECT 'SENSITIVITY', s.variant_name, s.status, s.reason
FROM sensitivity_runs s
WHERE s.run_id = (SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'ANALYSE' AND receipt_id = :receipt_id)
  AND s.status = 'SKIPPED'
UNION ALL
SELECT 'DIRECTION', d.direction_id, d.status, d.reason
FROM direction_registry d
WHERE d.receipt_id = :receipt_id AND d.status <> 'SUPPORTED'
UNION ALL
SELECT 'QUESTION', 'LINE_PREVALENCE', 'OPEN',
       'binary prevalence by line ranges from ' || ROUND(MIN(1.0 * positive_n / binary_n), 3) || ' to '
           || ROUND(MAX(1.0 * positive_n / binary_n), 3) || ' across ' || COUNT(*)
           || ' lines; whether this reflects zones, sampling or geology is not resolved'
FROM line_occurrence_summaries
WHERE receipt_id = :receipt_id
UNION ALL
SELECT 'QUESTION', 'LAG_WINDOW', 'OPEN',
       'collar pairs have a median separation of ' || ROUND(s.stat_value, 0) || ' m, while the lateral lag window ends at '
           || (SELECT MAX(lag_max_m) FROM variogram_experiments
               WHERE receipt_id = :receipt_id AND variant = 'BASE' AND direction_id = 'LATERAL_BETWEEN')
           || ' m; longer-range structure is not assessed'
FROM spatial_support_statistics s
WHERE s.receipt_id = :receipt_id AND s.stat_group = 'COLLAR_PAIR' AND s.stat_name = 'median'
UNION ALL
SELECT 'QUESTION', 'COLLAR_RL', 'OPEN',
       'no collar elevation (RL) is available; depth is relative to collar and absolute elevation is not used'
ORDER BY item_type, item_id;

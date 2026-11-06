-- O2-F11 alignment score against apparent dip (configuration 6, O2-CFG-2026.11.06-6), one panel per sample, both frames.
-- Rows come only from the configuration-6 stage run. The dotted line of each frame is the selection-null 95th percentile of
-- the maximum over the grid (the null includes the search over all 17 dips).
-- name: scores
SELECT s.sample_id, s.frame_id, s.dip_deg, s.alignment_score, s.n_supported_bins, s.is_selected, s.is_horizontal_control
FROM structural_alignment_scores s
WHERE s.receipt_id = :receipt_id AND s.config_version = 'O2-CFG-2026.11.06-6'
ORDER BY s.sample_id, s.frame_id, s.dip_deg;
-- name: nulls
SELECT n.sample_id, n.frame_id, n.selected_dip_deg, n.observed_max_alignment, n.null_p95_max, n.p_value
FROM structural_null_summary n
WHERE n.receipt_id = :receipt_id AND n.config_version = 'O2-CFG-2026.11.06-6'
ORDER BY n.sample_id, n.frame_id;

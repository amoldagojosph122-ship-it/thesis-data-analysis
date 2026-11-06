-- O2-T06 structural-frame alignment score by apparent dip, frame and sample, with the selection-null p-value and the
-- leave-one-line-out dips (configuration 6, O2-CFG-2026.11.06-6). Rows come only from the configuration-6 stage run.
-- name: alignment_by_dip
SELECT s.sample_id, s.frame_id, s.dip_deg, s.n_supported_bins, s.n_pairs,
       ROUND(s.alignment_score, 4) AS alignment_score, s.is_selected, s.is_horizontal_control,
       n.selected_dip_deg, ROUND(n.observed_max_alignment, 4) AS observed_max_alignment,
       ROUND(n.null_p95_max, 4) AS null_p95_max, ROUND(n.p_value, 4) AS null_p_value,
       (SELECT GROUP_CONCAT(x.excluded_line || ' ' || COALESCE(CAST(x.lolo_dip_deg AS TEXT), 'none'), '; ')
          FROM (SELECT l.excluded_line, l.lolo_dip_deg FROM structural_lolo_dips l
                WHERE l.receipt_id = s.receipt_id AND l.config_version = s.config_version AND l.sample_id = s.sample_id
                  AND l.frame_id = s.frame_id ORDER BY l.excluded_line) x) AS lolo_dips_deg
FROM structural_alignment_scores s
JOIN structural_null_summary n ON n.receipt_id = s.receipt_id AND n.config_version = s.config_version
     AND n.sample_id = s.sample_id AND n.frame_id = s.frame_id
WHERE s.receipt_id = :receipt_id AND s.config_version = 'O2-CFG-2026.11.06-6'
ORDER BY s.sample_id, s.frame_id, s.dip_deg;

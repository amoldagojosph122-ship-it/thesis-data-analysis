-- O2-F13 one section per drill line: easting against relative depth, intervals coloured by indicator, with traces of the
-- selected-dip plane (configuration 6, O2-CFG-2026.11.06-6, ALL_BINARY sample, RELATIVE frame). Rows come from the
-- configuration-6 stage run and from the binary intervals of the receipt.
-- name: intervals
SELECT a.line_code, a.hole_id, a.easting_m, a.z_relative_m, a.indicator
FROM analysis_observations a
WHERE a.receipt_id = :receipt_id AND a.in_binary_target = 1
ORDER BY a.line_code, a.hole_id, a.depth_from_m;
-- name: selected
SELECT n.sample_id, n.selected_dip_deg
FROM structural_null_summary n
WHERE n.receipt_id = :receipt_id AND n.config_version = 'O2-CFG-2026.11.06-6' AND n.frame_id = 'RELATIVE'
  AND n.sample_id = 'ALL_BINARY';

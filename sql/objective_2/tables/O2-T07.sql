-- O2-T07 fit at the selected dip (both models, identifiability, leave-one-line-out range stability) and the between-line
-- along-strike report (REPORT_ONLY, no fit). Configuration 6, O2-CFG-2026.11.06-6; rows come only from its stage run.
-- name: fit_and_between_line
SELECT 'FIT' AS row_type, f.sample_id, f.frame_id, f.selected_dip_deg AS dip_deg, f.model AS item, f.fit_status AS status,
       ROUND(f.nugget, 4) AS nugget, ROUND(f.structured_sill, 4) AS structured_sill, ROUND(f.range_m, 1) AS range_m,
       f.n_bins_used AS n_supported_bins, NULL AS n_pairs, NULL AS n_independent_hole_pairs, NULL AS gamma,
       f.stability_status AS stability, ROUND(f.range_ratio_min, 3) AS range_ratio_min,
       ROUND(f.range_ratio_max, 3) AS range_ratio_max, f.reason AS detail
FROM structural_fits f
WHERE f.receipt_id = :receipt_id AND f.config_version = 'O2-CFG-2026.11.06-6'
UNION ALL
SELECT 'BETWEEN_LINE', b.sample_id, b.frame_id, b.selected_dip_deg,
       printf('northing lag %g to %g m', b.lag_from_m, b.lag_to_m),
       CASE WHEN b.supported = 1 THEN 'SUPPORTED' ELSE 'NOT_SUPPORTED' END,
       NULL, NULL, NULL, NULL, b.n_pairs, b.n_independent_hole_pairs, ROUND(b.gamma, 4), 'REPORT_ONLY', NULL, NULL,
       'no fit; report only; pairs between holes on different lines with |ds| at most 3 m'
FROM structural_between_line b
WHERE b.receipt_id = :receipt_id AND b.config_version = 'O2-CFG-2026.11.06-6'
ORDER BY 1 DESC, 2, 3, 4, 5;

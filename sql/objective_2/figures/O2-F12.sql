-- O2-F12 experimental variogram at the selected dip and at dip 0, RELATIVE frame (configuration 6, O2-CFG-2026.11.06-6), with
-- hole-bootstrap bands and the fitted models at the selected dip. Rows come only from the configuration-6 stage run.
-- name: bins
SELECT b.sample_id, b.purpose, b.dip_deg, b.bin_index, b.lag_centre_m, b.n_pairs, b.n_independent_hole_pairs, b.gamma,
       b.supported, b.gamma_lower, b.gamma_upper, b.gamma_median, b.n_band_replicates
FROM structural_variogram_bins b
WHERE b.receipt_id = :receipt_id AND b.config_version = 'O2-CFG-2026.11.06-6' AND b.frame_id = 'RELATIVE'
ORDER BY b.sample_id, b.purpose, b.bin_index;
-- name: fits
SELECT f.sample_id, f.model, f.fit_status, f.reason, f.nugget, f.structured_sill, f.range_m, f.stability_status
FROM structural_fits f
WHERE f.receipt_id = :receipt_id AND f.config_version = 'O2-CFG-2026.11.06-6' AND f.frame_id = 'RELATIVE'
ORDER BY f.sample_id, f.model;

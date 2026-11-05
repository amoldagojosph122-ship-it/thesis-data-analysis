-- O2-F05 pair support by lag for the base experiments of one receipt. Counts come from pair_sampling_diagnostics;
-- the minimum pairs per bin come from the base experiment definition.
-- name: pair_support
SELECT direction_id, lag_bin_index, lag_from_m, lag_to_m, n_pairs, n_within_hole_pairs, n_between_hole_pairs,
       n_independent_hole_pairs, support_status
FROM pair_sampling_diagnostics
WHERE receipt_id = :receipt_id AND direction_id IN ('DOWNHOLE_WITHIN', 'LATERAL_BETWEEN', 'OMNI_3D_BETWEEN')
ORDER BY direction_id, lag_bin_index;
-- name: minimum_pairs
SELECT direction_id, MIN(min_pairs_per_bin) AS min_pairs_per_bin
FROM variogram_experiments
WHERE receipt_id = :receipt_id AND variant = 'BASE'
GROUP BY direction_id
ORDER BY direction_id;

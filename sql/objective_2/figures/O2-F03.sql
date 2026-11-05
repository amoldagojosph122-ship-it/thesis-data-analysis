-- O2-F03 binary occurrence by depth bin (all rock codes pooled, 10 m bins measured from collar) and by weathering class.
-- name: depth_bins
SELECT depth_bin_from_m, depth_bin_to_m, SUM(binary_n) AS binary_n, SUM(positive_n) AS positive_n
FROM depth_lithology_summaries
WHERE receipt_id = :receipt_id
GROUP BY depth_bin_from_m, depth_bin_to_m
ORDER BY depth_bin_from_m;
-- name: weathering
SELECT weathering_code, label_state, n_intervals
FROM weathering_cross_tabs
WHERE receipt_id = :receipt_id
ORDER BY weathering_code, label_state;

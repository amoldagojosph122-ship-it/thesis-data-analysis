-- O2-T01 hole and line geological summary with support. Binary counts exclude AMBIGUOUS and UNRESOLVED intervals,
-- which are reported in their own columns. Lengths are metres; depth is relative to collar.
-- name: hole_line_summary
SELECT * FROM (
    SELECT 'LINE' AS level, l.line_code, '' AS hole_id, l.n_holes AS holes, l.n_intervals, l.logged_m, l.binary_n,
           l.positive_n, l.negative_n, l.ambiguous_n, l.unresolved_n, l.positive_apparent_m,
           ROUND(l.graphitic_fraction_binary, 4) AS graphitic_fraction_binary, NULL AS collar_easting_m,
           NULL AS collar_northing_m, NULL AS max_depth_m
    FROM line_occurrence_summaries l
    WHERE l.receipt_id = :receipt_id
    UNION ALL
    SELECT 'HOLE', h.line_code, h.hole_id, 1, h.n_intervals, h.logged_m, h.binary_n,
           h.positive_n, h.negative_n, h.ambiguous_n, h.unresolved_n, h.positive_apparent_m,
           ROUND(h.graphitic_fraction_binary, 4), c.utm_easting_m, c.utm_northing_m, c.max_depth_m
    FROM hole_occurrence_summaries h
    JOIN collar_locations c ON c.receipt_id = h.receipt_id AND c.hole_id = h.hole_id
    WHERE h.receipt_id = :receipt_id
)
ORDER BY line_code, level DESC, hole_id;

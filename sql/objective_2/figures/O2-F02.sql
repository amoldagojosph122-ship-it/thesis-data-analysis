-- O2-F02 positive along-hole metres and graphitic fraction by hole and by line. The denominator of the fraction is the
-- number of binary intervals (AMBIGUOUS and UNRESOLVED excluded), reported beside each value.
-- name: holes
SELECT hole_id, line_code, binary_n, positive_n, positive_apparent_m, graphitic_fraction_binary AS fraction
FROM hole_occurrence_summaries
WHERE receipt_id = :receipt_id
ORDER BY (graphitic_fraction_binary IS NULL), graphitic_fraction_binary DESC, hole_id;
-- name: lines
SELECT line_code, n_holes, binary_n, positive_n, positive_apparent_m, graphitic_fraction_binary AS fraction
FROM line_occurrence_summaries
WHERE receipt_id = :receipt_id
ORDER BY line_code;

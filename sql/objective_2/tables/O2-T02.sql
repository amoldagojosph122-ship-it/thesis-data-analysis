-- O2-T02 indicator prevalence, ambiguity and missingness by line, with an all-lines row. Prevalence is the positive
-- share of binary intervals; missingness counts blank rock codes and blank weathering codes.
-- name: prevalence_by_line
WITH by_line AS (
    SELECT l.line_code, l.n_holes, l.n_intervals, l.binary_n, l.positive_n, l.negative_n, l.ambiguous_n, l.unresolved_n,
           (SELECT COUNT(*) FROM analysis_observations o
              WHERE o.receipt_id = l.receipt_id AND o.line_code = l.line_code
                AND (o.rock_code_raw IS NULL OR TRIM(o.rock_code_raw) = '')) AS rock_code_missing,
           (SELECT COUNT(*) FROM analysis_observations o
              WHERE o.receipt_id = l.receipt_id AND o.line_code = l.line_code
                AND (o.weathering_code IS NULL OR TRIM(o.weathering_code) = '')) AS weathering_missing
    FROM line_occurrence_summaries l
    WHERE l.receipt_id = :receipt_id
)
SELECT * FROM (
    SELECT line_code, n_holes, n_intervals, binary_n, positive_n, negative_n, ambiguous_n, unresolved_n,
           rock_code_missing, weathering_missing,
           ROUND(1.0 * positive_n / binary_n, 4) AS prevalence_binary,
           ROUND(1.0 * (ambiguous_n + unresolved_n) / n_intervals, 4) AS excluded_share
    FROM by_line
    UNION ALL
    SELECT 'ALL', (SELECT COUNT(*) FROM collar_locations WHERE receipt_id = :receipt_id),
           SUM(n_intervals), SUM(binary_n), SUM(positive_n), SUM(negative_n), SUM(ambiguous_n), SUM(unresolved_n),
           SUM(rock_code_missing), SUM(weathering_missing),
           ROUND(1.0 * SUM(positive_n) / SUM(binary_n), 4),
           ROUND(1.0 * (SUM(ambiguous_n) + SUM(unresolved_n)) / SUM(n_intervals), 4)
    FROM by_line
)
ORDER BY (line_code = 'ALL'), line_code;

-- O2-F04 observed hole strips in relative depth. Representative holes: the two holes per line with the most binary
-- intervals (ties broken by hole identifier). Only logged intervals are drawn; no contact is inferred.
-- name: representative_holes
WITH counts AS (
    SELECT line_code, hole_id, COUNT(*) AS n_binary
    FROM analysis_observations
    WHERE receipt_id = :receipt_id AND in_binary_target = 1
    GROUP BY line_code, hole_id
), ranked AS (
    SELECT line_code, hole_id, n_binary,
           ROW_NUMBER() OVER (PARTITION BY line_code ORDER BY n_binary DESC, hole_id) AS rank_in_line
    FROM counts
)
SELECT line_code, hole_id, n_binary, rank_in_line
FROM ranked
WHERE rank_in_line <= 2
ORDER BY line_code, rank_in_line;
-- name: intervals
WITH counts AS (
    SELECT line_code, hole_id, COUNT(*) AS n_binary
    FROM analysis_observations
    WHERE receipt_id = :receipt_id AND in_binary_target = 1
    GROUP BY line_code, hole_id
), ranked AS (
    SELECT line_code, hole_id,
           ROW_NUMBER() OVER (PARTITION BY line_code ORDER BY n_binary DESC, hole_id) AS rank_in_line
    FROM counts
)
SELECT o.line_code, o.hole_id, o.depth_from_m, o.depth_to_m, o.label_state, o.indicator
FROM analysis_observations o
JOIN ranked r ON r.line_code = o.line_code AND r.hole_id = o.hole_id AND r.rank_in_line <= 2
WHERE o.receipt_id = :receipt_id
ORDER BY o.line_code, o.hole_id, o.depth_from_m;
-- name: section_geometry
SELECT line_code, COUNT(*) AS n_holes, MIN(utm_northing_m) AS n_min, MAX(utm_northing_m) AS n_max
FROM collar_locations
WHERE receipt_id = :receipt_id
GROUP BY line_code
ORDER BY line_code;

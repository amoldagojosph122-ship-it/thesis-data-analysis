-- 0012_qaqc_summary_counts.sql
-- A check can be written twice: one aggregate finding for the dataset (entity DATASET, n = all records) and one
-- finding per record (entity INTERVAL or HOLE, n = 1). The earlier view added both, so each flagged record was
-- counted twice. n_records now uses the aggregate finding when a check has one, and the record findings otherwise.

DROP VIEW v_qaqc_summary;

CREATE VIEW v_qaqc_summary AS
SELECT g.check_id, c.category, c.description, g.severity, g.status, g.result,
       g.n_findings,
       COALESCE(g.aggregate_n, g.record_n) AS n_records
FROM (
    SELECT f.check_id, f.severity, f.status, f.result,
           COUNT(*) AS n_findings,
           SUM(CASE WHEN f.entity_type = 'DATASET' THEN f.n_records END) AS aggregate_n,
           SUM(CASE WHEN f.entity_type <> 'DATASET' THEN f.n_records END) AS record_n
    FROM qaqc_findings f
    WHERE f.dataset_version_id = (SELECT dataset_version_id FROM v_active_version)
    GROUP BY f.check_id, f.severity, f.status, f.result
) g
JOIN qaqc_checks c ON c.check_id = g.check_id;

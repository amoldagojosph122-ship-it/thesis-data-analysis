-- T01 part B: raw-to-curated reconciliation. 'reference' = ThesisDesign.docx preliminary figure,
-- shown only for comparison. It is never used as an input to any derivation.
SELECT 'Collars rows (raw)' AS item,
       (SELECT COUNT(*) FROM raw_collars WHERE source_file_id = (SELECT source_file_id FROM v_active_version)) AS observed,
       (SELECT COUNT(*) FROM v_holes) AS curated,
       71 AS reference
UNION ALL
SELECT 'Surveys rows (raw)',
       (SELECT COUNT(*) FROM raw_surveys WHERE source_file_id = (SELECT source_file_id FROM v_active_version)),
       (SELECT COUNT(*) FROM v_survey),
       71
UNION ALL
SELECT 'Logging rows (raw)',
       (SELECT COUNT(*) FROM raw_logging WHERE source_file_id = (SELECT source_file_id FROM v_active_version)),
       (SELECT COUNT(*) FROM v_intervals),
       1910
UNION ALL
SELECT 'Logged metres (sum of 1-m intervals)',
       1910,
       (SELECT ROUND(SUM(interval_length_m), 3) FROM v_intervals),
       1910
UNION ALL
SELECT 'Intervals with rock_type1 = Sgs',
       529,
       (SELECT COUNT(*) FROM v_label_evidence WHERE is_sgs = 1),
       529
UNION ALL
SELECT 'Holes intersecting Sgs',
       42,
       (SELECT COUNT(*) FROM v_hole_graphite WHERE sgs_n > 0),
       42;

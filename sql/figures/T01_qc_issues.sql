-- T01 part C: QA/QC issues summary (failed checks and ERROR-severity checks).
SELECT check_id, category, severity, status, result, n_records, description
FROM v_qaqc_summary
WHERE result = 'FAIL' OR severity = 'ERROR'
ORDER BY CASE severity WHEN 'ERROR' THEN 1 WHEN 'WARNING' THEN 2 ELSE 3 END, check_id;

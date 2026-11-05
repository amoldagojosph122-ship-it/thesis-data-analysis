-- F03 panel B: QA/QC findings by check, severity and status.
SELECT check_id, category, severity, status, result, n_findings, n_records, description
FROM v_qaqc_summary
ORDER BY CASE severity WHEN 'ERROR' THEN 1 WHEN 'WARNING' THEN 2 ELSE 3 END, check_id;

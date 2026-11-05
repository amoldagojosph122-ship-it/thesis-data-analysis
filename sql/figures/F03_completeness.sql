-- F03 panel A: non-blank completeness per raw field (from raw JSON payloads of the active source).
SELECT source_sheet, field_name, n_rows, n_non_blank,
       ROUND(100.0 * n_non_blank / n_rows, 2) AS pct_non_blank
FROM v_completeness
ORDER BY source_sheet, pct_non_blank, field_name;

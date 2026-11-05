-- T01 part A: workbook sheet inventory for the active source file.
SELECT ss.sheet_name, ss.sheet_state, ss.n_rows, ss.n_cols, ss.header_json, ss.blank_columns_json
FROM source_sheets ss
WHERE ss.source_file_id = (SELECT source_file_id FROM v_active_version)
ORDER BY ss.sheet_name;

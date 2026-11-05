-- 0008_views.sql
-- Stable read-only views for figures, tables and downstream receipts.
-- Every view is restricted to the ACTIVE dataset version. Figure SQL reads these views only.
-- Rule identifiers used below are the Stage A candidate rules defined in config/label_rules.yaml:
--   STRICT_SGS_v1 (Target A: rock code Sgs), RECON_2OF3_v1 (Target B candidate: >= 2 of 3 indicators),
--   ALL3_v1 (all three indicators), ANY_v1 (any indicator). All are PROPOSED until a reviewer approves.

CREATE VIEW v_active_version AS
SELECT dataset_version_id, dataset_version_key, dataset_label, source_file_id, etl_version,
       rule_versions_json, coordinate_decision_json, created_utc, activated_utc
FROM dataset_versions
WHERE status = 'ACTIVE';

CREATE VIEW v_source_file AS
SELECT sf.source_file_id, sf.file_name, sf.original_path, sf.raw_copy_path, sf.sha256, sf.size_bytes
FROM source_files sf
WHERE sf.source_file_id = (SELECT source_file_id FROM v_active_version);

CREATE VIEW v_holes AS
SELECT h.hole_id, h.raw_hole_id, h.hole_type, h.grid_label, h.easting_alt_m, h.northing_alt_m,
       h.utm_easting_m, h.utm_northing_m, h.line_code, h.rl_status, h.rl_m, h.max_depth_m,
       h.project_code, h.prospect, h.contractor, h.logged_by, h.date_drilled, h.dataset_version_id
FROM holes h
WHERE h.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_drill_lines AS
SELECT dl.line_code, dl.nominal_northing_m, dl.n_holes, dl.n_intervals, dl.grouping_method, dl.status
FROM drill_lines dl
WHERE dl.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_survey AS
SELECT s.hole_id, s.depth_m, s.dip_deg, s.azimuth_deg, s.station_kind, s.surveyed_by, s.instrument,
       s.convention_status
FROM survey_stations s
WHERE s.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_intervals AS
SELECT li.interval_id, li.interval_key, li.hole_id, h.line_code, li.source_row,
       li.depth_from_m, li.depth_to_m, li.interval_length_m, li.midpoint_m,
       li.rock_code_raw, li.rock_code_status, li.rock_description,
       li.colour1_code, li.colour2_code, li.weathering_code, li.weathering_status,
       li.alt_min1_code, li.alt_min1_int, li.alt_min2_code, li.comment_raw, li.dataset_version_id
FROM logging_intervals li
JOIN holes h ON h.dataset_version_id = li.dataset_version_id AND h.hole_id = li.hole_id
WHERE li.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_label_evidence AS
SELECT i.interval_id, i.interval_key, i.hole_id, i.line_code, i.depth_from_m, i.depth_to_m,
       i.interval_length_m, i.midpoint_m, i.rock_code_raw, i.rock_code_status, i.weathering_code,
       i.weathering_status, i.comment_raw, i.alt_min1_code,
       e.is_sgs, e.has_gr_mineral, e.comment_present, e.comment_graphitic, e.comment_trace_qualified,
       e.comment_term, e.positive_indicators, e.negative_indicators, e.label_conflict,
       e.evidence_pattern, e.label_review_status, e.rationale
FROM interval_label_evidence e
JOIN v_intervals i ON i.interval_id = e.interval_id
WHERE e.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_label_candidates AS
SELECT l.rule_id, r.rule_family, r.status AS rule_status, r.rule_version, i.interval_id, i.interval_key,
       i.hole_id, i.line_code, i.interval_length_m, i.midpoint_m, i.weathering_code,
       l.label, l.label_state
FROM interval_labels l
JOIN graphite_label_rules r ON r.rule_id = l.rule_id
JOIN v_intervals i ON i.interval_id = l.interval_id
WHERE l.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_label_candidate_counts AS
SELECT rule_id, rule_family, rule_status, label_state,
       COUNT(*) AS n_intervals,
       ROUND(SUM(interval_length_m), 3) AS logged_m
FROM v_label_candidates
GROUP BY rule_id, rule_family, rule_status, label_state;

CREATE VIEW v_label_disagreement AS
SELECT evidence_pattern, label_review_status,
       COUNT(*) AS n_intervals,
       ROUND(SUM(interval_length_m), 3) AS logged_m
FROM v_label_evidence
GROUP BY evidence_pattern, label_review_status;

-- One row per interval with the candidate label states side by side (used by figures and tables).
CREATE VIEW v_interval_flags AS
SELECT e.interval_id, e.interval_key, e.hole_id, e.line_code, e.depth_from_m, e.depth_to_m,
       e.interval_length_m, e.midpoint_m, e.rock_code_raw, e.rock_code_status, e.weathering_code,
       e.weathering_status, e.comment_raw, e.is_sgs, e.has_gr_mineral, e.comment_graphitic,
       e.comment_trace_qualified, e.positive_indicators, e.negative_indicators, e.label_conflict,
       e.evidence_pattern, e.label_review_status,
       s.label_state  AS strict_state,
       r.label_state  AS recon_state,
       a3.label_state AS all3_state,
       an.label_state AS any_state
FROM v_label_evidence e
LEFT JOIN v_label_candidates s  ON s.interval_id = e.interval_id  AND s.rule_id  = 'STRICT_SGS_v1'
LEFT JOIN v_label_candidates r  ON r.interval_id = e.interval_id  AND r.rule_id  = 'RECON_2OF3_v1'
LEFT JOIN v_label_candidates a3 ON a3.interval_id = e.interval_id AND a3.rule_id = 'ALL3_v1'
LEFT JOIN v_label_candidates an ON an.interval_id = e.interval_id AND an.rule_id = 'ANY_v1';

CREATE VIEW v_hole_graphite AS
SELECT f.hole_id, f.line_code,
       COUNT(*) AS n_intervals,
       ROUND(SUM(f.interval_length_m), 3) AS logged_m,
       ROUND(SUM(CASE WHEN f.is_sgs = 1 THEN f.interval_length_m ELSE 0 END), 3) AS sgs_m,
       SUM(CASE WHEN f.is_sgs = 1 THEN 1 ELSE 0 END) AS sgs_n,
       ROUND(SUM(CASE WHEN f.has_gr_mineral = 1 THEN f.interval_length_m ELSE 0 END), 3) AS gr_mineral_m,
       ROUND(SUM(CASE WHEN f.comment_graphitic = 1 THEN f.interval_length_m ELSE 0 END), 3) AS comment_graphitic_m,
       ROUND(SUM(CASE WHEN f.comment_trace_qualified = 1 THEN f.interval_length_m ELSE 0 END), 3) AS comment_trace_m,
       ROUND(SUM(CASE WHEN f.recon_state = 'POSITIVE' THEN f.interval_length_m ELSE 0 END), 3) AS recon_pos_m,
       ROUND(SUM(CASE WHEN f.recon_state = 'UNRESOLVED' THEN f.interval_length_m ELSE 0 END), 3) AS recon_unresolved_m,
       SUM(CASE WHEN f.label_conflict = 1 THEN 1 ELSE 0 END) AS conflict_n,
       SUM(CASE WHEN f.rock_code_status <> 'VALID' THEN 1 ELSE 0 END) AS unresolved_code_n
FROM v_interval_flags f
GROUP BY f.hole_id, f.line_code;

CREATE VIEW v_line_graphite AS
SELECT f.line_code,
       COUNT(DISTINCT f.hole_id) AS n_holes,
       COUNT(*) AS n_intervals,
       ROUND(SUM(f.interval_length_m), 3) AS logged_m,
       ROUND(SUM(CASE WHEN f.is_sgs = 1 THEN f.interval_length_m ELSE 0 END), 3) AS sgs_m,
       SUM(CASE WHEN f.is_sgs = 1 THEN 1 ELSE 0 END) AS sgs_n,
       ROUND(SUM(CASE WHEN f.recon_state = 'POSITIVE' THEN f.interval_length_m ELSE 0 END), 3) AS recon_pos_m,
       ROUND(SUM(CASE WHEN f.recon_state = 'UNRESOLVED' THEN f.interval_length_m ELSE 0 END), 3) AS recon_unresolved_m,
       SUM(CASE WHEN f.label_conflict = 1 THEN 1 ELSE 0 END) AS conflict_n,
       SUM(CASE WHEN f.rock_code_status <> 'VALID' THEN 1 ELSE 0 END) AS unresolved_code_n
FROM v_interval_flags f
GROUP BY f.line_code;

CREATE VIEW v_depth_weathering AS
SELECT CAST(f.midpoint_m / 5 AS INTEGER) * 5 AS depth_bin_from_m,
       COALESCE(f.weathering_code, 'MISSING') AS weathering_class,
       COUNT(*) AS n_all,
       SUM(CASE WHEN f.strict_state = 'POSITIVE' THEN 1 ELSE 0 END) AS n_strict_positive,
       SUM(CASE WHEN f.strict_state = 'NEGATIVE' THEN 1 ELSE 0 END) AS n_strict_negative,
       SUM(CASE WHEN f.strict_state = 'UNRESOLVED' THEN 1 ELSE 0 END) AS n_strict_unresolved
FROM v_interval_flags f
GROUP BY depth_bin_from_m, weathering_class;

CREATE VIEW v_rock_code_usage AS
WITH dictionary AS (
    SELECT code, description
    FROM geological_code_dictionary
    WHERE code_domain = 'RockType'
      AND dataset_version_id = (SELECT dataset_version_id FROM v_active_version)
),
observed AS (
    SELECT rock_code_raw AS code, COUNT(*) AS n_intervals, SUM(interval_length_m) AS logged_m
    FROM v_intervals
    WHERE rock_code_raw IS NOT NULL
    GROUP BY rock_code_raw
)
SELECT d.code, d.description AS legend_description, 'VALID' AS code_status,
       COALESCE(o.n_intervals, 0) AS n_intervals, ROUND(COALESCE(o.logged_m, 0), 3) AS logged_m
FROM dictionary d
LEFT JOIN observed o ON o.code = d.code
UNION ALL
SELECT o.code, NULL, 'UNSUPPORTED', o.n_intervals, ROUND(o.logged_m, 3)
FROM observed o
WHERE o.code NOT IN (SELECT code FROM dictionary);

CREATE VIEW v_collar_plan AS
SELECT h.hole_id, h.line_code, h.utm_easting_m AS easting_m, h.utm_northing_m AS northing_m,
       h.easting_alt_m, h.northing_alt_m, h.max_depth_m,
       g.n_intervals, g.logged_m, g.sgs_m, g.sgs_n, g.recon_pos_m,
       CASE WHEN g.logged_m > 0 THEN ROUND(g.sgs_m / g.logged_m, 4) END AS sgs_fraction
FROM v_holes h
JOIN v_hole_graphite g ON g.hole_id = h.hole_id;

CREATE VIEW v_interval_geometry AS
SELECT gb.geometry_build_id, ic.interval_id, i.interval_key, i.hole_id, i.line_code,
       i.depth_from_m, i.depth_to_m, i.midpoint_m, i.rock_code_raw, i.rock_code_status,
       i.weathering_code, i.interval_length_m,
       ic.dip_deg, ic.azimuth_deg, ic.delta_e_m, ic.delta_n_m, ic.delta_z_m,
       ic.easting_m, ic.northing_m, ic.z_relative_m, ic.z_absolute_m, ic.z_reference,
       gb.geometry_status, f.strict_state, f.recon_state
FROM interval_coordinates ic
JOIN geometry_builds gb ON gb.geometry_build_id = ic.geometry_build_id
JOIN v_intervals i ON i.interval_id = ic.interval_id
JOIN v_interval_flags f ON f.interval_id = ic.interval_id
WHERE gb.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_qaqc_summary AS
SELECT f.check_id, c.category, c.description, f.severity, f.status, f.result,
       COUNT(*) AS n_findings,
       SUM(f.n_records) AS n_records
FROM qaqc_findings f
JOIN qaqc_checks c ON c.check_id = f.check_id
WHERE f.dataset_version_id = (SELECT dataset_version_id FROM v_active_version)
GROUP BY f.check_id, c.category, c.description, f.severity, f.status, f.result;

-- Non-blank counts for every raw field, computed from the stored JSON payload of each raw row.
CREATE VIEW v_completeness AS
WITH src AS (
    SELECT 'Collars' AS source_sheet, payload_json FROM raw_collars
    WHERE source_file_id = (SELECT source_file_id FROM v_active_version)
    UNION ALL
    SELECT 'Surveys', payload_json FROM raw_surveys
    WHERE source_file_id = (SELECT source_file_id FROM v_active_version)
    UNION ALL
    SELECT 'Logging', payload_json FROM raw_logging
    WHERE source_file_id = (SELECT source_file_id FROM v_active_version)
)
SELECT s.source_sheet, j.key AS field_name,
       COUNT(*) AS n_rows,
       SUM(CASE WHEN j.type = 'null' OR TRIM(j.value) = '' THEN 0 ELSE 1 END) AS n_non_blank
FROM src s, json_each(s.payload_json) j
GROUP BY s.source_sheet, j.key;

CREATE VIEW v_regional_context AS
SELECT r.regional_polygon_id, r.feature_index, r.geo_symbol, r.stratigraphy, r.legend_text,
       r.metamorphism, r.geom_wkt, r.centroid_e_m, r.centroid_n_m, r.scale_note
FROM regional_geology_context r
WHERE r.intersects_collar_buffer = 1;

CREATE VIEW v_export_receipts AS
SELECT r.receipt_id, r.canonical_dataset_id, r.source_workbook_sha256, r.label_rule_id, r.label_rule_status,
       r.geometry_build_id, r.crs_key, r.vertical_datum_status, r.export_name, r.selected_sql_sha256,
       r.row_count, r.ordered_id_digest, r.status, r.exported_utc
FROM dataset_export_receipts r
WHERE r.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_figure_manifest AS
SELECT m.figure_id, f.title, f.stage_status, m.output_format, m.output_path, m.output_sha256, m.output_bytes,
       m.exported_utc, q.sql_file, q.sql_sha256
FROM figure_export_manifest m
JOIN figure_registry f ON f.figure_id = m.figure_id
LEFT JOIN figure_query_registry q ON q.figure_query_id = m.figure_query_id;

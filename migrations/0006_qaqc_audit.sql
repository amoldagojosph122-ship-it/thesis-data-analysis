-- 0006_qaqc_audit.sql
-- QA/QC catalogue and findings, figure and table registries, test evidence, export receipts,
-- and the regional geology context used as map background only.

CREATE TABLE qaqc_checks (
    check_id                TEXT    PRIMARY KEY,
    category                TEXT    NOT NULL,
    description             TEXT    NOT NULL,
    default_severity        TEXT    NOT NULL CHECK (default_severity IN ('ERROR', 'WARNING', 'INFO')),
    scope_if_failed         TEXT    NOT NULL,                 -- what is blocked or qualified when the check fails
    method                  TEXT    NOT NULL
);

CREATE TABLE qaqc_findings (
    finding_id              INTEGER PRIMARY KEY,
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    check_id                TEXT    NOT NULL REFERENCES qaqc_checks (check_id),
    severity                TEXT    NOT NULL CHECK (severity IN ('ERROR', 'WARNING', 'INFO')),
    status                  TEXT    NOT NULL CHECK (status IN ('BLOCKED', 'PROVISIONAL', 'APPROVED')),
    result                  TEXT    NOT NULL CHECK (result IN ('PASS', 'FAIL')),
    entity_type             TEXT    NOT NULL CHECK (entity_type IN
                              ('DATASET', 'SHEET', 'HOLE', 'INTERVAL', 'CODE', 'COLUMN', 'SURVEY', 'LINE', 'COORDINATE')),
    entity_key              TEXT    NOT NULL DEFAULT '',
    source_sheet            TEXT,
    source_row              INTEGER,
    n_records               INTEGER NOT NULL DEFAULT 0 CHECK (n_records >= 0),
    detail                  TEXT    NOT NULL,
    UNIQUE (dataset_version_id, check_id, entity_type, entity_key)
);

CREATE TABLE qaqc_resolutions (
    resolution_id           INTEGER PRIMARY KEY,
    finding_id              INTEGER NOT NULL REFERENCES qaqc_findings (finding_id),
    action                  TEXT    NOT NULL CHECK (action IN
                              ('RETAINED_RAW', 'QUARANTINED', 'NULL_LABEL_UNRESOLVED', 'PROVISIONAL_GEOMETRY',
                               'NO_ACTION_REQUIRED', 'REVIEW_REQUIRED')),
    decided_by              TEXT    NOT NULL,
    decided_utc             TEXT    NOT NULL,
    rationale               TEXT    NOT NULL
);

CREATE TABLE figure_registry (
    figure_id               TEXT    PRIMARY KEY,              -- F01..F09, T01..T03
    objective               TEXT    NOT NULL CHECK (objective IN ('O1', 'O2', 'O3', 'O4', 'O5')),
    kind                    TEXT    NOT NULL CHECK (kind IN ('FIGURE', 'TABLE')),
    title                   TEXT    NOT NULL,
    caption                 TEXT    NOT NULL,
    stage_status            TEXT    NOT NULL CHECK (stage_status IN ('VERIFIED', 'PROVISIONAL', 'BLOCKED', 'DEFERRED', 'FAILED')),
    geometry_status         TEXT    NOT NULL,
    label_status            TEXT    NOT NULL,
    denominator             TEXT    NOT NULL,
    sql_file                TEXT    NOT NULL,
    renderer                TEXT    NOT NULL,
    created_utc             TEXT    NOT NULL
);

CREATE TABLE figure_query_registry (
    figure_query_id         INTEGER PRIMARY KEY,
    figure_id               TEXT    NOT NULL REFERENCES figure_registry (figure_id),
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    sql_file                TEXT    NOT NULL,
    sql_sha256              TEXT    NOT NULL,
    row_count               INTEGER NOT NULL CHECK (row_count >= 0),
    query_run_utc           TEXT    NOT NULL,
    analysis_run_id         INTEGER REFERENCES analysis_runs (analysis_run_id),
    UNIQUE (figure_id, dataset_version_id, sql_sha256, analysis_run_id)
);

CREATE TABLE figure_export_manifest (
    export_id               INTEGER PRIMARY KEY,
    figure_id               TEXT    NOT NULL REFERENCES figure_registry (figure_id),
    output_path             TEXT    NOT NULL,
    output_format           TEXT    NOT NULL CHECK (output_format IN ('SVG', 'PDF', 'PNG', 'CSV', 'MD', 'TEX', 'HTML')),
    output_sha256           TEXT    NOT NULL,
    output_bytes            INTEGER NOT NULL CHECK (output_bytes > 0),
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    figure_query_id         INTEGER REFERENCES figure_query_registry (figure_query_id),
    renderer_sha256         TEXT    NOT NULL,
    exported_utc            TEXT    NOT NULL,
    UNIQUE (figure_id, output_path)
);

-- Declared for completeness of the Stage A contract. Stage A writes no snapshots (views are used instead).
CREATE TABLE plot_statistic_snapshots (
    snapshot_id             INTEGER PRIMARY KEY,
    figure_id               TEXT    NOT NULL REFERENCES figure_registry (figure_id),
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    statistic_name          TEXT    NOT NULL,
    statistic_value         REAL,
    denominator             INTEGER,
    created_utc             TEXT    NOT NULL
);

CREATE TABLE validation_test_results (
    test_result_id          INTEGER PRIMARY KEY,
    run_utc                 TEXT    NOT NULL,
    dataset_version_id      INTEGER REFERENCES dataset_versions (dataset_version_id),
    test_group              TEXT    NOT NULL CHECK (test_group IN ('SQL_INTEGRITY', 'RECONCILIATION', 'PYTEST', 'FIGURE_PROVENANCE')),
    test_name               TEXT    NOT NULL,
    expected                TEXT    NOT NULL,
    observed                TEXT    NOT NULL,
    outcome                 TEXT    NOT NULL CHECK (outcome IN ('PASS', 'FAIL', 'WARN', 'NOT_RUN')),
    detail                  TEXT
);

CREATE TABLE dataset_export_receipts (
    receipt_id              INTEGER PRIMARY KEY,
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    canonical_dataset_id    TEXT    NOT NULL,                 -- obj1_master:<dataset_version_key prefix>
    source_workbook_sha256  TEXT    NOT NULL,
    label_rule_id          TEXT    REFERENCES graphite_label_rules (rule_id),   -- NULL for exports that carry no label
    label_rule_status       TEXT,
    geometry_build_id       INTEGER REFERENCES geometry_builds (geometry_build_id),
    crs_key                 TEXT    NOT NULL,
    vertical_datum_status   TEXT    NOT NULL,
    export_name             TEXT    NOT NULL,
    selected_sql_sha256     TEXT    NOT NULL,
    row_count               INTEGER NOT NULL CHECK (row_count >= 0),
    ordered_id_digest       TEXT    NOT NULL,                 -- sha256 over ordered interval_key values
    status                  TEXT    NOT NULL CHECK (status IN ('VERIFIED', 'PROVISIONAL', 'BLOCKED', 'DEFERRED', 'FAILED')),
    exported_utc            TEXT    NOT NULL,
    UNIQUE (dataset_version_id, export_name, selected_sql_sha256)
);

-- Regional 1:1,000,000 geology polygons intersecting a buffer around the collars. Context only.
CREATE TABLE regional_geology_context (
    regional_polygon_id     INTEGER PRIMARY KEY,
    source_sha256           TEXT    NOT NULL,
    feature_index           INTEGER NOT NULL CHECK (feature_index >= 0),
    geo_symbol              TEXT    NOT NULL,
    stratigraphy            TEXT,
    legend_text             TEXT,
    metamorphism            TEXT,
    geom_wkt                TEXT    NOT NULL,
    centroid_e_m            REAL    NOT NULL,
    centroid_n_m            REAL    NOT NULL,
    intersects_collar_buffer INTEGER NOT NULL CHECK (intersects_collar_buffer IN (0, 1)),
    scale_note              TEXT    NOT NULL,
    UNIQUE (source_sha256, feature_index)
);

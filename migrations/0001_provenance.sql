-- 0001_provenance.sql
-- Provenance tables for obj1_master (database/kambale_thesis.sqlite).
-- Every raw-to-curated derivation is traceable through these tables.

CREATE TABLE source_files (
    source_file_id   INTEGER PRIMARY KEY,
    file_name        TEXT    NOT NULL,
    original_path    TEXT    NOT NULL,           -- path as supplied, recorded for audit
    raw_copy_path    TEXT    NOT NULL,           -- immutable copy under data/raw/
    sha256           TEXT    NOT NULL UNIQUE CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    size_bytes       INTEGER NOT NULL CHECK (size_bytes > 0),
    first_seen_utc   TEXT    NOT NULL,
    notes            TEXT
);

CREATE TABLE source_sheets (
    source_sheet_id     INTEGER PRIMARY KEY,
    source_file_id      INTEGER NOT NULL REFERENCES source_files (source_file_id),
    sheet_name          TEXT    NOT NULL,
    sheet_state         TEXT    NOT NULL CHECK (sheet_state IN ('visible', 'hidden', 'veryHidden')),
    n_rows              INTEGER NOT NULL CHECK (n_rows >= 0),
    n_cols              INTEGER NOT NULL CHECK (n_cols >= 0),
    header_json         TEXT,                   -- JSON array of header strings as stored in the workbook
    blank_columns_json  TEXT,                   -- JSON array of header names whose data cells are all blank
    UNIQUE (source_file_id, sheet_name)
);

CREATE TABLE ingestion_runs (
    ingestion_run_id     INTEGER PRIMARY KEY,
    source_file_id       INTEGER NOT NULL REFERENCES source_files (source_file_id),
    started_utc          TEXT    NOT NULL,
    finished_utc         TEXT,
    etl_version          TEXT    NOT NULL,
    dataset_version_key  TEXT,
    status               TEXT    NOT NULL CHECK (status IN ('RUNNING', 'VERIFIED', 'NOOP_IDENTICAL', 'FAILED')),
    message              TEXT
);

CREATE TABLE dataset_versions (
    dataset_version_id       INTEGER PRIMARY KEY,
    dataset_version_key      TEXT    NOT NULL UNIQUE,
    dataset_label            TEXT    NOT NULL,
    source_file_id           INTEGER NOT NULL REFERENCES source_files (source_file_id),
    etl_version              TEXT    NOT NULL,
    rule_versions_json       TEXT    NOT NULL,
    coordinate_decision_json TEXT    NOT NULL,
    status                   TEXT    NOT NULL CHECK (status IN ('BUILDING', 'ACTIVE', 'ARCHIVED', 'FAILED')),
    overall_status           TEXT    CHECK (overall_status IN ('VERIFIED', 'PROVISIONAL', 'BLOCKED', 'DEFERRED', 'FAILED')),
    created_utc              TEXT    NOT NULL,
    activated_utc            TEXT,
    archived_utc             TEXT
);

-- Exactly one ACTIVE dataset version may exist at any time.
CREATE UNIQUE INDEX ux_dataset_versions_one_active
    ON dataset_versions (status) WHERE status = 'ACTIVE';

CREATE TABLE raw_row_map (
    raw_row_map_id   INTEGER PRIMARY KEY,
    source_file_id   INTEGER NOT NULL REFERENCES source_files (source_file_id),
    source_sheet     TEXT    NOT NULL,
    source_row       INTEGER NOT NULL CHECK (source_row >= 1),   -- 1-based Excel row number
    raw_table        TEXT    NOT NULL,
    raw_rowid        INTEGER NOT NULL,
    UNIQUE (source_file_id, source_sheet, source_row)
);

CREATE TABLE analysis_runs (
    analysis_run_id   INTEGER PRIMARY KEY,
    command           TEXT    NOT NULL,
    args_json         TEXT    NOT NULL,
    code_version      TEXT    NOT NULL,
    dataset_version_id INTEGER REFERENCES dataset_versions (dataset_version_id),
    started_utc       TEXT    NOT NULL,
    finished_utc      TEXT,
    status            TEXT    NOT NULL CHECK (status IN ('RUNNING', 'VERIFIED', 'FAILED', 'BLOCKED')),
    message           TEXT
);

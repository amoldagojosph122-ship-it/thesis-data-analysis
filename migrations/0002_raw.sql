-- 0002_raw.sql
-- Immutable raw copies of workbook rows. Column names match the workbook headers exactly.
-- No declared column types: SQLite stores each value as read (no affinity coercion).
-- UPDATE and DELETE are rejected by triggers so source rows are never overwritten.

CREATE TABLE raw_collars (
    raw_collars_id   INTEGER PRIMARY KEY,
    source_file_id   INTEGER NOT NULL REFERENCES source_files (source_file_id),
    source_sheet     TEXT    NOT NULL DEFAULT 'Collars',
    source_row       INTEGER NOT NULL CHECK (source_row >= 2),
    HoleID,
    Grid,
    HoleType,
    Northing,
    Easting,
    RL,
    UTMNorthing,
    UTMEasting,
    max_depth,
    Project,
    Prospect,
    Contractor,
    LoggedBy,
    DateDrilled,
    payload_json    TEXT    NOT NULL,
    UNIQUE (source_file_id, source_sheet, source_row)
);

CREATE TABLE raw_surveys (
    raw_surveys_id   INTEGER PRIMARY KEY,
    source_file_id   INTEGER NOT NULL REFERENCES source_files (source_file_id),
    source_sheet     TEXT    NOT NULL DEFAULT 'Surveys',
    source_row       INTEGER NOT NULL CHECK (source_row >= 2),
    HoleID,
    depth,
    dip,
    azimuth,
    SurveyedBy,
    Instrument,
    payload_json    TEXT    NOT NULL,
    UNIQUE (source_file_id, source_sheet, source_row)
);

CREATE TABLE raw_logging (
    raw_logging_id   INTEGER PRIMARY KEY,
    source_file_id   INTEGER NOT NULL REFERENCES source_files (source_file_id),
    source_sheet     TEXT    NOT NULL DEFAULT 'Logging',
    source_row       INTEGER NOT NULL CHECK (source_row >= 2),
    HOLEID,
    DEPTH_FROM,
    DEPTH_TO,
    rock_type1,
    colour1,
    colour2,
    weathering,
    grainsize,
    structure,
    alt_min1,
    alt_min1int,
    alt_min2,
    alt_min2int,
    sul_min1,
    sul_min1pc,
    vn_type,
    vn_pc,
    Comment,
    sample_quality,
    payload_json    TEXT    NOT NULL,
    UNIQUE (source_file_id, source_sheet, source_row)
);

CREATE TABLE raw_geological_legend (
    raw_legend_id    INTEGER PRIMARY KEY,
    source_file_id   INTEGER NOT NULL REFERENCES source_files (source_file_id),
    source_sheet     TEXT    NOT NULL DEFAULT 'Logging Legend',
    source_row       INTEGER NOT NULL CHECK (source_row >= 1),
    legend_reference,
    legend_value,
    description,
    payload_json     TEXT    NOT NULL,
    UNIQUE (source_file_id, source_sheet, source_row)
);

-- Hidden reference sheets (___LoggingReferences, ___SurveyReferences, ___CollarReferences, ___SheetInfo).
-- Values are stored one row per (sheet, column, ordinal). The ___SheetInfo worksheet-protection value
-- is redacted in this copy; the original workbook bytes are unchanged and hashed in source_files.
CREATE TABLE raw_reference_lists (
    raw_reference_id INTEGER PRIMARY KEY,
    source_file_id   INTEGER NOT NULL REFERENCES source_files (source_file_id),
    source_sheet     TEXT    NOT NULL,
    source_row       INTEGER NOT NULL CHECK (source_row >= 1),
    column_name      TEXT    NOT NULL,
    ordinal          INTEGER NOT NULL CHECK (ordinal >= 1),
    value            TEXT,
    redacted         INTEGER NOT NULL DEFAULT 0 CHECK (redacted IN (0, 1)),
    UNIQUE (source_file_id, source_sheet, column_name, ordinal)
);

CREATE TRIGGER raw_collars_no_update BEFORE UPDATE ON raw_collars
BEGIN SELECT RAISE(ABORT, 'raw_collars is immutable'); END;
CREATE TRIGGER raw_collars_no_delete BEFORE DELETE ON raw_collars
BEGIN SELECT RAISE(ABORT, 'raw_collars is immutable'); END;

CREATE TRIGGER raw_surveys_no_update BEFORE UPDATE ON raw_surveys
BEGIN SELECT RAISE(ABORT, 'raw_surveys is immutable'); END;
CREATE TRIGGER raw_surveys_no_delete BEFORE DELETE ON raw_surveys
BEGIN SELECT RAISE(ABORT, 'raw_surveys is immutable'); END;

CREATE TRIGGER raw_logging_no_update BEFORE UPDATE ON raw_logging
BEGIN SELECT RAISE(ABORT, 'raw_logging is immutable'); END;
CREATE TRIGGER raw_logging_no_delete BEFORE DELETE ON raw_logging
BEGIN SELECT RAISE(ABORT, 'raw_logging is immutable'); END;

CREATE TRIGGER raw_legend_no_update BEFORE UPDATE ON raw_geological_legend
BEGIN SELECT RAISE(ABORT, 'raw_geological_legend is immutable'); END;
CREATE TRIGGER raw_legend_no_delete BEFORE DELETE ON raw_geological_legend
BEGIN SELECT RAISE(ABORT, 'raw_geological_legend is immutable'); END;

CREATE TRIGGER raw_reference_no_update BEFORE UPDATE ON raw_reference_lists
BEGIN SELECT RAISE(ABORT, 'raw_reference_lists is immutable'); END;
CREATE TRIGGER raw_reference_no_delete BEFORE DELETE ON raw_reference_lists
BEGIN SELECT RAISE(ABORT, 'raw_reference_lists is immutable'); END;

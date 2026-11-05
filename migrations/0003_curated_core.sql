-- 0003_curated_core.sql
-- Curated, version-scoped records. Every row carries dataset_version_id and a link to its raw row.
-- Holes, surveys and intervals are keyed by the normalised hole_id; raw spellings are kept.

CREATE TABLE drill_lines (
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    line_code               TEXT    NOT NULL,                 -- e.g. NOM_N1112140 (nominal Northing)
    nominal_northing_m      REAL    NOT NULL,
    n_holes                 INTEGER NOT NULL CHECK (n_holes > 0),
    n_intervals             INTEGER NOT NULL CHECK (n_intervals >= 0),
    grouping_method         TEXT    NOT NULL,
    status                  TEXT    NOT NULL CHECK (status IN ('PROVISIONAL', 'APPROVED')),
    PRIMARY KEY (dataset_version_id, line_code)
);

CREATE TABLE holes (
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    hole_id                 TEXT    NOT NULL,                 -- normalised identifier
    raw_hole_id             TEXT    NOT NULL,                 -- as stored in the workbook
    raw_collars_id          INTEGER NOT NULL REFERENCES raw_collars (raw_collars_id),
    hole_type               TEXT    NOT NULL,
    grid_label              TEXT    NOT NULL,                 -- grid nickname as recorded (e.g. UTM_30N)
    easting_alt_m           REAL,                             -- Easting column (alternate pair)
    northing_alt_m          REAL,                             -- Northing column (alternate pair)
    utm_easting_m           REAL,                             -- UTMEasting column
    utm_northing_m          REAL,                             -- UTMNorthing column
    line_code               TEXT,
    rl_status               TEXT    NOT NULL CHECK (rl_status IN ('MISSING', 'PRESENT')),
    rl_m                    REAL    CHECK (rl_m IS NULL OR rl_status = 'PRESENT'),
    max_depth_m             REAL    NOT NULL CHECK (max_depth_m > 0),
    project_code            TEXT,
    prospect                TEXT,
    contractor              TEXT,                             -- NULL when blank
    logged_by               TEXT,
    date_drilled            TEXT    CHECK (date_drilled IS NULL OR date_drilled GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    date_drilled_raw        TEXT,
    PRIMARY KEY (dataset_version_id, hole_id),
    FOREIGN KEY (dataset_version_id, line_code) REFERENCES drill_lines (dataset_version_id, line_code)
);

CREATE TABLE survey_stations (
    survey_station_id       INTEGER PRIMARY KEY,
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    hole_id                 TEXT    NOT NULL,
    raw_surveys_id          INTEGER NOT NULL REFERENCES raw_surveys (raw_surveys_id),
    depth_m                 REAL    NOT NULL CHECK (depth_m > 0),
    dip_deg                 REAL    NOT NULL CHECK (dip_deg >= -90 AND dip_deg <= 0),   -- from horizontal, negative downward
    azimuth_deg             REAL    NOT NULL CHECK (azimuth_deg >= 0 AND azimuth_deg < 360),
    station_kind            TEXT    NOT NULL CHECK (station_kind IN ('END_OF_HOLE_ONLY', 'MULTI_STATION', 'SINGLE_STATION_OTHER')),
    surveyed_by             TEXT,                             -- NULL = MISSING in source
    instrument              TEXT,                             -- NULL = MISSING in source
    convention_status       TEXT    NOT NULL CHECK (convention_status IN ('PROVISIONAL', 'APPROVED')),
    UNIQUE (dataset_version_id, hole_id, depth_m),
    FOREIGN KEY (dataset_version_id, hole_id) REFERENCES holes (dataset_version_id, hole_id)
);

CREATE TABLE geological_code_dictionary (
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    code_domain             TEXT    NOT NULL CHECK (code_domain IN
                              ('RockType', 'Colour', 'Weathering', 'Structure', 'RTMineral', 'SulMineral', 'Veining', 'SampleQual')),
    code                    TEXT    NOT NULL,
    description             TEXT    NOT NULL,
    legend_source_row       INTEGER,
    in_logging_legend       INTEGER NOT NULL CHECK (in_logging_legend IN (0, 1)),
    in_hidden_reference     INTEGER NOT NULL CHECK (in_hidden_reference IN (0, 1)),
    PRIMARY KEY (dataset_version_id, code_domain, code)
);

CREATE TABLE logging_intervals (
    interval_id             INTEGER PRIMARY KEY,
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    interval_key            TEXT    NOT NULL,                 -- stable across versions: hole_id@from
    hole_id                 TEXT    NOT NULL,
    raw_logging_id          INTEGER NOT NULL REFERENCES raw_logging (raw_logging_id),
    source_row              INTEGER NOT NULL,
    depth_from_m            REAL    NOT NULL CHECK (depth_from_m >= 0),
    depth_to_m              REAL    NOT NULL CHECK (depth_to_m > depth_from_m),
    interval_length_m       REAL    NOT NULL CHECK (interval_length_m > 0),
    midpoint_m              REAL    NOT NULL CHECK (midpoint_m > 0),
    rock_code_raw           TEXT,
    rock_code_status        TEXT    NOT NULL CHECK (rock_code_status IN ('VALID', 'UNSUPPORTED', 'MISSING')),
    rock_description        TEXT,
    colour1_code            TEXT,
    colour2_code            TEXT,
    weathering_code         TEXT,
    weathering_status       TEXT    NOT NULL CHECK (weathering_status IN ('VALID', 'MISSING', 'UNSUPPORTED')),
    grainsize_raw           REAL,
    structure_code          TEXT,
    alt_min1_code           TEXT,
    alt_min1_int            REAL,
    alt_min2_code           TEXT,
    alt_min2_int            REAL,
    sul_min1_code           TEXT,
    sul_min1_pc             REAL,
    vn_type                 TEXT,
    vn_pc                   REAL,
    comment_raw             TEXT,
    sample_quality_code     TEXT,
    UNIQUE (dataset_version_id, interval_key),
    UNIQUE (dataset_version_id, hole_id, depth_from_m),
    FOREIGN KEY (dataset_version_id, hole_id) REFERENCES holes (dataset_version_id, hole_id)
);

CREATE INDEX ix_logging_intervals_hole ON logging_intervals (dataset_version_id, hole_id);
CREATE INDEX ix_survey_stations_hole ON survey_stations (dataset_version_id, hole_id);

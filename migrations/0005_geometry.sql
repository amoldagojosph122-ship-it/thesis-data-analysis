-- 0005_geometry.sql
-- Coordinate decisions, elevation status and versioned straight-hole geometry.
-- Absolute elevation is blocked by construction: interval_coordinates.z_absolute_m must be NULL.
-- A later migration may relax the CHECK only after an APPROVED elevation source is recorded.

CREATE TABLE coordinate_system_registry (
    crs_key                 TEXT    PRIMARY KEY,              -- e.g. EPSG:32630
    authority_code          TEXT    NOT NULL,
    crs_name                TEXT    NOT NULL,
    projection              TEXT    NOT NULL,
    zone                    TEXT,
    datum_name              TEXT,
    datum_status            TEXT    NOT NULL CHECK (datum_status IN ('VERIFIED', 'UNVERIFIED')),
    horizontal_units        TEXT    NOT NULL CHECK (horizontal_units = 'm'),
    evidence                TEXT    NOT NULL,
    status                  TEXT    NOT NULL CHECK (status IN ('PROVISIONAL', 'APPROVED', 'BLOCKED'))
);

CREATE TABLE coordinate_decisions (
    coordinate_decision_id          INTEGER PRIMARY KEY,
    dataset_version_id              INTEGER NOT NULL UNIQUE REFERENCES dataset_versions (dataset_version_id),
    adopted_pair                    TEXT    NOT NULL CHECK (adopted_pair IN ('UTM_EASTING_NORTHING', 'EASTING_NORTHING')),
    crs_key                         TEXT    NOT NULL REFERENCES coordinate_system_registry (crs_key),
    units                           TEXT    NOT NULL CHECK (units = 'm'),
    transform_chain                 TEXT    NOT NULL,
    rationale                       TEXT    NOT NULL,
    n_holes                         INTEGER NOT NULL CHECK (n_holes > 0),
    median_pair_discrepancy_m       REAL    NOT NULL CHECK (median_pair_discrepancy_m >= 0),
    max_pair_discrepancy_m          REAL    NOT NULL CHECK (max_pair_discrepancy_m >= median_pair_discrepancy_m),
    status                          TEXT    NOT NULL CHECK (status IN ('PROVISIONAL', 'APPROVED')),
    approved_by                     TEXT,
    approved_utc                    TEXT
);

CREATE TABLE elevation_sources (
    elevation_source_id     INTEGER PRIMARY KEY,
    source_type             TEXT    NOT NULL CHECK (source_type IN ('NONE', 'DGPS_SURVEY', 'DEM', 'OTHER')),
    description             TEXT    NOT NULL,
    vertical_datum          TEXT,
    status                  TEXT    NOT NULL CHECK (status IN ('BLOCKED', 'PROVISIONAL', 'APPROVED')),
    approved_by             TEXT,
    approved_utc            TEXT,
    CHECK (status <> 'APPROVED' OR (vertical_datum IS NOT NULL AND approved_by IS NOT NULL))
);

INSERT INTO elevation_sources (elevation_source_id, source_type, description, vertical_datum, status)
VALUES (1, 'NONE',
        'No collar RL in workbook (RL blank for all collars); no DGPS survey or DEM supplied. Absolute elevation BLOCKED.',
        NULL, 'BLOCKED');

CREATE TABLE geometry_builds (
    geometry_build_id       INTEGER PRIMARY KEY,
    dataset_version_id      INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    coordinate_decision_id  INTEGER NOT NULL REFERENCES coordinate_decisions (coordinate_decision_id),
    elevation_source_id     INTEGER NOT NULL REFERENCES elevation_sources (elevation_source_id),
    method                  TEXT    NOT NULL CHECK (method = 'STRAIGHT_HOLE_EOH_ORIENTATION'),
    convention_text         TEXT    NOT NULL,
    angle_status            TEXT    NOT NULL CHECK (angle_status IN ('PROVISIONAL', 'APPROVED')),
    geometry_status         TEXT    NOT NULL CHECK (geometry_status IN ('PROVISIONAL_RELATIVE', 'BLOCKED_ABSOLUTE')),
    n_intervals             INTEGER NOT NULL CHECK (n_intervals >= 0),
    created_utc             TEXT    NOT NULL,
    UNIQUE (dataset_version_id, method)
);

CREATE TABLE interval_coordinates (
    geometry_build_id       INTEGER NOT NULL REFERENCES geometry_builds (geometry_build_id),
    interval_id             INTEGER NOT NULL REFERENCES logging_intervals (interval_id),
    midpoint_m              REAL    NOT NULL CHECK (midpoint_m > 0),
    dip_deg                 REAL    NOT NULL CHECK (dip_deg >= -90 AND dip_deg <= 0),
    azimuth_deg             REAL    NOT NULL CHECK (azimuth_deg >= 0 AND azimuth_deg < 360),
    delta_e_m               REAL    NOT NULL,
    delta_n_m               REAL    NOT NULL,
    delta_z_m               REAL    NOT NULL,
    easting_m               REAL    NOT NULL,
    northing_m              REAL    NOT NULL,
    z_relative_m            REAL    NOT NULL,                  -- relative to collar; NOT an elevation
    z_reference             TEXT    NOT NULL CHECK (z_reference = 'RELATIVE_TO_COLLAR'),
    z_absolute_m            REAL    CHECK (z_absolute_m IS NULL),  -- kept NULL until an APPROVED elevation source exists
    elevation_source_id     INTEGER NOT NULL REFERENCES elevation_sources (elevation_source_id),
    PRIMARY KEY (geometry_build_id, interval_id)
);

CREATE INDEX ix_interval_coordinates_build ON interval_coordinates (geometry_build_id);

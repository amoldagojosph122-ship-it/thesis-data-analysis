-- Objective 2 database: database/kambale_obj2_spatial.sqlite
-- Owns derived spatial summaries, experimental variograms, fits, diagnostics, gates and handoff decisions.
-- Objective 1 is read only. Keys are stable upstream identifiers recorded through source_receipts.
-- SQLite does not enforce foreign keys across database files; receipt and key checks run in the verifier.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version_id      INTEGER PRIMARY KEY CHECK (version_id = 1),
    schema_name     TEXT    NOT NULL,
    applied_utc     TEXT    NOT NULL
);

-- One row per imported Objective 1 snapshot. Imports are refused unless every status below matches.
CREATE TABLE IF NOT EXISTS source_receipts (
    receipt_id                    INTEGER PRIMARY KEY,
    upstream_logical_name         TEXT    NOT NULL CHECK (upstream_logical_name = 'obj1_master'),
    upstream_path                 TEXT    NOT NULL,
    upstream_dataset_version_id   INTEGER NOT NULL,
    upstream_dataset_version_key  TEXT    NOT NULL,
    upstream_etl_version          TEXT    NOT NULL,
    label_rule_id                 TEXT    NOT NULL,
    label_rule_status             TEXT    NOT NULL CHECK (label_rule_status = 'APPROVED'),
    label_rule_definition_sha256  TEXT    NOT NULL,
    geometry_build_id             INTEGER NOT NULL,
    geometry_status               TEXT    NOT NULL CHECK (geometry_status = 'PROVISIONAL_RELATIVE'),
    crs_key                       TEXT    NOT NULL CHECK (crs_key = 'EPSG:32630'),
    crs_datum_status              TEXT    NOT NULL CHECK (crs_datum_status = 'VERIFIED'),
    coordinate_pair_status        TEXT    NOT NULL CHECK (coordinate_pair_status = 'APPROVED'),
    drill_line_status             TEXT    NOT NULL CHECK (drill_line_status = 'APPROVED'),
    vertical_basis                TEXT    NOT NULL CHECK (vertical_basis = 'RELATIVE_TO_COLLAR'),
    content_sha256                TEXT    NOT NULL,
    row_count                     INTEGER NOT NULL CHECK (row_count >= 0),
    ordered_id_digest             TEXT    NOT NULL,
    selection_query_sha256        TEXT    NOT NULL,
    imported_utc                  TEXT    NOT NULL,
    code_commit                   TEXT,
    UNIQUE (upstream_dataset_version_key, content_sha256)
);

CREATE TABLE IF NOT EXISTS stage_runs (
    run_id              INTEGER PRIMARY KEY,
    run_kind            TEXT    NOT NULL CHECK (run_kind IN ('IMPORT','ANALYSE','SENSITIVITY','FIGURES','TABLES','VERIFY')),
    config_version      TEXT    NOT NULL,
    config_sha256       TEXT    NOT NULL,
    receipt_id          INTEGER REFERENCES source_receipts (receipt_id),
    started_utc         TEXT    NOT NULL,
    finished_utc        TEXT,
    status              TEXT    NOT NULL CHECK (status IN ('RUNNING','COMPLETED','FAILED','STOPPED')),
    code_commit         TEXT,
    note                TEXT
);

-- Analytical snapshot of the 1,910 logged intervals of one receipt (no copy of the raw logging rows).
CREATE TABLE IF NOT EXISTS analysis_observations (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    upstream_interval_id    INTEGER NOT NULL,
    upstream_interval_key   TEXT    NOT NULL,
    hole_id                 TEXT    NOT NULL,
    line_code               TEXT    NOT NULL,
    depth_from_m            REAL    NOT NULL CHECK (depth_from_m >= 0),
    depth_to_m              REAL    NOT NULL CHECK (depth_to_m > depth_from_m),
    support_length_m        REAL    NOT NULL CHECK (support_length_m = 1.0),
    midpoint_m              REAL    NOT NULL CHECK (midpoint_m > 0),
    weathering_code         TEXT,
    rock_code_raw           TEXT,
    rock_code_status        TEXT    NOT NULL,
    label_state             TEXT    NOT NULL CHECK (label_state IN ('POSITIVE','NEGATIVE','AMBIGUOUS','UNRESOLVED')),
    in_binary_target        INTEGER NOT NULL CHECK (in_binary_target IN (0,1)),
    indicator               INTEGER CHECK (indicator IN (0,1)),
    easting_m               REAL    NOT NULL,
    northing_m              REAL    NOT NULL,
    z_relative_m            REAL    NOT NULL CHECK (z_relative_m <= 0),
    geometry_status         TEXT    NOT NULL CHECK (geometry_status = 'PROVISIONAL_RELATIVE'),
    PRIMARY KEY (receipt_id, upstream_interval_id),
    UNIQUE (receipt_id, upstream_interval_key),
    CHECK ((label_state = 'POSITIVE' AND indicator = 1 AND in_binary_target = 1)
        OR (label_state = 'NEGATIVE' AND indicator = 0 AND in_binary_target = 1)
        OR (label_state IN ('AMBIGUOUS','UNRESOLVED') AND indicator IS NULL AND in_binary_target = 0))
);
CREATE INDEX IF NOT EXISTS ix_obs_hole ON analysis_observations (receipt_id, hole_id);
CREATE INDEX IF NOT EXISTS ix_obs_line ON analysis_observations (receipt_id, line_code);

-- Collar positions and totals of one receipt (UTM 30N metres; maximum depth in metres).
-- Added during implementation so that the footprint figure and the collar spacing diagnostics read from this database.
CREATE TABLE IF NOT EXISTS collar_locations (
    receipt_id          INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    hole_id             TEXT    NOT NULL,
    line_code           TEXT    NOT NULL,
    utm_easting_m       REAL    NOT NULL,
    utm_northing_m      REAL    NOT NULL,
    max_depth_m         REAL,
    PRIMARY KEY (receipt_id, hole_id)
);

-- Label of each interval under a comparator rule (STRICT_SGS_v1), read from the Objective 1 database. Used only for the
-- comparator sensitivity run; the handoff basis is always the approved DESIGN_8_2_v1 indicator.
CREATE TABLE IF NOT EXISTS comparator_observations (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    upstream_interval_id    INTEGER NOT NULL,
    rule_id                 TEXT    NOT NULL,
    label_state             TEXT    NOT NULL CHECK (label_state IN ('POSITIVE','NEGATIVE','AMBIGUOUS','UNRESOLVED')),
    in_binary_target        INTEGER NOT NULL CHECK (in_binary_target IN (0,1)),
    indicator               INTEGER CHECK (indicator IN (0,1)),
    PRIMARY KEY (receipt_id, upstream_interval_id, rule_id),
    CHECK ((label_state = 'POSITIVE' AND indicator = 1 AND in_binary_target = 1)
        OR (label_state = 'NEGATIVE' AND indicator = 0 AND in_binary_target = 1)
        OR (label_state IN ('AMBIGUOUS','UNRESOLVED') AND indicator IS NULL AND in_binary_target = 0))
);

CREATE TABLE IF NOT EXISTS hole_occurrence_summaries (
    receipt_id                  INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    hole_id                     TEXT    NOT NULL,
    line_code                   TEXT    NOT NULL,
    n_intervals                 INTEGER NOT NULL CHECK (n_intervals > 0),
    logged_m                    REAL    NOT NULL CHECK (logged_m > 0),
    binary_n                    INTEGER NOT NULL CHECK (binary_n >= 0),
    positive_n                  INTEGER NOT NULL CHECK (positive_n >= 0),
    negative_n                  INTEGER NOT NULL CHECK (negative_n >= 0),
    ambiguous_n                 INTEGER NOT NULL CHECK (ambiguous_n >= 0),
    unresolved_n                INTEGER NOT NULL CHECK (unresolved_n >= 0),
    positive_apparent_m         REAL    NOT NULL CHECK (positive_apparent_m >= 0),
    graphitic_fraction_binary   REAL    CHECK (graphitic_fraction_binary IS NULL OR graphitic_fraction_binary BETWEEN 0 AND 1),
    n_distinct_intersections    INTEGER NOT NULL CHECK (n_distinct_intersections >= 0),
    PRIMARY KEY (receipt_id, hole_id),
    CHECK (binary_n = positive_n + negative_n),
    CHECK (n_intervals = binary_n + ambiguous_n + unresolved_n)
);

CREATE TABLE IF NOT EXISTS line_occurrence_summaries (
    receipt_id                  INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    line_code                   TEXT    NOT NULL,
    n_holes                     INTEGER NOT NULL CHECK (n_holes > 0),
    n_intervals                 INTEGER NOT NULL CHECK (n_intervals > 0),
    logged_m                    REAL    NOT NULL CHECK (logged_m > 0),
    binary_n                    INTEGER NOT NULL CHECK (binary_n >= 0),
    positive_n                  INTEGER NOT NULL CHECK (positive_n >= 0),
    negative_n                  INTEGER NOT NULL CHECK (negative_n >= 0),
    ambiguous_n                 INTEGER NOT NULL CHECK (ambiguous_n >= 0),
    unresolved_n                INTEGER NOT NULL CHECK (unresolved_n >= 0),
    positive_apparent_m         REAL    NOT NULL CHECK (positive_apparent_m >= 0),
    graphitic_fraction_binary   REAL    CHECK (graphitic_fraction_binary IS NULL OR graphitic_fraction_binary BETWEEN 0 AND 1),
    n_distinct_intersections    INTEGER NOT NULL CHECK (n_distinct_intersections >= 0),
    PRIMARY KEY (receipt_id, line_code),
    CHECK (binary_n = positive_n + negative_n),
    CHECK (n_intervals = binary_n + ambiguous_n + unresolved_n)
);

CREATE TABLE IF NOT EXISTS depth_lithology_summaries (
    receipt_id          INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    depth_bin_from_m    REAL    NOT NULL CHECK (depth_bin_from_m >= 0),
    depth_bin_to_m      REAL    NOT NULL CHECK (depth_bin_to_m > depth_bin_from_m),
    rock_code_raw       TEXT    NOT NULL,            -- 'MISSING' when the logged rock code is blank
    binary_n            INTEGER NOT NULL CHECK (binary_n >= 0),
    positive_n          INTEGER NOT NULL CHECK (positive_n >= 0 AND positive_n <= binary_n),
    prevalence          REAL    CHECK (prevalence IS NULL OR prevalence BETWEEN 0 AND 1),
    PRIMARY KEY (receipt_id, depth_bin_from_m, rock_code_raw)
);

CREATE TABLE IF NOT EXISTS weathering_cross_tabs (
    receipt_id          INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    weathering_code     TEXT    NOT NULL,            -- 'MISSING' when blank
    label_state         TEXT    NOT NULL CHECK (label_state IN ('POSITIVE','NEGATIVE','AMBIGUOUS','UNRESOLVED')),
    n_intervals         INTEGER NOT NULL CHECK (n_intervals >= 0),
    PRIMARY KEY (receipt_id, weathering_code, label_state)
);

CREATE TABLE IF NOT EXISTS spatial_support_statistics (
    receipt_id          INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    stat_group          TEXT    NOT NULL,            -- COLLAR_NEAREST, COLLAR_PAIR, LINE, INTERVAL_SPACING
    stat_name           TEXT    NOT NULL,            -- n, min, p05, median, p95, max
    stat_value          REAL    NOT NULL,
    unit                TEXT    NOT NULL,
    n_basis             INTEGER NOT NULL CHECK (n_basis >= 0),
    PRIMARY KEY (receipt_id, stat_group, stat_name)
);

-- Declared directions and families for a receipt. Status records whether the direction may be analysed.
CREATE TABLE IF NOT EXISTS direction_registry (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    direction_id            TEXT    NOT NULL,
    family                  TEXT    NOT NULL CHECK (family IN ('LATERAL_BETWEEN','OMNI_BETWEEN','WITHIN_HOLE','HORIZONTAL_AZIMUTH')),
    azimuth_deg             REAL,                    -- clockwise from grid north; NULL for omnidirectional and downhole
    angular_tolerance_deg   REAL,
    geometry_basis          TEXT    NOT NULL,
    status                  TEXT    NOT NULL CHECK (status IN ('SUPPORTED','SKIPPED','NOT_SUPPORTED')),
    reason                  TEXT    NOT NULL,
    PRIMARY KEY (receipt_id, direction_id)
);

CREATE TABLE IF NOT EXISTS pair_sampling_diagnostics (
    receipt_id                INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    direction_id              TEXT    NOT NULL,
    lag_bin_index             INTEGER NOT NULL CHECK (lag_bin_index >= 0),
    lag_from_m                REAL    NOT NULL CHECK (lag_from_m >= 0),
    lag_to_m                  REAL    NOT NULL CHECK (lag_to_m > lag_from_m),
    n_pairs                   INTEGER NOT NULL CHECK (n_pairs >= 0),
    n_equal_class             INTEGER NOT NULL CHECK (n_equal_class >= 0),
    n_different_class         INTEGER NOT NULL CHECK (n_different_class >= 0),
    n_within_hole_pairs       INTEGER NOT NULL CHECK (n_within_hole_pairs >= 0),
    n_between_hole_pairs      INTEGER NOT NULL CHECK (n_between_hole_pairs >= 0),
    n_independent_hole_pairs  INTEGER NOT NULL CHECK (n_independent_hole_pairs >= 0),
    support_status            TEXT    NOT NULL CHECK (support_status IN ('SUPPORTED','SKIPPED')),
    PRIMARY KEY (receipt_id, direction_id, lag_bin_index),
    FOREIGN KEY (receipt_id, direction_id) REFERENCES direction_registry (receipt_id, direction_id),
    CHECK (n_equal_class + n_different_class = n_pairs),
    CHECK (n_within_hole_pairs + n_between_hole_pairs = n_pairs)
);

CREATE TABLE IF NOT EXISTS variogram_experiments (
    experiment_id           INTEGER PRIMARY KEY,
    run_id                  INTEGER NOT NULL REFERENCES stage_runs (run_id),
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    direction_id            TEXT    NOT NULL,
    variant                 TEXT    NOT NULL CHECK (variant IN ('BASE','SENSITIVITY')),
    lag_width_m             REAL    NOT NULL CHECK (lag_width_m > 0),
    lag_max_m               REAL    NOT NULL CHECK (lag_max_m > lag_width_m),
    angular_tolerance_deg   REAL,
    within_hole_pairs       TEXT    NOT NULL CHECK (within_hole_pairs IN ('EXCLUDED','INCLUDED','ONLY')),
    pair_weighting          TEXT    NOT NULL CHECK (pair_weighting IN ('EQUAL_PAIR','EQUAL_HOLE')),
    min_pairs_per_bin       INTEGER NOT NULL CHECK (min_pairs_per_bin >= 0),
    label_rule_id           TEXT    NOT NULL,
    config_version          TEXT    NOT NULL,
    status                  TEXT    NOT NULL CHECK (status IN ('COMPUTED','SKIPPED')),
    created_utc             TEXT    NOT NULL,
    FOREIGN KEY (receipt_id, direction_id) REFERENCES direction_registry (receipt_id, direction_id)
);

CREATE TABLE IF NOT EXISTS variogram_lag_bins (
    experiment_id               INTEGER NOT NULL REFERENCES variogram_experiments (experiment_id),
    bin_index                   INTEGER NOT NULL CHECK (bin_index >= 0),
    lag_from_m                  REAL    NOT NULL,
    lag_to_m                    REAL    NOT NULL CHECK (lag_to_m > lag_from_m),
    lag_centre_m                REAL    NOT NULL,
    n_pairs                     INTEGER NOT NULL CHECK (n_pairs >= 0),
    n_independent_hole_pairs    INTEGER NOT NULL CHECK (n_independent_hole_pairs >= 0),
    gamma                       REAL    CHECK (gamma IS NULL OR gamma >= 0),
    equal_class_fraction        REAL    CHECK (equal_class_fraction IS NULL OR equal_class_fraction BETWEEN 0 AND 1),
    supported                   INTEGER NOT NULL CHECK (supported IN (0,1)),
    PRIMARY KEY (experiment_id, bin_index),
    CHECK (supported = 0 OR (gamma IS NOT NULL AND n_pairs > 0))
);

CREATE TABLE IF NOT EXISTS variogram_fits (
    fit_id                  INTEGER PRIMARY KEY,
    experiment_id           INTEGER NOT NULL REFERENCES variogram_experiments (experiment_id),
    model                   TEXT    NOT NULL CHECK (model IN ('spherical','exponential')),
    fit_status              TEXT    NOT NULL CHECK (fit_status IN ('FITTED','NOT_IDENTIFIABLE','INADMISSIBLE')),
    weighting               TEXT    NOT NULL CHECK (weighting = 'CRESSIE_N_OVER_GAMMA2'),
    objective_value         REAL,
    n_bins_used             INTEGER NOT NULL CHECK (n_bins_used >= 0),
    admissible              INTEGER CHECK (admissible IS NULL OR admissible IN (0,1)),
    marginal_departure      REAL,                    -- (nugget + structured sill) / (p(1-p)) - 1
    stability_status        TEXT    NOT NULL CHECK (stability_status IN ('STABLE','UNSTABLE','NOT_ASSESSED')),
    reason                  TEXT    NOT NULL,
    created_utc             TEXT    NOT NULL,
    UNIQUE (experiment_id, model)
);

CREATE TABLE IF NOT EXISTS variogram_fit_parameters (
    fit_id              INTEGER NOT NULL REFERENCES variogram_fits (fit_id),
    parameter           TEXT    NOT NULL CHECK (parameter IN ('nugget','structured_sill','range_m')),
    estimate            REAL    NOT NULL,
    lower_bound         REAL    NOT NULL,
    upper_bound         REAL    NOT NULL,
    units               TEXT    NOT NULL CHECK (units IN ('indicator_variance','m')),
    leave_one_line_min  REAL,
    leave_one_line_max  REAL,
    PRIMARY KEY (fit_id, parameter),
    CHECK (estimate >= lower_bound AND estimate <= upper_bound)
);

CREATE TABLE IF NOT EXISTS anisotropy_diagnostics (
    anisotropy_id       INTEGER PRIMARY KEY,
    receipt_id          INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    direction_a         TEXT    NOT NULL,
    direction_b         TEXT    NOT NULL,
    range_a_m           REAL,
    range_b_m           REAL,
    range_ratio         REAL,
    support_status      TEXT    NOT NULL CHECK (support_status IN ('SUPPORTED','SKIPPED')),
    decision            TEXT    NOT NULL CHECK (decision IN ('ANISOTROPY_SUPPORTED','NOT_SUPPORTED','NOT_EVALUATED')),
    reason              TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sensitivity_runs (
    sensitivity_id      INTEGER PRIMARY KEY,
    run_id              INTEGER NOT NULL REFERENCES stage_runs (run_id),
    base_experiment_id  INTEGER REFERENCES variogram_experiments (experiment_id),
    variant_name        TEXT    NOT NULL,
    changed_factor      TEXT    NOT NULL,
    changed_value       TEXT    NOT NULL,
    status              TEXT    NOT NULL CHECK (status IN ('COMPLETED','SKIPPED')),
    reason              TEXT    NOT NULL,
    experiment_id       INTEGER REFERENCES variogram_experiments (experiment_id),
    fit_id              INTEGER REFERENCES variogram_fits (fit_id)
);

CREATE TABLE IF NOT EXISTS geological_section_registry (
    section_id              TEXT    PRIMARY KEY,
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    line_code               TEXT,
    section_azimuth_deg     REAL,
    projection_basis        TEXT    NOT NULL,
    vertical_basis          TEXT    NOT NULL CHECK (vertical_basis = 'RELATIVE_DEPTH'),
    observed_or_inferred    TEXT    NOT NULL CHECK (observed_or_inferred = 'OBSERVED_LOG_ONLY'),
    status                  TEXT    NOT NULL CHECK (status IN ('GENERATED','NOT_SUPPORTED')),
    reason                  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS continuity_handoff_decisions (
    handoff_id                          INTEGER PRIMARY KEY,
    receipt_id                          INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    fit_id                              INTEGER REFERENCES variogram_fits (fit_id),
    decision_status                     TEXT    NOT NULL CHECK (decision_status IN ('APPROVED','PROVISIONAL','REJECTED','NOT_IDENTIFIABLE')),
    candidate_family                    TEXT    NOT NULL,
    parameter_search_json               TEXT    NOT NULL,
    lag_setting_json                    TEXT    NOT NULL,
    full_data_parameters_for_test_folds INTEGER NOT NULL CHECK (full_data_parameters_for_test_folds = 0),
    rationale                           TEXT    NOT NULL,
    created_utc                         TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS figure_registry (
    figure_id       TEXT    PRIMARY KEY CHECK (figure_id LIKE 'O2-F%'),
    title           TEXT    NOT NULL,
    status          TEXT    NOT NULL CHECK (status IN ('GENERATED','NOT_SUPPORTED')),
    reason          TEXT    NOT NULL,
    caption         TEXT    NOT NULL,
    created_utc     TEXT
);

CREATE TABLE IF NOT EXISTS figure_query_registry (
    figure_id       TEXT    NOT NULL REFERENCES figure_registry (figure_id),
    query_name      TEXT    NOT NULL,
    sql_path        TEXT    NOT NULL,
    sql_sha256      TEXT    NOT NULL,
    params_json     TEXT    NOT NULL,
    row_count       INTEGER NOT NULL CHECK (row_count >= 0),
    PRIMARY KEY (figure_id, query_name)
);

CREATE TABLE IF NOT EXISTS table_registry (
    table_id        TEXT    PRIMARY KEY CHECK (table_id LIKE 'O2-T%'),
    title           TEXT    NOT NULL,
    status          TEXT    NOT NULL CHECK (status IN ('GENERATED','NOT_SUPPORTED')),
    sql_path        TEXT,
    row_count       INTEGER NOT NULL CHECK (row_count >= 0),
    reason          TEXT
);

CREATE TABLE IF NOT EXISTS table_query_registry (
    table_id        TEXT    NOT NULL REFERENCES table_registry (table_id),
    query_name      TEXT    NOT NULL,
    sql_path        TEXT    NOT NULL,
    sql_sha256      TEXT    NOT NULL,
    params_json     TEXT    NOT NULL,
    row_count       INTEGER NOT NULL CHECK (row_count >= 0),
    PRIMARY KEY (table_id, query_name)
);

CREATE TABLE IF NOT EXISTS export_manifests (
    artifact_path   TEXT    PRIMARY KEY,
    artifact_kind   TEXT    NOT NULL CHECK (artifact_kind IN ('FIGURE','TABLE','REPORT','DATA','MANIFEST')),
    artifact_sha256 TEXT    NOT NULL,
    receipt_id      INTEGER REFERENCES source_receipts (receipt_id),
    created_utc     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS gate_results (
    run_id          INTEGER NOT NULL REFERENCES stage_runs (run_id),
    gate_id         TEXT    NOT NULL,
    gate_name       TEXT    NOT NULL,
    status          TEXT    NOT NULL CHECK (status IN ('PASS','WARN','SKIP','STOP','DOWNGRADE')),
    scope           TEXT    NOT NULL,
    detail          TEXT    NOT NULL,
    created_utc     TEXT    NOT NULL,
    PRIMARY KEY (run_id, gate_id)
);

-- Configuration 5 (weathering front, fresh-rock variography). One front per hole: the shallowest interval whose weathering
-- code is in front_codes. front_z_relative_m is the relative depth of that interval's from-depth on the straight hole.
CREATE TABLE IF NOT EXISTS weathering_front_observations (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    hole_id                 TEXT    NOT NULL,
    line_code               TEXT    NOT NULL,
    easting_m               REAL    NOT NULL,
    northing_m              REAL    NOT NULL,
    front_depth_m           REAL    NOT NULL CHECK (front_depth_m >= 0),
    front_z_relative_m      REAL    NOT NULL CHECK (front_z_relative_m <= 0),
    n_reversal_intervals    INTEGER NOT NULL CHECK (n_reversal_intervals >= 0),
    config_version          TEXT    NOT NULL,
    PRIMARY KEY (receipt_id, hole_id, config_version)
);

-- Continuity diagnostics of the weathering front. stat_group: ALONG_LINE_ADJACENT, FRONT_SUMMARY,
-- INTERPOLATION_LEAVE_ONE_HOLE_OUT, INTERPOLATION_LEAVE_ONE_LINE_OUT. The interpolable flag is a decision row (0 or 1).
CREATE TABLE IF NOT EXISTS weathering_front_diagnostics (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    stat_group              TEXT    NOT NULL CHECK (stat_group IN ('ALONG_LINE_ADJACENT','FRONT_SUMMARY',
                                                                  'INTERPOLATION_LEAVE_ONE_HOLE_OUT',
                                                                  'INTERPOLATION_LEAVE_ONE_LINE_OUT')),
    stat_name               TEXT    NOT NULL,
    stat_value              REAL,
    unit                    TEXT    NOT NULL,
    n_basis                 INTEGER NOT NULL CHECK (n_basis >= 0),
    PRIMARY KEY (receipt_id, config_version, stat_group, stat_name)
);

-- Experimental semivariogram of the front between distinct holes (horizontal lag). gamma is withheld in unsupported bins.
CREATE TABLE IF NOT EXISTS weathering_front_variogram (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    bin_index               INTEGER NOT NULL CHECK (bin_index >= 0),
    lag_from_m              REAL    NOT NULL,
    lag_to_m                REAL    NOT NULL CHECK (lag_to_m > lag_from_m),
    n_hole_pairs            INTEGER NOT NULL CHECK (n_hole_pairs >= 0),
    gamma                   REAL    CHECK (gamma IS NULL OR gamma >= 0),
    supported               INTEGER NOT NULL CHECK (supported IN (0,1)),
    PRIMARY KEY (receipt_id, config_version, bin_index),
    CHECK (supported = 0 OR gamma IS NOT NULL)
);

-- Hole-bootstrap percentile band of the bin semivariance of one experiment. n_replicates counts the replicates in which
-- the bin had positive weight; the other replicates are skipped for that bin.
CREATE TABLE IF NOT EXISTS bootstrap_gamma_bands (
    experiment_id           INTEGER NOT NULL REFERENCES variogram_experiments (experiment_id),
    bin_index               INTEGER NOT NULL CHECK (bin_index >= 0),
    n_replicates            INTEGER NOT NULL CHECK (n_replicates >= 0),
    gamma_lower             REAL,
    gamma_upper             REAL,
    gamma_median            REAL,
    PRIMARY KEY (experiment_id, bin_index),
    CHECK (gamma_lower IS NULL OR gamma_upper IS NULL OR gamma_lower <= gamma_upper)
);

-- Configuration 6 (structural frame: apparent-dip search, circular down-hole null, LOLO dips, fits, between-line report).
-- frame_id RELATIVE is primary; DEM_ABSOLUTE is sensitivity only. No column name here contains the word absolute (G22).
CREATE TABLE IF NOT EXISTS structural_alignment_scores (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    sample_id               TEXT    NOT NULL CHECK (sample_id IN ('ALL_BINARY','FRESH')),
    frame_id                TEXT    NOT NULL CHECK (frame_id IN ('RELATIVE','DEM_ABSOLUTE')),
    dip_deg                 REAL    NOT NULL CHECK (dip_deg BETWEEN -90 AND 90),
    n_supported_bins        INTEGER NOT NULL CHECK (n_supported_bins >= 0),
    n_pairs                 INTEGER NOT NULL CHECK (n_pairs >= 0),
    alignment_score         REAL,
    is_selected             INTEGER NOT NULL CHECK (is_selected IN (0,1)),
    is_horizontal_control   INTEGER NOT NULL CHECK (is_horizontal_control IN (0,1)),
    PRIMARY KEY (receipt_id, config_version, sample_id, frame_id, dip_deg)
);

CREATE TABLE IF NOT EXISTS structural_null_summary (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    sample_id               TEXT    NOT NULL CHECK (sample_id IN ('ALL_BINARY','FRESH')),
    frame_id                TEXT    NOT NULL CHECK (frame_id IN ('RELATIVE','DEM_ABSOLUTE')),
    selected_dip_deg        REAL    NOT NULL,
    observed_max_alignment  REAL    NOT NULL,
    null_p95_max            REAL,
    n_permutations          INTEGER NOT NULL CHECK (n_permutations > 0),
    null_seed               INTEGER NOT NULL,
    n_null_valid            INTEGER NOT NULL CHECK (n_null_valid >= 0),
    p_value                 REAL    NOT NULL CHECK (p_value > 0 AND p_value <= 1),
    alpha                   REAL    NOT NULL,
    max_abs_ds_m            REAL    NOT NULL,
    lag_width_m             REAL    NOT NULL,
    lag_max_m               REAL    NOT NULL,
    bootstrap_replicates    INTEGER NOT NULL,
    bootstrap_seed          INTEGER NOT NULL,
    PRIMARY KEY (receipt_id, config_version, sample_id, frame_id)
);

CREATE TABLE IF NOT EXISTS structural_lolo_dips (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    sample_id               TEXT    NOT NULL,
    frame_id                TEXT    NOT NULL,
    excluded_line           TEXT    NOT NULL,
    full_dip_deg            REAL    NOT NULL,
    lolo_dip_deg            REAL,
    within_tolerance        INTEGER NOT NULL CHECK (within_tolerance IN (0,1)),
    PRIMARY KEY (receipt_id, config_version, sample_id, frame_id, excluded_line)
);

CREATE TABLE IF NOT EXISTS structural_variogram_bins (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    sample_id               TEXT    NOT NULL,
    frame_id                TEXT    NOT NULL,
    purpose                 TEXT    NOT NULL CHECK (purpose IN ('SELECTED','HORIZONTAL_CONTROL')),
    dip_deg                 REAL    NOT NULL,
    bin_index               INTEGER NOT NULL CHECK (bin_index >= 0),
    lag_from_m              REAL    NOT NULL,
    lag_to_m                REAL    NOT NULL CHECK (lag_to_m > lag_from_m),
    lag_centre_m            REAL    NOT NULL,
    n_pairs                 INTEGER NOT NULL CHECK (n_pairs >= 0),
    n_independent_hole_pairs INTEGER NOT NULL CHECK (n_independent_hole_pairs >= 0),
    gamma                   REAL    CHECK (gamma IS NULL OR gamma >= 0),
    supported               INTEGER NOT NULL CHECK (supported IN (0,1)),
    gamma_lower             REAL,
    gamma_upper             REAL,
    gamma_median            REAL,
    n_band_replicates       INTEGER NOT NULL CHECK (n_band_replicates >= 0),
    PRIMARY KEY (receipt_id, config_version, sample_id, frame_id, purpose, bin_index),
    CHECK (supported = 0 OR gamma IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS structural_fits (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    sample_id               TEXT    NOT NULL,
    frame_id                TEXT    NOT NULL,
    model                   TEXT    NOT NULL CHECK (model IN ('spherical','exponential')),
    selected_dip_deg        REAL    NOT NULL,
    fit_status              TEXT    NOT NULL CHECK (fit_status IN ('FITTED','NOT_IDENTIFIABLE','INADMISSIBLE')),
    reason                  TEXT    NOT NULL,
    nugget                  REAL,
    structured_sill         REAL,
    range_m                 REAL,
    n_bins_used             INTEGER NOT NULL CHECK (n_bins_used >= 0),
    objective_value         REAL,
    stability_status        TEXT    NOT NULL CHECK (stability_status IN ('STABLE','UNSTABLE','NOT_ASSESSED')),
    stability_reason        TEXT    NOT NULL,
    range_ratio_min         REAL,
    range_ratio_max         REAL,
    PRIMARY KEY (receipt_id, config_version, sample_id, frame_id, model),
    CHECK (fit_status = 'FITTED' OR (nugget IS NULL AND structured_sill IS NULL AND range_m IS NULL))
);

-- Between-line along-strike report (REPORT_ONLY): no fit, no decision, no handoff.
CREATE TABLE IF NOT EXISTS structural_between_line (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    sample_id               TEXT    NOT NULL,
    frame_id                TEXT    NOT NULL,
    selected_dip_deg        REAL    NOT NULL,
    lag_from_m              REAL    NOT NULL,
    lag_to_m                REAL    NOT NULL CHECK (lag_to_m > lag_from_m),
    n_pairs                 INTEGER NOT NULL CHECK (n_pairs >= 0),
    n_independent_hole_pairs INTEGER NOT NULL CHECK (n_independent_hole_pairs >= 0),
    n_different_class       INTEGER NOT NULL CHECK (n_different_class >= 0),
    gamma                   REAL    CHECK (gamma IS NULL OR gamma >= 0),
    supported               INTEGER NOT NULL CHECK (supported IN (0,1)),
    PRIMARY KEY (receipt_id, config_version, sample_id, frame_id, lag_from_m)
);

CREATE TABLE IF NOT EXISTS structural_decisions (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version          TEXT    NOT NULL,
    sample_id               TEXT    NOT NULL,
    frame_id                TEXT    NOT NULL CHECK (frame_id = 'RELATIVE'),
    decision                TEXT    NOT NULL CHECK (decision IN ('PROVISIONAL (structural frame)','NOT_IDENTIFIABLE (structural frame)')),
    p_value_below_alpha     INTEGER NOT NULL CHECK (p_value_below_alpha IN (0,1)),
    dip_stable              INTEGER NOT NULL CHECK (dip_stable IN (0,1)),
    lines_within_tolerance  INTEGER NOT NULL CHECK (lines_within_tolerance >= 0),
    stable_fitted_model     TEXT,
    range_stable            INTEGER NOT NULL CHECK (range_stable IN (0,1)),
    reason                  TEXT    NOT NULL,
    PRIMARY KEY (receipt_id, config_version, sample_id, frame_id)
);

-- Digest of the sorted pair identifiers of each dip and frame, and the within-hole counts (zero by construction in the
-- experiment; the candidates excluded are reported as a diagnostic).
CREATE TABLE IF NOT EXISTS structural_pair_digests (
    receipt_id                          INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    config_version                      TEXT    NOT NULL,
    sample_id                           TEXT    NOT NULL,
    frame_id                            TEXT    NOT NULL,
    dip_deg                             REAL    NOT NULL,
    n_pairs                             INTEGER NOT NULL CHECK (n_pairs >= 0),
    n_within_hole_pairs                 INTEGER NOT NULL CHECK (n_within_hole_pairs >= 0),
    n_within_hole_candidates_excluded   INTEGER NOT NULL CHECK (n_within_hole_candidates_excluded >= 0),
    pair_digest                         TEXT    NOT NULL,
    PRIMARY KEY (receipt_id, config_version, sample_id, frame_id, dip_deg)
);

-- Objective 5 schema: model-based uncertainty on a relative grid and the scenario simulation. O5-SCHEMA-2026.11.06-2.
-- Reads Objective 2, 3 and 4 databases read-only. Part 2 adds the sim_* tables (O5-T05, O5-T06, O5-F08..F10).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version_id   INTEGER PRIMARY KEY,
    schema_name  TEXT    NOT NULL,
    applied_utc  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS stage_runs (
    run_id          INTEGER PRIMARY KEY,
    run_kind        TEXT    NOT NULL,
    config_version  TEXT    NOT NULL,
    config_sha256   TEXT    NOT NULL,
    started_utc     TEXT    NOT NULL,
    finished_utc    TEXT,
    status          TEXT    NOT NULL CHECK (status IN ('RUNNING','COMPLETED','STOPPED','FAILED')),
    code_commit     TEXT,
    note            TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS input_files (
    role          TEXT    PRIMARY KEY,
    path          TEXT    NOT NULL,
    bytes         INTEGER NOT NULL CHECK (bytes >= 0),
    sha256        TEXT    NOT NULL,
    recorded_utc  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS source_receipts (
    receipt_id              INTEGER PRIMARY KEY,
    o3_path                 TEXT    NOT NULL,
    o3_receipt_id           INTEGER NOT NULL,
    label_rule_id           TEXT    NOT NULL CHECK (label_rule_id = 'DESIGN_8_2_v1'),
    geometry_status         TEXT    NOT NULL CHECK (geometry_status = 'PROVISIONAL_RELATIVE'),
    vertical_basis          TEXT    NOT NULL CHECK (vertical_basis = 'RELATIVE_TO_COLLAR'),
    crs_key                 TEXT    NOT NULL CHECK (crs_key = 'EPSG:32630'),
    config_version          TEXT    NOT NULL,
    config_sha256           TEXT    NOT NULL,
    n_intervals             INTEGER NOT NULL,
    n_binary                INTEGER NOT NULL,
    n_holes                 INTEGER NOT NULL,
    n_collars               INTEGER NOT NULL,
    prevalence              REAL    NOT NULL,
    imported_utc            TEXT    NOT NULL,
    code_commit             TEXT
);

-- All logged intervals of the receipt. in_binary_target = 1 is the DESIGN_8_2_v1 training set. Weathering codes are kept
-- for the observed weathering-front surface only.
CREATE TABLE IF NOT EXISTS observations (
    upstream_interval_id  INTEGER PRIMARY KEY,
    receipt_id            INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    hole_id               TEXT    NOT NULL,
    line_code             TEXT    NOT NULL,
    depth_from_m          REAL    NOT NULL,
    midpoint_m            REAL    NOT NULL,
    easting_m             REAL    NOT NULL,
    northing_m            REAL    NOT NULL,
    z_relative_m          REAL    NOT NULL,
    in_binary_target      INTEGER NOT NULL CHECK (in_binary_target IN (0,1)),
    indicator             INTEGER CHECK (indicator IS NULL OR indicator IN (0,1)),
    weathering_code       TEXT,
    label_state           TEXT
);

-- Collar coordinates from the thesis database (holes table, the Objective 3 dataset version).
CREATE TABLE IF NOT EXISTS collars (
    hole_id          TEXT    PRIMARY KEY,
    line_code        TEXT    NOT NULL,
    easting_m        REAL    NOT NULL,
    northing_m       REAL    NOT NULL,
    max_depth_m      REAL    NOT NULL,
    dataset_version_id INTEGER NOT NULL
);

-- Observed weathering front per hole, from the Objective 3 rule (weathering_front.hole_fronts).
CREATE TABLE IF NOT EXISTS hole_fronts (
    hole_id       TEXT PRIMARY KEY REFERENCES collars (hole_id),
    easting_m     REAL NOT NULL,
    northing_m    REAL NOT NULL,
    front_z_m     REAL NOT NULL
);

-- Locked handoffs read from the Objective 4 databases. match_status is MATCH or MISMATCH (a mismatch stops the run).
CREATE TABLE IF NOT EXISTS handoffs (
    tier                TEXT    PRIMARY KEY CHECK (tier IN ('TIER_1_EXTRAPOLATION','TIER_2_INTERPOLATION')),
    o4_path             TEXT    NOT NULL,
    o4_file_sha256      TEXT    NOT NULL,
    o4_locked_receipt_id INTEGER NOT NULL,
    o4_locked_receipt_sha256 TEXT NOT NULL,
    o4_config_version   TEXT    NOT NULL,
    split_plan_id       TEXT    NOT NULL,
    selected_model_id   TEXT    NOT NULL,
    selected_decision_id INTEGER NOT NULL,
    runner_up_model_id  TEXT    NOT NULL,
    runner_up_decision_id INTEGER NOT NULL,
    required_selected   TEXT    NOT NULL,
    required_runner_up  TEXT    NOT NULL,
    match_status        TEXT    NOT NULL CHECK (match_status IN ('MATCH','MISMATCH')),
    improvement_status  TEXT    NOT NULL,
    delta_brier         REAL,
    delta_brier_ci_low  REAL,
    delta_brier_ci_high REAL,
    selected_fold_consistency INTEGER,
    created_utc         TEXT    NOT NULL
);

-- Validated pooled scores carried from Objective 4 for the selected and runner-up models (not recomputed here).
CREATE TABLE IF NOT EXISTS carried_validation (
    tier         TEXT    NOT NULL REFERENCES handoffs (tier),
    role         TEXT    NOT NULL CHECK (role IN ('SELECTED','RUNNER_UP')),
    model_id     TEXT    NOT NULL,
    metric_id    TEXT    NOT NULL,
    weighting    TEXT    NOT NULL CHECK (weighting IN ('INTERVAL','EQUAL_HOLE')),
    value        REAL,
    status       TEXT    NOT NULL,
    n            INTEGER NOT NULL,
    n_positive   INTEGER NOT NULL,
    PRIMARY KEY (tier, role, metric_id, weighting)
);

-- Down-hole variogram check against inputs.downhole_variogram.expected_values.
CREATE TABLE IF NOT EXISTS downhole_variogram (
    check_id              INTEGER PRIMARY KEY CHECK (check_id = 1),
    o2_fit_id             INTEGER NOT NULL,
    o2_experiment_id      INTEGER NOT NULL,
    o2_config_version     TEXT    NOT NULL,
    model                 TEXT    NOT NULL,
    objective_value       REAL    NOT NULL,
    nugget                REAL    NOT NULL,
    structured_sill       REAL    NOT NULL,
    practical_range_m     REAL    NOT NULL,
    expected_model        TEXT    NOT NULL,
    expected_nugget       REAL    NOT NULL,
    expected_structured_sill REAL NOT NULL,
    expected_practical_range_m REAL NOT NULL,
    tolerance             REAL    NOT NULL,
    max_abs_difference    REAL    NOT NULL,
    status                TEXT    NOT NULL CHECK (status IN ('MATCH','MISMATCH'))
);

-- Final refits: one row per (tier, role). The fitted model lives in the artifact; the record holds what Objective 5 reports.
CREATE TABLE IF NOT EXISTS final_refits (
    refit_id                  INTEGER PRIMARY KEY,
    tier                      TEXT    NOT NULL REFERENCES handoffs (tier),
    role                      TEXT    NOT NULL CHECK (role IN ('SELECTED','RUNNER_UP')),
    model_id                  TEXT    NOT NULL,
    predictor_set             TEXT    NOT NULL,
    predictors_json           TEXT    NOT NULL,
    model_class               TEXT    NOT NULL,
    hyperparameters_json      TEXT    NOT NULL,
    inner_cv_score            REAL,
    inner_cv_score_sd         REAL,
    calibration_status        TEXT    NOT NULL,
    calibration_intercept     REAL,
    calibration_slope         REAL,
    calibration_n_inner       INTEGER,
    n_train                   INTEGER NOT NULL,
    n_positive                INTEGER NOT NULL,
    in_sample_brier           REAL    NOT NULL,
    in_sample_auc             REAL,
    o3_split_plan_id          TEXT    NOT NULL,
    o3_folds_selected         INTEGER NOT NULL,
    o3_most_frequent_json     TEXT,
    o3_most_frequent_count    INTEGER,
    o3_modes_tied             INTEGER,
    full_data_matches_o3_mode INTEGER NOT NULL CHECK (full_data_matches_o3_mode IN (0,1)),
    artifact_path             TEXT    NOT NULL,
    artifact_sha256           TEXT    NOT NULL,
    status                    TEXT    NOT NULL CHECK (status IN ('RUN','FAILED')),
    created_utc               TEXT    NOT NULL,
    UNIQUE (tier, role)
);

CREATE TABLE IF NOT EXISTS grid_layers (
    iz               INTEGER PRIMARY KEY,
    z_relative_m     REAL    NOT NULL,
    depth_below_collar_m REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS grid_meta (
    meta_key    TEXT PRIMARY KEY,
    meta_value  TEXT NOT NULL
);

-- One row per grid cell (centre). Probability columns are NULL for NO_SUPPORT cells.
CREATE TABLE IF NOT EXISTS grid_cells (
    cell_id                       INTEGER PRIMARY KEY,
    ix                            INTEGER NOT NULL,
    iy                            INTEGER NOT NULL,
    iz                            INTEGER NOT NULL REFERENCES grid_layers (iz),
    centre_easting_m              REAL    NOT NULL,
    centre_northing_m             REAL    NOT NULL,
    z_relative_m                  REAL    NOT NULL,
    depth_below_collar_m          REAL    NOT NULL,
    depth_band_top_m              INTEGER NOT NULL,
    nearest_collar_m              REAL    NOT NULL,
    zone                          TEXT    NOT NULL CHECK (zone IN ('INTERPOLATION','EXTRAPOLATION','NO_SUPPORT')),
    model_tier                    TEXT,
    selected_model_id             TEXT,
    runner_up_model_id            TEXT,
    deepest_sampled_z_m           REAL    NOT NULL,
    depth_support                 TEXT    NOT NULL CHECK (depth_support IN ('SUPPORTED','DEPTH_EXTRAPOLATED')),
    depth_below_weathering_front_m REAL   NOT NULL,
    above_weathering_front        INTEGER NOT NULL CHECK (above_weathering_front IN (0,1)),
    p_selected                    REAL,
    p_runner_up                   REAL,
    entropy_bits                  REAL,
    disagreement                  REAL,
    p_lo                          REAL,
    p_hi                          REAL,
    interval_width                REAL,
    bootstrap_successes           INTEGER,
    class_label                   TEXT,
    class_at_prevalence           TEXT,
    UNIQUE (ix, iy, iz)
);

CREATE INDEX IF NOT EXISTS ix_grid_zone ON grid_cells (zone);
CREATE INDEX IF NOT EXISTS ix_grid_iz ON grid_cells (iz);
CREATE INDEX IF NOT EXISTS ix_grid_iy ON grid_cells (iy);

CREATE TABLE IF NOT EXISTS bootstrap_replicates (
    zone               TEXT    NOT NULL,
    replicate_index    INTEGER NOT NULL CHECK (replicate_index >= 1),
    model_id           TEXT    NOT NULL,
    status             TEXT    NOT NULL CHECK (status IN ('SUCCESS','FAILED')),
    reason             TEXT    NOT NULL,
    n_unique_holes     INTEGER NOT NULL,
    n_rows             INTEGER NOT NULL,
    PRIMARY KEY (zone, replicate_index)
);

CREATE TABLE IF NOT EXISTS bootstrap_summary (
    zone               TEXT    PRIMARY KEY,
    model_id           TEXT    NOT NULL,
    n_replicates       INTEGER NOT NULL,
    n_success          INTEGER NOT NULL,
    success_fraction   REAL    NOT NULL,
    seed               INTEGER NOT NULL,
    runtime_s          REAL    NOT NULL,
    status             TEXT    NOT NULL CHECK (status IN ('PASS','STOP'))
);

CREATE TABLE IF NOT EXISTS classification_rules (
    rule_id                 TEXT PRIMARY KEY,
    decision_threshold      REAL NOT NULL,
    prevalence_threshold    REAL NOT NULL,
    disagreement_limit      REAL NOT NULL,
    statement               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS figure_registry (
    figure_id   TEXT    PRIMARY KEY CHECK (figure_id LIKE 'O5-F%'),
    title       TEXT    NOT NULL,
    status      TEXT    NOT NULL CHECK (status IN ('GENERATED','NOT_SUPPORTED')),
    reason      TEXT    NOT NULL,
    caption     TEXT    NOT NULL,
    created_utc TEXT
);

CREATE TABLE IF NOT EXISTS figure_sql_registry (
    figure_id   TEXT    NOT NULL REFERENCES figure_registry (figure_id),
    query_name  TEXT    NOT NULL,
    sql_path    TEXT    NOT NULL,
    sql_sha256  TEXT    NOT NULL,
    params_json TEXT    NOT NULL,
    row_count   INTEGER NOT NULL CHECK (row_count >= 0),
    PRIMARY KEY (figure_id, query_name)
);

CREATE TABLE IF NOT EXISTS table_registry (
    table_id    TEXT    PRIMARY KEY CHECK (table_id LIKE 'O5-T%'),
    title       TEXT    NOT NULL,
    status      TEXT    NOT NULL CHECK (status IN ('GENERATED','NOT_SUPPORTED')),
    row_count   INTEGER NOT NULL CHECK (row_count >= 0),
    reason      TEXT    NOT NULL,
    created_utc TEXT
);

CREATE TABLE IF NOT EXISTS table_sql_registry (
    table_id    TEXT    NOT NULL REFERENCES table_registry (table_id),
    query_name  TEXT    NOT NULL,
    sql_path    TEXT    NOT NULL,
    sql_sha256  TEXT    NOT NULL,
    params_json TEXT    NOT NULL,
    row_count   INTEGER NOT NULL CHECK (row_count >= 0),
    PRIMARY KEY (table_id, query_name)
);

CREATE TABLE IF NOT EXISTS export_manifests (
    manifest_id   INTEGER PRIMARY KEY,
    artifact_path TEXT    NOT NULL UNIQUE,
    artifact_kind TEXT    NOT NULL,
    artifact_id   TEXT    NOT NULL,
    sha256        TEXT    NOT NULL,
    bytes         INTEGER NOT NULL CHECK (bytes >= 0),
    created_utc   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS gate_results (
    run_id      INTEGER NOT NULL REFERENCES stage_runs (run_id),
    gate_id     TEXT    NOT NULL,
    gate_name   TEXT    NOT NULL,
    status      TEXT    NOT NULL CHECK (status IN ('PASS','WARN','STOP')),
    scope       TEXT    NOT NULL,
    detail      TEXT    NOT NULL,
    created_utc TEXT    NOT NULL,
    PRIMARY KEY (run_id, gate_id)
);

-- ---------------------------------------------------------------------------------------------------------------------
-- Part 2: scenario simulation (sequential indicator simulation with a locally varying mean). Scenario analysis only:
-- the lateral range of each scenario is assumed. One row per scenario; INFEASIBLE scenarios are recorded, not run.
CREATE TABLE IF NOT EXISTS sim_scenarios (
    scenario_id                 TEXT    PRIMARY KEY,
    scenario_index              INTEGER NOT NULL,
    horizontal_range_m          REAL    NOT NULL,
    feasibility                 TEXT    NOT NULL CHECK (feasibility IN ('FEASIBLE','INFEASIBLE')),
    vertical_bracket            REAL    NOT NULL,
    vertical_range_m            REAL,
    expected_vertical_range_m   REAL    NOT NULL,
    downhole_practical_range_m  REAL    NOT NULL,
    dip_deg                     REAL    NOT NULL,
    n_domain_nodes              INTEGER NOT NULL,
    n_data                      INTEGER NOT NULL,
    n_realisations              INTEGER,
    seed                        INTEGER NOT NULL,
    max_conditioning            INTEGER NOT NULL,
    max_simulated               INTEGER NOT NULL,
    search_radius               REAL    NOT NULL,
    jitter_fraction             REAL    NOT NULL,
    expected_volume_m3          REAL    NOT NULL,
    volume_p10_m3               REAL,
    volume_p50_m3               REAL,
    volume_p90_m3               REAL,
    components_p10              REAL,
    components_p50              REAL,
    components_p90              REAL,
    largest_share_p10           REAL,
    largest_share_p50           REAL,
    largest_share_p90           REAL,
    mean_local_mean             REAL,
    mean_frequency              REAL,
    mean_frequency_diff         REAL,
    frequency_status            TEXT,
    sk_fallbacks                INTEGER,
    sk_neighbourless_nodes      INTEGER,
    exact_neighbour_searches       INTEGER,
    downhole_max_abs_diff       REAL,
    downhole_mean_abs_diff      REAL,
    runtime_s                   REAL,
    status                      TEXT    NOT NULL CHECK (status IN ('COMPLETED','INFEASIBLE_NOT_RUN')),
    config_version              TEXT    NOT NULL,
    created_utc                 TEXT    NOT NULL
);

-- One row per realisation of a feasible scenario.
CREATE TABLE IF NOT EXISTS sim_realisations (
    scenario_id                 TEXT    NOT NULL REFERENCES sim_scenarios (scenario_id),
    realisation                 INTEGER NOT NULL CHECK (realisation >= 1),
    n_positive                  INTEGER NOT NULL CHECK (n_positive >= 0),
    volume_m3                   REAL    NOT NULL,
    n_components                INTEGER NOT NULL CHECK (n_components >= 0),
    largest_volume_m3           REAL    NOT NULL,
    largest_share               REAL,
    sk_fallbacks                INTEGER NOT NULL,
    sk_neighbourless_nodes      INTEGER NOT NULL,
    exact_neighbour_searches       INTEGER NOT NULL,
    PRIMARY KEY (scenario_id, realisation)
);

-- Per-cell frequency of positive outcomes over the realisations, and the local mean of the cell.
CREATE TABLE IF NOT EXISTS sim_cell_frequency (
    scenario_id                 TEXT    NOT NULL REFERENCES sim_scenarios (scenario_id),
    cell_id                     INTEGER NOT NULL REFERENCES grid_cells (cell_id),
    n_positive                  INTEGER NOT NULL,
    frequency                   REAL    NOT NULL,
    local_mean                  REAL    NOT NULL,
    PRIMARY KEY (scenario_id, cell_id)
);

-- Two full realisations per scenario (indicator values per simulation node).
CREATE TABLE IF NOT EXISTS sim_cell_realisation (
    scenario_id                 TEXT    NOT NULL REFERENCES sim_scenarios (scenario_id),
    realisation                 INTEGER NOT NULL CHECK (realisation IN (1,2)),
    cell_id                     INTEGER NOT NULL REFERENCES grid_cells (cell_id),
    value                       INTEGER NOT NULL CHECK (value IN (0,1)),
    PRIMARY KEY (scenario_id, realisation, cell_id)
);

-- Down-hole indicator semivariogram per Objective 2 lag bin: data and the realisations sampled at the nearest node.
CREATE TABLE IF NOT EXISTS sim_downhole_variogram (
    scenario_id                 TEXT    NOT NULL REFERENCES sim_scenarios (scenario_id),
    bin_index                   INTEGER NOT NULL,
    lag_centre_m                REAL    NOT NULL,
    n_pairs                     INTEGER NOT NULL,
    n_hole_pairs                INTEGER NOT NULL,
    supported                   INTEGER NOT NULL CHECK (supported IN (0,1)),
    n_realisations_sampled      INTEGER NOT NULL,
    data_gamma                  REAL,
    data_o2_gamma               REAL,
    sim_gamma_mean              REAL,
    sim_gamma_min               REAL,
    sim_gamma_max               REAL,
    PRIMARY KEY (scenario_id, bin_index)
);

-- Binary intervals with their local mean (final tier-2 refit) and the nearest simulation node.
CREATE TABLE IF NOT EXISTS sim_datum (
    upstream_interval_id        INTEGER PRIMARY KEY,
    hole_id                     TEXT    NOT NULL,
    easting_m                   REAL    NOT NULL,
    northing_m                  REAL    NOT NULL,
    z_relative_m                REAL    NOT NULL,
    indicator                   INTEGER NOT NULL CHECK (indicator IN (0,1)),
    local_mean                  REAL    NOT NULL,
    nearest_node_cell_id        INTEGER NOT NULL REFERENCES grid_cells (cell_id),
    nearest_node_distance_m     REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS sim_run_meta (
    meta_key                    TEXT    PRIMARY KEY,
    meta_value                  TEXT    NOT NULL
);

-- Objective 3 schema: indicator geostatistics, machine learning and hybrid occurrence models.
-- O3-SCHEMA-2026.11.05-1. Objective 3 reads Objective 1 and Objective 2 read-only and writes only this database.
-- Cross-database foreign keys cannot be enforced by SQLite; receipts and gates carry the cross-file checks.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version_id   INTEGER PRIMARY KEY,
    schema_name  TEXT    NOT NULL,
    applied_utc  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS source_receipts (
    receipt_id                      INTEGER PRIMARY KEY,
    upstream_logical_name           TEXT    NOT NULL,
    upstream_path                   TEXT    NOT NULL,
    upstream_dataset_version_id     INTEGER NOT NULL,
    upstream_dataset_version_key    TEXT    NOT NULL,
    upstream_etl_version            TEXT    NOT NULL,
    label_rule_id                   TEXT    NOT NULL,
    label_rule_status               TEXT    NOT NULL CHECK (label_rule_status = 'APPROVED'),
    label_rule_definition_sha256    TEXT    NOT NULL,
    geometry_build_id               INTEGER NOT NULL,
    geometry_status                 TEXT    NOT NULL CHECK (geometry_status = 'PROVISIONAL_RELATIVE'),
    crs_key                         TEXT    NOT NULL,
    crs_datum_status                TEXT    NOT NULL CHECK (crs_datum_status = 'VERIFIED'),
    coordinate_pair_status          TEXT    NOT NULL CHECK (coordinate_pair_status = 'APPROVED'),
    drill_line_status               TEXT    NOT NULL CHECK (drill_line_status = 'APPROVED'),
    vertical_basis                  TEXT    NOT NULL CHECK (vertical_basis = 'RELATIVE_TO_COLLAR'),
    o2_logical_name                 TEXT    NOT NULL,
    o2_path                         TEXT    NOT NULL,
    o2_receipt_id                   INTEGER NOT NULL,
    o2_content_sha256               TEXT    NOT NULL,
    o2_handoff_id                   INTEGER NOT NULL,
    o2_handoff_status               TEXT    NOT NULL,
    o2_candidate_family             TEXT    NOT NULL,
    content_sha256                  TEXT    NOT NULL,
    row_count                       INTEGER NOT NULL CHECK (row_count >= 0),
    ordered_id_digest               TEXT    NOT NULL,
    selection_query_sha256          TEXT    NOT NULL,
    imported_utc                    TEXT    NOT NULL,
    code_commit                     TEXT
);

CREATE TABLE IF NOT EXISTS stage_runs (
    run_id          INTEGER PRIMARY KEY,
    run_kind        TEXT    NOT NULL,
    config_version  TEXT    NOT NULL,
    config_sha256   TEXT    NOT NULL,
    receipt_id      INTEGER REFERENCES source_receipts (receipt_id),
    split_plan_id   TEXT,
    started_utc     TEXT    NOT NULL,
    finished_utc    TEXT,
    status          TEXT    NOT NULL CHECK (status IN ('RUNNING','COMPLETED','STOPPED','FAILED')),
    code_commit     TEXT,
    note            TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_observations (
    receipt_id              INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    upstream_interval_id    INTEGER NOT NULL,
    upstream_interval_key   TEXT    NOT NULL,
    hole_id                 TEXT    NOT NULL,
    line_code               TEXT    NOT NULL,
    depth_from_m            REAL    NOT NULL,
    depth_to_m              REAL    NOT NULL,
    support_length_m        REAL    NOT NULL CHECK (support_length_m > 0),
    midpoint_m              REAL    NOT NULL,
    easting_m               REAL    NOT NULL,
    northing_m              REAL    NOT NULL,
    z_relative_m            REAL    NOT NULL,
    label_state             TEXT    NOT NULL CHECK (label_state IN ('POSITIVE','NEGATIVE','AMBIGUOUS','UNRESOLVED')),
    in_binary_target        INTEGER NOT NULL CHECK (in_binary_target IN (0,1)),
    indicator               INTEGER CHECK (indicator IS NULL OR indicator IN (0,1)),
    geometry_status         TEXT    NOT NULL,
    rock_code_raw           TEXT,
    rock_code_status        TEXT,
    weathering_code         TEXT,
    PRIMARY KEY (receipt_id, upstream_interval_id),
    CHECK ((in_binary_target = 1 AND indicator IS NOT NULL) OR (in_binary_target = 0 AND indicator IS NULL))
);

CREATE TABLE IF NOT EXISTS target_registries (
    target_id              TEXT    PRIMARY KEY,
    receipt_id             INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    label_rule_id          TEXT    NOT NULL,
    label_rule_status      TEXT    NOT NULL CHECK (label_rule_status = 'APPROVED'),
    positive_state         TEXT    NOT NULL CHECK (positive_state = 'POSITIVE'),
    negative_state         TEXT    NOT NULL CHECK (negative_state = 'NEGATIVE'),
    excluded_states_json   TEXT    NOT NULL,
    binary_n               INTEGER NOT NULL CHECK (binary_n >= 0),
    positive_n             INTEGER NOT NULL CHECK (positive_n >= 0),
    negative_n             INTEGER NOT NULL CHECK (negative_n >= 0),
    ambiguous_n            INTEGER NOT NULL CHECK (ambiguous_n >= 0),
    unresolved_n           INTEGER NOT NULL CHECK (unresolved_n >= 0),
    created_utc            TEXT    NOT NULL,
    UNIQUE (receipt_id, label_rule_id)
);

CREATE TABLE IF NOT EXISTS label_versions (
    label_version_id       TEXT    PRIMARY KEY,
    receipt_id             INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    rule_id                TEXT    NOT NULL,
    rule_status            TEXT    NOT NULL CHECK (rule_status = 'APPROVED'),
    definition_sha256      TEXT    NOT NULL,
    positive_state         TEXT    NOT NULL,
    negative_state         TEXT    NOT NULL,
    excluded_states_json   TEXT    NOT NULL,
    binary_n               INTEGER NOT NULL,
    positive_n             INTEGER NOT NULL,
    negative_n             INTEGER NOT NULL,
    ambiguous_n            INTEGER NOT NULL,
    unresolved_n           INTEGER NOT NULL,
    frozen_utc             TEXT    NOT NULL,
    UNIQUE (receipt_id, rule_id)
);

CREATE TABLE IF NOT EXISTS geometry_versions (
    geometry_version_id    TEXT    PRIMARY KEY,
    receipt_id             INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    geometry_build_id      INTEGER NOT NULL,
    geometry_status        TEXT    NOT NULL CHECK (geometry_status = 'PROVISIONAL_RELATIVE'),
    crs_key                TEXT    NOT NULL,
    datum_status           TEXT    NOT NULL CHECK (datum_status = 'VERIFIED'),
    vertical_basis         TEXT    NOT NULL CHECK (vertical_basis = 'RELATIVE_TO_COLLAR'),
    z_absolute_used        INTEGER NOT NULL CHECK (z_absolute_used = 0),
    created_utc            TEXT    NOT NULL,
    UNIQUE (receipt_id, geometry_build_id)
);

CREATE TABLE IF NOT EXISTS feature_registry (
    feature_id              TEXT    PRIMARY KEY,
    name                    TEXT    NOT NULL UNIQUE,
    source_table            TEXT    NOT NULL,
    units                   TEXT,
    data_type               TEXT    NOT NULL,
    available_at_prediction INTEGER NOT NULL CHECK (available_at_prediction IN (0,1)),
    availability_basis      TEXT    NOT NULL,
    leakage_designation     TEXT    NOT NULL CHECK (leakage_designation IN
                                                        ('SAFE','FORBIDDEN','TARGET_DERIVED','LOG_ONLY','IDENTIFIER')),
    rationale               TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS spatial_split_plans (
    split_plan_id  TEXT    PRIMARY KEY,
    receipt_id     INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    method         TEXT    NOT NULL CHECK (method IN ('LEAVE_ONE_DRILL_LINE_OUT','GROUP_K_FOLD_BY_HOLE')),
    n_folds        INTEGER NOT NULL CHECK (n_folds >= 2),
    primary_plan   INTEGER NOT NULL CHECK (primary_plan IN (0,1)),
    seed           INTEGER NOT NULL,
    frozen_utc     TEXT    NOT NULL,
    plan_sha256    TEXT    NOT NULL,
    notes          TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS split_membership (
    split_plan_id  TEXT    NOT NULL REFERENCES spatial_split_plans (split_plan_id),
    fold_id        INTEGER NOT NULL CHECK (fold_id >= 1),
    observation_id INTEGER NOT NULL,
    hole_id        TEXT    NOT NULL,
    line_code      TEXT    NOT NULL,
    role           TEXT    NOT NULL CHECK (role IN ('TRAIN','TEST')),
    PRIMARY KEY (split_plan_id, fold_id, observation_id)
);

CREATE INDEX IF NOT EXISTS idx_split_membership_role
    ON split_membership (split_plan_id, fold_id, role, observation_id);

CREATE TABLE IF NOT EXISTS split_audit (
    split_plan_id              TEXT    NOT NULL REFERENCES spatial_split_plans (split_plan_id),
    fold_id                    INTEGER NOT NULL,
    n_train                    INTEGER NOT NULL CHECK (n_train >= 0),
    n_test                     INTEGER NOT NULL CHECK (n_test >= 0),
    train_positive             INTEGER NOT NULL CHECK (train_positive >= 0),
    test_positive              INTEGER NOT NULL CHECK (test_positive >= 0),
    train_holes                INTEGER NOT NULL CHECK (train_holes >= 0),
    test_holes                 INTEGER NOT NULL CHECK (test_holes >= 0),
    train_lines                INTEGER NOT NULL CHECK (train_lines >= 0),
    test_lines                 INTEGER NOT NULL CHECK (test_lines >= 0),
    disjoint                   INTEGER NOT NULL CHECK (disjoint IN (0,1)),
    both_classes_train         INTEGER NOT NULL CHECK (both_classes_train IN (0,1)),
    both_classes_test          INTEGER NOT NULL CHECK (both_classes_test IN (0,1)),
    min_train_test_collar_distance_m REAL,
    status                     TEXT    NOT NULL CHECK (status IN ('PASS','WARN','STOP')),
    reason                     TEXT    NOT NULL,
    PRIMARY KEY (split_plan_id, fold_id)
);

CREATE TABLE IF NOT EXISTS model_families (
    family_id     TEXT    PRIMARY KEY,
    name          TEXT    NOT NULL,
    model_class   TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('BASELINE','M1','M2','M3')),
    estimand      TEXT    NOT NULL,
    description   TEXT    NOT NULL,
    leakage_note  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS training_runs (
    training_run_id       INTEGER PRIMARY KEY,
    run_id                INTEGER NOT NULL REFERENCES stage_runs (run_id),
    receipt_id            INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    split_plan_id         TEXT    NOT NULL REFERENCES spatial_split_plans (split_plan_id),
    fold_id               INTEGER NOT NULL CHECK (fold_id >= 1),
    family_id             TEXT    NOT NULL REFERENCES model_families (family_id),
    candidate_run_id      TEXT    NOT NULL,
    model_class           TEXT    NOT NULL,
    hyperparameters_json  TEXT    NOT NULL,
    inner_cv_method       TEXT    NOT NULL,
    inner_cv_folds        INTEGER NOT NULL CHECK (inner_cv_folds >= 0),
    selection_metric      TEXT    NOT NULL,
    inner_cv_score        REAL,
    inner_cv_score_sd     REAL,
    training_n            INTEGER NOT NULL CHECK (training_n >= 0),
    training_positive     INTEGER NOT NULL CHECK (training_positive >= 0),
    training_negative     INTEGER NOT NULL CHECK (training_negative >= 0),
    training_holes        INTEGER NOT NULL CHECK (training_holes >= 0),
    training_lines        INTEGER NOT NULL CHECK (training_lines >= 0),
    test_n                INTEGER NOT NULL CHECK (test_n >= 0),
    test_positive         INTEGER NOT NULL CHECK (test_positive >= 0),
    test_negative         INTEGER NOT NULL CHECK (test_negative >= 0),
    selected              INTEGER NOT NULL DEFAULT 0 CHECK (selected IN (0,1)),
    threshold             REAL    NOT NULL CHECK (threshold BETWEEN 0 AND 1),
    threshold_source      TEXT    NOT NULL,
    status                TEXT    NOT NULL CHECK (status IN ('COMPLETED','NOT_ESTIMABLE','FAILED','FALLBACK')),
    reason                TEXT    NOT NULL,
    seed                  INTEGER NOT NULL,
    created_utc           TEXT    NOT NULL,
    UNIQUE (split_plan_id, fold_id, candidate_run_id)
);

CREATE INDEX IF NOT EXISTS idx_training_runs_fold ON training_runs (split_plan_id, fold_id, family_id);

CREATE TABLE IF NOT EXISTS hyperparameter_trials (
    trial_id               INTEGER PRIMARY KEY,
    training_run_id        INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    candidate_run_id       TEXT    NOT NULL,
    hyperparameters_json   TEXT    NOT NULL,
    inner_cv_score         REAL,
    inner_cv_score_sd      REAL,
    inner_fold_scores_json TEXT    NOT NULL,
    rank                   INTEGER,
    selected               INTEGER NOT NULL CHECK (selected IN (0,1)),
    status                 TEXT    NOT NULL CHECK (status IN ('COMPLETED','FAILED','SKIPPED')),
    reason                 TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS training_sample_manifest (
    training_run_id  INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    observation_id   INTEGER NOT NULL,
    hole_id          TEXT    NOT NULL,
    line_code        TEXT    NOT NULL,
    true_label       INTEGER NOT NULL CHECK (true_label IN (0,1)),
    role             TEXT    NOT NULL CHECK (role IN ('TRAIN','INNER_TRAIN','INNER_TEST')),
    PRIMARY KEY (training_run_id, observation_id, role)
);

CREATE TABLE IF NOT EXISTS variogram_training_fits (
    variogram_fit_id  INTEGER PRIMARY KEY,
    training_run_id   INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    fold_id           INTEGER NOT NULL,
    family_id         TEXT    NOT NULL,
    direction_id      TEXT    NOT NULL CHECK (direction_id = 'LATERAL_BETWEEN'),
    model             TEXT    NOT NULL CHECK (model IN ('spherical','exponential')),
    fit_status        TEXT    NOT NULL CHECK (fit_status IN ('FITTED','NOT_IDENTIFIABLE','INADMISSIBLE')),
    objective_value   REAL,
    n_bins_used       INTEGER NOT NULL CHECK (n_bins_used >= 0),
    admissible        INTEGER CHECK (admissible IS NULL OR admissible IN (0,1)),
    marginal_variance REAL    NOT NULL CHECK (marginal_variance >= 0),
    nugget            REAL,
    structured_sill   REAL,
    range_m           REAL,
    stability_status  TEXT    NOT NULL CHECK (stability_status IN ('STABLE','UNSTABLE','NOT_ASSESSED')),
    stable            INTEGER NOT NULL CHECK (stable IN (0,1)),
    reason            TEXT    NOT NULL,
    created_utc       TEXT    NOT NULL,
    UNIQUE (training_run_id, model),
    CHECK (fit_status = 'FITTED' OR (nugget IS NULL AND structured_sill IS NULL AND range_m IS NULL)),
    CHECK (fit_status <> 'FITTED' OR (nugget IS NOT NULL AND structured_sill IS NOT NULL AND range_m IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS training_lag_bins (
    training_run_id  INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    family_id        TEXT    NOT NULL,
    bin_index        INTEGER NOT NULL CHECK (bin_index >= 0),
    lag_from_m       REAL    NOT NULL CHECK (lag_from_m >= 0),
    lag_to_m         REAL    NOT NULL CHECK (lag_to_m > lag_from_m),
    lag_centre_m     REAL    NOT NULL,
    n_pairs          INTEGER NOT NULL CHECK (n_pairs >= 0),
    n_independent_hole_pairs INTEGER NOT NULL CHECK (n_independent_hole_pairs >= 0),
    gamma            REAL    CHECK (gamma IS NULL OR gamma >= 0),
    supported        INTEGER NOT NULL CHECK (supported IN (0,1)),
    PRIMARY KEY (training_run_id, bin_index),
    CHECK (supported = 0 OR (gamma IS NOT NULL AND n_pairs > 0))
);

CREATE TABLE IF NOT EXISTS hybrid_residual_variogram (
    hybrid_variogram_id INTEGER PRIMARY KEY,
    training_run_id     INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    fold_id             INTEGER NOT NULL,
    model               TEXT    NOT NULL CHECK (model IN ('spherical','exponential')),
    fit_status          TEXT    NOT NULL CHECK (fit_status IN ('FITTED','NOT_IDENTIFIABLE','INADMISSIBLE')),
    objective_value     REAL,
    n_bins_used         INTEGER NOT NULL CHECK (n_bins_used >= 0),
    admissible          INTEGER CHECK (admissible IS NULL OR admissible IN (0,1)),
    residual_variance   REAL    NOT NULL CHECK (residual_variance >= 0),
    nugget              REAL,
    structured_sill     REAL,
    range_m             REAL,
    stability_status    TEXT    NOT NULL CHECK (stability_status IN ('STABLE','UNSTABLE','NOT_ASSESSED')),
    supported           INTEGER NOT NULL CHECK (supported IN (0,1)),
    fallback_status     TEXT    NOT NULL CHECK (fallback_status IN ('HYBRID_USED','FALLBACK_ML_ONLY','NOT_ESTIMABLE')),
    reason              TEXT    NOT NULL,
    created_utc         TEXT    NOT NULL,
    UNIQUE (training_run_id, model)
);

CREATE TABLE IF NOT EXISTS calibration_fits (
    calibration_id   INTEGER PRIMARY KEY,
    training_run_id  INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    method           TEXT    NOT NULL CHECK (method IN ('PLATT','NONE')),
    n_inner          INTEGER NOT NULL CHECK (n_inner >= 0),
    inner_positive   INTEGER NOT NULL CHECK (inner_positive >= 0),
    inner_negative   INTEGER NOT NULL CHECK (inner_negative >= 0),
    intercept        REAL,
    slope            REAL,
    clip_epsilon     REAL    NOT NULL CHECK (clip_epsilon > 0),
    status           TEXT    NOT NULL CHECK (status IN ('FITTED','SKIPPED','FAILED')),
    reason           TEXT    NOT NULL,
    created_utc      TEXT    NOT NULL,
    UNIQUE (training_run_id)
);

CREATE TABLE IF NOT EXISTS model_artifacts (
    artifact_id       INTEGER PRIMARY KEY,
    training_run_id   INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    artifact_path     TEXT    NOT NULL UNIQUE,
    artifact_sha256   TEXT    NOT NULL,
    artifact_kind     TEXT    NOT NULL,
    bytes             INTEGER NOT NULL CHECK (bytes >= 0),
    created_utc       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions_oof (
    prediction_id       INTEGER PRIMARY KEY,
    training_run_id     INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    split_plan_id       TEXT    NOT NULL REFERENCES spatial_split_plans (split_plan_id),
    fold_id             INTEGER NOT NULL,
    observation_id      INTEGER NOT NULL,
    hole_id             TEXT    NOT NULL,
    line_code           TEXT    NOT NULL,
    family_id           TEXT    NOT NULL,
    candidate_run_id    TEXT    NOT NULL,
    true_label          INTEGER NOT NULL CHECK (true_label IN (0,1)),
    p_raw               REAL    NOT NULL CHECK (p_raw BETWEEN 0 AND 1),
    p_calibrated        REAL    NOT NULL CHECK (p_calibrated BETWEEN 0 AND 1),
    clipped_raw         INTEGER NOT NULL CHECK (clipped_raw IN (0,1)),
    clipped_calibrated  INTEGER NOT NULL CHECK (clipped_calibrated IN (0,1)),
    predicted_class     INTEGER NOT NULL CHECK (predicted_class IN (0,1)),
    threshold           REAL    NOT NULL CHECK (threshold BETWEEN 0 AND 1),
    threshold_source    TEXT    NOT NULL,
    geometry_status     TEXT    NOT NULL,
    label_rule_id       TEXT    NOT NULL,
    created_utc         TEXT    NOT NULL,
    UNIQUE (training_run_id, observation_id)
);

CREATE INDEX IF NOT EXISTS idx_predictions_fold ON predictions_oof (split_plan_id, fold_id, family_id);
CREATE INDEX IF NOT EXISTS idx_predictions_obs ON predictions_oof (observation_id);

CREATE TABLE IF NOT EXISTS prediction_failures (
    failure_id        INTEGER PRIMARY KEY,
    split_plan_id     TEXT    NOT NULL REFERENCES spatial_split_plans (split_plan_id),
    fold_id           INTEGER NOT NULL,
    observation_id    INTEGER NOT NULL,
    family_id         TEXT    NOT NULL,
    candidate_run_id  TEXT    NOT NULL,
    training_run_id   INTEGER REFERENCES training_runs (training_run_id),
    reason            TEXT    NOT NULL,
    created_utc       TEXT    NOT NULL,
    UNIQUE (split_plan_id, fold_id, observation_id, candidate_run_id)
);

CREATE TABLE IF NOT EXISTS residual_diagnostics (
    residual_id        INTEGER PRIMARY KEY,
    training_run_id    INTEGER NOT NULL REFERENCES training_runs (training_run_id),
    observation_id     INTEGER NOT NULL,
    role               TEXT    NOT NULL CHECK (role IN ('INNER_OOF','TEST')),
    fold_id            INTEGER NOT NULL,
    trend_probability  REAL    NOT NULL CHECK (trend_probability BETWEEN 0 AND 1),
    residual           REAL    NOT NULL CHECK (residual BETWEEN -1 AND 1),
    created_utc        TEXT    NOT NULL,
    UNIQUE (training_run_id, observation_id, role)
);

CREATE TABLE IF NOT EXISTS leakage_audit_log (
    audit_id     INTEGER PRIMARY KEY,
    run_id       INTEGER NOT NULL REFERENCES stage_runs (run_id),
    check_name   TEXT    NOT NULL,
    status       TEXT    NOT NULL CHECK (status IN ('PASS','WARN','FAIL')),
    detail       TEXT    NOT NULL,
    created_utc  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS final_refits (
    final_refit_id          INTEGER PRIMARY KEY,
    family_id               TEXT    NOT NULL REFERENCES model_families (family_id),
    candidate_run_id        TEXT    NOT NULL,
    selection_decision_id   TEXT,
    status                  TEXT    NOT NULL CHECK (status IN ('PENDING_O4','RUN','FAILED')),
    artifact_path           TEXT,
    artifact_sha256         TEXT,
    reason                  TEXT    NOT NULL,
    created_utc             TEXT    NOT NULL,
    UNIQUE (family_id, candidate_run_id)
);

CREATE TABLE IF NOT EXISTS figure_registry (
    figure_id   TEXT    PRIMARY KEY CHECK (figure_id LIKE 'O3-F%'),
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
    table_id    TEXT    PRIMARY KEY CHECK (table_id LIKE 'O3-T%'),
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
    status      TEXT    NOT NULL CHECK (status IN ('PASS','WARN','SKIP','STOP','DOWNGRADE')),
    scope       TEXT    NOT NULL,
    detail      TEXT    NOT NULL,
    created_utc TEXT    NOT NULL,
    PRIMARY KEY (run_id, gate_id)
);

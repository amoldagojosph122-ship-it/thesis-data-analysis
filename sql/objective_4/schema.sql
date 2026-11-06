-- Objective 4 schema: independent spatial validation and probability-based performance.
-- O4-SCHEMA-2026.11.05-1. Objective 4 reads Objective 1, 2 and 3 read-only and writes only this database.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version_id   INTEGER PRIMARY KEY,
    schema_name  TEXT    NOT NULL,
    applied_utc  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS source_receipts (
    receipt_id                      INTEGER PRIMARY KEY,
    o3_logical_name                 TEXT    NOT NULL,
    o3_path                         TEXT    NOT NULL,
    o3_receipt_id                   INTEGER NOT NULL,
    o3_config_version               TEXT    NOT NULL,
    o3_code_version                 TEXT    NOT NULL,
    o3_split_plan_id                TEXT    NOT NULL,
    o3_split_plan_sha256            TEXT    NOT NULL,
    o3_prediction_snapshot_sha256   TEXT    NOT NULL,
    o3_observation_count            INTEGER NOT NULL CHECK (o3_observation_count >= 0),
    o3_prediction_count             INTEGER NOT NULL CHECK (o3_prediction_count >= 0),
    o3_failure_count                INTEGER NOT NULL CHECK (o3_failure_count >= 0),
    o1_label_rule_id                TEXT    NOT NULL,
    o1_label_rule_status            TEXT    NOT NULL CHECK (o1_label_rule_status = 'APPROVED'),
    o1_label_rule_definition_sha256 TEXT    NOT NULL,
    o1_content_sha256               TEXT    NOT NULL,
    o1_dataset_version_key          TEXT    NOT NULL,
    o2_content_sha256               TEXT    NOT NULL,
    o2_handoff_status               TEXT    NOT NULL,
    target_id                       TEXT    NOT NULL,
    geometry_version_id             TEXT    NOT NULL,
    geometry_status                 TEXT    NOT NULL CHECK (geometry_status = 'PROVISIONAL_RELATIVE'),
    crs_key                         TEXT    NOT NULL,
    crs_datum_status                TEXT    NOT NULL CHECK (crs_datum_status = 'VERIFIED'),
    vertical_basis                  TEXT    NOT NULL CHECK (vertical_basis = 'RELATIVE_TO_COLLAR'),
    imported_utc                    TEXT    NOT NULL,
    code_commit                     TEXT
);

CREATE TABLE IF NOT EXISTS stage_runs (
    run_id          INTEGER PRIMARY KEY,
    run_kind        TEXT    NOT NULL,
    config_version  TEXT    NOT NULL,
    config_sha256   TEXT    NOT NULL,
    receipt_id      INTEGER REFERENCES source_receipts (receipt_id),
    started_utc     TEXT    NOT NULL,
    finished_utc    TEXT,
    status          TEXT    NOT NULL CHECK (status IN ('RUNNING','COMPLETED','STOPPED','FAILED')),
    code_commit     TEXT,
    note            TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_registry (
    model_id              TEXT    PRIMARY KEY,
    family_id             TEXT    NOT NULL,
    role                  TEXT    NOT NULL CHECK (role IN ('BASELINE','M1','M2','M3')),
    description           TEXT    NOT NULL,
    coverage_status       TEXT    NOT NULL CHECK (coverage_status IN ('FULL','PARTIAL','NONE','FALLBACK_IDENTICAL')),
    comparable            INTEGER NOT NULL CHECK (comparable IN (0,1)),
    fallback_identical_to TEXT,
    note                  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_population (
    receipt_id                          INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    observation_id                      INTEGER NOT NULL,
    fold_id                             INTEGER NOT NULL CHECK (fold_id >= 1),
    line_code                           TEXT    NOT NULL,
    hole_id                             TEXT    NOT NULL,
    true_label                          INTEGER NOT NULL CHECK (true_label IN (0,1)),
    easting_m                           REAL    NOT NULL,
    northing_m                          REAL    NOT NULL,
    z_relative_m                        REAL    NOT NULL,
    depth_from_m                        REAL    NOT NULL,
    weight_interval                     REAL    NOT NULL CHECK (weight_interval > 0),
    weight_equal_hole                   REAL    NOT NULL CHECK (weight_equal_hole > 0),
    min_distance_to_training_interval_m REAL,
    outside_training_northing_envelope  INTEGER NOT NULL CHECK (outside_training_northing_envelope IN (0,1)),
    extrapolation_status                TEXT    NOT NULL,
    in_common_cohort                    INTEGER NOT NULL CHECK (in_common_cohort IN (0,1)),
    PRIMARY KEY (receipt_id, observation_id)
);

CREATE TABLE IF NOT EXISTS prediction_snapshot (
    snapshot_id           INTEGER PRIMARY KEY,
    receipt_id            INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    source_training_run_id INTEGER NOT NULL,
    model_id              TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    observation_id        INTEGER NOT NULL,
    fold_id               INTEGER NOT NULL,
    line_code             TEXT    NOT NULL,
    hole_id               TEXT    NOT NULL,
    true_label            INTEGER NOT NULL CHECK (true_label IN (0,1)),
    p_raw                 REAL    NOT NULL CHECK (p_raw BETWEEN 0 AND 1),
    p_calibrated          REAL    NOT NULL CHECK (p_calibrated BETWEEN 0 AND 1),
    selected_probability  REAL    NOT NULL CHECK (selected_probability BETWEEN 0 AND 1),
    clipped               INTEGER NOT NULL CHECK (clipped IN (0,1)),
    threshold             REAL    NOT NULL CHECK (threshold BETWEEN 0 AND 1),
    predicted_class       INTEGER NOT NULL CHECK (predicted_class IN (0,1)),
    UNIQUE (model_id, observation_id),
    FOREIGN KEY (receipt_id, observation_id) REFERENCES evaluation_population (receipt_id, observation_id)
);

CREATE TABLE IF NOT EXISTS prediction_coverage (
    model_id       TEXT    PRIMARY KEY REFERENCES candidate_registry (model_id),
    n_expected     INTEGER NOT NULL CHECK (n_expected >= 0),
    n_predicted    INTEGER NOT NULL CHECK (n_predicted >= 0),
    n_failed       INTEGER NOT NULL CHECK (n_failed >= 0),
    coverage       REAL    NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    status         TEXT    NOT NULL CHECK (status IN ('FULL','PARTIAL','NONE','FALLBACK_IDENTICAL')),
    reason         TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_plan (
    plan_id               TEXT    PRIMARY KEY,
    primary_endpoint      TEXT    NOT NULL CHECK (primary_endpoint = 'BRIER'),
    primary_weighting     TEXT    NOT NULL CHECK (primary_weighting = 'INTERVAL'),
    secondary_weighting   TEXT    NOT NULL CHECK (secondary_weighting = 'EQUAL_HOLE'),
    unit_of_analysis      TEXT    NOT NULL,
    cohort_definition     TEXT    NOT NULL,
    calibration_policy    TEXT    NOT NULL,
    bootstrap_design      TEXT    NOT NULL,
    decision_policy_json  TEXT    NOT NULL,
    frozen_utc            TEXT    NOT NULL,
    plan_sha256           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_definitions (
    metric_id          TEXT    PRIMARY KEY,
    name               TEXT    NOT NULL,
    definition         TEXT    NOT NULL,
    direction          TEXT    NOT NULL CHECK (direction IN ('LOWER_IS_BETTER','HIGHER_IS_BETTER','DIAGNOSTIC')),
    status_vocabulary  TEXT    NOT NULL,
    notes              TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS fold_metrics (
    model_id      TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    fold_id       INTEGER NOT NULL CHECK (fold_id >= 1),
    weighting     TEXT    NOT NULL CHECK (weighting IN ('INTERVAL','EQUAL_HOLE')),
    metric_id     TEXT    NOT NULL REFERENCES metric_definitions (metric_id),
    value         REAL,
    status        TEXT    NOT NULL CHECK (status IN ('DEFINED','UNDEFINED','NOT_ESTIMABLE')),
    n             INTEGER NOT NULL CHECK (n >= 0),
    n_positive    INTEGER NOT NULL CHECK (n_positive >= 0),
    reason        TEXT    NOT NULL,
    PRIMARY KEY (model_id, fold_id, weighting, metric_id)
);

CREATE TABLE IF NOT EXISTS pooled_metrics (
    model_id      TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    weighting     TEXT    NOT NULL CHECK (weighting IN ('INTERVAL','EQUAL_HOLE')),
    metric_id     TEXT    NOT NULL REFERENCES metric_definitions (metric_id),
    value         REAL,
    status        TEXT    NOT NULL CHECK (status IN ('DEFINED','UNDEFINED','NOT_ESTIMABLE')),
    n             INTEGER NOT NULL CHECK (n >= 0),
    n_positive    INTEGER NOT NULL CHECK (n_positive >= 0),
    reason        TEXT    NOT NULL,
    PRIMARY KEY (model_id, weighting, metric_id)
);

CREATE TABLE IF NOT EXISTS class_confusion_matrices (
    model_id             TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    scope                TEXT    NOT NULL CHECK (scope IN ('POOLED','FOLD')),
    fold_id              INTEGER NOT NULL DEFAULT 0,
    threshold            REAL    CHECK (threshold IS NULL OR threshold BETWEEN 0 AND 1),
    threshold_source     TEXT    NOT NULL,
    tp                   INTEGER NOT NULL CHECK (tp >= 0),
    fp                   INTEGER NOT NULL CHECK (fp >= 0),
    tn                   INTEGER NOT NULL CHECK (tn >= 0),
    fn                   INTEGER NOT NULL CHECK (fn >= 0),
    precision            REAL,
    recall               REAL,
    specificity          REAL,
    balanced_accuracy    REAL,
    f1                   REAL,
    mcc                  REAL,
    status               TEXT    NOT NULL CHECK (status IN ('DEFINED','UNDEFINED')),
    reason               TEXT    NOT NULL,
    PRIMARY KEY (model_id, scope, fold_id)
);

CREATE TABLE IF NOT EXISTS calibration_bins (
    model_id       TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    bin_index      INTEGER NOT NULL CHECK (bin_index >= 0),
    bin_lower      REAL    NOT NULL CHECK (bin_lower BETWEEN 0 AND 1),
    bin_upper      REAL    NOT NULL CHECK (bin_upper BETWEEN 0 AND 1),
    n              INTEGER NOT NULL CHECK (n >= 0),
    mean_p         REAL,
    observed_rate  REAL,
    wilson_low     REAL,
    wilson_high    REAL,
    merged         INTEGER NOT NULL CHECK (merged IN (0,1)),
    PRIMARY KEY (model_id, bin_index),
    CHECK (bin_upper >= bin_lower)
);

CREATE TABLE IF NOT EXISTS calibration_diagnostics (
    model_id    TEXT    PRIMARY KEY REFERENCES candidate_registry (model_id),
    n           INTEGER NOT NULL CHECK (n >= 0),
    intercept   REAL,
    slope       REAL,
    status      TEXT    NOT NULL CHECK (status IN ('DEFINED','UNDEFINED','NOT_ESTIMABLE')),
    reason      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS spatial_error_summaries (
    model_id       TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    line_code      TEXT    NOT NULL,
    depth_bin_from_m REAL  NOT NULL,
    depth_bin_to_m REAL    NOT NULL,
    error_type     TEXT    NOT NULL CHECK (error_type IN ('TP','FP','TN','FN')),
    n              INTEGER NOT NULL CHECK (n >= 0),
    mean_residual  REAL,
    PRIMARY KEY (model_id, line_code, depth_bin_from_m, depth_bin_to_m, error_type)
);

CREATE TABLE IF NOT EXISTS paired_differences (
    pair_id        TEXT    NOT NULL,
    model_a        TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    model_b        TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    scope          TEXT    NOT NULL CHECK (scope IN ('POOLED','FOLD','LINE')),
    fold_id        INTEGER NOT NULL DEFAULT 0,
    line_code      TEXT    NOT NULL DEFAULT '',
    weighting      TEXT    NOT NULL CHECK (weighting IN ('INTERVAL','EQUAL_HOLE')),
    delta_brier    REAL,
    delta_log_loss REAL,
    delta_roc_auc  REAL,
    delta_pr_auc   REAL,
    ci_low         REAL,
    ci_high        REAL,
    ci_low_line    REAL,
    ci_high_line   REAL,
    ci_design      TEXT,
    n              INTEGER NOT NULL CHECK (n >= 0),
    status         TEXT    NOT NULL CHECK (status IN ('DEFINED','UNDEFINED','NOT_ESTIMABLE')),
    reason         TEXT    NOT NULL,
    PRIMARY KEY (pair_id, scope, fold_id, line_code, weighting)
);

CREATE TABLE IF NOT EXISTS resampling_designs (
    design_id     TEXT    PRIMARY KEY,
    method        TEXT    NOT NULL CHECK (method IN ('HOLE_CLUSTER','LINE_CLUSTER')),
    unit          TEXT    NOT NULL,
    n_units       INTEGER NOT NULL CHECK (n_units >= 1),
    n_replicates  INTEGER NOT NULL CHECK (n_replicates >= 1),
    seed          INTEGER NOT NULL,
    notes         TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS bootstrap_replicates (
    bootstrap_id            INTEGER PRIMARY KEY,
    design_id               TEXT    NOT NULL REFERENCES resampling_designs (design_id),
    pair_id                 TEXT    NOT NULL,
    replicate_index         INTEGER NOT NULL CHECK (replicate_index >= 1),
    model_a                 TEXT    NOT NULL,
    model_b                 TEXT    NOT NULL,
    delta_brier_interval    REAL    NOT NULL,
    delta_brier_equal_hole  REAL    NOT NULL,
    delta_log_loss_interval REAL    NOT NULL,
    n_obs                   INTEGER NOT NULL CHECK (n_obs >= 0),
    UNIQUE (design_id, pair_id, replicate_index)
);

CREATE TABLE IF NOT EXISTS comparison_decisions (
    decision_id          INTEGER PRIMARY KEY,
    model_id             TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    role                 TEXT    NOT NULL CHECK (role IN ('SELECTED','COMPARATOR','REJECTED','NOT_COMPARABLE')),
    rank                 INTEGER,
    improvement_status   TEXT    NOT NULL CHECK (improvement_status IN
                                                     ('SUPPORTED_IMPROVEMENT','INCONCLUSIVE','NO_IMPROVEMENT',
                                                      'NOT_COMPARABLE')),
    selection_basis      TEXT    NOT NULL,
    delta_brier          REAL,
    ci_low               REAL,
    ci_high              REAL,
    fold_consistency     INTEGER CHECK (fold_consistency IS NULL OR fold_consistency BETWEEN 0 AND 5),
    calibration_status   TEXT    NOT NULL,
    discrimination_status TEXT   NOT NULL,
    coverage             REAL    NOT NULL CHECK (coverage BETWEEN 0 AND 1),
    reason               TEXT    NOT NULL,
    UNIQUE (model_id)
);

CREATE TABLE IF NOT EXISTS locked_handoff_receipts (
    receipt_id           INTEGER PRIMARY KEY,
    selected_model_id    TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    decision_id          INTEGER NOT NULL REFERENCES comparison_decisions (decision_id),
    target_receipt_id    INTEGER NOT NULL REFERENCES source_receipts (receipt_id),
    split_plan_id        TEXT    NOT NULL,
    split_plan_sha256    TEXT    NOT NULL,
    metric_reference     TEXT    NOT NULL,
    calibration_policy   TEXT    NOT NULL,
    allowed_domain       TEXT    NOT NULL,
    caveats              TEXT    NOT NULL,
    created_utc          TEXT    NOT NULL,
    receipt_sha256       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluation_audit_log (
    audit_id      INTEGER PRIMARY KEY,
    run_id        INTEGER NOT NULL REFERENCES stage_runs (run_id),
    check_name    TEXT    NOT NULL,
    status        TEXT    NOT NULL CHECK (status IN ('PASS','WARN','FAIL')),
    detail        TEXT    NOT NULL,
    created_utc   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_curve_points (
    model_id    TEXT    NOT NULL REFERENCES candidate_registry (model_id),
    curve       TEXT    NOT NULL CHECK (curve IN ('ROC','PR')),
    point_index INTEGER NOT NULL CHECK (point_index >= 0),
    threshold   REAL,
    tpr         REAL,
    fpr         REAL,
    precision   REAL,
    recall      REAL,
    n           INTEGER NOT NULL CHECK (n >= 0),
    PRIMARY KEY (model_id, curve, point_index)
);

CREATE TABLE IF NOT EXISTS figure_registry (
    figure_id   TEXT    PRIMARY KEY CHECK (figure_id LIKE 'O4-F%'),
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
    table_id    TEXT    PRIMARY KEY CHECK (table_id LIKE 'O4-T%'),
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

CREATE VIEW IF NOT EXISTS v_common_cohort AS
SELECT p.*
FROM evaluation_population p
WHERE p.in_common_cohort = 1;

CREATE VIEW IF NOT EXISTS v_prediction_coverage_summary AS
SELECT c.model_id, c.n_expected, c.n_predicted, c.n_failed, c.coverage, c.status, c.reason,
       r.comparable, r.fallback_identical_to
FROM prediction_coverage c JOIN candidate_registry r ON r.model_id = c.model_id;

CREATE VIEW IF NOT EXISTS v_pooled_metrics_primary AS
SELECT m.model_id, m.metric_id, m.value, m.status, m.n, m.n_positive, m.reason
FROM pooled_metrics m
WHERE m.weighting = 'INTERVAL';

CREATE VIEW IF NOT EXISTS v_fold_metrics_primary AS
SELECT m.model_id, m.fold_id, m.metric_id, m.value, m.status, m.n, m.n_positive, m.reason
FROM fold_metrics m
WHERE m.weighting = 'INTERVAL';

CREATE VIEW IF NOT EXISTS v_selected_model AS
SELECT d.decision_id, d.model_id, d.role, d.improvement_status, d.selection_basis, d.delta_brier, d.ci_low, d.ci_high,
       d.fold_consistency, d.calibration_status, d.discrimination_status, d.coverage, d.reason
FROM comparison_decisions d
WHERE d.role = 'SELECTED';

CREATE VIEW IF NOT EXISTS v_coverage_by_line AS
SELECT p.model_id, e.line_code, COUNT(*) AS n_predicted, SUM(p.predicted_class) AS n_predicted_positive
FROM prediction_snapshot p JOIN evaluation_population e
  ON e.receipt_id = p.receipt_id AND e.observation_id = p.observation_id
WHERE e.in_common_cohort = 1
GROUP BY p.model_id, e.line_code;

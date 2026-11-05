-- 0007_future_contracts.sql
-- Future-stage contracts (Stage B and Objectives 2-5). These tables exist only so that the schema
-- contract is explicit. They are EMPTY in obj1_master and every INSERT is rejected by a trigger.
-- Populated outputs belong to database/kambale_obj2_spatial.sqlite ... kambale_obj5_uncertainty.sqlite.

CREATE TABLE spatial_folds (
    fold_id                 INTEGER PRIMARY KEY,
    split_plan_id           TEXT    NOT NULL,
    fold_label              TEXT    NOT NULL,
    held_out_group          TEXT    NOT NULL,
    role                    TEXT    NOT NULL CHECK (role IN ('OUTER_TEST', 'TRAIN'))
);

CREATE TABLE variogram_runs (
    variogram_run_id        INTEGER PRIMARY KEY,
    scope                   TEXT    NOT NULL CHECK (scope IN ('EXPLORATORY_ALL_HOLES', 'TRAINING_ONLY')),
    status                  TEXT    NOT NULL CHECK (status IN ('DEFERRED', 'PROVISIONAL', 'APPROVED', 'REJECTED', 'NOT_IDENTIFIABLE'))
);

CREATE TABLE variogram_points (
    variogram_point_id      INTEGER PRIMARY KEY,
    variogram_run_id        INTEGER NOT NULL REFERENCES variogram_runs (variogram_run_id),
    lag_m                   REAL    NOT NULL,
    gamma                   REAL    NOT NULL,
    pair_count              INTEGER NOT NULL
);

CREATE TABLE model_runs (
    model_run_id            INTEGER PRIMARY KEY,
    model_family            TEXT    NOT NULL CHECK (model_family IN ('M1_INDICATOR_KRIGING', 'M2_ML', 'M3_HYBRID', 'BASELINE')),
    fold_id                 INTEGER REFERENCES spatial_folds (fold_id),
    status                  TEXT    NOT NULL CHECK (status IN ('DEFERRED', 'NOT_ESTIMABLE', 'FAILED', 'COMPLETED'))
);

CREATE TABLE model_predictions (
    prediction_id           INTEGER PRIMARY KEY,
    model_run_id            INTEGER NOT NULL REFERENCES model_runs (model_run_id),
    interval_key            TEXT    NOT NULL,
    p_raw                   REAL    CHECK (p_raw IS NULL OR (p_raw >= 0 AND p_raw <= 1)),
    p_calibrated            REAL    CHECK (p_calibrated IS NULL OR (p_calibrated >= 0 AND p_calibrated <= 1))
);

CREATE TABLE model_evaluation_metrics (
    metric_id               INTEGER PRIMARY KEY,
    model_run_id            INTEGER NOT NULL REFERENCES model_runs (model_run_id),
    metric_name             TEXT    NOT NULL,
    metric_value            REAL,
    metric_status           TEXT    NOT NULL CHECK (metric_status IN ('DEFERRED', 'UNDEFINED', 'COMPUTED'))
);

CREATE TABLE probability_calibration (
    calibration_id          INTEGER PRIMARY KEY,
    model_run_id            INTEGER NOT NULL REFERENCES model_runs (model_run_id),
    method                  TEXT    NOT NULL,
    fitted_on               TEXT    NOT NULL CHECK (fitted_on IN ('TRAINING_ONLY', 'INNER_HELD_OUT'))
);

CREATE TABLE uncertainty_voxels (
    voxel_id                INTEGER PRIMARY KEY,
    grid_version            TEXT    NOT NULL,
    x_m                     REAL    NOT NULL,
    y_m                     REAL    NOT NULL,
    z_relative_m            REAL    NOT NULL,
    probability             REAL    CHECK (probability IS NULL OR (probability >= 0 AND probability <= 1))
);

CREATE TABLE simulation_runs (
    simulation_run_id       INTEGER PRIMARY KEY,
    method                  TEXT    NOT NULL,
    n_realizations          INTEGER NOT NULL CHECK (n_realizations > 0),
    status                  TEXT    NOT NULL CHECK (status IN ('DEFERRED', 'SIS_NOT_SUPPORTED', 'COMPLETED'))
);

CREATE TRIGGER future_spatial_folds_blocked BEFORE INSERT ON spatial_folds
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;
CREATE TRIGGER future_variogram_runs_blocked BEFORE INSERT ON variogram_runs
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;
CREATE TRIGGER future_variogram_points_blocked BEFORE INSERT ON variogram_points
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;
CREATE TRIGGER future_model_runs_blocked BEFORE INSERT ON model_runs
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;
CREATE TRIGGER future_model_predictions_blocked BEFORE INSERT ON model_predictions
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;
CREATE TRIGGER future_model_metrics_blocked BEFORE INSERT ON model_evaluation_metrics
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;
CREATE TRIGGER future_calibration_blocked BEFORE INSERT ON probability_calibration
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;
CREATE TRIGGER future_uncertainty_voxels_blocked BEFORE INSERT ON uncertainty_voxels
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;
CREATE TRIGGER future_simulation_runs_blocked BEFORE INSERT ON simulation_runs
BEGIN SELECT RAISE(ABORT, 'Stage B contract table: not populated in obj1_master'); END;

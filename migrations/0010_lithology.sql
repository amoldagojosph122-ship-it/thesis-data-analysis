-- 0010_lithology.sql
-- Descriptive lithology refinement, scoped to a dataset version. A refined code describes the rock.
-- It never replaces the logged rock code, and no label rule reads these tables, so graphitic labels are unchanged.
-- The rules are versioned in src/kambale/lithology.py (LITHOLOGY_CONVENTION_VERSION and convention_sha256).

CREATE TABLE lithology_refinements (
    dataset_version_id   INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    interval_id          INTEGER NOT NULL REFERENCES logging_intervals (interval_id),
    interval_key         TEXT    NOT NULL,
    label_code           TEXT,                                -- logged rock_type1, unchanged; NULL when blank
    refinement_status    TEXT    NOT NULL CHECK (refinement_status IN (
        'UNCHANGED', 'UNCHANGED_NO_COMMENT', 'REFINED', 'REFINED_GENERAL', 'CONFLICT_REVIEW',
        'NOT_REFINED_VEIN', 'REVIEW_MULTIPLE_MODIFIERS', 'UNRESOLVED_UNSUPPORTED_CODE', 'UNRESOLVED_MISSING_CODE')),
    refined_code         TEXT,                                -- descriptive code; NULL when the rock code is blank
    base_code            TEXT,                                -- legend code the refinement starts from; NULL when unresolved
    comment_as_logged    TEXT    NOT NULL,                    -- empty string when the comment cell is empty
    comment_normalised   TEXT    NOT NULL,
    comment_lithology    TEXT    NOT NULL,                    -- legend code the comment names; empty when none
    matrix_minerals      TEXT    NOT NULL,
    reason               TEXT    NOT NULL,
    notes                TEXT    NOT NULL,
    convention_version   TEXT    NOT NULL,
    convention_sha256    TEXT    NOT NULL,
    PRIMARY KEY (dataset_version_id, interval_id)
);

CREATE TABLE lithology_dictionary (
    dataset_version_id    INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    refined_code          TEXT    NOT NULL,                   -- (none) for intervals with a blank rock code
    base_codes            TEXT    NOT NULL,
    refined_description   TEXT    NOT NULL,                   -- legend description of the refined code, when it is a legend code
    base_description      TEXT    NOT NULL,
    matrix_minerals_named TEXT    NOT NULL,
    basis                 TEXT    NOT NULL CHECK (basis IN ('confirmed', 'review', 'unresolved')),
    intervals             INTEGER NOT NULL,
    PRIMARY KEY (dataset_version_id, refined_code)
);

CREATE VIEW v_lithology_refinement AS
SELECT r.interval_key, i.hole_id, i.depth_from_m, i.depth_to_m, r.label_code, r.refinement_status,
       r.refined_code, r.base_code, r.comment_as_logged, r.comment_normalised, r.comment_lithology,
       r.matrix_minerals, r.reason, r.notes, r.convention_version
FROM lithology_refinements r
JOIN logging_intervals i ON i.interval_id = r.interval_id
WHERE r.dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

CREATE VIEW v_lithology_change_log AS
SELECT COALESCE(label_code, '(blank)') AS original_code, comment_as_logged, comment_normalised,
       comment_lithology, matrix_minerals, refinement_status, refined_code, COUNT(*) AS intervals
FROM v_lithology_refinement
GROUP BY COALESCE(label_code, '(blank)'), comment_as_logged, comment_normalised, comment_lithology,
         matrix_minerals, refinement_status, refined_code;

CREATE VIEW v_lithology_dictionary AS
SELECT refined_code, base_codes, refined_description, base_description, matrix_minerals_named, basis, intervals
FROM lithology_dictionary
WHERE dataset_version_id = (SELECT dataset_version_id FROM v_active_version);

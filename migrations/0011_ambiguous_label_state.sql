-- 0011_ambiguous_label_state.sql
-- Adds the AMBIGUOUS label state (ThesisDesign section 8.2): one indicator only, or evidence that disagrees
-- with the rock code. An ambiguous interval has no label, like UNRESOLVED, but it is reported separately.
-- SQLite cannot alter a CHECK constraint, so interval_labels is rebuilt with the same columns, keys and
-- index. No foreign key or trigger refers to interval_labels, and the views that read it are unchanged.

CREATE TABLE interval_labels_0011 (
    dataset_version_id          INTEGER NOT NULL,
    interval_id                 INTEGER NOT NULL,
    rule_id                     TEXT    NOT NULL REFERENCES graphite_label_rules (rule_id),
    label                       INTEGER CHECK (label IS NULL OR label IN (0, 1)),
    label_state                 TEXT    NOT NULL CHECK (label_state IN ('POSITIVE', 'NEGATIVE', 'UNRESOLVED', 'AMBIGUOUS')),
    rule_status_at_derivation   TEXT    NOT NULL,
    PRIMARY KEY (dataset_version_id, interval_id, rule_id),
    FOREIGN KEY (dataset_version_id, interval_id)
        REFERENCES interval_label_evidence (dataset_version_id, interval_id),
    CHECK ((label_state = 'POSITIVE' AND label = 1) OR (label_state = 'NEGATIVE' AND label = 0)
           OR (label_state IN ('UNRESOLVED', 'AMBIGUOUS') AND label IS NULL))
);

INSERT INTO interval_labels_0011 (dataset_version_id, interval_id, rule_id, label, label_state, rule_status_at_derivation)
SELECT dataset_version_id, interval_id, rule_id, label, label_state, rule_status_at_derivation FROM interval_labels;

DROP TABLE interval_labels;

CREATE TABLE interval_labels (
    dataset_version_id          INTEGER NOT NULL,
    interval_id                 INTEGER NOT NULL,
    rule_id                     TEXT    NOT NULL REFERENCES graphite_label_rules (rule_id),
    label                       INTEGER CHECK (label IS NULL OR label IN (0, 1)),
    label_state                 TEXT    NOT NULL CHECK (label_state IN ('POSITIVE', 'NEGATIVE', 'UNRESOLVED', 'AMBIGUOUS')),
    rule_status_at_derivation   TEXT    NOT NULL,
    PRIMARY KEY (dataset_version_id, interval_id, rule_id),
    FOREIGN KEY (dataset_version_id, interval_id)
        REFERENCES interval_label_evidence (dataset_version_id, interval_id),
    CHECK ((label_state = 'POSITIVE' AND label = 1) OR (label_state = 'NEGATIVE' AND label = 0)
           OR (label_state IN ('UNRESOLVED', 'AMBIGUOUS') AND label IS NULL))
);

INSERT INTO interval_labels (dataset_version_id, interval_id, rule_id, label, label_state, rule_status_at_derivation)
SELECT dataset_version_id, interval_id, rule_id, label, label_state, rule_status_at_derivation FROM interval_labels_0011;

DROP TABLE interval_labels_0011;

CREATE INDEX ix_interval_labels_rule ON interval_labels (rule_id, dataset_version_id, label_state);

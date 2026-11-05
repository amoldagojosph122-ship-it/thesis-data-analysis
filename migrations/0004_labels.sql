-- 0004_labels.sql
-- Graphitic label candidates. Evidence fields are logged indicators, not independent laboratory tests.
-- No rule is APPROVED without a recorded reviewer decision (enforced by trigger below).

CREATE TABLE graphite_label_rules (
    rule_id                 TEXT    PRIMARY KEY,              -- e.g. STRICT_SGS_v1
    rule_version            TEXT    NOT NULL,
    rule_family             TEXT    NOT NULL CHECK (rule_family IN ('STRICT', 'RECONCILED', 'SENSITIVITY')),
    description             TEXT    NOT NULL,
    definition_sha256       TEXT    NOT NULL,                 -- hash of the YAML definition used
    status                  TEXT    NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED', 'APPROVED', 'REJECTED')),
    approved_by             TEXT,
    approved_utc            TEXT,
    created_utc             TEXT    NOT NULL,
    CHECK (status <> 'APPROVED' OR (approved_by IS NOT NULL AND approved_utc IS NOT NULL))
);

CREATE TABLE label_reviews (
    label_review_id         INTEGER PRIMARY KEY,
    dataset_version_id      INTEGER REFERENCES dataset_versions (dataset_version_id),
    rule_id                 TEXT    NOT NULL REFERENCES graphite_label_rules (rule_id),
    scope                   TEXT    NOT NULL CHECK (scope IN ('RULE', 'INTERVAL', 'HOLE', 'EVIDENCE_PATTERN')),
    scope_key               TEXT,
    reviewer                TEXT    NOT NULL,
    decision                TEXT    NOT NULL CHECK (decision IN
                              ('APPROVE_RULE', 'REJECT_RULE', 'AMEND_RULE', 'ACCEPT_LABEL', 'OVERRIDE_LABEL', 'DEFER')),
    decided_utc             TEXT    NOT NULL,
    rationale               TEXT    NOT NULL
);

-- FR-010: a rule may become APPROVED only when an APPROVE_RULE review exists for it.
CREATE TRIGGER graphite_rule_approval_requires_review
BEFORE UPDATE OF status ON graphite_label_rules
WHEN NEW.status = 'APPROVED'
     AND NOT EXISTS (SELECT 1 FROM label_reviews r WHERE r.rule_id = NEW.rule_id AND r.decision = 'APPROVE_RULE')
BEGIN
    SELECT RAISE(ABORT, 'graphite rule cannot be APPROVED without an APPROVE_RULE label_reviews row');
END;

CREATE TABLE interval_label_evidence (
    dataset_version_id          INTEGER NOT NULL REFERENCES dataset_versions (dataset_version_id),
    interval_id                 INTEGER NOT NULL REFERENCES logging_intervals (interval_id),
    rock_code_status            TEXT    NOT NULL CHECK (rock_code_status IN ('VALID', 'UNSUPPORTED', 'MISSING')),
    is_sgs                      INTEGER CHECK (is_sgs IS NULL OR is_sgs IN (0, 1)),          -- NULL unless rock code VALID
    has_gr_mineral              INTEGER NOT NULL CHECK (has_gr_mineral IN (0, 1)),          -- alt_min1 or alt_min2 == 'gr'
    comment_present             INTEGER NOT NULL CHECK (comment_present IN (0, 1)),
    comment_graphitic           INTEGER NOT NULL CHECK (comment_graphitic IN (0, 1)),       -- regex 'graphit' (case-insensitive)
    comment_trace_qualified     INTEGER NOT NULL CHECK (comment_trace_qualified IN (0, 1)), -- 'trace' and 'graphit' both present
    comment_term                TEXT    CHECK (comment_term IS NULL OR comment_term IN ('graphitic', 'graphite')),
    positive_indicators         INTEGER NOT NULL CHECK (positive_indicators BETWEEN 0 AND 3),
    negative_indicators         INTEGER NOT NULL CHECK (negative_indicators BETWEEN 0 AND 3),
    label_conflict              INTEGER NOT NULL CHECK (label_conflict IN (0, 1)),
    evidence_pattern            TEXT    NOT NULL,            -- e.g. SGS+GR+CMT, SGS+CMT, CMT, NONE
    label_review_status         TEXT    NOT NULL CHECK (label_review_status IN
                                  ('CONSISTENT_POSITIVE', 'CONSISTENT_NEGATIVE', 'CONFLICT_REVIEW_REQUIRED',
                                   'UNRESOLVED_CODE', 'UNRESOLVED_NO_COMMENT', 'UNRESOLVED_PARTIAL_EVIDENCE')),
    rationale                   TEXT    NOT NULL,
    PRIMARY KEY (dataset_version_id, interval_id)
);

CREATE TABLE interval_labels (
    dataset_version_id          INTEGER NOT NULL,
    interval_id                 INTEGER NOT NULL,
    rule_id                     TEXT    NOT NULL REFERENCES graphite_label_rules (rule_id),
    label                       INTEGER CHECK (label IS NULL OR label IN (0, 1)),
    label_state                 TEXT    NOT NULL CHECK (label_state IN ('POSITIVE', 'NEGATIVE', 'UNRESOLVED')),
    rule_status_at_derivation   TEXT    NOT NULL,
    PRIMARY KEY (dataset_version_id, interval_id, rule_id),
    FOREIGN KEY (dataset_version_id, interval_id)
        REFERENCES interval_label_evidence (dataset_version_id, interval_id),
    CHECK ((label_state = 'POSITIVE' AND label = 1) OR (label_state = 'NEGATIVE' AND label = 0)
           OR (label_state = 'UNRESOLVED' AND label IS NULL))
);

CREATE INDEX ix_interval_labels_rule ON interval_labels (rule_id, dataset_version_id, label_state);

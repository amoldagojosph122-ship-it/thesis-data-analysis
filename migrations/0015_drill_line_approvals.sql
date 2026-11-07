-- 0015_drill_line_approvals.sql
-- Approval of the nominal-Northing drill-line groups. The table is global, like elevation_sources, so an approval
-- survives rebuilds: the build reads it for every dataset version. Each row records the approver and the time.

CREATE TABLE drill_line_approvals (
    line_code               TEXT    PRIMARY KEY,              -- e.g. NOM_N1112140
    approved_by             TEXT    NOT NULL,
    approved_utc            TEXT    NOT NULL,
    rationale               TEXT    NOT NULL
);

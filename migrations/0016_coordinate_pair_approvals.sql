-- 0016_coordinate_pair_approvals.sql
-- Approval of the adopted horizontal coordinate pair. The table is global, like drill_line_approvals, so the approval
-- survives rebuilds: the build reads it for every dataset version. The row records the approver and the time.

CREATE TABLE coordinate_pair_approvals (
    adopted_pair            TEXT    PRIMARY KEY CHECK (adopted_pair IN ('UTM_EASTING_NORTHING', 'EASTING_NORTHING')),
    approved_by             TEXT    NOT NULL,
    approved_utc            TEXT    NOT NULL,
    rationale               TEXT    NOT NULL
);

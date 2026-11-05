**T01: Workbook inventory, reconciliation and integrity checks [T01_integrity] (obj1_master c45b6dfe0519; PROVISIONAL where labels or coordinates are used)**

| test_group | test_name | expected | observed | outcome | run_utc |
|---|---|---|---|---|---|
| RECONCILIATION | Holes | 71 | 71 | PASS | 2026-11-05T02:01:20Z |
| RECONCILIATION | Holes intersecting Sgs | 42 | 42 | PASS | 2026-11-05T02:01:20Z |
| RECONCILIATION | Logging intervals | 1910 | 1910 | PASS | 2026-11-05T02:01:20Z |
| RECONCILIATION | Sgs intervals | 529 | 529 | PASS | 2026-11-05T02:01:20Z |
| RECONCILIATION | Survey stations | 71 | 71 | PASS | 2026-11-05T02:01:20Z |
| SQL_INTEGRITY | PRAGMA foreign_key_check | 0 rows | 0 rows | PASS | 2026-11-05T02:01:20Z |
| SQL_INTEGRITY | PRAGMA integrity_check | ok | ok | PASS | 2026-11-05T02:01:20Z |
| SQL_INTEGRITY | Stage B contract tables: blocking triggers present and empty | 9 triggers; 0 rows | 9 triggers; 0 rows | PASS | 2026-11-05T02:01:20Z |
| SQL_INTEGRITY | raw_* UPDATE rejected by trigger | rejected | rejected | PASS | 2026-11-05T02:01:20Z |
| SQL_INTEGRITY | z_absolute_m non-null rows | 0 | 0 | PASS | 2026-11-05T02:01:20Z |

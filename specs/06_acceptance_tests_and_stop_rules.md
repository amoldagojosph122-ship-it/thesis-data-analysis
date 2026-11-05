# 06 Acceptance tests and stop rules

## Stop, warn and defer rules (as implemented)

| Condition | Behaviour | Where enforced |
|---|---|---|
| Workbook missing, or raw copy hash differs | STOP (SourceIntegrityError); no version written | source.ensure_raw_copy |
| Applied migration changed | STOP (MigrationError) | db.migrate |
| Foreign-key or integrity check fails | STOP; transaction rolled back; ingestion run FAILED | build._full_build |
| Identical dataset version exists and is ACTIVE | NOOP_IDENTICAL | build.build |
| Identical dataset version exists and is ARCHIVED | Re-activation without duplication | build._reactivate |
| Interval overlaps, invalid depths, out-of-range survey angles, duplicate or orphan records | Quarantined and reported as ERROR; raw row retained | curate, qaqc |
| Unsupported or missing rock code | Label UNRESOLVED for every rule; WARNING or ERROR | labels, qaqc |
| Collar RL missing, absolute elevation requested | Absolute BLOCKED; relative Z only (WARNING) | qaqc QC-RL, schema CHECK |
| Graphitic rule approval without review | STOP (trigger) | migration 0004 |
| Stage B table insert | STOP (trigger) | migration 0007 |
| Figure requested for a deferred item | Refused with a DEFERRED message | registry.render_figures |
| Unsupported version argument (other than active) | Refused | registry._check_version |

## Acceptance matrix

| # | Acceptance test | Evidence in this delivery | Result |
|---|---|---|---|
| 1 | Workbook SHA-256 logged; raw source preserved | `source_files.sha256`; `data/raw/SOURCE_HASH.txt`; `test_raw_copy_matches_workbook_hash`, `test_stored_source_hash_and_counts_match_workbook` | PASS |
| 2 | Counts recomputed from the workbook and reconciled | `kambale verify` RECONCILIATION rows: holes 71, survey stations 71, intervals 1,910, Sgs 529, holes with Sgs 42; evidence 476/87/43/1,304 via `test_evidence_distribution_reconciles_with_workbook_recount` | PASS |
| 3 | Every curated interval joins a valid hole, or is quarantined and reported | 0 orphans (`test_integrity_and_foreign_keys`); QC-ORPHAN-LOG PASS | PASS |
| 4 | Depth interval geometry physically plausible; assumptions explicit | 1-m intervals; geometry unit tests; config/coordinate_decisions.yaml | PASS |
| 5 | `foreign_key_check` and `integrity_check` succeed | verify: 0 rows; `ok` | PASS |
| 6 | Two identical reruns create no duplicates | `test_identical_rebuild_is_a_noop`: counts unchanged, one dataset version | PASS |
| 7 | Null collar RL never yields a measured z_absolute | `test_absolute_elevation_is_never_populated`; 0 non-null rows | PASS |
| 8 | Label-source disagreements reconstructable from the database | v_interval_flags, v_label_disagreement, ambiguity_review_intervals.csv | PASS |
| 9 | Each Stage A figure regenerated solely from SQLite; hashes match files | `test_manifest_hashes_match_files`; `test_figure_code_never_touches_the_workbook_or_shapefile`; `test_rerender_is_byte_identical` | PASS |
| 10 | Test suite succeeds; failures and limitations listed | `kambale verify`: pytest 35 passed; failures 0 | PASS |

## Test inventory (35 tests; run with `kambale verify` or `pytest`)

- tests/test_geometry.py: cardinal azimuths, vertical hole, dip -60 east, negative dip, refusal outside convention, drill-line grouping, null absolute elevation (in database).
- tests/test_labels.py: comment text evidence (parametrised), unsupported code unresolved, missing code, strict rule, two-of-three rule, blank comment, conflict flag, workbook recount reconciliation.
- tests/test_database.py: raw hash, stored hash and counts, integrity and foreign keys, raw UPDATE/DELETE rejection (parametrised), identical rebuild no-op, rule approval trigger, Stage B blocking, RL absent and rules PROPOSED.
- tests/test_figures.py: figure code does not read the workbook or shapefile; figure SQL has no `SELECT *`; manifest hashes match files; byte-identical rerender; deferred items have no outputs.

## Limitations of this verification

- Figures were checked for layout by viewing rendered PNGs for F01 and F09. F02-F08 were generated and hashed but not individually inspected in this session.
- The pytest suite does not test scientific correctness of the label definitions; it tests their logic and reconciliation with the workbook.
- Interactive HTML for the 3-D view was not produced (optional; plotly not installed in the project environment).

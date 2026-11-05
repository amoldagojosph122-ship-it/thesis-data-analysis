# Tasks: Kambale Objective 1 Database and Stage A Preliminary Geology

**Input**: `specs/001-kambale-o1-stage-a/spec.md`, `plan.md`
**Evidence rule**: a task is ticked only when the command named in its evidence column has been run in the current session and its output has been recorded.

Format: `[ID] [P?] [Story] Description — Evidence`. `[P]` = can run in parallel with other `[P]` tasks in the same phase. `[US#]` maps to the user story in `spec.md`.

## Phase 1: Setup and provenance

- [x] T001 Initialise Spec Kit (`specify init --here --force --integration claude --non-interactive`), backup of pre-init files taken — Evidence: `.specify/` and `.claude/skills/speckit-*` present; pre-init backup in scratchpad
- [x] T002 Write constitution v1.0.0 at `.specify/memory/constitution.md` — Evidence: file present with version line `1.0.0`
- [x] T003 Create feature `specs/001-kambale-o1-stage-a/` and `spec.md` — Evidence: spec file present
- [x] T004 Write `plan.md` and this `tasks.md` — Evidence: files present
- [ ] T005 Create package layout, `pyproject.toml` with pinned versions, `.venv` or documented interpreter — Evidence: `python -c "import kambale"` succeeds
- [ ] T006 [P] Copy workbook to `data/raw/` and write `data/raw/SOURCE_HASH.txt` with SHA-256 — Evidence: `sha256sum` of copy equals source hash (a449097f…dbfb6)
- [ ] T007 [P] Write `config/coordinate_decisions.yaml`, `config/label_rules.yaml`, `config/qaqc_thresholds.yaml` — Evidence: YAML loads without error

## Phase 2: Foundational — database contract

- [ ] T008 Write migration `0001_provenance.sql` (source_files, source_sheets, ingestion_runs, dataset_versions, raw_row_map, analysis_runs) — Evidence: migration applies to an empty DB
- [ ] T009 Write migration `0002_raw.sql` with `raw_collars`, `raw_surveys`, `raw_logging`, `raw_geological_legend`, `raw_reference_lists` and UPDATE/DELETE triggers — Evidence: test `test_raw_immutable` passes
- [ ] T010 Write migration `0003_curated_core.sql` (holes, survey_stations, logging_intervals, geological_code_dictionary, drill_lines) — Evidence: DDL applies; `PRAGMA foreign_key_list` shows FKs
- [ ] T011 Write migration `0004_labels.sql` (graphite_label_rules, interval_label_evidence, interval_labels, label_reviews) — Evidence: DDL applies
- [ ] T012 Write migration `0005_geometry.sql` (coordinate_system_registry, coordinate_decisions, elevation_sources, geometry_builds, interval_coordinates) with CHECK that `z_absolute_m` is NULL when `elevation_source_id` is NULL — Evidence: test inserting non-null z_absolute without source fails
- [ ] T013 Write migration `0006_qaqc_audit.sql` (qaqc_checks, qaqc_findings, qaqc_resolutions, figure_registry, figure_query_registry, figure_export_manifest, plot_statistic_snapshots, validation_test_results, dataset_export_receipts, regional_geology_context) — Evidence: DDL applies
- [ ] T014 Write migration `0007_future_contracts.sql` (spatial_folds, variogram_runs, variogram_points, model_runs, model_predictions, model_evaluation_metrics, probability_calibration, uncertainty_voxels, simulation_runs) as empty tables with insert-blocking triggers — Evidence: insert attempt raises ABORT in test
- [ ] T015 Implement `db.py`: `connect()` sets `PRAGMA foreign_keys=ON`; migration runner records `schema_migrations` with SHA-256 — Evidence: rerunning migrations is a no-op

## Phase 3: Ingestion and curation

- [ ] T016 [US1] Implement `source.py`: SHA-256 of file, copy-with-verification, sheet inventory (dimensions, headers, blank columns, inferred types) using openpyxl cell reads — Evidence: inventory printed for 8 sheets
- [ ] T017 [US1] Implement `ingest.py`: load `raw_*` tables with `source_sheet`, `source_row`, raw field values and `payload_json`; stop with FAILED on hash mismatch — Evidence: counts 71 / 71 / 1,910 / 72 legend rows match workbook recount
- [ ] T018 [US1] Redact the worksheet-protection value in `raw_reference_lists` (documented in plan decision 9) — Evidence: no password string appears in DB or outputs (`grep` check)
- [ ] T019 [US1] Implement `curate.py`: normalise HoleID (trim, collapse whitespace, upper-case), parse `DateDrilled` with `%d-%m-%Y`, build `holes`, `survey_stations`, `logging_intervals`, `geological_code_dictionary` — Evidence: `DateDrilled` parse count 71/71
- [ ] T020 [US1] Orphan and key checks: every interval matches a hole; every survey matches a hole; every hole has ≥1 interval — Evidence: `verify` reports 0 orphans
- [ ] T021 [US1] Overlap, gap, zero-length and depth-match checks; log end depth equals `max_depth` — Evidence: findings table with PASS counts

## Phase 4: QA/QC and graphitic label candidates

- [ ] T022 [US2] Implement `qaqc.py` with the check catalogue (ERROR/WARNING/INFO; BLOCKED/PROVISIONAL/APPROVED) covering: duplicates, depth validity, RL presence, survey conventions, coordinate pair discrepancy, project-prospect consistency, blank columns, unsupported and missing codes, legend agreement between `Logging Legend` and hidden reference list — Evidence: `qaqc_findings` row counts by check
- [ ] T023 [US2] Implement `labels.py` evidence flags: `is_sgs`, `has_gr_mineral` (alt_min1 and alt_min2 only), `comment_graphitic` (case-insensitive `graphit`), `comment_trace_qualified`, `comment_term` — Evidence: unit test on 10 synthetic comments
- [ ] T024 [US2] Implement conflict logic (`label_conflict` = at least one positive and at least one affirmative negative) and `label_review_status` — Evidence: conflict count equals 130 from the workbook recount (43 + 87)
- [ ] T025 [US2] Implement candidate rules from `config/label_rules.yaml` for `STRICT_SGS_v1`, `RECON_2OF3_v1`, `ALL3_v1`, `ANY_v1` with status `PROPOSED` — Evidence: `v_label_candidate_counts` returns 4 rules × 3 label states
- [ ] T026 [US2] Reconciliation check: evidence distribution reproduces 476 / 87 / 43 / 1,304 from the workbook; any difference recorded in `validation_test_results` — Evidence: test `test_evidence_reconciliation`
- [ ] T027 [US2] Export ambiguity review table (`data/derived/ambiguity_review_intervals.csv`) — Evidence: row count equals conflict count

## Phase 5: Geometry

- [ ] T028 [US3] Implement `geometry.py` coordinate decision (`UTM` pair adopted, PROVISIONAL), write `coordinate_system_registry`, `coordinate_decisions`, `elevation_sources` (BLOCKED row: "no approved source") — Evidence: rows present, `elevation_sources` has no approved row
- [ ] T029 [US3] Implement straight-hole offsets `delta_E`, `delta_N`, `delta_Z` in radians, rounding to 0.1 mm, with validation of dip ∈ [−90, 0] and azimuth ∈ [0, 360) — Evidence: test `test_geometry_cardinal_and_dip`
- [ ] T030 [US3] Write `interval_coordinates` for all 1,910 intervals with `z_relative_m` and NULL `z_absolute_m` — Evidence: `SELECT COUNT(*) WHERE z_absolute_m IS NOT NULL` = 0
- [ ] T031 [US3] Assign provisional drill lines by nominal Northing into `drill_lines`; store projection offset (`N_collar − N_nominal`) per hole — Evidence: 5 lines; hole counts 3/13/21/15/19
- [ ] T032 [US3] Ingest regional geology polygons within a 10 km buffer into `regional_geology_context` (with shapefile hash and 1:1,000,000 caveat) — Evidence: count and hash recorded

## Phase 6: Build and views

- [ ] T033 Implement `build.py`: single transaction; `dataset_version_key`; identical key → no-op; new key → ACTIVE with prior version ARCHIVED — Evidence: test `test_build_idempotent` (two runs, same counts, one ACTIVE row)
- [ ] T034 Write `0008_views.sql`: `v_active_version`, `v_holes`, `v_survey`, `v_logging`, `v_code_usage`, `v_label_evidence`, `v_label_candidates`, `v_label_candidate_counts`, `v_label_conflicts`, `v_hole_graphite`, `v_line_graphite`, `v_depth_weathering`, `v_collar_plan`, `v_interval_geometry`, `v_qaqc_summary`, `v_completeness`, `v_regional_context`, `v_export_receipts` — Evidence: each view selects without error
- [ ] T035 Implement `verify.py`: `PRAGMA foreign_key_check`, `integrity_check`, reconciliation counts, store results in `validation_test_results` — Evidence: `kambale verify` prints summary

## Phase 7: Figures and tables

- [ ] T036 [P] Write `sql/figures/F01.sql` … `F09.sql`, `T01.sql` … `T03.sql` (no `SELECT *`; all from `v_*` views) — Evidence: test `test_figure_sql_has_no_select_star`
- [ ] T037 [P] Implement `figures/style.py` (palette, footer, deterministic save) — Evidence: two saves produce identical SHA-256
- [ ] T038 [US4] Implement F01 collar plan (regional context, line colours, coordinate caveat), F02 length distribution, F03 completeness and QA chart — Evidence: PNG/SVG/PDF written, manifest rows
- [ ] T039 [US4] Implement F04 3-D relative-Z view and strip logs; optional interactive HTML if plotly is installed — Evidence: files written; caption states relative Z
- [ ] T040 [US4] Implement F05 lithology frequency and metres; F06 graphitic proportion and thickness by hole; F07 depth-bin × weathering; F08 plan map by graphitic fraction; F09 relative-Z sections by line — Evidence: five figure files each with manifest row
- [ ] T041 [US4] Implement T01 (workbook inventory and reconciliation), T02 (code dictionary and label disagreement), T03 (graphitic evidence by hole and line) as CSV, Markdown and LaTeX — Evidence: files written
- [ ] T042 [US4] Implement `registry.py`: write `figure_registry`, `figure_query_registry` (SQL hash), `figure_export_manifest` (output hash), `FIGURE_MANIFEST.csv` — Evidence: manifest hashes match files on disk
- [ ] T043 [US4] Write `DEFERRED_FIGURES.md` with each deferred item, its prerequisite gate and planned table contract — Evidence: file present; lists all deferred items from the Stage A prompt

## Phase 8: Tests and verification

- [ ] T044 Tests: raw hash and immutability; FK and integrity; geometry cardinal/dip cases; label evidence; idempotent build; null-RL safety; figure provenance and manifest hashes; future-table write block — Evidence: `pytest -q` output recorded in `validation_test_results`
- [ ] T045 Regenerate all figures twice; compare SHA-256 of outputs — Evidence: identical hashes recorded
- [ ] T046 Run ETL twice from a clean database; confirm identical counts — Evidence: recorded counts

## Phase 9: Reports and handover

- [ ] T047 Write `reports/QAQC_REPORT.md` from database content (counts, findings, decisions) — Evidence: report cites the executed commands
- [ ] T048 Write `README.md` (rerun commands, status vocabulary, limitations) — Evidence: commands in README were executed
- [ ] T049 Write seven stage deliverables `01_thesis_scope_and_objective_traceability.md` … `07_speckit_agent_kickoff.md` and `03_schema.sql` under `specs/` — Evidence: files present, no placeholders
- [ ] T050 Final handover: COMPLETED / PROVISIONAL / BLOCKED / DEFERRED / FAILED list with exact pass/fail counts — Evidence: handover section in README and final message

## Dependencies

- Phase 1 before Phase 2; Phase 2 before Phase 3; Phase 3 before Phase 4 and Phase 5 (both read curated tables); Phases 4 and 5 before Phase 6 (build assembles them); Phase 6 before Phase 7; Phases 7 before Phase 8 and 9.
- T036 and T037 can run in parallel with T038–T041 once views exist.

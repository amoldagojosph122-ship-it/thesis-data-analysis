# Feature Specification: Kambale Objective 1 Database and Stage A Preliminary Geology

**Feature Branch**: `001-kambale-o1-stage-a` (no git repository is initialised in this project; the branch name is informational only)

**Created**: 2026-11-05

**Status**: Draft for supervisor review

**Input**: User description: "Stage A of the Kambale graphite thesis: database-first Objective 1 implementation (SQLite canonical store for RAB collars, surveys and logging; QA/QC; graphitic label candidates; provisional relative 3-D geometry; Stage A figures and tables rendered from SQL; reproducible tests and handover). Objectives 2-5 are not implemented in this feature."

## Governing charter

- Thesis title and the five synopsis objectives are fixed and reproduced verbatim in `.specify/memory/constitution.md`. This feature implements the Objective 1 database and the data-supported part of the Objective 2 exploratory description. It does not implement Objectives 3, 4 or 5.
- Authoritative inputs: `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx` (primary); `ThesisDesign.docx` and `ReadingGuide.docx` (methodology and reconciliation expectations only); `Architecture/Kambale_Five_Database_Architecture_and_Execution_Order.md` and `Objective_1/Kambale_Objective_1_MultiDB_Addendum.md` (database allocation, which controls where they differ from the Stage A prompt); the regional 1:1,000,000 geology shapefile `GEOMAP1000_shp/Shapefiles/Geology/geology_polygon.shp` (geographic context only).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build an auditable canonical database from the workbook (Priority: P1)

As the thesis author, I run one command against the supplied workbook and obtain a SQLite database in which every raw row, its source sheet and row number, and the file hash are preserved, and every curated record links back to a raw row.

**Why this priority**: Every later figure, label and model depends on this provenance. Without it, no result is defensible.

**Independent Test**: Run the ETL on a clean checkout. Confirm that the stored SHA-256 equals the hash of the workbook, that raw row counts equal the workbook row counts, and that `PRAGMA foreign_key_check` and `PRAGMA integrity_check` return no rows and `ok`.

**Acceptance Scenarios**:

1. **Given** the workbook is present, **When** the ETL runs, **Then** `source_files` stores the SHA-256 of `data/raw/` copy and the original workbook hash, and both match.
2. **Given** the workbook has 71 collar rows, 71 survey rows and 1,910 logging rows, **When** the ETL completes, **Then** raw table counts equal those values (computed from the workbook, not hardcoded) and every logging interval resolves to a valid hole.
3. **Given** a raw row, **When** an UPDATE or DELETE is attempted on any `raw_*` table, **Then** the database rejects it.
4. **Given** the ETL has already run on the same source and code, **When** it runs again, **Then** no rows are duplicated and the active dataset version is unchanged.

---

### User Story 2 - Quality-control the geology and expose graphitic label candidates (Priority: P2)

As the supervising geologist, I review a QA/QC report and a set of candidate graphitic label definitions, each traceable to its evidence fields, and I record decisions without the software choosing one definition as truth.

**Why this priority**: The label is the thesis target. The workbook's three graphite fields disagree, and the thesis cannot proceed until a reviewed rule exists.

**Independent Test**: Query `v_interval_label_evidence` and `v_label_candidate_counts`. Confirm that the 3-indicator evidence distribution reproduces the earlier reconciliation expectation (476 / 87 / 43 / 1,304) and that every candidate rule row carries status `PROPOSED`.

**Acceptance Scenarios**:

1. **Given** the legend lists `Sgs` as meta-sediment graphite schist, **When** a logging interval has `rock_type1 = 'Sgs'`, **Then** `is_sgs = 1` and the interval carries the evidence row with its raw code preserved.
2. **Given** an unsupported code (`fsc`, not in the legend), **When** label candidates are derived, **Then** the strict label is NULL with status `UNSUPPORTED_CODE` and the interval is listed in the QA/QC findings as ERROR.
3. **Given** a graphitic comment on a `Sbs` interval, **When** the label is derived, **Then** the disagreement is recorded in `label_conflict` and listed in the ambiguity review export.
4. **Given** no supervisor decision has been recorded, **When** any figure is rendered, **Then** its label status reads `PROPOSED - NOT APPROVED`.

---

### User Story 3 - Derive verified along-hole geometry with explicit provisional status (Priority: P3)

As the author, I obtain interval midpoints and provisional relative 3-D offsets from the straight-hole assumption, and every coordinate row states that RL is absent and that `z_absolute_m` is NULL.

**Why this priority**: The thesis needs 3-D positions, but absolute elevation is not in the workbook. The geometry must be usable for relative sections without implying surveyed elevation.

**Independent Test**: Run the geometry unit tests (cardinal directions and dips) and check that `z_absolute_m` is NULL for all `interval_coordinates` rows.

**Acceptance Scenarios**:

1. **Given** dip `-90` and any azimuth, **When** offsets are computed, **Then** `delta_E = delta_N = 0` and `delta_Z = -m`.
2. **Given** dip `-60` and azimuth `90`, **When** offsets are computed for `m = 10.5`, **Then** `delta_E = 10.5 cos(-60°) sin(90°) = 5.25`, `delta_N = 0` and `delta_Z = 10.5 sin(-60°)`.
3. **Given** the RL column is blank for every collar, **When** any vertical position is written, **Then** it is stored as `z_relative_m` and labelled "relative vertical position (m; provisional)".

---

### User Story 4 - Regenerate Stage A figures and tables from SQLite (Priority: P4)

As the author, I render each Stage A figure or table with one CLI command, and each output is registered with its SQL hash, dataset version, label status, geometry status and its own file hash.

**Why this priority**: Reproducibility is a mandatory thesis requirement, and an unregistered figure cannot be defended.

**Independent Test**: Run `kambale plot --figure F06` twice; confirm that both outputs have identical SHA-256 values and that the manifest row matches the file.

**Acceptance Scenarios**:

1. **Given** the active dataset version, **When** `kambale plot --figure F01` runs, **Then** the figure is drawn only from `v_*` views and the query text is hashed into `figure_query_registry`.
2. **Given** a figure that depends on the provisional coordinate decision, **When** it is rendered, **Then** its caption and footer state the coordinate status.
3. **Given** a deferred item (variogram, indicator kriging, ML or simulation), **When** the figure catalogue is generated, **Then** it appears in `DEFERRED_FIGURES.md` with the prerequisite gate and no plot file.

---

### User Story 5 - Verify and hand over (Priority: P5)

As the supervisor, I read a QA/QC report, a figure manifest and a handover that list completed, provisional, blocked, deferred and failed items, each backed by an executed test.

**Why this priority**: Truthful status reporting is required before Stage B may start.

**Independent Test**: Run `pytest`, record the counts and the failures, and confirm that `QAQC_REPORT.md` and `FIGURE_MANIFEST.csv` agree with the database.

**Acceptance Scenarios**:

1. **Given** the test suite, **When** `pytest` runs, **Then** every test result is recorded in `validation_test_results` or reported as not run.
2. **Given** a Stage B-only figure request, **When** it is attempted, **Then** the command refuses with a DEFERRED status.

### Edge Cases

- A hole ID in logging or surveys has no collar record: the interval is quarantined and reported (none expected; the check must still run).
- Two logging intervals overlap, leave a gap, or have `DEPTH_FROM >= DEPTH_TO`: quarantined and reported as ERROR.
- The workbook changes after ingestion (different SHA-256): the ETL stops with a `FAILED` status and does not overwrite the previous dataset version.
- A missing lithology code (one interval, `rock_type1` blank): the strict label is NULL, status `MISSING_CODE`, reported as WARNING.
- Collar `RL` absent: all `z_absolute_m` values are NULL; any request for absolute 3-D products is BLOCKED.
- Two coordinate pairs disagree: both are stored; the adopted pair is recorded in `coordinate_decisions` with status PROVISIONAL and the disagreement statistics.
- A dip or azimuth outside the adopted convention (dip not in [-90, 0] or azimuth not in [0, 360)): flagged ERROR and the geometry for that hole is not written.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST copy the supplied workbook to `data/raw/` without modification and store its SHA-256 and original path in `source_files`.
- **FR-002**: The system MUST store every raw row of `Collars`, `Surveys`, `Logging`, `Logging Legend`, and the hidden reference sheets in `raw_*` tables with sheet name, Excel row number, raw field names and a JSON payload of the raw values.
- **FR-003**: The system MUST reject UPDATE and DELETE on `raw_*` tables with a database trigger.
- **FR-004**: The system MUST normalise `HoleID`/`HOLEID` (trim, collapse internal whitespace, upper-case) while retaining the raw spelling, and MUST report every unmatched ID across the three source sheets.
- **FR-005**: The system MUST run the QA/QC checks listed in `qaqc_checks` and record each finding with severity `ERROR`, `WARNING` or `INFO` and status `BLOCKED`, `PROVISIONAL` or `APPROVED`.
- **FR-006**: The system MUST parse `DateDrilled` with the explicit format `%d-%m-%Y` and MUST reject any value that does not parse under that format.
- **FR-007**: The system MUST load logging legend codes as reference data and MUST NOT infer geological meaning from code spelling.
- **FR-008**: The system MUST record, for every logging interval, `is_sgs`, `has_gr_mineral`, `comment_graphitic`, `label_evidence_count`, `label_conflict`, `label_review_status` and the rationale text.
- **FR-009**: The system MUST derive the candidate labels listed in `graphite_label_rules` (strict `Sgs`; reconciled "two or more of three indicators"; "all three"; "any indicator") and store each under its own rule version and status.
- **FR-010**: The system MUST NOT mark any rule `APPROVED` unless a row exists in `label_reviews` with a reviewer identifier and decision date.
- **FR-011**: The system MUST store all three raw coordinate columns and MUST record the chosen pair (`Easting`/`Northing` or `UTMEasting`/`UTMNorthing`), CRS, units, datum status and the transform chain in `coordinate_decisions`.
- **FR-012**: The system MUST compute `m = (DEPTH_FROM + DEPTH_TO) / 2` and, for the adopted straight-hole convention, `delta_E = m cos(d) sin(a)`, `delta_N = m cos(d) cos(a)`, `delta_Z = m sin(d)` in radians, with `d` the signed dip from horizontal (negative downward) and `a` the azimuth clockwise from north.
- **FR-013**: The system MUST store `z_relative_m = delta_Z` and `z_absolute_m = NULL` for every interval while `elevation_sources` contains no approved elevation source.
- **FR-014**: The system MUST group holes into drill lines by nominal collar Northing and MUST store the grouping in `drill_lines` with status PROVISIONAL.
- **FR-015**: The system MUST expose stable read-only `v_*` views for every figure and table, each filtered to the ACTIVE dataset version.
- **FR-016**: The system MUST render Stage A figures F01–F09 and tables T01–T03 from those views or from `sql/figures/*.sql` only.
- **FR-017**: The system MUST record each figure and table in `figure_registry`, its SQL file hash in `figure_query_registry`, and each output file hash in `figure_export_manifest`.
- **FR-018**: The system MUST write `FIGURE_MANIFEST.csv`, `DEFERRED_FIGURES.md`, `QAQC_REPORT.md` and `README.md` from database content.
- **FR-019**: The system MUST create the future-stage tables named in the Stage A prompt as empty contracts and MUST reject inserts into them.
- **FR-020**: The system MUST record a `dataset_export_receipts` row for each export that a later objective may consume.
- **FR-021**: The system MUST store the regional geology polygons intersecting the study extent in `regional_geology_context` with the shapefile hash and the statement that the map is 1:1,000,000 context only.
- **FR-022**: The system MUST NOT create a `z_absolute_m` value, a graphite grade, a tonnage, a resource or a variogram.

### Key Entities

- **source_files / source_sheets**: provenance of the workbook (hash, path, size, sheet inventory).
- **raw_collars / raw_surveys / raw_logging / raw_geological_legend / raw_reference_lists**: immutable copies of source rows with row numbers and payloads.
- **dataset_versions**: one row per ETL build, keyed by a deterministic `dataset_version_key`, with status ACTIVE or ARCHIVED.
- **holes**: curated collar record (normalised ID, nominal Northing line, UTM and E/N pairs, `max_depth`, `RL` status, parsed `DateDrilled`).
- **survey_stations**: curated survey observations, with the single end-of-hole station status.
- **logging_intervals**: curated 1-m intervals linked to holes by ID, with decoded codes and a link to the raw row.
- **geological_code_dictionary**: legend codes, descriptions, and usage counts.
- **graphite_label_rules / interval_label_evidence / interval_labels / label_reviews**: candidate label definitions, per-interval evidence, per-rule labels and reviewer decisions.
- **coordinate_system_registry / coordinate_decisions / elevation_sources**: CRS registry, adopted coordinate pair, and elevation source status.
- **drill_lines**: provisional grouping of holes by nominal Northing.
- **geometry_builds / interval_coordinates**: versioned straight-hole geometry with `z_relative_m` and NULL `z_absolute_m`.
- **qaqc_checks / qaqc_findings / qaqc_resolutions**: check catalogue, findings and decisions.
- **figure_registry / figure_query_registry / figure_export_manifest / analysis_runs**: figure provenance.
- **validation_test_results / dataset_export_receipts**: verification and export evidence.
- **regional_geology_context**: 1:1,000,000 regional polygons intersecting the study extent (context only).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The stored workbook SHA-256 equals the recomputed SHA-256 of `data/raw/` and of the original workbook, with zero mismatches.
- **SC-002**: Raw and curated counts equal values recomputed from the workbook in the same run; every discrepancy with `ThesisDesign.docx` is listed in `QAQC_REPORT.md` with its cause.
- **SC-003**: `PRAGMA foreign_key_check` returns zero rows and `PRAGMA integrity_check` returns `ok`.
- **SC-004**: Two consecutive ETL runs on the same source produce identical row counts in every table and one `dataset_versions` row.
- **SC-005**: `z_absolute_m` is NULL for 100 % of `interval_coordinates` rows while `elevation_sources` has no approved source.
- **SC-006**: The label evidence distribution reproduces 476 / 87 / 43 / 1,304 (or the workbook-recomputed values, with any difference explained).
- **SC-007**: Every Stage A figure and table has a registry row, a SQL hash, a dataset version and an output hash, and reruns of F06 produce identical SHA-256 values.
- **SC-008**: `pytest` completes with a recorded pass/fail count; no test is reported as passed unless it was executed.

## Assumptions

- The workbook is the complete supplied dataset (71 holes); the historic wider RAB campaign is not available. This is a supervisor decision still open (ThesisDesign §2.4).
- `UTM_30N` in the workbook denotes UTM zone 30N. The datum (WGS 84 or an Accra-based datum) is not stated; the coordinate status is PROVISIONAL until a survey or supervisor source confirms it.
- The dip and azimuth in `Surveys` (-60 and 090 at end of hole) are treated as a nominal straight-hole orientation with the convention "dip from horizontal, negative downward; azimuth clockwise from north". This convention is PROVISIONAL because the workbook names no instrument or surveyor.
- A blank mineral field means no code was logged for that mineral; it is evidence of absence only under the stated rule version, and the assumption is recorded in the rule.
- The regional geology shapefile is 1:1,000,000 context. It is not a local geological map and does not verify any local contact.
- No graphite assay or TGC data exist in the workbook; no tonnage, grade or resource calculation is in scope.
- Figures are produced with matplotlib (static) and an optional plotly HTML for the 3-D view only if the plotly package is available.

## Open decisions for the supervisor (recorded, not resolved by the software)

1. Confirm the coordinate pair and datum (`UTM_30N`; WGS 84 or Accra datum) for the adopted coordinates.
2. Obtain original collar RL from DGPS survey, or approve a DEM extraction method (not in scope for Stage A).
3. Approve or amend the graphitic label rule (strict `Sgs` versus reconciled candidates) and the handling of ambiguous and unsupported codes.
4. Confirm the five drill-line groups (nominal Northing clusters) or supply line assignments.
5. Confirm that the 71 holes are the intended study subset.
6. Confirm the dip and azimuth convention and whether the EOH orientation applies to the whole hole.

# JOSEPH'S KAMBALE MSc THESIS — DATABASE-FIRST SPECKIT MASTER PROMPT

## Role and assignment

You are a senior geological-engineering research methodologist, Python geospatial/geostatistical developer, SQLite database architect, and scientific-visualization engineer. Your assignment is to **design and implement the auditable data foundation and preliminary geological plotting workflow** for Joseph's MSc thesis. This is **not a Q1/Q2 manuscript-writing assignment**, a new research proposal, or a request to rewrite the synopsis. Build a thesis-grade research database that can later support the complete modelling study.

**Thesis title:** *Hybrid Machine Learning–Indicator Geostatistical Modelling for Spatially Validated Three-Dimensional Prediction and Uncertainty Characterization of Graphitic Domains at the Kambale Graphite Deposit, Ghana.*

### Fixed, approved thesis objectives — copy exactly; do not edit

1. To construct and quality-control a three-dimensional drill-hole database and define graphitic domains at the Kambale Graphite Deposit.
2. To characterize the spatial distribution, geological controls, and continuity of graphitic domains using exploratory spatial analysis and indicator variography.
3. To develop and spatially validate indicator-geostatistical, machine-learning, and hybrid models for predicting graphitic-domain occurrence.
4. To evaluate the predictive performance of the developed models using independent spatial validation and probability-based metrics.
5. To quantify and visualize three-dimensional uncertainty in graphitic-domain occurrence and identify areas of high confidence and high uncertainty.

**Primary supplied dataset:** `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx`. **Supporting methodology:** `ThesisDesign.docx` and `ReadingGuide.docx` when available locally. Regard the exact five objectives above as immutable and use the supporting design only to inform methods, not to change the objectives.

## Scope boundaries and execution stages

### NOW — Stage A: Build and verify the database; generate honest preliminary plots

Implement a working repository that:
1. Ingests the actual Excel workbook into SQLite with preserved raw values and provenance.
2. Inspects all workbook sheets, maps their exact field names, and constructs a data dictionary.
3. Performs geological and relational QA/QC without silently altering raw observations.
4. Produces standardized collar, survey, lithological-logging, legend, and interval tables.
5. Records multiple graphitic-domain **candidate definitions**, source evidence, disagreement, and approval status; does not silently declare one candidate to be geological truth.
6. Derives verified along-hole geometry and, where assumptions permit, **provisional relative 3-D trajectories**. It must not invent collar RL values or claim absolute 3-D elevation without defensible elevation input.
7. Persists all curated records, plot-ready statistics, geometry versions, source query identifiers, and figure export manifests in SQLite.
8. Generates the Objective 1 and **data-supported exploratory portion of Objective 2** figures directly from SQLite, using Python only.
9. Produces reproducible tests, a QA/QC report, schema documentation, a figure catalogue, and a clear handover for the next modelling stage.

### LATER — Stage B: Statistical/geostatistical modelling (do not execute now)

Reserve a compatible schema/interface for directional indicator variograms, indicator kriging, Random Forest, XGBoost, hybrid ML–geostatistics, grouped spatial folds, out-of-fold predictions, performance metrics, calibration, simulation and uncertainty grids. **Do not fit models, announce predictive results, produce synthetic findings, or generate model-dependent figures during Stage A.** Only create well-documented future extension interfaces where useful. Stage B begins after geological label, coordinates, group definitions, and QA/QC decisions are reviewed.

No graphite grade/TGC estimation, tonnage or resources. The supplied workbook has no usable graphite assays for these claims.

## Known workbook facts to verify programmatically

The existing workbook inspection identified these sheets:
- `Collars` (header fields: `HoleID`, `Grid`, `HoleType`, `Northing`, `Easting`, `RL`, `UTMNorthing`, `UTMEasting`, `max_depth`, `Project`, `Prospect`, `Contractor`, `LoggedBy`, `DateDrilled`).
- `Surveys` (`HoleID`, `depth`, `dip`, `azimuth`, `SurveyedBy`, `Instrument`).
- `Logging` (`HOLEID`, `DEPTH_FROM`, `DEPTH_TO`, `rock_type1`, `colour1`, `colour2`, `weathering`, `grainsize`, `structure`, `alt_min1`, `alt_min1int`, `alt_min2`, `alt_min2int`, `sul_min1`, `sul_min1pc`, `vn_type`, `vn_pc`, `Comment`, `sample_quality`).
- `Logging Legend`, `___LoggingReferences`, `___SurveyReferences`, `___CollarReferences`, `___SheetInfo`.

Previously reported diagnostic counts: **71 drill holes, 71 survey records, 1,910 logging intervals, 1,910 total logged metres, approximately 529 `Sgs` lithology intervals**. These are **reconciliation checks**, not numbers to force by modifying the data. The workbook may contain different candidate collar-coordinate columns (`Easting`/`Northing` and `UTMEasting`/`UTMNorthing`); investigate both and document the verified choice. `RL` appears missing. Survey rows may contain a single observation at end-of-hole depth; do not assert that dip/azimuth have been independently surveyed along the entire hole. The `Sgs` code, `gr` mineral code, and text descriptions are candidate evidence of graphitic geology; their disagreements require transparent review. Read the actual legend and reference sheets before defining code mappings.

If source characteristics differ from these preliminary facts, trust the actual workbook, log the discrepancy, and never hardcode the earlier counts into data processing.

## Non-negotiable architecture

- **SQLite is the canonical analytical source of truth (SSOT).** Preserve the original Excel bytes under `data/raw/` and its SHA-256 hash. SQLite may be updated through traceable, transactional and versioned ETL runs; source rows and past decisions must never be overwritten without history.
- Python 3.11+ performs extraction, checks, transformations, database writes, plots, and tests. Suggested packages: `pandas`, `openpyxl`, `numpy`, `sqlite3`/`SQLAlchemy`, `pandera` (if appropriate), `pyproj`, `scipy`, `matplotlib`, `seaborn` optional, `geopandas`, `rasterio` only if actual DEM is supplied, `pyvista` and `plotly` for 3-D interactive visualization, and `pytest`. Choose dependency versions compatible with the actual environment and lock them. Prefer the Python standard library where sufficient.
- **No QGIS, ArcGIS, Leapfrog, R or paid software is required.** Generate all Stage A figures using Python against read-only SQLite queries or persisted plot-ready views. R can be added later as an optional consumer of the same SQLite database, not a second source of truth.
- Temporary in-memory operations are allowed as implementation details, but **every raw-to-curated derivation and every result used in a thesis plot must be reconstructible and represented by committed SQLite records, versioned SQL definitions, or manifest-linked deterministic queries**. Do not use an untracked spreadsheet or notebook as an authoritative scientific result.
- Unit consistency, hole-ID referential integrity, unmodified raw codes, datum/CRS provenance, null semantics, geological label status, and audit logs are mandatory.
- Every plot must be regenerable with a documented CLI command and must display correct units, figure ID, sample support and methodological caveats. Use colorblind-accessible styles, vector PDF/SVG and 300-dpi or higher PNG; do not use decorative charts without a geological question.

## Scientific and geometric requirements

### Canonicalization and QA/QC

1. Inventory sheet names, table dimensions, exact headers, blank columns, duplicates and inferred types. Save the inventory and raw source hash.
2. Normalize `HoleID`/`HOLEID` consistently while retaining the raw spellings. Detect unmatched hole IDs across collars, surveys and logging; do not silently discard orphan records.
3. Check duplicate collars, duplicate survey stations, duplicate logging intervals, nonpositive hole depths, negative/malformed interval depths, `DEPTH_FROM >= DEPTH_TO`, overlap, gaps, log end-depth versus collar `max_depth`, unsupported lithological codes, inconsistent coordinate pairs and dip/azimuth values outside the adopted conventions.
4. Preserve original nulls and distinguish `MISSING`, `NOT_APPLICABLE`, `UNVERIFIED`, `DERIVED`, `IMPUTED` if needed. Any imputation requires explicit method/source and cannot be passed off as measured.
5. Parse `DateDrilled` explicitly; never allow date interpretation by locale guesswork.
6. Load logging reference/legend codes as reference data; do not infer geological meanings from code spelling alone.
7. Produce machine-readable QC severity `ERROR`, `WARNING`, `INFO`; contextual `BLOCKED`, `PROVISIONAL`, `APPROVED` status; and an auditable decision for every correction/exclusion.

### Graphitic label logic

Persist, for each logged interval:
- `is_sgs` evidence from lithology (`rock_type1 = 'Sgs'`, subject to exact code verification).
- `has_gr_mineral` evidence from the appropriate mineral-code fields, based on the legend.
- `comment_graphitic` text-evidence flag, with documented, testable word matching and explicit false-positive review.
- Candidate `strict_sgs_label` and a separately versioned `reconciled_label`; both nullable if unresolved.
- `label_evidence_count`, `label_conflict`, `label_review_status`, `rule_version`, `reviewer_decision`, and textual rationale, where applicable.

Do not falsely describe these three logging fields as independent laboratory confirmations. An approved geological rule or supervisor decision is required before using a reconciled label as the final supervised-learning target. Export ambiguity tables for geological review.

### Coordinates and drill-hole trajectories

Store all raw coordinate columns separately. Log a verified choice of source `Easting`/`Northing` vs `UTMEasting`/`UTMNorthing`, CRS (not merely a grid nickname), units, datum, coordinate-transform chain, and uncertainty. **Never silently mix these pairs**.

Compute and retain interval midpoint measured depth `m=(DEPTH_FROM+DEPTH_TO)/2` in metres. Determine whether dip is measured from horizontal (negative downward) and whether azimuth is clockwise from north, and validate against source metadata. For a straight-hole assumption using **verified** horizontal-referenced signed dip `d` and clockwise-north azimuth `a`, provisional relative offsets are:

`delta_E = m * cos(d) * sin(a)`
`delta_N = m * cos(d) * cos(a)`
`delta_Z = m * sin(d)`

Use radians in computation and test cardinal directions and dips. If source survey semantics or angles cannot be verified, expose coordinates as **provisional**, with a status flag and a QA/CAVEAT banner. If an appropriate verified down-hole-survey series is available, implement desurveying with an established tested method; do not pretend one end-of-hole station provides measured curvature.

For unknown collar `RL`, store `z_relative_m = delta_Z` and `z_absolute_m = NULL`; label plots `relative vertical position (m; provisional)` rather than elevation m a.s.l. Do not use `0` as an invented collar RL, and do not report a fully georeferenced 3-D mineralized volume. If survey RL or a suitable DEM is later provided, persist the actual source and vertical reference, regenerate a distinct approved geometry version, and keep the old version traceable.

## Required SQLite design

Create complete SQLite DDL, actual migrations and working SQL queries. At minimum implement:

**Provenance:** `source_files`, `source_sheets`, `ingestion_runs`, `dataset_versions`, `raw_row_map`, `analysis_runs`.

**Preserved raw data:** `raw_collars`, `raw_surveys`, `raw_logging`, `raw_geological_legend` (plus reference metadata, where relevant). Preserve original row numbers and raw field names via metadata or immutable JSON payload in addition to typed fields.

**Curated geological data:** `holes`, `survey_stations`, `logging_intervals`, `geological_code_dictionary`, `graphite_label_rules`, `interval_label_evidence`, `interval_labels`, `label_reviews`, `drill_lines`.

**Spatial/geometry:** `coordinate_system_registry`, `coordinate_decisions`, `elevation_sources`, `geometry_builds`, `interval_coordinates` (or versioned trajectory vertices and interval midpoint coordinates). Ensure coordinate geometry cannot imply non-null absolute elevation when RL is missing.

**Audit and plots:** `qaqc_checks`, `qaqc_findings`, `qaqc_resolutions`, `figure_registry`, `figure_query_registry`, `figure_export_manifest`, `plot_statistic_snapshots` (only when aggregate snapshots are used), `validation_test_results`.

**Future-only extension contracts** (do not populate as empirical modelling results): `spatial_folds`, `variogram_runs`, `variogram_points`, `model_runs`, `model_predictions`, `model_evaluation_metrics`, `probability_calibration`, `uncertainty_voxels`, `simulation_runs`.

All tables require appropriate primary keys, foreign keys, `NOT NULL`, uniqueness, checks, indices, timestamps, version keys and clear migration paths. Enforce `PRAGMA foreign_keys=ON` on every connection; transactional and idempotent ingestion is mandatory. Keep one active approved version distinguished from archived versions; do not rely on `SELECT *` in published plotting queries. Create stable `v_*` read-only SQL views for plotting with clear query definitions and version provenance.

Do not fabricate synthetic rows just to fill missing tables. Empty future model tables are entirely acceptable.

## Stage A figure and table catalogue — all figures must query SQLite

Implement working SQL query files and Python rendering scripts for every **data-supported** item below; each figure/table includes an ID, descriptive title, data source query, denominator, relevant QC state, version, caption and file manifest entry. Suggested IDs:

**Objective 1**
- `F01`: Collar location map with drill-hole identifiers, coordinates, scale, North orientation and coordinate-system qualification.
- `F02`: Drill-hole length distribution; count and length summaries.
- `F03`: Collar, survey and logging completeness / QA/QC chart and a tabular issues summary.
- `F04`: 3-D colored drill-hole traces and geological interval strips, **relative Z only until RL is validated**; provide static high-resolution views and optional interactive HTML.
- `T01`: Workbook inventory, raw-to-curated records and integrity checks.
- `T02`: Lithological code dictionary and graphitic-evidence label disagreement summary.

**Objective 2 — exploratory, currently feasible portion**
- `F05`: Lithology frequency and logged-metre distribution.
- `F06`: Graphitic (`Sgs`) interval proportion and intersected thickness by hole; distinguish strict indicator from any approved reconciled rule.
- `F07`: Graphitic interval distribution by measured-depth bins and weathering category, where available.
- `F08`: Drill-line and collar plan map colored by graphitic-intersection occurrence or fraction; drill-line assignment must be verified and explicitly versioned.
- `F09`: Representative geological sections through specified drill-line groups with exact projection method and caveats; do not assume continuous geology between holes.
- `T03`: Summary of graphitic domain evidence and uncertainty/ambiguity by hole and drill line.

**Deferred — do not produce fabricated plots:** directional indicator variograms, anisotropy parameters, indicator kriging, XGBoost/RF/hybrid comparisons, confusion matrices, held-out calibration, predictive probability volumes, entropy maps and simulation results. Instead document their required future database tables, query contracts and prerequisite gates in a `DEFERRED_FIGURES.md` catalogue. A future Stage B may enable these once real derived values exist.

Render plots from SQL views or explicit parameterized queries; never read the original Excel directly from the rendering layer. Store each figure's SQL file hash, input dataset version, label-rule version, geometry status, script version/hash, UTC export time, output path and file hash. Figures must be reproducible by figure ID, e.g. `python -m kambale.cli plot --figure F06 --version <approved_version>` (implement the actual available CLI options and document them accurately).

## SpecKit output package — provide complete real files

Generate the following files with full contents; no placeholders, fabricated statistical results or omitted SQL definitions:

1. `01_thesis_scope_and_objective_traceability.md`: Fixed thesis title and objectives exactly as above, Stage A/Stage B scope, objective-to-dataset-to-table-to-figure traceability matrix, scientific claims and prohibited overclaims.
2. `02_workbook_audit_and_data_contract.md`: Workbook sheet/header inventory, raw and curated schemas, data dictionary with units/types/nulls, code mapping, identifier rules, QC checks, graphitic-label decision workflow and source-provenance assumptions.
3. `03_schema.sql`: Executable SQLite DDL, constraints, indices, migrations and justified future-extension contracts; include views/migrations as extra SQL files where warranted.
4. `04_etl_geometry_and_qaqc.md`: Exact ETL stages, hole-to-survey-to-logging joins, conflict handling, trajectory equations and assumptions, conditional geometry validity, versioned outputs and deterministic pipeline commands.
5. `05_sql_plot_contract_and_figure_catalog.md`: Every Stage A figure/table listed above, complete query definitions or references to individually delivered `.sql` files, Python plotting functions, outputs, labels, captions, quality checks and database provenance requirements. Document deferred plots separately.
6. `06_acceptance_tests_and_stop_rules.md`: Executable QA/test acceptance matrix, severity rules, database integrity SQL tests, geometric unit tests, data reconciliation, figure-to-query audit, idempotent reruns, successful and blocked conditions.
7. `07_speckit_agent_kickoff.md`: Dependency-ordered tasks and a copy-ready coding-agent command sequence that initializes official Spec Kit when available, generates `spec.md`, `plan.md`, `tasks.md`, implements and tests the SQLite/Python pipeline, builds only Stage A figures, and produces a final verified handover report.

Also deliver **runnable code**, `pyproject.toml` or locked requirements, CLI entrypoint, SQL migration files, unit/integration tests, the created `.sqlite` file from the supplied workbook, generated Stage A plots (only those that can be supported), rendered thesis-ready tables, `README.md`, `QAQC_REPORT.md`, `FIGURE_MANIFEST.csv` and `DEFERRED_FIGURES.md`. A specification alone is not completion of this assignment.

Suggested repository structure:

```text
kambale-thesis/
  data/raw/                        # unchanged workbook + hash
  data/derived/                    # non-authoritative delivery copies only
  database/kambale_thesis.sqlite   # canonical research database
  migrations/                      # versioned DDL and SQL views
  sql/figures/                     # one reproducible query per figure/table
  src/kambale/                     # ingestion, QC, geology, geometry, figures, CLI
  config/                          # approved/non-approved decision YAML files
  tests/                           # unit, integration, geometry and snapshot tests
  specs/                           # 01–07 completed specifications
  figures/objective_1/
  figures/objective_2/
  tables/
  reports/
  README.md
  pyproject.toml
```

## Acceptance gates and STOP/WARN/DEFER behavior

**STOP the affected step, not necessarily the entire project, when:** source workbook is missing or corrupt; cannot prove join integrity; raw provenance is lost; malformed depth/overlapping intervals would contaminate a figure; CRS ambiguity would invalidate a purported map; relative Z is passed off as real elevation; a plot reads unapproved/disallowed synthetic data; the published source query cannot be recovered; the same data version produces irreproducible results.

**WARN and continue with correctly labeled partial outputs when:** a collar elevation is missing (allow relative-Z section only); an angle interpretation is provisional (allow only prominently qualified geometry); graphitic fields disagree (report each candidate separately); drill-line grouping is unapproved (show plan map but do not claim confirmed lines); some observations lack geological codes; geologic interpretation remains ambiguous.

**DEFER without inventing:** any publication figure or analysis that needs missing RL, a reviewed label definition, external assays, an approved 3-D geometry, fitted variograms, spatial folds, model predictions or a validated uncertainty model.

**Acceptance tests must demonstrate:**
1. Original workbook SHA-256 logged; raw source preserved.
2. Counts and fields recomputed from the actual workbook and reconciled to audit tables; discrepancies explained, not rewritten to match prior numbers.
3. Every curated interval joins to a valid hole or is quarantined and reported.
4. Depth interval geometry is physically plausible with correct units, and all associated assumptions are explicit.
5. SQLite `foreign_key_check` and `integrity_check` succeed.
6. Two identical ETL reruns do not create duplicate records or silently change approved data; versioning is deterministic.
7. A null collar RL never yields an ostensibly measured `z_absolute_m`.
8. Label-source disagreements can be fully reconstructed from the database.
9. Each Stage A figure is regenerated solely from SQLite under a known dataset version; figure registry and hashes match output files.
10. Test suite succeeds; failures/limitations listed plainly in handover. Do not claim success for unrun tests.

## Official Spec Kit initialization and coding-agent execution

Do not use unverified `npm install -g @github/spec-kit` or `speckit init` commands. The current official Spec Kit CLI is **`specify`**, typically installed from the `specify-cli` package. If `specify` is already available, verify `specify version`; otherwise, if `uv` and network access are available, install using `uv tool install specify-cli` (or a pinned verified official release). Initialize in the project root using `specify init --here --integration claude --non-interactive` if supported by the installed version. Confirm existing files are protected before initialization and do not force overwrite without a backup. Use `.specify/` and official agent commands; do not pretend a handmade `.speckit/` directory is equivalent to a successful official initialization. If official installation is blocked, record this explicitly and continue with the complete platform-neutral `specs/`, `tasks.md`, Python code and SQL pipeline.

Follow the official workflow in the coding agent: establish project principles and fixed thesis constraints, specify requirements, plan architecture, generate atomic dependency-ordered tasks, inspect for cross-artifact inconsistency, then implement/test stage by stage. Commit or checkpoint validated changes when version control is available.

**Implementation order:** workbook audit -> source hashing/raw ingestion -> schema and migrations -> relational/QA/QC -> geologic codes and candidate labels -> coordinates/geometry with explicit status -> plot-ready SQL views -> Stage A figures/tables -> reproducibility tests -> final handover.

Do not start model training merely because some Stage B tables exist. Never claim that an attractive section proves a geological contact, that graphitic lithology supplies graphite grade, or that plotted relative depth is surveyed elevation. Avoid arbitrary geological assumptions; represent uncertainties as review-required decisions while still completing every unaffected task.

## Final response format required from the coding agent

Report: (1) executable files created; (2) database location and complete table/view list; (3) source and curated record counts with qualification; (4) data problems and geological decisions still pending; (5) exact command to rerun ETL; (6) figure and table inventory with paths and source queries; (7) automated tests actually run and their results; (8) a precise list of deferred model-dependent objectives/figures and prerequisites. Distinguish **COMPLETED**, **PROVISIONAL**, **BLOCKED**, **DEFERRED**, and **FAILED** results.

The immediate success criterion is **a functioning, auditable Kambale SQLite database plus reproducible thesis-appropriate preliminary figures derived from actual observations**. It is not manuscript publication, speculative mineral-resource estimation, or a premature claim that hybrid modelling improves performance.

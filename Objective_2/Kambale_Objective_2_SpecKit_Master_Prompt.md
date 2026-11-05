# SPEC KIT CODING-AGENT MASTER PROMPT — OBJECTIVE 2

## Fixed scientific charter — mandatory for every stage

**Thesis title (unchanged):** *Hybrid Machine Learning–Indicator Geostatistical Modelling for Spatially Validated Three-Dimensional Prediction and Uncertainty Characterization of Graphitic Domains at the Kambale Graphite Deposit, Ghana*

**Synopsis objectives (copy exactly; do not rewrite, merge, amend or renumber):**

1. To construct and quality-control a three-dimensional drill-hole database and define graphitic domains at the Kambale Graphite Deposit.
2. To characterize the spatial distribution, geological controls, and continuity of graphitic domains using exploratory spatial analysis and indicator variography.
3. To develop and spatially validate indicator-geostatistical, machine-learning, and hybrid models for predicting graphitic-domain occurrence.
4. To evaluate the predictive performance of the developed models using independent spatial validation and probability-based metrics.
5. To quantify and visualize three-dimensional uncertainty in graphitic-domain occurrence and identify areas of high confidence and high uncertainty.

This is an **MSc Geological Engineering thesis implementation**, not a journal-submission drafting exercise. All conclusions must come from the Kambale RAB workbook and traceable derived analyses. No graphite-grade prediction, TGC, tonnage, reserves, or resource estimation; this data source does not contain graphite assays. Do not fabricate elevations, geological contacts, spatial correlations, model performances, or simulations.

### Source facts and prerequisite uncertainty

- Workbook: `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx`, with `Collars`, `Surveys`, `Logging`, `Logging Legend`, and reference sheets. Supporting documents: `ThesisDesign.docx`, `ReadingGuide.docx`, where available.
- Earlier inspection described 71 holes, 1,910 one-metre logged intervals, and approximately 529 intervals with `rock_type1 = Sgs`; these are **audit cross-checks only**, never hardcoded truths.
- Graphitic classification might depend on `rock_type1`, `alt_min1` / other mineral fields, and geological comments. They sometimes disagree. The agent must use an **approved, versioned label rule**, and preserve unknown/ambiguous records rather than force classifications.
- Collar RL/elevation is missing in the supplied workbook. Only approved, source-documented absolute elevation may support a georeferenced 3-D claim. Relative coordinates and plots remain **PROVISIONAL** and must be labelled explicitly. Check actual coordinate columns and CRS, survey conventions and azimuth/dip semantics rather than guessing.
- Drill-line groups have been described as five nominal lines; independently verify their definition from the master database. A provisional drill-line grouping is not an approved spatial split.

### Five distinct but connected SQLite databases

| Objective | Database (suggested name) | Authority |
|---|---|---|
| 1 | `database/kambale_thesis.sqlite` | **Authoritative raw/curated geology, source provenance, labels, coordinates and QC**; preserve the pre-existing Stage A path if already in use. |
| 2 | `database/kambale_obj2_spatial.sqlite` | Authoritative **derived spatial summaries, variograms, geological continuity diagnostics**. |
| 3 | `database/kambale_obj3_models.sqlite` | Authoritative **fold-specific modelling, predictions, hyperparameters and model artifacts**. |
| 4 | `database/kambale_obj4_validation.sqlite` | Authoritative **evaluation metrics, calibrations, diagnostics and comparison decisions**. |
| 5 | `database/kambale_obj5_uncertainty.sqlite` | Authoritative **prediction grid, simulations, entropy, confidence rules and uncertainty volumes**. |

**CRITICAL:** These are not five independent copies of the original geological observations. Database 1 is the only editable authority for source/curated facts and approved geology. Each later objective reads prior databases **read-only**, imports only necessary versioned analytical snapshots or traceable references, and owns only its new derived results. Maintain an immutable `source_receipts` record with: upstream database logical name and actual path; immutable snapshot SHA-256 or reproducible dataset-content hash; origin dataset ID; label rule ID; geometry version; CRS and vertical datum status; selection-query hash; upstream run/decision IDs; imported row counts, ordered-identifier digest; import UTC time and code commit. Verify receipts before every import and every publication export. SQLite cannot enforce `FOREIGN KEY` constraints across attached database files: use database-local FKs and explicit cross-database integrity tests (ID/key/cardinality/hash verification), never pretend the engine enforces cross-file FKs.

Use transactional, idempotent writes, local schema migrations, robust `PRAGMA foreign_keys=ON` connections, typed nulls, unique constraints, output hashes, and a full export manifest. The original Excel is immutable. All output tables/figures use verified database queries. Temporary calculations in Python are allowed, but final scientifically reported results must be committed to the appropriate objective database or be recoverable from versioned, hashed query and code artifacts. SQL files and decision YAMLs are version-controlled; changing an upstream version marks downstream runs **STALE**, not silently valid.

**Dependency graph:** O1 -> O2 -> O3 -> O4 -> O5, with read-only O1 inputs to O3/O4/O5 where explicitly necessary. O3 produces held-out predictions under a fixed split plan; O4 performs the comparative evaluation. O5 uses the model-selection decision from O4 and an O3-documented final refit. **No test-fold leakage**. Software: Python 3.11+, standard `sqlite3`/SQLAlchemy, scientific libraries as appropriate, Matplotlib and PyVista/Plotly for plots. QGIS, R, proprietary software, and a second manually maintained spreadsheet are **not requirements**.

### Workspace and provenance conventions

Use `specs/objective_2/`, `sql/objective_2/`, `src/kambale/objective_2/`, `config/objective_2/`, `tests/objective_2/`, `figures/objective_2/`, `tables/objective_2/`, `reports/objective_2/`; **one database file per objective**, plus immutable input receipts. Names can be adapted to existing code, but document an unambiguous mapping. Store versions of source files, schema, Python environment, dependencies, Git commit (if available), random seeds, SQL definitions, configuration, training partitions where relevant, and every exported figure/table. For all output figures save SVG or PDF and high-resolution PNG; embedded captions must report units, sample support, fold/geometry status and limitations.

---

# OBJECTIVE 2 — SPATIAL DISTRIBUTION, GEOLOGICAL CONTROLS AND INDICATOR VARIOGRAPHY

## Scope and research question

**Approved Objective 2 (verbatim):** To characterize the spatial distribution, geological controls, and continuity of graphitic domains using exploratory spatial analysis and indicator variography.

Research question: *What spatial patterns and directions of continuity, if any, are supportable from the approved graphitic-domain indicator and the actual RAB drill-hole configuration?* This stage is primarily **descriptive and diagnostic**. It must not fit graphitic-occurrence prediction models or claim mapped unobserved lithology as observed truth. Its main output is a geologically interrogated, versioned continuity model for Objective 3.

**Read-only inputs:** Objective 1 SQLite geological database and QA/approval reports. Prefer a validated geometry source, a formally approved label rule, and approved drill-line grouping. When absolute RL and/or CRS is missing, allow explicitly provisional local/relative spatial exploration but STOP georeferenced absolute-elevation products and technically invalid cross-hole directional analyses. Confirm true units and coordinates; do not create arbitrary east/north coordinates. The agent must inspect real upstream tables and build a tested compatibility adapter if table names differ.

**Output database:** `database/kambale_obj2_spatial.sqlite`. Do not edit O1 or copy all original logging rows into the O2 database as a second canonical source. Store stable keys and the smallest reproducible analytical snapshot needed for variogram computation, with complete source receipts.

## Required analytical sequence

1. **Input integrity gate.** Check source hash/version, approved interval label rule, valid hole joins, physical depth support, horizontal CRS and units, drill-line grouping, angle/relative-Z status. Exclude unresolved classification from binary target by explicit rule; report exclusion counts by hole and line. Make case-control/interval weighting choices explicit.
2. **Geological occurrence summaries.** Derive graphitic proportion and summed apparent drilled thickness by hole and line, number of distinct graphitic intersections, interval-length-weighted fractions, distributions versus measured depth and weathering. Report that intersected metreage is along-hole **apparent thickness**, not true stratigraphic thickness. If log support is uniformly 1 m, verify rather than assume.
3. **Geological sections and 3-D observation displays.** Produce projected sections with actual collar, dip, azimuth, line orientation and projection offset. Do not draw inferred contacts as observed. If elevation missing, label relative depth, not metres above sea level. Expose geologic assumptions of lenses, multiple structures and weathering; classify interpretations as conceptual.
4. **Indicator frequency and clustering.** For approved binary indicator `I(s)`, record global and per-group prevalence `p`, sample support, effective spatial sampling diagnostics, spacing distributions and positive-class coverage. Distinguish within-hole, between-hole on-line and between-line sample pairs.
5. **Experimental variography.** For predeclared direction/lag tolerance parameters calculate `gamma(h)=1/(2 N(h)) * sum_{(i,j) in pairs(h)}[I(si)-I(sj)]^2`. Compute lag-bin pair counts, independent-hole-pair support, frequency of equal-class/different-class pairs, directional coverage and empirical pair distances. Use geometric vector lags (not measured-depth difference alone), include omnidirectional and candidate geological strike, dip and cross-strike directions **only where geometry supports them**. Exclude exact duplicate coordinates/self-pairs. Avoid letting thousands of adjacent samples in a single hole determine purported between-hole range; report within-hole and cross-hole structure separately, with optional pair-declustering/down-weighting.
6. **Directional anisotropy.** Compare directional variograms only for supported directions and lag ranges; propose strike/dip anisotropy only if geological sections and spatial pair coverage agree. A different fitted range in two poorly supported directions is not proof of geological anisotropy.
7. **Model fitting and diagnostics.** Fit parsimonious spherical and/or exponential indicator semivariogram structures, possibly an isotropic baseline, by pre-specified constrained weighted least squares. Document nugget, structured sill, total sill, principal ranges, fit objective and sample-bin support, positive semidefiniteness admissibility of the covariance model, and parameter uncertainty/stability. Respect the binary marginal variance `p(1-p)` as a physical diagnostic, not a rigid finite-sample equality constraint; explain departures. Flag unstable/underdetermined fits, check leave-whole-hole/leave-line stability where feasible (without claiming prediction CV). If unsupported, output `VARIOGRAM_NOT_IDENTIFIABLE` and a fallback/handoff decision, not invented parameters.
8. **Sensitivity.** Compare strict `Sgs` and approved reconciled labels only if both authorized; alternative lag widths and angular tolerances; inclusive vs excluding along-hole pairs; hole-length weighting; limited support exclusion; tentative geologic orientation, relative-Z vs validated RL where applicable.
9. **Persist and export.** Commit all source receipts, descriptives, experimental points, fitted parameters, pair support, diagnostics, sensitivities and figure-level SQL extracts. Produce one locked **variogram handoff registry** for O3 with selected model ID and status (`APPROVED`, `PROVISIONAL`, `REJECTED`, `NOT_IDENTIFIABLE`). **Important anti-leakage:** A variogram fitted using *all* holes is exploratory only; O3 must refit or select its variogram using only training data inside every outer CV fold. Never supply an all-data fitted variogram to a held-out prediction run as if it were leakage-free.

## Suggested Python stack

`numpy`, `pandas`, `scipy`, `sqlite3`/`SQLAlchemy`, `scikit-gstat` (indicator experimental variograms and directional support; independently verify output), `gstools` (model covariance/variogram fits), `matplotlib`, `pyvista`/`plotly`; optional `shapely` and `geopandas` for actual coordinate/map geometry. Implement own audited pair-count diagnostics because black-box variogram curves can mask sparse between-hole support. Do not use QGIS.

## Required Objective 2 SQLite schema

Create data dictionary and complete DDL for at least: `source_receipts`, `stage_runs`, `analysis_observations` (stable upstream `interval_id`, `hole_id`, `line_id`, label, class-resolution status, X/Y/Z with geometry-status, support length, upstream version), `hole_occurrence_summaries`, `line_occurrence_summaries`, `depth_lithology_summaries`, `weathering_cross_tabs`, `spatial_support_statistics`, `pair_sampling_diagnostics`, `direction_registry`, `variogram_experiments`, `variogram_lag_bins`, `variogram_fits`, `variogram_fit_parameters`, `anisotropy_diagnostics`, `sensitivity_runs`, `geological_section_registry`, `continuity_handoff_decisions`, `figure_registry`, `figure_query_registry`, `table_registry`, `export_manifests`, `gate_results`. All fit IDs must reference the actual experimental variogram. Store model parameter units, explicit azimuth/inclination convention, lag vectors and tolerance metadata, and sample/pair support. No dummy fitted results.

### Required figures and tables (all from Objective 2 SQLite)

- `O2-F01`: Drill-hole footprint, approved line groups, and location-coded graphitic intersections; label coordinate reference system status.
- `O2-F02`: Graphitic along-hole interval metres and graphitic fraction by hole/line, with distinct denominators.
- `O2-F03`: Distribution of binary graphitic occurrence by logged depth/stratigraphy/weathering; state available variables.
- `O2-F04`: Representative geological cross-sections and/or observed hole strips; explicitly distinguish observed log from inferred between-hole interpolation.
- `O2-F05`: Spatial pair-distance and direction support diagrams, including cross-hole versus within-hole counts.
- `O2-F06`: Omnidirectional indicator semivariogram, lag counts, fitted candidate curves and supported ranges.
- `O2-F07`: Directional indicator variograms with azimuth/angle tolerance, measured pairs and explicit warnings where underpowered.
- `O2-F08`: Variogram sensitivity plot across hole-weighting, candidate label and lag rules; skip absent feasible alternatives.
- `O2-T01`: Hole/line geological summary and support.
- `O2-T02`: Indicator class prevalence, ambiguity and missingness by line.
- `O2-T03`: Variogram parameter fitting report (nugget/sill/ranges/objective/uncertainty/approval state).
- `O2-T04`: Approved spatial continuity handoff contract and unresolved geological questions.

**No fabricated F06/F07/F08 when pair counts or geometry are inadequate.** Produce a specifically named `NOT_SUPPORTED` figure-catalogue entry with reasons. Make each deliverable reproducible by exact run/SQL/plot command.

## Acceptance, failure rules and handoff

- **STOP:** source receipt mismatch; incompatible coordinate units; label rule missing; invalid or unreviewed geometry used as approved; nonpositive lag bins; self-pairs mistaken for pairs; fitted covariance mathematically invalid; georeferenced cross-sections without real RL; an O3-ready variogram contaminated by held-out folds.
- **WARN:** uneven sampling density, weak cross-hole support, geology not constraining strike, sparse minority class, relative-Z only, empirically distinct variograms with too few pairs to establish anisotropy.
- **SKIP:** directional candidate with fewer than configurable predeclared independent hole pairs or insufficient bins. Record thresholds and sensitivity, not arbitrary unrecorded post-hoc decisions.
- **DOWNGRADE:** unsupported directional anisotropy, unstable fit or unapproved label becomes exploratory, never an approved O3 spatial-continuity model.
- **Pass conditions:** receipts match; selected label and geometry statuses clear; all descriptive denominators reconstructible; empirical pair counts auditable; all fitted variogram params traceable and admissible; all figure/table queries versioned; O3 handoff indicates whether spatial continuity is supported. Run a unit test on a synthetic *unit-test-only* indicator pattern; keep it out of empirical study exports.

**Handoff to O3:** Approved, versioned candidate variogram family, parameter search ranges/orientation constraints, scientifically justified lag settings and spatial support diagnostics; **not** a full-data fitted parameter vector to reuse in test folds. If continuity cannot be identified, handoff explicitly allows baseline/ML comparisons but blocks unsupported geostatistical claims.

## Mandatory seven-file SpecKit specification package for Objective 2

The coding agent MUST create full, executable or fully specified content for **each** of these files, not summaries or boilerplate. File names are objective-local (`specs/objective_2/...`). Every document must identify exact inputs/outputs and trace its requirements to Objective 2, while preserving the five synopsis objectives unchanged.

1. **`01_thesis_scope_review_and_claims.md`** — scientific purpose, detailed objective traceability, critical MSc-examiner challenges, defensible claims vs prohibited claims, dependency and prior-stage acceptance gates; distinguish observation, interpretation, prediction and uncertainty.
2. **`02_methods_and_mathematical_framing.md`** — full methods and relevant equations, estimands/targets, parameter constraints, assumptions, baselines, competing designs, sensitivity studies, and interpretation requirements; do not invent numerical results.
3. **`03_acceptance_and_failure_gates.md`** — implementable STOP/WARN/SKIP/DOWNGRADE conditions, database SQL assertions and Python tests with deterministic output statuses. A scientific gate failure must be visible in exports and may block a particular figure or analysis without needlessly stopping unaffected work.
4. **`04_data_contract_and_io.md`** — exact upstream database and tables/SQL-view contracts (discover actual Objective 1 schema rather than assume names), column types/units/null semantics, keys, receipts, downstream output schemas, command-line interfaces and versioning. Document any compatibility adapter; never invent available fields.
5. **`05_schema.sql`** — executable, objective-specific SQLite DDL with primary/foreign keys, indexes, uniqueness, checks, UTC run metadata and import receipts, local migrations and views. Include SQL files for each thesis figure and table; persist plot-ready aggregates or their reproducible parameterized SQL-query definitions.
6. **`06_python_analysis_and_plotting.md`** — complete Python implementation plan and CLI, packages/versions, exact figure and table catalogue, SQL extracts, deterministic rendering and data lineage, test cases, plus explicit path examples. Deliver working Python code in addition to this plan.
7. **`07_speckit_agent_kickoff.md`** — copy-ready, dependency-ordered execution prompt for a coding agent (Claude Code, Cursor, etc.), official Spec Kit init and task generation, real command invocations, evidence required to mark tasks done, final handoff to the next objective.

Also deliver runnable `src/` modules, `.sql` migrations and figure SQL, `pyproject.toml` or dependency lock updates, `pytest` tests, populated objective-specific `.sqlite` from **actual upstream verified data**, figure/table files wherever scientific gates permit, `README.md`, `RUN_REPORT.md`, `DATA_LINEAGE.json` (or equivalent database tables), `FIGURE_MANIFEST.csv`, and `BLOCKED_OR_DEFERRED.md`. A specification without functioning code and database is incomplete.

### Official Spec Kit protocol

The CLI is `specify`, from the officially maintained `specify-cli` distribution; it is **not** an assumed `speckit` CLI. Verify in the live environment with `specify version`; if absent, use the verified official install method (`uv tool install specify-cli` where `uv`/network are available), check actual options via `specify init --help`, then initialize safely with `specify init --here --integration claude --non-interactive` or an equivalent command for the actual agent. Do not overwrite an existing project or force merge without backup. Follow the installed official integration's `constitution -> specify -> clarify/plan -> tasks -> analyze -> implement -> converge` sequence. If official scaffolding is unavailable, document why, retain working local `specs/objective_2/` documents and a dependency-ordered `tasks.md`, and continue implementing the code. Never claim successful installation if it was not executed.

### Mandatory completion report

Report exactly: (a) generated specification/code/SQL files; (b) objective database path, schema version, table row counts and upstream receipt hashes; (c) verification of predecessor acceptance; (d) CLI commands to rerun all stages; (e) figures/tables with SQL and hash manifest; (f) tests **actually run** and passed/failed; (g) geological/methodological assumptions and limitations; (h) STOP/WARN/SKIP records and deferred outputs; (i) exact handoff contract for the next objective. No hallucinated results, no unsupported claims, no unverified count or performance statistics. Reproducibility and truthful failure reporting outrank producing a visually attractive model.

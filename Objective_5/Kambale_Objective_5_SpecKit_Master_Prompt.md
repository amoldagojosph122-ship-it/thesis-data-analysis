# SPEC KIT CODING-AGENT MASTER PROMPT — OBJECTIVE 5

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

Use `specs/objective_5/`, `sql/objective_5/`, `src/kambale/objective_5/`, `config/objective_5/`, `tests/objective_5/`, `figures/objective_5/`, `tables/objective_5/`, `reports/objective_5/`; **one database file per objective**, plus immutable input receipts. Names can be adapted to existing code, but document an unambiguous mapping. Store versions of source files, schema, Python environment, dependencies, Git commit (if available), random seeds, SQL definitions, configuration, training partitions where relevant, and every exported figure/table. For all output figures save SVG or PDF and high-resolution PNG; embedded captions must report units, sample support, fold/geometry status and limitations.

---

# OBJECTIVE 5 — THREE-DIMENSIONAL GRAPHITIC OCCURRENCE UNCERTAINTY

## Scope and research question

**Approved Objective 5 (verbatim):** To quantify and visualize three-dimensional uncertainty in graphitic-domain occurrence and identify areas of high confidence and high uncertainty.

Research question: *Where does the approved RAB drilling and validated predictive model support reliable probabilities of graphitic-domain occurrence, where is the interpretation ambiguous, and where is spatial support insufficient?* The stage produces **3-D probability and uncertainty** visualizations, geological sections and support masks; not graphite grade or reserves.

**Read-only inputs:** O1 approved geology/coordinates and input observation support; O2 spatial-continuity diagnostics and geological interpretations; O3 selected model's **final refit** artifact and (where allowed) conditional simulation settings; O4 locked model-selection/calibration and limitation receipt. The selected model must come from O4. If O4 is inconclusive, show model-ensemble disagreement as an **explicit sensitivity comparison** rather than arbitrarily declaring a winner. Output `database/kambale_obj5_uncertainty.sqlite`.

## Core definitions and geometry gates

- For each justified prediction voxel center `s`, store `p(s)=Pr[graphitic occurrence at s]` and a status (approved, provisional, out-of-support, unpredicted). The target must use the same geological label definition approved in O1 and tested in O4.
- **Absolute Z policy:** Missing collar RL makes an absolute georeferenced 3-D volume scientifically unjustifiable. If no surveyed/DEM-based, datumed elevations have been approved, produce **explicitly provisional depth-referenced or relative-Z visualizations only**, subject to known dip assumptions; do not present an apparent aligned local grid as true ore-body geometry. The geographic alignment and topographic effect must be reviewed, particularly between holes. `z_absolute_m` must stay null until defensible evidence exists.
- Grid extents and voxel dimensions require explicit origin, coordinate reference system, rotation, top/base masks, variable support, resolution rationale and data-to-voxel distance. A 5-m voxel is a discretization choice, not proof of 5-m geological resolution. Use an approved drilling envelope, distance-to-observation threshold and optionally geologically constrained mask; flag unsupported areas instead of filling the entire deposit with precise-looking colors.
- **Entropy:** Use binary Shannon entropy in bits, `H_2(p)=-p log2(p)-(1-p) log2(1-p)`, define `0 log 0 = 0`, so 0 at `p=0 or 1` and 1 bit at `p=0.5`. Entropy measures *ambiguity of the predicted Bernoulli class*, **not automatically epistemic or calibrated geological uncertainty**. A wrong overconfident model can have low entropy.
- **Confidence versus support:** Build calibrated-confidence categories only if O4 probability calibration is adequate in analogous support regions. Separately expose `support_status` (e.g. inside hull / distance to nearest hole / count of nearby distinct holes / interpolation versus extrapolation), `model_status`, uncertainty due to label rules/variogram choices, and simulation or model disagreement. No automatic claim that `p≈0` or `p≈1` is reliable if spatial support is weak.

## Implementation sequence

1. **Lock prerequisites and no-leakage evidence.** Verify O1/O2/O3/O4 receipt hashes and target/geometry versions; require O4 decision and matching final full-data O3 fit. Record whether this is a spatially validated model *approach* refitted on all eligible training data, not a directly validated voxel-by-voxel geological truth.
2. **Declare prediction domain and grid.** Digitize or compute a conservative sampling envelope; record voxel center coordinates, CRS, Z semantics, block dimensions, resolution and geological/truncation masks. If absolute RL remains absent, use qualified relative-only analysis; create an `APPROVED_3D_GEOGRAPHIC_MODEL` output only when actual vertical datum and approved geometry exist.
3. **Evaluate selected final model** at voxel locations with permitted predictors, persist raw/approved probabilities, calibration pipeline identifier, model artifact hash, numerical and applicability diagnostics. Never infer unseen geological feature values from observed target labels without training-only conditioning and transparent modelling; avoid feature leakage in projection.
4. **Compute core uncertainty surfaces.** Persist entropy, probability margins/distance from 0.5, nearest-observation distance, count of unique nearby boreholes, anisotropic neighbourhood/support flags, class-evidence ambiguity influence where estimable, and prediction-support category. `p=0` or `1` remain valid but flagged as potential false certainty outside support.
5. **Conditional simulation (advanced, optional, only scientifically admissible).** If indicator spatial covariance and conditioning support allow, create multiple distinct conditional 3-D indicator realizations that honor geological indicator observations (subject to explicit conditioning assumptions). Use a validated sequential indicator simulation approach **only if package supports actual conditional binary/categorical 3-D simulation**, not continuous Gaussian simulation relabelled SIS. If using ML probabilities as local varying mean, fully specify the conditional simulation mathematics, non-stationary local mean, covariance/residual consistency and calibration checks. Verify realizations reproduce approved hard observations at conditioning locations and ensemble probability agrees with observed frequencies/target probability under appropriate conditions. Save seeds, method, model version, stored simulations (potentially compressed artifact with hash, grid mapping, and SQLite manifests), and convergence/sensitivity to number of realizations. If these assumptions cannot be met, mark `SIS_NOT_SUPPORTED` and deliver entropy/support analysis instead of fabricated simulation.
6. **Boundary and volumetric uncertainty.** Map probabilities and uncertainty around inferred domain boundaries under declared probability thresholds; quantify **model-implied graphitic-class voxel count / geometric volume sensitivity only** if geometry/extent is validated and numerical interpretation warranted; no mineral resources, grade or economically recoverable tonnes. If RL unverified, avoid reporting georeferenced volume estimates. Connectivity claims from realizations require formal connectivity and sufficient simulations; otherwise describe as exploratory.
7. **Sensitivity and model disagreement.** Evaluate validated alternative label definitions only with separate O3 models, probability thresholds, grid spacing, neighbourhood/support parameters, variogram families and simulation seed stability. Do not switch to alternative candidates based on attractive maps. Preserve O4 selected model as primary.
8. **Visualize and export.** Generate PyVista 3-D drill-hole overlays, observed geological intervals, probability voxels, thresholded domains and entropy/support volumes, plus cross-sections, plan slices and static 300-dpi/SVG/PDF figures. An interactive HTML output may supplement, but every thesis figure must be accessible as static reproducible output from O5 SQLite. Visible legends must separate probability from confidence/support status; no photorealistic interpolation pretending to be drilled geology.
9. **Decision-oriented interpretation.** Identify geographic areas with (a) good support and clear calibrated prediction, (b) good support but ambiguous probability, (c) poor support regardless of extreme probability. Where appropriate identify *candidate* infill-drilling areas based on formal uncertainty + logistical/geological feasibility; do not claim their effectiveness was field-verified.

## Objective 5 SQLite schema

Implement complete DDL for: `source_receipts`, `stage_runs`, `selected_model_receipts`, `geometry_authorizations`, `prediction_grid_versions`, `grid_voxels` (voxel ID, XYZ with Z semantics, cell dimensions and transform, support masks), `voxel_predictors`, `voxel_predictions` (probability, model ID, calibration ID), `voxel_support_metrics`, `voxel_entropy`, `confidence_rule_registry`, `voxel_confidence_classes`, `boundary_diagnostics`, `simulation_run_registry`, `simulation_artifact_registry`, `simulation_summary_voxels`, `simulation_conditioning_checks`, `sensitivity_runs`, `model_disagreement`, `geological_interpretation_annotations`, `figure_registry`, `figure_sql_registry`, `table_registry`, `export_manifests`, `gate_results`. Store compressed spatial array artifacts on disk only with SHA-256, shape, dtype, coordinate/grid version and retrieval path anchored in SQLite. Never store several giant simulation arrays in a loosely managed untracked folder; SQLite remains the authority for their provenance and validated identities.

## Required Objective 5 figures and tables

- `O5-F01`: Observed interval logs overlaid on approved/provisional georeferenced or relative-Z probability slices (with prominent geometry status).
- `O5-F02`: Three-dimensional graphitic occurrence probability volume, with masked outside-support voxels.
- `O5-F03`: Entropy volume with an explicit 0–1 bit legend and a note on prediction overconfidence.
- `O5-F04`: Distance-to-drill-hole and distinct-well support volume; show sparse/unobserved regions independently of entropy.
- `O5-F05`: Geological sections comparing observed drilled indicators and probabilities; no implied observed contacts between drill holes.
- `O5-F06`: Confidence/support classification panels (high/medium/low *when justified*; otherwise uncertainty ambiguity plus support).
- `O5-F07`: Conditional indicator simulation realizations and aggregate probability, **only if SIS validation gates pass**; otherwise show an explicit deferred item rather than fake realizations.
- `O5-F08`: Sensitivity maps or difference maps under label/grid/threshold/candidate modelling choices with full support caveats.
- `O5-T01`: Prediction grid geometry, resolution and data-envelope report.
- `O5-T02`: Probability, entropy and spatial-support categories by volumetric cells, with no grade/resource inference.
- `O5-T03`: Calibration provenance, confidence categorization and limitations.
- `O5-T04`: Simulation conditioning, convergence and sensitivity test results (if executed).
- `O5-T05`: Geological interpretation and potential infill drilling information gaps, clearly qualified.

## Acceptance and failure rules

- **STOP:** mismatched O1–O4 receipts; model not selected by O4 or not final-refitted with matching configuration; target leaks into voxel predictor; invalid probabilities; absolute elevation fabricated; voxel support/mask omitted; 3-D geological volume asserted without verified collar RL; fake SIS or realizations that do not condition on data.
- **WARN:** weak O4 calibration, domain drift, high uncertainty at domain boundaries, sparse conditioning holes, high extrapolation, ambiguous labels, uncertain variogram parameters, relative-Z use, high model disagreement.
- **SKIP:** SIS if training variogram/geometry/conditioning support insufficient; volume calculation if no defensible 3-D geometry; connectivity if insufficient realizations; high-confidence classifications if probability calibration has failed.
- **DOWNGRADE:** entropy-only display to *probability ambiguity* when epistemic uncertainty is unmeasured; provisional depth-referenced model to descriptive exploratory status, never a validated georeferenced 3-D ore-body map.
- **Pass:** exact handoff hashes; grid masks correctly implemented; entropy unit tests for p=0,0.5,1; verified interpolation masks; plotting reruns deterministic; calibrated classifier status accurate; simulation conditioning tests actually run if simulation claimed; all figures and tables grounded in SQLite.

Packages: `numpy`, `pandas`, `sqlite3`, `scipy`, `pyvista`, `plotly`, `matplotlib`, `gstools`/`geostatspy` or a separately validated SIS implementation; `pytest` for tests. For volumetric artifacts use carefully versioned `npz` or Zarr only as hashed binary payloads indexed by SQLite; do not use these artifact files as competing authoritative metadata.

**Final MSc handoff:** Archive all five objective databases, read-only source receipts, schema/figure manifests, environment lockfile, tests, geometry/label approval states, limits of claim and a thesis-ready figure/table inventory grouped by the exact five approved objectives. This stage completes the modelling workflow only to the extent the scientific gates passed; honestly report provisional, unsupported and missing outputs.

## Mandatory seven-file SpecKit specification package for Objective 5

The coding agent MUST create full, executable or fully specified content for **each** of these files, not summaries or boilerplate. File names are objective-local (`specs/objective_5/...`). Every document must identify exact inputs/outputs and trace its requirements to Objective 5, while preserving the five synopsis objectives unchanged.

1. **`01_thesis_scope_review_and_claims.md`** — scientific purpose, detailed objective traceability, critical MSc-examiner challenges, defensible claims vs prohibited claims, dependency and prior-stage acceptance gates; distinguish observation, interpretation, prediction and uncertainty.
2. **`02_methods_and_mathematical_framing.md`** — full methods and relevant equations, estimands/targets, parameter constraints, assumptions, baselines, competing designs, sensitivity studies, and interpretation requirements; do not invent numerical results.
3. **`03_acceptance_and_failure_gates.md`** — implementable STOP/WARN/SKIP/DOWNGRADE conditions, database SQL assertions and Python tests with deterministic output statuses. A scientific gate failure must be visible in exports and may block a particular figure or analysis without needlessly stopping unaffected work.
4. **`04_data_contract_and_io.md`** — exact upstream database and tables/SQL-view contracts (discover actual Objective 1 schema rather than assume names), column types/units/null semantics, keys, receipts, downstream output schemas, command-line interfaces and versioning. Document any compatibility adapter; never invent available fields.
5. **`05_schema.sql`** — executable, objective-specific SQLite DDL with primary/foreign keys, indexes, uniqueness, checks, UTC run metadata and import receipts, local migrations and views. Include SQL files for each thesis figure and table; persist plot-ready aggregates or their reproducible parameterized SQL-query definitions.
6. **`06_python_analysis_and_plotting.md`** — complete Python implementation plan and CLI, packages/versions, exact figure and table catalogue, SQL extracts, deterministic rendering and data lineage, test cases, plus explicit path examples. Deliver working Python code in addition to this plan.
7. **`07_speckit_agent_kickoff.md`** — copy-ready, dependency-ordered execution prompt for a coding agent (Claude Code, Cursor, etc.), official Spec Kit init and task generation, real command invocations, evidence required to mark tasks done, final handoff to the next objective.

Also deliver runnable `src/` modules, `.sql` migrations and figure SQL, `pyproject.toml` or dependency lock updates, `pytest` tests, populated objective-specific `.sqlite` from **actual upstream verified data**, figure/table files wherever scientific gates permit, `README.md`, `RUN_REPORT.md`, `DATA_LINEAGE.json` (or equivalent database tables), `FIGURE_MANIFEST.csv`, and `BLOCKED_OR_DEFERRED.md`. A specification without functioning code and database is incomplete.

### Official Spec Kit protocol

The CLI is `specify`, from the officially maintained `specify-cli` distribution; it is **not** an assumed `speckit` CLI. Verify in the live environment with `specify version`; if absent, use the verified official install method (`uv tool install specify-cli` where `uv`/network are available), check actual options via `specify init --help`, then initialize safely with `specify init --here --integration claude --non-interactive` or an equivalent command for the actual agent. Do not overwrite an existing project or force merge without backup. Follow the installed official integration's `constitution -> specify -> clarify/plan -> tasks -> analyze -> implement -> converge` sequence. If official scaffolding is unavailable, document why, retain working local `specs/objective_5/` documents and a dependency-ordered `tasks.md`, and continue implementing the code. Never claim successful installation if it was not executed.

### Mandatory completion report

Report exactly: (a) generated specification/code/SQL files; (b) objective database path, schema version, table row counts and upstream receipt hashes; (c) verification of predecessor acceptance; (d) CLI commands to rerun all stages; (e) figures/tables with SQL and hash manifest; (f) tests **actually run** and passed/failed; (g) geological/methodological assumptions and limitations; (h) STOP/WARN/SKIP records and deferred outputs; (i) exact handoff contract for the next objective. No hallucinated results, no unsupported claims, no unverified count or performance statistics. Reproducibility and truthful failure reporting outrank producing a visually attractive model.

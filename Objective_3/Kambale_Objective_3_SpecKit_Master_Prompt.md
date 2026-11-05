# SPEC KIT CODING-AGENT MASTER PROMPT — OBJECTIVE 3

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

Use `specs/objective_3/`, `sql/objective_3/`, `src/kambale/objective_3/`, `config/objective_3/`, `tests/objective_3/`, `figures/objective_3/`, `tables/objective_3/`, `reports/objective_3/`; **one database file per objective**, plus immutable input receipts. Names can be adapted to existing code, but document an unambiguous mapping. Store versions of source files, schema, Python environment, dependencies, Git commit (if available), random seeds, SQL definitions, configuration, training partitions where relevant, and every exported figure/table. For all output figures save SVG or PDF and high-resolution PNG; embedded captions must report units, sample support, fold/geometry status and limitations.

---

# OBJECTIVE 3 — INDICATOR GEOSTATISTICS, MACHINE LEARNING AND HYBRID OCCURRENCE MODELS

## Scope and research question

**Approved Objective 3 (verbatim):** To develop and spatially validate indicator-geostatistical, machine-learning, and hybrid models for predicting graphitic-domain occurrence.

Research question: *Can a hybrid model combining a nonlinear probability trend and geostatistical residual continuity predict graphitic occurrence at previously unseen RAB drilling locations, relative to stand-alone methods?* This stage **fits, tunes, and generates leakage-controlled out-of-fold predictions**, but defers final comparative scientific conclusions to Objective 4.

**Read-only input:** O1 verified geology and geometry, approved label/line registry; O2 spatial support diagnostics and candidate variogram *families*, not leakage-prone all-hole fitted parameters. Inputs must match SHA-256 or dataset content receipts. **Output:** `database/kambale_obj3_models.sqlite`. Preserve prediction records and fold IDs for Objective 4; never write back to O1/O2.

## Three pre-registered principal model families

- **M1 — Indicator-geostatistical baseline.** Estimate `P(I(s)=1)` from ordinary/simple indicator kriging with a training-only variogram and neighbourhood. Specify estimator, stationarity assumptions, matrix numerical stability, covariance validity, transform and handling of kriging values outside `[0,1]`. Clipping to `[0,1]` must be counted and audited; optional calibration trained only on inner-held-out data. If variogram support is insufficient, label M1 `NOT_ESTIMABLE` rather than invent results.
- **M2 — Nonlinear ML.** Train Random Forest and XGBoost/gradient boosting; select a fixed primary M2 candidate through nested spatial training-only optimization. Include a low-complexity prior-prevalence or logistic baseline for sanity checks if support allows. Only predictors available throughout the **target prediction volume** may be used, e.g., properly referenced XYZ or verified mapped/structural covariates if they exist. **Never** use lithology `Sgs`, logged graphite `gr`, graphitic comment text, selected label, sample ID, `HoleID`, split ID, or sample-specific mineral/weathering logs that are absent at prediction voxels as predictors. Do not use a target-derived block or an interpolation of target labels on the full dataset as an ML predictor.
- **M3 — Hybrid ML-informed spatial residual model.** Fit nonlinear ML probability trend `m(s)=P_ML(I=1|X(s))`, compute **training-only spatially cross-fitted residuals** `r_i=I_i-m_{-i,inner}(s_i)` using inner whole-hole/line folds, test whether residual covariance exists, estimate a permissible residual variogram from training-only data, krige residuals at held-out coordinates, and combine `p_H(s)=calibrate_or_constrain[m(s)+r_hat(s)]` with an explicit train-only calibration design. Document probability bounding (e.g. clipping counted and audited, or a coherent link-scale alternative), overfitting avoidance, kernel/neighbourhoods and failure fallback. An uncalibrated arithmetic average of M1 and M2 maps is **not** the defined hybrid. If residual covariance is unsupported, record a nested-CV-selected fallback (e.g., ML-only) and do not label it a novel successful hybrid.

## Non-negotiable spatial validation and experiment

1. **Freeze prediction target and feature availability.** Predeclare chosen O1 label version and observation exclusions; record counts by hole, line, class and geometry status. Do not silently alter this during model comparison.
2. **Freeze spatial split plan before training.** Primary: Leave-One-Drill-Line-Out (LODO) if enough validated lines and class support; hold out entire lines with all their intervals. Secondary: whole-hole group-block CV with documented spatial separation. Precalculate stable fold membership in Objective 3 SQLite, record fold version and hash. An external new drilling campaign is **not** supplied; these are spatially held-out internal tests, not independent future validation.
3. **Nested tuning.** Within each outer training fold, perform group-respecting inner splits for ML hyperparameters, feature transformations, class weights, geostatistical variogram/anisotropy/neighbourhood choices, hybrid residual structures, calibration and decision thresholds. Held-out line observations remain completely unseen until prediction export. Any training-derived feature engineering must be refit inside each fold. If inner spatial folds cannot support tuning, pre-register a low-complexity fixed model and mark limitations.
4. **Baseline fairness.** Same training/test samples and approved target for M1/M2/M3; explain predictor support and any legitimate algorithm-specific covariates; record effective sample counts and missingness per fit. Optional weighting: compare interval-weighted and hole-balanced approaches defined a priori. 1,910 intervals in 71 holes are not 1,910 independent wells.
5. **Fit M1/M2/M3.** Produce per-fold model hyperparameters, training-only variogram parameters, calibration method and status, numerical diagnostics, reproducible fitted model-artifact hash, seed and software versions. Different candidate ML models may be tested **inside** the training workflow, but do not use outer test performance to choose the final M2 candidate.
6. **Out-of-fold predictions.** Write one row per eligible `(observation_id, fold_id, model_family/model_run)` with true target label, `p_raw`, `p_calibrated` if properly trained, predicted class at a training-selected threshold, prediction timestamp, geometry/label/run IDs, and explicit absence/abstention reason. Keep predictions for all model families on identical held-out identifiers, or mark differences with transparent comparison-set rules. For probabilistic metrics, store predictions for all valid samples; never discard difficult cases post hoc.
7. **Residual and spatial diagnostics.** Persist training and held-out residuals with unambiguous status, residual variogram support and distance-to-training well. Do not calculate residual variogram from test labels for training decisions.
8. **Final fit contract (for Objective 5 only).** After Objective 4 locks model selection, implement the command to refit that selected full training pipeline using all **eligible** approved observations and produce a hashed final-fit artifact. The O3 database must distinguish `OUTER_CV_FIT` from `FINAL_FULL_FIT`. Do not call the full fit spatially validated; the support for its method comes from held-out O4 evaluation.

## Formulations and methodological decisions

Use `I(s) in {0,1}` and `p(s)=Pr[I(s)=1]`. Preserve distinct estimates and statuses for `p_IK`, `p_ML`, `p_H`. For OOF comparisons, probability scores require `p ∈ [0,1]`; audit any clipped values and missing predictions. Record logit-transform epsilon when used. For kriging, specify exact covariance equations and solver, regularization/nugget and how training-fold data determine hyperparameters. For hybrid residuals use out-of-fold inner predictions, not in-sample fitted ML predictions to define apparently vanishing residual variation. Discuss dependence across 1-m intervals, class imbalance, anisotropic sampling, geometry status, limited distinct drill lines, and extrapolation outside the observed envelope.

Packages: `numpy`, `pandas`, `scikit-learn` (`LeaveOneGroupOut`/`GroupKFold`, RF, calibration and metrics), `xgboost` (or audited gradient boosting fallback), `gstools`/`scikit-gstat`/`geostatspy` for validated geostatistical methods, `scipy`, `sqlite3`, `joblib`, `matplotlib`, `pytest`. Document when the selected Python package lacks *native* indicator kriging and explicitly implement/validate the binary-indicator kriging equations; a standard continuous-variable kriging routine applied to indicators must be described precisely, not misrepresented as a specialized package capability.

## Objective 3 SQLite schema

Build complete DDL for: `source_receipts`, `stage_runs`, `target_registries`, `feature_registry` (source, availability at voxels, leakage designation, units), `label_versions`, `geometry_versions`, `spatial_split_plans`, `split_membership` (all interval IDs, hole/line/fold), `split_audit`, `model_families`, `training_runs`, `hyperparameter_trials`, `training_sample_manifest`, `variogram_training_fits`, `hybrid_residual_variogram`, `calibration_fits`, `model_artifacts` (path/hash), `predictions_oof`, `prediction_failures`, `residual_diagnostics`, `leakage_audit_log`, `final_refits`, `figure_registry`, `figure_sql_registry`, `table_registry`, `export_manifests`, `gate_results`. Constraint: outer test IDs must never intersect training IDs; unique OOF predictions per `(outer_split, observation, candidate_run)`; probabilities bounded; target codes binary/null; explicit prediction support. Index interval/hole/fold/model/run IDs and read-only exports for O4.

## Thesis figures and tables — generated from O3 database

- `O3-F01`: Frozen outer-fold spatial map and class support, showing which drill line is held out each time.
- `O3-F02`: Exact deployment predictor-feature availability and 3-D support visualization; include warnings about missing spatial covariates.
- `O3-F03`: M1 probability predictions (sampled OOF locations), with geometry and clipping/calibration status.
- `O3-F04`: M2 RF/XGBoost OOF probability sections for comparable held-out locations.
- `O3-F05`: M3 hybrid OOF probability sections aligned with other models.
- `O3-F06`: Residual variogram diagnostics by training fold, with training-only source evidence.
- `O3-T01`: Model definitions, features, target/rule version and sample support.
- `O3-T02`: Split-by-split hyperparameters, variogram parameters and model fitting diagnostics.
- `O3-T03`: OOF prediction completeness and leakage auditing per family, line and class.
- `O3-T04`: M1/M2/M3 artifact and reproducibility registry.

Do NOT present out-of-fold ROC/AUC/Brier model rankings as the main O3 scientific result; leave final comparisons and inference to O4, although basic within-fold diagnostics for fitting are permitted and clearly labelled.

## Acceptance and handoff

- **STOP:** split contamination; any target-derived field used as predictor; test-based variogram/hyperparameter tuning or calibration; O1/O2 hash mismatch; use of unknown elevations as verified Z; model trained with one label version and evaluated with another without stratification; invalid predictive probabilities unrecorded; mismatch in fold evaluation IDs not disclosed.
- **WARN:** sparse class, conditional probability clipping, weak geostatistical support, low effective N, mixed geometry statuses, extrapolation, high residual autocorrelation, over-optimistic random split compared with blocked split (random split is exploratory only).
- **SKIP/DOWNGRADE:** missing both classes in a training fold; unsolvable kriging matrix; insufficient training pairs for variogram; incomplete covariate coverage; no stable hybrid residual continuity. Preserve a meaningful failure record and compare feasible model subsets fairly.
- **Pass:** hashes/keys match O1/O2; every training/test split audited; each successful model has OOF probabilities for allowed test IDs; no leakage; residual/variogram fits are training-only; actual tests pass; results traceable and readable by O4. Unit tests on tiny synthetic controlled cases are allowed for checking implementation but must never be reported as Kambale empirical results.

**Handoff to O4:** frozen `split_plan_id`, approved target/geometry version, complete OOF predictions and failure masks, hyperparameter/model artifacts, calibration metadata, selection policy and audit receipts. O4 may evaluate/rank, but must **not refit** models or change splits.

## Mandatory seven-file SpecKit specification package for Objective 3

The coding agent MUST create full, executable or fully specified content for **each** of these files, not summaries or boilerplate. File names are objective-local (`specs/objective_3/...`). Every document must identify exact inputs/outputs and trace its requirements to Objective 3, while preserving the five synopsis objectives unchanged.

1. **`01_thesis_scope_review_and_claims.md`** — scientific purpose, detailed objective traceability, critical MSc-examiner challenges, defensible claims vs prohibited claims, dependency and prior-stage acceptance gates; distinguish observation, interpretation, prediction and uncertainty.
2. **`02_methods_and_mathematical_framing.md`** — full methods and relevant equations, estimands/targets, parameter constraints, assumptions, baselines, competing designs, sensitivity studies, and interpretation requirements; do not invent numerical results.
3. **`03_acceptance_and_failure_gates.md`** — implementable STOP/WARN/SKIP/DOWNGRADE conditions, database SQL assertions and Python tests with deterministic output statuses. A scientific gate failure must be visible in exports and may block a particular figure or analysis without needlessly stopping unaffected work.
4. **`04_data_contract_and_io.md`** — exact upstream database and tables/SQL-view contracts (discover actual Objective 1 schema rather than assume names), column types/units/null semantics, keys, receipts, downstream output schemas, command-line interfaces and versioning. Document any compatibility adapter; never invent available fields.
5. **`05_schema.sql`** — executable, objective-specific SQLite DDL with primary/foreign keys, indexes, uniqueness, checks, UTC run metadata and import receipts, local migrations and views. Include SQL files for each thesis figure and table; persist plot-ready aggregates or their reproducible parameterized SQL-query definitions.
6. **`06_python_analysis_and_plotting.md`** — complete Python implementation plan and CLI, packages/versions, exact figure and table catalogue, SQL extracts, deterministic rendering and data lineage, test cases, plus explicit path examples. Deliver working Python code in addition to this plan.
7. **`07_speckit_agent_kickoff.md`** — copy-ready, dependency-ordered execution prompt for a coding agent (Claude Code, Cursor, etc.), official Spec Kit init and task generation, real command invocations, evidence required to mark tasks done, final handoff to the next objective.

Also deliver runnable `src/` modules, `.sql` migrations and figure SQL, `pyproject.toml` or dependency lock updates, `pytest` tests, populated objective-specific `.sqlite` from **actual upstream verified data**, figure/table files wherever scientific gates permit, `README.md`, `RUN_REPORT.md`, `DATA_LINEAGE.json` (or equivalent database tables), `FIGURE_MANIFEST.csv`, and `BLOCKED_OR_DEFERRED.md`. A specification without functioning code and database is incomplete.

### Official Spec Kit protocol

The CLI is `specify`, from the officially maintained `specify-cli` distribution; it is **not** an assumed `speckit` CLI. Verify in the live environment with `specify version`; if absent, use the verified official install method (`uv tool install specify-cli` where `uv`/network are available), check actual options via `specify init --help`, then initialize safely with `specify init --here --integration claude --non-interactive` or an equivalent command for the actual agent. Do not overwrite an existing project or force merge without backup. Follow the installed official integration's `constitution -> specify -> clarify/plan -> tasks -> analyze -> implement -> converge` sequence. If official scaffolding is unavailable, document why, retain working local `specs/objective_3/` documents and a dependency-ordered `tasks.md`, and continue implementing the code. Never claim successful installation if it was not executed.

### Mandatory completion report

Report exactly: (a) generated specification/code/SQL files; (b) objective database path, schema version, table row counts and upstream receipt hashes; (c) verification of predecessor acceptance; (d) CLI commands to rerun all stages; (e) figures/tables with SQL and hash manifest; (f) tests **actually run** and passed/failed; (g) geological/methodological assumptions and limitations; (h) STOP/WARN/SKIP records and deferred outputs; (i) exact handoff contract for the next objective. No hallucinated results, no unsupported claims, no unverified count or performance statistics. Reproducibility and truthful failure reporting outrank producing a visually attractive model.

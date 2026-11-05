# SPEC KIT CODING-AGENT MASTER PROMPT — OBJECTIVE 4

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

Use `specs/objective_4/`, `sql/objective_4/`, `src/kambale/objective_4/`, `config/objective_4/`, `tests/objective_4/`, `figures/objective_4/`, `tables/objective_4/`, `reports/objective_4/`; **one database file per objective**, plus immutable input receipts. Names can be adapted to existing code, but document an unambiguous mapping. Store versions of source files, schema, Python environment, dependencies, Git commit (if available), random seeds, SQL definitions, configuration, training partitions where relevant, and every exported figure/table. For all output figures save SVG or PDF and high-resolution PNG; embedded captions must report units, sample support, fold/geometry status and limitations.

---

# OBJECTIVE 4 — INDEPENDENT SPATIAL VALIDATION AND PROBABILITY-BASED PERFORMANCE

## Scope and research question

**Approved Objective 4 (verbatim):** To evaluate the predictive performance of the developed models using independent spatial validation and probability-based metrics.

Research question: *Under identical spatially held-out drill-line predictions, which modelling approach provides the most reliable and discriminating probability of graphitic-domain occurrence, and is any apparent improvement consistent and statistically credible?* The stage is **evaluation, auditing and decision-making**, not model development or tuning.

**Read-only inputs:** O1 approved target/geometry reference, O3 frozen split manifest and model OOF predictions, O2 spatial diagnostics where needed. Never access held-out labels to modify O3 predictions. **Output:** `database/kambale_obj4_validation.sqlite`. The only authoritative model fits and raw predictions remain in O3. Store evaluation-ready immutable prediction snapshots with integrity hashes, not independently edited or corrected probabilities. No O3 write operations.

## Analysis design and estimands

1. **Evaluate the holdout design.** Validate leave-one-drill-line-out groups, per-fold test counts, positive/negative class counts, hole counts, estimated spatial separation and possible training/test proximity. Record that this is *spatially held-out internal validation*, NOT a separate prospective exploration campaign or untouched external dataset. Check any spatial blocking compromise explicitly.
2. **Import exact OOF prediction cohorts.** For M1, M2 and M3 construct an intersection cohort of observations with valid comparable predictions, plus report the full per-model coverage rate. Never silently change denominators or exclude low-confidence cases. A model's failures are reported as part of applicability and are not erased by restricting to common-case predictions. Log exclusion reason for each sample and candidate.
3. **Predeclare primary endpoint and unit of analysis.** Suggested primary endpoint: **Brier score** on the common held-out cohort, with a declared primary weighting scheme and secondary sensitivity to equal-hole weighting versus interval weighting. `BS = (sum_i w_i (p_i-y_i)^2)/(sum_i w_i)`. Specify whether reported performance estimates represent a randomly selected logged interval or a randomly selected hole; they answer different questions.
4. **Secondary probability metrics.** PR-AUC (with held-out class prevalence baseline), ROC-AUC, log loss (only after documented epsilon convention), calibration-in-the-large/intercept/slope, reliability curves with bin counts, and explicitly labelled ECE if used. AUC is `UNDEFINED` where a fold contains only one class; do not coerce to zero or average silently. PR-AUC conventions (average precision vs trapezoidal PR area) must be stated. Never present AUC alone as proof of well-calibrated probabilities.
5. **Classification metrics.** With decision thresholds frozen using *training-only* folds in O3, compute precision, recall, specificity, balanced accuracy, F1/Dice, MCC and confusion matrices, with zero-denominator rules and class/threshold metadata. Do not optimize thresholds on O4 test labels.
6. **Reliability and calibration checks.** Verify calibration parameters were fitted within O3 training data and are consistent across folds; compare raw and properly calibrated probability distributions without recalibrating on held-out data. Draw reliability curves with observation counts and confidence interval method stated. Insufficiently populated bins are combined by a predeclared rule or omitted with explanation.
7. **Error geography.** Plot false positives/negatives and residuals by held-out line, depth, distance to training hole and extrapolation status, if those variables exist as verified features. Assess residual spatial clustering descriptively without overclaiming process causality.
8. **Paired comparison uncertainty.** Use paired OOF predictions over identical IDs and report `delta_BS = BS_hybrid - BS_baseline` and corresponding differences for discrimination/coverage. Show per-line differences (the effective number of independent lines may be small). When using bootstrap, resample at the **hole or spatial-group level** and keep pairs together; justify the sampling design, sparse five-line limitation, and report sensitivity to the clustering unit. Do **not** report interval-level i.i.d. bootstrap p-values or claim significance solely from 1,910 intervals.
9. **Decision policy.** Define `SUPPORTED_IMPROVEMENT`, `INCONCLUSIVE`, `NO_IMPROVEMENT`, or `NOT_COMPARABLE` using a pre-specified hierarchy: higher-priority lower Brier score plus credible fold consistency/uncertainty and acceptable calibration, discrimination and coverage. If small spatial folds cannot establish statistical certainty, a descriptive comparison is scientifically valid; label as **inconclusive** when warranted. A hybrid model can legitimately lose. Publish a single locked decision receipt for O5, with model ID and limitations; no post-hoc winner selection based on unreported metrics.
10. **No unsupported external validity.** A successful blocked CV predicts performance under a particular held-out spatial design, not automatically unknown distant geology. Explain prediction geography, interpolation/extrapolation and domain shifts.

## Objective 4 database schema

Complete SQLite DDL for: `source_receipts`, `stage_runs`, `evaluation_population` (frozen OOF ID / line / hole / class / weight), `candidate_registry`, `prediction_snapshot` (read-only snapshot origin ID, probability, calibrated flag, model/fold), `prediction_coverage`, `evaluation_plan` (primary endpoint, evaluation unit and weighting, calibration requirements), `metric_definitions`, `fold_metrics`, `pooled_metrics`, `class_confusion_matrices`, `calibration_bins`, `calibration_diagnostics`, `spatial_error_summaries`, `paired_differences`, `resampling_designs`, `bootstrap_replicates` (if performed), `comparison_decisions`, `locked_handoff_receipts`, `evaluation_audit_log`, `figure_registry`, `figure_sql_registry`, `table_registry`, `export_manifests`, `gate_results`. Include DB-level checks for probability bounds, class codes, finite metric ranges where defined, fold alignment, immutable source receipt references and reproducible seed ledger. Use SQL views with explicit common-cohort definitions and coverage counters.

## Required scientific figures and tables

- `O4-F01`: Spatial holdout fold map with holes/classes and inclusion/exclusion overlays.
- `O4-F02`: Brier score by model and drill line, with correctly defined paired contrasts.
- `O4-F03`: ROC curves (only for pooled observations or per-fold samples where both classes exist) and PR curves with prevalence baseline; indicate sample support.
- `O4-F04`: Calibration/reliability diagrams with bin counts and uncertainty bands only when estimates are supportable.
- `O4-F05`: Paired hybrid-versus-M1 and hybrid-versus-M2 Brier differences by line, including sign convention and interval/hole weighting.
- `O4-F06`: Spatial maps of prediction errors or residuals on withheld observations only.
- `O4-F07`: Coverage/abstention/missing-prediction plot; stratify by line/model, not silently prune difficult examples.
- `O4-T01`: Main evaluation summary, including support counts, coverage, weighting and the locked split plan.
- `O4-T02`: Fold-by-fold scores (Brier, discrimination, calibration and class support).
- `O4-T03`: Confusion matrices and threshold rule provenance.
- `O4-T04`: Paired difference uncertainty and sensitivity to clustering/weighting.
- `O4-T05`: Final model-selection decision, improvement claim classification, rejected alternatives and limitations.

## Automated scientific gates

- **STOP:** upstream receipt changes without revalidation; predictions generated by models exposed to their held-out labels during tuning; different target versions mixed in a ranking; metrics calculated on non-identical cohorts without disclosure; threshold calibrated on test folds; missing predictions silently removed; invalid probability values; confidence intervals calculated as if adjacent 1-m intervals were independent.
- **WARN:** only five spatial lines, very few graphitic classes in a fold, uncertain coordinate elevation, wide/unstable uncertainty intervals, heavy post-hoc threshold sensitivity, apparent model improvement concentrated in one line, large model-dependent coverage differences.
- **SKIP:** undefined AUC for one-class fold, unavailable calibration slope/intercept for ill-conditioned fold, non-estimable bootstrap contrast. Never replace undefined with zero; always store metric status and reason.
- **DOWNGRADE:** statistical significance unsupported or independent validation misdescribed. Save as descriptive comparison with explicit claim limitations.
- **Pass:** O3 prediction hashes match; no training/test overlap; cohort and weights declared; Brier numerically cross-checked by independent implementation; fold metrics reconstructable; decision rule predeclared and followed; figures query only O4 SQL and record its original source; tests and independent metric spot-checks passed.

Suggested stack: `sqlite3`/`SQLAlchemy`, `numpy`, `pandas`, `scikit-learn.metrics`, `scipy`, `statsmodels` for supported calibration/interval methods, `matplotlib`, `pytest`. All resampling random seeds/strata are recorded. Favor simple, transparent plots over unwarranted statistical complexity.

**Handoff to O5:** locked, signed model-choice decision with `model_id`, target/geometry data receipt, split plan and metric reference, calibration fit policy, allowed application domain, proper uncertainty caveats and an instruction to O3 to produce the **final full-data fit artifact** for the selected model. O5 must refuse to load a model artifact not approved by this O4 receipt.

## Mandatory seven-file SpecKit specification package for Objective 4

The coding agent MUST create full, executable or fully specified content for **each** of these files, not summaries or boilerplate. File names are objective-local (`specs/objective_4/...`). Every document must identify exact inputs/outputs and trace its requirements to Objective 4, while preserving the five synopsis objectives unchanged.

1. **`01_thesis_scope_review_and_claims.md`** — scientific purpose, detailed objective traceability, critical MSc-examiner challenges, defensible claims vs prohibited claims, dependency and prior-stage acceptance gates; distinguish observation, interpretation, prediction and uncertainty.
2. **`02_methods_and_mathematical_framing.md`** — full methods and relevant equations, estimands/targets, parameter constraints, assumptions, baselines, competing designs, sensitivity studies, and interpretation requirements; do not invent numerical results.
3. **`03_acceptance_and_failure_gates.md`** — implementable STOP/WARN/SKIP/DOWNGRADE conditions, database SQL assertions and Python tests with deterministic output statuses. A scientific gate failure must be visible in exports and may block a particular figure or analysis without needlessly stopping unaffected work.
4. **`04_data_contract_and_io.md`** — exact upstream database and tables/SQL-view contracts (discover actual Objective 1 schema rather than assume names), column types/units/null semantics, keys, receipts, downstream output schemas, command-line interfaces and versioning. Document any compatibility adapter; never invent available fields.
5. **`05_schema.sql`** — executable, objective-specific SQLite DDL with primary/foreign keys, indexes, uniqueness, checks, UTC run metadata and import receipts, local migrations and views. Include SQL files for each thesis figure and table; persist plot-ready aggregates or their reproducible parameterized SQL-query definitions.
6. **`06_python_analysis_and_plotting.md`** — complete Python implementation plan and CLI, packages/versions, exact figure and table catalogue, SQL extracts, deterministic rendering and data lineage, test cases, plus explicit path examples. Deliver working Python code in addition to this plan.
7. **`07_speckit_agent_kickoff.md`** — copy-ready, dependency-ordered execution prompt for a coding agent (Claude Code, Cursor, etc.), official Spec Kit init and task generation, real command invocations, evidence required to mark tasks done, final handoff to the next objective.

Also deliver runnable `src/` modules, `.sql` migrations and figure SQL, `pyproject.toml` or dependency lock updates, `pytest` tests, populated objective-specific `.sqlite` from **actual upstream verified data**, figure/table files wherever scientific gates permit, `README.md`, `RUN_REPORT.md`, `DATA_LINEAGE.json` (or equivalent database tables), `FIGURE_MANIFEST.csv`, and `BLOCKED_OR_DEFERRED.md`. A specification without functioning code and database is incomplete.

### Official Spec Kit protocol

The CLI is `specify`, from the officially maintained `specify-cli` distribution; it is **not** an assumed `speckit` CLI. Verify in the live environment with `specify version`; if absent, use the verified official install method (`uv tool install specify-cli` where `uv`/network are available), check actual options via `specify init --help`, then initialize safely with `specify init --here --integration claude --non-interactive` or an equivalent command for the actual agent. Do not overwrite an existing project or force merge without backup. Follow the installed official integration's `constitution -> specify -> clarify/plan -> tasks -> analyze -> implement -> converge` sequence. If official scaffolding is unavailable, document why, retain working local `specs/objective_4/` documents and a dependency-ordered `tasks.md`, and continue implementing the code. Never claim successful installation if it was not executed.

### Mandatory completion report

Report exactly: (a) generated specification/code/SQL files; (b) objective database path, schema version, table row counts and upstream receipt hashes; (c) verification of predecessor acceptance; (d) CLI commands to rerun all stages; (e) figures/tables with SQL and hash manifest; (f) tests **actually run** and passed/failed; (g) geological/methodological assumptions and limitations; (h) STOP/WARN/SKIP records and deferred outputs; (i) exact handoff contract for the next objective. No hallucinated results, no unsupported claims, no unverified count or performance statistics. Reproducibility and truthful failure reporting outrank producing a visually attractive model.

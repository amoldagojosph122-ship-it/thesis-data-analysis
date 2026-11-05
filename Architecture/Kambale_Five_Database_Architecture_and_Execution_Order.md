# Joseph's Kambale MSc — Five Separate SQLite Databases, One Controlled Scientific Workflow

## Decision

Maintain the **five approved synopsis objectives verbatim**. Organize execution by objective, each with a discrete SQLite database, but preserve a single geological source of truth in Objective 1. Thus, **five database files, five analytical responsibilities, one coordinated lineage system**.

## Database allocation and upstream lineage

| Stage | SQLite database | Responsible for | Required upstream |
|---|---|---|---|
| Objective 1 | `database/kambale_thesis.sqlite` (the existing DB path may be retained) | Original workbook ingestion, raw/curated tables, approved labels, survey/coordinate versions, QA/QC | Original Excel workbook and documented survey metadata |
| Objective 2 | `database/kambale_obj2_spatial.sqlite` | Hole/line summaries, indicator variograms, geological continuity/anisotropy diagnoses | Objective 1 approved dataset receipt |
| Objective 3 | `database/kambale_obj3_models.sqlite` | Fold definitions, fitted models, training-only variograms, model artifacts, out-of-fold probability predictions | Objective 1 target and geometry, Objective 2 variogram design (not full-data fit parameters in CV) |
| Objective 4 | `database/kambale_obj4_validation.sqlite` | Held-out evaluation and calibration audit, metrics, paired comparisons, locked selection decision | Objective 3 frozen OOF predictions, Objective 1 target reference |
| Objective 5 | `database/kambale_obj5_uncertainty.sqlite` | Approved predictive grid, support masks, entropy, simulations, 3-D plot/table results | Objectives 1/2 plus Objective 3 selected final fit and Objective 4 locked decision |

**Do not create five independently maintained copies of collar/logging facts.** Objective 1 is authoritative for original geological observations. Objectives 2–5 store derived results, necessary immutable/versioned analytic snapshots and read-only upstream receipts. Every downstream database must record input dataset IDs, geometry/label/fold/model versions, exact SQL extract hash, SHA-256 or stable ordered-content digest, row counts and code revision. Any source change invalidates descendants until recomputed.

**Cross-file integrity:** SQLite's foreign keys operate within a database file, not across attached SQLite databases. For each import, run explicit Python/SQL receipt comparison, expected-ID set and multiplicity checks; log failed alignment as STOP. Use `ATTACH DATABASE` read-only only where appropriate, or materialize a versioned minimal analytic snapshot with a hash. Never rely on `ATTACH` to create a nonexistent cross-database referential-integrity guarantee.

## Suggested execution order

1. Build/check Objective 1 and lock the approved graphitic label and coordinate/vertical datum status. The master database remains editable only via versioned ETL and recorded geological review decisions.
2. Run Objective 2 descriptive analysis and indicator variography. Its **full-data variogram is descriptive**; Objective 3 must refit any statistically estimated variogram using only each fold's training data.
3. Run Objective 3 grouped spatial CV, model training and OOF prediction exports. The holdout line must not influence any training-only transformation, variogram, calibration, tuning or threshold.
4. Run Objective 4 evaluation on frozen OOF predictions using the same holdout observations, with coverage, Brier, PR-AUC, calibration and class metrics, and record selected model with limitations.
5. Refit selected Objective 3 pipeline to eligible full training data **only after** model selection is locked. Run Objective 5 probability grids, spatial-support masks, entropy and optional validated conditional simulation; generate 3-D figures only within geometry/validation claim boundaries.

## Outputs and human approvals

- Each objective has its own `specs/`, `sql/`, `src/`, `tests/`, `figures/`, `tables/`, `reports/` subdirectories and SQLite DB.
- All figures and tables carry objective IDs (`O2-F01`, `O3-F01`, etc.) and hashes linking SQL, input dataset, script and output.
- Geological supervisor approvals needed for graphite target reconciliation, coordinate reference, drill-line groups and interpretation of probable continuity. The user may approve modelling methods separately; not a substitute for physical evidence.
- Missing collar RL permits provisional relative-geometry analysis, **not** a verified georeferenced 3-D volume. No assay -> no graphite-grade/resource claims.
- Stage-status vocabulary: `APPROVED`, `PROVISIONAL`, `EXPLORATORY`, `SKIPPED`, `BLOCKED`, `STALE`. Never quietly promote preliminary results to approved outputs.

## Four implementation prompts included

1. `Kambale_Objective_2_SpecKit_Master_Prompt.md`
2. `Kambale_Objective_3_SpecKit_Master_Prompt.md`
3. `Kambale_Objective_4_SpecKit_Master_Prompt.md`
4. `Kambale_Objective_5_SpecKit_Master_Prompt.md`

Give these to the coding agent **sequentially** alongside the Objective 1 database and previous stage's verified output. They tell the agent to generate seven complete specification files per objective plus working SQL/Python code, populated objective DBs and verified, data-supported figures.

The original Objective 1 master prompt is included in the bundle when present for continuity.

<!--
SYNC IMPACT REPORT (scratch material for human review; remove before committing)
Version change: template (unversioned) -> 1.0.0 (initial ratification)
Modified principles: none (template placeholders replaced)
Added sections: Technology and Data Constraints; Delivery Workflow and Quality Gates
Removed sections: none
Deferred TODOs: none. Ratification date set to the date this project constitution was first adopted (2026-11-05), taken from the Stage A session.
Source of principles: Kambale_Thesis_Database_First_SpecKit_Prompt.md, Architecture/Kambale_Five_Database_Architecture_and_Execution_Order.md, Objective_1/Kambale_Objective_1_MultiDB_Addendum.md, and Objective_2..5 SpecKit master prompts.
-->

# Kambale Graphite Thesis Constitution

Project: Hybrid Machine Learning–Indicator Geostatistical Modelling for Spatially Validated Three-Dimensional Prediction and Uncertainty Characterization of Graphitic Domains at the Kambale Graphite Deposit, Ghana (MSc Geological Engineering).

Fixed synopsis objectives (immutable, must be quoted verbatim in every stage specification):

1. To construct and quality-control a three-dimensional drill-hole database and define graphitic domains at the Kambale Graphite Deposit.
2. To characterize the spatial distribution, geological controls, and continuity of graphitic domains using exploratory spatial analysis and indicator variography.
3. To develop and spatially validate indicator-geostatistical, machine-learning, and hybrid models for predicting graphitic-domain occurrence.
4. To evaluate the predictive performance of the developed models using independent spatial validation and probability-based metrics.
5. To quantify and visualize three-dimensional uncertainty in graphitic-domain occurrence and identify areas of high confidence and high uncertainty.

## Core Principles

### I. Source Fidelity and Raw Immutability (NON-NEGOTIABLE)
The supplied workbook `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx` is the only primary data source. MUST be copied unchanged to `data/raw/`, hashed with SHA-256, and verified against that hash at every ETL run. Raw rows MUST be stored with their original sheet name, row number, raw field names and raw spelling, and SQLite triggers MUST reject UPDATE and DELETE on raw tables. A discrepancy between the workbook and previously reported counts MUST be logged and explained; counts MUST NOT be forced to match earlier figures. Rationale: the thesis defence depends on being able to reconstruct every number from the original file.

### II. SQLite as the Single Source of Truth for Objective 1
`database/kambale_thesis.sqlite` (logical alias `obj1_master`) is the only editable store of curated geological observations, label rules, coordinate decisions, geometry versions and QA/QC decisions. Every figure and table MUST be rendered from read-only `v_*` views or from a versioned, parameterised SQL file under `sql/figures/`. Rendering code MUST NOT read the Excel workbook, a notebook or an untracked spreadsheet. Objectives 2–5 MUST own their own databases and read Objective 1 only through documented receipts; SQLite foreign keys MUST NOT be assumed across attached files.

### III. Honest Geology: No Invented Elevations, Grades or Classes
Collar RL is absent for all 71 holes. `z_absolute_m` MUST remain NULL until an approved, source-documented elevation or DEM is recorded; `0` MUST NOT be used as a substitute RL; plots MUST label vertical positions as relative (provisional). `Sgs`, `gr` and graphitic comments are logged indicators, not laboratory confirmation and not graphite grade (no TGC/assay exists). Candidate graphitic label rules MUST be stored with version, evidence and status `PROPOSED` until a supervising geologist records an approval in `label_reviews`. Unsupported codes and missing codes MUST remain unresolved rather than be guessed. No contact between holes is drawn as observed geology.

### IV. Explicit Status, Severity and Stop/Warn/Defer Behaviour
Every QA/QC finding MUST carry severity `ERROR`, `WARNING` or `INFO` and a status `BLOCKED`, `PROVISIONAL` or `APPROVED`. Every output MUST carry one of the stage-status words `VERIFIED`, `PROVISIONAL`, `BLOCKED`, `DEFERRED` or `FAILED`. A failed gate stops only the affected step; unaffected work continues and is reported. Orphan, malformed, duplicate or unsupported records MUST be quarantined and reported, never silently dropped. Every correction or exclusion MUST have an auditable decision row.

### V. Reproducibility and Idempotence
ETL runs MUST be deterministic and transactional. A `dataset_version_key` derived from source hash, ETL code version and rule versions MUST make an identical rerun a no-op (no duplicate rows, no changed approved data). Figures MUST be regenerable by ID and dataset version through the documented CLI, and each output MUST be registered with the SHA-256 of its SQL file, its input dataset version, its label-rule version, its geometry status and its own output hash. Plot metadata that changes between runs (timestamps, software tags) MUST be suppressed so that reruns are byte-identical where the renderer allows it.

### VI. Leakage Discipline and Stage Gating
Stage B work (variograms, ML or hybrid fitting, predictions, calibration, simulation and uncertainty grids) MUST NOT run during Stage A. Future-stage tables MUST exist only as empty, write-protected contracts in Objective 1. Any variogram or model fitted on all holes is exploratory only and MUST NOT be presented as leakage-free. Test-fold information MUST NOT influence any training, tuning, threshold or calibration decision in later stages. Stage B begins only after the label rule, coordinate decision and drill-line grouping have been reviewed.

### VII. Verified Claims Only
A statement that a test passed, a file was produced or a hash matches MUST be backed by an executed command in the current session. Unrun tests MUST be reported as not run. Results MUST be reported with the exact pass/fail counts. Statistical summaries MUST use the stated denominator and sample support. Prohibited overclaims (graphite grade, tonnage, resources, geological continuity between holes, predictive accuracy from unmodelled data) MUST NOT appear in any figure, table or report.

## Technology and Data Constraints

- Python 3.11 or newer. Core packages: pandas, numpy, openpyxl, sqlite3 (standard library), pyproj, scipy, matplotlib, geopandas/pyogrio (regional context only), PyYAML, pytest. Optional: plotly for interactive HTML. Versions MUST be recorded in `pyproject.toml` and the lock file.
- QGIS, ArcGIS, Leapfrog, R, paid software and manually maintained spreadsheets are NOT required and MUST NOT be introduced as sources of truth.
- Spatial reference: UTM zone 30N as labelled in the workbook (`Grid = UTM_30N`). Datum is UNVERIFIED and MUST be reported as a provisional coordinate-reference status until confirmed.
- Schema changes MUST be made by numbered migration files in `migrations/`; applied migrations are recorded in `schema_migrations`.
- Output figures MUST be vector (SVG or PDF) plus PNG at 300 dpi or higher, using a colour-blind-safe palette.

## Delivery Workflow and Quality Gates

- Work follows the Spec Kit cycle: constitution → specify → plan → tasks → analyze → implement → converge. Each stage writes its artifacts under `specs/` before code that depends on them is merged.
- Each stage MUST pass its acceptance gate in `specs/` before the next stage begins. A stage that fails its gate MUST produce a documented blocked status, not an unverified success.
- Automated tests MUST cover: raw hash and immutability, referential integrity, depth and geometry unit cases (cardinal directions and dips), label evidence reconstruction, idempotent reruns, null-RL safety, figure-to-query provenance and manifest hashes.
- A handover report MUST list completed, provisional, blocked, deferred and failed items, with the exact rerun command.

## Governance

This constitution supersedes other project practices where they conflict. Amendments MUST be recorded in this file with an updated version line and a Sync Impact Report, and MUST state the rationale. Versioning follows semantic rules: MAJOR for removal or redefinition of a principle; MINOR for a new principle or materially expanded guidance; PATCH for clarifications. Every specification, plan, task list and report MUST be checked against these principles before implementation proceeds. Runtime development guidance is in `README.md`, which MUST be kept consistent with this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-11-05 | **Last Amended**: 2026-11-05

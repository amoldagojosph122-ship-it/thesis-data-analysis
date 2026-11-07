# thesis-data-analysis
Hybrid machine learning and indicator geostatistical modelling for 3D prediction and uncertainty characterisation of graphitic domains at the Kambale Graphite Deposit, Ghana.

## Kambale Stage A (Objective 1)


Database-first implementation for the MSc thesis *Hybrid Machine Learning–Indicator Geostatistical Modelling for Spatially Validated Three-Dimensional Prediction and Uncertainty Characterization of Graphitic Domains at the Kambale Graphite Deposit, Ghana*.

**Status (Stage A): PROVISIONAL.** The database build, integrity checks, reconciliation and test suite pass. Coordinates, vertical positions, graphitic label rules and drill-line groups are provisional. No collar RL exists, so absolute 3-D elevation is not produced. No graphite assay exists, so no grade, tonnage or resource is stated. The later work is in its own objective databases: Objective 2 (spatial analysis and variography) and Objective 3 (spatial split, models and out-of-fold predictions); uncertainty products remain to be built in Objective 5.

## Kambale Objective 2 (spatial analysis and indicator variography)

`database/kambale_obj2_spatial.sqlite` holds the derived spatial summaries, pair support and indicator variograms.
The lateral between-hole variogram is **not identifiable** at the available support; the within-hole range (about
15–24 m) is descriptive only. The Objective 3 handoff is `NOT_IDENTIFIABLE` with candidate family `NONE`.
Run it with `python -I -m kambale.objective_2 all`; the record is in `reports/objective_2/RUN_REPORT.md`.

## Kambale Objective 3 (indicator geostatistics, ML and hybrid models)

`database/kambale_obj3_models.sqlite` holds the frozen leave-one-drill-line-out split, inner whole-hole tuning,
out-of-fold predictions, failure masks, calibration, residual diagnostics and the Objective 4 handoff. The deployed
predictors are only easting, northing and relative Z. M1 indicator kriging and the M3 hybrid are attempted with
training-only variograms and are recorded as `NOT_ESTIMABLE` or as an explicit ML-only fallback when the
support fails; neither is claimed as a validated spatial model. Run it with
`python -I -m kambale.objective_3 all`; the record is in `reports/objective_3/RUN_REPORT.md`.

## Kambale Objective 4 (independent spatial validation)

`database/kambale_obj4_validation.sqlite` holds the frozen evaluation of the Objective 3 out-of-fold predictions:
Brier, log loss, ROC-AUC, PR-AUC, calibration diagnostics, confusion matrices, paired differences and hole-cluster
uncertainty. On the current snapshot the random forest has the lowest pooled Brier, but its improvement over logistic
regression is **INCONCLUSIVE**; M1 is not comparable (no prediction) and M3 is the fallback identical to M2_RF. The
locked Objective 5 model choice is stored in `locked_handoff_receipts`. Run it with
`python -I -m kambale.objective_4 all`; the record is in `reports/objective_4/tier_1/RUN_REPORT.md`.

## Layout

- `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx`: primary workbook (unchanged). `data/raw/` holds a read-only copy with its hash in `SOURCE_HASH.txt`.
- `database/kambale_thesis.sqlite`: canonical obj1_master database (logical alias obj1_master).
- `migrations/`: versioned DDL and views (0001-0008). `specs/03_schema.sql` is their concatenation.
- `config/`: coordinate decision, candidate label rules, QA/QC thresholds (YAML).
- `src/kambale/`: ETL (`build.py`), curation, QA/QC, labels, geometry, regional context, verification, figure and table registry, reports, CLI.
- `src/kambale/objective_2/`: spatial analysis and variography; `src/kambale/objective_3/`: spatial split, models, predictions, gates and reports; `src/kambale/objective_4/`: validation metrics, uncertainty and the locked decision.
- `sql/figures/`: one SQL file per figure or table part (22 files); `sql/objective_2/` and `sql/objective_3/` hold their schemas, figure and table queries.
- `figures/objective_1|2|3|4/`, `tables/objective_1|2|3|4/`: outputs (SVG, PDF, PNG; CSV, Markdown, LaTeX).
- `reports/QAQC_REPORT.md`, `FIGURE_MANIFEST.csv`, `DEFERRED_FIGURES.md`, `data/derived/` (non-authoritative CSV copies).
- `specs/`: constitution-aligned stage deliverables 01–07; `specs/001-kambale-o1-stage-a/` holds the Spec Kit feature (spec, plan, tasks).
- `tests/`: the Objective 1 suite and the `objective_2/` and `objective_3/` suites.

## Setup

The project environment is `.venv` (Python 3.14.6) with the pinned packages in `pyproject.toml`.

```bash
uv venv .venv --python C:/Python314/python.exe
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
```

## Commands

```bash
kambale build          # verified ETL; identical source and configuration is a no-op
kambale verify         # SQL integrity, reconciliation, Stage B blocking, pytest
kambale plot --all     # figures F01-F09 with SQL, dataset and output hashes
kambale tables         # tables T01-T03
kambale report         # QA/QC report, figure manifest, deferred list, derived CSVs

# Objective 2 (spatial analysis and indicator variography)
./.venv/Scripts/python.exe -I -m kambale.objective_2 all

# Objective 3 (spatial split, models, out-of-fold predictions and handoff)
./.venv/Scripts/python.exe -I -m kambale.objective_3 all

# Objective 4 (validation metrics, uncertainty and locked model choice)
./.venv/Scripts/python.exe -I -m kambale.objective_4 all
```

If the `kambale` script is not on the path, use `.venv/Scripts/python.exe -m kambale.cli <command>`.

## Rules for contributors

- Do not edit `raw_*` tables. They are protected by triggers, and the workbook must never be overwritten.
- Do not assign a value to `z_absolute_m`, and do not use 0 as a collar RL.
- Do not approve a label rule by editing its status. Record an APPROVE_RULE review in `label_reviews` first.
- Do not write a figure that reads the workbook, the shapefile or a notebook. Add a SQL file in `sql/figures/` that reads views.
- Changing any file in `config/`, or the ETL version, creates a new dataset version. The previous version is archived, never deleted.

## Open decisions (supervisor)

See `specs/001-kambale-o1-stage-a/spec.md`, section "Open decisions", and `reports/QAQC_REPORT.md`, section 7.

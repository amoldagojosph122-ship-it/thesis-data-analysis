# Kambale graphite thesis: Objective 1 database and Stage A preliminary geology

Database-first implementation for the MSc thesis *Hybrid Machine Learning–Indicator Geostatistical Modelling for Spatially Validated Three-Dimensional Prediction and Uncertainty Characterization of Graphitic Domains at the Kambale Graphite Deposit, Ghana*.

**Status (Stage A): PROVISIONAL.** The database build, integrity checks, reconciliation and test suite pass. Coordinates, vertical positions, graphitic label rules and drill-line groups are provisional. No collar RL exists, so absolute 3-D elevation is not produced. No graphite assay exists, so no grade, tonnage or resource is stated. Stage B (variograms, ML, hybrid models, uncertainty) is not run.

## Layout

- `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx`: primary workbook (unchanged). `data/raw/` holds a read-only copy with its hash in `SOURCE_HASH.txt`.
- `database/kambale_thesis.sqlite`: canonical obj1_master database (logical alias obj1_master).
- `migrations/`: versioned DDL and views (0001-0008). `specs/03_schema.sql` is their concatenation.
- `config/`: coordinate decision, candidate label rules, QA/QC thresholds (YAML).
- `src/kambale/`: ETL (`build.py`), curation, QA/QC, labels, geometry, regional context, verification, figure and table registry, reports, CLI.
- `sql/figures/`: one SQL file per figure or table part (22 files).
- `figures/objective_1|2/`, `tables/objective_1|2/`: outputs (SVG, PDF, PNG; CSV, Markdown, LaTeX).
- `reports/QAQC_REPORT.md`, `FIGURE_MANIFEST.csv`, `DEFERRED_FIGURES.md`, `data/derived/` (non-authoritative CSV copies).
- `specs/`: constitution-aligned stage deliverables 01–07; `specs/001-kambale-o1-stage-a/` holds the Spec Kit feature (spec, plan, tasks).
- `tests/`: 35 pytest tests.

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

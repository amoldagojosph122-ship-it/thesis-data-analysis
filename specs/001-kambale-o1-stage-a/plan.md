# Implementation Plan: Kambale Objective 1 Database and Stage A Preliminary Geology

**Branch**: `001-kambale-o1-stage-a` (informational; no git repository) | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-kambale-o1-stage-a/spec.md`

## Summary

Build the Objective 1 master database `database/kambale_thesis.sqlite` (logical alias `obj1_master`) from the supplied workbook. The pipeline (1) copies and hashes the workbook, (2) stores every source row unchanged in `raw_*` tables with row provenance, (3) builds curated tables for holes, surveys, 1-m logging intervals and the legend, (4) runs QA/QC checks that record ERROR/WARNING/INFO findings, (5) derives four versioned candidate graphitic label rules from three logging evidence fields without approving any of them, (6) derives straight-hole midpoint geometry with relative Z only (`z_absolute_m` NULL), (7) groups holes into provisional drill lines by nominal Northing, and (8) renders Stage A figures F01–F09 and tables T01–T03 from `v_*` views through a CLI. Future-stage tables exist only as write-protected contracts. Everything is transactional and idempotent, keyed by a `dataset_version_key`.

## Technical Context

**Language/Version**: Python 3.14.6 (project minimum 3.11), SQLite 3.x via standard-library `sqlite3`

**Primary Dependencies**: pandas 2.3.3, numpy 2.4.6, openpyxl 3.1.5 (raw cell reads), pyproj 3.7.2 (CRS checks), scipy 1.18.0 (nearest-neighbour spacing), matplotlib 3.11.1 (figures), geopandas 1.1.4 / shapely 2.1.2 / pyogrio 0.13.0 (regional context ingestion only), PyYAML 6.0.3 (decision files), pytest 9.1.1 (tests). plotly is optional (interactive 3-D HTML only).

**Storage**: `database/kambale_thesis.sqlite` (canonical); `data/raw/` (immutable workbook copy); `data/derived/` (CSV delivery copies, non-authoritative); `sql/figures/*.sql` (figure queries); `migrations/*.sql` (DDL and views); `config/*.yaml` (decision and rule definitions).

**Testing**: pytest with unit tests (geometry, labels, hashing, triggers), integration tests (build on a temporary copy, rerun idempotence, figure manifest hashes), and database checks (`PRAGMA foreign_key_check`, `integrity_check`).

**Target Platform**: Windows 11 (PowerShell and Git Bash available), single-user desktop, no network required at run time.

**Project Type**: Single Python package with CLI (`src/kambale/`), plus SQL migrations and documentation.

**Performance Goals**: Full ETL and all Stage A figures complete in under 2 minutes on the supplied dataset (1,910 intervals, 71 holes). Not a throughput requirement.

**Constraints**: Raw data immutable; no `z_absolute_m` value without an approved elevation source; no label approval without a `label_reviews` row; no Stage B computation; no Excel access from rendering code; deterministic figure bytes where the renderer permits.

**Scale/Scope**: 71 collars, 71 survey stations, 1,910 logging intervals, 72 legend codes, 5 nominal drill lines, regional polygons intersecting a 10 km buffer around the collars.

## Constitution Check

*GATE: checked before Phase 0 and again after Phase 1 design.*

| Principle (constitution 1.0.0) | Compliance in this plan | Status |
|---|---|---|
| I. Source fidelity and raw immutability | Workbook copied to `data/raw/`, SHA-256 stored and re-verified each run; raw tables read with openpyxl cell values; UPDATE/DELETE triggers on `raw_*`. | PASS |
| II. SQLite as single source of truth | Curated facts and decisions live in `obj1_master`; figures query `v_*` views or `sql/figures/*.sql`; no Excel access in `figures/`. Regional polygons are ingested to a table first. | PASS |
| III. Honest geology | `z_absolute_m` NULL by construction; `elevation_sources` holds a BLOCKED row; labels are PROPOSED; unsupported and missing codes stay NULL. | PASS |
| IV. Explicit status and severity | `qaqc_findings` carries severity and status; every output carries a stage-status word. | PASS |
| V. Reproducibility and idempotence | `dataset_version_key` makes identical reruns a no-op; figure outputs registered with SQL and output hashes; SVG/PDF/PNG metadata suppressed. | PASS |
| VI. Leakage discipline and stage gating | Future tables are empty with no-write triggers; no fitting or prediction code exists in this feature. | PASS |
| VII. Verified claims only | `validation_test_results` stores pytest outcomes; `QAQC_REPORT.md` cites executed commands only. | PASS |

Re-check after Phase 1 design: PASS (no new violations introduced by the data model or contracts below).

## Project Structure

### Documentation (this feature)

```text
specs/001-kambale-o1-stage-a/
├── spec.md              # Feature specification (user stories, FR-001..FR-022, SC-001..SC-008)
├── plan.md              # This file
├── tasks.md             # Dependency-ordered tasks with evidence requirements
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── (seven stage deliverables 01–07 are written under specs/ as described in the Stage A prompt)
```

### Source Code (repository root = project folder)

```text
src/kambale/
├── __init__.py
├── config.py        # paths, ETL_VERSION, rule file names, stage-status vocabulary
├── db.py            # connect() with PRAGMA foreign_keys=ON; migration runner; schema_migrations
├── source.py        # SHA-256, workbook copy, openpyxl cell-level reads, inventory
├── ingest.py        # raw_* loading (immutable), legend and reference lists
├── curate.py        # holes, survey_stations, logging_intervals, code dictionary, HoleID normalisation
├── qaqc.py          # check catalogue, findings, severity/status, resolutions
├── labels.py        # evidence flags, conflicts, candidate rules from config/label_rules.yaml
├── geometry.py      # coordinate decision, straight-hole offsets, drill lines, interval_coordinates
├── regional.py      # regional geology polygons (geopandas) to regional_geology_context
├── build.py         # one transactional ETL; dataset_version_key; activation; receipts
├── verify.py        # integrity SQL, reconciliation, validation_test_results
├── registry.py      # figure registry, query hashes, output hashes, manifest CSV
├── figures/
│   ├── __init__.py
│   ├── style.py     # colour-blind-safe palette, footer, deterministic save
│   ├── objective1.py  # F01, F02, F03, F04 (static 3-D and strip logs), T01, T02
│   └── objective2.py  # F05..F09, T03 (descriptive, from O1 views)
├── reports.py       # QAQC_REPORT.md, DEFERRED_FIGURES.md, FIGURE_MANIFEST.csv, README stats
└── cli.py           # build | verify | plot | tables | report

migrations/
├── 0001_provenance.sql
├── 0002_raw.sql
├── 0003_curated_core.sql
├── 0004_labels.sql
├── 0005_geometry.sql
├── 0006_qaqc_audit.sql
├── 0007_future_contracts.sql
└── 0008_views.sql

sql/figures/         # one .sql per figure/table (F01..F09, T01..T03)
config/              # coordinate_decisions.yaml, label_rules.yaml, qaqc_thresholds.yaml
tests/               # test_hashing_raw.py, test_schema_integrity.py, test_geometry.py,
                     # test_labels.py, test_build_idempotence.py, test_figures_provenance.py
data/raw/            # unchanged workbook copy + SOURCE_HASH.txt
data/derived/        # CSV exports (non-authoritative delivery copies)
database/kambale_thesis.sqlite
figures/objective_1/ figures/objective_2/ tables/ reports/
```

**Structure Decision**: One package, one database, one CLI. Objectives 2–5 get their own databases in their own feature cycles; this feature only exposes `dataset_export_receipts` and read-only views for them. Descriptive Objective 2 figures (F05–F09, T03) are rendered from Objective 1 views because they are pure summaries of curated observations; when Objective 2 starts, they are re-computed into `database/kambale_obj2_spatial.sqlite` with receipts (the Architecture document assigns O2 summaries to that database).

## Design decisions (to be reviewed by the supervisor)

1. **Coordinates**: `UTMEasting/UTMNorthing` adopted as provisional planimetric pair; `Easting/Northing` retained as alternate. Rationale: the UTM-named pair is the explicitly UTM-labelled pair; the alternate pair lies on 5 m/10 m nodes (consistent with a planned grid) while the UTM pair does not. This is an inference, recorded as evidence, not as proof. Horizontal discrepancy: median 3.16 m, maximum 13.34 m (computed). Switchable through `config/coordinate_decisions.yaml`.
2. **CRS**: `EPSG:32630` (WGS 84 / UTM zone 30N) as the declared CRS, status PROVISIONAL; datum unverified. The regional shapefile is also declared EPSG:32630, and all collars fall in one regional polygon, which is a plausibility check only (1:1,000,000 context).
3. **Dip/azimuth**: convention "dip from horizontal, negative downward; azimuth clockwise from north" (PROVISIONAL). The single end-of-hole station (dip −60, azimuth 090) is applied to the whole hole as a straight-hole assumption (PROVISIONAL).
4. **Blank mineral field**: treated as "no code logged" and evidence of absence for `gr` under rule versions that use it; recorded in the rule text.
5. **Label rules**: four candidates (`STRICT_SGS_v1`, `RECON_2OF3_v1`, `ALL3_v1`, `ANY_v1`). A rule returns NULL when the rock code is missing or unsupported, or when evidence is mixed without enough positives. A label 0 additionally requires a present comment. The thresholds live in `config/label_rules.yaml`, and their text is stored in the rule row.
6. **Drill lines**: five groups by exact nominal Northing (1111930 n=3; 1112140 n=13; 1112500 n=21; 1112600 n=15; 1113000 n=19). Status PROVISIONAL; not a spatial split.
7. **Dataset version**: `dataset_version_key = sha256(source_sha256 | ETL_VERSION | canonical JSON of rule versions and coordinate decision)`. Identical key → no-op; new key → new ACTIVE version, previous version ARCHIVED, rows retained.
8. **Regional context**: polygons intersecting a 10 km buffer around collars are copied with WKT to `regional_geology_context`; figures read that table, not the shapefile.
9. **Hidden sheet metadata**: the `___SheetInfo` sheet contains a worksheet-protection string. It is stored in `raw_reference_lists` with the value replaced by `[REDACTED: sheet-protection string present in source]`. The original file is untouched and its hash is recorded.
10. **Figure determinism**: `svg.hashsalt` fixed; `metadata={'Date': None}` (SVG), `metadata={'CreationDate': None}` (PDF), `metadata={'Software': None}` (PNG).

## Phases

- **Phase 0 (research and inspection)**: complete. Workbook inventory, legend review, cross-tab reconciliation, coordinate comparison, shapefile check. Results are in `reports/` after Phase 4.
- **Phase 1 (design)**: this plan, data model in `specs/001-kambale-o1-stage-a/data-model.md`, contracts in `specs/001-kambale-o1-stage-a/contracts/` (CLI and read-only SQL interface for later objectives).
- **Phase 2 (tasks)**: `tasks.md`.
- **Phase 3 (implementation)**: migrations → raw ingest → curation → QA/QC → labels → geometry → build → views → figures/tables → tests → reports.
- **Phase 4 (verification and handover)**: run `pytest`, `verify`, regenerate all figures twice, compare hashes, write reports.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Descriptive O2 figures generated from O1 views (not from an O2 database) | The Stage A prompt requires F05–F09 now; the O2 database is not yet specified | Deferring F05–F09 would leave the data-supported Stage A catalogue incomplete. The O1 views are read-only summaries, so no second source of truth is created. |
| Regional geology context table | The rendering layer may not read shapefiles | Reading the shapefile in figure code would break the SQL-only rule. |

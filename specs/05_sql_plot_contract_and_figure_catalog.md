# 05 SQL plot contract and figure catalogue

## Contract

- Every figure and table is rendered from `sql/figures/*.sql` (one reproducible query per file, 22 files). The queries read only the `v_*` views (active dataset version) or raw tables for completeness counts.
- The rendering code (`src/kambale/figures.py`) does not import openpyxl, read the workbook, read the shapefile, or use the raw copy path. `tests/test_figures.py` enforces this.
- No `SELECT *` in any figure SQL (tested).
- Each run records, in SQLite: the SQL SHA-256 (`figure_query_registry`), row count, dataset version, analysis run, output SHA-256 and bytes, renderer module SHA-256 (`figure_export_manifest`), and the figure's stage status and caption (`figure_registry`).
- Outputs: figures as SVG, PDF and 300-dpi PNG; tables as CSV, Markdown and LaTeX.

## Figure catalogue (Stage A)

| ID | Objective | Title | SQL files | Denominator | Status | Geometry / label status |
|---|---|---|---|---|---|---|
| F01 | O1 | Collar location map | F01_collar_plan.sql, F01_regional.sql | 71 collars | PROVISIONAL | plan coordinates provisional; no RL |
| F02 | O1 | Drill-hole length distribution | F02_hole_lengths.sql | 71 holes; 1,910 m | VERIFIED | not used |
| F03 | O1 | Completeness and QA/QC summary | F03_completeness.sql, F03_qc_summary.sql | rows per sheet | VERIFIED | not used |
| F04 | O1 | 3-D relative-Z traces and interval strips (two files) | F04_3d_intervals.sql, F04_strip_logs.sql | 1,910 intervals | PROVISIONAL | relative Z only; STRICT rule PROPOSED |
| F05 | O2 | Lithology frequency and logged metres | F05_rock_usage.sql, F05_missing_codes.sql | 1,910 intervals; 1,910 m | VERIFIED | codes as logged |
| F06 | O2 | Graphitic apparent thickness and proportion by hole | F06_hole_graphite.sql | logged metres per hole | PROVISIONAL | STRICT and RECON PROPOSED |
| F07 | O2 | Graphitic intervals by depth bin and weathering | F07_depth_weathering.sql | intervals per 5 m bin | PROVISIONAL | measured depth |
| F08 | O2 | Plan map of graphitic fraction | F08_plan_graphite.sql, F01_regional.sql, F08_lines.sql | logged metres per hole | PROVISIONAL | plan provisional |
| F09 | O2 | Relative-Z sections by drill line | F09_sections.sql | 1,910 intervals | PROVISIONAL | common collar datum assumed |
| T01 | O1 | Workbook inventory, reconciliation, QC issues, integrity | T01_inventory.sql, T01_reconciliation.sql, T01_qc_issues.sql, T01_integrity.sql | raw and curated counts | VERIFIED | not used |
| T02 | O1 | Code dictionary and disagreement summary | T02_code_dictionary.sql, T02_label_disagreement.sql | 1,910 intervals | PROVISIONAL | PROPOSED rules |
| T03 | O2 | Graphitic evidence and ambiguity by hole and line | T03_hole_evidence.sql, T03_line_evidence.sql | logged metres | PROVISIONAL | PROPOSED rules |

Captions, footers and the coordinate and label caveats are stored in `figure_registry.caption` and drawn on every figure. Captions state units, support and status.

## Views used by the figure SQL

`v_active_version`, `v_source_file`, `v_holes`, `v_drill_lines`, `v_survey`, `v_intervals`, `v_label_evidence`, `v_label_candidates`, `v_label_candidate_counts`, `v_label_disagreement`, `v_interval_flags`, `v_hole_graphite`, `v_line_graphite`, `v_depth_weathering`, `v_rock_code_usage`, `v_collar_plan`, `v_interval_geometry`, `v_qaqc_summary`, `v_completeness`, `v_regional_context`, `v_export_receipts`, `v_figure_manifest` (migration 0008).

## Stage A figure rules

- Figures that show labels say PROPOSED; figures that show positions say PROVISIONAL; no figure uses the word "elevation" for relative values.
- Colour-blind-safe Okabe-Ito palette; red-orange = strict Sgs; blue = other valid code; grey = unresolved or blank.
- Footer on every figure: dataset key, label status, coordinate status, vertical reference.

## Deferred figures

See `DEFERRED_FIGURES.md` (D01-D13). Each deferred item has a `figure_registry` row with stage status DEFERRED and no output file (tested).

## Regeneration

```bash
kambale plot --figure F06
kambale plot --all
kambale tables
```

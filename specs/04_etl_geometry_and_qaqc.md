# 04 ETL, geometry and QA/QC

## ETL stages (one IMMEDIATE transaction after the ingestion run is recorded)

1. Migrations: `kambale build` applies `migrations/0001..0008` in order; each applied file's SHA-256 is recorded in `schema_migrations`, and an altered applied file is refused.
2. Raw copy: `ensure_raw_copy` hashes the source workbook and the `data/raw/` copy. A mismatch STOPS the build. The copy is created only when absent, and is made read-only.
3. Cell read: openpyxl reads every sheet cell-by-cell (no pandas coercion). Formulas are counted (0).
4. Curation (`curate.py`): normalisation, explicit date parsing, numeric checks, survey range checks, interval contiguity checks. Records that fail hard rules are quarantined (none in this dataset).
5. Raw insert: `raw_*` rows keyed by (source file, sheet, Excel row), inserted once. Identical rebuilds do not duplicate them.
6. Curated insert for the new dataset version: drill lines, holes, survey stations, code dictionary, intervals (with decoded codes and rock_code_status).
7. Labels: evidence per interval, five candidate rules (including the trace-excluded sensitivity rule), interval_labels per rule.
8. Geometry: coordinate registry and decision, geometry build, interval coordinates (relative Z only).
9. Regional context: polygons intersecting the buffer are copied as WKT.
10. QA/QC: findings, resolutions and catalogue entries.
11. Activation: the previous ACTIVE version becomes ARCHIVED; the new version becomes ACTIVE (partial unique index enforces one ACTIVE).
12. Receipts: `dataset_export_receipts` for four label exports, `interval_flags`, `hole_summary` and `interval_geometry`. These are computed after activation so the views resolve to the new version.
13. Checks: `PRAGMA foreign_key_check` and `PRAGMA integrity_check` inside the transaction. Any failure rolls back.

## Dataset version key

`dataset_version_key = SHA-256(canonical JSON of {source_sha256, etl_version, label_set_version, rules, coordinate decision, thresholds})`. Current key begins `de29be738dcc`. Identical key and ACTIVE: NOOP_IDENTICAL. Identical key and ARCHIVED: re-activation without duplication.

## Hole-to-survey-to-logging joins

- holes ← logging_intervals on (dataset_version_id, hole_id); survey_stations ← holes on the same key.
- Every interval joins a hole (0 orphans). Every collar has logs and a survey (QC-NO-LOG, QC-NO-SURVEY PASS).
- The survey station used for geometry is the single end-of-hole station (`station_kind = END_OF_HOLE_ONLY`, 71 holes). Holes with zero or several stations get no geometry and are reported.

## Geometry equations (straight hole, provisional)

- m = (DEPTH_FROM + DEPTH_TO) / 2
- delta_E = m cos(d) sin(a); delta_N = m cos(d) cos(a); delta_Z = m sin(d), with d = dip (negative downward, from horizontal) and a = azimuth (clockwise from north), in radians.
- Rounded to 0.1 mm. Easting = collar UTM easting + delta_E; Northing = collar UTM northing + delta_N.
- `z_relative_m` = delta_Z (below collar). `z_absolute_m` = NULL.
- Unit cases (tests/test_geometry.py): cardinal azimuths, vertical hole, dip -60 at azimuth 090 (delta_E = 0.5 m), out-of-convention refusal.
- Example (12KBRB 001, interval 0-1 m): m = 0.5, delta_E = 0.25, delta_N = 0, delta_Z = -0.433.

## Coordinate decision

- Adopted: UTMEasting/UTMNorthing (PROVISIONAL). Alternate: Easting/Northing (retained, not used for geometry).
- Pair discrepancy: median 3.1623 m; max 13.3417 m; holes > 5 m: 17; mean dE 0.73 m, dN -0.61 m; no systematic shift.
- Evidence for the alternate pair being a design grid: 71/71 values on 5 m nodes, versus 4/71 for the UTM pair. This is an inference, not proof.
- CRS: EPSG:32630 declared; datum unverified. Plausibility check: UTM collars transform to 10.0586–10.0684 N, 2.5601–2.5397 W.
- Nearest-neighbour spacing (UTM pair): median 21.02 m.

## Drill lines

Exact nominal Northing clusters: NOM_N1111930 (3 holes), NOM_N1112140 (13), NOM_N1112500 (21), NOM_N1112600 (15), NOM_N1113000 (19). Status PROVISIONAL. The 1112500 and 1112600 lines are 100 m apart.

## Vertical status

Collar RL missing for 71 of 71 holes. `elevation_sources` row 1 is BLOCKED. `interval_coordinates.z_absolute_m` is NULL for all 1,910 rows (CHECK constraint and verification query).

## QA/QC checks

The catalogue (`qaqc_checks`) has 53 checks in categories Provenance, Identifiers, Referential, Depth, Duplicates, Survey, Vertical, Metadata, Coordinates, Geometry, Context, Codes, Labels and Curation.

Outcome of the run (dataset-level rows):
- PASS: source hash, duplicate collars/logs/surveys, orphans, no-log and no-survey, overlap, gaps, log-end depth, survey range, dates, legend agreement, quarantine, regional context, label reconciliation, Sgs count.
- FAIL or WARNING (qualified, not corrected): RL missing (BLOCKED absolute), contractor blank, survey metadata blank, uniform orientation, single end-of-hole station, pair discrepancy, CRS datum unverified, drill-line grouping provisional, project label `Akoko`, unsupported code `fsc` (12 intervals, ERROR), missing rock code (1, WARNING), weathering blank (21), colour blank (6), comment blank (6), grain-size and intensity units, comment trace qualifiers (58), label conflicts (126).

Each per-record finding has a resolution: NULL_LABEL_UNRESOLVED, REVIEW_REQUIRED, or QUARANTINED.

## Determinism

- Matplotlib outputs use fixed SVG hash salt and suppressed date and software metadata, so reruns produce byte-identical files (tested for F06: `tests/test_figures.py::test_rerender_is_byte_identical`).
- Configuration: `config/coordinate_decisions.yaml`, `config/label_rules.yaml`, `config/qaqc_thresholds.yaml`. Changing any of them changes the dataset version key.

## Deterministic pipeline commands

```bash
kambale build
kambale verify
kambale plot --all
kambale tables
kambale report
```

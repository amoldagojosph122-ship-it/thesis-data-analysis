# Kambale Objective 1 database: QA/QC report (Stage A)

Generated 2026-11-05T07:45:45Z from `database/kambale_thesis.sqlite`.

**Overall stage status: PROVISIONAL.** The ETL, integrity checks and reconciliation are verified. Coordinates,
vertical positions, graphitic label rules and drill-line groups are provisional. No collar RL exists, so no
absolute 3-D product is produced. No graphite assay exists, so no grade, tonnage or resource statement is made.

- Dataset version: `741da971d12cfaf269e421d2094709031f911e00c803a004e907f743a1067796` (label: obj1_master ETL 1.1.0 key 741da971d12c), ACTIVE, activated 2026-11-05T07:36:24Z.
- Source workbook: `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx`, SHA-256 `a449097f669b9a449d06acfdb31c62ccbc688936c90254a829ecade2b95dbfb6`, 107,376 bytes; raw copy `data/raw/Kambale RAB_Collar_Sampling_Geology_2012a.xlsx` (read-only, hash-checked).

## 1. Source inventory and record counts

| Sheet | State | Rows | Columns | Blank columns |
|---|---|---|---|---|
| Collars | visible | 72 | 14 | ["RL", "Contractor"] |
| Logging | visible | 1911 | 19 | ["structure", "sul_min1", "sul_min1pc", "vn_type", "vn_pc", "sample_quality"] |
| Logging Legend | visible | 205 | 4 | [] |
| Surveys | visible | 72 | 6 | ["SurveyedBy", "Instrument"] |
| ___CollarReferences | hidden | 54 | 5 | [] |
| ___LoggingReferences | hidden | 74 | 8 | [] |
| ___SheetInfo | hidden | 3 | 2 | [] |
| ___SurveyReferences | hidden | 14 | 2 | [] |

Reconciliation against the preliminary values in ThesisDesign.docx (comparison only; no value was forced to match):

| Item | Observed | Curated | ThesisDesign reference |
|---|---|---|---|
| Collars rows (raw) | 71 | 71 | 71 |
| Surveys rows (raw) | 71 | 71 | 71 |
| Logging rows (raw) | 1910 | 1910 | 1910 |
| Logged metres (sum of 1-m intervals) | 1910 | 1910.0 | 1910 |
| Intervals with rock_type1 = Sgs | 529 | 529 | 529 |
| Holes intersecting Sgs | 42 | 42 | 42 |

## 2. QA/QC findings

| Check | Severity | Status | Result | Records | Description |
|---|---|---|---|---|---|
| QC-CODE-ROCK-UNSUPPORTED | ERROR | BLOCKED | FAIL | 12 | rock_type1 code not in logging legend |
| QC-DATE | ERROR | APPROVED | PASS | 71 | DateDrilled parses under the explicit format %d-%m-%Y |
| QC-DEPTH-INTERVAL | ERROR | APPROVED | PASS | 0 | Non-numeric, negative or DEPTH_FROM >= DEPTH_TO intervals |
| QC-DUP-LOG | ERROR | APPROVED | PASS | 0 | Duplicate logging interval (hole, DEPTH_FROM) |
| QC-DUP-SURVEY | ERROR | APPROVED | PASS | 0 | Duplicate survey station (hole, depth) |
| QC-HOLEID-DUP | ERROR | APPROVED | PASS | 0 | Duplicate normalised HoleID in Collars |
| QC-ORPHAN-LOG | ERROR | APPROVED | PASS | 0 | Logging interval whose hole is not in Collars |
| QC-ORPHAN-SURVEY | ERROR | APPROVED | PASS | 0 | Survey record whose hole is not in Collars |
| QC-OVERLAP | ERROR | APPROVED | PASS | 0 | Overlapping logging intervals within a hole |
| QC-QUARANTINE | ERROR | APPROVED | PASS | 0 | Records excluded from curated tables by a hard rule |
| QC-SRC-HASH | ERROR | APPROVED | PASS | 0 | Workbook SHA-256 equals raw copy SHA-256 |
| QC-SURVEY-RANGE | ERROR | APPROVED | PASS | 0 | Dip outside [-90, 0] or azimuth outside [0, 360) |
| QC-CODE-ROCK-MISSING | WARNING | PROVISIONAL | FAIL | 1 | rock_type1 blank |
| QC-CODE-WEATHER-MISSING | WARNING | PROVISIONAL | FAIL | 21 | weathering blank |
| QC-COMMENT-MISSING | WARNING | PROVISIONAL | FAIL | 6 | Comment blank |
| QC-COMMENT-TRACE | WARNING | PROVISIONAL | FAIL | 56 | Graphite comment qualified by 'trace' (false-positive review) |
| QC-COORD-PAIR | WARNING | PROVISIONAL | FAIL | 17 | Discrepancy between UTM and Easting/Northing pairs |
| QC-CRS | WARNING | PROVISIONAL | FAIL | 0 | CRS declared and datum verified |
| QC-GAP | WARNING | APPROVED | PASS | 0 | Gaps between consecutive logging intervals or first interval not at 0 m |
| QC-GRAINSIZE | WARNING | PROVISIONAL | FAIL | 513 | grainsize values present without documented unit |
| QC-INTENSITY | WARNING | PROVISIONAL | FAIL | 16 | alt_min1int present without alt_min1 code |
| QC-INTENSITY-UNITS | WARNING | PROVISIONAL | FAIL | 0 | alt_min1int unit undocumented |
| QC-LABEL-CONFLICT | WARNING | PROVISIONAL | FAIL | 126 | Intervals with mixed graphite evidence |
| QC-LEGEND-AGREE | WARNING | APPROVED | PASS | 0 | Legend and hidden reference lists agree |
| QC-LINES | WARNING | PROVISIONAL | FAIL | 5 | Nominal Northing groups and provisional drill lines |
| QC-LOG-END | WARNING | APPROVED | PASS | 0 | Logged end depth versus collar max_depth |
| QC-NO-LOG | WARNING | APPROVED | PASS | 0 | Collar with no logging intervals |
| QC-NO-SURVEY | WARNING | APPROVED | PASS | 0 | Collar with no survey record |
| QC-PROJECT | WARNING | PROVISIONAL | FAIL | 5 | Project code inconsistent with prospect |
| QC-RL | WARNING | BLOCKED | FAIL | 71 | Collar RL present |
| QC-SURVEY-DEPTH | WARNING | APPROVED | PASS | 0 | Survey depth versus collar max_depth |
| QC-SURVEY-META | WARNING | PROVISIONAL | FAIL | 71 | SurveyedBy and Instrument blank in source |
| QC-SURVEY-STATIONS | WARNING | PROVISIONAL | FAIL | 71 | Number and type of survey stations per hole |
| QC-SURVEY-UNIFORM | WARNING | PROVISIONAL | FAIL | 71 | Dip and azimuth identical across all holes |
| QC-BLANK-COLUMNS | INFO | APPROVED | PASS | 0 | Columns with no data in source |
| QC-BLANK-ROWS | INFO | APPROVED | PASS | 0 | Fully blank rows skipped during ingestion |
| QC-CODE-COLOUR-MISSING | INFO | PROVISIONAL | FAIL | 6 | colour1 blank |
| QC-CONTRACTOR | INFO | PROVISIONAL | FAIL | 71 | Contractor blank in source |
| QC-COORD-NODES | INFO | APPROVED | PASS | 0 | Values on 5 m grid nodes by pair |
| QC-CRS-PLAUSIBILITY | INFO | APPROVED | PASS | 0 | Transformed collar location lies in the expected region |
| QC-HOLEID-RAW | INFO | APPROVED | PASS | 0 | Raw HoleID spelling differs from normalised form |
| QC-LABEL-RECON | INFO | APPROVED | PASS | 1910 | Evidence distribution versus ThesisDesign.docx |
| QC-LEGEND-UNUSED | INFO | APPROVED | PASS | 64 | Legend codes never used in logging |
| QC-NN-SPACING | INFO | APPROVED | PASS | 0 | Median nearest-neighbour collar spacing |
| QC-REGIONAL | INFO | APPROVED | PASS | 9 | Collars inside regional 1:1,000,000 polygons |
| QC-ROW-RECON | INFO | APPROVED | PASS | 0 | Data-row counts per sheet recomputed from the workbook |
| QC-SGS-COUNT | INFO | APPROVED | PASS | 529 | Sgs interval count versus ThesisDesign.docx |
| QC-SHEET-INVENTORY | INFO | APPROVED | PASS | 0 | Sheet inventory, states and hidden reference sheets |
| QC-SUPPORT | INFO | APPROVED | PASS | 1910 | Sample support: interval length distribution |
| QC-WEATHER-UNUSED | INFO | APPROVED | PASS | 2 | Legend weathering codes never used |

Detail text for each dataset-level finding is stored in `qaqc_findings.detail`.

## 3. Decisions and their status

| Adopted pair | CRS | Datum | Status | Median pair separation (m) | Max pair separation (m) | Holes |
|---|---|---|---|---|---|---|
| UTM_EASTING_NORTHING | EPSG:32630 | UNVERIFIED | PROVISIONAL | 3.1623 | 13.3417 | 71 |

| Rule | Version | Family | Status | Definition |
|---|---|---|---|---|
| ALL3_v1 | 1.0.0 | SENSITIVITY | PROPOSED | Conservative sensitivity definition. Label 1 only when all three indicators are positive; label 0 when none is positive; otherwise UNRESOLVED. |
| ANY_v1 | 1.0.0 | SENSITIVITY | PROPOSED | Liberal sensitivity definition. Label 1 when any indicator is positive; label 0 when none is positive and a comment is present. Included to show how far the label depends on the rule. |
| DESIGN_8_2_v1 | 1.0.0 | RECONCILED | PROPOSED | Target B as set out in ThesisDesign section 8.2 (reconciled; review form). Label 1 when the rock code is Sgs, at least one further indicator supports it and the description does not conflict. Label 0 when the code is another valid legend code, no graphite indicator is present and a comment exists. Ambiguous (no label) when only one indicator is present, or when the code and the other evidence disagree. Unresolved when the code is missing or unsupported, or when a non-Sgs interval has a blank comment. A blank graphite field is not counted against graphite. |
| RECON_2OF3_NOTRACE_v1 | 1.0.0 | SENSITIVITY | PROPOSED | Sensitivity to Target B. As RECON_2OF3_v1, except that a comment in which graphite is qualified by a trace ("traces of graphite") is not counted as positive evidence. Such an interval is negative when no other indicator is positive and a comment is present. |
| RECON_2OF3_v1 | 1.0.0 | RECONCILED | PROPOSED | Target B candidate (reconciled). Label 1 when at least two of the three logging indicators are positive; label 0 when none is positive and a comment is present; one positive indicator is left UNRESOLVED for geological review (ThesisDesign section 8.2 "Ambiguous"). |
| STRICT_SGS_v1 | 1.0.0 | STRICT | PROPOSED | Target A (strict). Label 1 when rock_type1 is Sgs (meta-sediment graphite schist); label 0 when rock_type1 is another valid legend code; unresolved for missing or unsupported codes. |



### Candidate label counts (1-m intervals; a label is UNRESOLVED when the rock code is missing or unsupported, or when evidence is partial)

| Rule | Label state | Intervals | Logged m |
|---|---|---|---|
| ALL3_v1 | NEGATIVE | 1289 | 1289.0 |
| ALL3_v1 | POSITIVE | 476 | 476.0 |
| ALL3_v1 | UNRESOLVED | 145 | 145.0 |
| ANY_v1 | NEGATIVE | 1289 | 1289.0 |
| ANY_v1 | POSITIVE | 605 | 605.0 |
| ANY_v1 | UNRESOLVED | 16 | 16.0 |
| DESIGN_8_2_v1 | AMBIGUOUS | 81 | 81.0 |
| DESIGN_8_2_v1 | NEGATIVE | 1289 | 1289.0 |
| DESIGN_8_2_v1 | POSITIVE | 524 | 524.0 |
| DESIGN_8_2_v1 | UNRESOLVED | 16 | 16.0 |
| RECON_2OF3_NOTRACE_v1 | NEGATIVE | 1310 | 1310.0 |
| RECON_2OF3_NOTRACE_v1 | POSITIVE | 527 | 527.0 |
| RECON_2OF3_NOTRACE_v1 | UNRESOLVED | 73 | 73.0 |
| RECON_2OF3_v1 | NEGATIVE | 1289 | 1289.0 |
| RECON_2OF3_v1 | POSITIVE | 562 | 562.0 |
| RECON_2OF3_v1 | UNRESOLVED | 59 | 59.0 |
| STRICT_SGS_v1 | NEGATIVE | 1368 | 1368.0 |
| STRICT_SGS_v1 | POSITIVE | 529 | 529.0 |
| STRICT_SGS_v1 | UNRESOLVED | 13 | 13.0 |

| Evidence pattern | Review status | Intervals |
|---|---|---|
| NONE | CONSISTENT_NEGATIVE | 1289 |
| SGS+GR+CMT | CONSISTENT_POSITIVE | 476 |
| SGS+CMT | CONFLICT_REVIEW_REQUIRED | 45 |
| CMT | CONFLICT_REVIEW_REQUIRED | 37 |
| GR+CMT | CONFLICT_REVIEW_REQUIRED | 33 |
| NONE/ROCK_UNSUPPORTED | UNRESOLVED_CODE | 12 |
| GR | CONFLICT_REVIEW_REQUIRED | 6 |
| SGS+GR | CONFLICT_REVIEW_REQUIRED | 5 |
| NONE | UNRESOLVED_NO_COMMENT | 3 |
| SGS+GR | UNRESOLVED_PARTIAL_EVIDENCE | 3 |
| GR+CMT/ROCK_MISSING | UNRESOLVED_CODE | 1 |

### Interpretation of the label evidence

- The three fields are logged indicators (rock code `Sgs`; mineral code `gr`; comment containing "graphit").
  They are not independent laboratory confirmations and do not measure graphite grade.
- The six candidate rules (STRICT_SGS_v1 for Target A, DESIGN_8_2_v1 for the ThesisDesign 8.2 Target B, the earlier reconciled candidates RECON_2OF3_v1, ALL3_v1 and ANY_v1, and the trace-excluded sensitivity RECON_2OF3_NOTRACE_v1) are PROPOSED. None is approved. `label_reviews` is empty, and a database trigger blocks
  approval without an APPROVE_RULE review.
- Conflicts are counted with the rule written in `config/label_rules.yaml`. The conflict count is 126: the naive count
  of 130 mixed-evidence intervals excludes one interval with an unsupported or missing code and three intervals
  with a blank comment, which stay unresolved.

## 4. Geometry and vertical status

- Method: straight-hole, single end-of-hole orientation (dip -60, azimuth 090 at all holes). PROVISIONAL.
- Offsets: delta_E = m cos(d) sin(a), delta_N = m cos(d) cos(a), delta_Z = m sin(d); m = interval midpoint.
- `z_relative_m` is stored relative to the collar. `z_absolute_m` is NULL for every interval (verified by `kambale verify`).
- Elevation status: BLOCKED (no collar RL in the workbook; no DGPS or DEM supplied).

## 5. Provisional drill lines and regional context

| Line | Nominal Northing (m) | Holes | Intervals | Status |
|---|---|---|---|---|
| NOM_N1111930 | 1111930.0 | 3 | 84 | PROVISIONAL |
| NOM_N1112140 | 1112140.0 | 13 | 440 | PROVISIONAL |
| NOM_N1112500 | 1112500.0 | 21 | 542 | PROVISIONAL |
| NOM_N1112600 | 1112600.0 | 15 | 423 | PROVISIONAL |
| NOM_N1113000 | 1113000.0 | 19 | 421 | PROVISIONAL |

Regional polygons are 1:1,000,000 context only and do not verify local contacts:

| GEO_SYMBOL | Stratigraphy | Legend text |
|---|---|---|
| bmbt | Birimian Supergroup | Biotite schist |
| bs | Birimian Supergroup | Sediment/volcaniclastic sediment, undifferentiated, locally mica schist |
| bvc | Birimian Supergroup | Undifferentiated volcaniclastics, spatially associated and interbedded with flow rock |
| gsb | Eburnean Plutonic Suite | Biotite (+/- hornblende, +/- muscovite) granitoid, undifferentiated |
| gsh | Eburnean Plutonic Suite | Hornblende-biotite granitoid, undifferentiated |
| msd | Mesozoic | Mafic dyke, dolerite (inferred from aeromagnetic data, may include pre-Mesozoic dykes, may be concealed by Voltaian cover) |
| tmbz | 'Tamnean' Plutonic Suite | Biotite-hornblende (monzo)granite, quartz monzodiorite and monzodiorite |

## 6. Verification results (latest run)

| Group | Test | Expected | Observed | Outcome | Run (UTC) |
|---|---|---|---|---|---|
| PYTEST | pytest suite (tests/) | 0 failed | 81 passed in 6.82s | PASS | 2026-11-05T07:42:13Z |
| RECONCILIATION | Holes | 71 | 71 | PASS | 2026-11-05T07:42:03Z |
| RECONCILIATION | Holes intersecting Sgs | 42 | 42 | PASS | 2026-11-05T07:42:03Z |
| RECONCILIATION | Logging intervals | 1910 | 1910 | PASS | 2026-11-05T07:42:03Z |
| RECONCILIATION | Sgs intervals | 529 | 529 | PASS | 2026-11-05T07:42:03Z |
| RECONCILIATION | Survey stations | 71 | 71 | PASS | 2026-11-05T07:42:03Z |
| SQL_INTEGRITY | PRAGMA foreign_key_check | 0 rows | 0 rows | PASS | 2026-11-05T07:42:03Z |
| SQL_INTEGRITY | PRAGMA integrity_check | ok | ok | PASS | 2026-11-05T07:42:03Z |
| SQL_INTEGRITY | Stage B contract tables: blocking triggers present and empty | 9 triggers; 0 rows | 9 triggers; 0 rows | PASS | 2026-11-05T07:42:03Z |
| SQL_INTEGRITY | one lithology refinement row per active interval | 1910 | 1910 | PASS | 2026-11-05T07:42:03Z |
| SQL_INTEGRITY | raw_* UPDATE rejected by trigger | rejected | rejected | PASS | 2026-11-05T07:42:03Z |
| SQL_INTEGRITY | z_absolute_m non-null rows | 0 | 0 | PASS | 2026-11-05T07:42:03Z |

## 7. Data problems and decisions still pending

1. Coordinate datum and pair choice: confirm the UTM pair (adopted, provisional) or the Easting/Northing pair. 17 holes differ by more than 5 m.
2. Collar RL: obtain the DGPS collar elevations or approve a DEM method. Until then, no absolute elevation exists.
3. Graphitic label rule: a supervising geologist must review the six candidate rules and the 126 conflicts (`ambiguity_review_intervals.csv`).
4. Unsupported rock code `fsc` (12 intervals, quartz mica schist comments) is not mapped. It is not assumed to equal `Fsc`.
5. One interval has a blank rock code (12KBRB 005, 8-9 m) with graphite mineral and comment evidence.
6. Dip and azimuth are a single end-of-hole nominal orientation; SurveyedBy and Instrument are blank.
7. The project label `Akoko` appears on five holes within the KAMBALE prospect.
8. Intensity (`alt_min1int`) and grain-size (`grainsize`) values have no documented units; they are not used in any derivation.
9. Contractor is blank for all holes; weathering `fr` (fresh) is never logged.
10. The hidden `___SheetInfo` sheet contains a worksheet-protection string. It is redacted in the database. The original file is unchanged.

## 8. Rerun commands

```bash
kambale build           # verified ETL; identical source and configuration is a no-op
kambale verify          # SQL integrity, reconciliation, Stage B blocking, pytest suite
kambale plot --all      # figures F01..F09 with registry rows and hashes
kambale tables          # tables T01..T03 (CSV, Markdown, LaTeX)
kambale report          # this report, FIGURE_MANIFEST.csv, DEFERRED_FIGURES.md, data/derived/*.csv
```

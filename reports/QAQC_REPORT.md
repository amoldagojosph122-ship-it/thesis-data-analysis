# Kambale Objective 1 database: QA/QC report (Stage A)

Generated 2026-11-05T12:25:25Z from `database/kambale_thesis.sqlite`.

**Overall stage status: PROVISIONAL.** The ETL, integrity checks and reconciliation are verified. The UTM coordinates and the WGS 84 datum are approved (2026-11-05). Vertical positions are provisional. The drill-line groups are approved (2026-11-05). Graphitic label rules other than DESIGN_8_2_v1 are provisional. No collar RL exists. The Copernicus
DEM elevations were approved on 2026-11-05 as the provisional vertical source (Dickson Abdul-Wahab, 10:46:46 UTC) and
are stored apart from the RL field. No graphite assay exists, so no grade, tonnage or resource statement is made.

- Dataset version: `55dead7da64cac14b0d79569e460739f8b9a217b17425a3e3ff2610649940248` (label: obj1_master ETL 1.5.0 key 55dead7da64c), ACTIVE, activated 2026-11-05T12:25:03Z.
- Source workbook: `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx`, SHA-256 `4840a9917a11dac22b190609c71f4eb0e0491fe7ab306ca09b02521cf9bf5e5a`, 107,538 bytes; raw copy `data/raw/Kambale RAB_Collar_Sampling_Geology_2012a_corrected_2026-11-05_rock_codes.xlsx` (read-only, hash-checked).

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
| Intervals with rock_type1 = Sgs | 529 | 530 | 529 |
| Holes intersecting Sgs | 42 | 42 | 42 |

## 2. QA/QC findings

| Check | Severity | Status | Result | Records | Description |
|---|---|---|---|---|---|
| QC-CODE-ROCK-UNSUPPORTED | ERROR | APPROVED | PASS | 0 | rock_type1 code not in logging legend |
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
| QC-CODE-ROCK-MISSING | WARNING | APPROVED | PASS | 0 | rock_type1 blank |
| QC-CODE-WEATHER-MISSING | WARNING | PROVISIONAL | FAIL | 21 | weathering blank |
| QC-COMMENT-MISSING | WARNING | APPROVED | PASS | 0 | Comment blank |
| QC-COMMENT-TRACE | WARNING | PROVISIONAL | FAIL | 56 | Graphite comment qualified by 'trace' (false-positive review) |
| QC-COORD-PAIR | WARNING | APPROVED | FAIL | 17 | Discrepancy between UTM and Easting/Northing pairs |
| QC-CRS | WARNING | APPROVED | PASS | 0 | CRS declared and datum verified |
| QC-GAP | WARNING | APPROVED | PASS | 0 | Gaps between consecutive logging intervals or first interval not at 0 m |
| QC-GRAINSIZE | WARNING | PROVISIONAL | FAIL | 513 | grainsize values present without documented unit |
| QC-INTENSITY | WARNING | PROVISIONAL | FAIL | 16 | alt_min1int present without alt_min1 code |
| QC-INTENSITY-UNITS | WARNING | PROVISIONAL | FAIL | 0 | alt_min1int unit undocumented |
| QC-LABEL-CONFLICT | WARNING | PROVISIONAL | FAIL | 126 | Intervals with mixed graphite evidence |
| QC-LEGEND-AGREE | WARNING | APPROVED | PASS | 0 | Legend and hidden reference lists agree |
| QC-LINES | WARNING | APPROVED | PASS | 5 | Nominal Northing groups and drill lines |
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
| QC-LABEL-RECON | INFO | PROVISIONAL | FAIL | 1910 | Evidence distribution versus ThesisDesign.docx |
| QC-LEGEND-UNUSED | INFO | APPROVED | PASS | 64 | Legend codes never used in logging |
| QC-NN-SPACING | INFO | APPROVED | PASS | 0 | Median nearest-neighbour collar spacing |
| QC-REGIONAL | INFO | APPROVED | PASS | 9 | Collars inside regional 1:1,000,000 polygons |
| QC-ROW-RECON | INFO | APPROVED | PASS | 0 | Data-row counts per sheet recomputed from the workbook |
| QC-SGS-COUNT | INFO | PROVISIONAL | FAIL | 530 | Sgs interval count versus ThesisDesign.docx |
| QC-SHEET-INVENTORY | INFO | APPROVED | PASS | 0 | Sheet inventory, states and hidden reference sheets |
| QC-SUPPORT | INFO | APPROVED | PASS | 1910 | Sample support: interval length distribution |
| QC-WEATHER-UNUSED | INFO | APPROVED | PASS | 2 | Legend weathering codes never used |

Detail text for each dataset-level finding is stored in `qaqc_findings.detail`.

## 3. Decisions and their status

| Adopted pair | CRS | Datum | Status | Median pair separation (m) | Max pair separation (m) | Holes |
|---|---|---|---|---|---|---|
| UTM_EASTING_NORTHING | EPSG:32630 | UNVERIFIED | APPROVED | 3.1623 | 13.3417 | 71 |

| Rule | Version | Family | Status | Definition |
|---|---|---|---|---|
| ALL3_v1 | 1.0.0 | SENSITIVITY | PROPOSED | Conservative sensitivity definition. Label 1 only when all three indicators are positive; label 0 when none is positive; otherwise UNRESOLVED. |
| ANY_v1 | 1.0.0 | SENSITIVITY | PROPOSED | Liberal sensitivity definition. Label 1 when any indicator is positive; label 0 when none is positive and a comment is present. Included to show how far the label depends on the rule. |
| DESIGN_8_2_v1 | 1.0.0 | RECONCILED | APPROVED | Target B as set out in ThesisDesign section 8.2 (reconciled; review form). Label 1 when the rock code is Sgs, at least one further indicator supports it and the description does not conflict. Label 0 when the code is another valid legend code, no graphite indicator is present and a comment exists. Ambiguous (no label) when only one indicator is present, or when the code and the other evidence disagree. Unresolved when the code is missing or unsupported, or when a non-Sgs interval has a blank comment. A blank graphite field is not counted against graphite. |
| RECON_2OF3_NOTRACE_v1 | 1.0.0 | SENSITIVITY | PROPOSED | Sensitivity to Target B. As RECON_2OF3_v1, except that a comment in which graphite is qualified by a trace ("traces of graphite") is not counted as positive evidence. Such an interval is negative when no other indicator is positive and a comment is present. |
| RECON_2OF3_v1 | 1.0.0 | RECONCILED | PROPOSED | Target B candidate (reconciled). Label 1 when at least two of the three logging indicators are positive; label 0 when none is positive and a comment is present; one positive indicator is left UNRESOLVED for geological review (ThesisDesign section 8.2 "Ambiguous"). |
| STRICT_SGS_v1 | 1.0.0 | STRICT | PROPOSED | Target A (strict). Label 1 when rock_type1 is Sgs (meta-sediment graphite schist); label 0 when rock_type1 is another valid legend code; unresolved for missing or unsupported codes. |



### Candidate label counts (1-m intervals; a label is UNRESOLVED when the rock code is missing or unsupported, or when evidence is partial)

| Rule | Label state | Intervals | Logged m |
|---|---|---|---|
| ALL3_v1 | NEGATIVE | 1304 | 1304.0 |
| ALL3_v1 | POSITIVE | 480 | 480.0 |
| ALL3_v1 | UNRESOLVED | 126 | 126.0 |
| ANY_v1 | NEGATIVE | 1304 | 1304.0 |
| ANY_v1 | POSITIVE | 606 | 606.0 |
| DESIGN_8_2_v1 | AMBIGUOUS | 81 | 81.0 |
| DESIGN_8_2_v1 | NEGATIVE | 1304 | 1304.0 |
| DESIGN_8_2_v1 | POSITIVE | 525 | 525.0 |
| RECON_2OF3_NOTRACE_v1 | NEGATIVE | 1325 | 1325.0 |
| RECON_2OF3_NOTRACE_v1 | POSITIVE | 528 | 528.0 |
| RECON_2OF3_NOTRACE_v1 | UNRESOLVED | 57 | 57.0 |
| RECON_2OF3_v1 | NEGATIVE | 1304 | 1304.0 |
| RECON_2OF3_v1 | POSITIVE | 563 | 563.0 |
| RECON_2OF3_v1 | UNRESOLVED | 43 | 43.0 |
| STRICT_SGS_v1 | NEGATIVE | 1380 | 1380.0 |
| STRICT_SGS_v1 | POSITIVE | 530 | 530.0 |

| Evidence pattern | Review status | Intervals |
|---|---|---|
| NONE | CONSISTENT_NEGATIVE | 1304 |
| SGS+GR+CMT | CONSISTENT_POSITIVE | 480 |
| SGS+CMT | CONFLICT_REVIEW_REQUIRED | 45 |
| CMT | CONFLICT_REVIEW_REQUIRED | 37 |
| GR+CMT | CONFLICT_REVIEW_REQUIRED | 33 |
| GR | CONFLICT_REVIEW_REQUIRED | 6 |
| SGS+GR | CONFLICT_REVIEW_REQUIRED | 5 |

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
- Surveyed elevation status: BLOCKED (no collar RL in the workbook; no DGPS supplied).
- Approved as the provisional vertical source on 2026-11-05 (Dickson Abdul-Wahab): Copernicus GLO-30 sampled at each collar (`holes.dem_elevation_m`, status PROVISIONAL);
  the interval values are `interval_coordinates.z_dem_absolute_m`. The DEM is a surface model that includes vegetation
  and buildings, so it is not a surveyed collar RL.

## 5. Drill lines (approved nominal-Northing groups) and regional context

| Line | Nominal Northing (m) | Holes | Intervals | Status |
|---|---|---|---|---|
| NOM_N1111930 | 1111930.0 | 3 | 84 | APPROVED |
| NOM_N1112140 | 1112140.0 | 13 | 440 | APPROVED |
| NOM_N1112500 | 1112500.0 | 21 | 542 | APPROVED |
| NOM_N1112600 | 1112600.0 | 15 | 423 | APPROVED |
| NOM_N1113000 | 1113000.0 | 19 | 421 | APPROVED |

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

## 7. Data problems and decisions still pending

1. Coordinate pair: the UTM pair was approved on 2026-11-05. 17 holes differ by more than 5 m from the Easting/Northing pair; the difference is recorded, not corrected. The datum is confirmed as WGS 84 (2026-11-05).
2. Collar RL: obtain the DGPS collar elevations. The DEM elevations are approved as the provisional vertical source (2026-11-05); a surveyed RL would replace them.
3. Graphitic label rules: DESIGN_8_2_v1 (Target B) was approved on 2026-11-05 by Dickson Abdul-Wahab. STRICT_SGS_v1 (Target A) and the other candidate rules remain PROPOSED. The conflicts are listed in `ambiguity_review_intervals.csv`.
4. Corrected from the original log on 2026-11-05: 12 intervals logged `fsc` (not in the legend, quartz mica schist comments) are now `Fsc` (felsic schist).
5. Corrected from the original log on 2026-11-05: the blank rock code on 12KBRB 005 (8-9 m) is now `Sgs`, matching its comment.
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

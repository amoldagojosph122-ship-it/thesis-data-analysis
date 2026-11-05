# 02 Workbook audit and data contract

Source: `Kambale RAB_Collar_Sampling_Geology_2012a.xlsx`, SHA-256 `a449097f669b9a449d06acfdb31c62ccbc688936c90254a829ecade2b95dbfb6` (verified equal to `data/raw/` copy).

## 1. Sheet inventory (recomputed by `kambale build`)

| Sheet | State | Data rows | Columns | Notes |
|---|---|---|---|---|
| Collars | visible | 71 | 14 | Header row 1 |
| Surveys | visible | 71 | 6 | Header row 1 |
| Logging | visible | 1,910 | 19 | Header row 1 |
| Logging Legend | visible | 203 | 4 (A blank) | Header row 2; title merged B1:D1 |
| ___LoggingReferences | hidden | 8 code lists | 8 | RockType 72, Colour 13, Weathering 6, Structure 68, RTMineral 23, SulMineral 10, Veining 5, SampleQual 6 |
| ___SurveyReferences | hidden | - | 2 | DHSurveyorID and SurveyInstrumentID lists |
| ___CollarReferences | hidden | - | 5 | Grid, HoleType, ProjectCode, ProspectCode, DrillContractorID lists |
| ___SheetInfo | hidden | 2 | 2 | Contains a worksheet-protection string: redacted in the database |

Formula cells: none detected. Blank rows skipped: 0.

## 2. Field audit

| Sheet.field | Non-blank | Observation |
|---|---|---|
| Collars.RL | 0 / 71 | Absent. Absolute elevation BLOCKED. |
| Collars.Contractor | 0 / 71 | Absent. |
| Collars.Grid | 71 / 71 | UTM_30N for all holes |
| Collars.Northing, Easting | 71 / 71 | All multiples of 5 m; 71/71 on 5 m nodes |
| Collars.UTMNorthing, UTMEasting | 71 / 71 | 4/71 on 5 m nodes; median pair separation 3.16 m; max 13.34 m; 17 holes > 5 m |
| Collars.Project | 71 / 71 | `Wa` 66, `Akoko` 5 (inconsistent with prospect KAMBALE for holes 055, 059, 063, 067, 071) |
| Collars.DateDrilled | 71 / 71 | Text dd-mm-yyyy, 17-23 March 2012; parsed with explicit format |
| Surveys.depth | 71 / 71 | Equals max_depth for every hole (single end-of-hole station) |
| Surveys.dip | 71 / 71 | -60 for all |
| Surveys.azimuth | 71 / 71 | 90 for all |
| Surveys.SurveyedBy, Instrument | 0 / 71 | Absent |
| Logging.DEPTH_FROM/TO | 1,910 / 1,910 | Integers; every interval 1 m; contiguous from 0; no overlap or gap |
| Logging.rock_type1 | 1,909 / 1,910 | 1 blank (12KBRB 005, 8-9 m) |
| Logging.weathering | 1,889 / 1,910 | 21 blank; `fr` never used |
| Logging.colour1 | 1,904 / 1,910 | 6 blank |
| Logging.alt_min1 | 524 / 1,910 | all `gr` |
| Logging.alt_min1int | 539 / 1,910 | units undocumented; 16 without alt_min1 |
| Logging.alt_min2 | 18 / 1,910 | `mn` |
| Logging.grainsize | 513 / 1,910 | all 0.2; units undocumented; not used |
| Logging.structure, sul_min1, sul_min1pc, vn_type, vn_pc, sample_quality | 0 / 1,910 | Blank columns |
| Logging.Comment | 1,904 / 1,910 | 6 blank |

## 3. Code mapping

- RockType codes are taken from `Logging Legend` (72 codes). The hidden `___LoggingReferences` list is identical (`QC-LEGEND-AGREE` PASS).
- `fsc` (12 intervals, quartz mica schist) is not in the legend (legend has `Fsc`). It is UNSUPPORTED and is not mapped.
- `Sgs` = "meta-sediment graphite schist" (legend). `Sbs` = "meta-sediment biotite schist" (legend).
- `gr` = Graphite (RTMineral). The only RTMineral domain fields are `alt_min1` and `alt_min2`.
- 64 legend RockType codes are unused in the logging. They are retained in the dictionary.

## 4. Identifier rules

- `hole_id` = raw HoleID or HOLEID with outer whitespace removed, internal whitespace collapsed, upper-cased. Raw spelling is kept in `holes.raw_hole_id` and in the raw tables. Observed raw spellings already normalised (0 differences).
- `interval_key` = `hole_id@depth_from` with the number in `%g` format, stable across dataset versions.

## 5. Null semantics

| Situation | Stored as |
|---|---|
| Blank source cell | NULL in curated tables; raw value kept in raw tables and payload_json |
| Blank rock code | rock_code_status = MISSING; labels UNRESOLVED |
| Code not in legend | rock_code_status = UNSUPPORTED; labels UNRESOLVED |
| Blank mineral field | "gr not logged" (has_gr_mineral = 0) under rule version 1.0.0 |
| Blank comment | comment_present = 0; no label 0 can be assigned by a comment-dependent rule |
| Absolute elevation | z_absolute_m NULL (CHECK) |

## 6. Types and units

- Depths: metres (float). Intervals: 1.0 m. Dip: degrees, signed from horizontal, negative downward. Azimuth: degrees clockwise from north, [0, 360).
- Coordinates: metres, UTM zone 30N as labelled; datum unverified. CRS registry key EPSG:32630 (PROVISIONAL).
- Dates: ISO-8601 text after explicit parsing with `%d-%m-%Y`.

## 7. QC severities and statuses

Severity: ERROR, WARNING, INFO. Status: BLOCKED, PROVISIONAL, APPROVED (PASS findings are APPROVED). Stage status words: VERIFIED, PROVISIONAL, BLOCKED, DEFERRED, FAILED.

## 8. Graphitic-label decision workflow

1. Evidence per interval: is_sgs, has_gr_mineral, comment_graphitic (text), comment_trace_qualified (graphite qualified by 'trace' in the same phrase; 56 intervals after correction), comment_term.
2. Candidate rules (config/label_rules.yaml, status PROPOSED): STRICT_SGS_v1, RECON_2OF3_v1, ALL3_v1, ANY_v1, and the sensitivity rule RECON_2OF3_NOTRACE_v1 (trace-qualified comments are not positive evidence).
3. Results recomputed from the workbook: evidence positives 3 = 476, 2 = 87, 1 = 43, 0 = 1,304 (matches ThesisDesign.docx).
4. Rule counts (POSITIVE / NEGATIVE / UNRESOLVED): STRICT 529 / 1,368 / 13; RECON_2OF3 562 / 1,289 / 59; RECON_2OF3_NOTRACE 527 / 1,310 / 73; ALL3 476 / 1,289 / 145; ANY 605 / 1,289 / 16.
5. Conflicts (mixed evidence): 126. Ambiguity export: `data/derived/ambiguity_review_intervals.csv`.
6. Approval: a supervising geologist writes a `label_reviews` row with decision APPROVE_RULE, then status may change to APPROVED. A trigger enforces this.

## 9. Source provenance assumptions

- The workbook is the only primary source. The regional shapefile supplies 1:1,000,000 context (9 polygons intersecting a 10 km collar buffer; all 71 collars fall inside mapped polygons).
- ThesisDesign.docx and ReadingGuide.docx provide reconciliation values and methodology only.
- The Architecture and Addendum documents control the database allocation: obj1_master is the path `database/kambale_thesis.sqlite`; later objectives get their own databases.
- The Geology_93.mdb geodatabase in the geology folder was not parsed (not needed for Stage A).

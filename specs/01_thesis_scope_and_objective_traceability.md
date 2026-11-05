# 01 Thesis scope and objective traceability (Stage A)

## Fixed thesis title

Hybrid Machine Learning–Indicator Geostatistical Modelling for Spatially Validated Three-Dimensional Prediction and Uncertainty Characterization of Graphitic Domains at the Kambale Graphite Deposit, Ghana.

## Fixed synopsis objectives (verbatim, not edited)

1. To construct and quality-control a three-dimensional drill-hole database and define graphitic domains at the Kambale Graphite Deposit.
2. To characterize the spatial distribution, geological controls, and continuity of graphitic domains using exploratory spatial analysis and indicator variography.
3. To develop and spatially validate indicator-geostatistical, machine-learning, and hybrid models for predicting graphitic-domain occurrence.
4. To evaluate the predictive performance of the developed models using independent spatial validation and probability-based metrics.
5. To quantify and visualize three-dimensional uncertainty in graphitic-domain occurrence and identify areas of high confidence and high uncertainty.

## Stage scope

| Stage | Content | Status in this delivery |
|---|---|---|
| A (this delivery) | Objective 1 database (`database/kambale_thesis.sqlite`), QA/QC, label candidates, provisional relative geometry, Stage A figures F01-F09 and tables T01-T03, tests | Implemented and verified (see QAQC_REPORT.md) |
| B (not executed) | Variograms, indicator kriging, ML, hybrid models, validation metrics, calibration, simulation, uncertainty volumes | DEFERRED (DEFERRED_FIGURES.md; empty blocking contracts in the database) |

## Objective-to-data-to-table-to-figure traceability

| Synopsis objective | Stage A data | Tables / views | Figures and tables | Claim allowed in Stage A |
|---|---|---|---|---|
| 1. Database, QA/QC, graphitic definition | Collars, Surveys, Logging, Logging Legend, hidden reference sheets | raw_*, holes, survey_stations, logging_intervals, geological_code_dictionary, interval_label_evidence, interval_labels, graphite_label_rules, qaqc_*, interval_coordinates | F01, F02, F03, F04, T01, T02 | Database built and verified; QA/QC findings listed; candidate definitions reported with disagreement; provisional geometry |
| 2. Spatial distribution and controls (exploratory portion only) | Curated intervals and provisional drill lines | v_hole_graphite, v_line_graphite, v_depth_weathering, v_collar_plan, v_interval_geometry | F05, F06, F07, F08, F09, T03 | Descriptive proportions and apparent thicknesses per hole, line and depth bin; no continuity, anisotropy or variogram claim |
| 3-5 (Stage B) | none in Stage A | future contracts (empty, write-blocked) | none (deferred) | None |

## Scientific claims permitted in Stage A

- The workbook contains 71 RAB holes, 71 end-of-hole orientation records and 1,910 contiguous 1-m logging intervals. These are verified counts from the workbook recount.
- 529 intervals carry rock code `Sgs`; 42 holes contain at least one `Sgs` interval. These match ThesisDesign.docx and are reported as reconciled values.
- The three logged graphite indicators disagree for a material number of intervals (126 conflicts under the stated rule).
- Collar positions form five nominal Northing groups, which are provisional drill lines.
- Relative vertical offsets below each collar can be computed under a stated straight-hole convention.

## Prohibited overclaims (must not appear in any Stage A output)

- Graphite grade, TGC, tonnage, reserve, resource, or any economic statement (no assays exist).
- Absolute elevation, mineralised volume in 3-D, or "depth below sea level" (collar RL absent; `z_absolute_m` NULL).
- Observed geological contacts or continuity between holes (no interpolation is performed).
- Predictive accuracy, calibration, improvement of a hybrid model, or uncertainty of any model (Stage B).
- Any statement that a graphitic label rule is approved (all five rules are PROPOSED).

## Open supervisor decisions (carried from spec.md)

1. Coordinate pair and datum (UTM pair adopted provisionally; datum unverified).
2. Collar RL or DEM method.
3. Graphitic label rule (strict Sgs or a reconciled candidate) and handling of unsupported (`fsc`) and blank codes.
4. Drill-line grouping (five nominal Northing groups provisional).
5. Whether the 71 holes are the intended study subset (ThesisDesign.docx section 2.4).
6. Dip and azimuth convention, and whether the end-of-hole orientation applies to the whole hole.

## Source-role note

ThesisDesign.docx lists seven specific objectives (proposed for supervisor review). The synopsis objectives above are the approved five and are the only objectives used in this repository. The seven-objective list is treated as a draft and is not implemented.

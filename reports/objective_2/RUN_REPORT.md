# Objective 2 run report: spatial distribution, geological controls and indicator variography

Configuration O2-CFG-2026.11.05-4 (SHA-256 bfc2962a9e89), code 2.1.0, schema O2-SCHEMA-2026.11.06-6, commit c13a75c. Import run 1, analysis run 2, gate run 20. Report written 2026-11-06T09:07:14Z.

## 1. Status

Stage exit conditions (specification 03, section 6): every required gate is PASS.
Handoff decision for Objective 3: NOT_IDENTIFIABLE (candidate family NONE). Full-data parameters for test folds: 0.

## 2. Inputs and receipt

- Objective 1 snapshot: C:/Users/ThinkPad P1 G4/Documents/Joseph_Thesis/database/kambale_thesis.sqlite (read-only; dataset version 10, ETL 1.5.0, content SHA-256 abf6f758faf7).
- Intervals imported: 1910 (each 1 m); holes 71; drill lines 5.
- Label rule DESIGN_8_2_v1 APPROVED; binary target 1829 intervals (525 POSITIVE, 1304 NEGATIVE); excluded 81 AMBIGUOUS and 0 UNRESOLVED.
- Geometry PROVISIONAL_RELATIVE: straight holes at dip -60, azimuth 90; collar elevation absent; depth relative to collar.
- Coordinates EPSG:32630 with datum VERIFIED; coordinate pair APPROVED; drill lines APPROVED.

## 3. Configuration

Predeclared version O2-CFG-2026.11.05-4 supersedes O2-CFG-2026.11.05-2. Revision: Adds one SKIP record to the sensitivity list for the tentative geologic orientation factor, which specification 02 section 10 names and the earlier list did not record. No numeric setting changed. Configuration 2 is kept in config/objective_2/superseded/ (decisions.md, O2-D15). Correction history (configuration 1 to 2): Configuration 1 measured every between-hole lag in three dimensions. Vertical separation between intervals at different depths then dominated the lag, and the directional classes used three-dimensional distances. Configuration 2 assesses lateral continuity with horizontal lag distances between intervals at similar depth (absolute relative-Z difference at most 3 m). The three-dimensional family is kept and reported, but it is not the handoff basis. Configuration 1 gave a flat omnidirectional curve at the marginal variance and a fitted range at the 10 m lower bound. That result is recorded in RUN_REPORT.md as superseded and is not used.

## 4. Superseded configuration (recorded, not used)

Configuration O2-CFG-2026.11.05-1 measured every between-hole lag in three dimensions and used three-dimensional distances for the directional classes. Its first analysis gave a between-hole variogram with all 25 lag bins supported and gamma between 0.15 and 0.24, close to p(1 - p); the exponential fit's range sat at the 10 m lower bound with a structured sill near zero. The within-hole fit had a range near 15 m and a sill near 0.177. The azimuth class at 90 degrees was supported with its range at the lower bound, and the other three azimuth classes were skipped. Its handoff decision (PROVISIONAL) was judged invalid, because the three-dimensional lag mixes depth separation into the between-hole structure. That run is not used anywhere in this report. Its configuration file is kept at config/objective_2/superseded/variogram_config_O2-CFG-2026.11.05-1.yaml; its database was set aside and is not part of the deliverables.

## 5. Results

### 5.1 Occurrence and geological controls

- Positive share of binary intervals: 0.287 overall. By line the positive share ranges from 0.041 (NOM_N1113000) to 0.506 (NOM_N1112140). This between-line difference is the strongest occurrence contrast in the data; whether it reflects zones, sampling or geology is not resolved.
- Depth and weathering summaries are in figure O2-F03 and table O2-T02.

### 5.2 Support

- Nearest-collar distance: median 21.0 m (5th to 95th percentile 16.2 to 41.1 m).
- Collar-pair separation: median 921 m (5th to 95th percentile 78 to 2008 m).
- Lateral pairs in supported bins: 1559 to 7059 per bin; independent hole pairs 16 to 68 per bin (thresholds 100 pairs and 10 hole pairs).

### 5.3 Variograms and fits

- Lateral between-hole (handoff basis): 25 supported bins; gamma 0.109 to 0.189; marginal variance p(1 - p) 0.2046. Both models are NOT_IDENTIFIABLE: the best non-negative fit is a pure nugget, confirmed by a profile over all candidate ranges (tests/objective_2/test_fitting.py).
- Three-dimensional between-hole (reported only): 25 supported bins; gamma 0.150 to 0.239; NOT_IDENTIFIABLE.
- Within-hole (downhole): 30 supported bins. Spherical range 15.0 m, sill 0.177, nugget 0.023; exponential range 23.5 m, sill 0.213, nugget 0.013. Within-hole continuity is identified and is reported separately from between-hole structure.
- Horizontal azimuth (exploratory): LAT_AZ_000 3 supported bins; LAT_AZ_045 0 supported bins; LAT_AZ_090 24 supported bins; LAT_AZ_135 0 supported bins. No azimuth fit is FITTED.

Fit-by-fit identifiability and stability are in table O2-T03 (below).

### 5.4 Leave-one-line-out

- The lateral basis was refitted once per line (5 lines, two models each). The base fits are not FITTED, so the stability status is NOT_ASSESSED; no envelope is claimed.

### 5.5 Sensitivity

| variant | factor | value | status | supported bins | reason |
|---|---|---|---|---|---|
| LAG_WIDTH_10M | lag_width_m | 10.0 | COMPLETED | 37 | 37 supported bins; spherical NOT_IDENTIFIABLE; exponential NOT_IDENTIFIABLE |
| TOLERANCE_30DEG | angular_tolerance_deg | 30.0 | COMPLETED | 3 | 3 supported bins; spherical NOT_IDENTIFIABLE; exponential NOT_IDENTIFIABLE |
| TOLERANCE_30DEG | angular_tolerance_deg | 30.0 | COMPLETED | 1 | 1 supported bins; spherical NOT_IDENTIFIABLE; exponential NOT_IDENTIFIABLE |
| TOLERANCE_30DEG | angular_tolerance_deg | 30.0 | COMPLETED | 24 | 24 supported bins; spherical NOT_IDENTIFIABLE; exponential NOT_IDENTIFIABLE |
| TOLERANCE_30DEG | angular_tolerance_deg | 30.0 | COMPLETED | 0 | 0 supported bins; spherical NOT_IDENTIFIABLE; exponential NOT_IDENTIFIABLE |
| WITHIN_HOLE_INCLUDED | within_hole_pairs | INCLUDED | COMPLETED | 25 | 25 supported bins; spherical FITTED; exponential FITTED |
| EQUAL_HOLE_WEIGHTING | pair_weighting | EQUAL_HOLE | COMPLETED | 25 | 25 supported bins; spherical NOT_IDENTIFIABLE; exponential NOT_IDENTIFIABLE |
| STRICT_SUPPORT_200_PAIRS | min_pairs_per_bin | 200 | COMPLETED | 25 | 25 supported bins; spherical NOT_IDENTIFIABLE; exponential NOT_IDENTIFIABLE |
| STRICT_LABEL_COMPARATOR | label_rule | STRICT_SGS_v1 | SKIPPED | 0 | SKIP_NOT_AUTHORISED: not run |
| ABSOLUTE_ELEVATION_GEOMETRY | vertical | z_absolute_m | SKIPPED | 0 | SKIP_NO_VALIDATED_RL: not run |
| TENTATIVE_GEOLOGIC_ORIENTATION | geologic_orientation | NONE_AVAILABLE | SKIPPED | 0 | SKIP_NO_GEOLOGIC_ORIENTATION: no strike or dip is recorded for the geology; all holes share one nominal orientation (G09) |

### 5.6 Anisotropy

- LAT_AZ_000 against LAT_AZ_090: SKIPPED, decision NOT_EVALUATED; no FITTED model in one direction.
- LAT_AZ_045 against LAT_AZ_135: SKIPPED, decision NOT_EVALUATED; no FITTED model in one direction.

### 5.7 Configuration 3 extension and STRICT comparator (exploratory)

Configuration O2-CFG-2026.11.05-3 (SHA-256 0176878c3d97), stage run 3: configuration 3: lateral extension and STRICT comparator (exploratory); extension decision: NOT_IDENTIFIABLE (extension); STRICT labels imported: 1910.

| label rule | lag setting | supported bins | gamma range | spherical | exponential | stability (spherical / exponential) |
|---|---|---|---|---|---|---|
| DESIGN_8_2_v1 | 50 m bins to 2000 m | 40 | 0.128 to 0.197 | NOT_IDENTIFIABLE | NOT_IDENTIFIABLE | NOT_ASSESSED / NOT_ASSESSED |
| STRICT_SGS_v1 | 20 m bins to 500 m | 25 | 0.109 to 0.189 | NOT_IDENTIFIABLE | NOT_IDENTIFIABLE | NOT_ASSESSED / NOT_ASSESSED |
| STRICT_SGS_v1 | 50 m bins to 2000 m | 40 | 0.128 to 0.197 | NOT_IDENTIFIABLE | NOT_IDENTIFIABLE | NOT_ASSESSED / NOT_ASSESSED |

Leave-one-line-out refits of the DESIGN extension: 10 refit rows, 0 FITTED.

Reading: no DESIGN model is FITTED in the extension. The fits run to the window limit or show no structure beyond the nugget, and the leave-one-line-out refits do not pass the rules, so a longer window does not identify a range.
The STRICT comparator disagrees with DESIGN on 0 of the DESIGN binary intervals. On the 81 intervals that DESIGN leaves ambiguous, STRICT gives 76 NEGATIVE, 5 POSITIVE.
Neither result changes the configuration-2 handoff (NOT_IDENTIFIABLE), which stands as recorded.

### 5.8 Configuration 5: weathering front and fresh-rock variography

Configuration O2-CFG-2026.11.06-5 (SHA-256 29ebcf7d3327), stage run 4: configuration 5: weathering front and fresh-rock variography; fresh-rock decisions: LATERAL_FRESH_COLLAR NOT_IDENTIFIABLE (fresh rock); LATERAL_FRESH_FRONT NOT_IDENTIFIABLE (fresh rock); no handoff row written.

Front definition: the shallowest interval with weathering code mw or sw in each hole, at its relative depth on the straight hole. Holes with a cw or hw interval below the front are reported, not redefined.

Holes with a front: 71; without: 0. Front relative elevation mean -7.39 m, sd 4.46 m, range -19.92 to 0.00 m. Holes with a cw or hw interval below the front: 9.

Along-line adjacent holes (66 pairs): median absolute front difference 2.60 m, 90th percentile 7.79 m, maximum 18.19 m; median collar distance 33 m.

| scheme | IDW RMSE (m) | training-mean RMSE (m) | skill ratio | decision (threshold 0.8) |
|---|---|---|---|---|
| leave one hole out | 4.85 | 4.49 | 1.079 | NOT INTERPOLABLE |
| leave one line out | 5.56 | 4.73 | 1.175 | NOT INTERPOLABLE |

Front semivariogram (between holes, 25 m bins to 500 m): 20 of 20 bins supported (at least 10 hole pairs); supported lags (m): 0 to 25, 25 to 50, 50 to 75, 75 to 100, 100 to 125, 125 to 150, 150 to 175, 175 to 200, 200 to 225, 225 to 250, 250 to 275, 275 to 300, 300 to 325, 325 to 350, 350 to 375, 375 to 400, 400 to 425, 425 to 450, 450 to 475, 475 to 500.

| experiment | supported bins | spherical | exponential | stability (spherical / exponential) |
|---|---|---|---|---|
| LATERAL_FRESH_COLLAR | 25 | NOT_IDENTIFIABLE | NOT_IDENTIFIABLE | NOT_ASSESSED / NOT_ASSESSED |
| LATERAL_FRESH_FRONT | 25 | FITTED | FITTED | UNSTABLE / UNSTABLE |

Leave-one-line-out refits of the fresh-rock experiments: 20 refit rows, 8 FITTED.

Decisions (fresh rock): LATERAL_FRESH_COLLAR NOT_IDENTIFIABLE (fresh rock); LATERAL_FRESH_FRONT NOT_IDENTIFIABLE (fresh rock).

Observability: 3 of 647 intervals logged cw or hw carry a POSITIVE DESIGN label. This is a limit of logging in strongly weathered material; it is not a finding that weathered rock is non-graphitic, and no interval is relabelled.

Configuration 5 writes no handoff row; the configuration-2 handoff (NOT_IDENTIFIABLE) stands as recorded.

### 5.9 Configuration 6: structural frame (apparent-dip search, selection null, between-line report)

Configuration O2-CFG-2026.11.06-6 (SHA-256 89ce6fff3fed), stage run 14: configuration 6: structural-frame indicator variography (dip search, circular down-hole null); no handoff row written; in-memory YAML scalar repairs: 2.

Dip grid -80 to 80 degrees in 17 steps. Pairs: within-line between-hole, |ds| at most 3 m, lag |dt| binned 20 m to 500 m. Null: circular down-hole shift, 500 permutations, whole grid rescored. Same-hole pairs in the experiments: 0; same-hole candidates excluded before the experiments: 478152.

| sample | frame | selected dip (deg) | A at selected dip | A at dip 0 | null 95th percentile of max | null p-value | lines within 10 deg of full dip | decision |
|---|---|---|---|---|---|---|---|---|
| ALL_BINARY | DEM_ABSOLUTE | +0 | 0.1837 | 0.1837 | 0.1669 | 0.0399 | 5 of 5 | sensitivity only |
| ALL_BINARY | RELATIVE | +0 | 0.1686 | 0.1686 | 0.1676 | 0.0519 | 5 of 5 | NOT_IDENTIFIABLE (structural frame) |
| FRESH | DEM_ABSOLUTE | +20 | 0.3033 | 0.1863 | 0.4286 | 0.5409 | 3 of 5 | sensitivity only |
| FRESH | RELATIVE | +20 | 0.2892 | 0.1914 | 0.4269 | 0.6048 | 2 of 5 | NOT_IDENTIFIABLE (structural frame) |

Leave-one-line-out dips (degrees):

- ALL_BINARY, DEM_ABSOLUTE, without NOM_N1111930: +0 (within 10 degrees of the full dip).
- ALL_BINARY, DEM_ABSOLUTE, without NOM_N1112140: +0 (within 10 degrees of the full dip).
- ALL_BINARY, DEM_ABSOLUTE, without NOM_N1112500: +0 (within 10 degrees of the full dip).
- ALL_BINARY, DEM_ABSOLUTE, without NOM_N1112600: +0 (within 10 degrees of the full dip).
- ALL_BINARY, DEM_ABSOLUTE, without NOM_N1113000: +0 (within 10 degrees of the full dip).
- ALL_BINARY, RELATIVE, without NOM_N1111930: +0 (within 10 degrees of the full dip).
- ALL_BINARY, RELATIVE, without NOM_N1112140: +0 (within 10 degrees of the full dip).
- ALL_BINARY, RELATIVE, without NOM_N1112500: +0 (within 10 degrees of the full dip).
- ALL_BINARY, RELATIVE, without NOM_N1112600: +0 (within 10 degrees of the full dip).
- ALL_BINARY, RELATIVE, without NOM_N1113000: +0 (within 10 degrees of the full dip).
- FRESH, DEM_ABSOLUTE, without NOM_N1111930: -60 (outside 10 degrees of the full dip).
- FRESH, DEM_ABSOLUTE, without NOM_N1112140: +20 (within 10 degrees of the full dip).
- FRESH, DEM_ABSOLUTE, without NOM_N1112500: +20 (within 10 degrees of the full dip).
- FRESH, DEM_ABSOLUTE, without NOM_N1112600: -20 (outside 10 degrees of the full dip).
- FRESH, DEM_ABSOLUTE, without NOM_N1113000: +20 (within 10 degrees of the full dip).
- FRESH, RELATIVE, without NOM_N1111930: -60 (outside 10 degrees of the full dip).
- FRESH, RELATIVE, without NOM_N1112140: +20 (within 10 degrees of the full dip).
- FRESH, RELATIVE, without NOM_N1112500: -50 (outside 10 degrees of the full dip).
- FRESH, RELATIVE, without NOM_N1112600: -20 (outside 10 degrees of the full dip).
- FRESH, RELATIVE, without NOM_N1113000: +20 (within 10 degrees of the full dip).

Fits at the selected dip (sill and nugget in indicator units; range in metres):

| sample | frame | model | fit status | nugget | structured sill | range | leave-one-line-out stability | range ratio min to max |
|---|---|---|---|---|---|---|---|---|
| ALL_BINARY | DEM_ABSOLUTE | exponential | NOT_IDENTIFIABLE | n/a | n/a | n/a | NOT_ASSESSED | n/a to n/a |
| ALL_BINARY | DEM_ABSOLUTE | spherical | NOT_IDENTIFIABLE | n/a | n/a | n/a | NOT_ASSESSED | n/a to n/a |
| ALL_BINARY | RELATIVE | exponential | NOT_IDENTIFIABLE | n/a | n/a | n/a | NOT_ASSESSED | n/a to n/a |
| ALL_BINARY | RELATIVE | spherical | NOT_IDENTIFIABLE | n/a | n/a | n/a | NOT_ASSESSED | n/a to n/a |
| FRESH | DEM_ABSOLUTE | exponential | NOT_IDENTIFIABLE | n/a | n/a | n/a | NOT_ASSESSED | n/a to n/a |
| FRESH | DEM_ABSOLUTE | spherical | NOT_IDENTIFIABLE | n/a | n/a | n/a | NOT_ASSESSED | n/a to n/a |
| FRESH | RELATIVE | exponential | NOT_IDENTIFIABLE | n/a | n/a | n/a | NOT_ASSESSED | n/a to n/a |
| FRESH | RELATIVE | spherical | NOT_IDENTIFIABLE | n/a | n/a | n/a | NOT_ASSESSED | n/a to n/a |

Between-line along-strike report (REPORT_ONLY, RELATIVE frame, selected dip; no fit):

- ALL_BINARY, lag 50 to 150 m: 43897 pairs, 315 independent hole pairs, gamma 0.186, supported.
- ALL_BINARY, lag 150 to 250 m: 6666 pairs, 39 independent hole pairs, gamma 0.186, supported.
- ALL_BINARY, lag 250 to 350 m: 3707 pairs, 32 independent hole pairs, gamma 0.188, supported.
- ALL_BINARY, lag 350 to 450 m: 72723 pairs, 526 independent hole pairs, gamma 0.170, supported.
- ALL_BINARY, lag 450 to 600 m: 89649 pairs, 657 independent hole pairs, gamma 0.150, supported.
- FRESH, lag 50 to 150 m: 0 pairs, 0 independent hole pairs, gamma n/a, below 100 pairs.
- FRESH, lag 150 to 250 m: 0 pairs, 0 independent hole pairs, gamma n/a, below 100 pairs.
- FRESH, lag 250 to 350 m: 0 pairs, 0 independent hole pairs, gamma n/a, below 100 pairs.
- FRESH, lag 350 to 450 m: 0 pairs, 0 independent hole pairs, gamma n/a, below 100 pairs.
- FRESH, lag 450 to 600 m: 1692 pairs, 42 independent hole pairs, gamma 0.244, supported.

Decisions (RELATIVE frame, structural frame): ALL_BINARY NOT_IDENTIFIABLE (structural frame) (selection-null p = 0.0519 (not below 0.05); 5 of 5 leave-one-line-out dips within 10 degrees (need 4); stable FITTED model: none; decision NOT_IDENTIFIABLE (structural frame)); FRESH NOT_IDENTIFIABLE (structural frame) (selection-null p = 0.6048 (not below 0.05); 2 of 5 leave-one-line-out dips within 10 degrees (need 4); stable FITTED model: none; decision NOT_IDENTIFIABLE (structural frame)).

The DEM_ABSOLUTE frame is sensitivity only and sets no decision. Configuration 6 writes no handoff row; the configuration-2 handoff (NOT_IDENTIFIABLE) stands as recorded.

Claims not permitted by configuration 6 (from its claims_not_permitted list):

- a measured strike or dip of the ore horizons (the dip here is an apparent, statistically selected dip)
- an along-strike range
- any change to the configuration-2 handoff decision
- geological continuity beyond the drilled lines

Decision label for a PROVISIONAL result: PROVISIONAL (structural frame). It supplies a structural-frame across-strike covariance only; no along-strike range is identified.

## 6. Gate results (VERIFY run 20)

| gate | name | status | detail |
|---|---|---|---|
| G01 | Receipt match | PASS | recomputed content abf6f758faf7 vs receipt abf6f758faf7; rows 1910 vs receipt 1910; observed holes missing upstream: 0 |
| G02 | Approved label rule | PASS | DESIGN_8_2_v1 APPROVED |
| G03 | Relative geometry only | PASS | z_absolute_m non-null rows = 0 |
| G04 | Coordinate pair and datum | PASS | pair APPROVED; datum VERIFIED |
| G05 | Drill-line grouping | PASS | 5 line codes; drill-line status APPROVED; holes on two lines: 0 |
| G06 | Support one metre | PASS | 0 intervals differ from 1 m in support or depth span |
| G07 | Pair validity | PASS | subset of 160 intervals: blockwise and brute-force counts agree over 602 pairs; 0 zero-distance pairs excluded |
| G08 | Exclusion accounting | PASS | 0 hole or line rows fail the identity |
| G09 | Declared orientation | WARN | survey orientations [(-60.0, 90.0)]; declared (-60.0, 90.0); uniform across holes = True |
| G10 | Class imbalance | WARN | lines below 10 per cent positive: NOM_N1113000 0.041 |
| G11 | Bin support consistency | PASS | 0 bins with inconsistent support and gamma |
| G12 | Directional support | WARN | skipped directions: LAT_AZ_000, LAT_AZ_045, LAT_AZ_135 |
| G13 | No parameters for unidentified fits | PASS | 0 unidentified fits carry parameters |
| G14 | Fit admissibility | PASS | 0 inadmissible fitted parameters |
| G15 | Identifiability | PASS | 0 FITTED range or sill values on a bound; 0 FITTED lateral fits without a leave-one-line-out envelope |
| G16 | Leave-one-line-out stability | WARN | 2 fits are unstable; 10 refit rows for 5 lines (two models each); of which configuration 5 (fresh rock): 2 (see RUN_REPORT 5.8) |
| G17 | Marginal variance departure | PASS | 0 fits depart from p(1-p) by more than 50 per cent |
| G18 | Anisotropy claims | PASS | anisotropy decisions: NOT_EVALUATED 2 |
| G19 | Base excludes within-hole pairs | PASS | 0 base between-hole experiments include within-hole pairs; lateral handoff base present: True |
| G20 | Sensitivity completeness | PASS | 8 of 8 configured sensitivity entries have a row (completed or skipped with reason) |
| G21 | Relative depth only | WARN | 5 of 5 sections labelled RELATIVE_DEPTH; no collar elevation is available, so the relative-depth limitation is always reported |
| G22 | No absolute-elevation products | PASS | absolute-elevation columns in the Objective 2 database: none |
| G23 | Observed versus inferred | PASS | 0 section rows claim an inferred contact as observation |
| G24 | Synthetic pattern not exported | PASS | 0 receipts or manifest entries carry synthetic data |
| G25 | No full-data parameters for test folds | PASS | 0 handoff rows allow full-data parameters |
| G26 | All-data fits labelled exploratory | PASS | 0 provisional handoffs do not carry the exploratory label |
| G27 | Handoff status and basis vocabulary | PASS | 0 handoff rows outside the stage vocabulary or the lateral basis |
| G28 | Query provenance | PASS | 0 figures and 0 tables without registered queries; 0 SQL files differ from their registered hash |
| G29 | NOT_SUPPORTED entries carry a reason | PASS | 0 NOT_SUPPORTED figures without a stated reason |
| G30 | Export hashes | PASS | 0 manifest entries differ from the file on disk |
| G31 | Configuration-5 stage writes no handoff | PASS | 0 handoff rows created at or after the start of configuration-5 run 4 |
| G32 | Structural stage: no within-hole pair | PASS | 68 dip and frame pair sets; within-hole pairs inside the experiments: 0; same-hole candidates excluded before the experiment: 478152 |
| G33 | Structural stage: grid, band, lag and seed | PASS | 68 alignment rows; 4 sample-frame combinations; configuration mismatches: none |
| G34 | Structural stage: d = 0 pair set | PASS | independent within-line between-hole set with |dz| <= 3 m: 75201 pairs; stage: 75201 pairs; digests agree |
| G35 | Structural stage writes no handoff | PASS | 0 handoff rows created at or after the start of configuration-6 run 14 |
| G36 | Structural selected dip not at the grid edge | PASS | selected dips at plus or minus 80 degrees: none |
| G37 | Structural frames agree on the selected dip | PASS | RELATIVE and DEM_ABSOLUTE selected dips: ALL_BINARY 0 and 0; FRESH 20 and 20; more than 20 degrees apart: 0 |

## 7. Tables

- O2-T01: GENERATED, 76 rows; Hole and line geological summary with support.
- O2-T02: GENERATED, 6 rows; Indicator prevalence, ambiguity and missingness by line.
- O2-T03: GENERATED, 40 rows; Variogram fitting report.
- O2-T04: GENERATED, 15 rows; Handoff contract and open items.
- O2-T05: GENERATED, 20 rows; Weathering front continuity and interpolation check.
- O2-T06: GENERATED, 68 rows; Structural-frame alignment score by apparent dip, selection-null p-value and leave-one-line-out dips.
- O2-T07: GENERATED, 28 rows; Structural-frame fit at the selected dip and between-line report.

### O2-T03 variogram fitting report


Leave-one-line-out refits are summarised by the envelope columns. Ranges are metres; nugget and sill are indicator units; p(1 - p) is the marginal variance.
Source: sql/objective_2/tables/O2-T03.sql, receipt 1, 40 rows.

| role | direction_id | variant | model | fit_status | stability_status | n_bins_used | objective | admissible | marginal_departure | nugget | structured_sill | range_m | range_loo_min_m | range_loo_max_m | handoff_status | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXPLORATORY_DIRECTIONAL | LAT_AZ_000 | BASE | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 3 |  |  |  |  |  |  |  |  | not a handoff basis | 3 supported bins; 5 required; stability: leave-one-line-out is applied to the lateral handoff basis only |
| EXPLORATORY_DIRECTIONAL | LAT_AZ_000 | BASE | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 3 |  |  |  |  |  |  |  |  | not a handoff basis | 3 supported bins; 5 required; stability: leave-one-line-out is applied to the lateral handoff basis only |
| EXPLORATORY_DIRECTIONAL | LAT_AZ_045 | BASE | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 0 |  |  |  |  |  |  |  |  | not a handoff basis | 0 supported bins; 5 required; stability: leave-one-line-out is applied to the lateral handoff basis only |
| EXPLORATORY_DIRECTIONAL | LAT_AZ_045 | BASE | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 0 |  |  |  |  |  |  |  |  | not a handoff basis | 0 supported bins; 5 required; stability: leave-one-line-out is applied to the lateral handoff basis only |
| EXPLORATORY_DIRECTIONAL | LAT_AZ_090 | BASE | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 24 | 1210.51 | 1 | -0.304 |  |  |  |  |  | not a handoff basis | range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: leave-one-line-out is applied to the lateral handoff basis only |
| EXPLORATORY_DIRECTIONAL | LAT_AZ_090 | BASE | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 24 | 1210.51 | 1 | -0.304 |  |  |  |  |  | not a handoff basis | structured sill below 5% of p(1-p): no structure beyond the nugget; stability: leave-one-line-out is applied to the lateral handoff basis only |
| EXPLORATORY_DIRECTIONAL | LAT_AZ_135 | BASE | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 0 |  |  |  |  |  |  |  |  | not a handoff basis | 0 supported bins; 5 required; stability: leave-one-line-out is applied to the lateral handoff basis only |
| EXPLORATORY_DIRECTIONAL | LAT_AZ_135 | BASE | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 0 |  |  |  |  |  |  |  |  | not a handoff basis | 0 supported bins; 5 required; stability: leave-one-line-out is applied to the lateral handoff basis only |
| HANDOFF_BASIS | LATERAL_BETWEEN | BASE | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 1416.44 | 1 | -0.289 |  |  |  |  |  | NOT_IDENTIFIABLE | range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: base fit is not FITTED |
| HANDOFF_BASIS | LATERAL_BETWEEN | BASE | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 1416.44 | 1 | -0.289 |  |  |  |  |  | NOT_IDENTIFIABLE | structured sill below 5% of p(1-p): no structure beyond the nugget; stability: base fit is not FITTED |
| REPORTED_3D | OMNI_3D_BETWEEN | BASE | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 5455.365 | 1 | -0.084 |  |  |  |  |  | not a handoff basis | range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: leave-one-line-out is applied to the lateral handoff basis only |
| REPORTED_3D | OMNI_3D_BETWEEN | BASE | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 5455.365 | 1 | -0.084 |  |  |  |  |  | not a handoff basis | range at the smallest supported lag: no spatial dependence beyond the nugget; stability: leave-one-line-out is applied to the lateral handoff basis only |
| REPORTED_WITHIN_HOLE | DOWNHOLE_WITHIN | BASE | exponential | FITTED | NOT_ASSESSED | 30 | 83.75 | 1 | 0.104 | 0.0128 | 0.2131 | 23.53 |  |  | not a handoff basis | converged inside bounds; stability: leave-one-line-out is applied to the lateral handoff basis only |
| REPORTED_WITHIN_HOLE | DOWNHOLE_WITHIN | BASE | spherical | FITTED | NOT_ASSESSED | 30 | 245.556 | 1 | -0.023 | 0.0229 | 0.177 | 15.03 |  |  | not a handoff basis | converged inside bounds; stability: leave-one-line-out is applied to the lateral handoff basis only |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 37 | 4041.413 | 1 | -0.332 |  |  |  |  |  | not a handoff basis | range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 2066.931 | 1 | -0.416 |  |  |  |  |  | not a handoff basis | range at the upper bound: not identified inside the supported lags; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 1416.44 | 1 | -0.289 |  |  |  |  |  | not a handoff basis | range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 40 | 2939.058 | 1 | -0.161 |  |  |  |  |  | not a handoff basis | range at the upper bound: not identified inside the supported lags; stability: base fit is not FITTED |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 1416.44 | 1 | -0.289 |  |  |  |  |  | not a handoff basis | range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: leave-one-line-out not run for this comparison |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 40 | 2939.058 | 1 | -0.161 |  |  |  |  |  | not a handoff basis | range at the upper bound: not identified inside the supported lags; stability: leave-one-line-out not run for this comparison |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 37 | 4041.413 | 1 | -0.332 |  |  |  |  |  | not a handoff basis | structured sill below 5% of p(1-p): no structure beyond the nugget; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 2066.931 | 1 | -0.416 |  |  |  |  |  | not a handoff basis | range at the upper bound: not identified inside the supported lags; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 1416.44 | 1 | -0.289 |  |  |  |  |  | not a handoff basis | structured sill below 5% of p(1-p): no structure beyond the nugget; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 40 | 2381.604 | 1 | -0.146 |  |  |  |  |  | not a handoff basis | range at the upper bound: not identified inside the supported lags; stability: base fit is not FITTED |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 1416.44 | 1 | -0.289 |  |  |  |  |  | not a handoff basis | structured sill below 5% of p(1-p): no structure beyond the nugget; stability: leave-one-line-out not run for this comparison |
| SENSITIVITY | LATERAL_BETWEEN | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 40 | 2381.604 | 1 | -0.146 |  |  |  |  |  | not a handoff basis | range at the upper bound: not identified inside the supported lags; stability: leave-one-line-out not run for this comparison |
| SENSITIVITY | LATERAL_FRESH_COLLAR | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 1175.159 | 1 | -0.212 |  |  |  |  |  | not a handoff basis | structured sill below 5% of p(1-p): no structure beyond the nugget; stability: base fit is not FITTED |
| SENSITIVITY | LATERAL_FRESH_COLLAR | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 25 | 1175.159 | 1 | -0.212 |  |  |  |  |  | not a handoff basis | range at the upper bound: not identified inside the supported lags; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: base fit is not FITTED |
| SENSITIVITY | LATERAL_FRESH_FRONT | SENSITIVITY | exponential | FITTED | UNSTABLE | 25 | 1625.719 | 1 | -0.213 | 0 | 0.1945 | 10.47 |  |  | not a handoff basis | converged inside bounds; stability: a leave-one-line-out refit was NOT_IDENTIFIABLE |
| SENSITIVITY | LATERAL_FRESH_FRONT | SENSITIVITY | spherical | FITTED | UNSTABLE | 25 | 1625.664 | 1 | -0.213 | 0.1726 | 0.0219 | 29.62 |  |  | not a handoff basis | converged inside bounds; stability: a leave-one-line-out refit was NOT_IDENTIFIABLE |
| SENSITIVITY | LAT_AZ_000 | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 3 |  |  |  |  |  |  |  |  | not a handoff basis | 3 supported bins; 5 required; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LAT_AZ_000 | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 3 |  |  |  |  |  |  |  |  | not a handoff basis | 3 supported bins; 5 required; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LAT_AZ_045 | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 1 |  |  |  |  |  |  |  |  | not a handoff basis | 1 supported bins; 5 required; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LAT_AZ_045 | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 1 |  |  |  |  |  |  |  |  | not a handoff basis | 1 supported bins; 5 required; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LAT_AZ_090 | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 24 | 1212.31 | 1 | -0.304 |  |  |  |  |  | not a handoff basis | range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LAT_AZ_090 | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 24 | 1212.31 | 1 | -0.304 |  |  |  |  |  | not a handoff basis | structured sill below 5% of p(1-p): no structure beyond the nugget; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LAT_AZ_135 | SENSITIVITY | exponential | NOT_IDENTIFIABLE | NOT_ASSESSED | 0 |  |  |  |  |  |  |  |  | not a handoff basis | 0 supported bins; 5 required; stability: sensitivity fit: stability not tested |
| SENSITIVITY | LAT_AZ_135 | SENSITIVITY | spherical | NOT_IDENTIFIABLE | NOT_ASSESSED | 0 |  |  |  |  |  |  |  |  | not a handoff basis | 0 supported bins; 5 required; stability: sensitivity fit: stability not tested |
| SENSITIVITY | OMNI_3D_BETWEEN | SENSITIVITY | exponential | FITTED | NOT_ASSESSED | 25 | 5626.432 | 1 | -0.083 | 0 | 0.1877 | 16.14 |  |  | not a handoff basis | converged inside bounds; stability: sensitivity fit: stability not tested |
| SENSITIVITY | OMNI_3D_BETWEEN | SENSITIVITY | spherical | FITTED | NOT_ASSESSED | 25 | 5600.839 | 1 | -0.083 | 0.1292 | 0.0585 | 29.96 |  |  | not a handoff basis | converged inside bounds; stability: sensitivity fit: stability not tested |

### O2-T04 handoff contract and open items


The handoff is for Objective 3 only. Full-data parameters are never supplied for test folds, and every open item is listed with its status.
Source: sql/objective_2/tables/O2-T04.sql, receipt 1, 15 rows.

| item_type | item_id | status | detail |
|---|---|---|---|
| DIRECTION | LAT_AZ_000 | SKIPPED | 3 supported bins; 5 required |
| DIRECTION | LAT_AZ_045 | SKIPPED | 0 supported bins; 5 required |
| DIRECTION | LAT_AZ_135 | SKIPPED | 0 supported bins; 5 required |
| GATE | G09 | WARN | Declared orientation: survey orientations [(-60.0, 90.0)]; declared (-60.0, 90.0); uniform across holes = True |
| GATE | G10 | WARN | Class imbalance: lines below 10 per cent positive: NOM_N1113000 0.041 |
| GATE | G12 | WARN | Directional support: skipped directions: LAT_AZ_000, LAT_AZ_045, LAT_AZ_135 |
| GATE | G16 | WARN | Leave-one-line-out stability: 2 fits are unstable; 10 refit rows for 5 lines (two models each); of which configuration 5 (fresh rock): 2 (see RUN_REPORT 5.8) |
| GATE | G21 | WARN | Relative depth only: 5 of 5 sections labelled RELATIVE_DEPTH; no collar elevation is available, so the relative-depth limitation is always reported |
| HANDOFF | O3-HANDOFF-1 | NOT_IDENTIFIABLE | candidate_family=NONE; full_data_parameters_for_test_folds=0; No lateral model is both FITTED and stable under leave-one-line-out: spherical NOT_IDENTIFIABLE (structured sill below 5% of p(1-p): no structure beyond the nugget); exponential NOT_IDENTIFIABLE (range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget). Lateral continuity is not identified at this support. Objective 3 must not use a between-hole continuity model whose parameters come from these fits; models without a geostatistical continuity term may proceed without a continuity claim. |
| QUESTION | COLLAR_RL | OPEN | no collar elevation (RL) is available; depth is relative to collar and absolute elevation is not used |
| QUESTION | LAG_WINDOW | OPEN | collar pairs have a median separation of 921.0 m, while the lateral lag window ends at 500.0 m; longer-range structure is not assessed |
| QUESTION | LINE_PREVALENCE | OPEN | binary prevalence by line ranges from 0.041 to 0.506 across 5 lines; whether this reflects zones, sampling or geology is not resolved |
| SENSITIVITY | ABSOLUTE_ELEVATION_GEOMETRY | SKIPPED | SKIP_NO_VALIDATED_RL: not run |
| SENSITIVITY | STRICT_LABEL_COMPARATOR | SKIPPED | SKIP_NOT_AUTHORISED: not run |
| SENSITIVITY | TENTATIVE_GEOLOGIC_ORIENTATION | SKIPPED | SKIP_NO_GEOLOGIC_ORIENTATION: no strike or dip is recorded for the geology; all holes share one nominal orientation (G09) |

Table O2-T01 (hole and line summary) and table O2-T02 (prevalence by line) are in tables/objective_2 as CSV, Markdown and LaTeX.

## 8. Figures

- O2-F01 (GENERATED): Drill-hole plan view by approved line. Plan view of 71 collars grouped by drill line (labels at the western collar of each line) with the midpoints of 525 POSITIVE intervals. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F02 (GENERATED): Positive metres and graphitic fraction by hole and line. Positive share (fraction) and positive apparent thickness (m) for 71 holes and 5 lines; 525 positive intervals. Each denominator is the number of binary intervals of that hole or line. Line labels are the nominal northing groups without their NOM_ prefix. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F03 (GENERATED): Binary occurrence by depth and by weathering class. Left: positive share of binary intervals by 10 m depth bin (variable: depth from collar; all rock codes pooled). Right: intervals by logged weathering code and label state (variables: weathering code; label state). Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F04 (GENERATED): Observed hole strips in relative depth. Logged intervals of the two holes per line with the most binary intervals, drawn as strips in depth below collar (m); lines shown: NOM_N1111930, NOM_N1112140, NOM_N1112500, NOM_N1112600, NOM_N1113000. Excluded intervals are hatched. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F05 (GENERATED): Pair support by lag. Number of pairs and of independent hole pairs per lag bin for the base experiments (counts only; no semivariance). Within-hole pairs are shown separately from between-hole pairs. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F06 (GENERATED): Between-hole indicator semivariograms. Experimental indicator semivariograms of between-hole pairs for the lateral basis (horizontal lag, relative-depth difference at most 3 m) and the three-dimensional family (reported). Dashed line: marginal variance p(1 - p) = 0.205; no base fit is FITTED, so no curve is drawn (fit status in O2-T03). Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F07 (GENERATED): Horizontal azimuth semivariograms (exploratory). Horizontal azimuth semivariograms (exploratory) at 0, 45, 90 and 135 degrees clockwise from grid north, tolerance ±22.5°. Dashed line: p(1 - p) = 0.205. Under-powered bins are marked with their pair counts; a direction with no supported bin is SKIPPED. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F08 (GENERATED): Sensitivity of supported bins and fit status. Supported lag bins and fit status (spherical and exponential) for 8 completed sensitivity experiments and their base experiments; 3 configured entries were skipped, with reasons shown in the figure. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F09 (GENERATED): Configuration-3 lateral extension with the STRICT comparator (exploratory). Configuration-3 exploratory lateral extension: experimental indicator semivariograms with 50 m bins to 2000 m and a relative-depth difference of at most 3 m, for DESIGN_8_2_v1 (approved, primary) and STRICT_SGS_v1 (comparator, authorised for this run only). Dashed line: the DESIGN marginal variance; dotted line, where it differs: the STRICT marginal variance; no model is FITTED, so no curve is drawn. The two samples give identical semivariances at every lag, because the comparator reproduces the DESIGN indicator on every DESIGN binary interval; the series coincide, so the comparator is drawn as hollow markers. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F10 (GENERATED): Weathering front and fresh-rock indicator semivariograms. Left: weathering front (shallowest interval with weathering mw or sw) of 71 holes by collar easting, one marker per drill line (vertical: relative depth of the front, m). Right: supported experimental indicator semivariograms of the fresh-rock sample (1163 binary intervals) for pairs at equal relative depth and for pairs at equal depth below their own front, 20 m bins to 500 m, with 95 per cent hole-bootstrap bands. Dashed line: p(1 - p) = 0.247; 2 fitted curve(s) drawn. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F11 (GENERATED): Structural-frame alignment score against apparent dip, with selection-null bands. Alignment score A(d) = 1 - mean semivariance at the first two supported lag bins divided by p(1 - p), for within-line between-hole pairs on the plane of apparent dip d (17 dips, -80 to 80 degrees). Each panel is one sample; blue solid is the RELATIVE frame (primary), green dashed is the DEM_ABSOLUTE frame (sensitivity). Dotted lines give the 95th percentile of the maximum over the dip grid under the circular down-hole shift null (500 permutations). Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F12 (GENERATED): Structural-frame experimental variograms at the selected dip and at dip 0. Experimental indicator semivariogram of within-line between-hole pairs in the RELATIVE frame, at the selected apparent dip (blue, with its hole-bootstrap band) and at dip 0 (green, horizontal control), for each sample; no model is FITTED at the selected dip, so no curve is drawn. Pairs lie within 3 m of one another across the plane. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F13 (GENERATED): Drill-line sections with the selected-dip planes. One vertical east-west section per drill line (relative depth). Intervals: filled vermillion indicator 1, open blue indicator 0. Black traces: planes of the selected apparent dip +0 degrees (positive dips toward east), spaced 20 m across the plane. Visual aid only; the dip is statistically selected and is not a measured orientation. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.

## 9. Tests

```text
...............................................................          [100%]
63 passed in 23.93s
```

## 10. Deviations and corrections in this stage

- The first analysis under configuration 1 was judged invalid after inspection (section 4); configuration 2 was written before any configuration-2 result was computed.
- The first configuration-2 analysis stopped on a coding error (every sensitivity value was converted to a number, so the text value for within-hole inclusion raised an error). The partial database was set aside and the import and analysis were repeated from an empty database.
- The first handoff rationale stated only that no lateral model was FITTED. The rationale now lists each model's reason; the decision is unchanged.
- The gate set was extended after the first VERIFY run to cover the stage exit requirements of specification 03 (G07, G15, G18, G21 to G24), G05 and G06 were brought into line with the specification wording, and G28 now covers tables. Gate results shown here come from the final VERIFY run before this report was written.
- The table query registry was added (schema O2-SCHEMA-2026.11.05-3) so that every table has a registered SQL hash, as figures already had.
- Figures were re-rendered several times for layout only (label placement, explicit margins, legend contents). The data rows were not changed between renders.
- The sensitivity variant STRICT_SUPPORT_200_PAIRS did not change any supported bin: the 200-pair threshold is not binding for the lateral family, whose bins hold at least 1,559 pairs each. The binding support constraint is the independent hole-pair threshold. The result is reported as found; the configuration was not altered after the run.
- Anisotropy is not evaluated. The azimuth fits are not leave-one-line-out tested, so no range ratio is claimed.
- The independent comparison with scikit-gstat was denied by the permission system once. It was run after the user approved it in chat; its result is in section 13.
- A Stage A test rewrote three tracked F06 figures in the Objective 2 folder during a full test run. They were restored from git, and the test now renders into a temporary folder.
- Configuration 3 was written before it ran and was not changed afterwards. Its comparator sample is the DESIGN binary set. STRICT agrees with DESIGN on that set, so the comparator does not test the 81 intervals that DESIGN excludes; a comparator on the full STRICT sample would need a further predeclared version.
- Configuration O2-CFG-2026.11.05-4 adds one SKIP record for the tentative geologic orientation factor that specification 02 section 10 names. No numeric setting changed. Configuration 2 is kept in config/objective_2/superseded/. The rebuilt database was compared with the configuration-2 build, and its experiments, fits and handoff are identical (decisions.md, O2-D15).
- The run order of `all` changed. Gates run before any figure or table is written, again before the report, and once more after the report (decisions.md, O2-D16). A STOP withdraws the receipt's handoff rows. Analysis rows are written once per receipt, so a withdrawn handoff needs a rebuild from an empty database.
- Gate G01 now also checks the row count against the receipt and every observed hole identifier against the upstream v_holes (specification 04, section 9). It previously checked only the version key and the content hash (decisions.md, O2-D17).
- Specifications 01, 03, 04 and 06 were corrected to the implemented command set, the nine figures, the within-hole pair flag and the gate numbers (decisions.md, O2-D17). Stage A's figures F05 to F09 are still under figures/objective_2: the Stage A registry tags F05 to F08 as Objective 2, and the Objective 1 database records the F05 and F06 outputs there. Moving them would change those database rows, so the move is left for a decision (decisions.md, O2-D14).
- The official Spec Kit initialisation (specify init) and the agent-side Spec Kit commands were not run. Re-initialising an existing project risks overwriting its templates. Specifications 01 to 07 and the task table in specification 07 are the record instead (specification 07, section 1a).

## 11. Objective 3 handoff contract

- Decision: NOT_IDENTIFIABLE. Candidate family: NONE.
- Parameters: none are supplied. The lateral family did not yield a FITTED, stable model, so no search range or leave-one-line-out envelope is handed over.
- Full-data parameters for test folds: 0. Any Objective 3 variogram must be refitted inside each outer training fold.
- Allowed: models without a geostatistical continuity term, judged against the gates and the untouched test folds.
- Not allowed: between-hole continuity parameters from these fits, and any claim of spatial continuity between holes.
- Within-hole continuity (downhole range about 15 to 24 m) is a descriptive result. It is not a between-hole basis.
- Lag setting recorded for reference: {"family": "LATERAL_BETWEEN", "lag_max_m": 500.0, "lag_width_m": 20.0, "max_abs_dz_m": 3.0, "min_independent_hole_pairs_per_bin": 10, "min_pairs_per_bin": 100}

## 12. Limitations

- Relative depth only: collar elevations are absent, so absolute elevation and the DEM are not used.
- One orientation for all holes (dip -60, azimuth 090): geology cannot be separated from the sampling direction.
- Five drill lines; the between-line contrast is large and its cause is not resolved.
- The lateral window (20 m bins to 500 m) excludes most collar pairs; regional structure beyond it is not assessed.
- Line NOM_N1111930 has 3 holes (84 binary intervals). Any statement about that line rests on those collars. No gate issues a WARN for it, and no direction is FITTED, so no fitted range depends on it.

## 13. Commands and environment

```bash
./.venv/Scripts/python.exe -I -m kambale.objective_2 all
./.venv/Scripts/python.exe -I -m pytest -o addopts= -q tests/objective_2 > reports/objective_2/PYTEST_OUTPUT.txt
./.venv/Scripts/python.exe -I -m kambale.objective_2 report
./.venv/Scripts/python.exe -I -m kambale.objective_2 verify
```

`all` runs import, analyse, extension, weathering, structural, verify, figures, tables, verify, report and verify. The stages can also be run one at a time with `import`, `analyse`, `extension`, `weathering`, `structural`, `figures`, `tables`, `report` and `verify`. The report reads PYTEST_OUTPUT.txt, so the test run comes before the second report.

Python 3.14.6 on Windows 11; numpy 2.4.6, scipy 1.18.0, matplotlib 3.11.1, PyYAML 6.0.3, pytest 9.1.1.
Independent check: scikit-gstat was installed with uv into a scratch directory outside the project environment, because installing it into the project environment would downgrade scipy from 1.18.0 to 1.16.3. The comparison ran after the user approved it in chat, on the three-dimensional omnidirectional experiment with within-hole pairs included, which scikit-gstat's Matheron estimator also uses. Maximum absolute difference in semivariance: 2.776e-17 (tolerance 1e-09). Result: PASS. The lateral basis is not compared directly, because scikit-gstat cannot restrict pairs to a relative-depth band. Both use the same estimator, so the agreement is evidence for the pair counting and the binning. It is run from a scratch directory outside the project environment: `./.venv/Scripts/python.exe -I -m kambale.objective_2.independent_check --site <scratch-directory>`.

## 14. Database row counts and receipt hashes

| table | rows |
|---|---|
| analysis_observations | 1910 |
| anisotropy_diagnostics | 2 |
| bootstrap_gamma_bands | 50 |
| collar_locations | 71 |
| comparator_observations | 1910 |
| continuity_handoff_decisions | 1 |
| depth_lithology_summaries | 28 |
| direction_registry | 9 |
| export_manifests | 67 |
| figure_query_registry | 34 |
| figure_registry | 13 |
| gate_results | 501 |
| geological_section_registry | 5 |
| hole_occurrence_summaries | 71 |
| line_occurrence_summaries | 5 |
| pair_sampling_diagnostics | 180 |
| schema_version | 1 |
| sensitivity_runs | 56 |
| source_receipts | 1 |
| spatial_support_statistics | 17 |
| stage_runs | 20 |
| structural_alignment_scores | 68 |
| structural_between_line | 20 |
| structural_decisions | 2 |
| structural_fits | 8 |
| structural_lolo_dips | 20 |
| structural_null_summary | 4 |
| structural_pair_digests | 68 |
| structural_variogram_bins | 200 |
| table_query_registry | 7 |
| table_registry | 7 |
| variogram_experiments | 40 |
| variogram_fit_parameters | 42 |
| variogram_fits | 80 |
| variogram_lag_bins | 1135 |
| weathering_cross_tabs | 12 |
| weathering_front_diagnostics | 20 |
| weathering_front_observations | 71 |
| weathering_front_variogram | 20 |

Receipt 1: content SHA-256 abf6f758faf75c82a250931ab034b145574a10f98362424e93dd6cc6483dea22; ordered identifier digest a94753f238d017f378b4b81fa61fcb061b63c62a687a68bafcdbbaf480027f55; selection query SHA-256 677203494777ff7efc26c6e5286142522049c7112f95109ed366a2da3481a767. Counts are taken when this report is written.

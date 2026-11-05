# Objective 2 run report: spatial distribution, geological controls and indicator variography

Configuration O2-CFG-2026.11.05-2 (SHA-256 ab3bc367fc82), code 2.1.0, schema O2-SCHEMA-2026.11.05-4, commit ef1a853. Import run 1, analysis run 2, gate run 6. Report written 2026-11-05T14:34:47Z.

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

Predeclared version O2-CFG-2026.11.05-2 supersedes O2-CFG-2026.11.05-1. Correction: Configuration 1 measured every between-hole lag in three dimensions. Vertical separation between intervals at different depths then dominated the lag, and the directional classes used three-dimensional distances. Configuration 2 assesses lateral continuity with horizontal lag distances between intervals at similar depth (absolute relative-Z difference at most 3 m). The three-dimensional family is kept and reported, but it is not the handoff basis. Configuration 1 gave a flat omnidirectional curve at the marginal variance and a fitted range at the 10 m lower bound. That result is recorded in RUN_REPORT.md as superseded and is not used.

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

## 6. Gate results (VERIFY run 6)

| gate | name | status | detail |
|---|---|---|---|
| G01 | Receipt match | PASS | recomputed content abf6f758faf7 vs receipt abf6f758faf7 |
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
| G16 | Leave-one-line-out stability | PASS | 0 fits are unstable; 10 refit rows for 5 lines (two models each) |
| G17 | Marginal variance departure | PASS | 0 fits depart from p(1-p) by more than 50 per cent |
| G18 | Anisotropy claims | PASS | anisotropy decisions: NOT_EVALUATED 2 |
| G19 | Base excludes within-hole pairs | PASS | 0 base between-hole experiments include within-hole pairs; lateral handoff base present: True |
| G20 | Sensitivity completeness | PASS | 7 of 7 configured sensitivity entries have a row (completed or skipped with reason) |
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

## 7. Tables

- O2-T01: GENERATED, 76 rows; Hole and line geological summary with support.
- O2-T02: GENERATED, 6 rows; Indicator prevalence, ambiguity and missingness by line.
- O2-T03: GENERATED, 36 rows; Variogram fitting report.
- O2-T04: GENERATED, 13 rows; Handoff contract and open items.

### O2-T03 variogram fitting report


Leave-one-line-out refits are summarised by the envelope columns. Ranges are metres; nugget and sill are indicator units; p(1 - p) is the marginal variance.
Source: sql/objective_2/tables/O2-T03.sql, receipt 1, 36 rows.

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
Source: sql/objective_2/tables/O2-T04.sql, receipt 1, 13 rows.

| item_type | item_id | status | detail |
|---|---|---|---|
| DIRECTION | LAT_AZ_000 | SKIPPED | 3 supported bins; 5 required |
| DIRECTION | LAT_AZ_045 | SKIPPED | 0 supported bins; 5 required |
| DIRECTION | LAT_AZ_135 | SKIPPED | 0 supported bins; 5 required |
| GATE | G09 | WARN | Declared orientation: survey orientations [(-60.0, 90.0)]; declared (-60.0, 90.0); uniform across holes = True |
| GATE | G10 | WARN | Class imbalance: lines below 10 per cent positive: NOM_N1113000 0.041 |
| GATE | G12 | WARN | Directional support: skipped directions: LAT_AZ_000, LAT_AZ_045, LAT_AZ_135 |
| GATE | G21 | WARN | Relative depth only: 5 of 5 sections labelled RELATIVE_DEPTH; no collar elevation is available, so the relative-depth limitation is always reported |
| HANDOFF | O3-HANDOFF-1 | NOT_IDENTIFIABLE | candidate_family=NONE; full_data_parameters_for_test_folds=0; No lateral model is both FITTED and stable under leave-one-line-out: spherical NOT_IDENTIFIABLE (structured sill below 5% of p(1-p): no structure beyond the nugget); exponential NOT_IDENTIFIABLE (range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget). Lateral continuity is not identified at this support. Objective 3 must not use a between-hole continuity model whose parameters come from these fits; models without a geostatistical continuity term may proceed without a continuity claim. |
| QUESTION | COLLAR_RL | OPEN | no collar elevation (RL) is available; depth is relative to collar and absolute elevation is not used |
| QUESTION | LAG_WINDOW | OPEN | collar pairs have a median separation of 921.0 m, while the lateral lag window ends at 500.0 m; longer-range structure is not assessed |
| QUESTION | LINE_PREVALENCE | OPEN | binary prevalence by line ranges from 0.041 to 0.506 across 5 lines; whether this reflects zones, sampling or geology is not resolved |
| SENSITIVITY | ABSOLUTE_ELEVATION_GEOMETRY | SKIPPED | SKIP_NO_VALIDATED_RL: not run |
| SENSITIVITY | STRICT_LABEL_COMPARATOR | SKIPPED | SKIP_NOT_AUTHORISED: not run |

Table O2-T01 (hole and line summary) and table O2-T02 (prevalence by line) are in tables/objective_2 as CSV, Markdown and LaTeX.

## 8. Figures

- O2-F01 (GENERATED): Drill-hole plan view by approved line. Plan view of 71 collars grouped by drill line (labels at the western collar of each line) with the midpoints of 525 POSITIVE intervals. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F02 (GENERATED): Positive metres and graphitic fraction by hole and line. Positive share (fraction) and positive apparent thickness (m) for 71 holes and 5 lines; 525 positive intervals. Each denominator is the number of binary intervals of that hole or line. Line labels are the nominal northing groups without their NOM_ prefix. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F03 (GENERATED): Binary occurrence by depth and by weathering class. Left: positive share of binary intervals by 10 m depth bin (variable: depth from collar; all rock codes pooled). Right: intervals by logged weathering code and label state (variables: weathering code; label state). Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F04 (GENERATED): Observed hole strips in relative depth. Logged intervals of the two holes per line with the most binary intervals, drawn as strips in depth below collar (m); lines shown: NOM_N1111930, NOM_N1112140, NOM_N1112500, NOM_N1112600, NOM_N1113000. Excluded intervals are hatched. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F05 (GENERATED): Pair support by lag. Number of pairs and of independent hole pairs per lag bin for the base experiments (counts only; no semivariance). Within-hole pairs are shown separately from between-hole pairs. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F06 (GENERATED): Between-hole indicator semivariograms. Experimental indicator semivariograms of between-hole pairs for the lateral basis (horizontal lag, relative-depth difference at most 3 m) and the three-dimensional family (reported). Dashed line: marginal variance p(1 - p) = 0.205; no base fit is FITTED, so no curve is drawn (fit status in O2-T03). Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F07 (GENERATED): Horizontal azimuth semivariograms (exploratory). Horizontal azimuth semivariograms (exploratory) at 0, 45, 90 and 135 degrees clockwise from grid north, tolerance ±22.5°. Dashed line: p(1 - p) = 0.205. Under-powered bins are marked with their pair counts; a direction with no supported bin is SKIPPED. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F08 (GENERATED): Sensitivity of supported bins and fit status. Supported lag bins and fit status (spherical and exponential) for 8 completed sensitivity experiments and their base experiments; 2 configured entries were skipped, with reasons shown in the figure. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.
- O2-F09 (GENERATED): Configuration-3 lateral extension with the STRICT comparator (exploratory). Configuration-3 exploratory lateral extension: experimental indicator semivariograms with 50 m bins to 2000 m and a relative-depth difference of at most 3 m, for DESIGN_8_2_v1 (approved, primary) and STRICT_SGS_v1 (comparator, authorised for this run only). Dashed line: the DESIGN marginal variance; dotted line, where it differs: the STRICT marginal variance; no model is FITTED, so no curve is drawn. The two samples give identical semivariances at every lag, because the comparator reproduces the DESIGN indicator on every DESIGN binary interval; the series coincide, so the comparator is drawn as hollow markers. Support: 1 m logged intervals. Geometry PROVISIONAL_RELATIVE: straight holes, collar elevation absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.

## 9. Tests

```text
.............................................................            [100%]
61 passed in 6.12s
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

## 13. Commands and environment

```bash
./.venv/Scripts/python.exe -I -m kambale.objective_2 import
./.venv/Scripts/python.exe -I -m kambale.objective_2 analyse
./.venv/Scripts/python.exe -I -m kambale.objective_2 figures
./.venv/Scripts/python.exe -I -m kambale.objective_2 tables
./.venv/Scripts/python.exe -I -m kambale.objective_2 verify
./.venv/Scripts/python.exe -I -m kambale.objective_2 report
./.venv/Scripts/python.exe -I -m pytest -o addopts= -q tests/objective_2
```

Python 3.14.6 on Windows 11; numpy 2.4.6, scipy 1.18.0, matplotlib 3.11.1, PyYAML 6.0.3, pytest 9.1.1.
Independent check: scikit-gstat was installed with uv into a scratch directory outside the project environment, because installing it into the project environment would downgrade scipy from 1.18.0 to 1.16.3. The comparison ran after the user approved it in chat, on the three-dimensional omnidirectional experiment with within-hole pairs included, which scikit-gstat's Matheron estimator also uses. Maximum absolute difference in semivariance: 2.776e-17 (tolerance 1e-09). Result: PASS. The lateral basis is not compared directly, because scikit-gstat cannot restrict pairs to a relative-depth band. Both use the same estimator, so the agreement is evidence for the pair counting and the binning.

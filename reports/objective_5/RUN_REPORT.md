# Objective 5 run report: model-based three-dimensional uncertainty (part 1)

Configuration O5-CFG-2026.11.06-2 (supersedes O5-CFG-2026.11.06-1); SHA-256 of the configuration bytes 77227d3a23ceb6ba50d93994d83ca7a1a367ba36451cb28d6271409413169893. Generated 2026-11-06T14:37:37Z. Relative depth below collar throughout; absolute elevation is not used.

Status: parts 1 and 2 of the predeclared stage. Part 2 is a scenario analysis with an assumed lateral range (section 10).

## 1. Inputs and receipts

| role | path | bytes | SHA-256 |
|---|---|---|---|
| o2_database | database/kambale_obj2_spatial.sqlite | 1232896 | e82be7e8802f31e0eb2f2af952f94b5e95b098ac98a5d83c8983569951087d2e |
| o3_config | config/objective_3/model_config.yaml | 7558 | 47569e360e552b442cef675ba0f709b44d036b783b8e230be0ee1762f98744f3 |
| o3_database | database/kambale_obj3_models.sqlite | 26550272 | d02654ee1c2f0bb610450cd89c12eac9903c99dca099c40607089724860fb412 |
| o4_tier_1_extrapolation_database | database/kambale_obj4_validation.sqlite | 22806528 | 4825a637856e898238ef3cbf1b72dc346165a3ccef77983313f02b9cd07db5de |
| o4_tier_2_interpolation_database | database/kambale_obj4_validation_tier2.sqlite | 23867392 | f60e4fd2aee3f09ff8f154e12d3a2bb95605db546b1e174176c9e9573c62393f |
| o5_config | config/objective_5/uncertainty_config.yaml | 14117 | 77227d3a23ceb6ba50d93994d83ca7a1a367ba36451cb28d6271409413169893 |
| thesis_database | database/kambale_thesis.sqlite | 10289152 | 096ffbb0b5f6b0e93a10d4188a79406137bba4628a39f64bb47077b132b1e0f5 |

Objective 3 receipt 1: 1910 logged intervals, 1829 binary intervals (DESIGN_8_2_v1), 71 holes, prevalence 0.2870.

Locked handoffs (selected and runner-up read from the Objective 4 comparison_decisions rows with role SELECTED and COMPARATOR):

| tier | selected | runner-up | match | improvement status | delta Brier (sel - ru) | 95% interval |
|---|---|---|---|---|---|---|
| TIER_1_EXTRAPOLATION | BASE_LOGISTIC_WF | M2_RF | MATCH | INCONCLUSIVE | -0.0004448 | [-0.01396, 0.01374] |
| TIER_2_INTERPOLATION | M2_HGB_WF | M2_HGB | MATCH | INCONCLUSIVE | -0.001764 | [-0.00695, 0.00287] |

Down-hole variogram (Objective 2 fit 16, exponential): nugget 0.012760, structured sill 0.213132, practical range 23.5297 m; maximum absolute difference from the predeclared values 1.85e-05 (status MATCH).

## 2. Final refits

Each selected and runner-up model was refitted once on all binary intervals with the Objective 3 rules. In-sample Brier and AUC are fit diagnostics only.

| tier | role | model | hyperparameters | calibration | intercept | slope | in-sample Brier | in-sample AUC |
|---|---|---|---|---|---|---|---|---|
| TIER_1_EXTRAPOLATION | SELECTED | BASE_LOGISTIC_WF | {"C":0.1,"class_weight":null,"max_iter":2000} | SKIPPED |  |  | 0.1525 | 0.806 |
| TIER_1_EXTRAPOLATION | RUNNER_UP | M2_RF | {"max_depth":8,"max_features":"sqrt","min_samples_leaf":20,"n_estimators":200} | FITTED | 0.02482 | 1.002 | 0.1017 | 0.934 |
| TIER_2_INTERPOLATION | SELECTED | M2_HGB_WF | {"l2_regularization":1.0,"learning_rate":0.05,"max_iter":150,"max_leaf_nodes":7,"min_samples_leaf":20} | FITTED | -0.2215 | 0.6413 | 0.09784 | 0.9528 |
| TIER_2_INTERPOLATION | RUNNER_UP | M2_HGB | {"l2_regularization":0.0,"learning_rate":0.05,"max_iter":150,"max_leaf_nodes":7,"min_samples_leaf":20} | FITTED | -0.1644 | 0.713 | 0.09804 | 0.9482 |

Full-data hyperparameters against the most frequent Objective 3 per-fold choice:

| tier | model | folds | O3 most frequent | count | tied modes | matches |
|---|---|---|---|---|---|---|
| TIER_1_EXTRAPOLATION | BASE_LOGISTIC_WF | 5 | {"C":0.1,"class_weight":null,"max_iter":2000} | 3 | 0 | yes |
| TIER_1_EXTRAPOLATION | M2_RF | 5 | {"max_depth":4,"max_features":"sqrt","min_samples_leaf":5,"n_estimators":200} | 2 | 1 | no |
| TIER_2_INTERPOLATION | M2_HGB_WF | 5 | {"l2_regularization":1.0,"learning_rate":0.05,"max_iter":150,"max_leaf_nodes":7,"min_samples_leaf":20} | 3 | 0 | yes |
| TIER_2_INTERPOLATION | M2_HGB | 5 | {"l2_regularization":1.0,"learning_rate":0.05,"max_iter":150,"max_leaf_nodes":7,"min_samples_leaf":20} | 3 | 0 | no |

## 3. Grid and zones

Grid: 244 x 129 x 28 cells = 881328 cells; cell 10 x 10 x 2 m; cell volume 200 m3 (relative grid volume only). Origin E 548100, N 1.11182e+06; margin 100 m around the 71 collars.

| zone | cells | relative volume (m3) | DEPTH_EXTRAPOLATED cells |
|---|---|---|---|
| EXTRAPOLATION | 829192 | 1.658e+08 | 460313 |
| INTERPOLATION | 28000 | 5.6e+06 | 12777 |
| NO_SUPPORT | 24136 | 4.827e+06 | 12924 |

## 4. Classes

| zone | class | cells | relative volume (m3) | cells above weathering front |
|---|---|---|---|---|
| EXTRAPOLATION | CONFIDENT_ABSENT | 221295 | 4.426e+07 | 106056 |
| EXTRAPOLATION | CONFIDENT_PRESENT | 28868 | 5.774e+06 | 0 |
| EXTRAPOLATION | UNCERTAIN | 579029 | 1.158e+08 | 4412 |
| INTERPOLATION | CONFIDENT_ABSENT | 8977 | 1.795e+06 | 3435 |
| INTERPOLATION | CONFIDENT_PRESENT | 972 | 1.944e+05 | 0 |
| INTERPOLATION | UNCERTAIN | 18051 | 3.61e+06 | 292 |
| NO_SUPPORT | NO_SUPPORT | 24136 | 4.827e+06 | 3543 |

Sensitivity at the training prevalence 0.2870 (headline threshold 0.5):

| zone | class at prevalence | cells |
|---|---|---|
| EXTRAPOLATION | CONFIDENT_ABSENT | 142425 |
| EXTRAPOLATION | CONFIDENT_PRESENT | 79387 |
| EXTRAPOLATION | UNCERTAIN | 607380 |
| INTERPOLATION | CONFIDENT_ABSENT | 4827 |
| INTERPOLATION | CONFIDENT_PRESENT | 3027 |
| INTERPOLATION | UNCERTAIN | 20146 |
| NO_SUPPORT | NO_SUPPORT | 24136 |

Confident classes depend on the width of the bootstrap interval of the zone's model. The tier-1 logistic model is smooth and its bootstrap intervals are narrow, so CONFIDENT classes in the EXTRAPOLATION zone reflect a stable simple trend, not better knowledge: its validated skill (tier 1) is lower than the tier-2 model's. EXTRAPOLATION-zone classes must be read with the tier-1 validation in O5-T03 and the model-disagreement map, and are not comparable with INTERPOLATION-zone classes.

## 5. Interval width and disagreement by zone

Median and 90th percentile over the supported cells of each zone.

| zone | width median | width P90 | disagreement median | disagreement P90 |
|---|---|---|---|---|
| INTERPOLATION | 0.3812 | 0.519 | 0.0311 | 0.09171 |
| EXTRAPOLATION | 0.1806 | 0.3178 | 0.201 | 0.5248 |

## 6. Carried validation (Objective 4, not recomputed)

| tier | role | model | metric | pooled value (interval-weighted) | n |
|---|---|---|---|---|---|
| TIER_1_EXTRAPOLATION | RUNNER_UP | M2_RF | BRIER | 0.1655 | 1829 |
| TIER_1_EXTRAPOLATION | RUNNER_UP | M2_RF | ROC_AUC | 0.7816 | 1829 |
| TIER_1_EXTRAPOLATION | SELECTED | BASE_LOGISTIC_WF | BRIER | 0.1651 | 1829 |
| TIER_1_EXTRAPOLATION | SELECTED | BASE_LOGISTIC_WF | ROC_AUC | 0.7487 | 1829 |
| TIER_2_INTERPOLATION | RUNNER_UP | M2_HGB | BRIER | 0.1548 | 1829 |
| TIER_2_INTERPOLATION | RUNNER_UP | M2_HGB | ROC_AUC | 0.8113 | 1829 |
| TIER_2_INTERPOLATION | SELECTED | M2_HGB_WF | BRIER | 0.1531 | 1829 |
| TIER_2_INTERPOLATION | SELECTED | M2_HGB_WF | ROC_AUC | 0.8142 | 1829 |

## 7. Bootstrap

| zone | model | replicates | successful | fraction | runtime (s) | status |
|---|---|---|---|---|---|---|
| EXTRAPOLATION | BASE_LOGISTIC_WF | 200 | 200 | 1 | 26.1 | PASS |
| INTERPOLATION | M2_HGB_WF | 200 | 200 | 1 | 100.4 | PASS |

## 8. Gates

| gate | name | status | detail |
|---|---|---|---|
| G01 | Input file receipts | PASS | 0 input files differ from their receipts |
| G02 | Locked handoff receipts match configuration | PASS | selected and runner-up models match for both tiers |
| G03 | Down-hole variogram parameters | PASS | fit 16 exponential; maximum absolute difference 1.85e-05 |
| G04 | No absolute elevation used | PASS | grid columns with elevation tokens: []; refits with other predictors: []; vertical axis is z_relative_m |
| G05 | Probabilities in [0, 1] and present for every supported cell | PASS | 0 supported cells violate the rule |
| G06 | Bootstrap success fraction | PASS | INTERPOLATION: 200/200; EXTRAPOLATION: 200/200 |
| G07 | Weathering front on the grid recomputed from observed hole fronts | PASS | 71 observed fronts; 31476 horizontal cells; maximum absolute difference 0.00e+00 (tolerance 1e-09); front table matches recomputation: True |
| G08 | NO_SUPPORT cells carry no probability or confident class | PASS | 0 NO_SUPPORT cells carry a probability or a class other than NO_SUPPORT |
| G09 | Grid cell counts consistent | PASS | 881328 cells stored; 881328 expected from the axes; 881328 distinct; 28 layers |
| G10 | Zones recomputed from collar coordinates | PASS | 71 collars (brute force, thesis database); 0 cells differ from the stored zone |
| G11 | Depth support recomputed | PASS | 0 cells differ from the recomputed depth-support flag |
| G12 | Final model artifacts match their SHA-256 records | PASS | 0 artifacts differ |
| G13 | Classification recomputed from stored probabilities | PASS | 0 cells differ from the recomputed class |
| G14 | Carried Objective 4 validation equals the source | PASS | 0 carried values differ from the Objective 4 pooled metrics |
| G15 | uint8 quantisation round trip | PASS | maximum round-trip error 0.001961 (limit 1/510 = 0.001961) |
| S01 | Scenario set matches configuration | PASS | [('SIS_AH015', 15.0), ('SIS_AH025', 25.0), ('SIS_AH050', 50.0), ('SIS_AH100', 100.0), ('SIS_AH200', 200.0)] |
| S02 | Realisation count, neighbour limits and seed | PASS | realisations per scenario {'SIS_AH015': 100, 'SIS_AH025': 100, 'SIS_AH050': 100, 'SIS_AH100': 100, 'SIS_AH200': 100}; neighbour limits 24/12; seed 20261109; mismatches [] |
| S03 | Vertical ranges match the expected values | PASS | a_v within 0.01 of the expected values; infeasibility recorded |
| S04 | Simulation nodes inside the domain | PASS | 0 simulated cells outside INTERPOLATION and SUPPORTED |
| W01 | Full-data hyperparameters versus the most frequent Objective 3 fold choice | WARN | TIER_1_EXTRAPOLATION M2_RF: full {"max_depth":8,"max_features":"sqrt","min_samples_leaf":20,"n_estimators":200} vs O3 mode {"max_depth":4,"max_features":"sqrt","min_samples_leaf":5,"n_estimators":200} (5 folds); TIER_2_INTERPOLATION M2_HGB: full {"l2_regularization":0.0,"learning_rate":0.05,"max_iter":150,"max_leaf_nodes":7,"min_samples_leaf":20} vs O3 mode {"l2_regularization":1.0,"learning_rate":0.05,"max_iter":150,"max_leaf_nodes":7,"min_samples_leaf":20} (5 folds) |
| W02 | Share of INTERPOLATION cells that are DEPTH_EXTRAPOLATED | PASS | 0.456 of 28000 interpolation cells |
| W03 | Mean simulated frequency against mean local mean | PASS | all scenarios within 0.05 |

## 9. Figures and tables

| id | title | status | detail |
|---|---|---|---|
| O5-F01 | Support zones in plan | GENERATED | rendered from O5-F01.sql; 31476 rows |
| O5-F02 | Probability depth slices | GENERATED | rendered from O5-F02.sql; 157380 rows |
| O5-F03 | Bootstrap interval width depth slices | GENERATED | rendered from O5-F03.sql; 157380 rows |
| O5-F04 | Model disagreement depth slices | GENERATED | rendered from O5-F04.sql; 157380 rows |
| O5-F05 | Class depth slices with weathering-front tag | GENERATED | rendered from O5-F05.sql; 157380 rows |
| O5-F06 | Along-line sections | GENERATED | rendered from O5-F06.sql; 34160 rows |
| O5-F07 | Three-dimensional view | GENERATED | rendered from O5-F07.sql; 19023 rows |
| O5-F08 | Graphitic grid volume distribution per scenario | GENERATED | rendered from O5-F08.sql; 500 rows |
| O5-F09 | Connectivity per scenario | GENERATED | rendered from O5-F09.sql; 500 rows |
| O5-F10 | Realisation and frequency section per scenario | GENERATED | rendered from O5-F10.sql; 34160 rows |

| id | title | status | rows |
|---|---|---|---|
| O5-T01 | Cell counts and relative grid volume by class, zone and depth band | GENERATED | 33 |
| O5-T02 | Sensitivity of the class counts to the decision threshold | GENERATED | 14 |
| O5-T03 | Validated skill carried from Objective 4 beside the class counts | GENERATED | 2 |
| O5-T04 | Final-refit record | GENERATED | 4 |
| O5-T05 | Scenario simulation summary (assumed lateral range) | GENERATED | 5 |
| O5-T06 | Scenario reproduction checks | GENERATED | 36 |

## 10. Scenario simulation (scenario analysis; lateral range assumed, not estimated)

Sequential indicator simulation with a locally varying mean (tier-2 M2_HGB_WF, calibrated), residual simple kriging with up to 24 conditioning data and 12 previously simulated nodes within anisotropy-scaled distance 1.0, 100 realisations per scenario, seed 20261109. Vertical range set so that the range along the hole direction (plunge 60 degrees) equals the fitted down-hole practical range. This is a scenario analysis: each lateral range is assumed, scenarios are reported separately and never pooled.

| scenario | a_h (m) | a_v (m) | volume P10 (m3) | volume P50 (m3) | volume P90 (m3) | expected sum(m) x 200 (m3) | components P50 | largest share P10 | P50 | P90 |
|---|---|---|---|---|---|---|---|---|---|---|
| SIS_AH015 | 15 | 32.85 | 8.656e+05 | 9.089e+05 | 9.368e+05 | 9.13e+05 | 73 | 0.4448 | 0.4743 | 0.4983 |
| SIS_AH025 | 25 | 23.09 | 8.448e+05 | 8.891e+05 | 9.401e+05 | 9.13e+05 | 61 | 0.4456 | 0.4758 | 0.505 |
| SIS_AH050 | 50 | 20.97 | 8.327e+05 | 8.894e+05 | 9.317e+05 | 9.13e+05 | 40.5 | 0.4418 | 0.4885 | 0.5175 |
| SIS_AH100 | 100 | 20.52 | 8.525e+05 | 8.879e+05 | 9.442e+05 | 9.13e+05 | 34 | 0.467 | 0.5056 | 0.5332 |
| SIS_AH200 | 200 | 20.41 | 8.673e+05 | 9.157e+05 | 9.539e+05 | 9.13e+05 | 35 | 0.4823 | 0.5102 | 0.5367 |

Reproduction and gates per scenario:

| scenario | mean simulated frequency | mean local mean | difference | frequency status | SK fallbacks | neighbourless node visits (sum over realisations) | exact neighbour searches (sum) | downhole max abs diff (supported bins) | runtime (s) |
|---|---|---|---|---|---|---|---|---|---|
| SIS_AH015 | 0.2972 | 0.2999 | -0.0026 | PASS | 0 | 9931 | 0 | 0.0526 | 184 |
| SIS_AH025 | 0.2923 | 0.2999 | -0.0076 | PASS | 0 | 1039 | 0 | 0.0333 | 239 |
| SIS_AH050 | 0.2913 | 0.2999 | -0.0086 | PASS | 0 | 42 | 8428 | 0.0133 | 257 |
| SIS_AH100 | 0.2936 | 0.2999 | -0.0063 | PASS | 0 | 5 | 33436 | 0.0186 | 260 |
| SIS_AH200 | 0.2998 | 0.2999 | -0.0001 | PASS | 0 | 0 | 34903 | 0.0179 | 262 |

Spread across scenarios (the finding): the median simulated volume ranges from 8.879e+05 to 9.157e+05 m3 over the 5 feasible scenarios, against an expected volume of 9.13e+05 to 9.13e+05 m3. The median largest-component share ranges from 0.474 to 0.510 and the median component count from 34 to 73. The result is this spread, which depends on the assumed lateral range; it is not one volume.

Data semivariance recomputed here against the stored Objective 2 DOWNHOLE_WITHIN bins: maximum absolute difference 0.00e+00. Down-hole reproduction per scenario is in O5-T06 (lags 1, 5, 10, 20 and 30 m, and the maximum over supported bins).

Scenario claims: Volumes are relative grid volumes of the logged DESIGN_8_2_v1 domain inside the INTERPOLATION zone. They are not resources, carry no grade, and depend on the assumed lateral range; the spread across scenarios is the result.

## 11. Claims not permitted

- grade, tonnage, resource or reserve of any kind
- a geostatistical uncertainty with an estimated lateral covariance; scenario results rest on an assumed lateral range
- a single best-estimate graphitic volume pooled across scenarios
- a claim that one model family is better than another
- absence of graphite in cells above the weathering front
- any probability beyond 560 m from the nearest drilled collar


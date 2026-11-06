# Objective 4 run report: TIER_1_EXTRAPOLATION

Configuration O4-CFG-2026.11.06-3 (SHA-256 d065104043aa), code 4.1.0, schema O4-SCHEMA-2026.11.06-1, commit a9b54df. Import run 1, evaluation run 2, gate run 5. Report written 2026-11-06T15:16:24Z.

**Claim.** skill when predicting a whole undrilled line from the other four lines

## 1. Status

Every required exit gate is PASS.
Locked model choice: **BASE_LOGISTIC_WF**; improvement status **INCONCLUSIVE**; selection basis **POINT_ESTIMATE_WITH_CAVEAT**; comparator **M2_RF**.

## 2. Inputs and receipt

- Tier: TIER_1_EXTRAPOLATION; fold unit HELD_OUT_LINE; Objective 3 split plan O3-SPLIT-LODO-1 (SHA-256 e1193a349fcd3426).
- Objective 3 database: C:/Users/ThinkPad P1 G4/Documents/Joseph_Thesis/database/kambale_obj3_models.sqlite (read-only; receipt 1, config O3-CFG-2026.11.06-2).
- Frozen prediction snapshot SHA-256: ae1093c78017fcc7..., 20119 prediction rows and 0 failure rows.
- Objective 1 content SHA-256 abf6f758faf7; label rule DESIGN_8_2_v1 APPROVED; geometry PROVISIONAL_RELATIVE, RELATIVE_TO_COLLAR; datum VERIFIED.
- Common held-out cohort: 1829 intervals in 71 holes and 5 drill lines; positive prevalence 0.287 (525 positives).

## 3. Evaluation plan

- Primary endpoint: **BRIER**, INTERVAL-weighted; secondary weighting EQUAL_HOLE.
- Unit: logged interval; fold unit HELD_OUT_LINE; uncertainty resampled by hole (primary) and line (sensitivity).
- Cohort: intersection of the full-coverage feasible models on the held-out folds.
- Bootstrap: HOLE_CLUSTER primary; LINE_CLUSTER sensitivity; 2000 replicates per design, seed 20261105.
- Calibration policy: O3 calibration only; O4 fits diagnostics and never recalibrates.
- Plan SHA-256: 0136fc87af721ca00912fbbe5ccc721e423cb730dbfc57c4d88e82be1ed254e2.

## 4. Models: coverage, identity and decision role

| model | role | identity | identical to | coverage | status | comparable | decision |
|---|---|---|---|---|---|---|---|
| BASE_LOGISTIC | BASELINE | DISTINCT | - | 1829 / 1829 (1.000) | FULL | 1 | REJECTED |
| BASE_LOGISTIC_WF | BASELINE | DISTINCT | - | 1829 / 1829 (1.000) | FULL | 1 | SELECTED |
| BASE_PREVALENCE | BASELINE | DISTINCT | - | 1829 / 1829 (1.000) | FULL | 1 | REJECTED |
| M1_IK | M1 | DISTINCT | - | 1829 / 1829 (1.000) | FULL | 1 | REJECTED |
| M2_HGB | M2 | DISTINCT | - | 1829 / 1829 (1.000) | FULL | 1 | REJECTED |
| M2_HGB_WF | M2 | DISTINCT | - | 1829 / 1829 (1.000) | FULL | 1 | REJECTED |
| M2_RF | M2 | DISTINCT | - | 1829 / 1829 (1.000) | FULL | 1 | COMPARATOR |
| M2_RF_WF | M2 | DISTINCT | - | 1829 / 1829 (1.000) | FULL | 1 | REJECTED |
| M2_SEL | M2 | IDENTICAL_TO | M2_RF | 1829 / 1829 (1.000) | FULL | 0 | NOT_COMPARABLE |
| M2_WF_SEL | M2 | IDENTICAL_TO | M2_RF_WF | 1829 / 1829 (1.000) | FULL | 0 | NOT_COMPARABLE |
| M3_HYBRID | M3 | IDENTICAL_TO | M2_WF_SEL | 1829 / 1829 (1.000) | FULL | 0 | NOT_COMPARABLE |

Identity means the calibrated probabilities equal the named earlier feasible model's on every common interval (tolerance 1e-12). Identical models are reported once, are not ranked, and are NOT_COMPARABLE with that reason. Coverage and identity are separate columns.

Identities found: M2_SEL = M2_RF; M2_WF_SEL = M2_RF_WF; M3_HYBRID = M2_WF_SEL.

## 5. Primary probability results (pooled, interval-weighted)

| model | Brier | Brier (equal-hole) | log loss | ROC-AUC | PR-AUC | ECE | slope | intercept |
|---|---|---|---|---|---|---|---|---|
| BASE_LOGISTIC | 0.1658 | 0.1515 | 0.5074 | 0.7562 | 0.6153 | 0.0596 | 0.887 | 0.060 |
| BASE_LOGISTIC_WF | 0.1651 | 0.1515 | 0.5085 | 0.7487 | 0.6198 | 0.0562 | 0.878 | 0.053 |
| BASE_PREVALENCE | 0.2211 | 0.1996 | 0.6404 | 0.2878 | 0.2248 | 0.1649 | -3.567 | -4.320 |
| M1_IK | 0.2194 | 0.1975 | 0.6363 | 0.3333 | 0.2106 | 0.1277 | -3.472 | -4.269 |
| M2_HGB | 0.1715 | 0.1564 | 0.5252 | 0.7513 | 0.5768 | 0.0508 | 1.077 | 0.223 |
| M2_HGB_WF | 0.1657 | 0.1507 | 0.5099 | 0.7635 | 0.5987 | 0.0498 | 1.060 | 0.226 |
| M2_RF | 0.1655 | 0.1510 | 0.5016 | 0.7816 | 0.5739 | 0.0602 | 1.369 | 0.263 |
| M2_RF_WF | 0.1677 | 0.1536 | 0.5198 | 0.7706 | 0.5901 | 0.0537 | 0.994 | -0.009 |
| M2_SEL | 0.1655 | 0.1510 | 0.5016 | 0.7816 | 0.5739 | 0.0602 | 1.369 | 0.263 |
| M2_WF_SEL | 0.1677 | 0.1536 | 0.5198 | 0.7706 | 0.5901 | 0.0537 | 0.994 | -0.009 |
| M3_HYBRID | 0.1677 | 0.1536 | 0.5198 | 0.7706 | 0.5901 | 0.0537 | 0.994 | -0.009 |

Lower Brier and log loss are better; higher AUC and PR-AUC are better. Calibration slope and intercept are diagnostic fits on the held-out predictions and are not applied. Undefined metrics are n/a and carry a status in O4-T02. Best comparable model by metric: BRIER Logistic + weathering, LOG_LOSS Random forest, ECE Gradient boosting + weathering, ROC_AUC Random forest, PR_AUC Logistic + weathering. The metric ranking is not unanimous; differences are judged by the interval and the decision rule below, not by the point ranking alone.

## 6. Paired comparisons (difference = Brier(b) minus Brier(a))

Negative means model b has the lower Brier. The power label follows the hole-cluster interval: RESOLVED when it excludes zero; UNRESOLVED when it includes zero, with the half-width the smallest difference this design could have detected; IDENTICAL when the two models are the same predictions.

### 6.1 Nested chain: trend, then weathering, then kriging, and trend then kriging

| pair | a vs b | delta Brier (b - a) | 95% hole CI | 95% line CI | power | half-width | folds b lower | status |
|---|---|---|---|---|---|---|---|---|
| PREV_vs_M2SEL | Prevalence vs M2 selected (= RF) | -0.055610 | [-0.081147, -0.031441] | [-0.106003, -0.013305] | RESOLVED | - | 4 / 5 | DEFINED |
| M2SEL_vs_M2WFSEL | M2 selected (= RF) vs M2 + weathering selected | 0.002202 | [-0.003522, 0.007828] | [-0.003086, 0.008062] | UNRESOLVED | 0.005675 | 1 / 5 | DEFINED |
| M2WFSEL_vs_M3 | M2 + weathering selected vs M3 hybrid | 0.000000 | identical; no interval | n/a | IDENTICAL | n/a | 0 / 5 | IDENTICAL |
| PREV_vs_M1 | Prevalence vs M1 indicator kriging | -0.001748 | [-0.002533, -0.000909] | [-0.002791, -0.000584] | RESOLVED | - | 5 / 5 | DEFINED |

M3_HYBRID is identical to M2_WF_SEL on every common interval. Its residual kriging adds nothing in this evaluation: the contrast M2_WF_SEL to M3 is exactly zero by construction, and no hybrid advantage is claimed.

M1 (indicator kriging) is distinct from the prevalence baseline. Its contrast with the prevalence baseline is RESOLVED (delta -0.001748).

### 6.2 Weathering-front effect inside each family

| pair | a vs b | delta Brier (b - a) | 95% hole CI | 95% line CI | power | half-width | folds b lower | status |
|---|---|---|---|---|---|---|---|---|
| LOG_vs_LOGWF | Logistic vs Logistic + weathering | -0.000747 | [-0.002704, 0.001247] | [-0.003482, 0.001968] | UNRESOLVED | 0.001975 | 3 / 5 | DEFINED |
| RF_vs_RFWF | Random forest vs Random forest + weathering | 0.002202 | [-0.003522, 0.007828] | [-0.003086, 0.008062] | UNRESOLVED | 0.005675 | 1 / 5 | DEFINED |
| HGB_vs_HGBWF | Gradient boosting vs Gradient boosting + weathering | -0.005764 | [-0.008715, -0.003039] | [-0.011104, -0.001417] | RESOLVED | - | 5 / 5 | DEFINED |

### 6.3 Family comparisons

| pair | a vs b | delta Brier (b - a) | 95% hole CI | 95% line CI | power | half-width | folds b lower | status |
|---|---|---|---|---|---|---|---|---|
| LOG_vs_RF | Logistic vs Random forest | -0.000302 | [-0.013688, 0.011983] | [-0.010218, 0.013111] | UNRESOLVED | 0.012836 | 3 / 5 | DEFINED |
| RF_vs_HGB | Random forest vs Gradient boosting | 0.005965 | [-0.005874, 0.017428] | [0.000161, 0.018511] | UNRESOLVED | 0.011651 | 1 / 5 | DEFINED |

Every configured pair is listed in O4-T04 with its weighting sensitivity.

### 6.4 Which comparisons are powered

- RESOLVED (interval excludes zero): PREV_vs_M2SEL (-0.0556), PREV_vs_M1 (-0.0017), HGB_vs_HGBWF (-0.0058).
- UNRESOLVED (interval includes zero; smallest detectable difference = half-width): M2SEL_vs_M2WFSEL (+/- 0.0057), LOG_vs_LOGWF (+/- 0.0020), RF_vs_RFWF (+/- 0.0057), LOG_vs_RF (+/- 0.0128), RF_vs_HGB (+/- 0.0117).
- IDENTICAL (no interval; the two models are the same predictions): M2WFSEL_vs_M3 (M2_WF_SEL = M3_HYBRID).

## 7. Decision

| rank | model | role | identity | status | basis | delta Brier | 95% CI | folds better | calibration | discrimination | coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | BASE_LOGISTIC_WF | SELECTED | DISTINCT | INCONCLUSIVE | POINT_ESTIMATE_WITH_CAVEAT | -0.000445 | [-0.013957, 0.013737] | 2 | ACCEPTABLE | WORSE | 1.000 |
| 2 | M2_RF | COMPARATOR | DISTINCT | INCONCLUSIVE | NOT_SELECTED | 0.000445 | [-0.013737, 0.013957] |  | ACCEPTABLE | NOT_WORSE | 1.000 |
| 3 | M2_HGB_WF | REJECTED | DISTINCT | INCONCLUSIVE | NOT_SELECTED | 0.000646 | [-0.011402, 0.012945] |  | ACCEPTABLE | NOT_WORSE | 1.000 |
| 4 | BASE_LOGISTIC | REJECTED | DISTINCT | INCONCLUSIVE | NOT_SELECTED | 0.000747 | [-0.001247, 0.002704] |  | ACCEPTABLE | NOT_WORSE | 1.000 |
| 5 | M2_RF_WF | REJECTED | DISTINCT | INCONCLUSIVE | NOT_SELECTED | 0.002647 | [-0.012577, 0.016558] |  | ACCEPTABLE | NOT_WORSE | 1.000 |
| 6 | M2_HGB | REJECTED | DISTINCT | INCONCLUSIVE | NOT_SELECTED | 0.006410 | [-0.006870, 0.020272] |  | ACCEPTABLE | NOT_WORSE | 1.000 |
| 7 | M1_IK | REJECTED | DISTINCT | NO_IMPROVEMENT | NOT_SELECTED | 0.054307 | [0.024818, 0.084930] |  | NOT_ACCEPTABLE | WORSE | 1.000 |
| 8 | BASE_PREVALENCE | REJECTED | DISTINCT | NO_IMPROVEMENT | NOT_SELECTED | 0.056055 | [0.026688, 0.086717] |  | NOT_ACCEPTABLE | WORSE | 1.000 |
|  | M2_SEL | NOT_COMPARABLE | IDENTICAL_TO | NOT_COMPARABLE | NOT_RANKED | n/a | [n/a, n/a] |  | ACCEPTABLE | IDENTICAL_TO_M2_RF | 1.000 |
|  | M2_WF_SEL | NOT_COMPARABLE | IDENTICAL_TO | NOT_COMPARABLE | NOT_RANKED | n/a | [n/a, n/a] |  | ACCEPTABLE | IDENTICAL_TO_M2_RF_WF | 1.000 |
|  | M3_HYBRID | NOT_COMPARABLE | IDENTICAL_TO | NOT_COMPARABLE | NOT_RANKED | n/a | [n/a, n/a] |  | ACCEPTABLE | IDENTICAL_TO_M2_WF_SEL | 1.000 |

Rule (predeclared):
- Selection: LOWEST_POOLED_INTERVAL_BRIER_AMONG_DISTINCT_FULL_COVERAGE_MODELS.
- Comparator: NEXT_LOWEST_POOLED_INTERVAL_BRIER.
- Improvement rule (predeclared, verbatim from the config): SUPPORTED_IMPROVEMENT requires all of: the 95% hole-cluster bootstrap interval of (Brier_selected - Brier_comparator) lies entirely below zero; the selected model has the lower Brier in at least four of the five folds; the calibration slope is in [0.5, 2.0] and |intercept| <= 0.5; the selected model's ROC-AUC is not worse than the comparator's by more than 0.02; and coverage is at least 0.95. INCONCLUSIVE applies when the interval includes zero or fold consistency is below four of five. NO_IMPROVEMENT applies when the point estimate is non-negative or the interval lies entirely above zero. NOT_COMPARABLE applies to a model with coverage below 0.95, a missing metric, or an identity with another model.
- Calibration and discrimination are diagnostic conditions inside the rule; the calibration fit is never applied.

Selected BASE_LOGISTIC_WF against comparator M2_RF: delta Brier (selected minus comparator) -0.000445, 95% hole-cluster interval [-0.013957, 0.013737], selected better in 2 of 5 folds. Status **INCONCLUSIVE**. The point estimate selects this model, but the predeclared improvement rule is not met. The choice is a point-estimate selection with a caveat, and no credible improvement over the comparator is claimed.

No selection result here is a hybrid advantage: M3_HYBRID is identical to its trend (M2_WF_SEL), so any gain attributed to the hybrid family is zero by construction.

## 8. Gates

| gate | name | status | detail |
|---|---|---|---|
| G01 | Objective 3 snapshot receipt | PASS | recomputed snapshot ae1093c78017fcc7 vs receipt ae1093c78017fcc7; O3 receipt 1 |
| G02 | Frozen split plan | PASS | O3-SPLIT-LODO-1 hash e1193a349fcd3426; method LEAVE_ONE_DRILL_LINE_OUT for fold unit HELD_OUT_LINE; config plan O3-SPLIT-LODO-1 |
| G03 | Target, label and geometry reference | PASS | rule DESIGN_8_2_v1; geometry GEOM-10-1 PROVISIONAL_RELATIVE |
| G04 | Prediction snapshot integrity | PASS | 0 out-of-bounds probabilities; 0 duplicate model/observation pairs |
| G05 | Common cohort identical across full-coverage models | PASS | 1829 common observations; 11 full-coverage feasible models; 0 missing model IDs |
| G06 | Coverage recorded for every candidate and matched to the snapshot | PASS | 11 candidates; all coverage rows match the snapshot |
| G07 | Identities recorded match a recomputation | PASS | 55 feasible pairs recomputed; 4 identical; differences: none |
| G08 | Thresholds frozen from O3 | PASS | 0 snapshot thresholds differ from the O3 training-only thresholds |
| G09 | No model refit in O4 | PASS | O4 contains no training or model-artifact table |
| G10 | Evaluation plan declared | PASS | primary BRIER / INTERVAL |
| G11 | Cohort and weights declared | PASS | 0 non-positive weights; 1829 common observations |
| G12 | Bootstrap uses spatial units | PASS | designs: O4-BOOT-HOLE=HOLE_CLUSTER, O4-BOOT-LINE=LINE_CLUSTER |
| G13 | Metric numerical cross-check on every feasible model | PASS | Brier vector vs independent loop for 11 of 11 feasible models |
| G14 | Calibration is diagnostic only | PASS | 11 diagnostic rows; no recalibrated prediction column |
| G15 | Undefined metrics are not coerced | PASS | 0 undefined metrics carry a value |
| G16 | Decision rule followed | PASS | selected BASE_LOGISTIC_WF; lowest distinct Brier BASE_LOGISTIC_WF; comparator M2_RF |
| G17 | Locked handoff receipt | PASS | selected BASE_LOGISTIC_WF; receipt hash present |
| G18 | Figure and table query provenance | PASS | 0 figure and 0 table entries are unregistered or changed |
| G19 | Export hashes | PASS | 0 manifest entries are missing or differ from the file |
| G20 | Relative geometry only | PASS | PROVISIONAL_RELATIVE; RELATIVE_TO_COLLAR |
| G21 | No absolute-elevation product | PASS | absolute columns: none |
| G22 | No grade, tonnage or resource product | PASS | grade-like columns: none |
| G23 | No synthetic data | PASS | 0 receipts reference a non-Objective-3 source |
| G24 | Coverage reported for every candidate | PASS | 11 coverage rows for 11 candidates; 11 of 11 feasible models |
| G25 | Cluster uncertainty for decisions | PASS | selected decision carries a hole-cluster interval |
| G26 | External validity not claimed | PASS | handoff caveat states internal held-out validation |
| G27 | Objective 3 prediction snapshot | PASS | snapshot ae1093c78017fcc7 |
| G28 | Handoff matches the tier configuration | PASS | tier TIER_1_EXTRAPOLATION; split O3-SPLIT-LODO-1 vs config O3-SPLIT-LODO-1; claim matches |
| G29 | Power labels follow the intervals | PASS | each configured pair is RESOLVED, UNRESOLVED or IDENTICAL from its interval |

Exit gates: G01, G02, G03, G04, G05, G06, G07, G08, G10, G11, G12, G13, G15, G16, G17, G18, G19, G20, G21, G24, G25, G28, G29. All exit gates PASS.

## 9. Audit

- PASS O3_SNAPSHOT_HASH_RECORDED: snapshot ae1093c78017fcc7
- PASS COMMON_COHORT_IDENTICAL_ACROSS_FULL_FEASIBLE_MODELS: 1829 common observations; 11 full-coverage feasible models; 0 missing model IDs
- PASS COVERAGE_MATCHES_SNAPSHOT: coverage rows match snapshot rows
- PASS IDENTITY_RECORDED_MATCHES_RECOMPUTATION: 55 feasible pairs recomputed
- PASS PROBABILITY_BOUNDS: 0 out-of-bounds probabilities
- PASS THRESHOLDS_FROZEN_FROM_O3: 20119 snapshot rows carry the O3 threshold
- PASS BOOTSTRAP_USES_SPATIAL_UNITS: hole-cluster design present
- PASS BRIER_NUMERICAL_CROSS_CHECK: BASE_PREVALENCE: vector 0.221125015909; loop 0.221125015909
- PASS BRIER_NUMERICAL_CROSS_CHECK: BASE_LOGISTIC: vector 0.165816966303; loop 0.165816966303
- PASS BRIER_NUMERICAL_CROSS_CHECK: BASE_LOGISTIC_WF: vector 0.165070011275; loop 0.165070011275
- PASS BRIER_NUMERICAL_CROSS_CHECK: M2_RF: vector 0.165514789602; loop 0.165514789602
- PASS BRIER_NUMERICAL_CROSS_CHECK: M2_HGB: vector 0.171479709250; loop 0.171479709250
- PASS BRIER_NUMERICAL_CROSS_CHECK: M2_RF_WF: vector 0.167717246492; loop 0.167717246492
- PASS BRIER_NUMERICAL_CROSS_CHECK: M2_HGB_WF: vector 0.165715858972; loop 0.165715858972
- PASS BRIER_NUMERICAL_CROSS_CHECK: M2_SEL: vector 0.165514789602; loop 0.165514789602
- PASS BRIER_NUMERICAL_CROSS_CHECK: M2_WF_SEL: vector 0.167717246492; loop 0.167717246492
- PASS BRIER_NUMERICAL_CROSS_CHECK: M1_IK: vector 0.219376716075; loop 0.219376716075
- PASS BRIER_NUMERICAL_CROSS_CHECK: M3_HYBRID: vector 0.167717246492; loop 0.167717246492
- PASS BRIER_CROSS_CHECK_COVERS_FEASIBLE_MODELS: 11 feasible models cross-checked
- PASS POWER_LABELS_MATCH_INTERVALS: all configured pairs labelled from their intervals
- PASS NO_MODEL_REFIT: Objective 4 contains no training or model-artifact table
- PASS CALIBRATION_DIAGNOSTIC_ONLY: calibration intercept and slope are diagnostics; no recalibrated probability column exists

## 10. Tables

- O4-T01: GENERATED, 11 rows; Main evaluation summary.
- O4-T02: GENERATED, 55 rows; Fold-by-fold scores.
- O4-T03: GENERATED, 66 rows; Confusion matrices and threshold provenance.
- O4-T04: GENERATED, 18 rows; Paired difference uncertainty and weighting sensitivity.
- O4-T05: GENERATED, 11 rows; Final model-selection decision and handoff.

## 11. Figures

- O4-F01 (GENERATED): Spatial holdout fold map and coverage. rendered from the registered queries
- O4-F02 (GENERATED): Brier score by model and held-out line. rendered from the registered queries
- O4-F03 (GENERATED): ROC and PR curves. rendered from the registered queries
- O4-F04 (GENERATED): Reliability diagrams. rendered from the registered queries
- O4-F05 (GENERATED): Paired Brier differences with hole-cluster intervals and power labels. rendered from the registered queries
- O4-F06 (GENERATED): Selected-model residuals on withheld observations. rendered from the registered queries
- O4-F07 (GENERATED): Coverage and missing predictions. rendered from the registered queries

## 12. Tests

```text
.......................................................                  [100%]
```

## 13. Limitations

- Internal spatially held-out validation on five drill lines: extrapolation to an unseen line, not an external prospective campaign.
- The effective independent spatial units are 5 drill lines and 71 holes, not 1829 intervals. The primary uncertainty resamples holes; the line-level interval is a coarse sensitivity.
- Only easting, northing and relative Z are predictors. The models are spatial-trend and kriging models, not geological-covariate models.
- Relative Z only; no collar elevation or DEM. No absolute-elevation product.
- Where a pair is UNRESOLVED, the data cannot distinguish the models at the stated half-width; no ranking is claimed for that pair.
- No grade, tonnage or resource is estimated.
- The Objective 3 working tree is not committed; the hashes in the receipt identify the exact run.

## 14. Commands and environment

```bash
./.venv/Scripts/python.exe -I -m kambale.objective_4 all --tier 1
./.venv/Scripts/python.exe -I -m pytest tests/objective_4 -q
./.venv/Scripts/python.exe -I -m kambale.objective_4 report --tier 1
./.venv/Scripts/python.exe -I -m kambale.objective_4 verify --tier 1
```

`all` runs import, evaluate, verify, figures, tables, verify, report and verify. The tier argument selects the config, database and output directories.

Python 3.14.6 on Windows-11-10.0.26200-SP0; numpy 2.4.6; scipy 1.18.0; scikit-learn 1.9.0; matplotlib 3.11.1; PyYAML 6.0.3; pytest 9.1.1.

## 15. Database row counts and receipts

| table | rows |
|---|---|
| bootstrap_replicates | 120000 |
| calibration_bins | 72 |
| calibration_diagnostics | 11 |
| candidate_registry | 11 |
| class_confusion_matrices | 66 |
| comparison_decisions | 11 |
| evaluation_audit_log | 22 |
| evaluation_plan | 1 |
| evaluation_population | 1829 |
| export_manifests | 41 |
| figure_registry | 7 |
| figure_sql_registry | 17 |
| fold_metrics | 550 |
| gate_results | 87 |
| locked_handoff_receipts | 1 |
| metric_curve_points | 18532 |
| metric_definitions | 13 |
| model_identities | 55 |
| paired_differences | 198 |
| pooled_metrics | 110 |
| prediction_coverage | 11 |
| prediction_snapshot | 20119 |
| resampling_designs | 2 |
| schema_version | 1 |
| source_receipts | 1 |
| spatial_error_summaries | 546 |
| stage_runs | 5 |
| table_registry | 5 |
| table_sql_registry | 5 |

Counts are taken when this report is written. The post-report VERIFY run adds one `stage_runs` row and one gate set; it is the authoritative final check.

O3 snapshot SHA-256: ae1093c78017fcc79f49bbf5bcd61f086fadd19c0566ade720ff6709c900efbb. O3 split hash: e1193a349fcd34264519672cb3de9854b19e984a21b21d784b011220e9888c1f. O1 content SHA-256: abf6f758faf75c82a250931ab034b145574a10f98362424e93dd6cc6483dea22.


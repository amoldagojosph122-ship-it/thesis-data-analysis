# Objective 4 run report: independent spatial validation and probability-based performance

Configuration O4-CFG-2026.11.05-1 (SHA-256 198d0c5b81b2), code 4.0.0, schema O4-SCHEMA-2026.11.05-1, commit c15b680. Import run 1, evaluation run 2, gate run 8. Report written 2026-11-05T20:18:53Z.

## 1. Status

Every required exit gate is PASS.
Locked model choice: **M2_RF**; improvement status **INCONCLUSIVE**; selection basis **POINT_ESTIMATE_WITH_CAVEAT**.

## 2. Inputs and receipt

- Objective 3 database: C:/Users/ThinkPad P1 G4/Documents/Joseph_Thesis/database/kambale_obj3_models.sqlite (read-only; receipt 1, config O3-CFG-2026.11.05-1, split O3-SPLIT-LODO-1).
- Frozen prediction snapshot SHA-256: 41f89be1d010b5d8..., 9145 prediction rows and 1829 failure rows.
- Objective 1 content SHA-256 abf6f758faf7; label rule DESIGN_8_2_v1 APPROVED; geometry PROVISIONAL_RELATIVE, RELATIVE_TO_COLLAR; datum VERIFIED.
- Common held-out cohort: 1829 intervals in 71 holes and 5 drill lines; positive prevalence 0.287 (525 positives).

## 3. Evaluation plan

- Primary endpoint: **BRIER**, INTERVAL-weighted; secondary weighting EQUAL_HOLE.
- Unit: logged interval; uncertainty resampled by hole (primary) and line (sensitivity).
- Cohort: intersection of feasible-model predictions on the held-out test folds.
- Bootstrap: HOLE_CLUSTER primary; LINE_CLUSTER sensitivity; 2000 replicates per design.
- Calibration policy: O3 calibration only; O4 fits diagnostics and never recalibrates.
- Plan SHA-256: 84af02fe9334621cd310544e948effc0098801f9b3583b425242d7779c1d3069.

## 4. Coverage

| model | role | predicted / expected | failed | coverage | status |
|---|---|---|---|---|---|
| BASE_LOGISTIC | BASELINE | 1829 / 1829 | 0 | 1.000 | FULL |
| BASE_PREVALENCE | BASELINE | 1829 / 1829 | 0 | 1.000 | FULL |
| M2_HGB | M2 | 1829 / 1829 | 0 | 1.000 | FULL |
| M2_RF | M2 | 1829 / 1829 | 0 | 1.000 | FULL |
| M3_HYBRID | M3 | 1829 / 1829 | 0 | 1.000 | FALLBACK_IDENTICAL |
| M1_IK | M1 | 0 / 1829 | 1829 | 0.000 | NONE |

A model's failures are part of its applicability; they are never silently removed. M1 produced no prediction in any fold; M3 is the recorded ML-only fallback and is identical to M2_RF in every fold.

## 5. Primary probability results (pooled, interval-weighted)

| model | Brier | Brier (equal-hole) | log loss | ROC-AUC | PR-AUC | ECE | slope | intercept |
|---|---|---|---|---|---|---|---|---|
| BASE_LOGISTIC | 0.1658 | 0.1515 | 0.5074 | 0.7562 | 0.6153 | 0.0596 | 0.887 | 0.060 |
| BASE_PREVALENCE | 0.2211 | 0.1996 | 0.6404 | 0.2878 | 0.2248 | 0.1649 | -3.567 | -4.320 |
| M2_HGB | 0.1715 | 0.1564 | 0.5252 | 0.7513 | 0.5768 | 0.0508 | 1.077 | 0.223 |
| M2_RF | 0.1655 | 0.1510 | 0.5016 | 0.7816 | 0.5739 | 0.0602 | 1.369 | 0.263 |
| M3_HYBRID | 0.1655 | 0.1510 | 0.5016 | 0.7816 | 0.5739 | 0.0602 | 1.369 | 0.263 |
| M1_IK | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

Lower Brier and log loss are better; higher AUC and PR-AUC are better. The calibration slope and intercept are diagnostic fits on the held-out predictions and are not applied. An undefined metric is shown as n/a with its status stored in O4-T02. M1 has no prediction.

The metric ranking is not unanimous: random forest has the lowest Brier and highest ROC-AUC, while logistic regression has the highest PR-AUC. The differences are small, and the primary Brier contrast between them is inconclusive at this support. The decision therefore reports a point-estimate selection with an explicit caveat rather than a claim of a credible improvement.

## 6. Paired comparisons and uncertainty

| pair | delta Brier (a - b) | 95% hole CI | 95% line CI | folds a better | status |
|---|---|---|---|---|---|
| LOG_vs_HGB | -0.005663 | [-0.019540, 0.007475] | [-0.026264, 0.009210] | 4 / 5 | DEFINED |
| LOG_vs_RF | 0.000302 | [-0.011983, 0.013688] | [-0.013111, 0.010218] | 2 / 5 | DEFINED |
| M3_vs_M2_HGB | -0.005965 | [-0.017428, 0.005874] | [-0.018511, -0.000161] | 4 / 5 | DEFINED |
| M3_vs_M2_RF | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0 / 5 | DEFINED |
| PREV_vs_HGB | 0.049645 | [0.027464, 0.073074] | [0.005106, 0.093340] | 2 / 5 | DEFINED |
| PREV_vs_LOG | 0.055308 | [0.026319, 0.085153] | [0.005219, 0.120267] | 1 / 5 | DEFINED |
| PREV_vs_RF | 0.055610 | [0.031441, 0.081147] | [0.013305, 0.106003] | 1 / 5 | DEFINED |
| RF_vs_HGB | -0.005965 | [-0.017428, 0.005874] | [-0.018511, -0.000161] | 4 / 5 | DEFINED |

Negative delta means model a has the lower Brier. The hole-cluster interval is the primary uncertainty statement; the five-line interval is a sensitivity analysis and is too coarse to establish significance on its own. An interval that includes zero is not evidence of an improvement. No interval-level i.i.d. bootstrap is used.

## 7. Decision

| rank | model | role | status | selection basis | delta Brier | 95% CI | folds better | calibration | discrimination | coverage |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | M2_RF | SELECTED | INCONCLUSIVE | POINT_ESTIMATE_WITH_CAVEAT | -0.000302 | [-0.013688, 0.011983] | 3 | ACCEPTABLE | NOT_WORSE | 1.000 |
| 2 | BASE_LOGISTIC | COMPARATOR | INCONCLUSIVE | NOT_SELECTED | 0.000302 | [-0.011983, 0.013688] |  | ACCEPTABLE | WORSE | 1.000 |
| 3 | M2_HGB | REJECTED | INCONCLUSIVE | NOT_SELECTED | 0.005965 | [-0.005874, 0.017428] |  | ACCEPTABLE | WORSE | 1.000 |
| 4 | BASE_PREVALENCE | REJECTED | NO_IMPROVEMENT | NOT_SELECTED | 0.055610 | [0.031441, 0.081147] |  | NOT_ACCEPTABLE | WORSE | 1.000 |
|  | M1_IK | NOT_COMPARABLE | NOT_COMPARABLE | NOT_RANKED | n/a | [n/a, n/a] |  | UNDEFINED | UNDEFINED | 0.000 |
|  | M3_HYBRID | NOT_COMPARABLE | NOT_COMPARABLE | NOT_RANKED | n/a | [n/a, n/a] |  | ACCEPTABLE | IDENTICAL_TO_M2_RF | 1.000 |

Selected model: **M2_RF**. Its improvement over the next-best model (BASE_LOGISTIC) is **INCONCLUSIVE**: delta Brier -0.000302, 95% hole-cluster interval [-0.013688, 0.011983], and the selected model is better in 3 of five lines. The selection is on the point estimate with an explicit caveat; no credible improvement over the comparator is claimed. The M1 contrast is not estimable (0 coverage). The M3 hybrid is the fallback identical to M2_RF and is not a separate candidate.

## 8. Gates

| gate | name | status | detail |
|---|---|---|---|
| G01 | Objective 3 snapshot receipt | PASS | recomputed snapshot 41f89be1d010b5d8 vs receipt 41f89be1d010b5d8; O3 receipt 1 |
| G02 | Frozen split plan | PASS | O3-SPLIT-LODO-1 hash e1193a349fcd3426 |
| G03 | Target, label and geometry reference | PASS | rule DESIGN_8_2_v1; geometry GEOM-10-1 PROVISIONAL_RELATIVE |
| G04 | Prediction snapshot integrity | PASS | 0 out-of-bounds probabilities; 0 duplicate model/observation pairs |
| G05 | Common cohort identical across models | PASS | 1829 common observations; 0 missing model IDs |
| G06 | M1 coverage reported and not ranked | PASS | M1 predicted 0, failed 1829; decision NOT_COMPARABLE |
| G07 | M3 fallback identity and not ranked | PASS | fallback M2_RF; 0 predictions differ from M2_RF; decision NOT_COMPARABLE |
| G08 | Thresholds frozen from O3 | PASS | 0 snapshot thresholds differ from the O3 training-only thresholds |
| G09 | No model refit in O4 | PASS | O4 contains no training or model-artifact table |
| G10 | Evaluation plan declared | PASS | primary BRIER / INTERVAL |
| G11 | Cohort and weights declared | PASS | 0 non-positive weights; 1829 common observations |
| G12 | Bootstrap uses spatial units | PASS | designs: O4-BOOT-HOLE=HOLE_CLUSTER, O4-BOOT-LINE=LINE_CLUSTER |
| G13 | Metric numerical cross-check | PASS | Brier vector vs independent loop |
| G14 | Calibration is diagnostic only | PASS | 6 diagnostic rows; no recalibrated prediction column |
| G15 | Undefined metrics are not coerced | PASS | 0 undefined metrics carry a value |
| G16 | Decision rule followed | PASS | selected M2_RF; lowest Brier M2_RF |
| G17 | Locked handoff receipt | PASS | selected M2_RF; receipt hash present |
| G18 | Figure and table query provenance | PASS | 0 figure and 0 table entries are unregistered or changed |
| G19 | Export hashes | PASS | 0 manifest entries are missing or differ from the file |
| G20 | Relative geometry only | PASS | PROVISIONAL_RELATIVE; RELATIVE_TO_COLLAR |
| G21 | No absolute-elevation product | PASS | absolute columns: none |
| G22 | No grade, tonnage or resource product | PASS | grade-like columns: none |
| G23 | No synthetic data | PASS | 0 receipts reference a non-Objective-3 source |
| G24 | Coverage reported for every candidate | PASS | 6 coverage rows |
| G25 | Cluster uncertainty for decisions | PASS | selected decision carries a hole-cluster interval |
| G26 | External validity not claimed | PASS | handoff caveat states internal held-out validation |
| G27 | Objective 3 prediction snapshot | PASS | snapshot 41f89be1d010b5d8 |

Exit gates: G01, G02, G03, G04, G05, G06, G07, G08, G10, G11, G12, G13, G15, G16, G17, G18, G19, G20, G21, G24, G25. All exit gates PASS.

## 9. Audit

- PASS O3_SNAPSHOT_HASH_RECORDED: snapshot 41f89be1d010b5d8
- PASS COMMON_COHORT_IDENTICAL_ACROSS_FEASIBLE_MODELS: 1829 common observations; 0 missing model IDs
- PASS M1_COVERAGE_REPORTED: M1 predicted 0; failed 1829
- PASS M3_FALLBACK_IDENTITY_RECORDED: M3 fallback identical to M2_RF
- PASS PROBABILITY_BOUNDS: 0 out-of-bounds probabilities
- PASS THRESHOLDS_FROZEN_FROM_O3: 9145 snapshot rows carry the O3 threshold
- PASS BOOTSTRAP_USES_SPATIAL_UNITS: hole-cluster design present
- PASS BRIER_NUMERICAL_CROSS_CHECK: vector 0.165514789602; loop 0.165514789602
- PASS NO_MODEL_REFIT: Objective 4 contains no training or model-artifact table
- PASS CALIBRATION_DIAGNOSTIC_ONLY: calibration intercept and slope are diagnostics; no recalibrated probability column exists

## 10. Tables

- O4-T01: GENERATED, 6 rows; Main evaluation summary.
- O4-T02: GENERATED, 30 rows; Fold-by-fold scores.
- O4-T03: GENERATED, 31 rows; Confusion matrices and threshold provenance.
- O4-T04: GENERATED, 16 rows; Paired difference uncertainty and weighting sensitivity.
- O4-T05: GENERATED, 6 rows; Final model-selection decision and handoff.

## 11. Figures

- O4-F01 (GENERATED): Spatial holdout fold map and coverage. rendered from the registered queries
- O4-F02 (GENERATED): Brier score by model and held-out line. rendered from the registered queries
- O4-F03 (GENERATED): ROC and PR curves. rendered from the registered queries
- O4-F04 (GENERATED): Reliability diagrams. rendered from the registered queries
- O4-F05 (GENERATED): Paired hybrid differences by line. rendered from the registered queries
- O4-F06 (GENERATED): Selected-model residuals on withheld observations. rendered from the registered queries
- O4-F07 (GENERATED): Coverage and missing predictions. rendered from the registered queries

## 12. Tests

```text
......................                                                   [100%]
22 passed in 1.28s
```

## 13. Limitations

- Internal spatially held-out validation on five drill lines; not an external prospective campaign.
- The effective independent spatial units are five lines and 71 holes, not 1,829 intervals. The primary uncertainty resamples holes; the line-level interval is a coarse sensitivity.
- Only easting, northing and relative Z are predictors. The models are spatial-trend models, not geological-covariate models.
- Relative Z only; no collar elevation or DEM. No absolute-elevation product.
- M1 is not estimable and M3 is the ML-only fallback; the hybrid claim is not supported.
- The random forest is selected on the point estimate but its improvement over logistic regression is inconclusive at this support.
- No grade, tonnage or resource is estimated.
- The Objective 3 working tree is not committed; the hashes in the receipt identify the exact run.

## 14. Commands and environment

```bash
./.venv/Scripts/python.exe -I -m kambale.objective_4 all
./.venv/Scripts/python.exe -I -m pytest -o addopts= -q tests/objective_4 > reports/objective_4/PYTEST_OUTPUT.txt
./.venv/Scripts/python.exe -I -m kambale.objective_4 report
./.venv/Scripts/python.exe -I -m kambale.objective_4 verify
```

`all` runs import, evaluate, verify, figures, tables, verify, report and verify.

Python 3.14.6 on Windows-11-10.0.26200-SP0; numpy 2.4.6; scipy 1.18.0; scikit-learn 1.9.1; matplotlib 3.11.1; PyYAML 6.0.3; pytest 9.1.1.

## 15. Database row counts and receipts

| table | rows |
|---|---|
| bootstrap_replicates | 32000 |
| calibration_bins | 32 |
| calibration_diagnostics | 6 |
| candidate_registry | 6 |
| class_confusion_matrices | 31 |
| comparison_decisions | 6 |
| evaluation_audit_log | 10 |
| evaluation_plan | 1 |
| evaluation_population | 1829 |
| export_manifests | 41 |
| figure_registry | 7 |
| figure_sql_registry | 18 |
| fold_metrics | 300 |
| gate_results | 162 |
| locked_handoff_receipts | 1 |
| metric_curve_points | 6332 |
| metric_definitions | 13 |
| paired_differences | 176 |
| pooled_metrics | 60 |
| prediction_coverage | 6 |
| prediction_snapshot | 9145 |
| resampling_designs | 2 |
| schema_version | 1 |
| source_receipts | 1 |
| spatial_error_summaries | 239 |
| stage_runs | 8 |
| table_registry | 5 |
| table_sql_registry | 5 |

Counts are taken when this report is written. The post-report VERIFY run adds one `stage_runs` row and one gate set; it is the authoritative final check.

O3 snapshot SHA-256: 41f89be1d010b5d842f2f2c15bc7aa2b13b1b5a6e65c321ce140c8e3d821141e. O3 split hash: e1193a349fcd34264519672cb3de9854b19e984a21b21d784b011220e9888c1f. O1 content SHA-256: abf6f758faf75c82a250931ab034b145574a10f98362424e93dd6cc6483dea22.


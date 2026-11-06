# Objective 3 run report: indicator geostatistics, machine learning and hybrid occurrence models

Configuration O3-CFG-2026.11.06-2 (SHA-256 47569e360e55), code 3.0.0, schema O3-SCHEMA-2026.11.06-2, commit 7d83644. Import run 1, split run 2, training run 4, gate run 7. Report written 2026-11-06T04:41:05Z.

## 1. Status

Every required exit gate is PASS.
Objective 2 continuity handoff: **NOT_IDENTIFIABLE**, candidate family **NONE**. Because no continuity model is identified, every M1 and M3 covariance below is chosen by inner cross-validation from a predeclared grid, and a pure-nugget choice is reported as such.

## 2. Inputs and receipt

- Objective 1 snapshot: C:/Users/ThinkPad P1 G4/Documents/Joseph_Thesis/database/kambale_thesis.sqlite (read-only; dataset version 10, ETL 1.5.0, content SHA-256 abf6f758faf7).
- Objective 2 receipt 1 at C:/Users/ThinkPad P1 G4/Documents/Joseph_Thesis/database/kambale_obj2_spatial.sqlite, content SHA-256 abf6f758faf7, handoff 1 (NOT_IDENTIFIABLE).
- Intervals imported: 1910; holes 71; approved drill lines 5.
- Label rule DESIGN_8_2_v1 APPROVED; binary target 1829 (525 POSITIVE, 1304 NEGATIVE); excluded 81 AMBIGUOUS and 0 UNRESOLVED.
- Geometry PROVISIONAL_RELATIVE, vertical basis RELATIVE_TO_COLLAR; z_absolute_used=0. Coordinates EPSG:32630, datum VERIFIED.

## 3. Configuration

Predeclared version O3-CFG-2026.11.06-2 (supersedes O3-CFG-2026.11.05-1). Predictor sets: TREND = easting_m, northing_m, z_relative_m; TREND_WF = easting_m, northing_m, z_relative_m, depth_below_weathering_front_m. The depth below the weathering front is a fold-safe inverse-distance surface built from training holes only (see section 5).
Two validation tiers are run: O3-SPLIT-LODO-1 (LEAVE_ONE_DRILL_LINE_OUT), O3-SPLIT-HOLE-IL-2 (INTERLEAVED_HOLES_WITHIN_LINE). The primary tier is O3-SPLIT-LODO-1; the second tier is an interpolation check at one hole spacing. Both are reported; neither is pooled with the other.
Inner tuning is GROUP_K_FOLD_BY_HOLE with 4 folds, selecting the lowest mean log loss. The decision threshold is the inner-CV Youden-J maximum; ties go to the threshold closest to 0.5. M2_SEL and M2_WF_SEL copy the inner-selected member of their pair. M1 and M3 covariances come from the grid of range [25.0, 50.0, 100.0, 200.0, 400.0] m by nugget fraction [0.25, 0.5, 0.75], plus PURE_NUGGET.
Random forest and sklearn.ensemble.HistGradientBoostingClassifier are the two M2 estimators; XGBoost is not installed in the verified environment. Logistic regression and training prevalence are the baselines.

## 4. Frozen spatial splits

### 4.1 O3-SPLIT-LODO-1 (LEAVE_ONE_DRILL_LINE_OUT, primary)

Plan hash e1193a349fcd34264519672cb3de9854b19e984a21b21d784b011220e9888c1f.

| fold | test lines | test holes | test intervals | test positive | train intervals | min collar distance (m) | audit |
|---|---|---|---|---|---|---|---|
| 1 | NOM_N1111930 | 3 | 84 | 29 | 1745 | 556.6 | PASS |
| 2 | NOM_N1112140 | 13 | 429 | 217 | 1400 | 453.6 | PASS |
| 3 | NOM_N1112500 | 21 | 528 | 130 | 1301 | 488.4 | PASS |
| 4 | NOM_N1112600 | 15 | 401 | 133 | 1428 | 453.6 | PASS |
| 5 | NOM_N1113000 | 19 | 387 | 16 | 1442 | 488.4 | PASS |

### 4.2 O3-SPLIT-HOLE-IL-2 (INTERLEAVED_HOLES_WITHIN_LINE, second tier)

Plan hash df0364073d40ae93e40195e1429d6a1ab23d32ebdeac7dfcf85e7a68f17577c1.

| fold | test lines | test holes | test intervals | test positive | train intervals | min collar distance (m) | audit |
|---|---|---|---|---|---|---|---|
| 1 | NOM_N1112140,NOM_N1112500,NOM_N1111930,NOM_N1113000,NOM_N1112600 | 16 | 383 | 83 | 1446 | 17.1 | PASS |
| 2 | NOM_N1112140,NOM_N1112500,NOM_N1111930,NOM_N1113000,NOM_N1112600 | 15 | 455 | 199 | 1374 | 15.2 | PASS |
| 3 | NOM_N1112140,NOM_N1112500,NOM_N1111930,NOM_N1113000,NOM_N1112600 | 15 | 383 | 119 | 1446 | 15.2 | PASS |
| 4 | NOM_N1112140,NOM_N1112500,NOM_N1113000,NOM_N1112600 | 13 | 303 | 54 | 1526 | 16.0 | PASS |
| 5 | NOM_N1112140,NOM_N1112500,NOM_N1113000,NOM_N1112600 | 12 | 305 | 70 | 1524 | 16.3 | PASS |

## 5. Models and training-only diagnostics

### 5.1 O3-SPLIT-LODO-1

Selected trend candidates by inner-CV log loss (the composites are the selection records):

| fold | M2_SEL (from plain pair) | inner CV | M2_WF_SEL (from weathering-front pair) | inner CV |
|---|---|---|---|---|
| 1 | M2_RF (COMPLETED) | 0.4578 | M2_RF_WF (COMPLETED) | 0.4491 |
| 2 | M2_RF (COMPLETED) | 0.4640 | M2_RF_WF (COMPLETED) | 0.4633 |
| 3 | M2_RF (COMPLETED) | 0.4827 | M2_RF_WF (COMPLETED) | 0.4966 |
| 4 | M2_RF (COMPLETED) | 0.4180 | M2_RF_WF (COMPLETED) | 0.4335 |
| 5 | M2_RF (COMPLETED) | 0.5388 | M2_RF_WF (COMPLETED) | 0.5309 |

M1 indicator kriging: covariance chosen by inner CV per fold.

| fold | status | chosen covariance | inner-CV log loss | trials recorded |
|---|---|---|---|---|
| 1 | COMPLETED | exponential range 400 m, nugget fraction 0.75 | 0.5071 | 16 |
| 2 | COMPLETED | exponential range 100 m, nugget fraction 0.75 | 0.4962 | 16 |
| 3 | COMPLETED | exponential range 400 m, nugget fraction 0.75 | 0.5835 | 16 |
| 4 | COMPLETED | exponential range 400 m, nugget fraction 0.75 | 0.4481 | 16 |
| 5 | COMPLETED | exponential range 400 m, nugget fraction 0.75 | 0.5764 | 16 |

M3 hybrid on the calibrated M2_WF_SEL trend: residual covariance and status per fold.

| fold | trend | status | residual covariance | fallback | trials recorded |
|---|---|---|---|---|---|
| 1 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |
| 2 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |
| 3 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |
| 4 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |
| 5 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |

M1 selected a spatial covariance in every fold.
M3 is recorded as FALLBACK_ML_ONLY in folds [1, 2, 3, 4, 5]; there it is identical to M2_WF_SEL and is not a hybrid result.

Out-of-fold prediction counts for this tier (no outer performance is computed here; Objective 4 evaluates):

| family | predictions | clipped (calibrated) | failures |
|---|---|---|---|
| BASE_LOGISTIC | 1829 | 0 | 0 |
| BASE_LOGISTIC_WF | 1829 | 0 | 0 |
| BASE_PREVALENCE | 1829 | 0 | 0 |
| M1_IK | 1829 | 0 | 0 |
| M2_HGB | 1829 | 0 | 0 |
| M2_HGB_WF | 1829 | 0 | 0 |
| M2_RF | 1829 | 0 | 0 |
| M2_RF_WF | 1829 | 0 | 0 |
| M2_SEL | 1829 | 0 | 0 |
| M2_WF_SEL | 1829 | 0 | 0 |
| M3_HYBRID | 1829 | 0 | 0 |

### 5.2 O3-SPLIT-HOLE-IL-2

Selected trend candidates by inner-CV log loss (the composites are the selection records):

| fold | M2_SEL (from plain pair) | inner CV | M2_WF_SEL (from weathering-front pair) | inner CV |
|---|---|---|---|---|
| 1 | M2_RF (COMPLETED) | 0.4868 | M2_RF_WF (COMPLETED) | 0.4822 |
| 2 | M2_RF (COMPLETED) | 0.4420 | M2_RF_WF (COMPLETED) | 0.4595 |
| 3 | M2_RF (COMPLETED) | 0.4572 | M2_RF_WF (COMPLETED) | 0.4627 |
| 4 | M2_RF (COMPLETED) | 0.4759 | M2_RF_WF (COMPLETED) | 0.4750 |
| 5 | M2_RF (COMPLETED) | 0.4603 | M2_RF_WF (COMPLETED) | 0.4619 |

M1 indicator kriging: covariance chosen by inner CV per fold.

| fold | status | chosen covariance | inner-CV log loss | trials recorded |
|---|---|---|---|---|
| 1 | COMPLETED | exponential range 400 m, nugget fraction 0.75 | 0.5624 | 16 |
| 2 | COMPLETED | exponential range 200 m, nugget fraction 0.75 | 0.5047 | 16 |
| 3 | COMPLETED | exponential range 400 m, nugget fraction 0.75 | 0.5043 | 16 |
| 4 | COMPLETED | exponential range 400 m, nugget fraction 0.75 | 0.5305 | 16 |
| 5 | COMPLETED | exponential range 400 m, nugget fraction 0.75 | 0.5245 | 16 |

M3 hybrid on the calibrated M2_WF_SEL trend: residual covariance and status per fold.

| fold | trend | status | residual covariance | fallback | trials recorded |
|---|---|---|---|---|---|
| 1 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |
| 2 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |
| 3 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |
| 4 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |
| 5 | M2_RF_WF | FALLBACK | PURE_NUGGET | FALLBACK_ML_ONLY | 16 |

M1 selected a spatial covariance in every fold.
M3 is recorded as FALLBACK_ML_ONLY in folds [1, 2, 3, 4, 5]; there it is identical to M2_WF_SEL and is not a hybrid result.

Out-of-fold prediction counts for this tier (no outer performance is computed here; Objective 4 evaluates):

| family | predictions | clipped (calibrated) | failures |
|---|---|---|---|
| BASE_LOGISTIC | 1829 | 0 | 0 |
| BASE_LOGISTIC_WF | 1829 | 0 | 0 |
| BASE_PREVALENCE | 1829 | 0 | 0 |
| M1_IK | 1829 | 0 | 0 |
| M2_HGB | 1829 | 0 | 0 |
| M2_HGB_WF | 1829 | 0 | 0 |
| M2_RF | 1829 | 0 | 0 |
| M2_RF_WF | 1829 | 0 | 0 |
| M2_SEL | 1829 | 0 | 0 |
| M2_WF_SEL | 1829 | 0 | 0 |
| M3_HYBRID | 1829 | 0 | 0 |

Inner scores are whole-hole cross-validation log losses on the outer training folds. They are selection diagnostics, not held-out performance. 630 hyperparameter trials were recorded across both tiers.

## 6. Gate results

| gate | name | status | detail |
|---|---|---|---|
| G01 | Receipt match | PASS | recomputed content abf6f758faf7 vs receipt abf6f758faf7; rows 1910 vs receipt 1910; version 55dead7da64c |
| G02 | Approved label rule | PASS | DESIGN_8_2_v1 APPROVED; definition hash matches: True |
| G03 | Relative geometry only | PASS | z_absolute_m non-null upstream rows = 0; vertical basis RELATIVE_TO_COLLAR |
| G04 | Coordinate pair, datum and lines | PASS | pair APPROVED; datum VERIFIED; 5 of 5 lines approved |
| G05 | Split integrity | PASS | membership rows: O3-SPLIT-HOLE-IL-2 9145 of 9145; O3-SPLIT-LODO-1 9145 of 9145; 0 duplicates; 0 train/test overlaps |
| G06 | Fold class and spatial support | PASS | O3-SPLIT-HOLE-IL-2 PASS 5, O3-SPLIT-LODO-1 PASS 5 |
| G07 | Predictor leakage | PASS | 0 deployed predictors are not SAFE/available; 0 forbidden features are deployed |
| G08 | Target consistency | PASS | 1 target registries; registered binary 1829 vs observations 1829 |
| G09 | OOF completeness | PASS | 0 test observations lack a prediction or a failure record across 110 runs in 2 split plans |
| G10 | Probability bounds and clipping | PASS | 0 out-of-bounds probabilities; O3-SPLIT-HOLE-IL-2 BASE_LOGISTIC clipped 0.000, O3-SPLIT-HOLE-IL-2 BASE_LOGISTIC_WF clipped 0.000, O3-SPLIT-HOLE-IL-2 BASE_PREVALENCE clipped 0.000, O3-SPLIT-HOLE-IL-2 M1_IK clipped 0.000, O3-SPLIT-HOLE-IL-2 M2_HGB clipped 0.000, O3-SPLIT-HOLE-IL-2 M2_HGB_WF clipped 0.000, O3-SPLIT-HOLE-IL-2 M2_RF clipped 0.000, O3-SPLIT-HOLE-IL-2 M2_RF_WF clipped 0.000, O3-SPLIT-HOLE-IL-2 M2_SEL clipped 0.000, O3-SPLIT-HOLE-IL-2 M2_WF_SEL clipped 0.000, O3-SPLIT-HOLE-IL-2 M3_HYBRID clipped 0.000, O3-SPLIT-LODO-1 BASE_LOGISTIC clipped 0.000, O3-SPLIT-LODO-1 BASE_LOGISTIC_WF clipped 0.000, O3-SPLIT-LODO-1 BASE_PREVALENCE clipped 0.000, O3-SPLIT-LODO-1 M1_IK clipped 0.000, O3-SPLIT-LODO-1 M2_HGB clipped 0.000, O3-SPLIT-LODO-1 M2_HGB_WF clipped 0.000, O3-SPLIT-LODO-1 M2_RF clipped 0.000, O3-SPLIT-LODO-1 M2_RF_WF clipped 0.000, O3-SPLIT-LODO-1 M2_SEL clipped 0.000, O3-SPLIT-LODO-1 M2_WF_SEL clipped 0.000, O3-SPLIT-LODO-1 M3_HYBRID clipped 0.000 |
| G11 | Training-only indicator covariance | PASS | 0 covariance rows reference another fold or family; 0 test rows are in a training manifest |
| G12 | Training-only residual covariance | PASS | 0 residual covariance rows reference another fold or family |
| G13 | Calibration uses inner data only | PASS | 0 calibration rows exceed the training fold or belong to an uncalibrated family |
| G14 | No full-data parameters for test folds | PASS | 0 final full-data refits are marked RUN before Objective 4 selection |
| G15 | Model artifact hashes | PASS | 0 artifact files are missing or differ from their hash |
| G16 | Figure and table query provenance | PASS | 0 figure and 0 table registry entries are unregistered or changed |
| G17 | Export hashes | PASS | 0 manifest entries are missing or differ from the file on disk |
| G18 | Tuning uses inner folds only | PASS | 0 completed candidates have no inner-CV score |
| G19 | M1 status honesty | PASS | 10 M1 runs; 0 runs lack the full trial grid or a chosen covariance; 0 pure-nugget runs; 0 pure-nugget predictions differ from the training prevalence by more than 1e-12 |
| G20 | M3 fallback is labelled | PASS | 10 hybrid runs; 0 carry an inconsistent label or differ from M2_WF_SEL (fallback predictions 3658 of 3658 equal, tolerance 1e-12) |
| G21 | Primary split plan is line-blocked | PASS | 1 primary plan(s): O3-SPLIT-LODO-1 LEAVE_ONE_DRILL_LINE_OUT; configured primary O3-SPLIT-LODO-1; plans in database 2 |
| G22 | Geometry and label status on predictions | PASS | 0 predictions carry a different geometry or label status |
| G23 | No absolute-elevation product | PASS | absolute-elevation columns: none |
| G24 | No synthetic data in exports | PASS | 0 receipts reference a non-Kambale source |
| G25 | Objective 2 handoff recorded | PASS | handoff NOT_IDENTIFIABLE; candidate family NONE |
| G26 | Predictions are held-out members | PASS | 0 predictions are not test members of their fold |
| G27 | Leakage audit log | PASS | 14 audit rows; 0 failed |
| G28 | Tier-2 plan interleaved | PASS | 0 along-line neighbour violations across 71 test holes in O3-SPLIT-HOLE-IL-2 |

Exit gates: G01, G02, G03, G05, G08, G09, G10, G11, G12, G13, G15, G16, G17, G19, G20, G21, G22, G25, G26, G28. All exit gates PASS.

## 7. Tables

- O3-T01: GENERATED, 61 rows; Model definitions, predictors, target version and sample support.
- O3-T02: GENERATED, 200 rows; Split-plan, fold and family hyperparameters, covariance selection and calibration diagnostics.
- O3-T03: GENERATED, 432 rows; Out-of-fold completeness and leakage audit, both split plans.
- O3-T04: GENERATED, 46 rows; Model artifact and reproducibility registry.

The rendered tables are in tables/objective_3 as CSV, Markdown and LaTeX.

## 8. Figures

Figures F01 to F05 show the primary tier O3-SPLIT-LODO-1. F06 shows the covariance selection of both tiers' M1 and M3 fits per fold.

- O3-F01 (GENERATED): Outer-fold spatial map and class support. rendered from the registered queries.
- O3-F02 (GENERATED): Predictor availability and observation support. rendered from the registered queries.
- O3-F03 (GENERATED): M1 indicator-kriging out-of-fold probabilities. rendered from the registered queries.
- O3-F04 (GENERATED): M2 out-of-fold probability sections. rendered from the registered queries.
- O3-F05 (GENERATED): M3 hybrid or fallback probability section. rendered from the registered queries.
- O3-F06 (GENERATED): Inner-CV covariance selection for M1 and M3. rendered from the registered queries.


## 9. Tests

```text
....................................................                     [100%]
52 passed in 1.73s
```

## 10. Deviations, warnings and limitations

- The fold-safe weathering-front predictor is an inverse-distance surface of the front heights of the training holes. It is a modelled, not an observed, front at a grid cell; it is not a geological covariate measured at the prediction location.
- The front is defined only where the log records a mw or sw interval; every hole in this snapshot carries one.
- The covariance grid is predeclared; the chosen covariance is per fold and can differ between folds.
- XGBoost is not installed; scikit-learn's histogram gradient boosting is the declared fallback.
- The final full-data refit is PENDING_O4. Objective 3 does not fit on all observations and does not call that fit spatially validated.
- The code commit is the last committed revision; the Objective 3 working tree is deliberately not committed. The configuration hash, SQL hashes and artifact hashes identify the exact run.

## 11. Objective 4 handoff contract

- Split plan `O3-SPLIT-LODO-1` (LEAVE_ONE_DRILL_LINE_OUT, primary=1), hash `e1193a349fcd34264519672cb3de9854b19e984a21b21d784b011220e9888c1f`, 5 folds.
- Split plan `O3-SPLIT-HOLE-IL-2` (INTERLEAVED_HOLES_WITHIN_LINE, primary=0), hash `df0364073d40ae93e40195e1429d6a1ab23d32ebdeac7dfcf85e7a68f17577c1`, 5 folds.
- Target: `TARGET-DESIGN_8_2_v1-1`, rule DESIGN_8_2_v1 APPROVED, 1829 binary intervals.
- Geometry: `GEOM-10-1`, PROVISIONAL_RELATIVE, vertical basis RELATIVE_TO_COLLAR, z_absolute_used=0.
- Predictions: `predictions_oof`, one row per (training run, held-out interval), with `p_raw`, `p_calibrated`, clipping flags, training-selected threshold and predicted class. The composites M2_SEL and M2_WF_SEL and the hybrid M3_HYBRID are written as their own runs.
- Failures: `prediction_failures`, one row per (plan, fold, held-out interval, family) that could not be predicted.
- Fits and diagnostics: `training_runs`, `hyperparameter_trials` (every covariance grid point for M1 and M3), `variogram_training_fits` and `hybrid_residual_variogram` (the chosen covariance per fold), `calibration_fits`, `residual_diagnostics`.
- Artifacts: `model_artifacts`, parameter and provenance records with SHA-256.
- Selection policy: inner whole-hole CV log loss; no outer test result was used to select a model, a covariance or a threshold. O4 may evaluate and rank, but must not refit models or change the splits.
- Final refit: `final_refits` row PENDING_O4. After O4 locks selection, Objective 3 must refit the selected pipeline on all eligible approved observations and hash the artifact; that fit is not spatially validated.

## 12. Commands and environment

```bash
./.venv/Scripts/python.exe -I -m kambale.objective_3 all
./.venv/Scripts/python.exe -I -m pytest -o addopts= -q tests/objective_3 > reports/objective_3/PYTEST_OUTPUT.txt
./.venv/Scripts/python.exe -I -m kambale.objective_3 report
./.venv/Scripts/python.exe -I -m kambale.objective_3 verify
```

`all` runs import, splits, train, verify, figures, tables, verify, report and verify. A STOP at a verify step ends the run before the next write.

Python 3.14.6 on Windows-11-10.0.26200-SP0; numpy 2.4.6; scipy 1.18.0; scikit-learn 1.9.1; matplotlib 3.11.1; PyYAML 6.0.3; pytest 9.1.1.

## 13. Database row counts and receipts

| table | rows |
|---|---|
| analysis_observations | 1910 |
| calibration_fits | 70 |
| export_manifests | 125 |
| feature_registry | 26 |
| figure_registry | 6 |
| figure_sql_registry | 17 |
| final_refits | 1 |
| gate_results | 84 |
| geometry_versions | 1 |
| hybrid_residual_variogram | 10 |
| hyperparameter_trials | 630 |
| label_versions | 1 |
| leakage_audit_log | 14 |
| model_artifacts | 90 |
| model_families | 11 |
| prediction_failures | 0 |
| predictions_oof | 40238 |
| residual_diagnostics | 18290 |
| schema_version | 1 |
| source_receipts | 1 |
| spatial_split_plans | 2 |
| split_audit | 10 |
| split_membership | 18290 |
| stage_runs | 7 |
| table_registry | 4 |
| table_sql_registry | 4 |
| target_registries | 1 |
| training_lag_bins | 0 |
| training_runs | 110 |
| training_sample_manifest | 160952 |
| variogram_training_fits | 10 |

Counts are taken when this report is written. The post-report VERIFY run adds one `stage_runs` row and one gate set; that run is the authoritative final check and its gate rows are in the database.

O1 receipt content SHA-256: abf6f758faf75c82a250931ab034b145574a10f98362424e93dd6cc6483dea22. O2 receipt 1 content SHA-256: abf6f758faf75c82a250931ab034b145574a10f98362424e93dd6cc6483dea22. Ordered identifier digest: a94753f238d017f378b4b81fa61fcb061b63c62a687a68bafcdbbaf480027f55. Selection query SHA-256: 677203494777ff7efc26c6e5286142522049c7112f95109ed366a2da3481a767.


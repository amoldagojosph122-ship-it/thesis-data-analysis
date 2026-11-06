# Objective 3 run report: indicator geostatistics, machine learning and hybrid occurrence models

Configuration O3-CFG-2026.11.05-1 (SHA-256 f0f2e1927db9), code 3.0.0, schema O3-SCHEMA-2026.11.05-1, commit c15b680. Import run 1, split run 2, training run 3, gate run 9. Report written 2026-11-05T18:59:57Z.

## 1. Status

Every required exit gate is PASS.
Objective 2 continuity handoff: **NOT_IDENTIFIABLE**, candidate family **NONE**. Accordingly, M1 indicator kriging is estimated only where a training-only variogram is identified and stable, and M3 is labelled an ML-only fallback where the residual covariance is unsupported. Neither is claimed as a successful spatial model.

## 2. Inputs and receipt

- Objective 1 snapshot: C:/Users/ThinkPad P1 G4/Documents/Joseph_Thesis/database/kambale_thesis.sqlite (read-only; dataset version 10, ETL 1.5.0, content SHA-256 abf6f758faf7).
- Objective 2 receipt 1 at C:/Users/ThinkPad P1 G4/Documents/Joseph_Thesis/database/kambale_obj2_spatial.sqlite, content SHA-256 abf6f758faf7, handoff 1 (NOT_IDENTIFIABLE).
- Intervals imported: 1910 (each 1 m); holes 71; approved drill lines 5.
- Label rule DESIGN_8_2_v1 APPROVED; binary target 1829 (525 POSITIVE, 1304 NEGATIVE); excluded 81 AMBIGUOUS and 0 UNRESOLVED.
- Geometry PROVISIONAL_RELATIVE, vertical basis RELATIVE_TO_COLLAR; z_absolute_used=0. Coordinates EPSG:32630, datum VERIFIED.

## 3. Configuration

Predeclared version O3-CFG-2026.11.05-1. Predictors are restricted to easting_m, northing_m, z_relative_m.
The outer split is LEAVE_ONE_DRILL_LINE_OUT with 5 folds and plan hash e1193a349fcd34264519672cb3de9854b19e984a21b21d784b011220e9888c1f. Inner tuning is GROUP_K_FOLD_BY_HOLE with 4 folds, selecting the lowest mean log loss. The decision threshold is the inner-CV Youden-J maximum; ties go to the threshold closest to 0.5.
Random forest and sklearn.ensemble.HistGradientBoostingClassifier are the two M2 candidates. XGBoost is not installed in the verified environment; the histogram gradient-boosting fallback is declared in the configuration. Logistic regression and the training prevalence are the baselines.

## 4. Frozen spatial split

| fold | test line | test intervals | test positive | train intervals | min collar distance (m) | audit |
|---|---|---|---|---|---|---|
| 1 | NOM_N1111930 | 84 | 29 | 1745 | 556.6 | PASS |
| 2 | NOM_N1112140 | 429 | 217 | 1400 | 453.6 | PASS |
| 3 | NOM_N1112500 | 528 | 130 | 1301 | 488.4 | PASS |
| 4 | NOM_N1112600 | 401 | 133 | 1428 | 453.6 | PASS |
| 5 | NOM_N1113000 | 387 | 16 | 1442 | 488.4 | PASS |

The secondary whole-hole split plan is registered and audited but does not produce the predictions handed to Objective 4. No random split is used.

## 5. Models and training-only diagnostics

### 5.1 Selected M2 trend by fold

| fold | selected candidate | inner CV log loss | threshold | training n | training positive |
|---|---|---|---|---|---|
| 1 | M2_RF | 0.4578 | 0.25 | 1745 | 496 |
| 2 | M2_RF | 0.4640 | 0.15 | 1400 | 308 |
| 3 | M2_RF | 0.4827 | 0.25 | 1301 | 395 |
| 4 | M2_RF | 0.4180 | 0.25 | 1428 | 392 |
| 5 | M2_RF | 0.5388 | 0.35 | 1442 | 509 |

The inner scores are whole-hole cross-validation log losses on the outer training fold. They are selection diagnostics, not held-out performance; Objective 4 performs the comparative evaluation. 80 hyperparameter trials were recorded.

### 5.2 M1 indicator kriging

M1 is **NOT_ESTIMABLE in every outer fold**. No training-only lateral indicator variogram was both identified and stable, so no kriging prediction was written and no parameter was invented. Failure rows record every held-out interval. The reasons by fold are:

- Fold 1: spherical: NOT_IDENTIFIABLE (range at the upper bound: not identified inside the supported lags; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- Fold 2: spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- Fold 3: spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- Fold 4: spherical: NOT_IDENTIFIABLE (range at the upper bound: not identified inside the supported lags; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- Fold 5: spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)

### 5.3 M3 hybrid

| fold | status | residual variogram | fallback |
|---|---|---|---|
| 1 | FALLBACK | exponential NOT_IDENTIFIABLE/NOT_ASSESSED; spherical NOT_IDENTIFIABLE/NOT_ASSESSED | FALLBACK_ML_ONLY |
| 2 | FALLBACK | exponential NOT_IDENTIFIABLE/NOT_ASSESSED; spherical NOT_IDENTIFIABLE/NOT_ASSESSED | FALLBACK_ML_ONLY |
| 3 | FALLBACK | exponential NOT_IDENTIFIABLE/NOT_ASSESSED; spherical NOT_IDENTIFIABLE/NOT_ASSESSED | FALLBACK_ML_ONLY |
| 4 | FALLBACK | exponential NOT_IDENTIFIABLE/NOT_ASSESSED; spherical NOT_IDENTIFIABLE/NOT_ASSESSED | FALLBACK_ML_ONLY |
| 5 | FALLBACK | exponential NOT_IDENTIFIABLE/NOT_ASSESSED; spherical NOT_IDENTIFIABLE/NOT_ASSESSED | FALLBACK_ML_ONLY |

The residual variogram is fitted on inner cross-fitted residuals of the outer training fold only. Where it was not identified and stable, M3 is recorded as `FALLBACK_ML_ONLY` and is not described as a successful hybrid. M3 never uses a test label.

### 5.4 Out-of-fold predictions

| family | predictions | failures | clipped (calibrated) | min p | max p |
|---|---|---|---|---|---|
| BASE_LOGISTIC | 1829 | 0 | 0 | 0.035 | 0.919 |
| BASE_PREVALENCE | 1829 | 0 | 0 | 0.220 | 0.353 |
| M2_HGB | 1829 | 0 | 0 | 0.020 | 0.801 |
| M2_RF | 1829 | 0 | 0 | 0.049 | 0.668 |
| M3_HYBRID | 1829 | 0 | 0 | 0.049 | 0.668 |
| M1_IK | 0 | 1829 | 0 | n/a | n/a |

A failure row is written for every held-out interval a family could not predict; it is never silently dropped. Clipping to [0,1] is counted per prediction. Probabilities are out-of-fold by construction.

## 6. Gate results

| gate | name | status | detail |
|---|---|---|---|
| G01 | Receipt match | PASS | recomputed content abf6f758faf7 vs receipt abf6f758faf7; rows 1910 vs receipt 1910; version 55dead7da64c |
| G02 | Approved label rule | PASS | DESIGN_8_2_v1 APPROVED; definition hash matches: True |
| G03 | Relative geometry only | PASS | z_absolute_m non-null upstream rows = 0; vertical basis RELATIVE_TO_COLLAR |
| G04 | Coordinate pair, datum and lines | PASS | pair APPROVED; datum VERIFIED; 5 of 5 lines approved |
| G05 | Split integrity | PASS | 9145 of 9145 expected membership rows; 0 duplicates; 0 train/test overlaps |
| G06 | Fold class and spatial support | PASS | PASS 5 for O3-SPLIT-LODO-1 |
| G07 | Predictor leakage | PASS | 0 deployed predictors are not SAFE/available; 0 forbidden features are deployed |
| G08 | Target consistency | PASS | 1 target registries; registered binary 1829 vs observations 1829 |
| G09 | OOF completeness | PASS | 0 test observations lack a prediction or a failure record across 30 runs |
| G10 | Probability bounds and clipping | PASS | 0 out-of-bounds probabilities; BASE_LOGISTIC clipped 0.000, BASE_PREVALENCE clipped 0.000, M2_HGB clipped 0.000, M2_RF clipped 0.000, M3_HYBRID clipped 0.000 |
| G11 | Training-only indicator variograms | PASS | 0 variogram rows reference another fold or family; 0 test rows are in a training manifest |
| G12 | Training-only residual variograms | PASS | 0 residual variogram rows reference another fold or family |
| G13 | Calibration uses inner data only | PASS | 0 calibration rows exceed the training fold or belong to an uncalibrated family |
| G14 | No full-data parameters for test folds | PASS | 0 final full-data refits are marked RUN before Objective 4 selection |
| G15 | Model artifact hashes | PASS | 0 artifact files are missing or differ from their hash |
| G16 | Figure and table query provenance | PASS | 0 figure and 0 table registry entries are unregistered or changed |
| G17 | Export hashes | PASS | 0 manifest entries are missing or differ from the file on disk |
| G18 | Tuning uses inner folds only | PASS | 0 completed candidates have no inner-CV score |
| G19 | M1 status honesty | PASS | 0 M1 rows claim a prediction or parameters without an identified variogram |
| G20 | M3 fallback is labelled | PASS | 0 hybrid runs carry an inconsistent fallback label |
| G21 | Primary split plan is line-blocked | PASS | 1 primary plans; O3-SPLIT-LODO-1 uses LEAVE_ONE_DRILL_LINE_OUT |
| G22 | Geometry and label status on predictions | PASS | 0 predictions carry a different geometry or label status |
| G23 | No absolute-elevation product | PASS | absolute-elevation columns: none |
| G24 | No synthetic data in exports | PASS | 0 receipts reference a non-Kambale source |
| G25 | Objective 2 handoff recorded | PASS | handoff NOT_IDENTIFIABLE; candidate family NONE |
| G26 | Predictions are held-out members | PASS | 0 predictions are not test members of their fold |
| G27 | Leakage audit log | PASS | 6 audit rows; 0 failed |

Exit gates: G01, G02, G03, G05, G08, G09, G10, G11, G12, G13, G15, G16, G17, G19, G20, G25, G26. All exit gates PASS.

## 7. Tables

- O3-T01: GENERATED, 39 rows; Model definitions, predictors, target version and sample support.
- O3-T02: GENERATED, 70 rows; Split-by-split hyperparameters, variogram and calibration diagnostics.
- O3-T03: GENERATED, 61 rows; Out-of-fold completeness and leakage audit.
- O3-T04: GENERATED, 31 rows; Model artifact and reproducibility registry.

The rendered tables are in tables/objective_3 as CSV, Markdown and LaTeX.

## 8. Figures

- O3-F01 (GENERATED): Outer-fold spatial map and class support. rendered from the registered queries.
- O3-F02 (GENERATED): Predictor availability and observation support. rendered from the registered queries.
- O3-F03 (NOT_SUPPORTED): M1 indicator-kriging out-of-fold probabilities. M1 indicator kriging produced no out-of-fold prediction because no training-only variogram was both identified and stable: F1: NOT_ESTIMABLE (spherical: NOT_IDENTIFIABLE (range at the upper bound: not identified inside the supported lags; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)); F2: NOT_ESTIMABLE (spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)); F3: NOT_ESTIMABLE (spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)); F4: NOT_ESTIMABLE (spherical: NOT_IDENTIFIABLE (range at the upper bound: not identified inside the supported lags; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)); F5: NOT_ESTIMABLE (spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)).
- O3-F04 (GENERATED): M2 out-of-fold probability sections. rendered from the registered queries.
- O3-F05 (GENERATED): M3 hybrid or fallback probability section. rendered from the registered queries.
- O3-F06 (GENERATED): Training-only residual variogram diagnostics. rendered from the registered queries.

M1 is registered NOT_SUPPORTED when no fold produced a kriging prediction; the reason is recorded in the figure registry and in section 5.2.

## 9. Tests

```text
......................................                                   [100%]
38 passed in 1.45s
```

## 10. Deviations, warnings and limitations

- M1 is not estimable at this support: the Objective 2 handoff found no between-hole continuity, and no outer training fold identified a stable lateral indicator variogram.
- M3 is an ML-only fallback in every fold where the residual variogram was unsupported; it is not a validated hybrid result.
- Only three predictors (easting, northing, relative Z) exist at every held-out interval. Weathering, lithology and label evidence are logged-only or target-derived and are forbidden as predictors. The models are therefore spatial-trend models, not geological-covariate models.
- Relative Z is used; no collar elevation or DEM is used, so no absolute-elevation claim is made.
- Five drill lines, one with only three holes, carry the outer split. A held-out line is an extrapolation in northing for the models.
- The secondary whole-hole split plan is registered and audited but not used for the Objective 4 predictions; a change of plan needs a new predeclared configuration.
- XGBoost is not installed; scikit-learn's histogram gradient boosting is the declared fallback.
- The final full-data refit is PENDING_O4. Objective 3 does not fit on all observations and does not call that fit spatially validated.
- The code commit is the last committed revision; the Objective 3 working tree is deliberately not committed. The configuration hash, SQL hashes and artifact hashes identify the exact run.

## 11. Objective 4 handoff contract

- Split plan: `O3-SPLIT-LODO-1`, hash `e1193a349fcd34264519672cb3de9854b19e984a21b21d784b011220e9888c1f`, 5 line folds.
- Target: `TARGET-DESIGN_8_2_v1-1`, rule DESIGN_8_2_v1 APPROVED, 1829 binary intervals.
- Geometry: `GEOM-10-1`, PROVISIONAL_RELATIVE, vertical basis RELATIVE_TO_COLLAR, z_absolute_used=0.
- Predictions: `predictions_oof`, one row per (training run, held-out interval), with `p_raw`, `p_calibrated`, clipping flags, training-selected threshold and predicted class.
- Failures: `prediction_failures`, one row per (fold, held-out interval, family) that could not be predicted.
- Fits and diagnostics: `training_runs`, `hyperparameter_trials`, `variogram_training_fits`, `hybrid_residual_variogram`, `training_lag_bins`, `calibration_fits`, `residual_diagnostics`.
- Artifacts: `model_artifacts`, parameter and provenance records with SHA-256.
- Selection policy: inner whole-hole CV log loss; no outer test result was used to select a model or a threshold. O4 may evaluate and rank, but must not refit models or change the split.
- M1 status by fold: F1=NOT_ESTIMABLE, F2=NOT_ESTIMABLE, F3=NOT_ESTIMABLE, F4=NOT_ESTIMABLE, F5=NOT_ESTIMABLE.
- M3 status by fold: F1=FALLBACK, F2=FALLBACK, F3=FALLBACK, F4=FALLBACK, F5=FALLBACK.
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
| calibration_fits | 20 |
| export_manifests | 62 |
| feature_registry | 25 |
| figure_registry | 6 |
| figure_sql_registry | 18 |
| final_refits | 1 |
| gate_results | 162 |
| geometry_versions | 1 |
| hybrid_residual_variogram | 10 |
| hyperparameter_trials | 80 |
| label_versions | 1 |
| leakage_audit_log | 6 |
| model_artifacts | 30 |
| model_families | 6 |
| prediction_failures | 1829 |
| predictions_oof | 9145 |
| residual_diagnostics | 9145 |
| schema_version | 1 |
| source_receipts | 1 |
| spatial_split_plans | 2 |
| split_audit | 10 |
| split_membership | 18290 |
| stage_runs | 9 |
| table_registry | 4 |
| table_sql_registry | 4 |
| target_registries | 1 |
| training_lag_bins | 250 |
| training_runs | 30 |
| training_sample_manifest | 43896 |
| variogram_training_fits | 10 |

Counts are taken when this report is written. The post-report VERIFY run adds one `stage_runs` row and one gate set; that run is the authoritative final check and its gate rows are in the database.

O1 receipt content SHA-256: abf6f758faf75c82a250931ab034b145574a10f98362424e93dd6cc6483dea22. O2 receipt 1 content SHA-256: abf6f758faf75c82a250931ab034b145574a10f98362424e93dd6cc6483dea22. Ordered identifier digest: a94753f238d017f378b4b81fa61fcb061b63c62a687a68bafcdbbaf480027f55. Selection query SHA-256: 677203494777ff7efc26c6e5286142522049c7112f95109ed366a2da3481a767.


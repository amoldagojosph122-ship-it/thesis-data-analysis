# Objective 3: blocked, skipped, failed and deferred items

Gate results are from VERIFY run 16. Every WARN, SKIP, STOP and model failure is listed.

## Gates with a warning or a stop

- none

## Model failures and fallbacks

- O3-SPLIT-HOLE-IL-2 fold 1 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-HOLE-IL-2 fold 2 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-HOLE-IL-2 fold 3 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-HOLE-IL-2 fold 4 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-HOLE-IL-2 fold 5 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-LODO-1 fold 1 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-LODO-1 fold 2 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-LODO-1 fold 3 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-LODO-1 fold 4 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback
- O3-SPLIT-LODO-1 fold 5 M3_HYBRID: FALLBACK: residual covariance PURE_NUGGET selected by inner CV: M3 equals the calibrated M2_WF_SEL trend and is recorded as the ML-only fallback

## Leakage audit

- PASS OUTER_TEST_NOT_IN_TRAINING_MANIFEST: 0 test observations appear in a training manifest of the same fold
- PASS PREDICTIONS_ARE_TEST_MEMBERS: 0 predictions are not test members of their fold
- PASS PREDICTORS_SAFE_AND_AVAILABLE: 0 deployed predictors are not SAFE and available (easting_m, northing_m, z_relative_m, depth_below_weathering_front_m)
- PASS FRONT_FEATURE_FOLD_SAFE: 5 outer folds recomputed with the test holes' weathering codes altered; 0 failed; fold 1: 3 test holes altered; 68 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 2: 13 test holes altered; 58 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 3: 21 test holes altered; 50 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 4: 15 test holes altered; 56 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 5: 19 test holes altered; 52 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True
- PASS VARIOGRAMS_BELONG_TO_THEIR_TRAINING_FOLD: 0 covariance rows reference a different fold
- PASS CALIBRATION_USES_INNER_DATA_ONLY: 0 calibration fits use more rows than the outer training fold
- PASS NO_FINAL_FULL_FIT_IN_OOF: 0 final full-data refits exist before Objective 4 selection
- PASS OUTER_TEST_NOT_IN_TRAINING_MANIFEST: 0 test observations appear in a training manifest of the same fold
- PASS PREDICTIONS_ARE_TEST_MEMBERS: 0 predictions are not test members of their fold
- PASS PREDICTORS_SAFE_AND_AVAILABLE: 0 deployed predictors are not SAFE and available (easting_m, northing_m, z_relative_m, depth_below_weathering_front_m)
- PASS FRONT_FEATURE_FOLD_SAFE: 5 outer folds recomputed with the test holes' weathering codes altered; 0 failed; fold 1: 16 test holes altered; 55 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 2: 15 test holes altered; 56 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 3: 15 test holes altered; 56 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 4: 13 test holes altered; 58 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 5: 12 test holes altered; 59 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True
- PASS VARIOGRAMS_BELONG_TO_THEIR_TRAINING_FOLD: 0 covariance rows reference a different fold
- PASS CALIBRATION_USES_INNER_DATA_ONLY: 0 calibration fits use more rows than the outer training fold
- PASS NO_FINAL_FULL_FIT_IN_OOF: 0 final full-data refits exist before Objective 4 selection

## Deferred work (not performed in this stage)

- O3-SPLIT-LODO-1: M3 is the ML-only fallback in folds [1, 2, 3, 4, 5]; it is not a validated hybrid.
- O3-SPLIT-HOLE-IL-2: M3 is the ML-only fallback in folds [1, 2, 3, 4, 5]; it is not a validated hybrid.
- Outer-test evaluation and model ranking: Objective 4.
- Final full-data refit: PENDING_O4.
- Geological covariates: none exist at prediction locations beyond the fold-safe front surface.
- Absolute elevation: no collar RL; no DEM and no absolute-Z product.
- XGBoost: not installed; sklearn histogram gradient boosting is the declared fallback.
- Commit and push: not done; this waits for the user's instruction.


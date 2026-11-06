# Objective 3: blocked, skipped, failed and deferred items

Gate results are from VERIFY run 9. Every WARN, SKIP, STOP and model failure is listed.

## Gates with a warning or a stop

- none

## Model failures and fallbacks

- M1 fold 1: NOT_ESTIMABLE: spherical: NOT_IDENTIFIABLE (range at the upper bound: not identified inside the supported lags; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- M1 fold 2: NOT_ESTIMABLE: spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- M1 fold 3: NOT_ESTIMABLE: spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- M1 fold 4: NOT_ESTIMABLE: spherical: NOT_IDENTIFIABLE (range at the upper bound: not identified inside the supported lags; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- M1 fold 5: NOT_ESTIMABLE: spherical: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED)
- M3 fold 1: FALLBACK: residual covariance unsupported: spherical: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); ML-only fallback
- M3 fold 2: FALLBACK: residual covariance unsupported: spherical: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); ML-only fallback
- M3 fold 3: FALLBACK: residual covariance unsupported: spherical: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); ML-only fallback
- M3 fold 4: FALLBACK: residual covariance unsupported: spherical: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); ML-only fallback
- M3 fold 5: FALLBACK: residual covariance unsupported: spherical: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); exponential: NOT_IDENTIFIABLE (range at the smallest supported lag: no dependence beyond the nugget; structured sill below 5% of the reference variance); stability NOT_ASSESSED (base fit is not FITTED); ML-only fallback

## Leakage audit

- PASS OUTER_TEST_NOT_IN_TRAINING_MANIFEST: 0 test observations appear in a training manifest of the same fold
- PASS PREDICTIONS_ARE_TEST_MEMBERS: 0 predictions are not test members of their fold
- PASS PREDICTORS_SAFE_AND_AVAILABLE: 0 deployed predictors are not SAFE and available
- PASS VARIOGRAMS_BELONG_TO_THEIR_TRAINING_FOLD: 0 variogram rows reference a different fold
- PASS CALIBRATION_USES_INNER_DATA_ONLY: 0 calibration fits use more rows than the outer training fold
- PASS NO_FINAL_FULL_FIT_IN_OOF: 0 final full-data refits exist before Objective 4 selection

## Deferred work (not performed in this stage)

- M1 indicator kriging at this support: no stable between-hole variogram was identified in any outer training fold. A future stage may re-test M1 only if the support or label basis changes.
- M3 hybrid: the residual covariance is unsupported in every fold, so the recorded result is the declared ML-only fallback. It is not a validated hybrid.
- Secondary whole-hole cross-validation: the fold plan and audit are stored, but its predictions are not handed to Objective 4.
- Geological covariates: none exist in the source at prediction locations. Weathering, lithology and comment evidence are logged-only or target-derived.
- Absolute elevation: no collar RL; no DEM and no absolute-Z product.
- Final full-data refit: PENDING_O4.
- XGBoost: not installed; sklearn histogram gradient boosting is the declared fallback.
- Commit and push: not done; this waits for the user's instruction.


# O3-T03. Out-of-fold completeness and leakage audit

Expected rows are the held-out intervals of each fold. A completed candidate has a prediction or an explicit failure record for every held-out interval. Leakage rows are the audit log written by training.
Source: sql/objective_3/tables/O3-T03.sql, receipt 1, 61 rows.

| section | fold_id | line_code | family_id | expected | predicted | failed | clipped | positive_true | positive_pred | status | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FOLD_FAMILY | 1 |  | BASE_LOGISTIC | 84 | 84 | 0 | 0 | 29 | 69 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | 1 |  | BASE_PREVALENCE | 84 | 84 | 0 | 0 | 29 | 0 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | 1 |  | M1_IK | 84 | 0 | 84 | 0 | 29 | 0 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | 1 |  | M2_HGB | 84 | 84 | 0 | 0 | 29 | 20 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | 1 |  | M2_RF | 84 | 84 | 0 | 0 | 29 | 42 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | 1 |  | M3_HYBRID | 84 | 84 | 0 | 0 | 29 | 42 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | 2 |  | BASE_LOGISTIC | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 2 |  | BASE_PREVALENCE | 429 | 429 | 0 | 0 | 217 | 0 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 2 |  | M1_IK | 429 | 0 | 429 | 0 | 217 | 0 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 2 |  | M2_HGB | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 2 |  | M2_RF | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 2 |  | M3_HYBRID | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 3 |  | BASE_LOGISTIC | 528 | 528 | 0 | 0 | 130 | 43 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 3 |  | BASE_PREVALENCE | 528 | 528 | 0 | 0 | 130 | 0 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 3 |  | M1_IK | 528 | 0 | 528 | 0 | 130 | 0 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 3 |  | M2_HGB | 528 | 528 | 0 | 0 | 130 | 486 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 3 |  | M2_RF | 528 | 528 | 0 | 0 | 130 | 256 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 3 |  | M3_HYBRID | 528 | 528 | 0 | 0 | 130 | 256 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 4 |  | BASE_LOGISTIC | 401 | 401 | 0 | 0 | 133 | 186 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 4 |  | BASE_PREVALENCE | 401 | 401 | 0 | 0 | 133 | 0 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 4 |  | M1_IK | 401 | 0 | 401 | 0 | 133 | 0 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 4 |  | M2_HGB | 401 | 401 | 0 | 0 | 133 | 216 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 4 |  | M2_RF | 401 | 401 | 0 | 0 | 133 | 249 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 4 |  | M3_HYBRID | 401 | 401 | 0 | 0 | 133 | 249 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | 5 |  | BASE_LOGISTIC | 387 | 387 | 0 | 0 | 16 | 17 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 5 |  | BASE_PREVALENCE | 387 | 387 | 0 | 0 | 16 | 0 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 5 |  | M1_IK | 387 | 0 | 387 | 0 | 16 | 0 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 5 |  | M2_HGB | 387 | 387 | 0 | 0 | 16 | 117 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 5 |  | M2_RF | 387 | 387 | 0 | 0 | 16 | 4 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | 5 |  | M3_HYBRID | 387 | 387 | 0 | 0 | 16 | 4 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| LEAKAGE |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | OUTER_TEST_NOT_IN_TRAINING_MANIFEST: 0 test observations appear in a training manifest of the same fold |
| LEAKAGE |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | PREDICTIONS_ARE_TEST_MEMBERS: 0 predictions are not test members of their fold |
| LEAKAGE |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | PREDICTORS_SAFE_AND_AVAILABLE: 0 deployed predictors are not SAFE and available |
| LEAKAGE |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | VARIOGRAMS_BELONG_TO_THEIR_TRAINING_FOLD: 0 variogram rows reference a different fold |
| LEAKAGE |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | CALIBRATION_USES_INNER_DATA_ONLY: 0 calibration fits use more rows than the outer training fold |
| LEAKAGE |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | NO_FINAL_FULL_FIT_IN_OOF: 0 final full-data refits exist before Objective 4 selection |
| LINE_FAMILY | 1 | NOM_N1111930 | BASE_LOGISTIC | 84 | 84 | 0 | 0 | 29 | 69 | COMPLETE | observations in the held-out line; mean p 0.5121 |
| LINE_FAMILY | 1 | NOM_N1111930 | BASE_PREVALENCE | 84 | 84 | 0 | 0 | 29 | 0 | COMPLETE | observations in the held-out line; mean p 0.2842 |
| LINE_FAMILY | 1 | NOM_N1111930 | M2_HGB | 84 | 84 | 0 | 0 | 29 | 20 | COMPLETE | observations in the held-out line; mean p 0.1142 |
| LINE_FAMILY | 1 | NOM_N1111930 | M2_RF | 84 | 84 | 0 | 0 | 29 | 42 | COMPLETE | observations in the held-out line; mean p 0.2142 |
| LINE_FAMILY | 1 | NOM_N1111930 | M3_HYBRID | 84 | 84 | 0 | 0 | 29 | 42 | COMPLETE | observations in the held-out line; mean p 0.2142 |
| LINE_FAMILY | 2 | NOM_N1112140 | BASE_LOGISTIC | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.4735 |
| LINE_FAMILY | 2 | NOM_N1112140 | BASE_PREVALENCE | 429 | 429 | 0 | 0 | 217 | 0 | COMPLETE | observations in the held-out line; mean p 0.22 |
| LINE_FAMILY | 2 | NOM_N1112140 | M2_HGB | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.4358 |
| LINE_FAMILY | 2 | NOM_N1112140 | M2_RF | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.3982 |
| LINE_FAMILY | 2 | NOM_N1112140 | M3_HYBRID | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.3982 |
| LINE_FAMILY | 3 | NOM_N1112500 | BASE_LOGISTIC | 528 | 528 | 0 | 0 | 130 | 43 | COMPLETE | observations in the held-out line; mean p 0.1415 |
| LINE_FAMILY | 3 | NOM_N1112500 | BASE_PREVALENCE | 528 | 528 | 0 | 0 | 130 | 0 | COMPLETE | observations in the held-out line; mean p 0.3036 |
| LINE_FAMILY | 3 | NOM_N1112500 | M2_HGB | 528 | 528 | 0 | 0 | 130 | 486 | COMPLETE | observations in the held-out line; mean p 0.2093 |
| LINE_FAMILY | 3 | NOM_N1112500 | M2_RF | 528 | 528 | 0 | 0 | 130 | 256 | COMPLETE | observations in the held-out line; mean p 0.2397 |
| LINE_FAMILY | 3 | NOM_N1112500 | M3_HYBRID | 528 | 528 | 0 | 0 | 130 | 256 | COMPLETE | observations in the held-out line; mean p 0.2397 |
| LINE_FAMILY | 4 | NOM_N1112600 | BASE_LOGISTIC | 401 | 401 | 0 | 0 | 133 | 186 | COMPLETE | observations in the held-out line; mean p 0.2547 |
| LINE_FAMILY | 4 | NOM_N1112600 | BASE_PREVALENCE | 401 | 401 | 0 | 0 | 133 | 0 | COMPLETE | observations in the held-out line; mean p 0.2745 |
| LINE_FAMILY | 4 | NOM_N1112600 | M2_HGB | 401 | 401 | 0 | 0 | 133 | 216 | COMPLETE | observations in the held-out line; mean p 0.2258 |
| LINE_FAMILY | 4 | NOM_N1112600 | M2_RF | 401 | 401 | 0 | 0 | 133 | 249 | COMPLETE | observations in the held-out line; mean p 0.3687 |
| LINE_FAMILY | 4 | NOM_N1112600 | M3_HYBRID | 401 | 401 | 0 | 0 | 133 | 249 | COMPLETE | observations in the held-out line; mean p 0.3687 |
| LINE_FAMILY | 5 | NOM_N1113000 | BASE_LOGISTIC | 387 | 387 | 0 | 0 | 16 | 17 | COMPLETE | observations in the held-out line; mean p 0.1442 |
| LINE_FAMILY | 5 | NOM_N1113000 | BASE_PREVALENCE | 387 | 387 | 0 | 0 | 16 | 0 | COMPLETE | observations in the held-out line; mean p 0.353 |
| LINE_FAMILY | 5 | NOM_N1113000 | M2_HGB | 387 | 387 | 0 | 0 | 16 | 117 | COMPLETE | observations in the held-out line; mean p 0.2054 |
| LINE_FAMILY | 5 | NOM_N1113000 | M2_RF | 387 | 387 | 0 | 0 | 16 | 4 | COMPLETE | observations in the held-out line; mean p 0.171 |
| LINE_FAMILY | 5 | NOM_N1113000 | M3_HYBRID | 387 | 387 | 0 | 0 | 16 | 4 | COMPLETE | observations in the held-out line; mean p 0.171 |

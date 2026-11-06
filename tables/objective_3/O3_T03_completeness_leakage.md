# O3-T03. Out-of-fold completeness and leakage audit, both split plans

Expected rows are the held-out intervals of each fold of each split plan. A completed candidate has a prediction or an explicit failure record for every held-out interval. Leakage rows are the audit log.
Source: sql/objective_3/tables/O3-T03.sql, receipt 1, 432 rows.

| section | split_plan_id | fold_id | line_code | family_id | expected | predicted | failed | clipped | positive_true | positive_pred | status | detail |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | BASE_LOGISTIC | 383 | 383 | 0 | 0 | 83 | 120 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | BASE_LOGISTIC_WF | 383 | 383 | 0 | 0 | 83 | 115 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | BASE_PREVALENCE | 383 | 383 | 0 | 0 | 83 | 0 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | M1_IK | 383 | 383 | 0 | 0 | 83 | 178 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | M2_HGB | 383 | 383 | 0 | 0 | 83 | 278 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | M2_HGB_WF | 383 | 383 | 0 | 0 | 83 | 294 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | M2_RF | 383 | 383 | 0 | 0 | 83 | 223 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | M2_RF_WF | 383 | 383 | 0 | 0 | 83 | 218 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | M2_SEL | 383 | 383 | 0 | 0 | 83 | 223 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | M2_WF_SEL | 383 | 383 | 0 | 0 | 83 | 218 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 |  | M3_HYBRID | 383 | 383 | 0 | 0 | 83 | 218 | COMPLETE | minimum test-to-train collar distance 17.1172427686237 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | BASE_LOGISTIC | 455 | 455 | 0 | 0 | 199 | 281 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | BASE_LOGISTIC_WF | 455 | 455 | 0 | 0 | 199 | 288 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | BASE_PREVALENCE | 455 | 455 | 0 | 0 | 199 | 0 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | M1_IK | 455 | 455 | 0 | 0 | 199 | 242 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | M2_HGB | 455 | 455 | 0 | 0 | 199 | 192 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | M2_HGB_WF | 455 | 455 | 0 | 0 | 199 | 138 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | M2_RF | 455 | 455 | 0 | 0 | 199 | 239 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | M2_RF_WF | 455 | 455 | 0 | 0 | 199 | 276 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | M2_SEL | 455 | 455 | 0 | 0 | 199 | 239 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | M2_WF_SEL | 455 | 455 | 0 | 0 | 199 | 276 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 |  | M3_HYBRID | 455 | 455 | 0 | 0 | 199 | 276 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | BASE_LOGISTIC | 383 | 383 | 0 | 0 | 119 | 134 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | BASE_LOGISTIC_WF | 383 | 383 | 0 | 0 | 119 | 109 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | BASE_PREVALENCE | 383 | 383 | 0 | 0 | 119 | 0 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | M1_IK | 383 | 383 | 0 | 0 | 119 | 148 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | M2_HGB | 383 | 383 | 0 | 0 | 119 | 240 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | M2_HGB_WF | 383 | 383 | 0 | 0 | 119 | 210 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | M2_RF | 383 | 383 | 0 | 0 | 119 | 130 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | M2_RF_WF | 383 | 383 | 0 | 0 | 119 | 196 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | M2_SEL | 383 | 383 | 0 | 0 | 119 | 130 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | M2_WF_SEL | 383 | 383 | 0 | 0 | 119 | 196 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 |  | M3_HYBRID | 383 | 383 | 0 | 0 | 119 | 196 | COMPLETE | minimum test-to-train collar distance 15.2315462117278 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | BASE_LOGISTIC | 303 | 303 | 0 | 0 | 54 | 141 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | BASE_LOGISTIC_WF | 303 | 303 | 0 | 0 | 54 | 140 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | BASE_PREVALENCE | 303 | 303 | 0 | 0 | 54 | 0 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | M1_IK | 303 | 303 | 0 | 0 | 54 | 119 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | M2_HGB | 303 | 303 | 0 | 0 | 54 | 106 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | M2_HGB_WF | 303 | 303 | 0 | 0 | 54 | 132 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | M2_RF | 303 | 303 | 0 | 0 | 54 | 116 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | M2_RF_WF | 303 | 303 | 0 | 0 | 54 | 139 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | M2_SEL | 303 | 303 | 0 | 0 | 54 | 116 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | M2_WF_SEL | 303 | 303 | 0 | 0 | 54 | 139 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 |  | M3_HYBRID | 303 | 303 | 0 | 0 | 54 | 139 | COMPLETE | minimum test-to-train collar distance 16.0312195418814 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | BASE_LOGISTIC | 305 | 305 | 0 | 0 | 70 | 93 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | BASE_LOGISTIC_WF | 305 | 305 | 0 | 0 | 70 | 154 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | BASE_PREVALENCE | 305 | 305 | 0 | 0 | 70 | 0 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | M1_IK | 305 | 305 | 0 | 0 | 70 | 129 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | M2_HGB | 305 | 305 | 0 | 0 | 70 | 181 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | M2_HGB_WF | 305 | 305 | 0 | 0 | 70 | 203 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | M2_RF | 305 | 305 | 0 | 0 | 70 | 159 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | M2_RF_WF | 305 | 305 | 0 | 0 | 70 | 169 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | M2_SEL | 305 | 305 | 0 | 0 | 70 | 159 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | M2_WF_SEL | 305 | 305 | 0 | 0 | 70 | 169 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 |  | M3_HYBRID | 305 | 305 | 0 | 0 | 70 | 169 | COMPLETE | minimum test-to-train collar distance 16.2788205960997 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | BASE_LOGISTIC | 84 | 84 | 0 | 0 | 29 | 69 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | BASE_LOGISTIC_WF | 84 | 84 | 0 | 0 | 29 | 81 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | BASE_PREVALENCE | 84 | 84 | 0 | 0 | 29 | 0 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | M1_IK | 84 | 84 | 0 | 0 | 29 | 16 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | M2_HGB | 84 | 84 | 0 | 0 | 29 | 20 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | M2_HGB_WF | 84 | 84 | 0 | 0 | 29 | 36 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | M2_RF | 84 | 84 | 0 | 0 | 29 | 42 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | M2_RF_WF | 84 | 84 | 0 | 0 | 29 | 39 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | M2_SEL | 84 | 84 | 0 | 0 | 29 | 42 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | M2_WF_SEL | 84 | 84 | 0 | 0 | 29 | 39 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 1 |  | M3_HYBRID | 84 | 84 | 0 | 0 | 29 | 39 | COMPLETE | minimum test-to-train collar distance 556.577038692758 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | BASE_LOGISTIC | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | BASE_LOGISTIC_WF | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | BASE_PREVALENCE | 429 | 429 | 0 | 0 | 217 | 0 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | M1_IK | 429 | 429 | 0 | 0 | 217 | 304 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | M2_HGB | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | M2_HGB_WF | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | M2_RF | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | M2_RF_WF | 429 | 429 | 0 | 0 | 217 | 365 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | M2_SEL | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | M2_WF_SEL | 429 | 429 | 0 | 0 | 217 | 365 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 2 |  | M3_HYBRID | 429 | 429 | 0 | 0 | 217 | 365 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | BASE_LOGISTIC | 528 | 528 | 0 | 0 | 130 | 43 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | BASE_LOGISTIC_WF | 528 | 528 | 0 | 0 | 130 | 44 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | BASE_PREVALENCE | 528 | 528 | 0 | 0 | 130 | 0 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | M1_IK | 528 | 528 | 0 | 0 | 130 | 1 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | M2_HGB | 528 | 528 | 0 | 0 | 130 | 486 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | M2_HGB_WF | 528 | 528 | 0 | 0 | 130 | 438 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | M2_RF | 528 | 528 | 0 | 0 | 130 | 256 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | M2_RF_WF | 528 | 528 | 0 | 0 | 130 | 408 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | M2_SEL | 528 | 528 | 0 | 0 | 130 | 256 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | M2_WF_SEL | 528 | 528 | 0 | 0 | 130 | 408 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 3 |  | M3_HYBRID | 528 | 528 | 0 | 0 | 130 | 408 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | BASE_LOGISTIC | 401 | 401 | 0 | 0 | 133 | 186 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | BASE_LOGISTIC_WF | 401 | 401 | 0 | 0 | 133 | 163 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | BASE_PREVALENCE | 401 | 401 | 0 | 0 | 133 | 0 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | M1_IK | 401 | 401 | 0 | 0 | 133 | 257 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | M2_HGB | 401 | 401 | 0 | 0 | 133 | 216 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | M2_HGB_WF | 401 | 401 | 0 | 0 | 133 | 260 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | M2_RF | 401 | 401 | 0 | 0 | 133 | 249 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | M2_RF_WF | 401 | 401 | 0 | 0 | 133 | 220 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | M2_SEL | 401 | 401 | 0 | 0 | 133 | 249 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | M2_WF_SEL | 401 | 401 | 0 | 0 | 133 | 220 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 4 |  | M3_HYBRID | 401 | 401 | 0 | 0 | 133 | 220 | COMPLETE | minimum test-to-train collar distance 453.558430634907 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | BASE_LOGISTIC | 387 | 387 | 0 | 0 | 16 | 17 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | BASE_LOGISTIC_WF | 387 | 387 | 0 | 0 | 16 | 11 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | BASE_PREVALENCE | 387 | 387 | 0 | 0 | 16 | 0 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | M1_IK | 387 | 387 | 0 | 0 | 16 | 110 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | M2_HGB | 387 | 387 | 0 | 0 | 16 | 117 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | M2_HGB_WF | 387 | 387 | 0 | 0 | 16 | 0 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | M2_RF | 387 | 387 | 0 | 0 | 16 | 4 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | M2_RF_WF | 387 | 387 | 0 | 0 | 16 | 35 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | M2_SEL | 387 | 387 | 0 | 0 | 16 | 4 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | M2_WF_SEL | 387 | 387 | 0 | 0 | 16 | 35 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| FOLD_FAMILY | O3-SPLIT-LODO-1 | 5 |  | M3_HYBRID | 387 | 387 | 0 | 0 | 16 | 35 | COMPLETE | minimum test-to-train collar distance 488.409664114051 |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | OUTER_TEST_NOT_IN_TRAINING_MANIFEST: 0 test observations appear in a training manifest of the same fold |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | PREDICTIONS_ARE_TEST_MEMBERS: 0 predictions are not test members of their fold |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | PREDICTORS_SAFE_AND_AVAILABLE: 0 deployed predictors are not SAFE and available (easting_m, northing_m, z_relative_m, depth_below_weathering_front_m) |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | FRONT_FEATURE_FOLD_SAFE: 5 outer folds recomputed with the test holes' weathering codes altered; 0 failed; fold 1: 3 test holes altered; 68 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 2: 13 test holes altered; 58 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 3: 21 test holes altered; 50 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 4: 15 test holes altered; 56 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 5: 19 test holes altered; 52 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | VARIOGRAMS_BELONG_TO_THEIR_TRAINING_FOLD: 0 covariance rows reference a different fold |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | CALIBRATION_USES_INNER_DATA_ONLY: 0 calibration fits use more rows than the outer training fold |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | NO_FINAL_FULL_FIT_IN_OOF: 0 final full-data refits exist before Objective 4 selection |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | OUTER_TEST_NOT_IN_TRAINING_MANIFEST: 0 test observations appear in a training manifest of the same fold |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | PREDICTIONS_ARE_TEST_MEMBERS: 0 predictions are not test members of their fold |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | PREDICTORS_SAFE_AND_AVAILABLE: 0 deployed predictors are not SAFE and available (easting_m, northing_m, z_relative_m, depth_below_weathering_front_m) |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | FRONT_FEATURE_FOLD_SAFE: 5 outer folds recomputed with the test holes' weathering codes altered; 0 failed; fold 1: 16 test holes altered; 55 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 2: 15 test holes altered; 56 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 3: 15 test holes altered; 56 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 4: 13 test holes altered; 58 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True; fold 5: 12 test holes altered; 59 surface holes; test holes contributing to the surface: 0; test values unchanged: True; training values unchanged: True |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | VARIOGRAMS_BELONG_TO_THEIR_TRAINING_FOLD: 0 covariance rows reference a different fold |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | CALIBRATION_USES_INNER_DATA_ONLY: 0 calibration fits use more rows than the outer training fold |
| LEAKAGE |  |  |  |  | 0 | 0 | 0 | 0 | 0 | 0 | PASS | NO_FINAL_FULL_FIT_IN_OOF: 0 final full-data refits exist before Objective 4 selection |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | BASE_LOGISTIC | 30 | 30 | 0 | 0 | 11 | 20 | COMPLETE | observations in the held-out line; mean p 0.4631 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | BASE_LOGISTIC | 81 | 81 | 0 | 0 | 28 | 56 | COMPLETE | observations in the held-out line; mean p 0.469 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | BASE_LOGISTIC | 119 | 119 | 0 | 0 | 20 | 21 | COMPLETE | observations in the held-out line; mean p 0.2159 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | BASE_LOGISTIC | 77 | 77 | 0 | 0 | 21 | 23 | COMPLETE | observations in the held-out line; mean p 0.2987 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | BASE_LOGISTIC | 76 | 76 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.083 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | BASE_LOGISTIC_WF | 30 | 30 | 0 | 0 | 11 | 19 | COMPLETE | observations in the held-out line; mean p 0.4202 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | BASE_LOGISTIC_WF | 81 | 81 | 0 | 0 | 28 | 54 | COMPLETE | observations in the held-out line; mean p 0.4418 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | BASE_LOGISTIC_WF | 119 | 119 | 0 | 0 | 20 | 15 | COMPLETE | observations in the held-out line; mean p 0.2144 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | BASE_LOGISTIC_WF | 77 | 77 | 0 | 0 | 21 | 27 | COMPLETE | observations in the held-out line; mean p 0.3253 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | BASE_LOGISTIC_WF | 76 | 76 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.1107 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | BASE_PREVALENCE | 30 | 30 | 0 | 0 | 11 | 0 | COMPLETE | observations in the held-out line; mean p 0.3057 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | BASE_PREVALENCE | 81 | 81 | 0 | 0 | 28 | 0 | COMPLETE | observations in the held-out line; mean p 0.3057 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | BASE_PREVALENCE | 119 | 119 | 0 | 0 | 20 | 0 | COMPLETE | observations in the held-out line; mean p 0.3057 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | BASE_PREVALENCE | 77 | 77 | 0 | 0 | 21 | 0 | COMPLETE | observations in the held-out line; mean p 0.3057 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | BASE_PREVALENCE | 76 | 76 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.3057 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | M1_IK | 30 | 30 | 0 | 0 | 11 | 16 | COMPLETE | observations in the held-out line; mean p 0.3537 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | M1_IK | 81 | 81 | 0 | 0 | 28 | 60 | COMPLETE | observations in the held-out line; mean p 0.4336 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | M1_IK | 119 | 119 | 0 | 0 | 20 | 53 | COMPLETE | observations in the held-out line; mean p 0.2664 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | M1_IK | 77 | 77 | 0 | 0 | 21 | 44 | COMPLETE | observations in the held-out line; mean p 0.361 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | M1_IK | 76 | 76 | 0 | 0 | 3 | 5 | COMPLETE | observations in the held-out line; mean p 0.1014 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | M2_HGB | 30 | 30 | 0 | 0 | 11 | 28 | COMPLETE | observations in the held-out line; mean p 0.3536 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | M2_HGB | 81 | 81 | 0 | 0 | 28 | 79 | COMPLETE | observations in the held-out line; mean p 0.4342 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | M2_HGB | 119 | 119 | 0 | 0 | 20 | 82 | COMPLETE | observations in the held-out line; mean p 0.2133 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | M2_HGB | 77 | 77 | 0 | 0 | 21 | 77 | COMPLETE | observations in the held-out line; mean p 0.3076 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | M2_HGB | 76 | 76 | 0 | 0 | 3 | 12 | COMPLETE | observations in the held-out line; mean p 0.088 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | M2_HGB_WF | 30 | 30 | 0 | 0 | 11 | 25 | COMPLETE | observations in the held-out line; mean p 0.3233 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | M2_HGB_WF | 81 | 81 | 0 | 0 | 28 | 74 | COMPLETE | observations in the held-out line; mean p 0.4442 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | M2_HGB_WF | 119 | 119 | 0 | 0 | 20 | 84 | COMPLETE | observations in the held-out line; mean p 0.2493 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | M2_HGB_WF | 77 | 77 | 0 | 0 | 21 | 75 | COMPLETE | observations in the held-out line; mean p 0.3214 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | M2_HGB_WF | 76 | 76 | 0 | 0 | 3 | 36 | COMPLETE | observations in the held-out line; mean p 0.105 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | M2_RF | 30 | 30 | 0 | 0 | 11 | 18 | COMPLETE | observations in the held-out line; mean p 0.2964 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | M2_RF | 81 | 81 | 0 | 0 | 28 | 65 | COMPLETE | observations in the held-out line; mean p 0.5061 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | M2_RF | 119 | 119 | 0 | 0 | 20 | 63 | COMPLETE | observations in the held-out line; mean p 0.2581 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | M2_RF | 77 | 77 | 0 | 0 | 21 | 77 | COMPLETE | observations in the held-out line; mean p 0.3168 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | M2_RF | 76 | 76 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.0449 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | M2_RF_WF | 30 | 30 | 0 | 0 | 11 | 18 | COMPLETE | observations in the held-out line; mean p 0.2806 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | M2_RF_WF | 81 | 81 | 0 | 0 | 28 | 63 | COMPLETE | observations in the held-out line; mean p 0.4338 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | M2_RF_WF | 119 | 119 | 0 | 0 | 20 | 65 | COMPLETE | observations in the held-out line; mean p 0.2487 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | M2_RF_WF | 77 | 77 | 0 | 0 | 21 | 67 | COMPLETE | observations in the held-out line; mean p 0.3143 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | M2_RF_WF | 76 | 76 | 0 | 0 | 3 | 5 | COMPLETE | observations in the held-out line; mean p 0.0748 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | M2_SEL | 30 | 30 | 0 | 0 | 11 | 18 | COMPLETE | observations in the held-out line; mean p 0.2964 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | M2_SEL | 81 | 81 | 0 | 0 | 28 | 65 | COMPLETE | observations in the held-out line; mean p 0.5061 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | M2_SEL | 119 | 119 | 0 | 0 | 20 | 63 | COMPLETE | observations in the held-out line; mean p 0.2581 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | M2_SEL | 77 | 77 | 0 | 0 | 21 | 77 | COMPLETE | observations in the held-out line; mean p 0.3168 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | M2_SEL | 76 | 76 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.0449 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | M2_WF_SEL | 30 | 30 | 0 | 0 | 11 | 18 | COMPLETE | observations in the held-out line; mean p 0.2806 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | M2_WF_SEL | 81 | 81 | 0 | 0 | 28 | 63 | COMPLETE | observations in the held-out line; mean p 0.4338 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | M2_WF_SEL | 119 | 119 | 0 | 0 | 20 | 65 | COMPLETE | observations in the held-out line; mean p 0.2487 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | M2_WF_SEL | 77 | 77 | 0 | 0 | 21 | 67 | COMPLETE | observations in the held-out line; mean p 0.3143 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | M2_WF_SEL | 76 | 76 | 0 | 0 | 3 | 5 | COMPLETE | observations in the held-out line; mean p 0.0748 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1111930 | M3_HYBRID | 30 | 30 | 0 | 0 | 11 | 18 | COMPLETE | observations in the held-out line; mean p 0.2806 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112140 | M3_HYBRID | 81 | 81 | 0 | 0 | 28 | 63 | COMPLETE | observations in the held-out line; mean p 0.4338 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112500 | M3_HYBRID | 119 | 119 | 0 | 0 | 20 | 65 | COMPLETE | observations in the held-out line; mean p 0.2487 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1112600 | M3_HYBRID | 77 | 77 | 0 | 0 | 21 | 67 | COMPLETE | observations in the held-out line; mean p 0.3143 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 1 | NOM_N1113000 | M3_HYBRID | 76 | 76 | 0 | 0 | 3 | 5 | COMPLETE | observations in the held-out line; mean p 0.0748 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | BASE_LOGISTIC | 34 | 34 | 0 | 0 | 18 | 32 | COMPLETE | observations in the held-out line; mean p 0.4483 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | BASE_LOGISTIC | 141 | 141 | 0 | 0 | 89 | 137 | COMPLETE | observations in the held-out line; mean p 0.5761 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | BASE_LOGISTIC | 115 | 115 | 0 | 0 | 42 | 56 | COMPLETE | observations in the held-out line; mean p 0.2207 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | BASE_LOGISTIC | 88 | 88 | 0 | 0 | 50 | 54 | COMPLETE | observations in the held-out line; mean p 0.2815 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | BASE_LOGISTIC | 77 | 77 | 0 | 0 | 0 | 2 | COMPLETE | observations in the held-out line; mean p 0.0788 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | BASE_LOGISTIC_WF | 34 | 34 | 0 | 0 | 18 | 32 | COMPLETE | observations in the held-out line; mean p 0.3798 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | BASE_LOGISTIC_WF | 141 | 141 | 0 | 0 | 89 | 133 | COMPLETE | observations in the held-out line; mean p 0.5054 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | BASE_LOGISTIC_WF | 115 | 115 | 0 | 0 | 42 | 56 | COMPLETE | observations in the held-out line; mean p 0.2147 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | BASE_LOGISTIC_WF | 88 | 88 | 0 | 0 | 50 | 62 | COMPLETE | observations in the held-out line; mean p 0.2942 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | BASE_LOGISTIC_WF | 77 | 77 | 0 | 0 | 0 | 5 | COMPLETE | observations in the held-out line; mean p 0.1091 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | BASE_PREVALENCE | 34 | 34 | 0 | 0 | 18 | 0 | COMPLETE | observations in the held-out line; mean p 0.2373 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | BASE_PREVALENCE | 141 | 141 | 0 | 0 | 89 | 0 | COMPLETE | observations in the held-out line; mean p 0.2373 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | BASE_PREVALENCE | 115 | 115 | 0 | 0 | 42 | 0 | COMPLETE | observations in the held-out line; mean p 0.2373 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | BASE_PREVALENCE | 88 | 88 | 0 | 0 | 50 | 0 | COMPLETE | observations in the held-out line; mean p 0.2373 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | BASE_PREVALENCE | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.2373 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | M1_IK | 34 | 34 | 0 | 0 | 18 | 18 | COMPLETE | observations in the held-out line; mean p 0.2558 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | M1_IK | 141 | 141 | 0 | 0 | 89 | 111 | COMPLETE | observations in the held-out line; mean p 0.3634 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | M1_IK | 115 | 115 | 0 | 0 | 42 | 51 | COMPLETE | observations in the held-out line; mean p 0.2338 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | M1_IK | 88 | 88 | 0 | 0 | 50 | 62 | COMPLETE | observations in the held-out line; mean p 0.3517 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | M1_IK | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.0947 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | M2_HGB | 34 | 34 | 0 | 0 | 18 | 1 | COMPLETE | observations in the held-out line; mean p 0.2684 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | M2_HGB | 141 | 141 | 0 | 0 | 89 | 99 | COMPLETE | observations in the held-out line; mean p 0.4843 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | M2_HGB | 115 | 115 | 0 | 0 | 42 | 26 | COMPLETE | observations in the held-out line; mean p 0.1844 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | M2_HGB | 88 | 88 | 0 | 0 | 50 | 66 | COMPLETE | observations in the held-out line; mean p 0.3835 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | M2_HGB | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.0694 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | M2_HGB_WF | 34 | 34 | 0 | 0 | 18 | 0 | COMPLETE | observations in the held-out line; mean p 0.2614 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | M2_HGB_WF | 141 | 141 | 0 | 0 | 89 | 93 | COMPLETE | observations in the held-out line; mean p 0.4829 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | M2_HGB_WF | 115 | 115 | 0 | 0 | 42 | 10 | COMPLETE | observations in the held-out line; mean p 0.1828 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | M2_HGB_WF | 88 | 88 | 0 | 0 | 50 | 35 | COMPLETE | observations in the held-out line; mean p 0.3685 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | M2_HGB_WF | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.0708 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | M2_RF | 34 | 34 | 0 | 0 | 18 | 15 | COMPLETE | observations in the held-out line; mean p 0.1996 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | M2_RF | 141 | 141 | 0 | 0 | 89 | 114 | COMPLETE | observations in the held-out line; mean p 0.4517 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | M2_RF | 115 | 115 | 0 | 0 | 42 | 34 | COMPLETE | observations in the held-out line; mean p 0.1675 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | M2_RF | 88 | 88 | 0 | 0 | 50 | 76 | COMPLETE | observations in the held-out line; mean p 0.4007 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | M2_RF | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.0421 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | M2_RF_WF | 34 | 34 | 0 | 0 | 18 | 19 | COMPLETE | observations in the held-out line; mean p 0.1814 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | M2_RF_WF | 141 | 141 | 0 | 0 | 89 | 119 | COMPLETE | observations in the held-out line; mean p 0.4415 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | M2_RF_WF | 115 | 115 | 0 | 0 | 42 | 63 | COMPLETE | observations in the held-out line; mean p 0.1967 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | M2_RF_WF | 88 | 88 | 0 | 0 | 50 | 75 | COMPLETE | observations in the held-out line; mean p 0.3819 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | M2_RF_WF | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.0764 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | M2_SEL | 34 | 34 | 0 | 0 | 18 | 15 | COMPLETE | observations in the held-out line; mean p 0.1996 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | M2_SEL | 141 | 141 | 0 | 0 | 89 | 114 | COMPLETE | observations in the held-out line; mean p 0.4517 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | M2_SEL | 115 | 115 | 0 | 0 | 42 | 34 | COMPLETE | observations in the held-out line; mean p 0.1675 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | M2_SEL | 88 | 88 | 0 | 0 | 50 | 76 | COMPLETE | observations in the held-out line; mean p 0.4007 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | M2_SEL | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.0421 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | M2_WF_SEL | 34 | 34 | 0 | 0 | 18 | 19 | COMPLETE | observations in the held-out line; mean p 0.1814 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | M2_WF_SEL | 141 | 141 | 0 | 0 | 89 | 119 | COMPLETE | observations in the held-out line; mean p 0.4415 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | M2_WF_SEL | 115 | 115 | 0 | 0 | 42 | 63 | COMPLETE | observations in the held-out line; mean p 0.1967 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | M2_WF_SEL | 88 | 88 | 0 | 0 | 50 | 75 | COMPLETE | observations in the held-out line; mean p 0.3819 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | M2_WF_SEL | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.0764 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1111930 | M3_HYBRID | 34 | 34 | 0 | 0 | 18 | 19 | COMPLETE | observations in the held-out line; mean p 0.1814 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112140 | M3_HYBRID | 141 | 141 | 0 | 0 | 89 | 119 | COMPLETE | observations in the held-out line; mean p 0.4415 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112500 | M3_HYBRID | 115 | 115 | 0 | 0 | 42 | 63 | COMPLETE | observations in the held-out line; mean p 0.1967 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1112600 | M3_HYBRID | 88 | 88 | 0 | 0 | 50 | 75 | COMPLETE | observations in the held-out line; mean p 0.3819 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 2 | NOM_N1113000 | M3_HYBRID | 77 | 77 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.0764 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | BASE_LOGISTIC | 20 | 20 | 0 | 0 | 0 | 14 | COMPLETE | observations in the held-out line; mean p 0.4011 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | BASE_LOGISTIC | 99 | 99 | 0 | 0 | 43 | 72 | COMPLETE | observations in the held-out line; mean p 0.4886 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | BASE_LOGISTIC | 101 | 101 | 0 | 0 | 30 | 24 | COMPLETE | observations in the held-out line; mean p 0.2101 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | BASE_LOGISTIC | 71 | 71 | 0 | 0 | 43 | 22 | COMPLETE | observations in the held-out line; mean p 0.2584 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | BASE_LOGISTIC | 92 | 92 | 0 | 0 | 3 | 2 | COMPLETE | observations in the held-out line; mean p 0.0762 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | BASE_LOGISTIC_WF | 20 | 20 | 0 | 0 | 0 | 12 | COMPLETE | observations in the held-out line; mean p 0.4156 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | BASE_LOGISTIC_WF | 99 | 99 | 0 | 0 | 43 | 63 | COMPLETE | observations in the held-out line; mean p 0.4796 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | BASE_LOGISTIC_WF | 101 | 101 | 0 | 0 | 30 | 14 | COMPLETE | observations in the held-out line; mean p 0.1995 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | BASE_LOGISTIC_WF | 71 | 71 | 0 | 0 | 43 | 20 | COMPLETE | observations in the held-out line; mean p 0.2772 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | BASE_LOGISTIC_WF | 92 | 92 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.0765 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | BASE_PREVALENCE | 20 | 20 | 0 | 0 | 0 | 0 | COMPLETE | observations in the held-out line; mean p 0.2808 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | BASE_PREVALENCE | 99 | 99 | 0 | 0 | 43 | 0 | COMPLETE | observations in the held-out line; mean p 0.2808 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | BASE_PREVALENCE | 101 | 101 | 0 | 0 | 30 | 0 | COMPLETE | observations in the held-out line; mean p 0.2808 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | BASE_PREVALENCE | 71 | 71 | 0 | 0 | 43 | 0 | COMPLETE | observations in the held-out line; mean p 0.2808 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | BASE_PREVALENCE | 92 | 92 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.2808 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | M1_IK | 20 | 20 | 0 | 0 | 0 | 6 | COMPLETE | observations in the held-out line; mean p 0.2827 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | M1_IK | 99 | 99 | 0 | 0 | 43 | 68 | COMPLETE | observations in the held-out line; mean p 0.4488 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | M1_IK | 101 | 101 | 0 | 0 | 30 | 37 | COMPLETE | observations in the held-out line; mean p 0.2326 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | M1_IK | 71 | 71 | 0 | 0 | 43 | 37 | COMPLETE | observations in the held-out line; mean p 0.27 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | M1_IK | 92 | 92 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.0877 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | M2_HGB | 20 | 20 | 0 | 0 | 0 | 16 | COMPLETE | observations in the held-out line; mean p 0.334 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | M2_HGB | 99 | 99 | 0 | 0 | 43 | 89 | COMPLETE | observations in the held-out line; mean p 0.5296 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | M2_HGB | 101 | 101 | 0 | 0 | 30 | 78 | COMPLETE | observations in the held-out line; mean p 0.2529 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | M2_HGB | 71 | 71 | 0 | 0 | 43 | 57 | COMPLETE | observations in the held-out line; mean p 0.2247 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | M2_HGB | 92 | 92 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.0797 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | M2_HGB_WF | 20 | 20 | 0 | 0 | 0 | 14 | COMPLETE | observations in the held-out line; mean p 0.261 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | M2_HGB_WF | 99 | 99 | 0 | 0 | 43 | 79 | COMPLETE | observations in the held-out line; mean p 0.484 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | M2_HGB_WF | 101 | 101 | 0 | 0 | 30 | 59 | COMPLETE | observations in the held-out line; mean p 0.239 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | M2_HGB_WF | 71 | 71 | 0 | 0 | 43 | 56 | COMPLETE | observations in the held-out line; mean p 0.2413 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | M2_HGB_WF | 92 | 92 | 0 | 0 | 3 | 2 | COMPLETE | observations in the held-out line; mean p 0.095 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | M2_RF | 20 | 20 | 0 | 0 | 0 | 8 | COMPLETE | observations in the held-out line; mean p 0.2922 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | M2_RF | 99 | 99 | 0 | 0 | 43 | 72 | COMPLETE | observations in the held-out line; mean p 0.5482 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | M2_RF | 101 | 101 | 0 | 0 | 30 | 35 | COMPLETE | observations in the held-out line; mean p 0.2073 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | M2_RF | 71 | 71 | 0 | 0 | 43 | 15 | COMPLETE | observations in the held-out line; mean p 0.2234 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | M2_RF | 92 | 92 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.0701 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | M2_RF_WF | 20 | 20 | 0 | 0 | 0 | 9 | COMPLETE | observations in the held-out line; mean p 0.2287 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | M2_RF_WF | 99 | 99 | 0 | 0 | 43 | 80 | COMPLETE | observations in the held-out line; mean p 0.4523 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | M2_RF_WF | 101 | 101 | 0 | 0 | 30 | 49 | COMPLETE | observations in the held-out line; mean p 0.2172 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | M2_RF_WF | 71 | 71 | 0 | 0 | 43 | 48 | COMPLETE | observations in the held-out line; mean p 0.2293 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | M2_RF_WF | 92 | 92 | 0 | 0 | 3 | 10 | COMPLETE | observations in the held-out line; mean p 0.0991 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | M2_SEL | 20 | 20 | 0 | 0 | 0 | 8 | COMPLETE | observations in the held-out line; mean p 0.2922 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | M2_SEL | 99 | 99 | 0 | 0 | 43 | 72 | COMPLETE | observations in the held-out line; mean p 0.5482 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | M2_SEL | 101 | 101 | 0 | 0 | 30 | 35 | COMPLETE | observations in the held-out line; mean p 0.2073 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | M2_SEL | 71 | 71 | 0 | 0 | 43 | 15 | COMPLETE | observations in the held-out line; mean p 0.2234 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | M2_SEL | 92 | 92 | 0 | 0 | 3 | 0 | COMPLETE | observations in the held-out line; mean p 0.0701 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | M2_WF_SEL | 20 | 20 | 0 | 0 | 0 | 9 | COMPLETE | observations in the held-out line; mean p 0.2287 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | M2_WF_SEL | 99 | 99 | 0 | 0 | 43 | 80 | COMPLETE | observations in the held-out line; mean p 0.4523 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | M2_WF_SEL | 101 | 101 | 0 | 0 | 30 | 49 | COMPLETE | observations in the held-out line; mean p 0.2172 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | M2_WF_SEL | 71 | 71 | 0 | 0 | 43 | 48 | COMPLETE | observations in the held-out line; mean p 0.2293 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | M2_WF_SEL | 92 | 92 | 0 | 0 | 3 | 10 | COMPLETE | observations in the held-out line; mean p 0.0991 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1111930 | M3_HYBRID | 20 | 20 | 0 | 0 | 0 | 9 | COMPLETE | observations in the held-out line; mean p 0.2287 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112140 | M3_HYBRID | 99 | 99 | 0 | 0 | 43 | 80 | COMPLETE | observations in the held-out line; mean p 0.4523 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112500 | M3_HYBRID | 101 | 101 | 0 | 0 | 30 | 49 | COMPLETE | observations in the held-out line; mean p 0.2172 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1112600 | M3_HYBRID | 71 | 71 | 0 | 0 | 43 | 48 | COMPLETE | observations in the held-out line; mean p 0.2293 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 3 | NOM_N1113000 | M3_HYBRID | 92 | 92 | 0 | 0 | 3 | 10 | COMPLETE | observations in the held-out line; mean p 0.0991 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | BASE_LOGISTIC | 55 | 55 | 0 | 0 | 24 | 51 | COMPLETE | observations in the held-out line; mean p 0.4467 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | BASE_LOGISTIC | 87 | 87 | 0 | 0 | 16 | 32 | COMPLETE | observations in the held-out line; mean p 0.1868 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | BASE_LOGISTIC | 75 | 75 | 0 | 0 | 10 | 44 | COMPLETE | observations in the held-out line; mean p 0.2891 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | BASE_LOGISTIC | 86 | 86 | 0 | 0 | 4 | 14 | COMPLETE | observations in the held-out line; mean p 0.1153 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | BASE_LOGISTIC_WF | 55 | 55 | 0 | 0 | 24 | 50 | COMPLETE | observations in the held-out line; mean p 0.4644 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | BASE_LOGISTIC_WF | 87 | 87 | 0 | 0 | 16 | 30 | COMPLETE | observations in the held-out line; mean p 0.1853 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | BASE_LOGISTIC_WF | 75 | 75 | 0 | 0 | 10 | 48 | COMPLETE | observations in the held-out line; mean p 0.3137 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | BASE_LOGISTIC_WF | 86 | 86 | 0 | 0 | 4 | 12 | COMPLETE | observations in the held-out line; mean p 0.1077 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | BASE_PREVALENCE | 55 | 55 | 0 | 0 | 24 | 0 | COMPLETE | observations in the held-out line; mean p 0.3087 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | BASE_PREVALENCE | 87 | 87 | 0 | 0 | 16 | 0 | COMPLETE | observations in the held-out line; mean p 0.3087 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | BASE_PREVALENCE | 75 | 75 | 0 | 0 | 10 | 0 | COMPLETE | observations in the held-out line; mean p 0.3087 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | BASE_PREVALENCE | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.3087 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | M1_IK | 55 | 55 | 0 | 0 | 24 | 41 | COMPLETE | observations in the held-out line; mean p 0.4138 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | M1_IK | 87 | 87 | 0 | 0 | 16 | 37 | COMPLETE | observations in the held-out line; mean p 0.2691 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | M1_IK | 75 | 75 | 0 | 0 | 10 | 41 | COMPLETE | observations in the held-out line; mean p 0.3443 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | M1_IK | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.0973 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | M2_HGB | 55 | 55 | 0 | 0 | 24 | 11 | COMPLETE | observations in the held-out line; mean p 0.2473 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | M2_HGB | 87 | 87 | 0 | 0 | 16 | 39 | COMPLETE | observations in the held-out line; mean p 0.2825 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | M2_HGB | 75 | 75 | 0 | 0 | 10 | 56 | COMPLETE | observations in the held-out line; mean p 0.4143 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | M2_HGB | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.0655 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | M2_HGB_WF | 55 | 55 | 0 | 0 | 24 | 33 | COMPLETE | observations in the held-out line; mean p 0.3352 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | M2_HGB_WF | 87 | 87 | 0 | 0 | 16 | 37 | COMPLETE | observations in the held-out line; mean p 0.2664 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | M2_HGB_WF | 75 | 75 | 0 | 0 | 10 | 62 | COMPLETE | observations in the held-out line; mean p 0.4311 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | M2_HGB_WF | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.0991 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | M2_RF | 55 | 55 | 0 | 0 | 24 | 19 | COMPLETE | observations in the held-out line; mean p 0.2892 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | M2_RF | 87 | 87 | 0 | 0 | 16 | 39 | COMPLETE | observations in the held-out line; mean p 0.2673 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | M2_RF | 75 | 75 | 0 | 0 | 10 | 58 | COMPLETE | observations in the held-out line; mean p 0.4512 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | M2_RF | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.0718 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | M2_RF_WF | 55 | 55 | 0 | 0 | 24 | 39 | COMPLETE | observations in the held-out line; mean p 0.3826 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | M2_RF_WF | 87 | 87 | 0 | 0 | 16 | 37 | COMPLETE | observations in the held-out line; mean p 0.2457 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | M2_RF_WF | 75 | 75 | 0 | 0 | 10 | 63 | COMPLETE | observations in the held-out line; mean p 0.4376 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | M2_RF_WF | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.096 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | M2_SEL | 55 | 55 | 0 | 0 | 24 | 19 | COMPLETE | observations in the held-out line; mean p 0.2892 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | M2_SEL | 87 | 87 | 0 | 0 | 16 | 39 | COMPLETE | observations in the held-out line; mean p 0.2673 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | M2_SEL | 75 | 75 | 0 | 0 | 10 | 58 | COMPLETE | observations in the held-out line; mean p 0.4512 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | M2_SEL | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.0718 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | M2_WF_SEL | 55 | 55 | 0 | 0 | 24 | 39 | COMPLETE | observations in the held-out line; mean p 0.3826 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | M2_WF_SEL | 87 | 87 | 0 | 0 | 16 | 37 | COMPLETE | observations in the held-out line; mean p 0.2457 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | M2_WF_SEL | 75 | 75 | 0 | 0 | 10 | 63 | COMPLETE | observations in the held-out line; mean p 0.4376 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | M2_WF_SEL | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.096 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112140 | M3_HYBRID | 55 | 55 | 0 | 0 | 24 | 39 | COMPLETE | observations in the held-out line; mean p 0.3826 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112500 | M3_HYBRID | 87 | 87 | 0 | 0 | 16 | 37 | COMPLETE | observations in the held-out line; mean p 0.2457 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1112600 | M3_HYBRID | 75 | 75 | 0 | 0 | 10 | 63 | COMPLETE | observations in the held-out line; mean p 0.4376 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 4 | NOM_N1113000 | M3_HYBRID | 86 | 86 | 0 | 0 | 4 | 0 | COMPLETE | observations in the held-out line; mean p 0.096 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | BASE_LOGISTIC | 53 | 53 | 0 | 0 | 33 | 31 | COMPLETE | observations in the held-out line; mean p 0.4586 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | BASE_LOGISTIC | 106 | 106 | 0 | 0 | 22 | 26 | COMPLETE | observations in the held-out line; mean p 0.2316 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | BASE_LOGISTIC | 90 | 90 | 0 | 0 | 9 | 36 | COMPLETE | observations in the held-out line; mean p 0.3402 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | BASE_LOGISTIC | 56 | 56 | 0 | 0 | 6 | 0 | COMPLETE | observations in the held-out line; mean p 0.0893 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | BASE_LOGISTIC_WF | 53 | 53 | 0 | 0 | 33 | 46 | COMPLETE | observations in the held-out line; mean p 0.4613 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | BASE_LOGISTIC_WF | 106 | 106 | 0 | 0 | 22 | 46 | COMPLETE | observations in the held-out line; mean p 0.2283 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | BASE_LOGISTIC_WF | 90 | 90 | 0 | 0 | 9 | 57 | COMPLETE | observations in the held-out line; mean p 0.3507 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | BASE_LOGISTIC_WF | 56 | 56 | 0 | 0 | 6 | 5 | COMPLETE | observations in the held-out line; mean p 0.0876 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | BASE_PREVALENCE | 53 | 53 | 0 | 0 | 33 | 0 | COMPLETE | observations in the held-out line; mean p 0.2986 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | BASE_PREVALENCE | 106 | 106 | 0 | 0 | 22 | 0 | COMPLETE | observations in the held-out line; mean p 0.2986 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | BASE_PREVALENCE | 90 | 90 | 0 | 0 | 9 | 0 | COMPLETE | observations in the held-out line; mean p 0.2986 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | BASE_PREVALENCE | 56 | 56 | 0 | 0 | 6 | 0 | COMPLETE | observations in the held-out line; mean p 0.2986 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | M1_IK | 53 | 53 | 0 | 0 | 33 | 40 | COMPLETE | observations in the held-out line; mean p 0.432 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | M1_IK | 106 | 106 | 0 | 0 | 22 | 49 | COMPLETE | observations in the held-out line; mean p 0.2818 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | M1_IK | 90 | 90 | 0 | 0 | 9 | 40 | COMPLETE | observations in the held-out line; mean p 0.3399 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | M1_IK | 56 | 56 | 0 | 0 | 6 | 0 | COMPLETE | observations in the held-out line; mean p 0.0787 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | M2_HGB | 53 | 53 | 0 | 0 | 33 | 41 | COMPLETE | observations in the held-out line; mean p 0.4921 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | M2_HGB | 106 | 106 | 0 | 0 | 22 | 66 | COMPLETE | observations in the held-out line; mean p 0.3353 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | M2_HGB | 90 | 90 | 0 | 0 | 9 | 72 | COMPLETE | observations in the held-out line; mean p 0.3159 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | M2_HGB | 56 | 56 | 0 | 0 | 6 | 2 | COMPLETE | observations in the held-out line; mean p 0.0723 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | M2_HGB_WF | 53 | 53 | 0 | 0 | 33 | 51 | COMPLETE | observations in the held-out line; mean p 0.5212 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | M2_HGB_WF | 106 | 106 | 0 | 0 | 22 | 69 | COMPLETE | observations in the held-out line; mean p 0.3108 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | M2_HGB_WF | 90 | 90 | 0 | 0 | 9 | 75 | COMPLETE | observations in the held-out line; mean p 0.3136 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | M2_HGB_WF | 56 | 56 | 0 | 0 | 6 | 8 | COMPLETE | observations in the held-out line; mean p 0.0904 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | M2_RF | 53 | 53 | 0 | 0 | 33 | 43 | COMPLETE | observations in the held-out line; mean p 0.4937 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | M2_RF | 106 | 106 | 0 | 0 | 22 | 57 | COMPLETE | observations in the held-out line; mean p 0.2901 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | M2_RF | 90 | 90 | 0 | 0 | 9 | 59 | COMPLETE | observations in the held-out line; mean p 0.3333 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | M2_RF | 56 | 56 | 0 | 0 | 6 | 0 | COMPLETE | observations in the held-out line; mean p 0.0261 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | M2_RF_WF | 53 | 53 | 0 | 0 | 33 | 40 | COMPLETE | observations in the held-out line; mean p 0.4401 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | M2_RF_WF | 106 | 106 | 0 | 0 | 22 | 61 | COMPLETE | observations in the held-out line; mean p 0.2931 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | M2_RF_WF | 90 | 90 | 0 | 0 | 9 | 68 | COMPLETE | observations in the held-out line; mean p 0.3268 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | M2_RF_WF | 56 | 56 | 0 | 0 | 6 | 0 | COMPLETE | observations in the held-out line; mean p 0.0561 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | M2_SEL | 53 | 53 | 0 | 0 | 33 | 43 | COMPLETE | observations in the held-out line; mean p 0.4937 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | M2_SEL | 106 | 106 | 0 | 0 | 22 | 57 | COMPLETE | observations in the held-out line; mean p 0.2901 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | M2_SEL | 90 | 90 | 0 | 0 | 9 | 59 | COMPLETE | observations in the held-out line; mean p 0.3333 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | M2_SEL | 56 | 56 | 0 | 0 | 6 | 0 | COMPLETE | observations in the held-out line; mean p 0.0261 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | M2_WF_SEL | 53 | 53 | 0 | 0 | 33 | 40 | COMPLETE | observations in the held-out line; mean p 0.4401 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | M2_WF_SEL | 106 | 106 | 0 | 0 | 22 | 61 | COMPLETE | observations in the held-out line; mean p 0.2931 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | M2_WF_SEL | 90 | 90 | 0 | 0 | 9 | 68 | COMPLETE | observations in the held-out line; mean p 0.3268 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | M2_WF_SEL | 56 | 56 | 0 | 0 | 6 | 0 | COMPLETE | observations in the held-out line; mean p 0.0561 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112140 | M3_HYBRID | 53 | 53 | 0 | 0 | 33 | 40 | COMPLETE | observations in the held-out line; mean p 0.4401 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112500 | M3_HYBRID | 106 | 106 | 0 | 0 | 22 | 61 | COMPLETE | observations in the held-out line; mean p 0.2931 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1112600 | M3_HYBRID | 90 | 90 | 0 | 0 | 9 | 68 | COMPLETE | observations in the held-out line; mean p 0.3268 |
| LINE_FAMILY | O3-SPLIT-HOLE-IL-2 | 5 | NOM_N1113000 | M3_HYBRID | 56 | 56 | 0 | 0 | 6 | 0 | COMPLETE | observations in the held-out line; mean p 0.0561 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | BASE_LOGISTIC | 84 | 84 | 0 | 0 | 29 | 69 | COMPLETE | observations in the held-out line; mean p 0.5121 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | BASE_LOGISTIC_WF | 84 | 84 | 0 | 0 | 29 | 81 | COMPLETE | observations in the held-out line; mean p 0.5285 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | BASE_PREVALENCE | 84 | 84 | 0 | 0 | 29 | 0 | COMPLETE | observations in the held-out line; mean p 0.2842 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | M1_IK | 84 | 84 | 0 | 0 | 29 | 16 | COMPLETE | observations in the held-out line; mean p 0.2801 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | M2_HGB | 84 | 84 | 0 | 0 | 29 | 20 | COMPLETE | observations in the held-out line; mean p 0.1142 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | M2_HGB_WF | 84 | 84 | 0 | 0 | 29 | 36 | COMPLETE | observations in the held-out line; mean p 0.1236 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | M2_RF | 84 | 84 | 0 | 0 | 29 | 42 | COMPLETE | observations in the held-out line; mean p 0.2142 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | M2_RF_WF | 84 | 84 | 0 | 0 | 29 | 39 | COMPLETE | observations in the held-out line; mean p 0.1937 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | M2_SEL | 84 | 84 | 0 | 0 | 29 | 42 | COMPLETE | observations in the held-out line; mean p 0.2142 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | M2_WF_SEL | 84 | 84 | 0 | 0 | 29 | 39 | COMPLETE | observations in the held-out line; mean p 0.1937 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 1 | NOM_N1111930 | M3_HYBRID | 84 | 84 | 0 | 0 | 29 | 39 | COMPLETE | observations in the held-out line; mean p 0.1937 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | BASE_LOGISTIC | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.4735 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | BASE_LOGISTIC_WF | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.4752 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | BASE_PREVALENCE | 429 | 429 | 0 | 0 | 217 | 0 | COMPLETE | observations in the held-out line; mean p 0.22 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | M1_IK | 429 | 429 | 0 | 0 | 217 | 304 | COMPLETE | observations in the held-out line; mean p 0.22 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | M2_HGB | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.4358 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | M2_HGB_WF | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.4538 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | M2_RF | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.3982 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | M2_RF_WF | 429 | 429 | 0 | 0 | 217 | 365 | COMPLETE | observations in the held-out line; mean p 0.4031 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | M2_SEL | 429 | 429 | 0 | 0 | 217 | 429 | COMPLETE | observations in the held-out line; mean p 0.3982 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | M2_WF_SEL | 429 | 429 | 0 | 0 | 217 | 365 | COMPLETE | observations in the held-out line; mean p 0.4031 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 2 | NOM_N1112140 | M3_HYBRID | 429 | 429 | 0 | 0 | 217 | 365 | COMPLETE | observations in the held-out line; mean p 0.4031 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | BASE_LOGISTIC | 528 | 528 | 0 | 0 | 130 | 43 | COMPLETE | observations in the held-out line; mean p 0.1415 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | BASE_LOGISTIC_WF | 528 | 528 | 0 | 0 | 130 | 44 | COMPLETE | observations in the held-out line; mean p 0.1422 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | BASE_PREVALENCE | 528 | 528 | 0 | 0 | 130 | 0 | COMPLETE | observations in the held-out line; mean p 0.3036 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | M1_IK | 528 | 528 | 0 | 0 | 130 | 1 | COMPLETE | observations in the held-out line; mean p 0.2945 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | M2_HGB | 528 | 528 | 0 | 0 | 130 | 486 | COMPLETE | observations in the held-out line; mean p 0.2093 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | M2_HGB_WF | 528 | 528 | 0 | 0 | 130 | 438 | COMPLETE | observations in the held-out line; mean p 0.2062 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | M2_RF | 528 | 528 | 0 | 0 | 130 | 256 | COMPLETE | observations in the held-out line; mean p 0.2397 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | M2_RF_WF | 528 | 528 | 0 | 0 | 130 | 408 | COMPLETE | observations in the held-out line; mean p 0.2693 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | M2_SEL | 528 | 528 | 0 | 0 | 130 | 256 | COMPLETE | observations in the held-out line; mean p 0.2397 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | M2_WF_SEL | 528 | 528 | 0 | 0 | 130 | 408 | COMPLETE | observations in the held-out line; mean p 0.2693 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 3 | NOM_N1112500 | M3_HYBRID | 528 | 528 | 0 | 0 | 130 | 408 | COMPLETE | observations in the held-out line; mean p 0.2693 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | BASE_LOGISTIC | 401 | 401 | 0 | 0 | 133 | 186 | COMPLETE | observations in the held-out line; mean p 0.2547 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | BASE_LOGISTIC_WF | 401 | 401 | 0 | 0 | 133 | 163 | COMPLETE | observations in the held-out line; mean p 0.2346 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | BASE_PREVALENCE | 401 | 401 | 0 | 0 | 133 | 0 | COMPLETE | observations in the held-out line; mean p 0.2745 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | M1_IK | 401 | 401 | 0 | 0 | 133 | 257 | COMPLETE | observations in the held-out line; mean p 0.2772 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | M2_HGB | 401 | 401 | 0 | 0 | 133 | 216 | COMPLETE | observations in the held-out line; mean p 0.2258 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | M2_HGB_WF | 401 | 401 | 0 | 0 | 133 | 260 | COMPLETE | observations in the held-out line; mean p 0.2317 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | M2_RF | 401 | 401 | 0 | 0 | 133 | 249 | COMPLETE | observations in the held-out line; mean p 0.3687 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | M2_RF_WF | 401 | 401 | 0 | 0 | 133 | 220 | COMPLETE | observations in the held-out line; mean p 0.3027 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | M2_SEL | 401 | 401 | 0 | 0 | 133 | 249 | COMPLETE | observations in the held-out line; mean p 0.3687 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | M2_WF_SEL | 401 | 401 | 0 | 0 | 133 | 220 | COMPLETE | observations in the held-out line; mean p 0.3027 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 4 | NOM_N1112600 | M3_HYBRID | 401 | 401 | 0 | 0 | 133 | 220 | COMPLETE | observations in the held-out line; mean p 0.3027 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | BASE_LOGISTIC | 387 | 387 | 0 | 0 | 16 | 17 | COMPLETE | observations in the held-out line; mean p 0.1442 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | BASE_LOGISTIC_WF | 387 | 387 | 0 | 0 | 16 | 11 | COMPLETE | observations in the held-out line; mean p 0.1561 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | BASE_PREVALENCE | 387 | 387 | 0 | 0 | 16 | 0 | COMPLETE | observations in the held-out line; mean p 0.353 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | M1_IK | 387 | 387 | 0 | 0 | 16 | 110 | COMPLETE | observations in the held-out line; mean p 0.3484 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | M2_HGB | 387 | 387 | 0 | 0 | 16 | 117 | COMPLETE | observations in the held-out line; mean p 0.2054 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | M2_HGB_WF | 387 | 387 | 0 | 0 | 16 | 0 | COMPLETE | observations in the held-out line; mean p 0.1707 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | M2_RF | 387 | 387 | 0 | 0 | 16 | 4 | COMPLETE | observations in the held-out line; mean p 0.171 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | M2_RF_WF | 387 | 387 | 0 | 0 | 16 | 35 | COMPLETE | observations in the held-out line; mean p 0.1911 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | M2_SEL | 387 | 387 | 0 | 0 | 16 | 4 | COMPLETE | observations in the held-out line; mean p 0.171 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | M2_WF_SEL | 387 | 387 | 0 | 0 | 16 | 35 | COMPLETE | observations in the held-out line; mean p 0.1911 |
| LINE_FAMILY | O3-SPLIT-LODO-1 | 5 | NOM_N1113000 | M3_HYBRID | 387 | 387 | 0 | 0 | 16 | 35 | COMPLETE | observations in the held-out line; mean p 0.1911 |

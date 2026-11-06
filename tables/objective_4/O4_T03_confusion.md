# O4-T03. Confusion matrices and threshold provenance

The pooled matrix sums the fold-specific confusion counts; the threshold is therefore NULL and the source records that the fold-specific thresholds were summed.
Source: sql/objective_4/tables/O4-T03.sql, receipt 1, 66 rows.

| model_id | scope | fold_id | threshold | threshold_source | tp | fp | tn | fn | precision | recall | specificity | balanced_accuracy | f1 | mcc | status | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE_LOGISTIC | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 339 | 405 | 899 | 186 | 0.455645 | 0.645714 | 0.689417 | 0.667566 | 0.534279 | 0.308626 | DEFINED | all rates defined |
| BASE_LOGISTIC | FOLD | 1 | 0.3 | O3_TRAINING_ONLY_THRESHOLD | 29 | 40 | 15 | 0 | 0.42029 | 1 | 0.272727 | 0.636364 | 0.591837 | 0.338562 | DEFINED | all rates defined |
| BASE_LOGISTIC | FOLD | 2 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 217 | 212 | 0 | 0 | 0.505828 | 1 | 0 | 0.5 | 0.671827 |  | UNDEFINED | undefined rates: mcc |
| BASE_LOGISTIC | FOLD | 3 | 0.3 | O3_TRAINING_ONLY_THRESHOLD | 19 | 24 | 374 | 111 | 0.44186 | 0.146154 | 0.939698 | 0.542926 | 0.219653 | 0.135226 | DEFINED | all rates defined |
| BASE_LOGISTIC | FOLD | 4 | 0.2 | O3_TRAINING_ONLY_THRESHOLD | 74 | 112 | 156 | 59 | 0.397849 | 0.556391 | 0.58209 | 0.56924 | 0.46395 | 0.130739 | DEFINED | all rates defined |
| BASE_LOGISTIC | FOLD | 5 | 0.35 | O3_TRAINING_ONLY_THRESHOLD | 0 | 17 | 354 | 16 | 0 | 0 | 0.954178 | 0.477089 |  | -0.044514 | UNDEFINED | undefined rates: f1 |
| BASE_LOGISTIC_WF | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 334 | 394 | 910 | 191 | 0.458791 | 0.63619 | 0.697853 | 0.667022 | 0.533121 | 0.308718 | DEFINED | all rates defined |
| BASE_LOGISTIC_WF | FOLD | 1 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 29 | 52 | 3 | 0 | 0.358025 | 1 | 0.054545 | 0.527273 | 0.527273 | 0.139745 | DEFINED | all rates defined |
| BASE_LOGISTIC_WF | FOLD | 2 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 217 | 212 | 0 | 0 | 0.505828 | 1 | 0 | 0.5 | 0.671827 |  | UNDEFINED | undefined rates: mcc |
| BASE_LOGISTIC_WF | FOLD | 3 | 0.3 | O3_TRAINING_ONLY_THRESHOLD | 20 | 24 | 374 | 110 | 0.454545 | 0.153846 | 0.939698 | 0.546772 | 0.229885 | 0.145809 | DEFINED | all rates defined |
| BASE_LOGISTIC_WF | FOLD | 4 | 0.2 | O3_TRAINING_ONLY_THRESHOLD | 68 | 95 | 173 | 65 | 0.417178 | 0.511278 | 0.645522 | 0.5784 | 0.459459 | 0.1503 | DEFINED | all rates defined |
| BASE_LOGISTIC_WF | FOLD | 5 | 0.35 | O3_TRAINING_ONLY_THRESHOLD | 0 | 11 | 360 | 16 | 0 | 0 | 0.97035 | 0.485175 |  | -0.03552 | UNDEFINED | undefined rates: f1 |
| BASE_PREVALENCE | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 0 | 0 | 1304 | 525 |  | 0 | 1 | 0.5 |  |  | UNDEFINED | undefined rates: precision, f1, mcc |
| BASE_PREVALENCE | FOLD | 1 | 0.5 | O3_TRAINING_ONLY_THRESHOLD | 0 | 0 | 55 | 29 |  | 0 | 1 | 0.5 |  |  | UNDEFINED | undefined rates: precision, f1, mcc |
| BASE_PREVALENCE | FOLD | 2 | 0.5 | O3_TRAINING_ONLY_THRESHOLD | 0 | 0 | 212 | 217 |  | 0 | 1 | 0.5 |  |  | UNDEFINED | undefined rates: precision, f1, mcc |
| BASE_PREVALENCE | FOLD | 3 | 0.5 | O3_TRAINING_ONLY_THRESHOLD | 0 | 0 | 398 | 130 |  | 0 | 1 | 0.5 |  |  | UNDEFINED | undefined rates: precision, f1, mcc |
| BASE_PREVALENCE | FOLD | 4 | 0.5 | O3_TRAINING_ONLY_THRESHOLD | 0 | 0 | 268 | 133 |  | 0 | 1 | 0.5 |  |  | UNDEFINED | undefined rates: precision, f1, mcc |
| BASE_PREVALENCE | FOLD | 5 | 0.5 | O3_TRAINING_ONLY_THRESHOLD | 0 | 0 | 371 | 16 |  | 0 | 1 | 0.5 |  |  | UNDEFINED | undefined rates: precision, f1, mcc |
| M1_IK | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 325 | 363 | 941 | 200 | 0.472384 | 0.619048 | 0.721626 | 0.670337 | 0.535862 | 0.318141 | DEFINED | all rates defined |
| M1_IK | FOLD | 1 | 0.284241 | O3_TRAINING_ONLY_THRESHOLD | 12 | 4 | 51 | 17 | 0.75 | 0.413793 | 0.927273 | 0.670533 | 0.533333 | 0.412956 | DEFINED | all rates defined |
| M1_IK | FOLD | 2 | 0.22 | O3_TRAINING_ONLY_THRESHOLD | 199 | 105 | 107 | 18 | 0.654605 | 0.917051 | 0.504717 | 0.710884 | 0.763916 | 0.464066 | DEFINED | all rates defined |
| M1_IK | FOLD | 3 | 0.303613 | O3_TRAINING_ONLY_THRESHOLD | 0 | 1 | 397 | 130 | 0 | 0 | 0.997487 | 0.498744 |  | -0.024896 | UNDEFINED | undefined rates: f1 |
| M1_IK | FOLD | 4 | 0.27451 | O3_TRAINING_ONLY_THRESHOLD | 102 | 155 | 113 | 31 | 0.396887 | 0.766917 | 0.421642 | 0.59428 | 0.523077 | 0.185052 | DEFINED | all rates defined |
| M1_IK | FOLD | 5 | 0.352982 | O3_TRAINING_ONLY_THRESHOLD | 12 | 98 | 273 | 4 | 0.109091 | 0.75 | 0.735849 | 0.742925 | 0.190476 | 0.214443 | DEFINED | all rates defined |
| M2_HGB | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 459 | 809 | 495 | 66 | 0.361987 | 0.874286 | 0.379601 | 0.626943 | 0.511991 | 0.249068 | DEFINED | all rates defined |
| M2_HGB | FOLD | 1 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 15 | 5 | 50 | 14 | 0.75 | 0.517241 | 0.909091 | 0.713166 | 0.612245 | 0.475909 | DEFINED | all rates defined |
| M2_HGB | FOLD | 2 | 0.05 | O3_TRAINING_ONLY_THRESHOLD | 217 | 212 | 0 | 0 | 0.505828 | 1 | 0 | 0.5 | 0.671827 |  | UNDEFINED | undefined rates: mcc |
| M2_HGB | FOLD | 3 | 0.1 | O3_TRAINING_ONLY_THRESHOLD | 130 | 356 | 42 | 0 | 0.26749 | 1 | 0.105528 | 0.552764 | 0.422078 | 0.168011 | DEFINED | all rates defined |
| M2_HGB | FOLD | 4 | 0.2 | O3_TRAINING_ONLY_THRESHOLD | 84 | 132 | 136 | 49 | 0.388889 | 0.631579 | 0.507463 | 0.569521 | 0.481375 | 0.131318 | DEFINED | all rates defined |
| M2_HGB | FOLD | 5 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 13 | 104 | 267 | 3 | 0.111111 | 0.8125 | 0.719677 | 0.766088 | 0.195489 | 0.23069 | DEFINED | all rates defined |
| M2_HGB_WF | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 473 | 690 | 614 | 52 | 0.406707 | 0.900952 | 0.470859 | 0.685906 | 0.560427 | 0.349554 | DEFINED | all rates defined |
| M2_HGB_WF | FOLD | 1 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 23 | 13 | 42 | 6 | 0.638889 | 0.793103 | 0.763636 | 0.77837 | 0.707692 | 0.534885 | DEFINED | all rates defined |
| M2_HGB_WF | FOLD | 2 | 0.05 | O3_TRAINING_ONLY_THRESHOLD | 217 | 212 | 0 | 0 | 0.505828 | 1 | 0 | 0.5 | 0.671827 |  | UNDEFINED | undefined rates: mcc |
| M2_HGB_WF | FOLD | 3 | 0.1 | O3_TRAINING_ONLY_THRESHOLD | 130 | 308 | 90 | 0 | 0.296804 | 1 | 0.226131 | 0.613065 | 0.457746 | 0.259068 | DEFINED | all rates defined |
| M2_HGB_WF | FOLD | 4 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 103 | 157 | 111 | 30 | 0.396154 | 0.774436 | 0.414179 | 0.594308 | 0.524173 | 0.185983 | DEFINED | all rates defined |
| M2_HGB_WF | FOLD | 5 | 0.4 | O3_TRAINING_ONLY_THRESHOLD | 0 | 0 | 371 | 16 |  | 0 | 1 | 0.5 |  |  | UNDEFINED | undefined rates: precision, f1, mcc |
| M2_RF | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 444 | 536 | 768 | 81 | 0.453061 | 0.845714 | 0.588957 | 0.717336 | 0.590033 | 0.394287 | DEFINED | all rates defined |
| M2_RF | FOLD | 1 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 25 | 17 | 38 | 4 | 0.595238 | 0.862069 | 0.690909 | 0.776489 | 0.704225 | 0.525822 | DEFINED | all rates defined |
| M2_RF | FOLD | 2 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 217 | 212 | 0 | 0 | 0.505828 | 1 | 0 | 0.5 | 0.671827 |  | UNDEFINED | undefined rates: mcc |
| M2_RF | FOLD | 3 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 104 | 152 | 246 | 26 | 0.40625 | 0.8 | 0.61809 | 0.709045 | 0.53886 | 0.360395 | DEFINED | all rates defined |
| M2_RF | FOLD | 4 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 98 | 151 | 117 | 35 | 0.393574 | 0.736842 | 0.436567 | 0.586705 | 0.513089 | 0.168284 | DEFINED | all rates defined |
| M2_RF | FOLD | 5 | 0.35 | O3_TRAINING_ONLY_THRESHOLD | 0 | 4 | 367 | 16 | 0 | 0 | 0.989218 | 0.494609 |  | -0.021223 | UNDEFINED | undefined rates: f1 |
| M2_RF_WF | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 454 | 613 | 691 | 71 | 0.425492 | 0.864762 | 0.529908 | 0.697335 | 0.570352 | 0.362154 | DEFINED | all rates defined |
| M2_RF_WF | FOLD | 1 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 24 | 15 | 40 | 5 | 0.615385 | 0.827586 | 0.727273 | 0.777429 | 0.705882 | 0.528962 | DEFINED | all rates defined |
| M2_RF_WF | FOLD | 2 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 211 | 154 | 58 | 6 | 0.578082 | 0.97235 | 0.273585 | 0.622968 | 0.725086 | 0.345129 | DEFINED | all rates defined |
| M2_RF_WF | FOLD | 3 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 130 | 278 | 120 | 0 | 0.318627 | 1 | 0.301508 | 0.650754 | 0.483271 | 0.309949 | DEFINED | all rates defined |
| M2_RF_WF | FOLD | 4 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 85 | 135 | 133 | 48 | 0.386364 | 0.639098 | 0.496269 | 0.567683 | 0.481586 | 0.128072 | DEFINED | all rates defined |
| M2_RF_WF | FOLD | 5 | 0.35 | O3_TRAINING_ONLY_THRESHOLD | 4 | 31 | 340 | 12 | 0.114286 | 0.25 | 0.916442 | 0.583221 | 0.156863 | 0.115533 | DEFINED | all rates defined |
| M2_SEL | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 444 | 536 | 768 | 81 | 0.453061 | 0.845714 | 0.588957 | 0.717336 | 0.590033 | 0.394287 | DEFINED | all rates defined |
| M2_SEL | FOLD | 1 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 25 | 17 | 38 | 4 | 0.595238 | 0.862069 | 0.690909 | 0.776489 | 0.704225 | 0.525822 | DEFINED | all rates defined |
| M2_SEL | FOLD | 2 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 217 | 212 | 0 | 0 | 0.505828 | 1 | 0 | 0.5 | 0.671827 |  | UNDEFINED | undefined rates: mcc |
| M2_SEL | FOLD | 3 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 104 | 152 | 246 | 26 | 0.40625 | 0.8 | 0.61809 | 0.709045 | 0.53886 | 0.360395 | DEFINED | all rates defined |
| M2_SEL | FOLD | 4 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 98 | 151 | 117 | 35 | 0.393574 | 0.736842 | 0.436567 | 0.586705 | 0.513089 | 0.168284 | DEFINED | all rates defined |
| M2_SEL | FOLD | 5 | 0.35 | O3_TRAINING_ONLY_THRESHOLD | 0 | 4 | 367 | 16 | 0 | 0 | 0.989218 | 0.494609 |  | -0.021223 | UNDEFINED | undefined rates: f1 |
| M2_WF_SEL | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 454 | 613 | 691 | 71 | 0.425492 | 0.864762 | 0.529908 | 0.697335 | 0.570352 | 0.362154 | DEFINED | all rates defined |
| M2_WF_SEL | FOLD | 1 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 24 | 15 | 40 | 5 | 0.615385 | 0.827586 | 0.727273 | 0.777429 | 0.705882 | 0.528962 | DEFINED | all rates defined |
| M2_WF_SEL | FOLD | 2 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 211 | 154 | 58 | 6 | 0.578082 | 0.97235 | 0.273585 | 0.622968 | 0.725086 | 0.345129 | DEFINED | all rates defined |
| M2_WF_SEL | FOLD | 3 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 130 | 278 | 120 | 0 | 0.318627 | 1 | 0.301508 | 0.650754 | 0.483271 | 0.309949 | DEFINED | all rates defined |
| M2_WF_SEL | FOLD | 4 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 85 | 135 | 133 | 48 | 0.386364 | 0.639098 | 0.496269 | 0.567683 | 0.481586 | 0.128072 | DEFINED | all rates defined |
| M2_WF_SEL | FOLD | 5 | 0.35 | O3_TRAINING_ONLY_THRESHOLD | 4 | 31 | 340 | 12 | 0.114286 | 0.25 | 0.916442 | 0.583221 | 0.156863 | 0.115533 | DEFINED | all rates defined |
| M3_HYBRID | POOLED | 0 |  | O3_FOLD_SPECIFIC_THRESHOLDS_SUMMED | 454 | 613 | 691 | 71 | 0.425492 | 0.864762 | 0.529908 | 0.697335 | 0.570352 | 0.362154 | DEFINED | all rates defined |
| M3_HYBRID | FOLD | 1 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 24 | 15 | 40 | 5 | 0.615385 | 0.827586 | 0.727273 | 0.777429 | 0.705882 | 0.528962 | DEFINED | all rates defined |
| M3_HYBRID | FOLD | 2 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 211 | 154 | 58 | 6 | 0.578082 | 0.97235 | 0.273585 | 0.622968 | 0.725086 | 0.345129 | DEFINED | all rates defined |
| M3_HYBRID | FOLD | 3 | 0.15 | O3_TRAINING_ONLY_THRESHOLD | 130 | 278 | 120 | 0 | 0.318627 | 1 | 0.301508 | 0.650754 | 0.483271 | 0.309949 | DEFINED | all rates defined |
| M3_HYBRID | FOLD | 4 | 0.25 | O3_TRAINING_ONLY_THRESHOLD | 85 | 135 | 133 | 48 | 0.386364 | 0.639098 | 0.496269 | 0.567683 | 0.481586 | 0.128072 | DEFINED | all rates defined |
| M3_HYBRID | FOLD | 5 | 0.35 | O3_TRAINING_ONLY_THRESHOLD | 4 | 31 | 340 | 12 | 0.114286 | 0.25 | 0.916442 | 0.583221 | 0.156863 | 0.115533 | DEFINED | all rates defined |

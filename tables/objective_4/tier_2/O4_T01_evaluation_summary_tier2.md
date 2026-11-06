# O4-T01. Main evaluation summary

Brier is the primary endpoint; the equal-hole weighting is a sensitivity analysis. Coverage is the share of held-out intervals with a prediction. identity_status marks a model whose calibrated predictions equal an earlier feasible model's on every common interval (identical_to names it); identical models are not ranked.
Source: sql/objective_4/tables/O4-T01.sql, receipt 1, 11 rows.

| model_id | role | comparable | identity_status | identical_to | coverage | n_predicted | n_expected | n_failed | brier_interval | brier_equal_hole | log_loss_interval | roc_auc | pr_auc | ece | calibration_intercept | calibration_slope | calibration_status | decision_rank | improvement_status | selection_basis |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M2_HGB_WF | M2 | 1 | DISTINCT |  | 1 | 1829 | 1829 | 0 | 0.153063 | 0.139071 | 0.461357 | 0.814162 | 0.6221 | 0.048039 | 0.121931 | 1.170599 | DEFINED | 1 | INCONCLUSIVE | POINT_ESTIMATE_WITH_CAVEAT |
| M2_HGB | M2 | 1 | DISTINCT |  | 1 | 1829 | 1829 | 0 | 0.154827 | 0.140921 | 0.468376 | 0.811309 | 0.622919 | 0.059613 | 0.087819 | 1.079429 | DEFINED | 2 | INCONCLUSIVE | NOT_SELECTED |
| BASE_LOGISTIC | BASELINE | 1 | DISTINCT |  | 1 | 1829 | 1829 | 0 | 0.15942 | 0.146138 | 0.481317 | 0.786004 | 0.627496 | 0.041851 | 0.003012 | 0.978341 | DEFINED | 3 | INCONCLUSIVE | NOT_SELECTED |
| M2_RF | M2 | 1 | DISTINCT |  | 1 | 1829 | 1829 | 0 | 0.16184 | 0.146977 | 0.48174 | 0.790342 | 0.582982 | 0.047371 | -0.002164 | 0.906268 | DEFINED | 4 | NO_IMPROVEMENT | NOT_SELECTED |
| BASE_LOGISTIC_WF | BASELINE | 1 | DISTINCT |  | 1 | 1829 | 1829 | 0 | 0.162646 | 0.148084 | 0.489432 | 0.783073 | 0.592853 | 0.026994 | 0.057442 | 1.019717 | DEFINED | 5 | INCONCLUSIVE | NOT_SELECTED |
| M2_RF_WF | M2 | 1 | DISTINCT |  | 1 | 1829 | 1829 | 0 | 0.162769 | 0.146938 | 0.481505 | 0.791049 | 0.561357 | 0.066507 | 0.064473 | 0.971668 | DEFINED | 6 | NO_IMPROVEMENT | NOT_SELECTED |
| M1_IK | M1 | 1 | DISTINCT |  | 1 | 1829 | 1829 | 0 | 0.175954 | 0.154213 | 0.516587 | 0.755858 | 0.481416 | 0.054696 | -0.085588 | 0.800734 | DEFINED | 7 | NO_IMPROVEMENT | NOT_SELECTED |
| BASE_PREVALENCE | BASELINE | 1 | DISTINCT |  | 1 | 1829 | 1829 | 0 | 0.21078 | 0.187689 | 0.615054 | 0.372593 | 0.240337 | 0.084769 | -3.899234 | -3.154363 | DEFINED | 8 | NO_IMPROVEMENT | NOT_SELECTED |
| M2_SEL | M2 | 0 | IDENTICAL_TO | M2_RF | 1 | 1829 | 1829 | 0 | 0.16184 | 0.146977 | 0.48174 | 0.790342 | 0.582982 | 0.047371 | -0.002164 | 0.906268 | DEFINED |  | NOT_COMPARABLE | NOT_RANKED |
| M2_WF_SEL | M2 | 0 | IDENTICAL_TO | M2_RF_WF | 1 | 1829 | 1829 | 0 | 0.162769 | 0.146938 | 0.481505 | 0.791049 | 0.561357 | 0.066507 | 0.064473 | 0.971668 | DEFINED |  | NOT_COMPARABLE | NOT_RANKED |
| M3_HYBRID | M3 | 0 | IDENTICAL_TO | M2_WF_SEL | 1 | 1829 | 1829 | 0 | 0.162769 | 0.146938 | 0.481505 | 0.791049 | 0.561357 | 0.066507 | 0.064473 | 0.971668 | DEFINED |  | NOT_COMPARABLE | NOT_RANKED |

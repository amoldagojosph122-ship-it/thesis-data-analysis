# O5-T03. Validated skill carried from Objective 4 beside the class counts

Pooled interval-weighted Brier and ROC-AUC are Objective 4 values, carried without recomputation. The interval is the Objective 4 hole-cluster interval of the Brier difference (selected minus runner-up).
Source: sql/objective_5/tables/O5-T03.sql, receipt 1, 2 rows.

| validation_tier | zone | selected_model | selected_pooled_brier | selected_pooled_roc_auc | runner_up_model | runner_up_pooled_brier | runner_up_pooled_roc_auc | delta_brier_selected_minus_runner_up | delta_ci_low | delta_ci_high | improvement_status | confident_present_cells | confident_absent_cells | uncertain_cells | cells |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TIER_2_INTERPOLATION | INTERPOLATION | M2_HGB_WF | 0.153063 | 0.814162 | M2_HGB | 0.154827 | 0.811309 | -0.001764 | -0.006949 | 0.002869 | INCONCLUSIVE | 972 | 8977 | 18051 | 28000 |
| TIER_1_EXTRAPOLATION | EXTRAPOLATION | BASE_LOGISTIC_WF | 0.16507 | 0.748707 | M2_RF | 0.165515 | 0.781648 | -0.000445 | -0.013957 | 0.013737 | INCONCLUSIVE | 28868 | 221295 | 579029 | 829192 |

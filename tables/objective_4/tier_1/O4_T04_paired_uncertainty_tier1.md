# O4-T04. Paired difference uncertainty and weighting sensitivity

Sign convention: difference = Brier(model_b) minus Brier(model_a); negative means model_b has the lower Brier. power_label: RESOLVED when the 95% hole-cluster interval excludes zero; UNRESOLVED when it includes zero, with detectable_half_width the smallest difference this design could have detected; IDENTICAL when the two models are the same predictions (no interval). The line-level interval is a sensitivity analysis.
Source: sql/objective_4/tables/O4-T04.sql, receipt 1, 18 rows.

| pair_id | model_a | model_b | weighting | delta_brier_b_minus_a | delta_log_loss_b_minus_a | ci_low_hole | ci_high_hole | ci_low_line | ci_high_line | power_label | detectable_half_width | folds_b_better | n | status | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HGB_vs_HGBWF | M2_HGB | M2_HGB_WF | EQUAL_HOLE | -0.005771 | -0.017582 |  |  |  |  |  |  | 5 | 1829 | DEFINED | both models defined on this subset |
| HGB_vs_HGBWF | M2_HGB | M2_HGB_WF | INTERVAL | -0.005764 | -0.01531 | -0.008715 | -0.003039 | -0.011104 | -0.001417 | RESOLVED |  | 5 | 1829 | DEFINED | both models defined on this subset |
| LOG_vs_LOGWF | BASE_LOGISTIC | BASE_LOGISTIC_WF | EQUAL_HOLE | 0.000008 | 0.003996 |  |  |  |  |  |  | 2 | 1829 | DEFINED | both models defined on this subset |
| LOG_vs_LOGWF | BASE_LOGISTIC | BASE_LOGISTIC_WF | INTERVAL | -0.000747 | 0.001109 | -0.002704 | 0.001247 | -0.003482 | 0.001968 | UNRESOLVED | 0.001975 | 3 | 1829 | DEFINED | both models defined on this subset |
| LOG_vs_RF | BASE_LOGISTIC | M2_RF | EQUAL_HOLE | -0.000518 | -0.002974 |  |  |  |  |  |  | 3 | 1829 | DEFINED | both models defined on this subset |
| LOG_vs_RF | BASE_LOGISTIC | M2_RF | INTERVAL | -0.000302 | -0.00584 | -0.013688 | 0.011983 | -0.010218 | 0.013111 | UNRESOLVED | 0.012836 | 3 | 1829 | DEFINED | both models defined on this subset |
| M2SEL_vs_M2WFSEL | M2_SEL | M2_WF_SEL | EQUAL_HOLE | 0.002575 | 0.020634 |  |  |  |  |  |  | 2 | 1829 | DEFINED | both models defined on this subset |
| M2SEL_vs_M2WFSEL | M2_SEL | M2_WF_SEL | INTERVAL | 0.002202 | 0.018185 | -0.003522 | 0.007828 | -0.003086 | 0.008062 | UNRESOLVED | 0.005675 | 1 | 1829 | DEFINED | both models defined on this subset |
| M2WFSEL_vs_M3 | M2_WF_SEL | M3_HYBRID | EQUAL_HOLE | 0 | 0 |  |  |  |  |  |  | 0 | 1829 | IDENTICAL | identical predictions on every common observation; no interval |
| M2WFSEL_vs_M3 | M2_WF_SEL | M3_HYBRID | INTERVAL | 0 | 0 |  |  |  |  | IDENTICAL |  | 0 | 1829 | IDENTICAL | identical predictions on every common observation; no interval |
| PREV_vs_M1 | BASE_PREVALENCE | M1_IK | EQUAL_HOLE | -0.002063 | -0.004807 |  |  |  |  |  |  | 5 | 1829 | DEFINED | both models defined on this subset |
| PREV_vs_M1 | BASE_PREVALENCE | M1_IK | INTERVAL | -0.001748 | -0.004102 | -0.002533 | -0.000909 | -0.002791 | -0.000584 | RESOLVED |  | 5 | 1829 | DEFINED | both models defined on this subset |
| PREV_vs_M2SEL | BASE_PREVALENCE | M2_SEL | EQUAL_HOLE | -0.048575 | -0.125118 |  |  |  |  |  |  | 4 | 1829 | DEFINED | both models defined on this subset |
| PREV_vs_M2SEL | BASE_PREVALENCE | M2_SEL | INTERVAL | -0.05561 | -0.138767 | -0.081147 | -0.031441 | -0.106003 | -0.013305 | RESOLVED |  | 4 | 1829 | DEFINED | both models defined on this subset |
| RF_vs_HGB | M2_RF | M2_HGB | EQUAL_HOLE | 0.005441 | 0.024545 |  |  |  |  |  |  | 1 | 1829 | DEFINED | both models defined on this subset |
| RF_vs_HGB | M2_RF | M2_HGB | INTERVAL | 0.005965 | 0.023587 | -0.005874 | 0.017428 | 0.000161 | 0.018511 | UNRESOLVED | 0.011651 | 1 | 1829 | DEFINED | both models defined on this subset |
| RF_vs_RFWF | M2_RF | M2_RF_WF | EQUAL_HOLE | 0.002575 | 0.020634 |  |  |  |  |  |  | 2 | 1829 | DEFINED | both models defined on this subset |
| RF_vs_RFWF | M2_RF | M2_RF_WF | INTERVAL | 0.002202 | 0.018185 | -0.003522 | 0.007828 | -0.003086 | 0.008062 | UNRESOLVED | 0.005675 | 1 | 1829 | DEFINED | both models defined on this subset |

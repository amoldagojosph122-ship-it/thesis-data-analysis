# O5-T05. Scenario simulation summary (assumed lateral range)

Scenario analysis: the lateral range is assumed, not estimated, and scenarios are never pooled. Volumes are relative grid volumes of the simulated domain (INTERPOLATION, SUPPORTED cells), not resources. A scenario with a_h <= a_d cos(60) is INFEASIBLE and is not run.
Source: sql/objective_5/tables/O5-T05.sql, receipt 1, 5 rows.

| scenario_id | a_h_m | feasibility | vertical_bracket | a_v_m | a_v_expected_m | n_realisations | expected_volume_m3 | volume_p10_m3 | volume_p50_m3 | volume_p90_m3 | components_p10 | components_p50 | components_p90 | largest_share_p10 | largest_share_p50 | largest_share_p90 | sk_fallbacks | sk_neighbourless_nodes | exact_neighbour_searches | runtime_s | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SIS_AH015 | 15 | FEASIBLE | 0.000695 | 32.847912 | 32.85 | 100 | 913030.945005 | 865580 | 908900 | 936820 | 61.9 | 73 | 84.1 | 0.444758 | 0.474284 | 0.498271 | 0 | 9931 | 0 | 185.023129 | COMPLETED |
| SIS_AH025 | 25 | FEASIBLE | 0.001406 | 23.094351 | 23.09 | 100 | 913030.945005 | 844780 | 889100 | 940140 | 51 | 61 | 69.1 | 0.445604 | 0.4758 | 0.505026 | 0 | 1039 | 0 | 234.517125 | COMPLETED |
| SIS_AH050 | 50 | FEASIBLE | 0.001706 | 20.965951 | 20.97 | 100 | 913030.945005 | 832680 | 889400 | 931700 | 35 | 40.5 | 48 | 0.441848 | 0.488468 | 0.517493 | 0 | 42 | 8428 | 250.846585 | COMPLETED |
| SIS_AH100 | 100 | FEASIBLE | 0.001781 | 20.519806 | 20.52 | 100 | 913030.945005 | 852540 | 887900 | 944160 | 29 | 34 | 41 | 0.467029 | 0.505648 | 0.533176 | 0 | 5 | 33436 | 260.83858 | COMPLETED |
| SIS_AH200 | 200 | FEASIBLE | 0.0018 | 20.412649 | 20.41 | 100 | 913030.945005 | 867320 | 915700 | 953900 | 28.9 | 35 | 43 | 0.482277 | 0.510206 | 0.536716 | 0 | 0 | 34903 | 261.250934 | COMPLETED |

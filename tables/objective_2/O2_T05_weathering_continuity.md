# O2-T05. Weathering front continuity and interpolation check

Front = shallowest interval with weathering code mw or sw, depth in metres relative to collar. Interpolation is inverse-distance (power 2, 8 nearest holes); skill ratio = IDW RMSE / training-mean RMSE; interpolable when the ratio is at most 0.8. Configuration 5 is a sensitivity stage and writes no handoff.
Source: sql/objective_2/tables/O2-T05.sql, receipt 1, 20 rows.

| stat_group | stat_name | stat_value | unit | n_basis |
|---|---|---|---|---|
| ALONG_LINE_ADJACENT | max_abs_front_difference_m | 18.1865 | m | 66 |
| ALONG_LINE_ADJACENT | median_abs_front_difference_m | 2.5981 | m | 66 |
| ALONG_LINE_ADJACENT | median_collar_distance_m | 33.3449 | m | 66 |
| ALONG_LINE_ADJACENT | n_adjacent_pairs | 66 | count | 66 |
| ALONG_LINE_ADJACENT | p90_abs_front_difference_m | 7.7942 | m | 66 |
| FRONT_SUMMARY | max_front_z_relative_m | 0 | m | 71 |
| FRONT_SUMMARY | mean_front_z_relative_m | -7.3917 | m | 71 |
| FRONT_SUMMARY | min_front_z_relative_m | -19.9186 | m | 71 |
| FRONT_SUMMARY | n_holes | 71 | count | 71 |
| FRONT_SUMMARY | n_holes_with_reversals | 9 | count | 71 |
| FRONT_SUMMARY | n_holes_without_front | 0 | count | 71 |
| FRONT_SUMMARY | sd_front_z_relative_m | 4.4613 | m | 71 |
| INTERPOLATION_LEAVE_ONE_HOLE_OUT | interpolable | 0 | flag | 71 |
| INTERPOLATION_LEAVE_ONE_HOLE_OUT | rmse_idw_m | 4.8495 | m | 71 |
| INTERPOLATION_LEAVE_ONE_HOLE_OUT | rmse_training_mean_m | 4.4931 | m | 71 |
| INTERPOLATION_LEAVE_ONE_HOLE_OUT | skill_ratio | 1.0793 | ratio | 71 |
| INTERPOLATION_LEAVE_ONE_LINE_OUT | interpolable | 0 | flag | 71 |
| INTERPOLATION_LEAVE_ONE_LINE_OUT | rmse_idw_m | 5.5637 | m | 71 |
| INTERPOLATION_LEAVE_ONE_LINE_OUT | rmse_training_mean_m | 4.7344 | m | 71 |
| INTERPOLATION_LEAVE_ONE_LINE_OUT | skill_ratio | 1.1752 | ratio | 71 |

# O3-T01. Model definitions, predictors, target version and sample support

Predictors are restricted to the three safe coordinates; target-derived and logged-only fields are listed as non-predictors. Sample support is the outer training fold, never the held-out line.
Source: sql/objective_3/tables/O3-T01.sql, receipt 1, 39 rows.

| item_type | item_id | item | category | detail | units | status | n |
|---|---|---|---|---|---|---|---|
| FEATURE | F_BINARY | in_binary_target | TARGET_DERIVED | Direct target. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_COMMENT | comment_raw | TARGET_DERIVED | Label evidence. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_DEPTHFROM | depth_from_m | LOG_ONLY | Redundant with z_relative_m and tied to sampling geometry. | m | NOT_AVAILABLE | 0 |
| FEATURE | F_DEPTHTO | depth_to_m | LOG_ONLY | Redundant with z_relative_m and tied to sampling geometry. | m | NOT_AVAILABLE | 0 |
| FEATURE | F_DESIGNLABEL | design_label | TARGET_DERIVED | Direct target. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_EASTING | easting_m | SAFE | Planar coordinate; not derived from the target. | m | AVAILABLE_AT_PREDICTION | 0 |
| FEATURE | F_GRMIN | has_gr_mineral | TARGET_DERIVED | Label evidence. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_HOLE | hole_id | IDENTIFIER | Using it would memorise holes and leak the spatial split. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_INDICATOR | indicator | TARGET_DERIVED | Direct target. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_INTERVALID | upstream_interval_id | IDENTIFIER | Would memorise individual intervals. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_INTERVALKEY | upstream_interval_key | IDENTIFIER | Would memorise individual intervals. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_LABEL | label_state | TARGET_DERIVED | Direct target. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_LENGTH | interval_length_m | LOG_ONLY | No predictive content. | m | NOT_AVAILABLE | 0 |
| FEATURE | F_LINE | line_code | IDENTIFIER | Using it would leak the held-out line identity. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_MID | midpoint_m | LOG_ONLY | Redundant with z_relative_m and tied to sampling geometry. | m | NOT_AVAILABLE | 0 |
| FEATURE | F_NEGIND | negative_indicators | TARGET_DERIVED | Label evidence. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_NORTHING | northing_m | SAFE | Planar coordinate; not derived from the target. | m | AVAILABLE_AT_PREDICTION | 0 |
| FEATURE | F_PATTERN | evidence_pattern | TARGET_DERIVED | Label evidence. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_POSIND | positive_indicators | TARGET_DERIVED | Label evidence. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_ROCK | rock_code_raw | TARGET_DERIVED | The approved rule classifies graphite from rock type and mineral evidence. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_ROCKSTATUS | rock_code_status | TARGET_DERIVED | Rock-code validity is part of the label rule. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_SGS | is_sgs | TARGET_DERIVED | Label evidence. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_SUPPORT | support_length_m | LOG_ONLY | No predictive content. | m | NOT_AVAILABLE | 0 |
| FEATURE | F_WEATHER | weathering_code | LOG_ONLY | Not a mapped covariate; using it would not be deployable. |  | NOT_AVAILABLE | 0 |
| FEATURE | F_ZREL | z_relative_m | SAFE | Relative vertical position; z_absolute_m is never used. | m | AVAILABLE_AT_PREDICTION | 0 |
| GEOMETRY | GEOM-10-1 | 10 | PROVISIONAL_RELATIVE | CRS EPSG:32630; datum VERIFIED; vertical RELATIVE_TO_COLLAR; z_absolute_used=0 |  | VERIFIED | 0 |
| MODEL | BASE_LOGISTIC | Logistic regression | BASELINE | L2 logistic regression on the three safe coordinates, with standardisation refitted inside each fold. |  |  | 0 |
| MODEL | BASE_PREVALENCE | Training prevalence | BASELINE | Constant probability equal to the training-fold prevalence. Sanity baseline for every fold. |  |  | 0 |
| MODEL | M1_IK | Indicator kriging | M1 | Simple indicator kriging with a variogram and kriging neighbourhood fitted on the outer training fold only. |  |  | 0 |
| MODEL | M2_HGB | Gradient boosting | M2 | Histogram gradient boosting on the three safe coordinates. Audited fallback for XGBoost, which is not installed. |  |  | 0 |
| MODEL | M2_RF | Random forest | M2 | Random forest on the three safe coordinates. Hyperparameters selected by inner whole-hole CV. |  |  | 0 |
| MODEL | M3_HYBRID | Hybrid residual model | M3 | ML trend from the selected M2 candidate plus a kriged residual from an inner cross-fitted residual variogram. When the residual variogram is not supported, the run is recorded as an ML-only fallback, not a hybrid success. |  |  | 0 |
| SAMPLE | BASE_LOGISTIC | BASE_LOGISTIC | FOLD_SUMMARY | training rows 1301 to 1745; training positive 308 to 509; test rows 84 to 528; test positive 16 to 217; folds 5 | rows | OBSERVED | 7316 |
| SAMPLE | BASE_PREVALENCE | BASE_PREVALENCE | FOLD_SUMMARY | training rows 1301 to 1745; training positive 308 to 509; test rows 84 to 528; test positive 16 to 217; folds 5 | rows | OBSERVED | 7316 |
| SAMPLE | M1_IK | M1_IK | FOLD_SUMMARY | training rows 1301 to 1745; training positive 308 to 509; test rows 84 to 528; test positive 16 to 217; folds 5 | rows | OBSERVED | 7316 |
| SAMPLE | M2_HGB | M2_HGB | FOLD_SUMMARY | training rows 1301 to 1745; training positive 308 to 509; test rows 84 to 528; test positive 16 to 217; folds 5 | rows | OBSERVED | 7316 |
| SAMPLE | M2_RF | M2_RF | FOLD_SUMMARY | training rows 1301 to 1745; training positive 308 to 509; test rows 84 to 528; test positive 16 to 217; folds 5 | rows | OBSERVED | 7316 |
| SAMPLE | M3_HYBRID | M3_HYBRID | FOLD_SUMMARY | training rows 1301 to 1745; training positive 308 to 509; test rows 84 to 528; test positive 16 to 217; folds 5 | rows | OBSERVED | 7316 |
| TARGET | TARGET-DESIGN_8_2_v1-1 | DESIGN_8_2_v1 | APPROVED | positive=POSITIVE; negative=NEGATIVE; excluded=["AMBIGUOUS", "UNRESOLVED"] | intervals | APPROVED | 1829 |

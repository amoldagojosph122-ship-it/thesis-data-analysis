# O2-T04. Handoff contract and open items

The handoff is for Objective 3 only. Full-data parameters are never supplied for test folds, and every open item is listed with its status.
Source: sql/objective_2/tables/O2-T04.sql, receipt 1, 14 rows.

| item_type | item_id | status | detail |
|---|---|---|---|
| DIRECTION | LAT_AZ_000 | SKIPPED | 3 supported bins; 5 required |
| DIRECTION | LAT_AZ_045 | SKIPPED | 0 supported bins; 5 required |
| DIRECTION | LAT_AZ_135 | SKIPPED | 0 supported bins; 5 required |
| GATE | G09 | WARN | Declared orientation: survey orientations [(-60.0, 90.0)]; declared (-60.0, 90.0); uniform across holes = True |
| GATE | G10 | WARN | Class imbalance: lines below 10 per cent positive: NOM_N1113000 0.041 |
| GATE | G12 | WARN | Directional support: skipped directions: LAT_AZ_000, LAT_AZ_045, LAT_AZ_135 |
| GATE | G21 | WARN | Relative depth only: 5 of 5 sections labelled RELATIVE_DEPTH; no collar elevation is available, so the relative-depth limitation is always reported |
| HANDOFF | O3-HANDOFF-1 | NOT_IDENTIFIABLE | candidate_family=NONE; full_data_parameters_for_test_folds=0; No lateral model is both FITTED and stable under leave-one-line-out: spherical NOT_IDENTIFIABLE (structured sill below 5% of p(1-p): no structure beyond the nugget); exponential NOT_IDENTIFIABLE (range at the smallest supported lag: no spatial dependence beyond the nugget; structured sill below 5% of p(1-p): no structure beyond the nugget). Lateral continuity is not identified at this support. Objective 3 must not use a between-hole continuity model whose parameters come from these fits; models without a geostatistical continuity term may proceed without a continuity claim. |
| QUESTION | COLLAR_RL | OPEN | no collar elevation (RL) is available; depth is relative to collar and absolute elevation is not used |
| QUESTION | LAG_WINDOW | OPEN | collar pairs have a median separation of 921.0 m, while the lateral lag window ends at 500.0 m; longer-range structure is not assessed |
| QUESTION | LINE_PREVALENCE | OPEN | binary prevalence by line ranges from 0.041 to 0.506 across 5 lines; whether this reflects zones, sampling or geology is not resolved |
| SENSITIVITY | ABSOLUTE_ELEVATION_GEOMETRY | SKIPPED | SKIP_NO_VALIDATED_RL: not run |
| SENSITIVITY | STRICT_LABEL_COMPARATOR | SKIPPED | SKIP_NOT_AUTHORISED: not run |
| SENSITIVITY | TENTATIVE_GEOLOGIC_ORIENTATION | SKIPPED | SKIP_NO_GEOLOGIC_ORIENTATION: no strike or dip is recorded for the geology; all holes share one nominal orientation (G09) |

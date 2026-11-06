# Objective 2: blocked, skipped and deferred items

Gate results are from VERIFY run 12. Every WARN, SKIP, DOWNGRADE and STOP is listed.

## Gates with a warning or a skip

| gate | status | detail |
|---|---|---|
| G09 Declared orientation | WARN | survey orientations [(-60.0, 90.0)]; declared (-60.0, 90.0); uniform across holes = True |
| G10 Class imbalance | WARN | lines below 10 per cent positive: NOM_N1113000 0.041 |
| G12 Directional support | WARN | skipped directions: LAT_AZ_000, LAT_AZ_045, LAT_AZ_135 |
| G16 Leave-one-line-out stability | WARN | 2 fits are unstable; 10 refit rows for 5 lines (two models each); of which configuration 5 (fresh rock): 2 (see RUN_REPORT 5.8) |
| G21 Relative depth only | WARN | 5 of 5 sections labelled RELATIVE_DEPTH; no collar elevation is available, so the relative-depth limitation is always reported |

## Sensitivity entries not run

- STRICT_LABEL_COMPARATOR: SKIP_NOT_AUTHORISED: not run
- ABSOLUTE_ELEVATION_GEOMETRY: SKIP_NO_VALIDATED_RL: not run
- TENTATIVE_GEOLOGIC_ORIENTATION: SKIP_NO_GEOLOGIC_ORIENTATION: no strike or dip is recorded for the geology; all holes share one nominal orientation (G09)

## Figures and tables not supported

- none

## Independent checks

- Independent comparison with scikit-gstat: scikit-gstat was installed with uv into a scratch directory outside the project environment, because installing it into the project environment would downgrade scipy from 1.18.0 to 1.16.3. The comparison ran after the user approved it in chat, on the three-dimensional omnidirectional experiment with within-hole pairs included, which scikit-gstat's Matheron estimator also uses. Maximum absolute difference in semivariance: 2.776e-17 (tolerance 1e-09). Result: PASS. The lateral basis is not compared directly, because scikit-gstat cannot restrict pairs to a relative-depth band. Both use the same estimator, so the agreement is evidence for the pair counting and the binning.

## Deferred work (not performed in this stage)

- Lag window: configuration 3 tested lags to 2000 m as an exploratory extension (RUN_REPORT.md section 5.7). No range is identified inside that window. The median collar-pair separation is 921 m.
- Anisotropy: not evaluated. The azimuth fits are not leave-one-line-out tested, and no direction is supported in both opposite classes.
- Leave-one-line-out refits for the azimuth families: not assessed (exploratory families).
- Absolute elevation and the DEM: not used. Collar RL is missing from the source data (gate G03), and the DEM is provisional.
- STRICT_SGS_v1 comparator: run under configuration 3 as authorised (RUN_REPORT.md section 5.7). The rule stays PROPOSED; the authorisation covers the comparator run only. A comparator on the full STRICT sample of 1910 intervals is not run.
- Collar elevations: the RL column of the raw Collars sheet is empty for all 71 holes. The data request is in COLLAR_RL_REQUEST.md.
- Objective 3 modelling: not started. The handoff contract is in RUN_REPORT.md section 11.
- On-line versus between-line pairs (master prompt, step 4): not computed. Pairs are split only into within-hole and between-hole. This needs a further predeclared configuration.
- Projected sections with line orientation and projection offset (master prompt, step 3): not produced. O2-F04 shows observed hole strips only.
- Official Spec Kit initialisation (specify init) and the agent-side commands: not run (specification 07, section 1a).
- Commit and push of the Objective 2 work: not done. It waits for the user's instruction.

# Deferred figures and tables (Stage B and out-of-scope items)

Dataset c45b6dfe05190380d592fdd9f24ae8998f92796e1d6fb2c1ee14dda33f009d10. These items are NOT produced in Stage A. Each has a registry row with stage status `DEFERRED` in `figure_registry`, and no output file exists for it.

The Stage A figure catalogue (F01-F09, T01-T03) is complete for the data-supported items. Only the items below are deferred.

| ID | Objective | Item | Prerequisite gate and planned table contract |
|---|---|---|---|
| D01 | O2 | Directional indicator variograms and anisotropy | Stage B; needs approved label rule and training-only fitting |
| D02 | O2 | Indicator semivariogram fits and variogram admissibility | Stage B; needs validated pair support |
| D03 | O3 | Indicator kriging probability maps (M1) | Stage B; needs fitted training-only variogram |
| D04 | O3 | Random Forest and XGBoost predictions (M2) | Stage B; needs grouped spatial folds |
| D05 | O3 | Hybrid ML-indicator residual model (M3) | Stage B; needs residual variogram from training data |
| D06 | O4 | Confusion matrices and threshold-based classification metrics | Stage B; needs out-of-fold predictions |
| D07 | O4 | Calibration curves and calibration intercept/slope | Stage B; needs held-out predictions |
| D08 | O4 | ROC and PR curves for model comparison | Stage B; needs held-out predictions |
| D09 | O5 | Predictive probability volumes and 3-D graphitic probability | Stage B; needs final model and approved geometry |
| D10 | O5 | Entropy maps and uncertainty volumes | Stage B; needs probability volumes |
| D11 | O5 | Sequential indicator simulation realizations | Stage B; needs SIS validation gates |
| D12 | O1 | Absolute 3-D elevation model and georeferenced volume | Needs approved collar RL or DEM with vertical datum |
| D13 | O1 | Grade, tonnage or resource estimates | Not in scope: no graphite assays or TGC in workbook |

## Gates that must pass before Stage B starts

1. A supervising geologist approves one graphitic label rule (`label_reviews`, decision APPROVE_RULE).
2. Collar coordinates and datum are confirmed, and the drill-line grouping is approved or replaced.
3. Collar RL is supplied with a vertical datum, or a DEM method is approved. Until then, all vertical outputs remain relative and no georeferenced volume is claimed.
4. Stage B tables are populated only in their objective databases (`kambale_obj2_spatial.sqlite` and later). The blocking triggers in obj1_master must stay in place.
5. Variograms and models are fitted only on training data inside each spatial fold. A variogram fitted on all holes is exploratory only.

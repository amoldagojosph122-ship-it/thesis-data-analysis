# Methods, reasons and justification: Kambale graphite thesis

A working guide for writing the methods chapter and defending it in the viva. For every objective it gives:
- **what was done**, step by step;
- **why each choice was made**, with the evidence from the data;
- **how to defend it**: the question an examiner is likely to ask and a short answer.

Numbers come from the run reports and configuration files in this repository. Rewrite the text in your own words for
the thesis. Use this file as the source of facts and reasons, not as finished prose.

---

## 0. Principles that apply to every objective

### 0.1 Settings were fixed before each analysis was run

**What.** Every analysis setting (lag widths, thresholds, model grids, validation splits, decision rules) was written
into a configuration file before the analysis that uses it was run. When a first run showed that a design could not
work, a new version was written. The old version and its result were kept and reported, with the reason for the change.

**Why.** With 71 holes and five drill lines, it is easy to keep trying settings until a pleasing result appears. That
inflates apparent skill and continuity. Fixing the settings first separates "what the data show" from "what we tuned".

**Defence.**
- *"You changed your design after seeing results."* Yes, openly. Each change is recorded with its reason, and the
  earlier result is reported, not hidden. Each change narrows how an objective is measured, never what it asks. For
  example, Objective 3 added a second validation setting because leave-one-line-out put every test point 450–560 m from
  training, beyond any range the data support. That is a design limitation found by the first run, not a result being
  tuned.

### 0.2 Validation is spatial, never random

**What.** Models are always tested on whole held-out blocks: whole drill lines, or whole holes. Intervals from the
same hole are never split between training and test.

**Why.** Neighbouring 1 m intervals in one hole are strongly correlated (the down-hole range is about 23 m). With
random splitting, almost every test interval has a training interval a metre away, and accuracy is grossly inflated.
Spatial blocks give an honest estimate of skill at an undrilled location.

**Defence.**
- *"Why not ordinary k-fold?"* Because the test points would not be independent of the training data, and the score
  would describe interpolation within a hole, which nobody needs a model for.

### 0.3 The hole is the unit of uncertainty

**What.** Uncertainty intervals come from resampling **holes** with replacement and keeping all the intervals of a
drawn hole together (a hole-cluster bootstrap).

**Why.** The 1,829 intervals are not 1,829 independent observations. Most of the dependence is within holes, so the
effective sample is closer to 71 holes. Resampling intervals would give intervals that are far too narrow.

### 0.4 Probabilities, not just classes

**What.** Models are judged mainly on the **Brier score**, the mean squared error of the predicted probability. Log
loss, ROC-AUC, PR-AUC and calibration are reported alongside it.

**Why.** The thesis is about uncertainty, so the quality of the probability matters, not only whether a threshold gives
the right class. The Brier score is a proper scoring rule: it rewards honest probabilities. It is bounded and easy to
interpret against a baseline: always predicting the prevalence gives p(1−p), about 0.21–0.22 here. AUC ignores
calibration and accuracy depends on an arbitrary threshold, so neither can be the primary measure.

### 0.5 What the data cannot support is stated, not forced

The data have no assays, no collar elevations, no downhole surveys, and lines 100–400 m apart. Several analyses
therefore end in "not identifiable" or "not statistically resolved". These are results, and the thesis should present
them as findings about what this drilling can and cannot tell us.

---

## 1. Objective 1: database, QA/QC and the graphitic definition

**Aim.** Build and check a three-dimensional drill-hole database and define graphitic domains.

### 1.1 Database from the workbook

**What.** The drilling workbook (Collars, Surveys, Logging, Logging Legend) was imported into a relational SQLite
database. Raw sheets are kept unchanged, and cleaned tables are built from them. Every count was checked against a
recount of the workbook: 71 RAB holes, 71 end-of-hole orientation records, and 1,910 contiguous 1 m logging intervals.

**Why.** A database with keys and constraints makes errors visible (gaps, overlaps, unknown codes, duplicate holes)
and lets every later number be traced back to a query. Keeping the raw sheets means any cleaning step can be checked.

**Defence.**
- *"Why not work in Excel?"* Excel cannot enforce that intervals are contiguous, that codes exist in the legend, or that
  a figure comes from a stated query. The database can, and it is checked automatically.

### 1.2 QA/QC checks

**What.** Checks covered:
- interval continuity (no gaps or overlaps);
- depth consistency against hole length;
- dip and azimuth ranges;
- codes present in the legend;
- the horizontal difference between the two coordinate pairs in the workbook;
- reconciliation against the counts in the preliminary thesis design document.

Each finding has a severity and is reported.

**Result to mention.** The design document reports 529 `Sgs` intervals; the database holds 530. The one-interval
difference is recorded, and the database value is used.

### 1.3 Coordinates

**What.** The UTM pair (UTMEasting/UTMNorthing, WGS 84 / UTM zone 30N) was adopted. The alternate Easting/Northing pair
is kept but not used.

**Why.** The workbook declares UTM 30N for all 71 holes, and the regional geology shapefile uses the same system. The
alternate pair sits on 5 m and 10 m nodes, which suggests planned rather than surveyed positions. That is an
inference, and it is recorded as one.

### 1.4 Hole geometry

**What.** Each hole is treated as straight, with its single recorded orientation (dip −60°, azimuth 090°) applied from
collar to end of hole. Interval midpoints are placed at ΔE = m cos δ sin α, ΔN = m cos δ cos α, ΔZ = m sin δ. All depths
are **relative to the collar**.

**Why.**
- There is one orientation record per hole and no downhole survey, so a straight hole is the only defensible model.
- Holes are short RAB holes (tens of metres), so deviation over that length is likely small.
- No collar elevation (RL) is in the workbook, so absolute elevation cannot be computed. A Copernicus 30 m DEM was used
  only as a provisional sensitivity check. It is a surface model (it includes vegetation) and is not a surveyed RL.

**Defence.**
- *"All holes having exactly −60/090 looks like planned values."* Agreed, and it is flagged. The orientation is
  assumed, not measured, and that limits any structural interpretation (see 2.6).

### 1.5 Graphitic label: rule DESIGN_8_2_v1

**What.** Graphitic status is not recorded in one field. Three logged indicators were combined:
- s: the rock code is `Sgs` (graphite schist);
- g: a graphite mineral is logged;
- c: the comment describes graphite.

The approved rule DESIGN_8_2_v1 (from section 8.2 of the thesis design document) labels an interval:
- **POSITIVE** when the code is `Sgs`, at least one other indicator supports it, and nothing conflicts;
- **NEGATIVE** when the code is another valid code, no graphite indicator is present, and a comment exists;
- **AMBIGUOUS** when only one indicator is present or the evidence disagrees;
- **UNRESOLVED** when the code is missing or unsupported.

Only POSITIVE and NEGATIVE intervals (1,829 of 1,910) enter the models.

**Why.**
- The three indicators disagree in 126 intervals, so the rock code alone is not a complete definition.
- Requiring agreement gives a cleaner target, and excluding the doubtful intervals is better than guessing their class.
- A blank mineral field is not counted against graphite, because blank means "not logged", not "absent".

**Sensitivity rules.** STRICT_SGS (code only), RECON_2OF3, ALL3 (all three indicators) and ANY (any indicator) were
computed and remain PROPOSED. They show how far the labels depend on the rule.

**Defence.**
- *"Excluding 81 ambiguous intervals biases the sample."* It removes intervals whose class cannot be stated. Their
  number and location are reported, and the label sensitivity is shown under the other rules.
- *"Why not use assays?"* There are none. The label is a **logged occurrence**, not a grade, and no grade or resource
  statement is made.

### 1.6 Drill lines

**What.** Holes were grouped into five drill lines by nominal Northing.

**Why.** The collars fall clearly into five Northing groups, and the holes are drilled east along them. The lines are
the natural blocks for spatial validation.

---

## 2. Objective 2: spatial distribution, geological controls and continuity

**Aim.** Characterise where graphite occurs, what controls it, and how continuous it is, using exploratory analysis
and indicator variography.

### 2.1 Descriptive occurrence

**What.** The graphitic proportion was mapped by hole, line, depth and weathering class.

**Result.** Graphite is common in moderately weathered rock (mw, prevalence about 0.46) and essentially absent in
completely or highly weathered rock (cw, hw). It also varies strongly between lines; one line is only about 4 per cent
graphitic.

**Why it matters.** Weathering class explains most of the contrast in prevalence. That is why the weathering front is
treated as a geological control (2.5) and used as a predictor (Objective 3).

### 2.2 Indicator variogram: why an indicator

**What.** Each binary interval gets i = 1 if graphitic and 0 otherwise. The semivariogram γ(h) is half the mean squared
difference between pairs at lag h. For a 0/1 variable this equals half the proportion of pairs that disagree.

**Why.** The target is categorical (graphitic or not) and there is no grade, so indicator geostatistics is the standard
approach. The indicator variogram describes how quickly the chance that two points share a class decays with
distance.

### 2.3 Lag definition: horizontal lag at similar depth

**What.**
- **Lateral (between-hole):** horizontal lag √(ΔE² + ΔN²) between intervals in different holes whose relative depths
  differ by at most 3 m. Bins are 20 m wide, up to 500 m.
- **Down-hole (within-hole):** 1 m bins, up to 30 m.

The two are reported separately.

**Why.** The first configuration used a 3-D lag. Vertical separation then dominated every lag, the curve was flat at
the sill, and the fitted range sat at its lower bound. That design mixed down-hole and lateral structure. Restricting
pairs to similar depth isolates lateral continuity, which is the question that matters between holes. The earlier
result is kept and reported as superseded.

**Defence.**
- *"Why 3 m?"* It is about three logging intervals: wide enough to form pairs, narrow enough that pairs compare the same
  depth level.
- *"Why at least 100 pairs and 10 independent hole pairs per bin?"* Bins with few pairs, or with pairs from only one or
  two hole pairs, give erratic estimates that look like structure. These are conventional minimum-support rules, fixed
  in advance.

### 2.4 Model fitting and the identifiability rule

**What.** Spherical and exponential models were fitted by weighted least squares with Cressie weights (N/γ²). The
bounds were:
- nugget between 0 and p(1−p);
- structured sill between 0 and 1.5·p(1−p);
- range between the first supported lag and the maximum lag.

A fit counts as **NOT_IDENTIFIABLE** in any of these cases:
- the range sits at a bound;
- the sill sits at its upper bound;
- the structured sill is below 5 per cent of p(1−p);
- there are fewer than 5 supported bins.

A fit is **STABLE** only if refitting with each line left out keeps the range within a factor of 2.

**Why.** A least-squares fit always returns numbers, even to noise. These rules separate a real structure from a fit
that is just pressed against a constraint. Leaving one line out tests whether a single line drives the result, which
matters with only five lines.

**Result.**
- **Down-hole** continuity is identified, with a practical range of about 15–24 m (exponential fit 23.5 m).
- **Lateral** continuity is **not identifiable** at this drilling support. Holes are about 21–33 m apart within lines,
  lines are 100–400 m apart, and graphitic runs are short (median about 4 m).

**Defence.**
- *"So you found nothing laterally?"* We found that this drilling cannot resolve lateral continuity. That is a
  substantive result, and it decides how Objectives 3–5 must be designed. Lateral continuity is treated as an
  assumption, tested in scenarios, and never estimated.

### 2.5 Further attempts to find lateral structure (each predeclared)

1. **Longer lags (to 2000 m).** Most collar pairs lie beyond 500 m (median 921 m), so the window was extended to cover
   the 95th percentile of separations. The structure was still not identifiable.
2. **Directional (azimuth) variograms.** Exploratory only, because no geological strike is recorded. Three of the four
   directions had too few pairs, so anisotropy cannot be established.
3. **Weathering front as a control, and fresh-rock-only variograms.** Graphite occurs mainly below the front, so
   variography was repeated within the mw/sw rock. Pairs were matched by depth below the collar, and also by depth
   below each hole's own front. The front-aligned pairing fitted a structure, but it was unstable when a line was left
   out.
4. **Structural (dipping-plane) frame.**
   - *Reason:* published work on the deposit (Sunkari et al., 2026) describes stratabound horizons. If the horizons dip,
     pairs at equal depth in neighbouring holes compare different layers and look like nugget.
   - *Method:* the apparent dip was searched from −80° to +80° within each section. The search was tested against a
     permutation null that accounts for picking the best of 17 dips.
   - *Result:* no stable structural frame was identified for the primary sample.

**Defence.**
- *"Isn't four attempts a fishing expedition?"* Each was written down before it was run, each has a stated geological
  reason, and the dip search was tested against a null built for the selection. None was claimed when it failed.

### 2.6 The weathering front

**What.** The front of each hole is the top of the shallowest interval coded mw or sw. Its continuity was measured in
three ways:
- the difference between adjacent holes on a line (median 2.6 m);
- a semivariogram of front depth;
- inverse-distance prediction under leave-one-hole-out and leave-one-line-out, compared with simply predicting the
  training mean.

**Result.** The front is locally similar between neighbouring holes, but it is **not interpolable**:
- inverse distance does slightly worse than the mean (RMSE 4.85 m against 4.49 m leaving one hole out; 5.56 m against
  4.73 m leaving one line out);
- the front semivariogram is at its sill from the first 25 m bin.

### 2.7 What Objective 2 permits

- **Permits:** occurrence controlled by weathering; down-hole continuity of about 20 m; lateral continuity not resolved
  at this spacing.
- **Does not permit:** a lateral range for graphitic domains, a strike direction, or a front surface usable away from
  the holes.

---

## 3. Objective 3: indicator, machine-learning and hybrid models

**Aim.** Develop and spatially validate indicator-geostatistical (M1), machine-learning (M2) and hybrid (M3) models of
graphitic occurrence.

### 3.1 Two validation settings

**What.**
- **Prediction to a new drill line** (leave-one-line-out, 5 folds). Each line is predicted from the other four.
- **Prediction between holes on the same line** (interleaved holes, 5 folds). Within each line, holes are ordered by
  easting and every fifth hole is held out together, so held-out holes keep training neighbours about one hole spacing
  away (15–17 m).

**Why.** Leave-one-line-out alone put every test point 450–560 m from training, beyond any supported range. In that
setting no spatial method can use spatial correlation, so M1 and M3 could not be tested fairly. The two settings answer
two different practical questions: "how well can we predict an undrilled line?" and "how well can we infill between
holes?". They are evaluated separately, because one pooled score would mix them.

### 3.2 Predictors

**What.** The models use:
- **TREND:** easting, northing and relative depth;
- **TREND_WF:** TREND plus **depth below the weathering front**.

Logged variables (rock code, weathering code, comments) are forbidden as predictors.

**Why.**
- The logged variables are what defines the label, or are only known after drilling, so using them would be circular.
- Coordinates carry the large-scale trend.
- The weathering front is the one geological control that Objective 2 showed matters, and it can be estimated at an
  undrilled location from the surrounding holes.

### 3.3 Depth below the front, and why inverse distance

**What.** At each location the front depth is an inverse-distance average (power 2, eight nearest holes) of the
observed hole fronts. The predictor is the modelled front depth minus the interval depth. It is **fold-safe**:
- a training row uses the other training holes only (its own hole is left out);
- a test row uses training holes only;
- test holes never contribute, and an automated check confirms that altering test-hole fronts changes nothing in
  training.

**Why inverse distance rather than kriging:**
1. The front semivariogram is at its sill from the first lag, so there is no spatial structure for kriging to use. A
   kriged surface would reduce to the mean, and any fitted range would be arbitrary.
2. Inverse distance has no parameters to estimate, so it can be rebuilt in every fold without leaking information or
   failing to converge.
3. It honours each hole's observed front and gives a local weighted average between holes.

**Honest limitation.** Objective 2 showed the front is not predictable between holes. The predictor therefore carries
the broad trend of front depth, not local detail. Power 2 and eight neighbours are conventional defaults. Section 6
tests six alternatives: none gave a resolved improvement for the selected models, and removing the front's lateral
variation made the tree models worse.

### 3.4 Model families

| Model | What it is | Why it was included |
|---|---|---|
| BASE_PREVALENCE | Always predicts the training proportion | The floor any model must beat |
| BASE_LOGISTIC (and _WF) | Logistic regression on standardised predictors, L2 penalty | Simple, smooth, interpretable trend; a strong baseline for small data |
| M2_RF (and _WF) | Random forest | Captures non-linear trends and interactions; robust with little tuning |
| M2_HGB (and _WF) | Histogram gradient boosting | Strong learner for tabular data; models log-odds as a sum of trees |
| M1_IK | Simple indicator kriging | The geostatistical model named in the title |
| M3_HYBRID | ML trend plus kriged residuals | Tests whether spatial correlation remains after the trend |

XGBoost was planned but not installed. Histogram gradient boosting is the equivalent gradient-boosting method from
scikit-learn.

### 3.5 Tuning, calibration and thresholds (inside each training fold only)

**What.**
- **Tuning:** hyperparameters were chosen by inner cross-validation (4 folds grouped by hole), minimising log loss over
  small grids fixed in advance.
- **Calibration:** random-forest and boosting outputs were recalibrated with Platt scaling, fitted on the inner
  out-of-fold predictions. Logistic regression is already calibrated by construction.
- **Threshold:** the classification threshold maximises Youden's J on the inner predictions. It is used only for
  class maps; probabilities are what is evaluated.

**Why.** Nothing about a test fold may influence the model that predicts it, so all choices are made inside the
training fold. The grids are small because, with 71 holes, a large search overfits the inner folds. Tree ensembles
give poorly calibrated probabilities (pushed towards 0.5 for forests), and Platt scaling corrects this with only two
parameters.

### 3.6 Indicator kriging (M1)

**What.** Simple kriging of the indicator, with:
- mean equal to the training prevalence;
- exponential covariance with horizontal distance;
- neighbours restricted to within 3 m of the same depth.

The covariance (range 25–400 m, nugget fraction 0.25–0.75, or pure nugget) is **chosen by inner cross-validation** from a
fixed grid, not read from the experimental variogram.

**Why.** Objective 2 found the lateral variogram not identifiable, so there is no experimental model to plug in.
Choosing the covariance by predictive performance inside the training fold is a fair alternative. Including "pure
nugget" (no correlation) as a candidate lets the data say that there is no usable structure. Simple kriging with the
training mean is appropriate for an indicator whose mean is estimated from the training data.

### 3.7 Hybrid (M3)

**What.** The residual of the calibrated ML trend (observed 0/1 minus predicted probability) is kriged and added back
to the trend, then clipped to [0, 1]. The trend is cross-fitted inside the training fold, so the residuals are honest.

**Result.** In all 10 runs, inner validation chose no residual correlation (pure nugget). M3 therefore equals its ML
trend.

**Defence.**
- *"Then the hybrid failed?"* It was built and tested. The test found no spatial correlation left after the trend at
  this spacing. This is a finding, consistent with Objective 2, and the hybrid was not forced to use a correlation the
  data do not support.

### 3.8 Leakage controls

Every run records checks that:
- the predictors are available at prediction time;
- no test point is in the training data;
- variograms belong to their own training fold;
- calibration used inner data only;
- every prediction belongs to its fold.

All 14 checks passed.

---

## 4. Objective 4: predictive performance and model comparison

**Aim.** Evaluate the models with independent spatial validation and probability-based metrics.

### 4.1 What was compared

All held-out predictions from Objective 3 were scored on the same 1,829 intervals, once for each validation setting.
No model was refitted and no threshold was tuned in Objective 4.

### 4.2 Metrics

| Metric | What it measures | Why |
|---|---|---|
| Brier score (primary) | Mean squared error of the probability | Proper, bounded, directly comparable with the prevalence baseline |
| Log loss | Penalises confident wrong predictions strongly | Sensitive to over-confidence |
| ROC-AUC, PR-AUC | Ranking of positives above negatives | Discrimination, independent of calibration; PR-AUC suits about 29 per cent prevalence |
| ECE, reliability bins | Calibration | Whether a probability of 0.3 really means 30 per cent |
| Calibration intercept and slope | Over- or under-confidence | Diagnostic only, never applied |

The interval-weighted Brier score is primary. An equal-hole weighting is reported as a check, so that long holes do not
dominate.

### 4.3 Paired comparison with hole-cluster intervals

**What.** For each pair of models, the Brier difference was computed on the same intervals, with a 95 per cent
interval from 2,000 hole-cluster bootstrap replicates. A difference is **resolved** only if its interval excludes zero.
When it is unresolved, the half-width of the interval is reported as the smallest difference this design could detect.

**Why.** Comparing two models on the same data removes most of the noise shared between them, so paired differences
are far more sensitive than comparing two separate scores. Resampling holes respects the dependence within holes.
Reporting the detectable difference turns "no difference" into "no difference larger than about 0.013 Brier", which is
the honest statement.

### 4.4 Decision rule (fixed in advance)

The selected model is the distinct model with the lowest Brier score; the next lowest is the comparator. A
**supported improvement** needs all of the following:
- the interval of the difference entirely below zero;
- the selected model better in at least 4 of the 5 folds;
- acceptable calibration (slope between 0.5 and 2, |intercept| at most 0.5);
- ROC-AUC not worse than the comparator by more than 0.02;
- coverage of at least 95 per cent.

Otherwise the decision is **inconclusive**, and the lowest-Brier model is kept as a point estimate with a caveat.

**Results.**

| Setting | Selected | Comparator | Brier difference [95% interval] | Decision |
|---|---|---|---|---|
| New drill line | Logistic regression with front depth | Random forest | −0.0004 [−0.014, +0.014] | Inconclusive |
| Between holes | Gradient boosting with front depth | Gradient boosting | −0.0018 [−0.007, +0.003] | Inconclusive |

The resolved findings are:
- The coordinate trend beats prevalence in both settings (Brier difference −0.056 on a new line, −0.049 between holes).
- Indicator kriging beats prevalence between holes (0.176 against 0.211), but is no better than prevalence on a new
  line (0.219 against 0.221), as expected when test points lie beyond any correlation range.

**Defence.**
- *"So which model is best?"* With five lines and 71 holes, the leading models cannot be separated. Differences smaller
  than about 0.013 Brier cannot be detected. We select the lowest-scoring model and carry the unresolved choice forward
  as an uncertainty (Objective 5 maps where the two leading models disagree).
- *"Why not just report accuracy?"* Accuracy depends on the threshold and ignores how confident the model is. A
  probability-based thesis needs a proper scoring rule.

---

## 5. Objective 5: three-dimensional uncertainty and scenarios

**Aim.** Quantify and visualise 3-D uncertainty, and identify areas of high confidence and high uncertainty.

### 5.1 Why the uncertainty is model-based

Objective 2 found no identifiable lateral variogram, and Objective 4 left the model choice unresolved. A conventional
geostatistical simulation needs a lateral covariance estimated from data, and none exists. The headline uncertainty is
therefore built from the validated models:
- the probability;
- the entropy of that probability;
- a hole bootstrap of the model fit;
- the disagreement between the two leading models.

Joint (multi-cell) uncertainty is added separately as labelled **scenarios** with an assumed range.

### 5.2 Grid and support zones

**What.** The grid uses 10 m × 10 m × 2 m cells (200 m³) over the collar area plus a 100 m margin, in depth relative to
the collar. Each cell gets a zone from its distance to the nearest collar:

| Zone | Distance | Model used | Basis |
|---|---|---|---|
| Interpolation | ≤ 25 m | Between-hole model (gradient boosting with front depth) | Its test holes were 15–17 m from training; 25 m is about one hole spacing |
| Extrapolation | 25–560 m | New-line model (logistic with front depth) | Its test lines were 454–557 m from training; distances in between were not tested, so the more conservative new-line skill is used |
| No support | > 560 m | None | Beyond any validated distance |

Cells deeper than the deepest sampled interval within 100 m are marked depth-extrapolated, and they are never
classed as confident.

**Why.** A model is only trustworthy at the distances where it was validated. Tying each zone to the validation
setting that tested that distance prevents the map from claiming skill it never demonstrated.

### 5.3 Uncertainty measures

- **Probability** p from the zone's selected model, refitted on all data with the same tuning procedure.
- **Entropy** H(p), in bits. It is largest at p = 0.5, so it shows where the model is least decided.
- **Hole bootstrap** (200 replicates). The model, the front surface and the calibration are refitted on resampled
  holes, giving a 90 per cent interval [p_lo, p_hi] per cell. This shows how much the prediction depends on which holes
  happened to be drilled.
- **Model disagreement** |p_selected − p_runner-up|. Because the model choice is unresolved, this shows where that
  choice matters.

### 5.4 Confidence classes

- **Confident present:** p_lo ≥ 0.5, disagreement < 0.20, and not depth-extrapolated.
- **Confident absent:** p_hi < 0.5, under the same conditions.
- **Uncertain:** everything else with a probability.

**Why.**
- 0.5 means "more likely than not"; the training prevalence is shown as a sensitivity threshold.
- Requiring the whole bootstrap interval on one side of the threshold, and the two models to agree within 0.20, means a
  cell is called confident only when neither the sample nor the model choice could reasonably change its class.
- Cells above the weathering front classed "confident absent" mean "not logged as graphitic", because weathered rock
  rarely carries the graphite logging, not "proven barren".

### 5.5 Scenario simulation (sequential indicator simulation with a locally varying mean)

**What.**
- **Domain:** interpolation-zone cells only.
- **Mean:** the local mean at each node is the between-hole model's probability.
- **Residual covariance:** taken from the down-hole variogram (nugget and sill fitted in Objective 2), with geometric
  anisotropy.
- **Lateral range:** **assumed**, at five values (15, 25, 50, 100 and 200 m).
- **Vertical range:** set so that the range along the hole direction equals the fitted down-hole range of 23.5 m.
- **Simulation:** 100 realisations per scenario, conditioned on all binary intervals.
- **Outputs:** graphitic grid volume (P10/P50/P90) and connectivity (share of graphitic cells in the largest connected
  body), reported per scenario.

**Why.**
- Per-cell uncertainty cannot answer joint questions such as "how much graphitic rock?" or "is it one body or many?".
  Those need spatially correlated realisations.
- The down-hole structure is the only correlation the data identify, so it sets the vertical behaviour.
- The lateral range cannot be estimated, so it is varied as a scenario. The five values run from "no correlation
  between holes" (15 m), through one hole spacing (25 m), to the stratabound continuity described in the literature
  (50–200 m).
- The locally varying mean keeps the validated trend, while the simulation adds only the residual variability.

**Result.** Median volume varies from about 888,000 to 916,000 m³ across scenarios, against an expected 913,000 m³.
The largest-body share varies from 0.47 to 0.51.

**Defence.**
- *"Which scenario is right?"* None can be chosen from these data. The spread across scenarios is the uncertainty due
  to unknown lateral continuity. Volumes are grid volumes in a relative-depth frame, not resource volumes.

---

## 6. Sensitivity of the weathering-front interpolation (supplementary)

Full results: `reports/sensitivity/FRONT_SURFACE_SENSITIVITY.md`, tables `tables/sensitivity/front_surface/`, and
figures `figures/sensitivity/SF01` and `SF02`. The settings were written in `config/sensitivity/front_surface_config.yaml`
before the run.

### 6.1 What was done

The three front-depth models (logistic, random forest and gradient boosting) were refitted with seven front surfaces:

| Variant | Surface |
|---|---|
| IDW_P2_K8 | The original: inverse distance, power 2, 8 nearest holes |
| IDW_P1_K8, IDW_P3_K8 | Power 1 (smoother) and power 3 (more local) |
| IDW_P2_K4, IDW_P2_K16 | 4 and 16 neighbours |
| NEAREST_HOLE | The front of the single nearest hole |
| TRAINING_MEAN | The mean front of the training holes, with no lateral variation at all |

The folds, tuning grids, calibration and seed are the same as in Objective 3. As a check, the original surface had to
reproduce the stored Objective 3 predictions exactly, and it did (maximum difference 0). Each alternative was compared
with the original on the same held-out intervals: Brier difference (alternative minus original), with a 95 per cent
interval from 2,000 hole-cluster bootstrap replicates.

### 6.2 Results

**How well each surface predicts the front itself** (error ratio against the training mean; below 1 is better than the
mean):

| Surface | Leave one hole out | Leave one line out |
|---|---|---|
| Power 2, 8 holes (original) | 1.08 | 1.18 |
| Power 1, 8 holes | 1.01 | 1.17 |
| Power 3, 8 holes | 1.13 | 1.18 |
| Power 2, 4 holes | 1.09 | 1.20 |
| Power 2, 16 holes | 1.08 | 1.14 |
| Nearest hole | 1.29 | 1.61 |

No surface predicts the front better than its mean. The more local the surface (nearest hole, power 3), the worse it
does. This confirms the Objective 2 finding that the front is not interpolable between holes.

**Effect on held-out model performance** (Brier score; the Objective 4 selected model in bold):

| Surface | New drill line: **logistic** | random forest | gradient boosting | Between holes: logistic | random forest | **gradient boosting** |
|---|---|---|---|---|---|---|
| Original | **0.1651** | 0.1677 | 0.1657 | 0.1627 | 0.1628 | **0.1531** |
| Largest change from original | +0.0010 (unresolved) | +0.0050 (resolved, mean surface) | +0.0077 (resolved, mean surface) | −0.0032 (resolved, mean surface) | −0.0011 (unresolved, mean surface); −0.0010 resolved with 4 holes | +0.0044 (resolved, mean surface) |

Seven of 36 comparisons were statistically resolved:
- **New drill line.** Removing the lateral variation of the front (mean surface) made the random forest and gradient
  boosting worse, by 0.005 and 0.008. Power 1 made them worse by 0.002 and 0.003. The selected logistic model did not
  change by a resolved amount under any surface.
- **Between holes.** The mean surface made the selected gradient-boosting model worse (+0.004) but made logistic
  regression better (−0.003). Four neighbours made the random forest slightly better (−0.001).

Under the rule fixed beforehand, both prediction settings are therefore labelled **performance-sensitive**: at least
one resolved difference exists.

**Which model scores lowest.** The lowest-Brier model changed under 4 of the 7 surfaces in each setting:
- on a new line, it moved between logistic with front depth, gradient boosting with front depth, and random forest;
- between holes, it moved between gradient boosting with and without front depth.

These are the same models that Objective 4 could not separate.

### 6.3 What it means

1. **The original surface is never beaten for the selected models.** No alternative surface gave a resolved improvement
   for the model that Objective 4 selected in either setting (logistic on a new line, gradient boosting between holes).
   For the gradient-boosting model, removing the lateral front variation made it resolvably worse.
2. **The lateral variation of the front carries information, even though the front cannot be interpolated accurately.**
   When it is removed (mean surface), the tree models predicting a new line get resolvably worse. The surface works as a
   smoothed regional trend of the weathering level, not as an accurate local front.
3. **The effects are small.** Every resolved difference is at most 0.008 Brier, below the roughly 0.013 that Objective 4
   could detect between models. The surface choice moves models around within the group that was already statistically
   tied, and it does not change any conclusion of Objectives 4 or 5.
4. **The "performance-sensitive" label must be reported as it stands.** It was the rule fixed in advance. The honest
   reading is that individual models respond to the surface by small but detectable amounts, while the overall findings
   (trend models beat prevalence; leading models not separable; front predictor useful mainly as a broad trend) hold
   under every surface tested.

### 6.4 Suggested thesis wording

> "Because the inverse-distance settings (power 2, eight neighbours) were conventional rather than optimised, a
> sensitivity analysis refitted the weathering-front models with six alternative surfaces, from the nearest hole to a
> constant training mean, under the same folds, tuning and calibration. No surface predicted the front better than its
> mean, confirming that the front is not interpolable at this spacing. For the models selected in Objective 4, no
> alternative surface gave a resolved improvement. Removing the lateral variation of the front made the tree-based
> models resolvably worse when predicting an unseen line (by 0.005–0.008 Brier). The surface therefore acts as a
> smoothed regional trend of the weathering level. All resolved differences (at most 0.008) were smaller than the
> differences Objective 4 could detect between models, so the choice of surface does not change the model comparison or
> the three-dimensional products."

**Defence.**
- *"Why IDW, if it predicts the front worse than the mean?"* Because the models are not judged on predicting the front;
  they are judged on predicting graphite. The sensitivity analysis shows that the IDW surface's lateral variation helps
  the tree models predict graphite on an unseen line, and that no other tested surface did better for the selected
  models.

---

## 7. Limitations to state plainly

1. **Relative depth only.** There is no collar RL, so there is no absolute elevation, depth below sea level or absolute
   volume.
2. **Assumed orientation.** One planned orientation applies to all holes, with no downhole surveys, so geology and
   drilling direction cannot be separated.
3. **No assays.** The label is a logged occurrence, with no grade or resource statement.
4. **Lateral continuity unresolved.** Lines are 100–400 m apart; continuity between lines is an assumption, carried as
   scenarios.
5. **Model ranking unresolved.** The leading models cannot be separated at this sample size.
6. **Hybrid equals its trend.** Whether a residual structure exists cannot be tested at this spacing.

**What would resolve them.** Infill drilling between lines would resolve the lateral structure. Assays would give a
grade-based definition. A surveyed collar RL would allow absolute elevation, and downhole surveys would allow a real
structural frame.

---

## 8. One-paragraph summary for the viva

> "I built a checked database from the drilling workbook and defined graphite from three logged indicators that had to
> agree. Variography showed clear down-hole continuity of about 20 m. Lateral continuity could not be identified,
> because the holes and lines are too far apart for the short graphitic runs, even after testing longer lags, the
> weathering control and a dipping-plane frame. So I compared geostatistical, machine-learning and hybrid models under
> two spatial validation settings, and judged them on held-out probability scores with hole-level uncertainty. Trend
> models with the weathering front did best, but not by a resolvable margin. Kriging helped only between holes, and the
> hybrid found no residual correlation. The 3-D products therefore show model-based uncertainty tied to the distance at
> which each model was validated, plus scenarios for the lateral continuity the data cannot resolve."

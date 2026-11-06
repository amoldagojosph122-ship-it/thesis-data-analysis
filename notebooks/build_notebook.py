#!/usr/bin/env python
"""Build the Kambale results notebook and the standalone mathematical notes.

Run from anywhere:

    python notebooks/build_notebook.py

Writes (overwriting):
    notebooks/Kambale_Thesis_Results.ipynb   notebook source with empty outputs (requires nbformat)
    notebooks/MATH_NOTES.md                  the mathematical notes, from the same strings as the notebook

Content is defined in this file so that it can be reviewed in git. Numbers are never typed into the text: they are
queried from the objective databases (read-only) or read from configuration and report files when the notebook runs.
Every formula below was checked against the implementation named next to it.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOK_PATH = HERE / "Kambale_Thesis_Results.ipynb"
MATH_PATH = HERE / "MATH_NOTES.md"

CELLS: list[tuple[str, str, list[str]]] = []


def _clean(text: str) -> str:
    return textwrap.dedent(text).strip("\n") + "\n"


def MD(text: str) -> None:
    CELLS.append(("markdown", _clean(text), []))


def CODE(text: str, tags: tuple[str, ...] = ()) -> None:
    CELLS.append(("code", _clean(text), list(tags)))


# =====================================================================================================================
# Mathematical notes. One list of markdown strings per objective. The notebook and MATH_NOTES.md use the same strings.
# =====================================================================================================================

MATH: dict[str, list[str]] = {}

MATH["O1"] = [
    r'''
**Straight-hole geometry** (`src/kambale/geometry.py`, `straight_hole_offsets`). With interval midpoint
$m=(\text{DEPTH\_FROM}+\text{DEPTH\_TO})/2$, dip $\delta$ (signed from horizontal, negative downward) and azimuth
$\alpha$ (clockwise from north), the offsets from the collar are

$$\Delta E = m\cos\delta\,\sin\alpha,\qquad \Delta N = m\cos\delta\,\cos\alpha,\qquad \Delta Z = m\sin\delta .$$

The declared orientation is the one recorded in the Objective 2 configuration (`geometry.declared_dip_deg`,
`geometry.declared_azimuth_deg`). Vertical values are relative to the collar. No absolute elevation is produced
(`geometry.absolute_elevation_allowed = False`).
''',
    r'''
**Drill-line grouping and collar-pair check** (`geometry.py`, `assign_drill_lines`, `pair_discrepancies`). Holes are
grouped by their nominal Northing, with line code $\text{NOM\_N}\{\operatorname{round}(N_0)\}$. The discrepancy between the
UTM collar pair and the Easting/Northing pair of each hole is the horizontal distance
$\sqrt{(E_{\text{UTM}}-E)^2+(N_{\text{UTM}}-N)^2}$.
''',
    r'''
**Graphitic label rule DESIGN_8_2_v1** (`src/kambale/labels.py`, `evidence` and `design_8_2`). Three logging
indicators are evaluated per interval: $s$ = rock code is `Sgs`; $g$ = a graphite mineral is logged in the mineral
fields; $c$ = the comment describes graphite or graphitic material. Let $k=s+g+c$ be the number of positive indicators.
The rule is

$$
\text{label}=\begin{cases}
\text{UNRESOLVED} & \text{if } s=0 \text{ and no comment is present}\\
\text{NEGATIVE}   & \text{if } k=0\\
\text{AMBIGUOUS}  & \text{if } (s=0 \text{ and } k\ge 1) \text{ or } (\text{comment present and } c=0) \text{ or } k=1\\
\text{POSITIVE}   & \text{otherwise.}
\end{cases}
$$

The approved rule text is stored with its SHA-256 definition hash in the database (`graphite_label_rules`). Only
POSITIVE and NEGATIVE intervals form the binary target; AMBIGUOUS and UNRESOLVED intervals are excluded. The
sensitivity rules (ALL3_v1, ANY_v1, RECON_2OF3_v1 and its trace-excluded variant) are PROPOSED and are used only to show
how far the labels depend on the rule.
''',
    r'''
**Evidence conflict.** An interval is a conflict when at least one indicator is positive and at least one is negative
(`labels.py`, `evidence`: `conflict = 1 if n_pos >= 1 and n_neg >= 1`). Conflicts are counted in
`interval_label_evidence.label_conflict`.
''',
]

MATH["O2"] = [
    r'''
**Indicator.** For a binary interval $\mathbf u$ with label $y(\mathbf u)\in\{\text{POSITIVE},\text{NEGATIVE}\}$,
$i(\mathbf u)=1$ if POSITIVE (graphitic) and $i(\mathbf u)=0$ if NEGATIVE. AMBIGUOUS and UNRESOLVED intervals are not
used (`variogram_config.yaml`, `label_rule`).
''',
    r'''
**Experimental indicator semivariogram** (`src/kambale/objective_2/variogram.py`, `compute`; `pairs.py`,
`accumulate`). For the set $N(h)$ of pairs $(\alpha,\beta)$ whose lag falls in a bin centred on $h$, with $N_{\text{pairs}}=|N(h)|$:

$$\hat\gamma(h)=\frac{1}{2N(h)}\sum_{(\alpha,\beta)\in N(h)}\bigl(i(\mathbf u_\alpha)-i(\mathbf u_\beta)\bigr)^2
=\frac{\#\{\text{pairs with } i_\alpha\ne i_\beta\}}{2\,N_{\text{pairs}}}\quad\text{(EQUAL\_PAIR weighting).}$$

Under EQUAL_HOLE weighting each pair carries weight $w_{\alpha\beta}=1/(n_{h(\alpha)}\,n_{h(\beta)})$, where $n_h$ is the
number of binary intervals in hole $h$ (`pairs.py`, `accumulate`), and
$\hat\gamma(h)=\sum w_{\alpha\beta}(i_\alpha-i_\beta)^2/(2\sum w_{\alpha\beta})$. A bin is supported only when it holds at
least `min_pairs_per_bin` pairs and `min_independent_hole_pairs_per_bin` distinct hole pairs (`variogram_config.yaml`).
The marginal variance is $p(1-p)$, with $p$ the prevalence of the binary target.
''',
    r'''
**Lag definitions.** Between-hole pairs use two different holes (`within = EXCLUDED`). The lateral basis uses the
horizontal lag $h=\sqrt{\Delta E^2+\Delta N^2}$ and keeps only pairs with $|\Delta Z|\le$ `max_abs_dz_m`
(`variogram_config.yaml`, `lateral_between_hole`). The within-hole (down-hole) experiment uses only pairs inside one hole,
with the lag equal to the separation along the hole (`downhole_within_hole`, 1-m bins).
''',
    r'''
**Models** (`src/kambale/objective_2/fitting.py`, `gamma_model`). With nugget $c_0$, structured sill $c_1$ and range $a$:

$$\gamma_{\text{sph}}(h)=c_0+c_1\Bigl(\tfrac32 u-\tfrac12 u^3\Bigr),\quad u=\min(h/a,1);\qquad
\gamma_{\text{exp}}(h)=c_0+c_1\bigl(1-e^{-3h/a}\bigr).$$

For the exponential model $a$ is the **practical range**: the lag at which the semivariance reaches 95 per cent of
$c_0+c_1$. The code uses the factor $3h/a$ exactly as written.
''',
    r'''
**Constrained weighted least squares** (`fitting.py`, `fit`). The parameters minimise
$\sum_k w_k\bigl(\hat\gamma_k-\gamma(h_k;c_0,c_1,a)\bigr)^2$ with $w_k=\sqrt{N_k/\hat\gamma_k^2}$ (the Cressie weighting
$N/\gamma^2$ in squared form). Bounds: $0\le c_0\le p(1-p)$, $0\le c_1\le 1.5\,p(1-p)$, and $a$ between the first
supported lag centre and the maximum lag. Three starting points are tried and the lowest cost is kept.
''',
    r'''
**Identifiability and stability** (`fitting.py`, `fit` and `stability`). A fit is NOT_IDENTIFIABLE when fewer supported
bins than `min_supported_bins_for_fit` exist, or when the fit sits on a constraint: range at the smallest lag, range at
the upper bound, structured sill below `model_fitting.min_structured_sill_fraction` of $p(1-p)$, or sill at its upper bound. A fit is FITTED otherwise.
Leave-one-line-out stability: each line is removed and the model refitted. The fit is STABLE only when every refit is
FITTED and every range ratio $a_{(-j)}/a$ lies inside `model_fitting.stable_if_range_ratio_between`.
''',
    r'''
**Weathering front** (`src/kambale/objective_2/weathering.py`, `extract_fronts`, `front_semivariogram`,
`interpolation_check`, `idw_predict`). The front of a hole is the relative depth of the top of its shallowest interval coded
`mw` or `sw` (`weathering_config_O2-CFG-2026.11.06-5.yaml`, `weathering_front`). Continuity is measured as the semivariogram of
the front elevation $z_f$ between holes (`weathering_front.continuity.semivariogram`) and by inverse-distance
interpolation with the power and neighbour count of `weathering_front.continuity.interpolation_check`. Leave-one-hole-out and leave-one-line-out skill ratios are
$\text{RMSE}_{\text{IDW}}/\text{RMSE}_{\text{training mean}}$; a scheme is INTERPOLABLE only if the ratio is at or below
the configured threshold.
''',
    r'''
**Fresh-rock sample.** The configuration calls the intervals coded `mw` or `sw` the fresh-rock sample
(`fresh_rock_variography.sample`). This is the sample used for the lateral experiments LATERAL_FRESH_COLLAR (pairs at equal
relative elevation) and LATERAL_FRESH_FRONT (pairs at equal depth below their own front). Confidence bands come from a
hole bootstrap (`fresh_rock_variography.hole_bootstrap`). The word "fresh" follows the configuration; it is not a
claim that these intervals are unweathered.
''',
    r'''
**Structural frame: apparent-dip search** (`src/kambale/objective_2/structural.py`, `plane_coordinates`, `alignment`,
`select_dip`). For an apparent dip $d$, each interval is placed on a plane by
$s=z\cos d+x\sin d$ (across the layering) and $t=x\cos d-z\sin d$ (along the plane). Pairs are within-line between-hole
pairs with $|\Delta s|\le$ the tolerance in the structural configuration (`max_abs_ds`), binned by $|\Delta t|$. The alignment score is

$$A(d)=1-\frac{\overline{\hat\gamma}_{1,2}(d)}{p(1-p)},$$

where $\overline{\hat\gamma}_{1,2}(d)$ is the mean semivariance over the first two supported lag bins. The selected dip is the
$d$ on the grid $[-80^\circ,80^\circ]$ with the largest $A(d)$; ties go to the dip closest to zero.
''',
    r'''
**Selection null** (`structural.py`, `circular_shift`, `null_p_value`). Each hole's indicator sequence, ordered by depth, is
rotated by its own random offset; this keeps within-hole structure and destroys between-hole alignment. The whole dip grid
is rescored in each permutation. With $n_{\text{perm}}$ permutations,

$$p=\frac{1+\#\{\max_d A^{\text{null}}_b(d)\ge \max_d A^{\text{obs}}(d)\}}{n_{\text{perm}}+1}.$$

A PROVISIONAL structural result needs $p<\alpha$, enough lines whose own selected dip lies within the tolerance, and a stable
FITTED model. Otherwise the decision is NOT_IDENTIFIABLE (structural frame). The apparent dip is a statistically selected
direction, not a measured orientation of the ore.
''',
    r'''
**Down-hole variogram.** The within-hole exponential fit (fit 16 in `variogram_fits`, from the `DOWNHOLE_WITHIN`
experiment) supplies the nugget $c_0$, sill $c_1$ and practical range $a_d$ that Objective 5 reuses as its down-hole
correlogram. The fitted parameters are read from `variogram_fit_parameters`.
''',
]

MATH["O3"] = [
    r'''
**Target and predictors** (`src/kambale/objective_3/features.py`; `config/objective_3/model_config.yaml`, `features`).
The target is $y(\mathbf u)=1$ for POSITIVE and $0$ for NEGATIVE (rule DESIGN_8_2_v1). Predictor set TREND is
$\mathbf x=(E,N,Z_{\text{rel}})$. Predictor set TREND_WF adds the depth below the modelled weathering front:

$$d_{\text{wf}}(\mathbf u)=\hat z_f(E,N)-Z_{\text{rel}}\qquad(\text{positive below the front}).$$
''',
    r'''
**Fold-safe weathering-front surface** (`src/kambale/objective_3/weathering_front.py`, `idw`, `feature_for_fold`). The
front elevation at a location is an inverse-distance weighted average of the front elevations of the nearest training
holes (`features.derived.depth_below_weathering_front_m.surface`), with weights $w_k=1/d_k^2$:

$$\hat z_f(\mathbf x)=\frac{\sum_k w_k z_{f,k}}{\sum_k w_k}.$$

For a training row the hole's own front is left out; test rows use only training holes. `fold_safety_check` confirms that
altering test-hole fronts does not change the training features.
''',
    r'''
**Logistic regression (BASE_LOGISTIC, BASE_LOGISTIC_WF)** (`models.py`, `make_estimator`). Predictors are standardised
and the model is $p(\mathbf x)=\sigma(\beta_0+\boldsymbol\beta^\top\mathbf x)$ with $\sigma(t)=1/(1+e^{-t})$, fitted by
L2-penalised maximum likelihood (`LogisticRegression`, inverse regularisation $C$ from the grid in
`models.logistic.grid`).
''',
    r'''
**Tree ensembles as probability estimators** (`models.py`, `make_estimator`, `predict_positive`). M2_RF is a
random forest: $p(\mathbf x)$ is the average over trees of the class-1 fraction in the leaf reached by $\mathbf x$.
M2_HGB is a histogram gradient-boosting classifier (`HistGradientBoostingClassifier`), which models the log-odds as a sum
of regression trees, $p(\mathbf x)=\sigma(F(\mathbf x))$. The hyperparameter grids are in `models.random_forest.grid` and
`models.gradient_boosting.grid`. XGBoost is not used; the report records that it was not installed.
''',
    r'''
**Inner selection** (`training.py`, `_standard_candidate`; `models.py`, `inner_cv`, `select_trials`). Within each outer
training fold, hyperparameters are chosen by cross-validation with `inner_cv.n_folds` folds grouped by hole (`GROUP_K_FOLD_BY_HOLE`), minimising the
mean log loss $-\frac1n\sum_i[y_i\log p_i+(1-y_i)\log(1-p_i)]$. The composites M2_SEL and M2_WF_SEL copy whichever of the
RF or HGB pair has the lower inner score. No outer test result enters this choice.
''',
    r'''
**Platt calibration** (`models.py`, `platt_fit`, `platt_apply`). Random forest and gradient-boosting outputs (not the
logistic model) are recalibrated by $p_{\text{cal}}=\sigma(a+b\,\operatorname{logit}p_{\text{raw}})$, fitted on the inner
out-of-fold predictions only. Probabilities are clipped to $[\varepsilon,1-\varepsilon]$ with
$\varepsilon=10^{-6}$ (`calibration.clip_epsilon`).
''',
    r'''
**Decision threshold** (`models.py`, `youden_threshold`). The threshold $t$ maximises Youden's index
$J(t)=\text{sensitivity}(t)+\text{specificity}(t)-1$ on the inner predictions; ties go to the threshold closest to 0.5.
The threshold is used only to classify; probabilities are evaluated in Objective 4.
''',
    r'''
**Indicator kriging, M1** (`src/kambale/objective_3/kriging.py`, `simple_kriging`, `neighbourhoods`, `_cov`). The
estimate at $\mathbf u_0$ is simple kriging of the indicator with known mean $m$ (training prevalence) and
variance $m(1-m)$:

$$\hat p(\mathbf u_0)=m+\boldsymbol\lambda^\top(\mathbf i-m\mathbf 1),\qquad \boldsymbol\lambda=\mathbf K^{-1}\mathbf k,$$

where $K_{ij}=C(h_{ij})$ and $k_i=C(h_{i0})$, with $C(0)=m(1-m)$ and the exponential covariance
$C(h)=c_1\,e^{-3h/a}$ for $h>0$. The distance $h$ is **horizontal** (E, N) and only training values in the same depth band
($|\Delta Z|\le$ `depth_band_m`) are used, between `min_neighbours` and `max_neighbours`. Range $a$ and nugget fraction
$c_0/(c_0+c_1)$ come from the predeclared grid, or PURE_NUGGET ($c_1=0$, where $\hat p=m$). The covariance is chosen per fold
by inner-CV log loss (`select_covariance`).
''',
    r'''
**Hybrid M3** (`training.py`, `_m3`; `kriging.m3` in the configuration). Let $\tilde p^{\text{trend}}$ be the calibrated
M2_WF_SEL probability and $r_\alpha=y_\alpha-\tilde p^{\text{trend}}_\alpha$ the residual, with the trend cross-fitted inside
the training fold. The residual is kriged by simple kriging with mean 0 and sill equal to the residual variance, and

$$\hat p_{\text{M3}}(\mathbf u_0)=\operatorname{clip}_{[\varepsilon,1-\varepsilon]}\bigl(\tilde p^{\text{trend}}(\mathbf u_0)+\hat r(\mathbf u_0)\bigr).$$

If the inner selection chooses PURE_NUGGET, $\hat r\equiv0$ and M3 equals its trend. The run is then labelled
FALLBACK_ML_ONLY. That label is the outcome, not an omission.
''',
    r'''
**Leakage controls** (`training.py`, `_leakage_audit`). Each run writes audit rows for: predictors safe and available at
prediction; outer test points absent from the training manifest; variograms belonging to their training fold; calibration
using inner data only; no full-data fit inside out-of-fold predictions; and predictions being test members of their fold.
''',
]

MATH["O4"] = [
    r'''
**Pooled Brier score** (`src/kambale/objective_4/metrics.py`, `brier`). For predictions $p_i$ and outcomes $y_i$ with
weights $w_i$,

$$B=\frac{\sum_i w_i\,(p_i-y_i)^2}{\sum_i w_i}.$$

The primary weighting is INTERVAL ($w_i=1$). The secondary weighting EQUAL_HOLE uses $w_i=1/n_{h(i)}$, where $n_{h(i)}$ is the
number of intervals in the hole of interval $i$; the stored weights sum to one within each hole
(`evaluation_population.weight_equal_hole`).
''',
    r'''
**Log loss** (`metrics.py`, `log_loss`). $L=-\dfrac{\sum_i w_i[y_i\log q_i+(1-y_i)\log(1-q_i)]}{\sum_i w_i}$, with
$q_i$ the prediction clipped to $[\varepsilon,1-\varepsilon]$ and $\varepsilon=10^{-6}$ (`evaluation.epsilon`).
''',
    r'''
**ROC-AUC and PR-AUC** (`metrics.py`, `roc_auc`, `pr_auc`). ROC-AUC is the weighted area under the ROC curve
(`roc_auc_score` with `sample_weight`). PR-AUC is the weighted average precision,
$\sum_k (R_k-R_{k-1})P_k$ over the thresholds, with $P_k$ precision and $R_k$ recall (`average_precision_score`). Both
are undefined when only one class is present; undefined values are reported as such and are not coerced to numbers.
''',
    r'''
**Expected calibration error and reliability bins** (`metrics.py`, `reliability_bins`, `ece_from_bins`). Predictions
fall into bins on $[0,1]$ (edges in `evaluation.calibration_bins`). Adjacent bins are merged upward until each holds at
least `evaluation.calibration_min_bin_n` weight. For bin $b$ with weight $n_b$, mean prediction $\bar p_b$ and observed rate
$\bar y_b$,

$$\text{ECE}=\sum_b\frac{n_b}{n}\,|\bar p_b-\bar y_b|.$$

Each observed rate has a Wilson score interval.
''',
    r'''
**Calibration intercept and slope (diagnostic only)** (`metrics.py`, `calibration_fit`). A logistic regression
$y\sim\sigma(a+b\,\operatorname{logit}p)$ is fitted to the pooled held-out predictions with weights. The intercept $a$ and
slope $b$ describe the existing probabilities. They are never applied to them (`evaluation.calibration.recalibration_on_holdout = False`).
''',
    r'''
**Paired differences** (`evaluation.py`, `_pair_rows`). For each configured pair $(a,b)$,

$$\Delta_{ab}=B_b-B_a,$$

so a negative value means that model $b$ has the lower Brier score. The same definition is used for log loss and AUC
differences in the database.
''',
    r'''
**Hole-cluster bootstrap** (`evaluation.py`, `_bootstrap`, `_update_pair_ci`). Holes are resampled with replacement
(`evaluation.bootstrap.n_replicates` replicates, fixed seed); all intervals of a drawn hole are kept and the same
observations enter both models. The 95 per cent interval is the 2.5th to 97.5th percentile of the replicate differences.
A LINE_CLUSTER design with five lines is kept as a sensitivity analysis. The hole design is the primary one because the
hole is the unit that carries most of the dependence in the data.
''',
    r'''
**Power label and detectable difference** (`evaluation.py`, `power_label`). A pair is RESOLVED when its hole-cluster
interval excludes zero. Otherwise it is UNRESOLVED and its detectable half-width is
$h=(\mathrm{CI}_{\text{high}}-\mathrm{CI}_{\text{low}})/2$. This is the half-width of the observed interval, the smallest
difference that this design could have distinguished. It is not an analytic power calculation.
''',
    r'''
**Decision rule** (`src/kambale/objective_4/decision.py`; `evaluation.decision` in the configuration). The selected model
is the distinct, fully covered model with the lowest pooled interval Brier score; the comparator is the next lowest. A
SUPPORTED_IMPROVEMENT requires all of the following: the hole-cluster interval of $B_{\text{sel}}-B_{\text{comp}}$ lies
entirely below zero; the selected model is better in at least `fold_consistency_min` of the five folds; calibration slope
within the configured range and $|\text{intercept}|$ within its limit; ROC-AUC not worse than the comparator by more than
`discrimination_margin_auc`; and coverage at least `coverage_threshold`. INCONCLUSIVE applies when the interval includes
zero or fold consistency is too low. NO_IMPROVEMENT applies when the point estimate is non-negative or the interval lies entirely
above zero.
''',
    r'''
**Identity of models** (`evaluation.py`, `_identical_keys`; `model_identities`). Two models are IDENTICAL when their
calibrated probabilities agree on every common interval within $10^{-12}$. Identical models are reported once, are not
ranked, and carry the reason NOT_COMPARABLE. M2_SEL, M2_WF_SEL and M3_HYBRID are identical to M2_RF, M2_RF_WF and M2_WF_SEL
respectively; the hybrid therefore adds nothing in this evaluation.
''',
]

MATH["O5"] = [
    r'''
**Grid and support zones** (`src/kambale/objective_5/grid.py`, `grid_axes`, `zone_from_distance`). Cells have the size in
`grid.cell_size_m` (horizontal easting and northing, and vertical), with the vertical axis relative to the collar. The horizontal extent is the
collar bounding box expanded by a margin, and each cell carries the nearest-collar distance $d(\mathbf u)$:

$$\text{zone}(\mathbf u)=\begin{cases}\text{INTERPOLATION} & d\le d_{\text{I}}\\ \text{EXTRAPOLATION} & d_{\text{I}}<d\le d_{\text{E}}\\ \text{NO\_SUPPORT} & d>d_{\text{E}}\end{cases}$$

with $d_{\text{I}}$ and $d_{\text{E}}$ from `support_zones.zones`. INTERPOLATION cells take the tier-2 model and
EXTRAPOLATION cells the tier-1 model. NO_SUPPORT cells get no probability.
''',
    r'''
**Depth support** (`grid.py`, `deepest_sampled_z`, `depth_support_labels`). A cell is DEPTH_EXTRAPOLATED when $z(\mathbf u)$ lies
below the deepest sampled $z$ of the holes within `support_zones.depth_support.neighbourhood_m` of it (or of the nearest
hole when none is within that distance). These cells are never classed as confident.
''',
    r'''
**Probability, uncertainty measures** (`src/kambale/objective_5/bootstrap.py`, `grid.py`). $p(\mathbf u)$ is the calibrated
probability of the zone's selected model at the cell, from the full-data final refit. The weathering-front surface on the
grid is the inverse-distance surface of Objective 3 built from the observed holes. The hole bootstrap gives, for each cell,
the 5th and 95th percentiles $[p_{\text{lo}},p_{\text{hi}}]$ over successful replicates, and the interval width is
$p_{\text{hi}}-p_{\text{lo}}$. Hyperparameters are fixed at the full-data selection; the estimator, front surface and
Platt calibration are refitted in each replicate.
''',
    r'''
**Model disagreement and entropy** (`grid.py`, `build_cells`, `entropy_bits`). Disagreement is
$D(\mathbf u)=|p_{\text{sel}}(\mathbf u)-p_{\text{ru}}(\mathbf u)|$ between the selected and runner-up calibrated models. Entropy,
in bits, is

$$H(p)=-p\log_2 p-(1-p)\log_2(1-p),$$

with $H=0$ at $p\in\{0,1\}$. Both are trend-based uncertainty from the selected models, not geostatistical uncertainty.
''',
    r'''
**Classification** (`src/kambale/objective_5/classify.py`, `classify_arrays`). With decision threshold $t$ and
disagreement limit $\delta$ (`classification` in the configuration):

- CONFIDENT_PRESENT if $p_{\text{lo}}\ge t$, $D<\delta$ and the cell is not DEPTH_EXTRAPOLATED;
- CONFIDENT_ABSENT if $p_{\text{hi}}<t$, $D<\delta$ and the cell is not DEPTH_EXTRAPOLATED;
- UNCERTAIN otherwise;
- NO_SUPPORT in the NO_SUPPORT zone.

The sensitivity classification repeats the rule with $t$ equal to the training prevalence.
''',
    r'''
**Scenario SIS with a locally varying mean** (`src/kambale/objective_5/simulate.py`, `simulate_realisation`, `sk_weights`,
`correlogram`, `scaled_coordinates`). The local mean $m(\mathbf u)$ is the calibrated M2_HGB_WF probability at each node. The
residual $i-m$ is simple-kriged with covariance

$$C(\mathbf u,\mathbf v)=\sqrt{m(\mathbf u)(1-m(\mathbf u))\,m(\mathbf v)(1-m(\mathbf v))}\;\rho(h_{\text{aniso}}),$$

where $\rho(0)=1$ and $\rho(h)=\dfrac{c_1}{c_0+c_1}e^{-3h}$ for $h>0$, with $c_0$, $c_1$ the down-hole nugget and sill, and the
anisotropy-scaled distance $h_{\text{aniso}}=\sqrt{(\Delta x^2+\Delta y^2)/a_h^2+\Delta z^2/a_v^2}$
(`scenario_simulation.anisotropy.scaled_distance`).
''',
    r'''
**Sequential draw** (`simulate.py`, `simulate_realisation`). Nodes are visited along a random path. At node $\mathbf u$ the
conditional probability is

$$p^*(\mathbf u)=\operatorname{clip}_{[0,1]}\Bigl(m(\mathbf u)+\sum_i\lambda_i\,(i_i-m_i)\Bigr),\qquad i(\mathbf u)=\mathbb 1[U<p^*(\mathbf u)],$$

with $U$ uniform. The neighbours are at most 24 conditioning intervals and at most 12 previously simulated nodes within
scaled distance 1.0 (`scenario_simulation.kriging`). A node with no neighbours takes its local mean. The
conditioning data are the binary intervals at their own midpoints.
''',
    r'''
**Vertical practical range** (`simulate.py`, `vertical_range`). The lateral range $a_h$ is an **assumed** scenario value. The
vertical range $a_v$ is set so that the practical range along the hole direction, at the plunge $\delta$ given by `scenario_simulation.anisotropy.vertical_range_rule`, equals
the fitted down-hole practical range $a_d$:

$$\frac{1}{a_v^2}=\frac{1/a_d^2-\cos^2\delta/a_h^2}{\sin^2\delta}.$$

The scenario is INFEASIBLE when the bracket is zero or negative, which happens when $a_h\le a_d\cos\delta$.
''',
    r'''
**Volume and connectivity** (`simulate.py`, `connectivity`, `write_results`). For realisation $r$, the graphitic grid volume is
$V_r=\Delta V\sum_k i_r(\mathbf u_k)$ with $\Delta V=200\ \text{m}^3$. The expected volume is
$\Delta V\sum_k m(\mathbf u_k)$. Connected components are counted with a 26-neighbour structuring element (`STRUCTURE_26`),
and the largest-component share is the fraction of positive cells in the largest component. P10, P50 and P90 are
percentiles over the realisations of a scenario (linear interpolation, `numpy.percentile`). Scenarios are reported separately.
''',
    r'''
**Reproduction checks.** The down-hole experimental semivariogram of realisations is compared with the stored Objective 2
correlogram at the configured lags, and the mean simulated frequency over the domain is compared with the mean local
mean (`scenario_simulation.outputs_per_scenario.reproduction`). Both are gates in the Objective 5 run.
''',
]

# =====================================================================================================================
# Notebook cells
# =====================================================================================================================

MD(r'''
# Kambale graphite deposit: results notebook

**Thesis.** Hybrid Machine Learning–Indicator Geostatistical Modelling for Spatially Validated Three-Dimensional Prediction
and Uncertainty Characterization of Graphitic Domains at the Kambale Graphite Deposit, Ghana.

**Author.** Dickson Abdul-Wahab

**About this file.** This notebook is generated by `notebooks/build_notebook.py` and committed without outputs. Numbers
are queried live from the objective databases (read-only) or read from configuration and report files when the notebook
runs. Nothing is typed in by hand. Use `MODE = "present"` for the stored results (fast). `MODE = "reproduce"` re-runs the
pipeline on a copy of the repository and takes about 15 minutes.
''')

CODE(r'''
MODE = "present"      # "present": show stored results. "reproduce": also re-run the pipeline on a copy (about 15 minutes).
RUN_GATES = True      # False skips the gate run (used for quick test executions).
''', tags=("parameters",))

CODE(r'''
import html
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from IPython.display import HTML, Image, Markdown, display


def find_repo(start=None):
    """Walk up from the working directory until the folder holding pyproject.toml and src/kambale is found."""
    here = Path(start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "kambale").is_dir():
            return candidate
    raise RuntimeError(f"repository root not found above {here}")


REPO = find_repo()
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kambale.notebook.env import config_receipts, database_manifest_check, environment_summary
from kambale.notebook.gates import run_gates
from kambale.notebook.paths import CONFIG_FILES, DB_PATHS, OUTPUT_DIRS
from kambale.notebook.readonly import list_tables, query
from kambale.notebook.receipts import receipt_check
from kambale.notebook.reproduce import reproduce

pd.set_option("display.max_columns", 40)
pd.set_option("display.width", 180)
pd.set_option("display.max_colwidth", 110)
assert MODE in ("present", "reproduce"), f"MODE must be 'present' or 'reproduce', not {MODE!r}"


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def load_yaml(relative):
    """Parse a configuration file. A file that is not valid YAML is reported, not hidden."""
    try:
        return yaml.safe_load(read_text(REPO / relative))
    except yaml.YAMLError as exc:
        return {"_yaml_error": " ".join(str(exc).split())[:300]}


def flat_items(obj, prefix="", out=None):
    out = [] if out is None else out
    if isinstance(obj, dict):
        for key, value in obj.items():
            flat_items(value, f"{prefix}.{key}" if prefix else str(key), out)
    elif isinstance(obj, list) and len(obj) > 6:
        out.append((prefix, f"list of {len(obj)} items; first {obj[0]!r}"[:170]))
    else:
        out.append((prefix, repr(obj)[:170]))
    return out


def config_table(cfg, pattern=None, limit=60):
    rows = flat_items(cfg)
    if pattern:
        rows = [row for row in rows if re.search(pattern, row[0])]
    return pd.DataFrame(rows[:limit], columns=["key", "value"])


def as_frame(obj):
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, dict):
        return pd.DataFrame(list(obj.items()), columns=["item", "value"])
    if isinstance(obj, (list, tuple)) and obj and isinstance(obj[0], dict):
        return pd.DataFrame(obj)
    return pd.DataFrame({"value": [str(obj)]})


def section_text(text, heading):
    """Text from a heading line up to the next level-2 heading."""
    start = text.find(heading)
    if start < 0:
        return f"*(heading not found in file: {heading})*"
    end = text.find("\n## ", start + len(heading))
    block = text[start:end if end > 0 else None].strip()
    # Quoted report headings become level-4 headings without their report numbering,
    # so they do not break this notebook's own outline.
    return re.sub(r"^#{1,6} +(?:\d+\.\s*)?", "#### ", block, flags=re.M)


def between(text, start_marker, end_marker):
    start = text.find(start_marker)
    if start < 0:
        return f"*(text not found: {start_marker})*"
    end = text.find(end_marker, start + len(start_marker))
    return text[start:end if end > 0 else None].strip()


def show_figures(key, frame, width=900):
    """Show the registered PNG files of one output folder, with the registry title as caption."""
    folder = Path(OUTPUT_DIRS[key]["figures"])
    for _, row in frame.iterrows():
        fid = str(row["figure_id"])
        matches = sorted({*folder.glob(fid.replace("-", "_") + "*.png"), *folder.glob(fid + "*.png")})
        if not matches:
            display(Markdown(f"**{fid}**: no PNG found in `{folder}`"))
            continue
        for png in matches:
            display(Markdown(f"**{fid}. {row['title']}** (status {row['status']}); file `{png.name}`"))
            display(Image(filename=str(png), width=width))


def callout(text):
    display(HTML('<div style="border:2px solid #b45309;background:#fff7ed;padding:10px 14px;border-radius:6px;'
                 'margin:8px 0">' + text + "</div>"))
''')

MD(r'''
## 1. How to read this notebook

**What the two modes prove.**

- **Mode A (`MODE = "present"`)** shows the stored results of the five objectives. It checks that the environment,
  configurations, databases and receipts are consistent with the run reports, and that the verification gates pass on a copy
  of the repository. Every number is queried from a database read-only, so the notebook cannot alter the results.
- **Mode B (`MODE = "reproduce"`)** re-runs the pipelines on a copy of the repository and compares the regenerated tables and
  figures with the registered ones. It never writes to the real databases. It is the stronger claim, and it takes about 15 minutes.

**The evidence chain.** Each result rests on the following links, in order:

1. a **predeclared configuration** (a YAML file with a version, committed before its results were computed);
2. **locked inputs** with SHA-256 receipts (each database is recorded with its content hash and receipt);
3. **SQL-registered figures and tables** (every figure and table names the SQL that produced it, and its hash is recorded);
4. **STOP and WARN gates** (checks that stop a run when violated, and report warnings when a result needs care);
5. **tests** (unit and integration tests run after each stage).

**How the objectives fit together.** Objective 1 builds and checks the drill-hole database and defines the graphitic label.
Objective 2 characterises occurrence, continuity and the weathering front. Objective 3 builds indicator, machine-learning
and hybrid models and validates them spatially. Objective 4 evaluates the locked models on held-out data. Objective 5
turns the locked models into three-dimensional probability, uncertainty and scenario products.

**Glossary.**

| Term | Meaning in this project |
|---|---|
| Indicator | 1 for a graphitic (POSITIVE) interval, 0 for a non-graphitic (NEGATIVE) interval. Only binary intervals enter the models. |
| Variogram (semivariogram) | Half the mean squared difference between indicator values of pairs of intervals, as a function of separation (lag). |
| Practical range | For the exponential model, the lag at which the semivariance reaches 95 per cent of its sill. Beyond it, pairs are treated as unrelated. |
| Nugget | The semivariance at zero lag, which measures variation that is not spatially structured at the sampled scale (or sampling error). |
| Sill | The total semivariance at large lags (nugget plus structured sill). For an indicator, the sill is near $p(1-p)$. |
| Kriging | Estimation as a weighted average of nearby data, with weights from a covariance model that describes spatial correlation. |
| Brier score | The mean squared difference between predicted probability and outcome. Lower is better; 0 is perfect, and always predicting the prevalence gives $p(1-p)$. |
| Calibration | Agreement between predicted probabilities and observed frequencies. Judged here by reliability bins, ECE and a diagnostic intercept and slope. |
| AUC | Area under the ROC curve: the probability that a random positive interval scores higher than a random negative one. PR-AUC is the analogue for precision and recall. |
| Spatial cross-validation | Validation in which whole blocks are held out (here whole drill lines, or whole holes interleaved within lines), so that the test data are spatially separated from the training data. |
| Tier 1 extrapolation | Predicting a whole drill line from the other lines. Test points are far from training data, beyond the lateral range of any supported structure. |
| Tier 2 interpolation | Predicting an undrilled position between drilled holes of the same line, at about one hole spacing. |
| Bootstrap | Resampling with replacement to estimate uncertainty. Here it resamples holes (or lines), keeping all intervals of a drawn unit together. |
| Entropy | Binary entropy of a probability, in bits. It is 0 at $p=0$ or $1$ and largest at $p=0.5$. |
| SIS | Sequential indicator simulation: a random path through the grid, drawing each cell from a conditional probability given data and earlier draws. |
| Locally varying mean | The local probability $m(\mathbf u)$ used as the mean of the simulation, so that the large-scale trend comes from the model and the simulation supplies the residual structure. |
| Realisation | One simulated 3-D indicator field from SIS. Summaries are taken across realisations. |
| Connectivity | Whether positive cells form one body. Measured here as 26-neighbour connected components and the share of positive volume in the largest one. |
| Support zone | A region defined by distance to the nearest collar (INTERPOLATION, EXTRAPOLATION or NO_SUPPORT), each with its own validated model tier. |

**Language.** "Relative" depth means depth below the collar; collar elevations are absent, so no absolute elevation or
grade, tonnage or resource statement is made anywhere in this notebook.
''')

MD(r'''
## 2. Reproducibility summary

The cells below check the environment, the predeclared configurations, the database manifest and receipts, and the
verification gates. The gate run uses a copy of the repository, so it does not change any file.
''')

CODE(r'''
display(Markdown("### Environment"))
display(as_frame(environment_summary()))
display(Markdown("### Predeclared configurations: each was committed before its results were computed"))
display(as_frame(config_receipts()))
display(Markdown("### Database manifest: SHA-256 of each database against the recorded manifest"))
display(as_frame(database_manifest_check()))
display(Markdown("### Receipts: content hash and row count of each upstream snapshot"))
display(as_frame(receipt_check()))
''')

CODE(r'''
if RUN_GATES:
    gates = as_frame(run_gates())
    display(Markdown("### Verification gates: objective by status (number of gates)"))
    display(pd.crosstab(gates["objective"], gates["status"], margins=True))
    display(Markdown("Gates with a WARN or STOP status are discussed in the objective sections."))
    display(HTML("<details><summary><b>Full gate table</b> (click to expand)</summary>"
                 + gates.to_html(index=False) + "</details>"))
else:
    display(Markdown("*Gates were not run in this execution (`RUN_GATES = False`).*"))
''')

CODE(r'''
if MODE == "reproduce":
    rep = reproduce(keep=False)
    rep = rep if isinstance(rep, dict) else {"verdict": str(rep)}
    display(Markdown("### Mode B: reproduction on a copy of the repository"))
    display(Markdown(f"Working copy: `{rep.get('workdir', 'not reported')}`"))
    display(as_frame(rep.get("steps", [])))
    if "tables" in rep:
        display(Markdown("**Table comparison (regenerated against registered)**"))
        display(as_frame(rep["tables"]))
    if "figures" in rep:
        display(Markdown("**Figure comparison**"))
        display(as_frame(rep["figures"]))
    callout("<b>Reproduction verdict:</b> " + html.escape(str(rep.get("verdict", "not reported")))
            + "<br><b>Scope:</b> " + html.escape(str(rep.get("scope_note", ""))))
else:
    display(Markdown(
        "**Mode B was not run (`MODE = \"present\"`).** To run it, execute the notebook with `-p MODE reproduce`. "
        "It re-runs the pipelines on a copy of the repository (about 15 minutes), compares the regenerated tables and "
        "figures with the registered ones, and never changes the real databases. See `notebooks/README.md`."))
''')

# ---------------------------------------------------------------------------------------------------------------------
# Objective sections. Each has the same sub-structure: a objective and refinement; b predeclared configuration;
# c key results (live queries); d figures; e mathematical notes; f how to explain; g claims.
# ---------------------------------------------------------------------------------------------------------------------

MD("## 3. Objective 1: database, QA/QC and the graphitic definition")
MD("### 3a. Objective and operational refinement")
CODE(r'''
SPEC_PATH = REPO / "specs" / "01_thesis_scope_and_objective_traceability.md"
SPEC = read_text(SPEC_PATH) if SPEC_PATH.exists() else ""


def synopsis_objective(n):
    """Verbatim synopsis objective n, read from specs/01 at run time."""
    block = section_text(SPEC, "## Fixed synopsis objectives")
    items = re.findall(r"^(\d)\. (.*)$", block, flags=re.M)
    for number, text in items:
        if int(number) == n:
            return text
    return "(objective not found in specs/01)"


def refinement_rows(n):
    """Operational refinement row n from the table in specs/01 (objectives 2 to 4)."""
    block = section_text(SPEC, "## Operational refinement")
    for line in block.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0] == str(n):
            return cells
    return None


def objective_block(n):
    display(Markdown(f"**Synopsis objective {n} (verbatim from specs/01).** " + synopsis_objective(n)))
    row = refinement_rows(n)
    if row:
        display(Markdown(
            "**Operational refinement (specs/01, 2026-11-06).**\n\n"
            f"- Original operationalisation: {row[1]}\n"
            f"- Refined operationalisation: {row[2]}\n"
            f"- Reason (evidence): {row[3]}\n"
            f"- Achievement under the refinement: {row[4]}"))
    else:
        display(Markdown("*No operational refinement is recorded for this objective in specs/01.*"))


objective_block(1)
''')

MD("### 3b. What was predeclared")
CODE(r'''
o1_cfg = {name: load_yaml(f"config/{name}") for name in
          ["label_rules.yaml", "coordinate_decisions.yaml", "dem.yaml", "qaqc_thresholds.yaml"]}
for name, cfg in o1_cfg.items():
    display(Markdown(f"**config/{name}**"))
    display(config_table(cfg, limit=25))
''')

MD("### 3c. Key results (queried live from the Stage A database)")
CODE(r'''
o1_counts = query("o1", """
SELECT
  (SELECT COUNT(*) FROM holes)                                              AS holes,
  (SELECT COUNT(*) FROM v_intervals)                                        AS intervals_1m,
  (SELECT ROUND(SUM(interval_length_m), 1) FROM v_intervals)                AS logged_m,
  (SELECT COUNT(*) FROM v_intervals WHERE rock_code_raw = 'Sgs')            AS sgs_intervals,
  (SELECT COUNT(DISTINCT hole_id) FROM v_intervals WHERE rock_code_raw = 'Sgs') AS sgs_holes,
  (SELECT COUNT(*) FROM interval_label_evidence WHERE label_conflict = 1)   AS label_conflicts,
  (SELECT COUNT(*) FROM drill_lines)                                        AS drill_lines
""")
o1_rules = query("o1", """
SELECT rule_id, rule_family, status, approved_by, SUBSTR(definition_sha256, 1, 12) AS definition_sha256_prefix
FROM graphite_label_rules ORDER BY rule_family, rule_id
""")
o1_candidates = query("o1", """
SELECT rule_id, rule_family, rule_status, label_state, n_intervals, ROUND(logged_m, 1) AS logged_m
FROM v_label_candidate_counts ORDER BY rule_id, label_state
""")
o1_conflicts = query("o1", """
SELECT evidence_pattern, label_review_status, n_intervals, ROUND(logged_m, 1) AS logged_m
FROM v_label_disagreement ORDER BY n_intervals DESC
""")
o1_qaqc = query("o1", """
SELECT severity, status, COUNT(*) AS checks, SUM(n_findings) AS findings
FROM v_qaqc_summary GROUP BY severity, status ORDER BY severity, status
""")
o1_lines = query("o1", """
SELECT line_code, nominal_northing_m, n_holes, n_intervals, status FROM v_drill_lines ORDER BY nominal_northing_m
""")
o1_depth = query("o1", """
SELECT ROUND(MIN(max_depth_m), 1) AS min_depth_m, ROUND(AVG(max_depth_m), 1) AS mean_depth_m,
       ROUND(MAX(max_depth_m), 1) AS max_depth_m FROM holes
""")
o1_rl = query("o1", """
SELECT rl_status, COUNT(*) AS holes FROM holes GROUP BY rl_status
""")
o1_recon = query("o1", """
SELECT test_name AS check_name, expected, observed, outcome, detail
FROM validation_test_results
WHERE test_group = 'RECONCILIATION'
  AND run_utc = (SELECT MAX(run_utc) FROM validation_test_results WHERE test_group = 'RECONCILIATION')
""")
display(Markdown("**Counts (interval = 1 m logged interval; holes are the 71 drill holes)**"))
display(o1_counts)
display(Markdown("**Reconciliation against the workbook and the preliminary thesis document**"))
display(o1_recon)
display(Markdown("**Graphitic label rules: status and approval (rule text is in the database)**"))
display(o1_rules)
display(Markdown("**Intervals by candidate rule and label state**"))
display(o1_candidates)
display(Markdown("**Evidence pattern of the 126 conflicting intervals and their review status**"))
display(o1_conflicts)
display(Markdown("**QA/QC checks by severity and status (checks, findings)**"))
display(o1_qaqc)
display(Markdown("**Drill lines (provisional grouping by nominal Northing)**"))
display(o1_lines)
display(Markdown("**Hole depth (m below collar) and collar elevation status**"))
display(o1_depth)
display(o1_rl)
''')

MD("### 3d. Figures")
CODE(r'''
o1_fig = query("o1", """
SELECT figure_id, title, stage_status AS status FROM figure_registry
WHERE objective = 'O1' AND kind = 'FIGURE' AND figure_id LIKE 'F%' ORDER BY figure_id
""")
show_figures("o1", o1_fig)
''')

MD("### 3e. Mathematical notes: Objective 1")
for _s in MATH["O1"]:
    MD(_s)

MD("### 3f. How to explain this result")
CODE(r'''
c = o1_counts.iloc[0]
cand = o1_candidates.set_index(["rule_id", "label_state"])["n_intervals"]
n_ambiguous = int(cand.get(("DESIGN_8_2_v1", "AMBIGUOUS"), 0))
n_binary = int(cand.get(("DESIGN_8_2_v1", "POSITIVE"), 0) + cand.get(("DESIGN_8_2_v1", "NEGATIVE"), 0))
rec = o1_recon.set_index("check_name")
display(Markdown(f"""
**Plain-language summary.** The workbook became a verified database of {int(c.holes)} drill holes and
{int(c.intervals_1m):,} contiguous 1-metre logging intervals ({c.logged_m:,.0f} m logged). Graphitic status cannot be read
from one field: the rock code `Sgs`, the graphite mineral field and the graphite comment disagree for
{int(c.label_conflicts)} intervals. The reconciled rule DESIGN_8_2_v1 is the approved rule used by Objectives 2 to 4. It leaves
{n_ambiguous} intervals ambiguous and excluded, giving {n_binary} binary intervals. Collar elevations are absent, so every
vertical value is relative to the collar.
"""))
display(Markdown(f"""
**Likely questions and answers**

- **Why not use the `Sgs` code alone?** The code gives {int(c.sgs_intervals)} intervals in {int(c.sgs_holes)} holes.
  The three logged indicators (code, graphite mineral field, graphite comment) disagree within
  {int(c.label_conflicts)} intervals, so the code alone is not a complete definition. The workbook reconciliation expected
  {rec.loc['Sgs intervals', 'expected'] if 'Sgs intervals' in rec.index else 'n/a'} `Sgs` intervals and the database holds
  {rec.loc['Sgs intervals', 'observed'] if 'Sgs intervals' in rec.index else 'n/a'}; that difference is recorded as a WARN and
  is not hidden.
- **Is the approved rule the same as the Stage A rule?** Stage A reported every candidate rule as PROPOSED. The current
  database shows DESIGN_8_2_v1 as APPROVED (approved by the author); the other rules remain PROPOSED sensitivity analyses.
- **Why are the lines "provisional"?** Holes were grouped by nominal Northing. The grouping was approved as the
  drill-line basis, but no surveyed collar elevation exists to confirm the geometry.
- **Why is depth relative?** No collar RL is in the workbook (see the status table above), so absolute elevation and
  depth below sea level cannot be computed.
"""))
''')

MD(r'''
### 3g. What this result permits you to claim, and what it does not permit

The lists below are read from `specs/01_thesis_scope_and_objective_traceability.md` when the notebook runs.
''')

CODE(r'''
display(Markdown(section_text(SPEC, "## Scientific claims permitted in Stage A")))
display(Markdown(section_text(SPEC, "## Prohibited overclaims")))
display(Markdown("Read with the database: the approval of DESIGN_8_2_v1 post-dates the Stage A statement that all rules are PROPOSED."))
''')

# ----- Objective 2 ---------------------------------------------------------------------------------------------------

MD("## 4. Objective 2: spatial distribution, geological controls and continuity")
MD("### 4a. Objective and operational refinement")
CODE(r'''
objective_block(2)
''')

MD("### 4b. What was predeclared")
CODE(r'''
o2_var_cfg = load_yaml("config/objective_2/variogram_config.yaml")
o2_wx_cfg = load_yaml("config/objective_2/weathering_config_O2-CFG-2026.11.06-5.yaml")
o2_ext_cfg = load_yaml("config/objective_2/extension_config_O2-CFG-2026.11.05-3.yaml")
o2_struct_cfg = load_yaml("config/objective_2/structural_config_O2-CFG-2026.11.06-6.yaml")
display(Markdown("**Base variogram configuration** (`config/objective_2/variogram_config.yaml`)"))
display(config_table(o2_var_cfg, pattern=r"config_version|label_rule|lag_|min_|identifiab|stab|structured_sill_bounds|declared", limit=40))
display(Markdown("**Weathering-front and fresh-rock configuration** (`weathering_config_O2-CFG-2026.11.06-5.yaml`)"))
display(config_table(o2_wx_cfg, pattern=r"config_version|extends|front_codes|lag_|min_|bootstrap\.n_rep|confidence|skill_rule", limit=30))
display(Markdown("**Extension configuration** (`extension_config_O2-CFG-2026.11.05-3.yaml`)"))
display(config_table(o2_ext_cfg, pattern=r"config_version|lag|label|comparator", limit=15))
display(Markdown("**Structural-frame configuration** (`structural_config_O2-CFG-2026.11.06-6.yaml`)"))
if "_yaml_error" in o2_struct_cfg:
    display(Markdown(
        "The structural configuration is **not valid YAML as written** (YAML error: "
        f"`{o2_struct_cfg['_yaml_error']}`). The pipeline repairs plain scalars in memory and records how many repairs "
        "it made. That count is read from the run report below. The parameters that were actually used are stored in the "
        "database and are shown in section 4c."))
    report_o2 = read_text(REPO / "reports/objective_2/RUN_REPORT.md")
    m = re.search(r"in-memory YAML scalar repairs: (\d+)", report_o2)
    display(Markdown(f"In-memory YAML scalar repairs recorded in the run report: **{m.group(1) if m else 'not found'}**."))
else:
    display(config_table(o2_struct_cfg, pattern=r"config_version|grid|perm|alpha|seed|lag|max_abs", limit=30))
display(Markdown("**Stage runs recorded in the database, by run kind and configuration**"))
display(query("o2", """
SELECT run_kind, config_version, COUNT(*) AS runs, SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
       MIN(started_utc) AS first_started_utc, MAX(finished_utc) AS last_finished_utc
FROM stage_runs GROUP BY run_kind, config_version ORDER BY MIN(started_utc)
"""))
''')

MD("### 4c. Key results (queried live from the Objective 2 database)")
CODE(r'''
o2_lines = query("o2", """
SELECT line_code, n_holes, binary_n AS binary_intervals, positive_n AS positive_intervals,
       negative_n AS negative_intervals, ROUND(graphitic_fraction_binary, 3) AS positive_share
FROM line_occurrence_summaries ORDER BY line_code
""")
o2_weathering = query("o2", """
SELECT weathering_code, label_state, n_intervals FROM weathering_cross_tabs
ORDER BY weathering_code, label_state
""")
o2_support = query("o2", """
SELECT stat_group, stat_name, ROUND(stat_value, 2) AS value, unit, n_basis
FROM spatial_support_statistics
WHERE stat_group IN ('COLLAR_NEAREST', 'COLLAR_PAIR') AND stat_name IN ('p05', 'median', 'p95')
ORDER BY stat_group, stat_name
""")
o2_holes = query("o2", """
SELECT COUNT(*) AS holes, COUNT(DISTINCT line_code) AS lines, SUM(binary_n) AS binary_intervals,
       SUM(positive_n) AS positive_intervals FROM hole_occurrence_summaries
""")
o2_collars_lines = query("o1", """
SELECT line_code, nominal_northing_m FROM v_drill_lines ORDER BY nominal_northing_m
""")  # drill lines are a Stage A (Objective 1) table; the Objective 2 receipt uses the same lines

wx = o2_weathering.pivot_table(index="weathering_code", columns="label_state", values="n_intervals",
                               aggfunc="sum", fill_value=0)
wx_table = pd.DataFrame({
    "weathering_code": wx.index,
    "positive_intervals": wx.get("POSITIVE", 0).values,
    "negative_intervals": wx.get("NEGATIVE", 0).values,
    "ambiguous_intervals": wx.get("AMBIGUOUS", 0).values,
})
wx_table["binary_intervals"] = wx_table["positive_intervals"] + wx_table["negative_intervals"]
wx_table["prevalence_of_positive"] = np.where(wx_table["binary_intervals"] > 0,
                                              wx_table["positive_intervals"] / wx_table["binary_intervals"].replace(0, np.nan), np.nan)
wx_table["prevalence_of_positive"] = wx_table["prevalence_of_positive"].round(3)

display(Markdown("**Occurrence by drill line (binary intervals only; AMBIGUOUS excluded)**"))
display(o2_lines)
display(Markdown("**Prevalence of graphitic (POSITIVE) intervals by logged weathering code**"))
display(wx_table)
display(Markdown("**Collar spacing (m): nearest collar per hole and collar pairs**"))
display(o2_support)
display(Markdown("**Holes and lines in the lateral analysis**"))
display(o2_holes)
''')

CODE(r'''
o2_fits = query("o2", """
SELECT e.variant, e.direction_id AS experiment, f.model, f.fit_status, f.n_bins_used AS supported_bins,
       f.stability_status, f.fit_id
FROM variogram_fits f JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
WHERE e.variant = 'BASE' ORDER BY e.direction_id, f.model
""")
o2_params = query("o2", """
SELECT e.direction_id AS experiment, f.model, p.parameter, ROUND(p.estimate, 5) AS estimate,
       ROUND(p.lower_bound, 4) AS lower_bound, ROUND(p.upper_bound, 4) AS upper_bound, p.units
FROM variogram_fit_parameters p
JOIN variogram_fits f ON f.fit_id = p.fit_id
JOIN variogram_experiments e ON e.experiment_id = f.experiment_id
WHERE e.variant = 'BASE' AND e.direction_id IN ('DOWNHOLE_WITHIN', 'LATERAL_BETWEEN')
ORDER BY e.direction_id, f.model, p.parameter
""")
o2_bins = query("o2", """
SELECT e.direction_id AS experiment, COUNT(*) AS lag_bins, SUM(b.supported) AS supported_bins,
       MIN(CASE WHEN b.supported = 1 THEN b.n_independent_hole_pairs END) AS min_hole_pairs_in_supported_bin
FROM variogram_lag_bins b JOIN variogram_experiments e ON e.experiment_id = b.experiment_id
WHERE e.variant = 'BASE' GROUP BY e.direction_id ORDER BY e.direction_id
""")
o2_handoff = query("o2", """
SELECT decision_status, candidate_family, full_data_parameters_for_test_folds AS full_data_params_for_test_folds
FROM continuity_handoff_decisions
""")
display(Markdown("**Base experiments: supported bins and fit status (lateral basis is the handoff basis)**"))
display(o2_bins)
display(o2_fits)
display(Markdown("**Fitted parameters of the base fits that converged** (nugget and sill in indicator units; range in m)"))
display(o2_params)
display(Markdown("**Objective 3 handoff for the lateral continuity model**"))
display(o2_handoff)
''')

CODE(r'''
o2_struct_null = query("o2", """
SELECT sample_id, frame_id, selected_dip_deg, ROUND(observed_max_alignment, 4) AS alignment_at_selected_dip,
       ROUND(null_p95_max, 4) AS null_95th_percentile_of_max, n_permutations, ROUND(p_value, 4) AS p_value
FROM structural_null_summary ORDER BY sample_id, frame_id
""")
o2_struct_sel = query("o2", """
SELECT sample_id, frame_id, dip_deg AS selected_dip_deg, ROUND(alignment_score, 4) AS alignment_score, n_pairs
FROM structural_alignment_scores WHERE is_selected = 1 ORDER BY sample_id, frame_id
""")
o2_struct_lolo = query("o2", """
SELECT sample_id, frame_id, SUM(within_tolerance) AS lines_within_tolerance, COUNT(*) AS lines
FROM structural_lolo_dips GROUP BY sample_id, frame_id ORDER BY sample_id, frame_id
""")
o2_struct_dec = query("o2", """
SELECT sample_id, frame_id, decision FROM structural_decisions ORDER BY sample_id, frame_id
""")
o2_front = query("o2", """
SELECT stat_group, stat_name, ROUND(stat_value, 3) AS value, unit, n_basis
FROM weathering_front_diagnostics ORDER BY stat_group, stat_name
""")
display(Markdown("**Structural frame: selected apparent dip and selection null** (RELATIVE is the primary frame; DEM_ABSOLUTE is sensitivity only)"))
display(o2_struct_sel)
display(o2_struct_null)
display(Markdown("**Leave-one-line-out dips within 10 degrees of the full selection**"))
display(o2_struct_lolo)
display(Markdown("**Structural decisions**"))
display(o2_struct_dec)
display(Markdown("**Weathering front: relative elevation, along-line differences and interpolation skill**"))
display(o2_front)
''')

CODE(r'''
o2_gates = query("o2", """
SELECT gate_id, gate_name, status, SUBSTR(detail, 1, 220) AS detail
FROM gate_results WHERE run_id = (SELECT MAX(run_id) FROM gate_results) ORDER BY gate_id
""")
display(Markdown("**Objective 2 gates of the latest verification run: counts by status**"))
display(o2_gates["status"].value_counts().rename_axis("status").reset_index(name="gates"))
display(Markdown("**Gates that are not PASS**"))
display(o2_gates[o2_gates["status"] != "PASS"])
''')

MD("### 4d. Figures")
CODE(r'''
o2_fig = query("o2", """
SELECT figure_id, title, status FROM figure_registry ORDER BY figure_id
""")
show_figures("o2", o2_fig)
''')

MD("### 4e. Mathematical notes: Objective 2")
for _s in MATH["O2"]:
    MD(_s)

MD("### 4f. How to explain this result")
CODE(r'''
lat = o2_bins.set_index("experiment").loc["LATERAL_BETWEEN"]
lat_fit = o2_fits[(o2_fits["experiment"] == "LATERAL_BETWEEN")]
spher_status = lat_fit.loc[lat_fit["model"] == "spherical", "fit_status"].iloc[0]
expo_status = lat_fit.loc[lat_fit["model"] == "exponential", "fit_status"].iloc[0]
dh = o2_params[o2_params["experiment"] == "DOWNHOLE_WITHIN"].pivot_table(index="model", columns="parameter", values="estimate")
dh_exp = dh.loc["exponential"] if "exponential" in dh.index else None
dh_sph = dh.loc["spherical"] if "spherical" in dh.index else None
near_med = o2_support[(o2_support.stat_group == "COLLAR_NEAREST") & (o2_support.stat_name == "median")]["value"].iloc[0]
near_p05 = o2_support[(o2_support.stat_group == "COLLAR_NEAREST") & (o2_support.stat_name == "p05")]["value"].iloc[0]
near_p95 = o2_support[(o2_support.stat_group == "COLLAR_NEAREST") & (o2_support.stat_name == "p95")]["value"].iloc[0]
gap = np.diff(o2_collars_lines["nominal_northing_m"].to_numpy(dtype=float))
gap_min, gap_max = float(gap.min()), float(gap.max())
struct_sel = o2_struct_sel.set_index(["sample_id", "frame_id"])
struct_null = o2_struct_null.set_index(["sample_id", "frame_id"])
rel_all = struct_null.loc[("ALL_BINARY", "RELATIVE")]
rel_fresh = struct_null.loc[("FRESH", "RELATIVE")]
dec = o2_struct_dec.set_index(["sample_id", "frame_id"])["decision"]
mw = wx_table.set_index("weathering_code")
cw_prev = float(mw.loc["cw", "prevalence_of_positive"]) if "cw" in mw.index else float("nan")
mw_prev = float(mw.loc["mw", "prevalence_of_positive"]) if "mw" in mw.index else float("nan")
dh_bins = int(o2_bins.set_index("experiment").loc["DOWNHOLE_WITHIN", "supported_bins"])
dh_sill = float(dh.loc["exponential", "structured_sill"]) if dh_exp is not None else float("nan")
front_skill = o2_front[o2_front["stat_name"] == "skill_ratio"].set_index("stat_group")["value"]
skill_threshold = float(re.search(r"at most ([0-9.]+) times", o2_wx_cfg["weathering_front"]["continuity"]
                                  ["interpolation_check"]["skill_rule"]).group(1))
skill_hole = float(front_skill.get("INTERPOLATION_LEAVE_ONE_HOLE_OUT", float("nan")))
skill_line = float(front_skill.get("INTERPOLATION_LEAVE_ONE_LINE_OUT", float("nan")))
display(Markdown(f"""
**Plain-language summary.** Occurrence of graphite is not uniform. It is most common in the mw-coded intervals (prevalence
{mw_prev:.2f}) and absent from the cw-coded intervals (prevalence {cw_prev:.2f}), and it varies strongly between drill lines.
Continuity can be measured within a hole, where
the down-hole structure is fitted (practical range {dh_exp['range_m']:.1f} m for the exponential fit). Between holes, the
data do not identify a lateral range: holes are a median {near_med:.0f} m from their nearest collar, and drill lines
are {gap_min:.0f} to {gap_max:.0f} m apart, so lateral pairs do not resolve the structure. The apparent-dip search finds no
stable structural frame for the primary sample, and the weathering front is not interpolable between holes by the
predeclared method.
"""))
display(Markdown(f"""
**Likely questions and answers**

- **Why no lateral variogram?** The lateral basis is `{lat_fit.iloc[0]['experiment']}` with {int(lat['supported_bins'])} supported
  bins. The spherical fit is {spher_status} and the exponential fit is {expo_status}. The nearest-collar median is
  {near_med:.0f} m (5th to 95th percentile {near_p05:.0f} to {near_p95:.0f} m), while drill lines are {gap_min:.0f} to
  {gap_max:.0f} m apart. Pairs at the lags that separate lines do not identify a structure, and the structure at the scale of
  the lateral lags is not resolved.
- **Why is the within-hole result usable and the lateral one not?** The down-hole experiment has {dh_bins} supported
  one-metre bins along each hole, and its exponential fit converges inside its bounds (sill {dh_sill:.3f}). The lateral result
  is not identified, so Objective 3 is not given a between-hole continuity model.
- **Is the weathering front continuous?** The front is locally similar between neighbouring holes, but the interpolation
  skill ratios are {skill_hole:.2f} (leave one hole out) and {skill_line:.2f} (leave one line out), against the threshold of
  {skill_threshold:.2f} for INTERPOLABLE. It is not interpolable by the predeclared method and is not used as a surface away from the drilled holes.
- **What does the structural result mean?** The selected apparent dip is the statistically favoured plane, not a measured
  orientation. For the primary sample the selection null gives decision `{dec.loc[('ALL_BINARY', 'RELATIVE')]}`, so no
  structural frame is claimed.
- **Why do the lines differ so much in occurrence?** The between-line contrast is the strongest occurrence contrast in the
  data. The database does not say whether it reflects zones, sampling or geology, so it is reported as an open question.
"""))
''')

MD("### 4g. What this result permits you to claim, and what it does not permit")
CODE(r'''
display(Markdown("**Achievement under the refinement (specs/01)**"))
display(Markdown(refinement_rows(2)[4] if refinement_rows(2) else "*(not found)*"))
display(Markdown("**Specification 01: claims that these refinements do not permit**"))
display(Markdown(between(SPEC, "Claims these refinements do NOT permit", "\n\n") or "*(not found)*"))
display(Markdown("**Configuration 6 (structural frame): claims not permitted, from the run report**"))
rep2 = read_text(REPO / "reports/objective_2/RUN_REPORT.md")
display(Markdown(between(rep2, "Claims not permitted by configuration 6", "Decision label")))
display(Markdown("**Objective 3 handoff, from the run report (what Objective 3 may and may not use)**"))
display(Markdown(section_text(rep2, "## 11. Objective 3 handoff contract")))
''')

# ----- Objective 3 ---------------------------------------------------------------------------------------------------

MD("## 5. Objective 3: indicator, machine-learning and hybrid models, spatially validated")
MD("### 5a. Objective and operational refinement")
CODE(r'''
objective_block(3)
''')

MD("### 5b. What was predeclared")
CODE(r'''
o3_cfg = load_yaml("config/objective_3/model_config.yaml")
display(Markdown("**Model configuration** (`config/objective_3/model_config.yaml`)"))
display(config_table(o3_cfg, pattern=r"config_version|supersedes|target\.|predictor_sets|splits\.tiers|inner_cv\.|"
                                     r"kriging\.(grid|m1|m3|depth|min_|max_|model|estimator)|calibration\.(method|clip|apply)|"
                                     r"logistic\.grid|random_forest\.grid|gradient_boosting\.grid", limit=60))
display(Markdown("**Split plans and their audits (each plan has five outer folds)**"))
display(query("o3", """
SELECT split_plan_id, method, n_folds, primary_plan FROM spatial_split_plans ORDER BY split_plan_id
"""))
display(query("o3", """
SELECT split_plan_id, fold_id, n_train, n_test, test_positive, train_holes, test_holes, test_lines,
       ROUND(min_train_test_collar_distance_m, 1) AS min_train_test_collar_distance_m, disjoint, status
FROM split_audit ORDER BY split_plan_id, fold_id
"""))
''')

MD("### 5c. Key results (queried live from the Objective 3 database)")
CODE(r'''
o3_families = query("o3", """
SELECT family_id, name, role FROM model_families ORDER BY role, family_id
""")
o3_runs = query("o3", """
SELECT split_plan_id, family_id, status, COUNT(*) AS folds
FROM training_runs GROUP BY split_plan_id, family_id, status ORDER BY split_plan_id, family_id, status
""")
o3_runs_pivot = o3_runs.pivot_table(index=["family_id"], columns=["split_plan_id"], values="folds", aggfunc="sum",
                                    fill_value=0)
o3_inner = query("o3", """
SELECT split_plan_id, family_id, ROUND(AVG(inner_cv_score), 4) AS mean_inner_cv_log_loss, COUNT(*) AS runs
FROM training_runs WHERE inner_cv_score IS NOT NULL
GROUP BY split_plan_id, family_id ORDER BY split_plan_id, family_id
""")
o3_m1 = query("o3", """
SELECT r.split_plan_id, r.fold_id, t.hyperparameters_json
FROM hyperparameter_trials t JOIN training_runs r ON r.training_run_id = t.training_run_id
WHERE t.candidate_run_id = 'M1_IK' AND t.selected = 1 ORDER BY r.split_plan_id, r.fold_id
""")
o3_m1["chosen_covariance"] = [json.loads(h).get("covariance_label", "") for h in o3_m1["hyperparameters_json"]]
o3_m3 = query("o3", """
SELECT split_plan_id, fold_id, status, SUBSTR(reason, 1, 120) AS reason FROM training_runs
WHERE family_id = 'M3_HYBRID' ORDER BY split_plan_id, fold_id
""")
o3_hyb = query("o3", """
SELECT fallback_status, fit_status, COUNT(*) AS folds FROM hybrid_residual_variogram GROUP BY fallback_status, fit_status
""")
o3_leak = query("o3", """
SELECT check_name, status, COUNT(*) AS audit_rows FROM leakage_audit_log GROUP BY check_name, status ORDER BY check_name
""")
o3_pred = query("o3", """
SELECT family_id, COUNT(*) AS predictions FROM predictions_oof GROUP BY family_id ORDER BY family_id
""")
o3_final = query("o3", """
SELECT status, SUBSTR(reason, 1, 200) AS reason FROM final_refits
""")
display(Markdown("**Model families (role in the analysis)**"))
display(o3_families)
display(Markdown("**Training runs by split plan, family and status (five folds per family)**"))
display(o3_runs_pivot)
display(Markdown("**Mean inner-CV log loss of each family (selection diagnostics, not held-out performance)**"))
display(o3_inner)
display(Markdown("**M1 indicator kriging: covariance chosen by inner CV in each outer fold**"))
display(o3_m1)
display(Markdown("**M3 hybrid: status per fold, and the residual covariance found by inner CV**"))
display(o3_m3)
display(o3_hyb)
display(Markdown("**Leakage audit (all rows, both split plans)**"))
display(o3_leak)
display(Markdown("**Out-of-fold predictions per family (one row per held-out interval and plan)**"))
display(o3_pred)
display(Markdown("**Final full-data refit recorded by Objective 3**"))
display(o3_final)
''')

CODE(r'''
o3_gates = query("o3", """
SELECT status, COUNT(*) AS gates FROM gate_results
WHERE run_id = (SELECT MAX(run_id) FROM gate_results) GROUP BY status
""")
display(Markdown("**Objective 3 gates of the latest verification run**"))
display(o3_gates)
''')

MD("### 5d. Figures")
CODE(r'''
o3_fig = query("o3", """
SELECT figure_id, title, status FROM figure_registry ORDER BY figure_id
""")
show_figures("o3", o3_fig)
''')

MD("### 5e. Mathematical notes: Objective 3")
for _s in MATH["O3"]:
    MD(_s)

MD("### 5f. How to explain this result")
CODE(r'''
m3 = o3_m3.set_index(["split_plan_id", "fold_id"])["status"]
m3_fallback_all = bool((o3_hyb["fallback_status"] == "FALLBACK_ML_ONLY").all()) if len(o3_hyb) else False
m3_folds = int(len(m3))
m3_fallback_folds = int((m3 == "FALLBACK").sum())
lodo = o3_leak
n_leak_pass = int(lodo.loc[lodo["status"] == "PASS", "audit_rows"].sum())
n_leak_rows = int(lodo["audit_rows"].sum())
plans = query("o3", """
SELECT split_plan_id, method, n_folds FROM spatial_split_plans ORDER BY split_plan_id
""").set_index("split_plan_id")
m1_covs = o3_m1.groupby("split_plan_id")["chosen_covariance"].agg(lambda s: "; ".join(sorted(set(s))))
display(Markdown("**Indicator-kriging covariances chosen by inner CV, per plan**"))
display(m1_covs.rename("covariances chosen in the five folds").to_frame())
display(Markdown(f"""
**Plain-language summary.** Five model families were built for each of two spatial validation plans. The first plan
holds out whole drill lines (tier 1, extrapolation). The second holds out interleaved holes within each line (tier 2,
interpolation). Indicator kriging chose a spatial covariance (not pure nugget) in each fold. The hybrid model fell back to
its machine-learning trend in {m3_fallback_folds} of its {m3_folds} runs (status FALLBACK, labelled FALLBACK_ML_ONLY). That is a
tested result: inner cross-validation found no residual correlation worth keeping, so the hybrid equals its trend.
{n_leak_pass} of {n_leak_rows} leakage-audit rows pass.
"""))
display(Markdown(f"""
**Likely questions and answers**

- **Why is the hybrid not better?** Its residual kriging step is switched off by inner cross-validation in every fold
  (pure nugget). M3 then equals the calibrated trend, so any hybrid advantage is zero by construction. This is reported as a
  finding; no hybrid advantage is claimed. The evaluation in Objective 4 confirms the identity.
- **Why does M1 use a spatial covariance when the hybrid does not?** M1 kriges the indicator itself, whose large-scale
  pattern the trend also captures. M3 kriges only the residual after the trend, and inner cross-validation finds no
  residual correlation to keep. A covariance chosen for prediction is not a variogram identified from the data
  (Objective 2 finds no identified lateral variogram), so the two results are not in conflict.
- **Why two validation tiers?** Tier 1 holds out a whole line, so its test points lie far from training data
  (beyond the lateral range of any supported structure). Tier 2 holds out interleaved holes, so its test points are at about
  one hole spacing. The two answer different questions and are reported separately.
- **Why is the weathering-front feature fold-safe?** Its surface is built from training holes only, and the audit confirms
  that changing test-hole fronts leaves the training features unchanged.
- **Why is there no full-data model here?** The final full-data refit is recorded as pending until Objective 4 locks the
  selection. Objective 5 then refits the locked models; that fit is not spatially validated.
"""))
''')

MD("### 5g. What this result permits you to claim, and what it does not permit")
CODE(r'''
rep3 = read_text(REPO / "reports/objective_3/RUN_REPORT.md")
display(Markdown("**Objective 3 limitations and deviations, from the run report**"))
display(Markdown(section_text(rep3, "## 10. Deviations, warnings and limitations")))
display(Markdown("**Scope statement: prohibited overclaims (these apply to every objective, including 3 to 5)**"))
display(Markdown(section_text(SPEC, "## Prohibited overclaims")))
''')

# ----- Objective 4 ---------------------------------------------------------------------------------------------------

MD("## 6. Objective 4: predictive performance and model comparison under spatial validation")
MD("### 6a. Objective and operational refinement")
CODE(r'''
objective_block(4)
''')

MD("### 6b. What was predeclared")
CODE(r'''
o4_cfg_t1 = load_yaml("config/objective_4/evaluation_config.yaml")
o4_cfg_t2 = load_yaml("config/objective_4/evaluation_config_tier2.yaml")
o4_pattern = (r"config_version|^tier|^claim|paths\.o3_split|primary_endpoint|primary_weighting|secondary_weighting|"
              r"epsilon|calibration_min_bin_n|calibration_slope|calibration_intercept|discrimination_margin|"
              r"fold_consistency_min|coverage_threshold|bootstrap\.(n_replicates|seed|confidence|primary_design)|"
              r"decision\.(select|comparator|selection_basis)")
display(Markdown("**Tier 1 extrapolation configuration** (`evaluation_config.yaml`)"))
display(config_table(o4_cfg_t1, pattern=o4_pattern, limit=40))
display(Markdown("**Tier 2 interpolation configuration** (`evaluation_config_tier2.yaml`)"))
display(config_table(o4_cfg_t2, pattern=o4_pattern, limit=40))
''')

MD("### 6c. Key results (queried live; one block per tier)")
CODE(r'''
TIERS = [("o4_t1", "Tier 1 (extrapolation to an unseen drill line)"),
         ("o4_t2", "Tier 2 (interpolation between holes of one line)")]
o4_results = {}
for key, label in TIERS:
    res = {}
    res["cohort"] = query(key, """
SELECT COUNT(*) AS intervals, SUM(true_label) AS positive_intervals, COUNT(DISTINCT hole_id) AS holes,
       COUNT(DISTINCT line_code) AS lines, ROUND(AVG(true_label), 3) AS prevalence
FROM v_common_cohort WHERE in_common_cohort = 1
""")
    res["metrics"] = query(key, """
SELECT model_id, metric_id, ROUND(value, 4) AS value, n, n_positive, status
FROM v_pooled_metrics_primary
WHERE metric_id IN ('BRIER', 'LOG_LOSS', 'ROC_AUC', 'PR_AUC', 'ECE')
ORDER BY metric_id, model_id
""")
    res["identity"] = query(key, """
SELECT model_id, role, identity_status, identical_to, coverage_status, comparable FROM candidate_registry ORDER BY model_id
""")
    res["decision"] = query(key, """
SELECT CASE WHEN rank IS NULL THEN 99 ELSE rank END AS sort_rank, model_id, role, rank, improvement_status,
       ROUND(delta_brier, 6) AS delta_brier_vs_comparator, ROUND(ci_low, 6) AS ci_low, ROUND(ci_high, 6) AS ci_high,
       fold_consistency, calibration_status, discrimination_status, coverage
FROM comparison_decisions ORDER BY sort_rank, model_id
""")
    res["pairs"] = query(key, """
SELECT pair_id, model_a, model_b, ROUND(delta_brier, 6) AS delta_brier_b_minus_a, ROUND(ci_low, 6) AS ci_low,
       ROUND(ci_high, 6) AS ci_high, ROUND(detectable_half_width, 6) AS detectable_half_width, power_label
FROM paired_differences WHERE scope = 'POOLED' AND weighting = 'INTERVAL' ORDER BY pair_id
""")
    res["calib"] = query(key, """
SELECT model_id, ROUND(intercept, 3) AS calibration_intercept, ROUND(slope, 3) AS calibration_slope, status
FROM calibration_diagnostics ORDER BY model_id
""")
    res["locked"] = query(key, """
SELECT tier, selected_model_id, decision_id, metric_reference, calibration_policy FROM locked_handoff_receipts
""")
    res["gates"] = query(key, """
SELECT status, COUNT(*) AS gates FROM gate_results WHERE run_id = (SELECT MAX(run_id) FROM gate_results) GROUP BY status
""")
    o4_results[key] = res
    display(Markdown(f"### {label}"))
    display(Markdown("**Common held-out cohort** (intervals present in every fully covered model)"))
    display(res["cohort"])
    display(Markdown("**Pooled probability metrics, interval-weighted** (lower is better for Brier, log loss and ECE; higher is better for AUC)"))
    display(res["metrics"].pivot_table(index="model_id", columns="metric_id", values="value"))
    display(Markdown("**Model identity and role**"))
    display(res["identity"])
    display(Markdown("**Paired Brier differences, b minus a (interval-weighted; hole-cluster 95 per cent interval)**"))
    display(res["pairs"])
    display(Markdown("**Decision table** (rank, role and improvement status under the predeclared rule)"))
    display(res["decision"])
    display(Markdown("**Calibration intercept and slope (diagnostic only; not applied)**"))
    display(res["calib"])
    display(Markdown("**Locked model for this tier**"))
    display(res["locked"])
    display(Markdown("**Gates of the latest verification run**"))
    display(res["gates"])
''')

MD("### 6d. Figures")
CODE(r'''
o4_figs = {}
for key, label in TIERS:
    display(Markdown(f"### Figures, {label}"))
    fig_frame = query(key, "SELECT figure_id, title, status FROM figure_registry ORDER BY figure_id")
    show_figures(key, fig_frame, width=760)
''')

MD("### 6e. Mathematical notes: Objective 4")
for _s in MATH["O4"]:
    MD(_s)

MD("### 6f. How to explain this result")
CODE(r'''
for key, label in TIERS:
    r = o4_results[key]
    m = r["metrics"].pivot_table(index="model_id", columns="metric_id", values="value")
    pairs = r["pairs"].set_index("pair_id")
    dec = r["decision"].set_index("model_id")
    sel = r["locked"].iloc[0]["selected_model_id"]
    comp = dec.loc[dec["role"] == "COMPARATOR"].index[0]
    d_sel = dec.loc[sel, "delta_brier_vs_comparator"]
    lo_sel, hi_sel = dec.loc[sel, "ci_low"], dec.loc[sel, "ci_high"]
    improvement = dec.loc[sel, "improvement_status"]
    folds_better = dec.loc[sel, "fold_consistency"]
    trend_pair = pairs.loc["PREV_vs_M2SEL"] if "PREV_vs_M2SEL" in pairs.index else None
    half = float(pairs.loc["LOG_vs_RF", "detectable_half_width"]) if "LOG_vs_RF" in pairs.index else float("nan")
    m1_pair = pairs.loc["PREV_vs_M1"] if "PREV_vs_M1" in pairs.index else None
    trend_label = (f"{trend_pair['power_label']} (difference {float(trend_pair['delta_brier_b_minus_a']):+.4f})"
                   if trend_pair is not None else "not reported")
    m1_label = (f"{m1_pair['power_label']} (difference {float(m1_pair['delta_brier_b_minus_a']):+.4f})"
                if m1_pair is not None else "not reported")
    hyb_identical = (pairs.loc["M2WFSEL_vs_M3", "power_label"] if "M2WFSEL_vs_M3" in pairs.index else "not reported")
    hyb_identical = "IDENTICAL" if str(hyb_identical).upper() == "IDENTICAL" else f"not identical ({hyb_identical})"
    best_brier = m["BRIER"].drop(index=[i for i in m.index if i in ("M2_SEL", "M2_WF_SEL", "M3_HYBRID")]).idxmin()
    display(Markdown(f"""
**{label}.** Locked model: **{sel}** (status {improvement}, comparator {comp}). The point estimate of the difference
{sel} minus {comp} is {d_sel:+.4f} Brier, with hole-cluster 95 per cent interval [{lo_sel:+.4f}, {hi_sel:+.4f}]; the
selected model is better in {int(folds_better)} of the 5 folds. The lowest pooled Brier among distinct models is {best_brier}.
The coordinate trend against the training prevalence (PREV_vs_M2SEL): {trend_label}.
The hybrid M3 is {hyb_identical} with its trend M2_WF_SEL on every common interval, so the hybrid adds nothing in this evaluation.
"""))
    display(Markdown(f"""
**Likely questions and answers ({label})**

- **Why is the result {improvement}?** The rule requires the hole-cluster interval of the selected-minus-comparator
  difference to lie entirely below zero. Here that difference is {d_sel:+.4f} and its interval is
  [{lo_sel:+.4f}, {hi_sel:+.4f}]. For the logistic-versus-random-forest pair the smallest difference this design can
  distinguish is {half:.4f} Brier units, so differences of that size between the top models cannot be told apart.
- **Why is the choice then made at all?** The predeclared selection rule is the lowest pooled Brier. It is reported as a
  point estimate with a caveat, not as evidence of improvement.
- **Is the coordinate trend better than the prevalence?** The pair PREV_vs_M2SEL is {trend_label}. A RESOLVED result
  here is the most secure comparison in this objective.
- **Is the kriging model better than the prevalence baseline?** The pair PREV_vs_M1 is {m1_label}. Kriging is never
  claimed to beat the coordinate trend in this evaluation.
- **Is the hybrid better than its trend?** No. The hybrid is identical to its trend on every common interval, so the gain
  attributed to the hybrid family is zero by construction.
- **Does this show that the model predicts well in new areas?** It shows internal spatial validation on five drill lines.
  It is not an external or prospective test, and no grade, tonnage or resource statement follows.
"""))
''')

MD("### 6g. What this result permits you to claim, and what it does not permit")
CODE(r'''
rep4a = read_text(REPO / "reports/objective_4/tier_1/RUN_REPORT.md")
rep4b = read_text(REPO / "reports/objective_4/tier_2/RUN_REPORT.md")
display(Markdown("**Achievement under the refinement (specs/01)**"))
display(Markdown(refinement_rows(4)[4] if refinement_rows(4) else "*(not found)*"))
display(Markdown("**Specification 01: claims that these refinements do not permit**"))
display(Markdown(between(SPEC, "Claims these refinements do NOT permit", "\n\n") or "*(not found)*"))
display(Markdown("**Tier 1 limitations, from the run report**"))
display(Markdown(section_text(rep4a, "## 13. Limitations")))
display(Markdown("**Tier 2 limitations, from the run report**"))
display(Markdown(section_text(rep4b, "## 13. Limitations")))
''')

# ----- Objective 5 ---------------------------------------------------------------------------------------------------

MD("## 7. Objective 5: three-dimensional uncertainty and scenario analysis")
MD("### 7a. Objective and operational refinement")
CODE(r'''
objective_block(5)
display(Markdown(
    "Objective 5 is not refined in specs/01; its design follows the consequence stated in specs/01: inside the drilled block "
    "the tier-2 selection is used, outside it the tier-1 selection. Probability and entropy are trend-based uncertainty "
    "from the selected model, not geostatistical uncertainty."))
''')

MD("### 7b. What was predeclared")
CODE(r'''
o5_cfg = load_yaml("config/objective_5/uncertainty_config.yaml")
display(Markdown("**Uncertainty configuration** (`config/objective_5/uncertainty_config.yaml`)"))
display(config_table(o5_cfg, pattern=r"config_version|supersedes|label_rule_id|geometry\.|grid\.(cell|z_range|origin)|"
                                     r"support_zones\.zones|depth_support\.neighbourhood|uncertainty_measures\.(hole_bootstrap\.(n_rep|seed|interval)|model_disagreement|entropy)|"
                                     r"classification\.(decision|disagreement|sensitivity)|scenario_simulation\.(method|n_real|seed|kriging\.(max|search))|"
                                     r"scenario_simulation\.anisotropy\.type|downhole_variogram\.expected", limit=70))
display(Markdown("**Scenario set (assumed lateral ranges; each is reported separately)**"))
display(pd.DataFrame(o5_cfg["scenario_simulation"]["scenarios"]))
display(Markdown("**Classification rule**"))
display(query("o5", "SELECT rule_id, decision_threshold, prevalence_threshold, disagreement_limit FROM classification_rules"))
display(Markdown("**Down-hole variogram used for the simulation: check against the Objective 2 fit**"))
display(query("o5", """
SELECT check_id, model, ROUND(nugget, 5) AS nugget, ROUND(structured_sill, 6) AS structured_sill,
       ROUND(practical_range_m, 3) AS practical_range_m, ROUND(max_abs_difference, 8) AS max_abs_difference, status
FROM downhole_variogram
"""))
''')

MD("### 7c. Key results (queried live from the Objective 5 database)")
CODE(r'''
o5_zone_class = query("o5", """
SELECT zone, class_label, COUNT(*) AS cells,
       ROUND(COUNT(*) * (SELECT CAST(meta_value AS REAL) FROM grid_meta WHERE meta_key = 'cell_volume_m3'), 0) AS relative_volume_m3,
       SUM(CASE WHEN above_weathering_front = 1 THEN 1 ELSE 0 END) AS cells_above_weathering_front
FROM grid_cells GROUP BY zone, class_label ORDER BY zone, class_label
""")
o5_zone_sens = query("o5", """
SELECT zone, class_at_prevalence AS class_at_training_prevalence, COUNT(*) AS cells
FROM grid_cells GROUP BY zone, class_at_prevalence ORDER BY zone, class_at_prevalence
""")
o5_depth = query("o5", """
SELECT zone, COUNT(*) AS cells,
       SUM(CASE WHEN depth_support = 'DEPTH_EXTRAPOLATED' THEN 1 ELSE 0 END) AS depth_extrapolated_cells
FROM grid_cells GROUP BY zone ORDER BY zone
""")
o5_boot = query("o5", """
SELECT zone, model_id, n_replicates, n_success, ROUND(success_fraction, 3) AS success_fraction,
       ROUND(runtime_s, 1) AS runtime_s, status
FROM bootstrap_summary ORDER BY zone
""")
o5_carried = query("o5", """
SELECT tier, role, model_id, metric_id, ROUND(value, 4) AS value, n FROM carried_validation
WHERE weighting = 'INTERVAL' ORDER BY tier, role, metric_id
""")
o5_refit = query("o5", """
SELECT tier, role, model_id, calibration_status, ROUND(in_sample_brier, 4) AS in_sample_brier,
       ROUND(in_sample_auc, 3) AS in_sample_auc, o3_modes_tied, full_data_matches_o3_mode
FROM final_refits ORDER BY tier, role
""")
o5_scen = query("o5", """
SELECT scenario_id, horizontal_range_m AS assumed_lateral_range_m, ROUND(vertical_range_m, 2) AS vertical_range_m,
       ROUND(downhole_practical_range_m, 2) AS downhole_range_m, dip_deg AS plunge_deg, n_realisations,
       ROUND(expected_volume_m3, 0) AS expected_volume_m3,
       ROUND(volume_p10_m3, 0) AS volume_p10_m3, ROUND(volume_p50_m3, 0) AS volume_p50_m3, ROUND(volume_p90_m3, 0) AS volume_p90_m3,
       components_p10, components_p50, components_p90,
       ROUND(largest_share_p10, 3) AS largest_share_p10, ROUND(largest_share_p50, 3) AS largest_share_p50,
       ROUND(largest_share_p90, 3) AS largest_share_p90, feasibility
FROM sim_scenarios ORDER BY horizontal_range_m
""")
o5_scen_rep = query("o5", """
SELECT scenario_id, ROUND(mean_frequency, 4) AS mean_simulated_frequency, ROUND(mean_local_mean, 4) AS mean_local_mean
FROM sim_scenarios ORDER BY scenario_id
""")
display(Markdown("**Cells by support zone and class** (EXTRAPOLATION cells are read with the tier-1 validation; they are not comparable with INTERPOLATION cells)"))
display(o5_zone_class)
display(Markdown("**Sensitivity: classes at the training prevalence instead of 0.5**"))
display(o5_zone_sens)
display(Markdown("**Depth support: cells that lie below the deepest sampled interval of their neighbourhood**"))
display(o5_depth)
''')

CODE(r'''
o5_width = query("o5", """
SELECT zone, interval_width, disagreement, entropy_bits FROM grid_cells WHERE zone <> 'NO_SUPPORT'
""")
q = o5_width.groupby("zone").agg(
    width_median=("interval_width", "median"),
    width_p90=("interval_width", lambda s: s.quantile(0.9)),
    disagreement_median=("disagreement", "median"),
    disagreement_p90=("disagreement", lambda s: s.quantile(0.9)),
    entropy_median_bits=("entropy_bits", "median"),
    cells=("interval_width", "size"),
).round(4).reset_index()
display(Markdown("**Bootstrap interval width (p_hi minus p_lo), model disagreement and entropy, per supported zone**"))
display(q)
display(Markdown("**Hole-bootstrap run per zone**"))
display(o5_boot)
display(Markdown("**Validated skill carried from Objective 4 (interval-weighted, not recomputed here)**"))
display(o5_carried)
display(Markdown("**Final full-data refits** (in-sample values are fit diagnostics, not validation)"))
display(o5_refit)
''')

CODE(r'''
display(Markdown("**Scenario simulation: volume, connectivity and reproduction by assumed lateral range**"))
display(o5_scen)
display(o5_scen_rep)
sp50 = o5_scen["volume_p50_m3"]
display(Markdown(
    f"Across the {len(o5_scen)} feasible scenarios the median (P50) volume ranges from {sp50.min():,.0f} to {sp50.max():,.0f} m³ "
    f"against an expected volume of {o5_scen['expected_volume_m3'].iloc[0]:,.0f} m³. The P50 largest-component share ranges from "
    f"{o5_scen['largest_share_p50'].min():.3f} to {o5_scen['largest_share_p50'].max():.3f}. The spread is the finding; "
    "it depends on the assumed lateral range and is not one volume."))
''')

CODE(r'''
o5_gates = query("o5", """
SELECT gate_id, gate_name, status, SUBSTR(detail, 1, 200) AS detail
FROM gate_results WHERE run_id = (SELECT MAX(run_id) FROM gate_results) ORDER BY gate_id
""")
display(Markdown("**Objective 5 gates of the latest verification run** (the scenario gates S01 to S04 and the W gates are included)"))
display(o5_gates)
''')

MD("### 7d. Figures")
CODE(r'''
o5_fig = query("o5", "SELECT figure_id, title, status FROM figure_registry ORDER BY figure_id")
show_figures("o5", o5_fig)
''')

MD("### 7e. Mathematical notes: Objective 5")
for _s in MATH["O5"]:
    MD(_s)

MD("### 7f. How to explain this result")
CODE(r'''
zc = o5_zone_class.pivot_table(index="zone", columns="class_label", values="cells", aggfunc="sum", fill_value=0)
boot_pct = float(re.search(r"(\d+) per cent", o5_cfg["uncertainty_measures"]["hole_bootstrap"]["interval"]).group(1))
conf_present_ext = int(zc.loc["EXTRAPOLATION", "CONFIDENT_PRESENT"]) if "EXTRAPOLATION" in zc.index else 0
conf_absent_ext = int(zc.loc["EXTRAPOLATION", "CONFIDENT_ABSENT"]) if "EXTRAPOLATION" in zc.index else 0
unc_int = int(zc.loc["INTERPOLATION", "UNCERTAIN"]) if "INTERPOLATION" in zc.index else 0
ext_disagree_med = float(q.loc[q.zone == "EXTRAPOLATION", "disagreement_median"].iloc[0])
int_disagree_med = float(q.loc[q.zone == "INTERPOLATION", "disagreement_median"].iloc[0])
display(Markdown(f"""
**Plain-language summary.** The three-dimensional grid is split into zones by distance to the nearest collar. Inside
about one hole spacing the tier-2 model applies; further out, up to the tier-1 limit, the tier-1 model applies, and beyond
that no probability is reported. Each cell is labelled confident or uncertain from a {boot_pct:.0f} per cent hole-bootstrap interval and
from the disagreement between the two locked models. The two locked models disagree most in the extrapolation zone (median
disagreement {ext_disagree_med:.3f}, against {int_disagree_med:.3f} in the interpolation zone), so the map of disagreement is
the map of where the unresolved model choice matters. The volume results depend on an assumed lateral range and are reported
as a set of scenarios.
"""))
display(Markdown(f"""
**Likely questions and answers**

- **Why scenarios instead of one simulation?** The lateral range cannot be estimated from these data (Objective 2), so each
  assumed range gives its own simulation. Volume is almost insensitive to the range, but connectivity is not, so the
  results are reported per scenario and never pooled.
- **Why are the confident classes in the extrapolation zone not comparable with the interpolation zone?** The
  extrapolation zone uses the tier-1 model, whose validated skill is lower than the tier-2 model's, and its bootstrap
  intervals are narrow because the logistic trend is smooth. The {conf_present_ext:,} present and {conf_absent_ext:,} absent
  extrapolation cells therefore reflect a stable trend, not better knowledge.
- **What does the uncertain class contain?** {unc_int:,} interpolation cells are uncertain. A cell is uncertain when its
  bootstrap interval straddles the threshold, when the two locked models disagree by more than the limit, or when it is
  DEPTH_EXTRAPOLATED.
- **Are the volumes resources?** No. They are relative grid volumes in the relative-depth frame, carry no grade, and depend
  on the assumed lateral range. The notebook makes no economic statement.
- **Why is entropy shown?** Entropy is a transform of the probability ($H(p)$ in bits). It shows where the locked model is
  near 0.5, which is not the same as geostatistical uncertainty.
"""))
''')

MD("### 7g. What this result permits you to claim, and what it does not permit")
CODE(r'''
rep5 = read_text(REPO / "reports/objective_5/RUN_REPORT.md")
display(Markdown("**Objective 5: claims not permitted, from the run report**"))
display(Markdown(section_text(rep5, "## 11. Claims not permitted")))
display(Markdown("**Objective 5: limitations recorded in the configuration**"))
display(Markdown("\n".join(f"- {item}" for item in o5_cfg.get("claims_not_permitted", []))
                 if isinstance(o5_cfg, dict) else "*(not available)*"))
''')

# ----- Limitations and appendix --------------------------------------------------------------------------------------

MD(r'''
## 8. Limitations and future work

The results are limited in the following ways. Each limitation is recorded in a run report and is visible in the tables above.

1. **Relative vertical frame.** No collar RL or surveyed elevation is available. All vertical values are depth below the
   collar, along straight holes with one declared orientation. Absolute elevation, depth below sea level and any volume in
   absolute coordinates cannot be stated. The orientation was declared, not measured, and no geological strike or dip is
   recorded, so geology and sampling direction cannot be separated.
2. **No assays.** Graphitic status is a logging-based label with conflicts. No grade, total graphitic carbon or assay-based
   statement can be made, so the label is a logged occurrence, not a measured concentration.
3. **Lateral range unidentifiable.** The lateral pair structure is not resolved at this support: holes are close within lines
   and lines are far apart. Continuity between lines is therefore an assumption in Objective 5, carried as a set of scenarios.
4. **Model ranking unresolved.** The locked models of both tiers are INCONCLUSIVE against their next-best model. The
   choice is a point estimate with a caveat. Objective 5 therefore states that the model choice is not resolved.
5. **Hybrid not separated from its trend.** Inner validation chose no residual correlation, so the hybrid equals its trend.
   Whether a residual structure exists cannot be tested with these data.

**What data would resolve them.** Infill drilling between the existing lines would resolve the lateral structure at the
scale of the between-line gap. Assays on the logged intervals would allow a grade-based definition and remove the label
conflicts. A surveyed collar RL would allow absolute elevation, and a measured downhole orientation would allow a true structural
frame instead of a statistically selected dip.
''')

MD(r'''
## 9. Appendix

### Commands that regenerate everything

```bash
pip install -e ".[notebook]"               # installs the notebook extra (Jupyter, nbformat, nbclient, papermill)
python notebooks/build_notebook.py          # regenerates the .ipynb (no outputs) and MATH_NOTES.md
papermill notebooks/Kambale_Thesis_Results.ipynb notebooks/output/Results_present.ipynb -p MODE present
jupyter nbconvert --to html notebooks/output/Results_present.ipynb --no-input
```

The notebook reads the databases read-only. `notebooks/output/` holds executed copies, which contain query results, and is
not committed. See `notebooks/README.md`.

### Run reports and configurations (relative links)

Links are relative to this notebook (in `notebooks/`).

- Stage A (Objective 1): [QA/QC report](../reports/QAQC_REPORT.md)
- Objective 2: [run report](../reports/objective_2/RUN_REPORT.md), [README](../reports/objective_2/README.md)
- Objective 3: [run report](../reports/objective_3/RUN_REPORT.md), [README](../reports/objective_3/README.md)
- Objective 4, tier 1 (extrapolation): [run report](../reports/objective_4/tier_1/RUN_REPORT.md)
- Objective 4, tier 2 (interpolation): [run report](../reports/objective_4/tier_2/RUN_REPORT.md)
- Objective 5: [run report](../reports/objective_5/RUN_REPORT.md)
- Specification (scope and claims): `specs/01_thesis_scope_and_objective_traceability.md`
- Decision logs: `config/objective_2/superseded/`, `config/objective_3/superseded/`, `config/objective_4/superseded/`,
  `config/objective_5/superseded/`
''')


# =====================================================================================================================
# Writers
# =====================================================================================================================

def math_document() -> str:
    parts = [
        "# Mathematical notes: Kambale graphite results",
        "",
        "Generated by `notebooks/build_notebook.py` from the same strings as "
        "`notebooks/Kambale_Thesis_Results.ipynb`. Edit the builder, not this file. Each formula is tied to the "
        "module and function that implements it; configuration keys are given where a parameter is set.",
        "",
        "Notation: $\\mathbf u$ is a location, $i(\\mathbf u)\\in\\{0,1\\}$ the indicator of a graphitic interval, "
        "$p=\\Pr(i=1)$ the prevalence, $\\gamma(h)$ the semivariogram at lag $h$, $c_0$ the nugget, $c_1$ the structured "
        "sill, $a$ the practical range, $\\sigma(t)=1/(1+e^{-t})$.",
        "",
    ]
    titles = {
        "O1": "1. Objective 1: database, geometry and graphitic label",
        "O2": "2. Objective 2: occurrence, indicator variography and structure",
        "O3": "3. Objective 3: indicator kriging, machine learning and hybrid models",
        "O4": "4. Objective 4: probability metrics, paired comparisons and decision rule",
        "O5": "5. Objective 5: three-dimensional probability, uncertainty and scenarios",
    }
    for key in ("O1", "O2", "O3", "O4", "O5"):
        parts.append(f"## {titles[key]}")
        parts.append("")
        for block in MATH[key]:
            parts.append(textwrap.dedent(block).strip("\n"))
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def build_notebook() -> None:
    try:
        import nbformat
        from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(f"nbformat is required to build the notebook: {exc}. Install with pip install -e \".[notebook]\".")

    cells = []
    for kind, source, tags in CELLS:
        if kind == "markdown":
            cells.append(new_markdown_cell(source))
        else:
            cell = new_code_cell(source)
            cell.outputs = []
            cell.execution_count = None
            if tags:
                cell.metadata["tags"] = tags
            cells.append(cell)
    notebook = new_notebook(cells=cells, metadata={
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
    })
    nbformat.validate(notebook)
    nbformat.write(notebook, NOTEBOOK_PATH)


def main() -> int:
    build_notebook()
    MATH_PATH.write_text(math_document(), encoding="utf-8")
    print(f"wrote {NOTEBOOK_PATH}")
    print(f"wrote {MATH_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

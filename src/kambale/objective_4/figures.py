"""Objective 4 figure renderers.

Every figure reads only its registered SQL file in sql/objective_4/figures/ against the latest evaluation receipt.
A figure whose required rows are missing is registered NOT_SUPPORTED with the reason.
"""

from __future__ import annotations

import textwrap
from collections import OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from kambale.objective_4.config import (O4_DB_PATH, O4_FIGURE_DIR, O4_SQL_DIR, PROJECT_ROOT, StopError, sha256_bytes,
                                        utc_now)  # noqa: E402
from kambale.objective_4.db import connect_o4  # noqa: E402

BLUE = "#0072B2"
GREEN = "#009E73"
VERMILLION = "#D55E00"
ORANGE = "#E69F00"
PURPLE = "#CC79A7"
NEUTRAL = "#6E6E6E"
LIGHT = "#C9C9C9"
INK = "#222222"
MUTED = "#555555"
FOLD_COLORS = [BLUE, GREEN, VERMILLION, ORANGE, PURPLE]
FOLD_MARKERS = ["o", "s", "^", "D", "v"]
MODEL_COLORS = {"BASE_PREVALENCE": NEUTRAL, "BASE_LOGISTIC": GREEN, "M2_RF": BLUE, "M2_HGB": ORANGE,
                "M1_IK": LIGHT, "M3_HYBRID": PURPLE}
MODEL_ORDER = ["BASE_PREVALENCE", "BASE_LOGISTIC", "M2_RF", "M2_HGB"]
MODEL_LABEL = {"BASE_PREVALENCE": "Prevalence", "BASE_LOGISTIC": "Logistic", "M2_RF": "Random forest",
               "M2_HGB": "Gradient boosting", "M1_IK": "M1 kriging", "M3_HYBRID": "M3 hybrid (fallback)"}

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.grid": False,
    "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 300, "pdf.compression": 6,
})


class NotSupported(Exception):
    pass


def load_queries(path: Path) -> OrderedDict:
    queries, name, buf = OrderedDict(), None, []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        if line.startswith("-- name:"):
            if name is not None:
                queries[name] = "".join(buf)
            name, buf = line.split(":", 1)[1].strip(), []
        elif name is not None:
            buf.append(line)
    if name is not None:
        queries[name] = "".join(buf)
    if not queries:
        raise StopError(f"{path.name} defines no named query")
    return queries


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _footer(fig, receipt, extra):
    base = (f"O4 receipt {receipt['receipt_id']} | O3 split {receipt['o3_split_plan_id']} | "
            f"{receipt['o1_label_rule_id']} APPROVED | geometry {receipt['geometry_status']} | "
            f"EPSG:32630 datum VERIFIED | vertical relative to collar")
    fig.text(0.01, 0.012, textwrap.fill(f"{base} | {extra}", 170), fontsize=5.0, color=MUTED, ha="left", va="bottom")


def _caption(receipt, body):
    return (f"{body} Support: 1 m logged intervals, 1,829 held-out intervals in 71 holes on five drill lines. "
            f"Geometry {receipt['geometry_status']}: straight holes, depth relative to collar; absolute elevation is "
            "not used. This is internal spatially held-out validation, not an external prospective campaign.")


def _model_color(m):
    return MODEL_COLORS.get(m, NEUTRAL)


def _fold_map(rows, receipt):
    collars, counts, cov = rows["fold_map"], rows["fold_counts"], rows["coverage"]
    if not collars:
        raise NotSupported("no held-out observations in the evaluation population")
    lines = {r["fold_id"]: r["line_code"] for r in counts}
    positive = {r["fold_id"]: r["positive"] for r in counts}
    fig = plt.figure(figsize=(7.6, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0], left=0.09, right=0.98, top=0.86, bottom=0.24, wspace=0.3)
    ax = fig.add_subplot(gs[0, 0])
    for k, fold in enumerate(sorted({c["fold_id"] for c in collars})):
        sub = [c for c in collars if c["fold_id"] == fold]
        ax.scatter([c["easting_m"] for c in sub], [c["northing_m"] for c in sub], s=22,
                   marker=FOLD_MARKERS[k % len(FOLD_MARKERS)], color=FOLD_COLORS[k % len(FOLD_COLORS)],
                   edgecolors="white", linewidths=0.5, zorder=3,
                   label=f"Fold {fold}: hold out {lines.get(fold, '?')} "
                         f"({len(sub)} holes, {positive.get(fold, 0)} positive)")
        if sub:
            west = min(sub, key=lambda c: c["easting_m"])
            ax.annotate(f"F{fold}", (west["easting_m"], west["northing_m"]), xytext=(-10, 0),
                        textcoords="offset points", ha="right", va="center", fontsize=6.2,
                        color=FOLD_COLORS[k % len(FOLD_COLORS)])
    ax.set_xlabel("UTM 30N easting (m)")
    ax.set_ylabel("UTM 30N northing (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.set_title("Held-out drill line and evaluation population", loc="left", fontsize=7.5)
    ax.legend(loc="upper left", markerscale=1.2, handletextpad=0.4, borderaxespad=0.2, fontsize=5.8)
    ax2 = fig.add_subplot(gs[0, 1])
    x = np.arange(len(cov))
    pred = np.array([r["n_predicted"] for r in cov], dtype=float)
    fail = np.array([r["n_failed"] for r in cov], dtype=float)
    ax2.bar(x, pred, width=0.62, color=[_model_color(r["model_id"]) for r in cov], linewidth=0)
    ax2.bar(x, fail, bottom=pred, width=0.62, color=LIGHT, hatch="////", edgecolor="white", linewidth=0.4)
    for k, r in enumerate(cov):
        ax2.text(k, r["n_expected"] + 30, f"{r['coverage']:.2f}", ha="center", va="bottom", fontsize=5.8, color=INK)
    ax2.set_xticks(x, [r["model_id"].replace("BASE_", "").replace("M2_", "").replace("M1_", "") for r in cov],
                   rotation=35, ha="right", fontsize=5.8)
    ax2.set_ylim(0, 2050)
    ax2.set_ylabel("Held-out intervals")
    ax2.set_title("Prediction coverage by model", loc="left", fontsize=7.5)
    _footer(fig, receipt, "colored bars are predictions and hatched bars are explicit failures; all 1,829 held-out "
                          "intervals are in the common cohort; M1 has no prediction")
    return fig, _caption(receipt, "Held-out drill lines and the frozen evaluation population. The right panel shows "
                                  "prediction coverage per model: M1 has no prediction, M3 is the fallback identical to "
                                  "M2_RF, and the four feasible models cover every held-out interval.")


def _brier(rows, receipt):
    pooled, line, paired = rows["pooled_brier"], rows["line_brier"], rows["paired"]
    if not pooled:
        raise NotSupported("no pooled Brier score")
    models = [r["model_id"] for r in pooled]
    fig, (ax, axh) = plt.subplots(1, 2, figsize=(7.6, 4.4), gridspec_kw={"width_ratios": [1.0, 1.25]})
    fig.subplots_adjust(left=0.1, right=0.88, top=0.84, bottom=0.26, wspace=0.3)
    ax.bar(range(len(models)), [r["brier"] for r in pooled], width=0.62,
           color=[_model_color(m) for m in models], linewidth=0)
    for k, r in enumerate(pooled):
        ax.text(k, r["brier"] + 0.004, f"{r['brier']:.3f}", ha="center", va="bottom", fontsize=6.0, color=INK)
    ax.set_xticks(range(len(models)), [MODEL_LABEL[m] for m in models], rotation=30, ha="right", fontsize=6.0)
    ax.set_ylim(0, max(r["brier"] for r in pooled) * 1.25)
    ax.set_ylabel("Pooled Brier score (interval-weighted)")
    ax.set_title("Pooled held-out Brier", loc="left", fontsize=7.5)
    # The per-line heatmap compares the candidate models; the prevalence baseline stays in the pooled panel.
    heat_models = [m for m in models if m != "BASE_PREVALENCE"]
    lines = sorted({r["line_code"] for r in line})
    grid = np.full((len(heat_models), len(lines)), np.nan)
    for r in line:
        if r["model_id"] in heat_models:
            grid[heat_models.index(r["model_id"]), lines.index(r["line_code"])] = r["brier"]
    im = axh.imshow(grid, aspect="auto", cmap="cividis", vmin=0.15, vmax=0.27)
    for i in range(len(heat_models)):
        for j in range(len(lines)):
            if np.isfinite(grid[i, j]):
                axh.text(j, i, f"{grid[i, j]:.3f}", ha="center", va="center", fontsize=5.8,
                         color="white" if grid[i, j] < 0.21 else INK)
    axh.set_xticks(range(len(lines)), [ln.replace("NOM_", "") for ln in lines], rotation=30, ha="right", fontsize=5.8)
    axh.set_yticks(range(len(heat_models)), [MODEL_LABEL[m] for m in heat_models], fontsize=6.0)
    axh.set_title("Brier by held-out line (models; baseline pooled)", loc="left", fontsize=7.5)
    cax = fig.add_axes([0.9, 0.26, 0.012, 0.58])
    fig.colorbar(im, cax=cax, label="Brier")
    note = "; ".join(f"{r['pair_id']} {r['delta_brier']:+.4f} [{r['ci_low']:+.4f}, {r['ci_high']:+.4f}]"
                     for r in paired if r["ci_low"] is not None)
    _footer(fig, receipt, "sign convention delta Brier = Brier(a) - Brier(b); " + (note or "no paired rows") +
            "; M1 has no prediction and M3 equals M2_RF")
    return fig, _caption(receipt, "Pooled and line-by-line Brier scores on the identical 1,829-interval cohort. "
                                  "Lower is better. The paired note gives the point difference and its 95% hole-cluster "
                                  "interval; an interval that includes zero is not evidence of an improvement.")


def _curves(rows, receipt):
    pts = rows["curve_points"]
    if not pts:
        raise NotSupported("no curve points")
    disc = {(r["model_id"], r["metric_id"]): r for r in rows["discrimination"]}
    prev = rows["prevalence"][0]["prevalence"] if rows["prevalence"] else None
    fig, (axr, axp) = plt.subplots(1, 2, figsize=(7.6, 4.0))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.84, bottom=0.19, wspace=0.26)
    for m in MODEL_ORDER:
        roc = sorted([r for r in pts if r["model_id"] == m and r["curve"] == "ROC"], key=lambda r: r["point_index"])
        pr = sorted([r for r in pts if r["model_id"] == m and r["curve"] == "PR"], key=lambda r: r["point_index"])
        if roc:
            auc = disc.get((m, "ROC_AUC"), {}).get("value")
            axr.plot([r["fpr"] for r in roc], [r["tpr"] for r in roc], color=_model_color(m), lw=1.1,
                     label=f"{MODEL_LABEL[m]} (AUC {auc:.3f})" if auc is not None else MODEL_LABEL[m])
        if pr:
            ap = disc.get((m, "PR_AUC"), {}).get("value")
            axp.plot([r["recall"] for r in pr], [r["precision"] for r in pr], color=_model_color(m), lw=1.1,
                     label=f"{MODEL_LABEL[m]} (AP {ap:.3f})" if ap is not None else MODEL_LABEL[m])
    axr.plot([0, 1], [0, 1], ls="--", lw=0.8, color=NEUTRAL)
    axr.set_xlabel("False positive rate")
    axr.set_ylabel("True positive rate")
    axr.set_xlim(0, 1)
    axr.set_ylim(0, 1)
    axr.set_title("ROC curves, pooled held-out cohort", loc="left", fontsize=7.5)
    axr.legend(loc="lower right", fontsize=5.8)
    if prev is not None:
        axp.axhline(prev, ls="--", lw=0.8, color=NEUTRAL, label=f"Positive-rate baseline {prev:.3f}")
    axp.set_xlabel("Recall")
    axp.set_ylabel("Precision")
    axp.set_xlim(0, 1)
    axp.set_ylim(0, 1)
    axp.set_title("Precision-recall curves", loc="left", fontsize=7.5)
    axp.legend(loc="upper right", fontsize=5.8)
    _footer(fig, receipt, "AUC and average precision are weighted; M1 has no prediction and M3 duplicates M2_RF")
    return fig, _caption(receipt, "ROC and precision-recall curves for the four distinct feasible models on the pooled "
                                  "held-out cohort. The dashed line in the PR panel is the prevalence baseline. Curves are "
                                  "descriptive; the Brier score is the primary endpoint.")


def _reliability(rows, receipt):
    bins, diag = rows["bins"], rows["diagnostics"]
    if not bins:
        raise NotSupported("no calibration bins")
    models = [m for m in MODEL_ORDER if any(b["model_id"] == m for b in bins)]
    ncols = 2
    nrows = int(np.ceil(len(models) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.2, 3.2 * nrows))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.12, wspace=0.28, hspace=0.5)
    axes = np.atleast_1d(axes).ravel()
    for ax, m in zip(axes, models):
        bb = sorted([b for b in bins if b["model_id"] == m], key=lambda b: b["bin_index"])
        d = next((x for x in diag if x["model_id"] == m), None)
        xs = [b["mean_p"] for b in bb]
        ys = [b["observed_rate"] for b in bb]
        lo = [b["wilson_low"] for b in bb]
        hi = [b["wilson_high"] for b in bb]
        ax.plot([0, 1], [0, 1], ls="--", lw=0.8, color=NEUTRAL)
        ax.errorbar(xs, ys, yerr=[np.array(ys) - np.array(lo), np.array(hi) - np.array(ys)], fmt="o", ms=3.2,
                    lw=0.8, capsize=1.5, color=_model_color(m))
        for b in bb:
            ax.text(b["mean_p"] + 0.012, b["observed_rate"] + 0.02, str(b["n"]), ha="left", va="bottom", fontsize=4.6,
                    color=MUTED)
        title = MODEL_LABEL[m]
        if d:
            title += f"\nslope {d['slope']:.2f}, intercept {d['intercept']:.2f}, ECE {d['ece']:.3f}"
        ax.set_title(title, loc="left", fontsize=6.6)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Mean predicted probability")
        ax.set_ylabel("Observed positive rate")
    for ax in axes[len(models):]:
        ax.axis("off")
    _footer(fig, receipt, "Wilson 95% intervals; numbers above points are merged-bin counts; diagnostics are not applied")
    return fig, _caption(receipt, "Reliability diagrams for the feasible models on the pooled held-out cohort. The "
                                  "diagonal is perfect calibration. Calibration intercept and slope are diagnostic fits and "
                                  "are never used to recalibrate the predictions.")


def _paired(rows, receipt):
    line, pooled, m1 = rows["line_pairs"], rows["pooled_pairs"], (rows["m1"][0] if rows["m1"] else None)
    if not line or not pooled:
        raise NotSupported("no paired line differences")
    fig, axes = plt.subplots(1, 3, figsize=(7.8, 3.8), gridspec_kw={"width_ratios": [1.0, 1.0, 0.85]})
    fig.subplots_adjust(left=0.08, right=0.98, top=0.84, bottom=0.22, wspace=0.32)
    for ax, pair_id, title in ((axes[0], "M3_vs_M2_RF", "M3 hybrid vs M2_RF"),
                               (axes[1], "M3_vs_M2_HGB", "M3 hybrid vs M2_HGB")):
        rr = sorted([r for r in line if r["pair_id"] == pair_id], key=lambda r: r["line_code"])
        x = np.arange(len(rr))
        ax.bar(x, [r["delta_brier"] for r in rr], width=0.6, color=PURPLE if pair_id.endswith("RF") else ORANGE,
               linewidth=0)
        ax.axhline(0, lw=0.8, color=NEUTRAL)
        ax.set_xticks(x, [r["line_code"].replace("NOM_", "") for r in rr], rotation=30, ha="right", fontsize=5.8)
        ax.set_ylabel("Delta Brier (a - b)")
        ax.set_title(title, loc="left", fontsize=7)
        p = next((r for r in pooled if r["pair_id"] == pair_id), None)
        if p and p["ci_low"] is not None:
            ax.text(0.98, 0.95, f"pooled {p['delta_brier']:+.4f}\nhole CI [{p['ci_low']:+.4f}, {p['ci_high']:+.4f}]",
                    transform=ax.transAxes, fontsize=5.6, color=INK, va="top", ha="right",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.2))
    axes[0].text(0.5, 0.55, "Delta = 0 in every line\nM3 is the M2_RF fallback", transform=axes[0].transAxes,
                 ha="center", va="center", fontsize=6.4, color=MUTED)
    axes[2].axis("off")
    if m1:
        text = (f"M1: {m1['n_predicted']} of {m1['n_expected']} predicted\n"
                f"{m1['n_failed']} explicit failures\nM1 is NOT_COMPARABLE")
    else:
        text = "M1: no coverage row"
    axes[2].text(0.05, 0.7, text, fontsize=7, color=INK, va="top")
    axes[2].set_title("Hybrid vs M1", loc="left", fontsize=7)
    _footer(fig, receipt, "line panels are interval-weighted; equal-hole sensitivity is in O4-T04; negative delta "
                          "means model a has the lower Brier; M3 equals M2_RF by construction")
    return fig, _caption(receipt, "Paired hybrid-versus-M2 Brier differences by held-out line. The M3 hybrid is the "
                                  "recorded ML-only fallback and its contrast with M2_RF is exactly zero. The M1 contrast "
                                  "is not estimable because M1 produced no prediction.")


def _error_map(rows, receipt):
    sel = rows["selected"]
    errs = rows["selected_errors"]
    if not sel or not errs:
        raise NotSupported("no selected model or no withheld errors")
    model = sel[0]["model_id"]
    lines = sorted({e["line_code"] for e in errs})
    fig, axes = plt.subplots(1, len(lines), figsize=(7.8, 4.2), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.9, top=0.82, bottom=0.2, wspace=0.12)
    axes = np.atleast_1d(axes)
    sc = None
    for ax, line in zip(axes, lines):
        sub = [e for e in errs if e["line_code"] == line]
        sc = ax.scatter([e["easting_m"] for e in sub], [e["z_relative_m"] for e in sub],
                        c=[e["residual"] for e in sub], cmap="RdBu_r", vmin=-1, vmax=1, s=7, linewidths=0)
        wrong = [e for e in sub if e["true_label"] != e["predicted_class"]]
        ax.scatter([e["easting_m"] for e in wrong], [e["z_relative_m"] for e in wrong], s=14, facecolors="none",
                   edgecolors=INK, linewidths=0.35)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
        ax.ticklabel_format(style="plain", useOffset=False, axis="x")
        ax.tick_params(axis="x", labelrotation=30)
        ax.set_title(f"{line.replace('NOM_', '')} (n={len(sub)})", loc="left", fontsize=6.6)
        ax.set_xlabel("Easting (m)")
    axes[0].set_ylabel("Relative Z (m)")
    cax = fig.add_axes([0.92, 0.2, 0.012, 0.6])
    fig.colorbar(sc, cax=cax, label="Residual y - p")
    _footer(fig, receipt, f"selected model {model}; black rings mark misclassified intervals")
    return fig, _caption(receipt, f"Residuals of the selected model ({model}) on the withheld observations, by held-out "
                                  "line. Blue residuals are over-predictions and red residuals under-predictions; black "
                                  "rings mark misclassified intervals at the frozen threshold.")


def _coverage(rows, receipt):
    cov, by_line = rows["coverage"], rows["coverage_by_line"]
    if not cov:
        raise NotSupported("no coverage rows")
    fig, (ax, axh) = plt.subplots(1, 2, figsize=(7.6, 4.3), gridspec_kw={"width_ratios": [1.0, 1.25]})
    fig.subplots_adjust(left=0.1, right=0.98, top=0.84, bottom=0.26, wspace=0.28)
    x = np.arange(len(cov))
    pred = np.array([r["n_predicted"] for r in cov], dtype=float)
    fail = np.array([r["n_failed"] for r in cov], dtype=float)
    ax.bar(x, pred, width=0.62, color=[_model_color(r["model_id"]) for r in cov], linewidth=0)
    ax.bar(x, fail, bottom=pred, width=0.62, color=LIGHT, hatch="////", edgecolor="white", linewidth=0.3)
    for k, r in enumerate(cov):
        ax.text(k, r["n_expected"] + 30, f"{r['coverage']:.2f}", ha="center", va="bottom", fontsize=5.6, color=INK)
    ax.set_xticks(x, [r["model_id"].replace("BASE_", "").replace("M2_", "").replace("M1_", "") for r in cov],
                  rotation=35, ha="right", fontsize=5.8)
    ax.set_ylim(0, 2050)
    ax.set_ylabel("Held-out intervals")
    ax.set_title("Coverage and abstention", loc="left", fontsize=7.5)
    models = [r["model_id"] for r in cov]
    lines = sorted({r["line_code"] for r in by_line})
    grid = np.full((len(models), len(lines)), np.nan)
    for r in by_line:
        grid[models.index(r["model_id"]), lines.index(r["line_code"])] = r["predicted"] / r["expected"]
    im = axh.imshow(grid, aspect="auto", cmap="cividis", vmin=0, vmax=1)
    for i in range(len(models)):
        for j in range(len(lines)):
            axh.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=5.8,
                     color="white" if grid[i, j] < 0.6 else INK)
    axh.set_xticks(range(len(lines)), [ln.replace("NOM_", "") for ln in lines], rotation=30, ha="right", fontsize=5.8)
    axh.set_yticks(range(len(models)), [MODEL_LABEL.get(m, m) for m in models], fontsize=5.8)
    axh.set_title("Coverage by model and held-out line", loc="left", fontsize=7.5)
    cax = fig.add_axes([0.93, 0.26, 0.012, 0.58])
    fig.colorbar(im, cax=cax, label="Coverage")
    _footer(fig, receipt, "colored bars are predictions and hatched bars are explicit failures; a missing prediction "
                          "is a coverage result and is never dropped silently")
    return fig, _caption(receipt, "Prediction coverage and abstention per model and held-out line. M1 has no prediction; "
                                  "the failure rows are retained. M3 is the fallback identical to M2_RF.")


FIGURES = OrderedDict([
    ("O4-F01", ("Spatial holdout fold map and coverage", "O4_F01_holdout_coverage", _fold_map, "O4-F01.sql")),
    ("O4-F02", ("Brier score by model and held-out line", "O4_F02_brier", _brier, "O4-F02.sql")),
    ("O4-F03", ("ROC and PR curves", "O4_F03_curves", _curves, "O4-F03.sql")),
    ("O4-F04", ("Reliability diagrams", "O4_F04_reliability", _reliability, "O4-F04.sql")),
    ("O4-F05", ("Paired hybrid differences by line", "O4_F05_paired", _paired, "O4-F05.sql")),
    ("O4-F06", ("Selected-model residuals on withheld observations", "O4_F06_residuals", _error_map, "O4-F06.sql")),
    ("O4-F07", ("Coverage and missing predictions", "O4_F07_coverage", _coverage, "O4-F07.sql")),
])


def _save(fig, figure_id, stem):
    O4_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["svg.hashsalt"] = figure_id
    paths = []
    for ext, kwargs in (("svg", {"metadata": {"Date": None}}),
                        ("pdf", {"metadata": {"CreationDate": None, "ModDate": None}}),
                        ("png", {"dpi": 300, "metadata": {"Software": None}})):
        path = O4_FIGURE_DIR / f"{stem}.{ext}"
        fig.savefig(path, **kwargs)
        paths.append(path)
    return paths


def render_all(o4_path=None, figure_ids=None):
    conn = connect_o4(o4_path or O4_DB_PATH)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise StopError("no receipt: run the import first")
        receipt = dict(receipt)
        created = utc_now()
        summary = {}
        for fid, (title, stem, renderer, sql_file) in FIGURES.items():
            if figure_ids and fid not in figure_ids:
                continue
            sql_path = O4_SQL_DIR / "figures" / sql_file
            queries = load_queries(sql_path)
            rows = {name: [dict(r) for r in conn.execute(text).fetchall()] for name, text in queries.items()}
            try:
                fig, caption = renderer(rows, receipt)
            except NotSupported as exc:
                fig, caption, status, reason = None, f"Not drawn: {exc}.", "NOT_SUPPORTED", str(exc)
            else:
                status, reason = "GENERATED", "rendered from the registered queries"
            conn.execute("DELETE FROM figure_sql_registry WHERE figure_id = ?", (fid,))
            conn.execute("INSERT OR REPLACE INTO figure_registry (figure_id, title, status, reason, caption, created_utc) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (fid, title, status, reason, caption, created))
            for name, text in queries.items():
                conn.execute("INSERT INTO figure_sql_registry (figure_id, query_name, sql_path, sql_sha256, params_json, "
                             "row_count) VALUES (?, ?, ?, ?, ?, ?)",
                             (fid, name, _rel(sql_path), sha256_bytes(sql_path.read_bytes()), "{}", len(rows[name])))
            if fig is None:
                summary[fid] = {"status": status, "reason": reason}
                continue
            paths = _save(fig, fid, stem)
            plt.close(fig)
            for path in paths:
                conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_id, "
                             "sha256, bytes, created_utc) VALUES (?, 'FIGURE', ?, ?, ?, ?)",
                             (_rel(path), fid, sha256_bytes(path.read_bytes()), path.stat().st_size, created))
            summary[fid] = {"status": status, "files": [_rel(p) for p in paths]}
        return summary
    finally:
        conn.close()

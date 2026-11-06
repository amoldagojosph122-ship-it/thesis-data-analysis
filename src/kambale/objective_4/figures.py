"""Objective 4 figure renderers, one set per evaluation tier.

Every figure reads only its registered SQL file in sql/objective_4/figures/ against the latest evaluation receipt.
A figure whose required rows are missing is registered NOT_SUPPORTED with the reason. Labels and captions are
built from the receipt, the tier's config and the database counts, not from fixed text.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from kambale.objective_4.config import (O4_CONFIG_PATH, O4_DB_PATH, O4_FIGURE_DIR, O4_SQL_DIR, PROJECT_ROOT, StopError,
                                        load_config, sha256_bytes, utc_now)  # noqa: E402
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
MODEL_ORDER = ["BASE_PREVALENCE", "BASE_LOGISTIC", "BASE_LOGISTIC_WF", "M2_RF", "M2_RF_WF", "M2_HGB", "M2_HGB_WF",
               "M2_SEL", "M2_WF_SEL", "M1_IK", "M3_HYBRID"]
MODEL_COLORS = {"BASE_PREVALENCE": NEUTRAL, "BASE_LOGISTIC": GREEN, "BASE_LOGISTIC_WF": "#7ACFB5",
                "M2_RF": BLUE, "M2_RF_WF": "#8DB9DE", "M2_HGB": ORANGE, "M2_HGB_WF": "#F3CD73",
                "M2_SEL": "#0B3C5D", "M2_WF_SEL": "#5C8FB0", "M1_IK": VERMILLION, "M3_HYBRID": PURPLE}
MODEL_LABEL = {"BASE_PREVALENCE": "Prevalence", "BASE_LOGISTIC": "Logistic", "BASE_LOGISTIC_WF": "Logistic + weathering",
               "M2_RF": "Random forest", "M2_RF_WF": "Random forest + weathering", "M2_HGB": "Gradient boosting",
               "M2_HGB_WF": "Gradient boosting + weathering", "M2_SEL": "M2 selected (= RF)",
               "M2_WF_SEL": "M2 + weathering selected", "M1_IK": "M1 indicator kriging",
               "M3_HYBRID": "M3 hybrid"}
MODEL_SHORT = {"BASE_PREVALENCE": "Prevalence", "BASE_LOGISTIC": "Logistic", "BASE_LOGISTIC_WF": "Logistic+WF",
               "M2_RF": "RF", "M2_RF_WF": "RF+WF", "M2_HGB": "GB", "M2_HGB_WF": "GB+WF", "M2_SEL": "M2 sel.",
               "M2_WF_SEL": "M2+WF sel.", "M1_IK": "M1 kriging", "M3_HYBRID": "M3 hybrid"}
PAIR_COLORS = {"RESOLVED": GREEN, "UNRESOLVED": ORANGE, "IDENTICAL": NEUTRAL}
WEATHERING_PAIRS = {"LOG_vs_LOGWF": ("Logistic", GREEN), "RF_vs_RFWF": ("Random forest", BLUE),
                    "HGB_vs_HGBWF": ("Gradient boosting", ORANGE)}

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.2, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
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


def _label(model):
    return MODEL_LABEL.get(model, model)


def _short(model):
    return MODEL_SHORT.get(model, model)


def _color(model):
    return MODEL_COLORS.get(model, LIGHT)


def _unit_phrase(receipt):
    return ("held-out drill line" if receipt["fold_unit"] == "HELD_OUT_LINE" else "interleaved hole fold")


def _caption(receipt, body):
    return (f"{body} Support: {receipt['n_common']} held-out one-metre intervals in {receipt['n_holes']} holes on "
            f"{receipt['n_lines']} drill lines, evaluated by {_unit_phrase(receipt)}. Geometry "
            f"{receipt['geometry_status']}: straight holes, depth relative to collar; absolute elevation is not used. "
            f"Claim: {receipt['claim']}")


def _identity_note(rows):
    ids = rows.get("identities", [])
    if not ids:
        return "no identical models"
    return "identical, not drawn: " + "; ".join(f"{_short(r['model_id'])} = {_short(r['identical_to'])}" for r in ids)


def _fold_map(rows, receipt):
    collars, counts, cov = rows["fold_map"], rows["fold_counts"], rows["coverage"]
    if not collars:
        raise NotSupported("no held-out observations in the evaluation population")
    fig = plt.figure(figsize=(7.6, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0], left=0.09, right=0.98, top=0.86, bottom=0.24, wspace=0.3)
    ax = fig.add_subplot(gs[0, 0])
    fold_markers = ["o", "s", "^", "D", "v"]
    fold_colors = [BLUE, GREEN, VERMILLION, ORANGE, PURPLE]
    count_by_fold = {r["fold_id"]: r for r in counts}
    for k, fold in enumerate(sorted({c["fold_id"] for c in collars})):
        sub = [c for c in collars if c["fold_id"] == fold]
        meta = count_by_fold.get(fold, {})
        if receipt["fold_unit"] == "HELD_OUT_LINE":
            text = f"Fold {fold}: hold out {meta.get('lines', '?')} ({len(sub)} holes, {meta.get('positive', 0)} positive)"
        else:
            text = f"Fold {fold}: interleaved holes ({len(sub)} holes, {meta.get('positive', 0)} positive)"
        ax.scatter([c["easting_m"] for c in sub], [c["northing_m"] for c in sub], s=22,
                   marker=fold_markers[k % len(fold_markers)], color=fold_colors[k % len(fold_colors)],
                   edgecolors="white", linewidths=0.5, zorder=3, label=text)
    ax.set_xlabel("UTM 30N easting (m)")
    ax.set_ylabel("UTM 30N northing (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.set_title(f"Hole collars by {_unit_phrase(receipt)} (shallowest collar per hole)", loc="left", fontsize=7.5)
    ax.legend(loc="upper left", markerscale=1.2, handletextpad=0.4, borderaxespad=0.2, fontsize=5.6)
    ax2 = fig.add_subplot(gs[0, 1])
    x = np.arange(len(cov))
    pred = np.array([r["n_predicted"] for r in cov], dtype=float)
    fail = np.array([r["n_failed"] for r in cov], dtype=float)
    ax2.bar(x, pred, width=0.62, color=[_color(r["model_id"]) for r in cov], linewidth=0)
    ax2.bar(x, fail, bottom=pred, width=0.62, color=LIGHT, hatch="////", edgecolor="white", linewidth=0.4)
    top = max(r["n_expected"] for r in cov)
    for k, r in enumerate(cov):
        ax2.text(k, r["n_expected"] + top * 0.012, f"{r['coverage']:.2f}", ha="center", va="bottom", fontsize=5.2, color=INK)
    ax2.set_xticks(x, [_short(r["model_id"]) for r in cov], rotation=40, ha="right", fontsize=5.4)
    ax2.set_ylim(0, top * 1.1)
    ax2.set_ylabel("Held-out intervals")
    ax2.set_title("Prediction coverage by model", loc="left", fontsize=7.5)
    return fig, _caption(receipt, f"Held-out {_unit_phrase(receipt)}s and the evaluation population. The right panel "
                                  "shows prediction coverage per model: coloured bars are predictions, hatched bars are "
                                  "explicit failures, and the number above each bar is coverage (coverage below 0.95 is "
                                  "not comparable). A missing prediction is a coverage result and is never dropped silently.")


def _brier(rows, receipt):
    pooled, line = rows["pooled_brier"], rows["line_brier"]
    if not pooled:
        raise NotSupported("no pooled Brier score for a distinct feasible model")
    pooled = sorted(pooled, key=lambda r: r["brier"])
    fig, (ax, axh) = plt.subplots(1, 2, figsize=(7.8, 4.8), gridspec_kw={"width_ratios": [1.0, 1.15]})
    fig.subplots_adjust(left=0.27, right=0.865, top=0.84, bottom=0.22, wspace=0.95)
    y = np.arange(len(pooled))
    ax.barh(y, [r["brier"] for r in pooled], height=0.62, color=[_color(r["model_id"]) for r in pooled], linewidth=0)
    for k, r in enumerate(pooled):
        ax.text(r["brier"] + 0.001, k, f"{r['brier']:.4f}", ha="left", va="center", fontsize=5.6, color=INK)
    ax.set_yticks(y, [_label(r["model_id"]) for r in pooled], fontsize=5.8)
    ax.invert_yaxis()
    lo = min(r["brier"] for r in pooled)
    hi = max(r["brier"] for r in pooled)
    ax.set_xlim(max(0.0, lo - 0.03), hi + 0.02)
    ax.set_xlabel("Pooled Brier score (interval-weighted; lower is better)")
    ax.set_title("Pooled held-out Brier", loc="left", fontsize=7.5)
    heat_models = [r["model_id"] for r in pooled if r["model_id"] != "BASE_PREVALENCE"]
    lines = sorted({r["line_code"] for r in line})
    grid = np.full((len(heat_models), len(lines)), np.nan)
    for r in line:
        if r["model_id"] in heat_models:
            grid[heat_models.index(r["model_id"]), lines.index(r["line_code"])] = r["brier"]
    finite = grid[np.isfinite(grid)]
    vmin, vmax = (float(finite.min()), float(finite.max())) if finite.size else (0.0, 1.0)
    im = axh.imshow(grid, aspect="auto", cmap="cividis", vmin=vmin, vmax=vmax)
    mid = (vmin + vmax) / 2
    for i in range(len(heat_models)):
        for j in range(len(lines)):
            if np.isfinite(grid[i, j]):
                axh.text(j, i, f"{grid[i, j]:.3f}", ha="center", va="center", fontsize=5.4,
                         color="white" if grid[i, j] < mid else INK)
    axh.set_xticks(range(len(lines)), [ln.replace("NOM_", "") for ln in lines], rotation=30, ha="right", fontsize=5.6)
    axh.set_yticks(range(len(heat_models)), [_short(m) for m in heat_models], fontsize=5.8)
    axh.set_title("Brier by drill line (prevalence pooled only)", loc="left", fontsize=7.5)
    cax = fig.add_axes([0.89, 0.26, 0.012, 0.58])
    fig.colorbar(im, cax=cax, label="Brier")
    return fig, _caption(receipt, "Pooled and per-line Brier scores for each distinct feasible model on the identical "
                                  "common cohort. Models identical to an earlier model are not drawn ("
                                  + _identity_note(rows) + "). Lower is better; the paired intervals are in the "
                                  "paired-comparison figure.")


def _curves(rows, receipt):
    pts = rows["curve_points"]
    if not pts:
        raise NotSupported("no curve points")
    disc = {(r["model_id"], r["metric_id"]): r for r in rows["discrimination"]}
    prev = rows["prevalence"][0]["prevalence"] if rows["prevalence"] else None
    fig, (axr, axp) = plt.subplots(1, 2, figsize=(7.8, 4.4))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.84, bottom=0.19, wspace=0.26)
    for m in [x for x in MODEL_ORDER if any(p["model_id"] == x for p in pts)]:
        style = "--" if m.endswith("_WF") else "-"
        roc = sorted([r for r in pts if r["model_id"] == m and r["curve"] == "ROC"], key=lambda r: r["point_index"])
        pr = sorted([r for r in pts if r["model_id"] == m and r["curve"] == "PR"], key=lambda r: r["point_index"])
        if roc:
            auc = disc.get((m, "ROC_AUC"), {}).get("value")
            axr.plot([r["fpr"] for r in roc], [r["tpr"] for r in roc], color=_color(m), lw=1.0, ls=style,
                     label=f"{_short(m)} (AUC {auc:.3f})" if auc is not None else _short(m))
        if pr:
            ap = disc.get((m, "PR_AUC"), {}).get("value")
            axp.plot([r["recall"] for r in pr], [r["precision"] for r in pr], color=_color(m), lw=1.0, ls=style,
                     label=f"{_short(m)} (AP {ap:.3f})" if ap is not None else _short(m))
    axr.plot([0, 1], [0, 1], ls=":", lw=0.8, color=NEUTRAL)
    axr.set_xlabel("False positive rate")
    axr.set_ylabel("True positive rate")
    axr.set_xlim(0, 1)
    axr.set_ylim(0, 1)
    axr.set_title("ROC curves, pooled held-out cohort", loc="left", fontsize=7.5)
    axr.legend(loc="lower right", fontsize=5.2, frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)
    if prev is not None:
        axp.axhline(prev, ls=":", lw=0.8, color=NEUTRAL, label=f"Positive-rate baseline {prev:.3f}")
    axp.set_xlabel("Recall")
    axp.set_ylabel("Precision")
    axp.set_xlim(0, 1)
    axp.set_ylim(0, 1)
    axp.set_title("Precision-recall curves", loc="left", fontsize=7.5)
    axp.legend(loc="upper right", fontsize=5.2, frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)
    return fig, _caption(receipt, "ROC and precision-recall curves for the distinct feasible models on the pooled held-out "
                                  "cohort. Weathering-front models are dashed; AUC and average precision are weighted. "
                                  "The dotted line in the PR panel is the prevalence baseline. Curves are descriptive; "
                                  "the Brier score is the primary endpoint. " + _identity_note(rows) + ".")


def _reliability(rows, receipt):
    bins, diag = rows["bins"], rows["diagnostics"]
    if not bins:
        raise NotSupported("no calibration bins")
    models = [m for m in MODEL_ORDER if any(b["model_id"] == m for b in bins)]
    ncols = 3
    nrows = int(np.ceil(len(models) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.6, 2.55 * nrows))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.10, wspace=0.34, hspace=0.75)
    axes = np.atleast_1d(axes).ravel()
    for ax, m in zip(axes, models):
        bb = sorted([b for b in bins if b["model_id"] == m], key=lambda b: b["bin_index"])
        d = next((x for x in diag if x["model_id"] == m), None)
        xs = [b["mean_p"] for b in bb]
        ys = [b["observed_rate"] for b in bb]
        lo = [b["wilson_low"] for b in bb]
        hi = [b["wilson_high"] for b in bb]
        ax.plot([0, 1], [0, 1], ls=":", lw=0.8, color=NEUTRAL)
        ax.errorbar(xs, ys, yerr=[np.array(ys) - np.array(lo), np.array(hi) - np.array(ys)], fmt="o", ms=2.8,
                    lw=0.7, capsize=1.2, color=_color(m))
        title = _short(m)
        if d and d["slope"] is not None:
            title += f"\nslope {d['slope']:.2f}, intercept {d['intercept']:.2f}, ECE {d['ece']:.3f}"
        ax.set_title(title, loc="left", fontsize=6.2)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Mean predicted probability", fontsize=5.8)
        ax.set_ylabel("Observed rate", fontsize=5.8)
        ax.tick_params(labelsize=5.2)
    for ax in axes[len(models):]:
        ax.axis("off")
    return fig, _caption(receipt, "Reliability diagrams for the distinct feasible models on the pooled held-out cohort. The "
                                  "dotted diagonal is perfect calibration. Bars are Wilson 95% intervals. The slope and "
                                  "intercept are diagnostic fits and are never used to recalibrate the predictions.")


def _paired(rows, receipt):
    pooled, line = rows["pooled_pairs"], rows["line_pairs"]
    if not pooled:
        raise NotSupported("no paired differences")
    fig = plt.figure(figsize=(7.9, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0], left=0.30, right=0.98, top=0.86, bottom=0.17, wspace=1.0)
    ax = fig.add_subplot(gs[0, 0])
    rows_sorted = list(reversed(pooled))
    for k, r in enumerate(rows_sorted):
        label = r["power_label"]
        if label == "IDENTICAL" or r["delta_brier"] is None:
            ax.scatter([0], [k], marker="D", s=14, facecolors="white", edgecolors=NEUTRAL, linewidths=0.8, zorder=3)
            note, color = "IDENTICAL, no interval", NEUTRAL
        else:
            color = PAIR_COLORS.get(label, NEUTRAL)
            ax.errorbar([r["delta_brier"]], [k], xerr=[[r["delta_brier"] - r["ci_low"]], [r["ci_high"] - r["delta_brier"]]],
                        fmt="o", ms=3.6, lw=1.0, capsize=2, color=color, zorder=3)
            note = (f"UNRESOLVED, +/-{r['detectable_half_width']:.4f}" if label == "UNRESOLVED" else label)
        # Labels sit in a fixed column outside the data area so they never overlap an interval.
        ax.text(1.04, k, note, transform=ax.get_yaxis_transform(), ha="left", va="center", fontsize=5.2,
                color=color, clip_on=False)
    ax.axvline(0, lw=0.8, color=NEUTRAL)
    ax.set_yticks(range(len(rows_sorted)), [f"{_short(r['model_a'])} vs {_short(r['model_b'])}" for r in rows_sorted],
                  fontsize=5.6)
    ax.set_xlabel("Brier(b) minus Brier(a); negative favours b")
    ax.set_title("Pooled differences, 95% hole-cluster intervals", loc="left", fontsize=7.2)
    ax2 = fig.add_subplot(gs[0, 1])
    lines = sorted({r["line_code"] for r in line})
    if line:
        width = 0.26
        for j, (pid, (name, color)) in enumerate(WEATHERING_PAIRS.items()):
            vals = []
            for ln in lines:
                match = next((r for r in line if r["pair_id"] == pid and r["line_code"] == ln), None)
                vals.append(match["delta_brier"] if match else np.nan)
            x = np.arange(len(lines)) + (j - 1) * width
            ax2.bar(x, vals, width=width * 0.92, color=color, linewidth=0, label=name)
        ax2.axhline(0, lw=0.8, color=NEUTRAL)
        ax2.set_xticks(range(len(lines)), [ln.replace("NOM_", "") for ln in lines], rotation=30, ha="right", fontsize=5.6)
        ax2.set_ylabel("Delta Brier (weathering - base)", fontsize=6.5)
        ax2.set_ylim(-0.0135, 0.024)
        ax2.legend(loc="upper left", ncol=1, fontsize=5.2, handlelength=1.2)
    else:
        ax2.text(0.5, 0.5, "no line-level weathering pairs", ha="center", va="center", transform=ax2.transAxes)
    ax2.set_title("Weathering effect by drill line", loc="left", fontsize=7.2)
    return fig, _caption(receipt, "Paired Brier differences for each configured comparison. Difference = Brier(b) minus "
                                  "Brier(a); the left panel shows the hole-cluster interval. The right panel is the "
                                  "line-level pattern of the weathering pairs (negative favours weathering). A pair is "
                                  "RESOLVED when its interval excludes zero, UNRESOLVED when it includes zero (the "
                                  "half-width is the smallest difference this design could detect), and IDENTICAL when "
                                  "the two models are the same predictions.")


def _error_map(rows, receipt):
    sel = rows["selected"]
    errs = rows["selected_errors"]
    if not sel or not errs:
        raise NotSupported("no selected model or no withheld errors")
    model = sel[0]["model_id"]
    lines = sorted({e["line_code"] for e in errs})
    nrows, ncols = 2, 3
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.2, 5.0), sharey=True, layout="constrained")
    axes_flat = list(axes.ravel())
    sc = None
    for ax, line in zip(axes_flat, lines):
        sub = [e for e in errs if e["line_code"] == line]
        sc = ax.scatter([e["easting_m"] for e in sub], [e["z_relative_m"] for e in sub],
                        c=[e["residual"] for e in sub], cmap="RdBu_r", vmin=-1, vmax=1, s=7, linewidths=0)
        wrong = [e for e in sub if e["true_label"] != e["predicted_class"]]
        ax.scatter([e["easting_m"] for e in wrong], [e["z_relative_m"] for e in wrong], s=14, facecolors="none",
                   edgecolors=INK, linewidths=0.35)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
        ax.ticklabel_format(style="plain", useOffset=False, axis="x")
        ax.tick_params(axis="x", labelsize=5.8, pad=2)
        ax.set_title(f"{line.replace('NOM_', '')} (n={len(sub)})", loc="left", fontsize=6.6)
    for k, ax in enumerate(axes_flat):
        if k >= len(lines):
            ax.axis("off")
        if k % ncols == 0:
            ax.set_ylabel("Relative Z (m)")
        if k // ncols == nrows - 1:
            ax.set_xlabel("Easting (m)")
    if len(lines) < nrows * ncols:
        key = axes_flat[len(lines)]
        key.legend(handles=[Line2D([0], [0], marker="o", ls="none", mfc="none", mec=INK, ms=4.5,
                                   label="Misclassified at the frozen threshold")],
                   loc="center", fontsize=6.2, handletextpad=0.3)
    fig.colorbar(sc, ax=axes_flat, label="Residual y - p", shrink=0.9, aspect=30)
    return fig, _caption(receipt, f"Residuals of the selected model ({_label(model)}) on the withheld observations, by drill "
                                  "line. Blue residuals are over-predictions and red residuals under-predictions; black "
                                  "rings mark misclassified intervals at the frozen threshold.")


def _coverage(rows, receipt):
    cov, by_line = rows["coverage"], rows["coverage_by_line"]
    if not cov:
        raise NotSupported("no coverage rows")
    fig, (ax, axh) = plt.subplots(1, 2, figsize=(7.8, 4.5), gridspec_kw={"width_ratios": [1.0, 1.25]})
    fig.subplots_adjust(left=0.1, right=0.86, top=0.84, bottom=0.3, wspace=0.42)
    x = np.arange(len(cov))
    pred = np.array([r["n_predicted"] for r in cov], dtype=float)
    fail = np.array([r["n_failed"] for r in cov], dtype=float)
    ax.bar(x, pred, width=0.62, color=[_color(r["model_id"]) for r in cov], linewidth=0)
    ax.bar(x, fail, bottom=pred, width=0.62, color=LIGHT, hatch="////", edgecolor="white", linewidth=0.3)
    top = max(r["n_expected"] for r in cov)
    for k, r in enumerate(cov):
        ax.text(k, r["n_expected"] + top * 0.012, f"{r['coverage']:.2f}", ha="center", va="bottom", fontsize=5.0, color=INK)
    ax.set_xticks(x, [_short(r["model_id"]) for r in cov], rotation=40, ha="right", fontsize=5.2)
    ax.set_ylim(0, top * 1.1)
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
            axh.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=5.0,
                     color="white" if grid[i, j] < 0.6 else INK)
    axh.set_xticks(range(len(lines)), [ln.replace("NOM_", "") for ln in lines], rotation=30, ha="right", fontsize=5.4)
    axh.set_yticks(range(len(models)), [_short(m) for m in models], fontsize=5.4)
    axh.set_title("Coverage by model and drill line", loc="left", fontsize=7.5)
    cax = fig.add_axes([0.885, 0.3, 0.012, 0.55])
    fig.colorbar(im, cax=cax, label="Coverage")
    return fig, _caption(receipt, "Prediction coverage and abstention per model and drill line. Coloured bars are "
                                  "predictions and hatched bars are explicit failures; a missing prediction is a coverage "
                                  "result and is never dropped silently. Coverage below the predeclared threshold makes a "
                                  "model not comparable; failures are retained.")


FIGURES = OrderedDict([
    ("O4-F01", ("Spatial holdout fold map and coverage", "O4_F01_holdout_coverage", _fold_map, "O4-F01.sql")),
    ("O4-F02", ("Brier score by model and held-out line", "O4_F02_brier", _brier, "O4-F02.sql")),
    ("O4-F03", ("ROC and PR curves", "O4_F03_curves", _curves, "O4-F03.sql")),
    ("O4-F04", ("Reliability diagrams", "O4_F04_reliability", _reliability, "O4-F04.sql")),
    ("O4-F05", ("Paired Brier differences with hole-cluster intervals and power labels", "O4_F05_paired", _paired,
                "O4-F05.sql")),
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


def _receipt_context(conn, receipt):
    config, _ = load_config(O4_CONFIG_PATH)
    counts = conn.execute("SELECT COUNT(*) AS n, COUNT(DISTINCT hole_id) AS holes, COUNT(DISTINCT line_code) AS lines "
                          "FROM evaluation_population WHERE in_common_cohort = 1").fetchone()
    return {**dict(receipt), "claim": config["claim"].strip(), "fold_unit": config["evaluation"]["fold_unit"],
            "n_common": counts["n"], "n_holes": counts["holes"], "n_lines": counts["lines"]}


def render_all(o4_path=None, figure_ids=None):
    conn = connect_o4(o4_path or O4_DB_PATH)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise StopError("no receipt: run the import first")
        receipt = _receipt_context(conn, receipt)
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

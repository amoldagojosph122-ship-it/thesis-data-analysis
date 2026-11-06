"""Objective 3 figure renderers (specification 06, section 4).

Every figure is drawn only from the rows of its registered SQL file in sql/objective_3/figures/, run against the latest
receipt and the primary split plan. A figure whose required rows are missing is registered NOT_SUPPORTED with the reason
and is not drawn. Probabilities are out-of-fold; no test-fold observation was used to fit or select its model.

Colour: blue (negative class), vermillion (positive class), bluish green, orange and purple for the five spatial folds.
Identity is also carried by marker shape and direct text labels. Probability panels use the perceptually uniform
cividis colormap.
"""

from __future__ import annotations

import json
import textwrap
from collections import OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import matplotlib.ticker  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from kambale.objective_3.config import (O3_DB_PATH, O3_FIGURE_DIR, O3_SQL_DIR, PROJECT_ROOT, StopError, sha256_bytes,
                                        utc_now)  # noqa: E402
from kambale.objective_3.db import connect_o3  # noqa: E402

BLUE = "#0072B2"
GREEN = "#009E73"
VERMILLION = "#D55E00"
ORANGE = "#E69F00"
PURPLE = "#CC79A7"
INK = "#222222"
MUTED = "#555555"
NEUTRAL = "#6E6E6E"
LIGHT = "#C9C9C9"
FOLD_COLORS = [BLUE, GREEN, VERMILLION, ORANGE, PURPLE]
FOLD_MARKERS = ["o", "s", "^", "D", "v"]
STATE_COLOR = {0: BLUE, 1: VERMILLION}

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.grid": False,
    "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 300, "pdf.compression": 6,
})


class NotSupported(Exception):
    """A required input is missing. The figure is registered NOT_SUPPORTED with this reason and is not drawn."""


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


def _caption(receipt: dict, body: str) -> str:
    return (f"{body} Support: 1 m logged intervals. Outer folds are leave-one-drill-line-out; every probability is "
            f"out-of-fold. Geometry {receipt['geometry_status']}: straight holes, collar elevation absent, depth relative "
            "to collar; absolute elevation is not used.")


def _line_labels(fold_lines: list[dict]) -> dict[int, str]:
    return {r["fold_id"]: r["line_code"].replace("NOM_", "") for r in fold_lines}


def _fold_plan(rows: dict, receipt: dict):
    collars, audit, fold_lines = rows["collar_folds"], rows["fold_audit"], rows["fold_lines"]
    if not collars:
        raise NotSupported("no collar rows for the primary split plan")
    labels = _line_labels(fold_lines)
    fig = plt.figure(figsize=(7.6, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1.0], left=0.1, right=0.98, top=0.86, bottom=0.24, wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])
    for k, (fold, color, marker) in enumerate(zip(sorted({c["fold_id"] for c in collars}), FOLD_COLORS, FOLD_MARKERS)):
        sub = [c for c in collars if c["fold_id"] == fold]
        ax.scatter([c["easting_m"] for c in sub], [c["northing_m"] for c in sub], s=22, marker=marker, color=color,
                   linewidths=0.5, edgecolors="white", zorder=3,
                   label=f"Fold {fold}: hold out {labels.get(fold, '?')} (n={len(sub)})")
        if sub:
            west = min(sub, key=lambda c: c["easting_m"])
            ax.annotate(f"F{fold}", (west["easting_m"], west["northing_m"]), xytext=(-10, 0),
                        textcoords="offset points", ha="right", va="center", fontsize=6.4, color=color)
    ax.set_xlabel("UTM 30N easting (m)")
    ax.set_ylabel("UTM 30N northing (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.set_title("Outer spatial folds: one drill line held out at a time", loc="left", fontsize=7.5)
    ax.legend(loc="upper left", markerscale=1.3, handletextpad=0.4, borderaxespad=0.2)
    ax2 = fig.add_subplot(gs[0, 1])
    folds = sorted(audit, key=lambda a: a["fold_id"])
    x = np.arange(len(folds))
    pos = np.array([a["test_positive"] for a in folds], dtype=float)
    neg = np.array([a["n_test"] - a["test_positive"] for a in folds], dtype=float)
    ax2.bar(x, pos, width=0.62, color=VERMILLION, linewidth=0, label="Positive")
    ax2.bar(x, neg, bottom=pos, width=0.62, color=BLUE, linewidth=0, label="Negative")
    for k, a in enumerate(folds):
        ax2.text(k, a["n_test"] + 10, f"{a['n_test']}\ntrain p=\n{a['train_positive'] / a['n_train']:.2f}", ha="center",
                 va="bottom", fontsize=5.6, color=INK, linespacing=1.1)
    ax2.set_xticks(x, [f"F{a['fold_id']}" for a in folds], fontsize=6.5)
    ax2.set_ylim(0, 1.42 * max(a["n_test"] for a in folds))
    ax2.set_ylabel("Held-out binary intervals")
    ax2.set_title("Class support of each held-out line", loc="left", fontsize=7.5)
    ax2.legend(loc="upper right", ncol=2, handletextpad=0.3)
    return fig, _caption(receipt, "Outer split plan: each approved drill line is held out once. Left: collars by fold. "
                                  "Right: held-out class counts; the training prevalence is printed below each fold. "
                                  "Inner tuning uses whole-hole folds inside the remaining lines.")


def _feature_support(rows: dict, receipt: dict):
    points, features = rows["observation_points"], rows["feature_availability"]
    if not points:
        raise NotSupported("no binary observations in the receipt")
    safe = [f for f in features if f["available_at_prediction"] == 1]
    logged = [f for f in features if f["leakage_designation"] == "LOG_ONLY"]
    target = [f for f in features if f["leakage_designation"] in ("TARGET_DERIVED", "FORBIDDEN")]
    ident = [f for f in features if f["leakage_designation"] == "IDENTIFIER"]
    fig, (ax, axz) = plt.subplots(1, 2, figsize=(7.6, 4.4), gridspec_kw={"width_ratios": [1.25, 1.0]})
    fig.subplots_adjust(left=0.1, right=0.98, top=0.84, bottom=0.19, wspace=0.28)
    for value, label in ((0, "Negative (indicator 0)"), (1, "Positive (indicator 1)")):
        sub = [p for p in points if p["indicator"] == value]
        ax.scatter([p["easting_m"] for p in sub], [p["northing_m"] for p in sub], s=6 if value == 1 else 4,
                   color=STATE_COLOR[value], linewidths=0, alpha=0.9 if value == 1 else 0.5,
                   label=f"{label}, n={len(sub)}")
    ax.set_xlabel("UTM 30N easting (m)")
    ax.set_ylabel("UTM 30N northing (m)")
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.set_title("Observation support by class", loc="left", fontsize=7.5)
    ax.legend(loc="upper left", markerscale=2.4, handletextpad=0.4)
    z = np.array([p["z_relative_m"] for p in points], dtype=float)
    y = np.array([p["indicator"] for p in points], dtype=int)
    bins = np.linspace(float(z.min()), 0.0, 22)
    axz.hist(z[y == 0], bins=bins, color=BLUE, alpha=0.75, label="Negative", linewidth=0)
    axz.hist(z[y == 1], bins=bins, color=VERMILLION, alpha=0.80, label="Positive", linewidth=0)
    axz.invert_yaxis()
    axz.set_xlabel("Vertical position, metres relative to collar")
    axz.set_ylabel("Binary intervals")
    axz.set_title("Depth support by class", loc="left", fontsize=7.5)
    axz.legend(loc="lower left")
    fig.text(0.98, 0.955, "Deployed predictors: " + ", ".join(f["name"] for f in safe), ha="right", va="bottom",
             fontsize=6.4, color=INK)
    fig.text(0.98, 0.925, f"Not predictors: {len(target)} target-derived, {len(logged)} log-only, {len(ident)} identifier "
                          "fields", ha="right", va="bottom", fontsize=6.4, color=MUTED)
    return fig, _caption(receipt, "Observation support and the deployed predictor set. Only easting, northing and "
                                  "relative-Z exist at every held-out interval. Weathering and lithology are logged only where "
                                  "a hole exists, and rock type, mineral evidence and comments define the approved label. "
                                  "Those attributes are not predictors.")


def _section_scatter(ax, sub, title, vmin=0.0, vmax=1.0):
    if not sub:
        ax.text(0.5, 0.5, "no predictions", transform=ax.transAxes, ha="center", va="center", color=MUTED)
        ax.set_title(title, loc="left", fontsize=7)
        return None
    sc = ax.scatter([p["easting_m"] for p in sub], [p["z_relative_m"] for p in sub],
                    c=[p["p_calibrated"] for p in sub], cmap="cividis", vmin=vmin, vmax=vmax, s=11, linewidths=0)
    clip = [p for p in sub if p["clipped_calibrated"]]
    if clip:
        ax.scatter([p["easting_m"] for p in clip], [p["z_relative_m"] for p in clip], s=24, facecolors="none",
                   edgecolors=INK, linewidths=0.5)
    ax.ticklabel_format(style="plain", useOffset=False, axis="x")
    ax.set_title(title, loc="left", fontsize=7)
    return sc


def _m1(rows: dict, receipt: dict):
    preds, status = rows["m1_predictions"], rows["m1_status"]
    if not preds:
        reasons = "; ".join(f"F{s['fold_id']}: {s['status']} ({s['reason']})" for s in status) or "no M1 training rows"
        raise NotSupported("M1 indicator kriging produced no out-of-fold prediction: " + reasons)
    folds = sorted({p["fold_id"] for p in preds})
    nrows, ncols = 2, 3
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.2, 4.9), sharey=True, layout="constrained")
    axes_flat = list(axes.ravel())
    sc = None
    for ax, fold in zip(axes_flat, folds):
        sub = [p for p in preds if p["fold_id"] == fold]
        sc = ax.scatter([p["easting_m"] for p in sub], [p["z_relative_m"] for p in sub],
                        c=[p["p_calibrated"] for p in sub], cmap="cividis", vmin=0.0, vmax=1.0, s=12, linewidths=0)
        clip = [p for p in sub if p["clipped_calibrated"]]
        if clip:
            ax.scatter([p["easting_m"] for p in clip], [p["z_relative_m"] for p in clip], s=26, facecolors="none",
                       edgecolors=INK, linewidths=0.5)
        ax.set_title(f"Fold {fold}", loc="left", fontsize=7)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
        ax.ticklabel_format(style="plain", useOffset=False, axis="x")
    for k, ax in enumerate(axes_flat):
        if k >= len(folds):
            ax.axis("off")
        if k % ncols == 0:
            ax.set_ylabel("Relative Z (m)")
        if k // ncols == nrows - 1:
            ax.set_xlabel("Easting (m)")
    if len(folds) < nrows * ncols:
        key = axes_flat[len(folds)]
        key.legend(handles=[Line2D([0], [0], marker="o", ls="none", mfc="none", mec=INK, ms=4.5,
                                   label="Clipped to [0,1]")], loc="center", fontsize=6.5)
    if sc is not None:
        fig.colorbar(sc, ax=axes_flat, label="P(I=1) out-of-fold", shrink=0.9, aspect=30)
    return fig, _caption(receipt, "M1 simple indicator kriging out-of-fold probabilities at held-out intervals. "
                                  "The covariance is chosen by whole-hole inner cross-validation inside each outer training "
                                  "fold; a pure-nugget choice gives the training prevalence. Clipped values are counted in O3-T03. "
                                  "Simple indicator kriging; covariance chosen by inner CV in each fold; clipped values marked.")


def _m2_sections(rows: dict, receipt: dict):
    preds, fold_lines = rows["m2_predictions"], rows["fold_lines"]
    if not preds:
        raise NotSupported("no M2 out-of-fold predictions")
    labels = _line_labels(fold_lines)
    folds = sorted({p["fold_id"] for p in preds})
    models = [("M2_RF", "Random forest"), ("M2_HGB", "Gradient boosting")]
    fig, axes = plt.subplots(len(folds), 2, figsize=(7.2, 1.42 * len(folds) + 0.9), sharey="row", layout="constrained")
    axes = np.atleast_2d(axes)
    sc = None
    for r, fold in enumerate(folds):
        for c, (family, name) in enumerate(models):
            sub = [p for p in preds if p["fold_id"] == fold and p["family_id"] == family]
            ax = axes[r, c]
            sc = _section_scatter(ax, sub, f"Fold {fold} · held out {labels.get(fold, '?')} · {name}")
            ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
            if c == 0:
                ax.set_ylabel("Relative Z (m)")
            if r == len(folds) - 1:
                ax.set_xlabel("Easting (m)")
    if sc is not None:
        fig.colorbar(sc, ax=list(axes.ravel()), label="P(I=1) out-of-fold, calibrated", shrink=0.85, aspect=40)
    selected = {s["fold_id"]: s["candidate_run_id"] for s in rows["selected_m2"]}
    note = "; ".join(f"F{f}: {selected.get(f, 'none')}" for f in folds)
    fig.suptitle(textwrap.fill("Selected M2 trend by fold: " + note + "; probabilities are calibrated on inner out-of-fold "
                               "predictions; no outer test label enters", 150), x=0.01, ha="left", fontsize=6.4, color=INK)
    return fig, _caption(receipt, "M2 out-of-fold probability sections for every held-out line, random forest and gradient "
                                  "boosting. Each panel uses only the intervals of the line held out in that fold; the "
                                  "selected M2 trend is printed above the panels. No model ranking is made here.")


def _m3_sections(rows: dict, receipt: dict):
    m3 = rows["m3_predictions"]
    if not m3:
        raise NotSupported("no M3 out-of-fold predictions")
    fold = max(sorted({p["fold_id"] for p in m3}), key=lambda f: sum(1 for p in m3 if p["fold_id"] == f))
    status = next((s for s in rows["m3_status"] if s["fold_id"] == fold), None)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.4), sharey=True, layout="constrained")
    axes_flat = list(axes.ravel())
    sc = None
    m3_label = "M3 hybrid (fallback)" if status and status["status"] == "FALLBACK" else "M3 hybrid"
    panels = [("M2_RF", "Random forest"), ("M2_HGB", "Gradient boosting"), ("M3_HYBRID", m3_label)]
    for ax, (family, name) in zip(axes_flat, panels):
        if family == "M3_HYBRID":
            sub = [p for p in m3 if p["fold_id"] == fold]
        else:
            sub = [p for p in rows["m2_predictions"] if p["fold_id"] == fold and p["family_id"] == family]
        sc = _section_scatter(ax, sub, name)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
    axes[0, 0].set_ylabel("Relative Z (m)")
    axes[1, 0].set_ylabel("Relative Z (m)")
    for ax in axes[1]:
        ax.set_xlabel("Easting (m)")
    fb = status["status"] if status else "UNKNOWN"
    note = (f"Fold {fold}. M3 status: {fb}. " +
            ("Residual covariance was not identified or stable, so M3 is the selected ML-only fallback; the M3 panel "
             "therefore duplicates the selected M2 trend and is not a hybrid success." if fb == "FALLBACK" else
             "A training-only residual variogram was identified and stable; the M3 panel adds the kriged residual."))
    key = axes_flat[3]
    key.axis("off")
    key.text(0.0, 1.0, textwrap.fill(note, 46), transform=key.transAxes, ha="left", va="top", fontsize=6.4, color=INK)
    if sc is not None:
        fig.colorbar(sc, ax=axes_flat, label="P(I=1) out-of-fold", shrink=0.85, aspect=35)
    return fig, _caption(receipt, "M3 out-of-fold probability section for the fold with the most held-out intervals, "
                                  "aligned with the two M2 candidates. The hybrid label is used only when the residual "
                                  "variogram is supported; otherwise the panel is the explicit ML-only fallback. "
                                  "The M3 residual variogram is fitted on inner cross-fitted residuals of the training fold only.")


def _covariance_trials(rows: dict, receipt: dict):
    trials = rows["covariance_trials"]
    if not trials:
        raise NotSupported("no covariance trials were stored for M1 or M3")
    fams = [("M1_IK", "M1 indicator kriging"), ("M3_HYBRID", "M3 residual kriging")]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 4.2))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.36, wspace=0.28)
    cmap = plt.get_cmap("cividis")
    # Nugget fractions use a single sequential ramp so they cannot be confused with the fold hues of the PURE_NUGGET lines.
    nugget_colors = {0.25: cmap(0.12), 0.5: cmap(0.5), 0.75: cmap(0.88)}
    for ax, (fam, name) in zip(axes, fams):
        sub = [t for t in trials if t["family_id"] == fam]
        for t in sub:
            cov = json.loads(t["hyperparameters_json"])
            fold = int(t["fold_id"])
            marker = FOLD_MARKERS[(fold - 1) % len(FOLD_MARKERS)]
            if cov.get("covariance") == "PURE_NUGGET":
                ax.axhline(t["inner_cv_score"], color=FOLD_COLORS[(fold - 1) % len(FOLD_COLORS)], ls="--", lw=0.7)
                continue
            ax.scatter(cov["range_m"], t["inner_cv_score"], s=34 if t["selected"] else 14, marker=marker,
                       color=nugget_colors.get(float(cov["nugget_fraction"]), NEUTRAL),
                       edgecolors=INK if t["selected"] else "none", linewidths=0.8, zorder=3)
        ax.set_xscale("log")
        ax.set_xticks([25, 50, 100, 200, 400])   # the predeclared range grid, so every column of points has a label
        ax.set_xticklabels(["25", "50", "100", "200", "400"])
        ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        ax.set_xlabel("Practical range (m, log scale)")
        ax.set_title(name, loc="left", fontsize=7.2)
    axes[0].set_ylabel("Inner-CV mean log loss")
    handles = [Line2D([0], [0], marker="o", ls="none", color=c, label=f"nugget fraction {k:g}")
               for k, c in nugget_colors.items()]
    handles += [Line2D([0], [0], ls="--", color=FOLD_COLORS[k], marker=FOLD_MARKERS[k % len(FOLD_MARKERS)],
                       markerfacecolor=NEUTRAL, markeredgecolor="none", label=f"fold {k + 1}: marker; PURE_NUGGET line")
                for k in range(len(FOLD_COLORS))]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.085), fontsize=5.6, ncol=4)
    return fig, _caption(receipt, "Covariance selection for M1 and M3 by whole-hole inner cross-validation, one marker per "
                                  "grid point and outer fold. Dashed lines are the pure-nugget score of each fold; a "
                                  "pure-nugget choice means no spatial covariance was supported.")


FIGURES = OrderedDict([
    ("O3-F01", ("Outer-fold spatial map and class support", "O3_F01_outer_folds", _fold_plan, "O3-F01.sql")),
    ("O3-F02", ("Predictor availability and observation support", "O3_F02_predictor_support", _feature_support,
                "O3-F02.sql")),
    ("O3-F03", ("M1 indicator-kriging out-of-fold probabilities", "O3_F03_m1_probabilities", _m1, "O3-F03.sql")),
    ("O3-F04", ("M2 out-of-fold probability sections", "O3_F04_m2_sections", _m2_sections, "O3-F04.sql")),
    ("O3-F05", ("M3 hybrid or fallback probability section", "O3_F05_m3_sections", _m3_sections, "O3-F05.sql")),
    ("O3-F06", ("Inner-CV covariance selection for M1 and M3", "O3_F06_covariance_selection", _covariance_trials,
                "O3-F06.sql")),
])


def _save(fig, figure_id: str, stem: str) -> list[Path]:
    O3_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["svg.hashsalt"] = figure_id
    paths = []
    for ext, kwargs in (("svg", {"metadata": {"Date": None}}),
                        ("pdf", {"metadata": {"CreationDate": None, "ModDate": None}}),
                        ("png", {"dpi": 300, "metadata": {"Software": None}})):
        path = O3_FIGURE_DIR / f"{stem}.{ext}"
        fig.savefig(path, **kwargs)
        paths.append(path)
    return paths


def render_all(o3_path=O3_DB_PATH, figure_ids: list[str] | None = None, split_plan_id: str | None = None) -> dict:
    conn = connect_o3(o3_path)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise StopError("no receipt: run the import first")
        receipt = dict(receipt)
        rid = receipt["receipt_id"]
        plan = split_plan_id or conn.execute("SELECT split_plan_id FROM spatial_split_plans WHERE primary_plan = 1").fetchone()[0]
        created = utc_now()
        summary = {}
        for fid, (title, stem, renderer, sql_file) in FIGURES.items():
            if figure_ids and fid not in figure_ids:
                continue
            sql_path = O3_SQL_DIR / "figures" / sql_file
            queries = load_queries(sql_path)
            rows = {name: [dict(r) for r in conn.execute(text, {"receipt_id": rid, "split_plan_id": plan}).fetchall()]
                    for name, text in queries.items()}
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
                             (fid, name, _rel(sql_path), sha256_bytes(sql_path.read_bytes()),
                              '{"receipt_id": %d, "split_plan_id": "%s"}' % (rid, plan), len(rows[name])))
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

"""Objective 2 figure renderers (specification 06, section 4).

Each figure is drawn only from the rows of its registered SQL file in sql/objective_2/figures/, run against the latest
receipt. A figure whose required rows are missing is registered NOT_SUPPORTED with its reason and is not drawn (gate G29).

Colour: the Okabe-Ito subset blue, bluish green and vermillion, checked with scripts/validate_palette.js (blue beside
bluish green: CVD delta E 18.0; the three together: minimum delta E 11.0; no warning). Vermillion always means POSITIVE;
blue is the negative class or the primary series; bluish green is the secondary series. Identity is also carried by
direct labels, marker shape and hatching, never colour alone.

Layout uses explicit margins, so labels are never clipped or resized by the layout engine. Outputs are SVG, PDF and PNG.
The SVG hash salt is the figure identifier and creation dates are removed from the metadata, so a repeated render of the
same rows is byte-identical.
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
from matplotlib.patches import Patch, Rectangle  # noqa: E402

from kambale.objective_2.config import O2_DB_PATH, O2_FIGURE_DIR, O2_SQL_DIR, PROJECT_ROOT, StopError, sha256_bytes, utc_now  # noqa: E402
from kambale.objective_2.db import connect_o2  # noqa: E402
from kambale.objective_2.fitting import gamma_model  # noqa: E402

BLUE = "#0072B2"
GREEN = "#009E73"
VERMILLION = "#D55E00"
INK = "#222222"
MUTED = "#555555"
NEUTRAL = "#6E6E6E"
NEUTRAL_LIGHT = "#C9C9C9"
POINT_GREY = "#4D4D4D"
SECTION_NORTHING_RANGE_MAX_M = 25.0
WEATHERING_ORDER = {"cw": 0, "hw": 1, "mw": 2, "sw": 3, "fr": 4, "MISSING": 9}
STATE_ORDER = ("POSITIVE", "NEGATIVE", "AMBIGUOUS", "UNRESOLVED")
STATE_LABEL = {"POSITIVE": "Positive (indicator 1)", "NEGATIVE": "Negative (indicator 0)",
               "AMBIGUOUS": "Ambiguous (excluded)", "UNRESOLVED": "Unresolved (excluded)"}

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.grid": False,
    "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 300, "pdf.compression": 6,
})


class NotSupported(Exception):
    """A required input is missing. The figure is registered NOT_SUPPORTED with this reason and is not drawn."""


def load_queries(path: Path) -> OrderedDict:
    """Named queries of one SQL file. Each query starts at a line '-- name: <query_name>'."""
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


def _section_rows(receipt_id: int, geometry: list[dict]) -> list[dict]:
    """One relative-depth section per drill line. A line is drawn only when its collars lie within the projection limit."""
    rows = []
    for g in geometry:
        spread = g["n_max"] - g["n_min"]
        ok = spread <= SECTION_NORTHING_RANGE_MAX_M
        rows.append({
            "section_id": f"O2-S-{g['line_code']}", "receipt_id": receipt_id, "line_code": g["line_code"],
            "section_azimuth_deg": 90.0,
            "projection_basis": (f"collars of {g['n_holes']} holes projected onto the east-west plane of the line; "
                                 f"northing range {spread:.1f} m; holes drawn as strips in depth below collar"),
            "vertical_basis": "RELATIVE_DEPTH", "observed_or_inferred": "OBSERVED_LOG_ONLY",
            "status": "GENERATED" if ok else "NOT_SUPPORTED",
            "reason": ("northing range within the %.0f m projection limit" % SECTION_NORTHING_RANGE_MAX_M) if ok else
                      f"northing range {spread:.1f} m exceeds the {SECTION_NORTHING_RANGE_MAX_M:.0f} m projection limit",
        })
    return rows


def _footer(fig, receipt: dict, extra: str) -> None:
    base = (f"upstream {receipt['upstream_dataset_version_key'][:12]} | receipt {receipt['receipt_id']} | "
            f"{receipt['label_rule_id']} {receipt['label_rule_status']} | coordinates {receipt['coordinate_pair_status']} "
            f"(UTM 30N, datum {receipt['crs_datum_status'].lower()}) | vertical = metres relative to collar (no collar RL)")
    fig.text(0.01, 0.012, textwrap.fill(f"{base} | {extra}", 170), fontsize=5.0, color=MUTED, ha="left", va="bottom")


def _caption(receipt: dict, body: str) -> str:
    return (f"{body} Support: 1 m logged intervals. Geometry {receipt['geometry_status']}: straight holes, collar elevation "
            "absent, depth relative to collar; absolute elevation is not used. No cross-validation folds exist in this stage.")


def _pq(rows: dict) -> float:
    return float(rows["marginal_variance"][0]["p_one_minus_p"])


def _plan(rows: dict, receipt: dict):
    collars, positives = rows["collars"], rows["positive_midpoints"]
    if not collars:
        raise NotSupported("no collar locations in the receipt")
    fig, ax = plt.subplots(figsize=(7.0, 5.2))
    fig.subplots_adjust(left=0.1, right=0.98, bottom=0.11, top=0.98)
    ax.scatter([c["easting_m"] for c in collars], [c["northing_m"] for c in collars], s=12, color=POINT_GREY,
               linewidths=0, zorder=3, label=f"Collar ({len(collars)} holes)")
    if positives:
        ax.scatter([p["easting_m"] for p in positives], [p["northing_m"] for p in positives], s=7, color=VERMILLION,
                   linewidths=0, alpha=0.9, zorder=4, label=f"Midpoint of POSITIVE interval (n = {len(positives)})")
    for line in sorted({c["line_code"] for c in collars}):
        west = min((c for c in collars if c["line_code"] == line), key=lambda c: c["easting_m"])
        ax.annotate(line, (west["easting_m"], west["northing_m"]), xytext=(0, 5), textcoords="offset points",
                    ha="left", va="bottom", fontsize=6, color=INK)
    ax.set_aspect("equal", adjustable="datalim")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.set_xlabel("UTM 30N easting (m)")
    ax.set_ylabel("UTM 30N northing (m)")
    ax.legend(loc="upper left", markerscale=1.6, handletextpad=0.4)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    bar_x, bar_y = x1 - 0.04 * (x1 - x0) - 200.0, y0 + 0.05 * (y1 - y0)
    ax.plot([bar_x, bar_x + 200.0], [bar_y, bar_y], color=INK, lw=1.4, solid_capstyle="butt")
    ax.text(bar_x + 100.0, bar_y + 0.012 * (y1 - y0), "200 m", ha="center", va="bottom", fontsize=6.5)
    _footer(fig, receipt, "plan view; positions are UTM 30N metres")
    return fig, _caption(receipt, f"Plan view of {len(collars)} collars grouped by drill line (labels at the western collar "
                                  f"of each line) with the midpoints of {len(positives)} POSITIVE intervals.")


def _occurrence(rows: dict, receipt: dict):
    holes, lines = rows["holes"], rows["lines"]
    if not holes:
        raise NotSupported("no hole summaries in the receipt")
    fig = plt.figure(figsize=(7.4, 8.2))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.0, 0.9], left=0.12, right=0.985, top=0.94, bottom=0.085, wspace=0.5)
    ax_f = fig.add_subplot(gs[0, 0])
    ax_m = fig.add_subplot(gs[0, 1], sharey=ax_f)
    sub = gs[0, 2].subgridspec(2, 1, hspace=0.45)
    ax_lf = fig.add_subplot(sub[0])
    ax_lm = fig.add_subplot(sub[1])
    y = np.arange(len(holes))
    ax_f.barh(y, [h["fraction"] or 0.0 for h in holes], height=0.72, color=VERMILLION, linewidth=0)
    ax_f.set_yticks(y, [f"{h['hole_id']}  n={h['binary_n']}" for h in holes], fontsize=4.4)
    ax_f.invert_yaxis()
    ax_f.set_xlim(0, 1)
    ax_f.set_xlabel("Positive share of binary intervals")
    ax_f.set_title("By hole: fraction", loc="left", fontsize=7)
    ax_m.barh(y, [h["positive_apparent_m"] for h in holes], height=0.72, color=VERMILLION, linewidth=0)
    ax_m.tick_params(axis="y", labelleft=False)
    ax_m.set_xlabel("Positive apparent thickness (m)")
    ax_m.set_title("By hole: positive metres", loc="left", fontsize=7)
    yl = np.arange(len(lines))
    names = [ln["line_code"].replace("NOM_", "") for ln in lines]
    ax_lf.barh(yl, [ln["fraction"] or 0.0 for ln in lines], height=0.6, color=VERMILLION, linewidth=0)
    for k, ln in enumerate(lines):
        ax_lf.text((ln["fraction"] or 0.0) + 0.02, k, f"n={ln['binary_n']}", va="center", fontsize=5.0, color=INK)
    ax_lf.set_yticks(yl, names, fontsize=5.2)
    ax_lf.invert_yaxis()
    ax_lf.set_xlim(0, 1.2)
    ax_lf.set_xticks([0.0, 0.5, 1.0])
    ax_lf.set_title("By line: fraction", loc="left", fontsize=7)
    xmax = max(ln["positive_apparent_m"] for ln in lines)
    ax_lm.barh(yl, [ln["positive_apparent_m"] for ln in lines], height=0.6, color=VERMILLION, linewidth=0)
    for k, ln in enumerate(lines):
        ax_lm.text(ln["positive_apparent_m"] + 0.03 * xmax, k, f"{ln['positive_n']} intervals", va="center", fontsize=5.0,
                   color=INK)
    ax_lm.set_yticks(yl, names, fontsize=5.2)
    ax_lm.invert_yaxis()
    ax_lm.set_xlim(0, 1.5 * xmax)
    ax_lm.set_xlabel("Positive thickness (m)")
    ax_lm.set_title("By line: positive metres", loc="left", fontsize=7)
    _footer(fig, receipt, "denominators are binary intervals; AMBIGUOUS and UNRESOLVED intervals are excluded")
    n_pos = sum(h["positive_n"] for h in holes)
    return fig, _caption(receipt, f"Positive share (fraction) and positive apparent thickness (m) for {len(holes)} holes and "
                                  f"{len(lines)} lines; {n_pos} positive intervals. Each denominator is the number of binary "
                                  "intervals of that hole or line. Line labels are the nominal northing groups without their "
                                  "NOM_ prefix.")


def _depth_weathering(rows: dict, receipt: dict):
    bins, weathering = rows["depth_bins"], rows["weathering"]
    if not bins:
        raise NotSupported("no depth bins in depth_lithology_summaries")
    if not weathering:
        raise NotSupported("no weathering class in weathering_cross_tabs")
    fig, (ax_d, ax_w) = plt.subplots(1, 2, figsize=(7.4, 3.8), gridspec_kw={"width_ratios": [1.0, 1.15]})
    fig.subplots_adjust(left=0.09, right=0.985, top=0.80, bottom=0.19, wspace=0.28)
    width_bin = bins[0]["depth_bin_to_m"] - bins[0]["depth_bin_from_m"]
    centres = [(b["depth_bin_from_m"] + b["depth_bin_to_m"]) / 2 for b in bins]
    shares = [b["positive_n"] / b["binary_n"] if b["binary_n"] else 0.0 for b in bins]
    ax_d.bar(centres, shares, width=0.8 * width_bin, color=VERMILLION, linewidth=0)
    for c, s, b in zip(centres, shares, bins):
        ax_d.text(c, s + 0.015, f"{b['binary_n']}", ha="center", va="bottom", fontsize=4.8, color=INK, rotation=90)
    ax_d.set_ylim(0, 1.12)
    ax_d.set_xlabel("Depth from collar (m), 10 m bins")
    ax_d.set_ylabel("Positive share of binary intervals")
    ax_d.set_title("By depth, all rock codes pooled (label: n)", loc="left", fontsize=7)
    codes = sorted({w["weathering_code"] for w in weathering}, key=lambda c: (WEATHERING_ORDER.get(c, 8), c))
    present = [s for s in STATE_ORDER if any(w["label_state"] == s and w["n_intervals"] for w in weathering)]
    style = {"POSITIVE": {"color": VERMILLION}, "NEGATIVE": {"color": BLUE},
             "AMBIGUOUS": {"color": NEUTRAL_LIGHT, "hatch": "////"}, "UNRESOLVED": {"color": NEUTRAL, "hatch": "...."}}
    bottom = np.zeros(len(codes))
    for state in present:
        counts = np.array([next((w["n_intervals"] for w in weathering if w["weathering_code"] == c and
                                 w["label_state"] == state), 0) for c in codes], dtype=float)
        ax_w.bar(range(len(codes)), counts, bottom=bottom, width=0.7, linewidth=0.5, edgecolor="white", **style[state])
        bottom += counts
    ax_w.set_xticks(range(len(codes)), [c if c != "MISSING" else "blank" for c in codes])
    ax_w.set_xlabel("Weathering code as logged")
    ax_w.set_ylabel("Intervals")
    ax_w.set_title("By weathering class: intervals by label state", loc="left", fontsize=7)
    handles = [Patch(facecolor=style[s]["color"], edgecolor="white", hatch=style[s].get("hatch"), label=STATE_LABEL[s])
               for s in present]
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), bbox_to_anchor=(0.5, 0.99))
    _footer(fig, receipt, "depth bins pool all rock codes; blank weathering is shown as blank")
    return fig, _caption(receipt, "Left: positive share of binary intervals by 10 m depth bin (variable: depth from collar; "
                                  "all rock codes pooled). Right: intervals by logged weathering code and label state "
                                  "(variables: weathering code; label state).")


def _strip_style(state: str) -> dict:
    if state == "POSITIVE":
        return {"facecolor": VERMILLION, "edgecolor": "white", "linewidth": 0.3}
    if state == "NEGATIVE":
        return {"facecolor": BLUE, "edgecolor": "white", "linewidth": 0.3}
    return {"facecolor": "white", "edgecolor": NEUTRAL, "linewidth": 0.4, "hatch": "////"}


def _strips(rows: dict, receipt: dict):
    intervals = rows["intervals"]
    if not intervals:
        raise NotSupported("no hole on a line has observations")
    sections = {s["line_code"]: s for s in _section_rows(receipt["receipt_id"], rows["section_geometry"])}
    lines = [g["line_code"] for g in rows["section_geometry"] if sections[g["line_code"]]["status"] == "GENERATED"]
    if not lines:
        raise NotSupported("no line passes the section projection limit")
    holes_by_line: dict[str, list[str]] = {}
    for r in rows["representative_holes"]:
        holes_by_line.setdefault(r["line_code"], []).append(r["hole_id"])
    by_hole: dict[tuple[str, str], list[dict]] = {}
    for i in intervals:
        by_hole.setdefault((i["line_code"], i["hole_id"]), []).append(i)
    max_depth = max(i["depth_to_m"] for i in intervals)
    fig, axes = plt.subplots(1, len(lines), figsize=(7.4, 4.9), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.985, top=0.84, bottom=0.21, wspace=0.55)
    axes = np.atleast_1d(axes)
    for ax, line in zip(axes, lines):
        holes = holes_by_line.get(line, [])
        for k, hole in enumerate(holes):
            for i in by_hole.get((line, hole), []):
                ax.add_patch(Rectangle((k - 0.3, i["depth_from_m"]), 0.6, i["depth_to_m"] - i["depth_from_m"],
                                       **_strip_style(i["label_state"])))
        ax.set_xlim(-0.7, max(len(holes) - 1, 0) + 0.7)
        ax.set_ylim(max_depth + 1.0, 0.0)
        ax.set_xticks(range(len(holes)), holes, rotation=90, fontsize=5.5)
        ax.set_title(line, fontsize=6.5)
    axes[0].set_ylabel("Depth below collar (m)")
    handles = [Patch(facecolor=VERMILLION, label="Positive (indicator 1)"),
               Patch(facecolor=BLUE, label="Negative (indicator 0)"),
               Patch(facecolor="white", edgecolor=NEUTRAL, hatch="////", label="Ambiguous or unresolved (excluded)")]
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 0.995))
    _footer(fig, receipt, "strips are logged intervals only; no contact is inferred")
    return fig, _caption(receipt, f"Logged intervals of the two holes per line with the most binary intervals, drawn as strips in "
                                  f"depth below collar (m); lines shown: {', '.join(lines)}. Excluded intervals are hatched.")


def _pair_support(rows: dict, receipt: dict):
    pairs = rows["pair_support"]
    if not pairs:
        raise NotSupported("no pair counts exist in pair_sampling_diagnostics")
    minimum = {m["direction_id"]: m["min_pairs_per_bin"] for m in rows["minimum_pairs"]}
    panels = [("DOWNHOLE_WITHIN", "Within-hole (along-hole lag, m)"),
              ("LATERAL_BETWEEN", "Between-hole, lateral basis (horizontal lag, m)"),
              ("OMNI_3D_BETWEEN", "Between-hole, three-dimensional lag (m)")]
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 3.5), sharey=True)
    fig.subplots_adjust(left=0.08, right=0.985, top=0.79, bottom=0.2, wspace=0.12)
    for ax, (direction, title) in zip(axes, panels):
        rr = [r for r in pairs if r["direction_id"] == direction]
        ax.set_title(title, loc="left", fontsize=7)
        if not rr:
            ax.text(0.5, 0.5, "no pair counts", transform=ax.transAxes, ha="center", color=MUTED)
            continue
        x = [0.5 * (r["lag_from_m"] + r["lag_to_m"]) for r in rr]
        ax.plot(x, [r["n_pairs"] for r in rr], marker="o", ms=2.8, lw=0.9, color=BLUE, label="Pairs")
        ax.plot(x, [r["n_independent_hole_pairs"] for r in rr], marker="s", ms=2.4, lw=0.9, color=GREEN,
                label="Independent hole pairs")
        if direction in minimum:
            ax.axhline(minimum[direction], ls="--", lw=0.8, color=NEUTRAL, label="Minimum pairs per bin")
        ax.set_yscale("log")
        ax.set_xlabel("Lag (m)")
    axes[0].set_ylabel("Count per lag bin (log scale)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 0.995))
    _footer(fig, receipt, "for within-hole bins the independent count is the number of distinct holes contributing")
    return fig, _caption(receipt, "Number of pairs and of independent hole pairs per lag bin for the base experiments "
                                  "(counts only; no semivariance). Within-hole pairs are shown separately from between-hole pairs.")


def _variogram(rows: dict, receipt: dict):
    bins = rows["experimental_bins"]
    if not any(b["supported"] for b in bins):
        raise NotSupported("no supported bins for the between-hole base experiments")
    pq = _pq(rows)
    xmax = max(b["lag_centre_m"] for b in bins)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    fig.subplots_adjust(left=0.11, right=0.74, top=0.97, bottom=0.14)
    series = [("LATERAL_BETWEEN", "Lateral between-hole (handoff basis)", "lateral (handoff basis)", BLUE, "o"),
              ("OMNI_3D_BETWEEN", "Three-dimensional between-hole (reported)", "3-D (reported)", GREEN, "s")]
    end, gammas = {}, [pq]
    for direction, legend_label, direct_label, color, marker in series:
        pts = sorted((b["lag_centre_m"], b["gamma"]) for b in bins if b["direction_id"] == direction and b["supported"])
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=marker, ms=3.6, lw=0.6, color=color, label=legend_label)
            end[direct_label] = (pts[-1][0], pts[-1][1])
            gammas += [p[1] for p in pts]
    fitted = {}
    for r in rows["fitted_parameters"]:
        fitted.setdefault((r["direction_id"], r["model"]), {})[r["parameter"]] = r["estimate"]
    h = np.linspace(0.0, xmax + 10.0, 300)
    for (direction, model), par in sorted(fitted.items()):
        color = BLUE if direction == "LATERAL_BETWEEN" else GREEN
        style = "-" if model == "spherical" else ":"
        curve = gamma_model(h, model, par["nugget"], par["structured_sill"], par["range_m"])
        gammas += list(curve)
        ax.plot(h, curve, ls=style, lw=1.1, color=color, label=f"Fitted {model} ({direction.replace('_', ' ').lower()})")
    ax.axhline(pq, ls="--", lw=0.8, color=NEUTRAL)
    ax.set_xlim(0.0, xmax + 10.0)
    ax.set_ylim(0.0, max(0.27, 1.12 * max(gammas)))
    for label, (x, y) in end.items():
        ax.annotate(label, (x, y), xytext=(7, 0), textcoords="offset points", ha="left", va="center", fontsize=6.2,
                    color=INK, annotation_clip=False)
    ax.annotate(f"p(1 - p) = {pq:.3f}", (xmax + 10.0, pq), xytext=(4, 0), textcoords="offset points", ha="left",
                va="center", fontsize=6.2, color=INK, annotation_clip=False)
    ax.set_xlabel("Lag centre (m)")
    ax.set_ylabel("Semivariance γ(h) (indicator units)")
    status = {(r["direction_id"], r["model"]): r["fit_status"] for r in rows["fit_status"]}
    if not fitted:
        note = "No model drawn; fit status: " + "; ".join(
            f"{d.lower().replace('_', ' ')}, {m}: {s.lower().replace('_', ' ')}" for (d, m), s in sorted(status.items()))
        ax.text(0.02, 0.03, textwrap.fill(note, 80), transform=ax.transAxes, fontsize=5.8, color=INK, va="bottom")
    ax.legend(loc="upper left", fontsize=6.2)
    _footer(fig, receipt, "between-hole pairs only; within-hole pairs excluded")
    fit_text = (f"{len(fitted)} of {len(status)} base fits are FITTED and drawn as curves" if fitted else
                f"no base fit is FITTED, so no curve is drawn (fit status in O2-T03)")
    return fig, _caption(receipt, "Experimental indicator semivariograms of between-hole pairs for the lateral basis (horizontal "
                                  "lag, relative-depth difference at most 3 m) and the three-dimensional family (reported). "
                                  f"Dashed line: marginal variance p(1 - p) = {pq:.3f}; {fit_text}.")


def _azimuth(rows: dict, receipt: dict):
    bins = rows["azimuth_bins"]
    if not bins:
        raise NotSupported("no horizontal azimuth bins in the receipt")
    if all(b["direction_status"] != "SUPPORTED" for b in bins):
        raise NotSupported("every horizontal azimuth direction is SKIPPED")
    pq = _pq(rows)
    directions = sorted({(b["azimuth_deg"], b["direction_id"], b["direction_status"], b["angular_tolerance_deg"])
                         for b in bins})
    compass = {0.0: "N-S", 45.0: "NE-SW", 90.0: "E-W", 135.0: "NW-SE"}
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.1, right=0.98, top=0.85, bottom=0.11, wspace=0.12, hspace=0.6)
    top = max(0.3, 1.15 * pq)
    for ax, (az, direction, status, tol) in zip(axes.flat, directions):
        rr = [b for b in bins if b["direction_id"] == direction]
        supported = [b for b in rr if b["supported"]]
        under = [b for b in rr if not b["supported"] and b["n_pairs"] > 0]
        if supported:
            ax.plot([b["lag_centre_m"] for b in supported], [b["gamma"] for b in supported], "o", ms=3.4, color=BLUE)
        if under:
            ax.plot([b["lag_centre_m"] for b in under], [0.0] * len(under), "x", ms=4, color=NEUTRAL, mew=0.9, ls="none")
            for b in under:
                ax.text(b["lag_centre_m"], 0.012, f"{b['n_pairs']}", ha="center", va="bottom", fontsize=4.6, color=INK)
        ax.axhline(pq, ls="--", lw=0.8, color=NEUTRAL)
        ax.set_title(f"{az:03.0f}° ({compass.get(az, '')}), tolerance ±{tol:g}°\n"
                     f"{status.lower()}, {len(supported)} supported bins", loc="left", fontsize=6.2)
        ax.set_ylim(0.0, top)
    for ax in axes[-1]:
        ax.set_xlabel("Lag centre (m)")
    for ax in axes[:, 0]:
        ax.set_ylabel("γ(h)")
    handles = [Line2D([], [], marker="o", ls="none", ms=3.6, color=BLUE, label="Supported bin (γ shown)"),
               Line2D([], [], marker="x", ls="none", ms=4, color=NEUTRAL, mew=0.9,
                      label="Under-powered bin (pair count shown; γ withheld)"),
               Line2D([], [], ls="--", lw=0.8, color=NEUTRAL, label="p(1 - p), marginal variance")]
    fig.legend(handles=handles, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 0.995))
    _footer(fig, receipt, "exploratory: no leave-one-line-out test and no fit; relative-depth difference at most 3 m")
    return fig, _caption(receipt, "Horizontal azimuth semivariograms (exploratory) at 0, 45, 90 and 135 degrees clockwise from "
                                  f"grid north, tolerance ±22.5°. Dashed line: p(1 - p) = {pq:.3f}. Under-powered bins are "
                                  "marked with their pair counts; a direction with no supported bin is SKIPPED.")


def _sensitivity(rows: dict, receipt: dict):
    sens = [s for s in rows["sensitivity_rows"] if s["status"] == "COMPLETED"]
    skipped = [s for s in rows["sensitivity_rows"] if s["status"] == "SKIPPED"]
    if not sens:
        raise NotSupported("no completed sensitivity run")
    short = {"FITTED": "fitted", "NOT_IDENTIFIABLE": "not identifiable", "INADMISSIBLE": "inadmissible", None: "no fit"}
    entries = []
    for r in rows["base_rows"]:
        entries.append((f"{r['direction_id']} · base", r["supported_bins"], r["spherical_status"], r["exponential_status"], True))
    for s in sens:
        entries.append((f"{s['direction_id']} · {s['variant_name']}", s["supported_bins"], s["spherical_status"],
                        s["exponential_status"], False))
    entries.sort(key=lambda e: (e[0].split(" · ")[0], not e[4], e[0]))
    height = 0.34 * len(entries) + 2.0
    fig, ax = plt.subplots(figsize=(7.2, height))
    fig.subplots_adjust(left=0.36, right=0.97, top=1.0 - 0.5 / height, bottom=1.25 / height)
    y = np.arange(len(entries))
    ax.barh(y, [e[1] or 0 for e in entries], height=0.62, linewidth=0,
            color=[NEUTRAL_LIGHT if e[4] else BLUE for e in entries])
    for k, e in enumerate(entries):
        ax.text((e[1] or 0) + 0.4, k, f"spherical {short.get(e[2], e[2])}; exponential {short.get(e[3], e[3])}",
                va="center", fontsize=5.6, color=INK)
    ax.set_yticks(y, [e[0] for e in entries], fontsize=5.8)
    ax.invert_yaxis()
    ax.set_xlim(0, max((e[1] or 0) for e in entries) + 36)
    ax.set_xlabel("Supported lag bins (count)")
    handles = [Patch(facecolor=NEUTRAL_LIGHT, label="Base experiment"),
               Patch(facecolor=BLUE, label="Sensitivity variant (one factor changed)")]
    ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, fontsize=6.2)
    if skipped:
        note = "; ".join(f"{s['variant_name']} {s['reason']}" for s in skipped)
        fig.text(0.01, 0.05, textwrap.fill("Not run: " + note, 160), fontsize=5.6, color=MUTED, va="bottom")
    _footer(fig, receipt, "one factor changed per variant; base values are the predeclared configuration")
    return fig, _caption(receipt, f"Supported lag bins and fit status (spherical and exponential) for {len(sens)} completed "
                                  f"sensitivity experiments and their base experiments; {len(skipped)} configured entries were "
                                  "skipped, with reasons shown in the figure.")


def _extension(rows: dict, receipt: dict):
    design, strict = "DESIGN_8_2_v1", "STRICT_SGS_v1"
    bins = [b for b in rows["extension_bins"] if b["supported"]]
    if not bins:
        raise NotSupported("no supported bins for the configuration-3 lateral extension")
    marg = {m["label_rule_id"]: float(m["p_one_minus_p"]) for m in rows["marginal_variance"]}
    status = {(r["label_rule_id"], r["model"]): r["fit_status"] for r in rows["fit_status"]}
    pts = {rule: sorted((b["lag_centre_m"], b["gamma"]) for b in bins if b["label_rule_id"] == rule) for rule in (design, strict)}
    same_curve = bool(pts[design]) and len(pts[design]) == len(pts[strict]) and np.allclose(
        [p[1] for p in pts[design]], [p[1] for p in pts[strict]], rtol=0.0, atol=1e-12)
    same_marg = abs(marg[design] - marg[strict]) < 1e-12
    xmax = max(b["lag_centre_m"] for b in bins)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    fig.subplots_adjust(left=0.11, right=0.74, top=0.97, bottom=0.14)
    gammas, end = [max(marg.values(), default=0.0)], {}
    # The comparator is drawn first, as hollow squares, so that the DESIGN circles stay visible where the curves coincide.
    if pts[strict]:
        ax.plot([p[0] for p in pts[strict]], [p[1] for p in pts[strict]], marker="s", ms=6.2, mfc="none", mec=GREEN,
                mew=0.9, lw=0.6, color=GREEN, label="STRICT_SGS_v1 (comparator, authorised)")
        gammas += [p[1] for p in pts[strict]]
    if pts[design]:
        ax.plot([p[0] for p in pts[design]], [p[1] for p in pts[design]], marker="o", ms=3.4, lw=0.6, color=BLUE,
                label="DESIGN_8_2_v1 (approved, primary)")
        gammas += [p[1] for p in pts[design]]
    if same_curve:
        end["DESIGN = STRICT (identical)"] = pts[design][-1]
    else:
        if pts[design]:
            end["DESIGN_8_2_v1"] = pts[design][-1]
        if pts[strict]:
            end["STRICT comparator"] = pts[strict][-1]
    fitted = {}
    for r in rows["fitted_parameters"]:
        fitted.setdefault((r["label_rule_id"], r["model"]), {})[r["parameter"]] = r["estimate"]
    h = np.linspace(0.0, xmax + 10.0, 300)
    for (rule, model), par in sorted(fitted.items()):
        curve = gamma_model(h, model, par["nugget"], par["structured_sill"], par["range_m"])
        gammas += list(curve)
        ax.plot(h, curve, ls="-" if model == "spherical" else "-.", lw=1.1, color=BLUE if rule == design else GREEN,
                label=f"Fitted {model} ({'DESIGN' if rule == design else 'STRICT'})")
    if same_marg:
        refs = [(marg[design], f"p(1 - p) = {marg[design]:.3f} (both samples)")]
        ax.axhline(marg[design], ls="--", lw=0.8, color=NEUTRAL)
    else:
        refs = [(marg[design], f"p(1 - p) DESIGN = {marg[design]:.3f}"), (marg[strict], f"p(1 - p) STRICT = {marg[strict]:.3f}")]
        ax.axhline(marg[design], ls="--", lw=0.8, color=NEUTRAL)
        ax.axhline(marg[strict], ls=":", lw=0.8, color=NEUTRAL)
    ax.set_xlim(0.0, xmax + 10.0)
    ax.set_ylim(0.0, max(0.27, 1.12 * max(gammas)))
    for label, (x, y) in end.items():
        ax.annotate(label, (x, y), xytext=(7, 0), textcoords="offset points", ha="left", va="center", fontsize=6.2,
                    color=INK, annotation_clip=False)
    for y, text in refs:
        ax.annotate(text, (xmax + 10.0, y), xytext=(4, 0), textcoords="offset points", ha="left", va="center",
                    fontsize=6.2, color=INK, annotation_clip=False)
    ax.set_xlabel("Lag centre (m)")
    ax.set_ylabel("Semivariance γ(h) (indicator units)")
    if not fitted:
        note = "No model drawn; fit status: " + "; ".join(
            f"{'DESIGN' if r == design else 'STRICT'} {m}: {s.lower().replace('_', ' ')}"
            for (r, m), s in sorted(status.items()))
        ax.text(0.02, 0.03, textwrap.fill(note, 80), transform=ax.transAxes, fontsize=5.8, color=INK, va="bottom")
    ax.legend(loc="upper left", fontsize=6.2)
    _footer(fig, receipt, "exploratory configuration-3 extension; this figure does not change the handoff")
    fit_text = f"{len(fitted)} fitted curve(s) drawn" if fitted else "no model is FITTED, so no curve is drawn"
    coincide = (" The two samples give identical semivariances at every lag, because the comparator reproduces the DESIGN "
                "indicator on every DESIGN binary interval; the series coincide, so the comparator is drawn as hollow markers."
                if same_curve else "")
    return fig, _caption(receipt, "Configuration-3 exploratory lateral extension: experimental indicator semivariograms with "
                                  "50 m bins to 2000 m and a relative-depth difference of at most 3 m, for DESIGN_8_2_v1 "
                                  "(approved, primary) and STRICT_SGS_v1 (comparator, authorised for this run only). Dashed line: "
                                  "the DESIGN marginal variance; dotted line, where it differs: the STRICT marginal variance; "
                                  f"{fit_text}.{coincide}")


FIGURES = OrderedDict([
    ("O2-F01", ("Drill-hole plan view by approved line", "O2_F01_drill_hole_plan", _plan, "O2-F01.sql")),
    ("O2-F02", ("Positive metres and graphitic fraction by hole and line", "O2_F02_occurrence_hole_line", _occurrence,
                "O2-F02.sql")),
    ("O2-F03", ("Binary occurrence by depth and by weathering class", "O2_F03_depth_weathering", _depth_weathering,
                "O2-F03.sql")),
    ("O2-F04", ("Observed hole strips in relative depth", "O2_F04_hole_strips", _strips, "O2-F04.sql")),
    ("O2-F05", ("Pair support by lag", "O2_F05_pair_support", _pair_support, "O2-F05.sql")),
    ("O2-F06", ("Between-hole indicator semivariograms", "O2_F06_between_hole_variogram", _variogram, "O2-F06.sql")),
    ("O2-F07", ("Horizontal azimuth semivariograms (exploratory)", "O2_F07_azimuth_variograms", _azimuth, "O2-F07.sql")),
    ("O2-F08", ("Sensitivity of supported bins and fit status", "O2_F08_sensitivity", _sensitivity, "O2-F08.sql")),
    ("O2-F09", ("Configuration-3 lateral extension with the STRICT comparator (exploratory)", "O2_F09_extension_strict",
                _extension, "O2-F09.sql")),
])


def _save(fig, figure_id: str, stem: str) -> list[Path]:
    O2_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["svg.hashsalt"] = figure_id
    paths = []
    for ext, kwargs in (("svg", {"metadata": {"Date": None}}),
                        ("pdf", {"metadata": {"CreationDate": None, "ModDate": None}}),
                        ("png", {"dpi": 300, "metadata": {"Software": None}})):
        path = O2_FIGURE_DIR / f"{stem}.{ext}"
        fig.savefig(path, **kwargs)
        paths.append(path)
    return paths


def render_all(o2_path=O2_DB_PATH, figure_ids: list[str] | None = None) -> dict:
    conn = connect_o2(o2_path)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise StopError("no receipt: run the import first")
        receipt = dict(receipt)
        rid = receipt["receipt_id"]
        created = utc_now()
        summary = {}
        for fid, (title, stem, renderer, sql_file) in FIGURES.items():
            if figure_ids and fid not in figure_ids:
                continue
            sql_path = O2_SQL_DIR / "figures" / sql_file
            queries = load_queries(sql_path)
            rows = {name: [dict(r) for r in conn.execute(text, {"receipt_id": rid}).fetchall()]
                    for name, text in queries.items()}
            if fid == "O2-F04":
                for s in _section_rows(rid, rows["section_geometry"]):
                    conn.execute("INSERT OR REPLACE INTO geological_section_registry (section_id, receipt_id, line_code, "
                                 "section_azimuth_deg, projection_basis, vertical_basis, observed_or_inferred, status, reason) "
                                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                 (s["section_id"], s["receipt_id"], s["line_code"], s["section_azimuth_deg"],
                                  s["projection_basis"], s["vertical_basis"], s["observed_or_inferred"], s["status"],
                                  s["reason"]))
            try:
                fig, caption = renderer(rows, receipt)
            except NotSupported as exc:
                fig, caption, status, reason = None, f"Not drawn: {exc}.", "NOT_SUPPORTED", str(exc)
            else:
                status, reason = "GENERATED", "rendered from the registered queries"
            conn.execute("DELETE FROM figure_query_registry WHERE figure_id = ?", (fid,))
            conn.execute("INSERT OR REPLACE INTO figure_registry (figure_id, title, status, reason, caption, created_utc) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (fid, title, status, reason, caption, created))
            for name, text in queries.items():
                conn.execute("INSERT INTO figure_query_registry (figure_id, query_name, sql_path, sql_sha256, params_json, "
                             "row_count) VALUES (?, ?, ?, ?, ?, ?)",
                             (fid, name, _rel(sql_path), sha256_bytes(sql_path.read_bytes()),
                              '{"receipt_id": %d}' % rid, len(rows[name])))
            if fig is None:
                summary[fid] = {"status": status, "reason": reason}
                continue
            paths = _save(fig, fid, stem)
            plt.close(fig)
            for path in paths:
                conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_sha256, "
                             "receipt_id, created_utc) VALUES (?, 'FIGURE', ?, ?, ?)",
                             (_rel(path), sha256_bytes(path.read_bytes()), rid, created))
            summary[fid] = {"status": status, "files": [_rel(p) for p in paths]}
        return summary
    finally:
        conn.close()

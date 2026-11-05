"""Stage A figure renderers. Every renderer receives rows from SQL files in sql/figures/ and never reads the
workbook, a notebook or any shapefile directly. Each function returns the list of drawn Figure objects with
the output stems that the registry will hash and record.
"""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402
from mpl_toolkits.mplot3d import Axes3D  # noqa: E402,F401  (registers the 3-D projection)
from shapely import wkt as shapely_wkt  # noqa: E402

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False, "svg.hashsalt": "kambale-stage-a",
    "pdf.compression": 6, "figure.dpi": 100, "savefig.dpi": 300,
})

# Okabe-Ito palette (colour-blind safe)
OI = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "vermillion": "#D55E00",
      "sky": "#56B4E9", "purple": "#CC79A7", "yellow": "#F0E442", "black": "#000000", "grey": "#8C8C8C"}
LINE_COLOURS = [OI["blue"], OI["green"], OI["purple"], OI["orange"], OI["sky"]]
STATE_COLOUR = {"POSITIVE": OI["vermillion"], "NEGATIVE": OI["sky"], "UNRESOLVED": "#BDBDBD"}
WEATHER_COLOUR = {"cw": OI["purple"], "hw": OI["orange"], "mw": OI["green"], "sw": OI["blue"],
                  "MISSING": OI["grey"], "fr": OI["yellow"]}
FOOTER_TEMPLATE = ("obj1_master {key} | label rules PROPOSED, not approved | coordinates PROVISIONAL "
                   "(UTM 30N, datum unverified) | vertical = metres relative to collar (no collar RL)")


def footer(fig, key: str, extra: str = "") -> None:
    import textwrap

    text = FOOTER_TEMPLATE.format(key=key)
    if extra:
        text = f"{text} | {extra}"
    fig.text(0.01, 0.005, textwrap.fill(text, 150), fontsize=5.5, color="#444444", ha="left", va="bottom")


def header(fig, figure_id: str, title: str) -> None:
    fig.text(0.01, 0.985, f"{figure_id}  {title}", fontsize=10, weight="bold", ha="left", va="top")


def _polygons(ax, rows, extent=None):
    palette = {"bmbt": "#F3E3B5", "bsa": "#D9D9D9"}
    for row in rows:
        geom = shapely_wkt.loads(row["geom_wkt"])
        parts = geom.geoms if hasattr(geom, "geoms") else [geom]
        for part in parts:
            coords = list(part.exterior.coords)
            ax.add_patch(Polygon(coords, closed=True, facecolor=palette.get(row["geo_symbol"], "#EEEEEE"),
                                 edgecolor="#AAAAAA", linewidth=0.3, zorder=0))
    if extent:
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])


def _scale_and_north(ax, x0, y0, length_m=500):
    ax.plot([x0, x0 + length_m], [y0, y0], color="black", lw=2)
    ax.text(x0 + length_m / 2, y0 + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.012, f"{length_m} m",
            ha="center", va="bottom", fontsize=6)
    xr = ax.get_xlim()[1]
    yr = ax.get_ylim()[1]
    ax.annotate("N", xy=(xr - (xr - ax.get_xlim()[0]) * 0.03, yr - (yr - ax.get_ylim()[0]) * 0.10),
                xytext=(xr - (xr - ax.get_xlim()[0]) * 0.03, yr - (yr - ax.get_ylim()[0]) * 0.02),
                ha="center", fontsize=8, arrowprops=dict(arrowstyle="-|>", color="black"))


def f01(rows: dict, key: str) -> list:
    plan, regional = rows["F01_collar_plan.sql"], rows["F01_regional.sql"]
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    xs = [r["easting_m"] for r in plan]
    ys = [r["northing_m"] for r in plan]
    pad = 350
    extent = (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)
    _polygons(ax, regional, extent)
    lines = sorted({r["line_code"] for r in plan})
    for index, line in enumerate(lines):
        pts = [r for r in plan if r["line_code"] == line]
        ax.scatter([p["easting_m"] for p in pts], [p["northing_m"] for p in pts], s=18,
                   color=LINE_COLOURS[index % 5], edgecolor="black", linewidth=0.3, zorder=3, label=f"{line} (n={len(pts)})")
        for p in pts:
            ax.text(p["easting_m"] + 6, p["northing_m"] + 6, p["hole_id"].split(" ")[-1], fontsize=4.2, zorder=4)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_aspect("equal")
    ax.set_xlabel("Easting (m, UTM zone 30N; provisional)")
    ax.set_ylabel("Northing (m, UTM zone 30N; provisional)")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.tick_params(labelsize=6)
    _scale_and_north(ax, extent[0] + 200, extent[2] + 200)
    handles = [Line2D([0], [0], marker="o", ls="", color=LINE_COLOURS[i % 5], markeredgecolor="black",
                      markersize=4, label=f"{line} (n={sum(1 for r in plan if r['line_code'] == line)})")
               for i, line in enumerate(lines)]
    handles.append(Polygon([(0, 0)], facecolor="#F3E3B5", edgecolor="#AAAAAA", label="bmbt biotite schist (regional)"))
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=6)
    ax.set_title("Collar locations by provisional drill line (alternate Easting/Northing pair differs by "
                 "median 3.2 m, max 13.3 m)", fontsize=7)
    header(fig, "F01", "Collar location map")
    fig.subplots_adjust(top=0.90, bottom=0.10, left=0.10, right=0.98)
    footer(fig, key, "regional polygons: 1:1,000,000 context only")
    return [("F01_collar_plan", fig)]


def f02(rows: dict, key: str) -> list:
    holes = rows["F02_hole_lengths.sql"]
    depths = [r["max_depth_m"] for r in holes]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.6), gridspec_kw={"width_ratios": [1.2, 1]})
    bins = list(range(0, 70, 5))
    a.hist(depths, bins=bins, color=OI["blue"], edgecolor="white")
    a.set_xlabel("Drilled length (max_depth, m)")
    a.set_ylabel("Number of holes")
    a.set_title("Hole length distribution (bin width 5 m)")
    lines = sorted({r["line_code"] for r in holes})
    data = [[r["max_depth_m"] for r in holes if r["line_code"] == line] for line in lines]
    b.boxplot(data, tick_labels=[ln.replace("NOM_N", "N") for ln in lines], patch_artist=True,
              boxprops=dict(facecolor="#D6EAF8"), medianprops=dict(color=OI["vermillion"]))
    b.set_ylabel("Drilled length (m)")
    b.set_title("By provisional drill line")
    b.tick_params(axis="x", labelsize=6)
    total = sum(depths)
    summary = (f"n = {len(depths)} holes; total drilled = {total:.0f} m; mean = {total / len(depths):.1f} m; "
               f"min = {min(depths):.0f} m; max = {max(depths):.0f} m. Denominator: holes.")
    fig.text(0.01, 0.10, summary, fontsize=6.5)
    header(fig, "F02", "Drill-hole length distribution")
    fig.subplots_adjust(top=0.82, bottom=0.25, left=0.08, right=0.98, wspace=0.3)
    footer(fig, key)
    return [("F02_hole_lengths", fig)]


def f03(rows: dict, key: str) -> list:
    comp, qc = rows["F03_completeness.sql"], rows["F03_qc_summary.sql"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 5.2), gridspec_kw={"width_ratios": [1.1, 1]})
    sheet_colour = {"Collars": OI["blue"], "Surveys": OI["green"], "Logging": OI["orange"]}
    labels = [f"{r['source_sheet']}.{r['field_name']}" for r in comp]
    values = [r["pct_non_blank"] for r in comp]
    colours = [sheet_colour[r["source_sheet"]] for r in comp]
    y = list(range(len(comp)))
    a.barh(y, values, color=colours)
    a.set_yticks(y)
    a.set_yticklabels(labels, fontsize=4.8)
    a.set_xlim(0, 100)
    a.set_xlabel("Non-blank records (%); denominator = rows per sheet")
    a.set_title("A. Field completeness (raw sheets)")
    a.legend(handles=[Rectangle((0, 0), 1, 1, color=c, label=s) for s, c in sheet_colour.items()],
             loc="lower right", frameon=False)
    failed = [r for r in qc if r["result"] == "FAIL" and r["n_records"]]
    failed.sort(key=lambda r: (r["severity"], -r["n_records"]))
    sev_colour = {"ERROR": OI["vermillion"], "WARNING": OI["orange"], "INFO": OI["sky"]}
    yb = list(range(len(failed)))
    b.barh(yb, [r["n_records"] for r in failed], color=[sev_colour[r["severity"]] for r in failed])
    b.set_yticks(yb)
    b.set_yticklabels([r["check_id"] for r in failed], fontsize=5)
    b.invert_yaxis()
    b.set_xlabel("Records flagged (n_records)")
    b.set_title("B. QA/QC checks with FAIL results")
    b.legend(handles=[Rectangle((0, 0), 1, 1, color=c, label=s) for s, c in sev_colour.items()],
             loc="lower right", frameon=False)
    header(fig, "F03", "Completeness and QA/QC summary")
    fig.subplots_adjust(top=0.92, bottom=0.10, left=0.25, right=0.98, wspace=0.75)
    footer(fig, key, "PASS checks are listed in T01 part C and reports/QAQC_REPORT.md")
    return [("F03_completeness_qc", fig)]


def f04(rows: dict, key: str) -> list:
    geo = rows["F04_3d_intervals.sql"]
    fig = plt.figure(figsize=(7.2, 6.0))
    ax = fig.add_subplot(111, projection="3d")
    by_hole = defaultdict(list)
    for r in geo:
        by_hole[r["hole_id"]].append(r)
    for hole, items in by_hole.items():
        ax.plot([i["easting_m"] for i in items], [i["northing_m"] for i in items], [i["z_relative_m"] for i in items],
                color="#B0B0B0", lw=0.5, zorder=1)
        for state in ("UNRESOLVED", "NEGATIVE", "POSITIVE"):
            pts = [i for i in items if i["strict_state"] == state]
            if pts:
                ax.scatter([p["easting_m"] for p in pts], [p["northing_m"] for p in pts],
                           [p["z_relative_m"] for p in pts], s=3, color=STATE_COLOUR[state], depthshade=False)
    ax.set_xlabel("Easting (m)", labelpad=6)
    ax.set_ylabel("Northing (m)", labelpad=6)
    ax.set_zlabel("Relative Z (m; below collar)", labelpad=6)
    ax.view_init(elev=22, azim=-62)
    ax.tick_params(labelsize=6)
    handles = [Line2D([0], [0], marker="o", ls="", color=STATE_COLOUR[s], markersize=4, label=lbl)
               for s, lbl in (("POSITIVE", "Sgs, strict candidate"), ("NEGATIVE", "other valid code"),
                              ("UNRESOLVED", "unresolved code"))]
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=6)
    header(fig, "F04", "A. 3-D interval midpoints (relative Z only; provisional)")
    fig.subplots_adjust(top=0.92, bottom=0.04, left=0.0, right=0.98)
    footer(fig, key, "straight-hole, single end-of-hole orientation; no collar RL")
    strip = _strip_figure(rows["F04_strip_logs.sql"], key)
    return [("F04_3d_relative_z", fig), ("F04_strip_logs", strip)]


def _strip_figure(rows, key):
    holes = OrderedDict()
    for r in sorted(rows, key=lambda r: (r["line_code"], r["hole_id"])):
        holes.setdefault(r["line_code"], OrderedDict()).setdefault(r["hole_id"], []).append(r)
    n_lines = len(holes)
    fig, axes = plt.subplots(1, n_lines, figsize=(7.6, 5.4), sharey=True,
                             gridspec_kw={"width_ratios": [max(len(v), 1) for v in holes.values()]})
    if n_lines == 1:
        axes = [axes]
    max_depth = max(r["max_depth_m"] for r in rows)
    for ax, (line, group) in zip(axes, holes.items()):
        for col, (hole, items) in enumerate(group.items()):
            for it in items:
                state = it["strict_state"] or "UNRESOLVED"
                hatch = "//" if it["rock_code_status"] != "VALID" else None
                ax.add_patch(Rectangle((col - 0.4, it["depth_from_m"]), 0.8, it["depth_to_m"] - it["depth_from_m"],
                                       facecolor=STATE_COLOUR[state], edgecolor="none", hatch=hatch, linewidth=0))
            ax.text(col, -max_depth * 0.02, hole.split(" ")[-1], ha="center", va="bottom", fontsize=3.8, rotation=90)
        ax.set_xlim(-0.6, len(group) - 0.4)
        ax.set_title(line.replace("NOM_N", "N "), fontsize=7)
        ax.set_xticks([])
    axes[0].set_ylim(max_depth * 1.02, -max_depth * 0.08)
    axes[0].set_ylabel("Measured depth (m; 1-m intervals)")
    handles = [Rectangle((0, 0), 1, 1, color=STATE_COLOUR[s], label=lbl)
               for s, lbl in (("POSITIVE", "Sgs (strict)"), ("NEGATIVE", "other valid code"),
                              ("UNRESOLVED", "unresolved")) ]
    handles.append(Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="black", hatch="//", label="code not in legend / blank"))
    axes[-1].legend(handles=handles, loc="lower right", frameon=False, fontsize=6)
    header(fig, "F04", "B. Interval strips by provisional drill line (measured depth)")
    fig.subplots_adjust(top=0.88, bottom=0.12, left=0.08, right=0.98, wspace=0.12)
    footer(fig, key, "columns = holes within each line; no interpolation between holes")
    return fig


def f05(rows: dict, key: str) -> list:
    usage = [r for r in rows["F05_rock_usage.sql"] if r["n_intervals"] > 0]
    missing = rows["F05_missing_codes.sql"][0]
    labels = [f"{r['code']}  {r['legend_description'] or '(not in legend)'}" for r in usage]
    labels.append("(blank)  rock_type1 missing")
    counts = [r["n_intervals"] for r in usage] + [missing["n_intervals"]]
    metres = [r["logged_m"] for r in usage] + [missing["logged_m"]]
    colours = [OI["vermillion"] if r["code"] == "Sgs" else (OI["grey"] if r["code_status"] != "VALID" else OI["blue"])
               for r in usage] + [OI["grey"]]
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 4.2), sharey=True)
    y = list(range(len(labels)))
    a.barh(y, counts, color=colours)
    b.barh(y, metres, color=colours)
    a.set_yticks(y)
    a.set_yticklabels(labels, fontsize=5.5)
    a.invert_yaxis()
    a.set_xlabel("Intervals (n; denominator 1,910)")
    b.set_xlabel("Logged metres (1-m support)")
    a.set_title("A. Count")
    b.set_title("B. Logged metres")
    header(fig, "F05", "Lithology code frequency (logged as recorded)")
    fig.subplots_adjust(top=0.88, bottom=0.12, left=0.42, right=0.98, wspace=0.08)
    footer(fig, key, "grey = code not in legend or blank; red = Sgs")
    return [("F05_lithology_frequency", fig)]


def f06(rows: dict, key: str) -> list:
    data = rows["F06_hole_graphite.sql"]
    order = sorted(data, key=lambda r: (-r["sgs_m"], r["hole_id"]))
    names = [r["hole_id"].split(" ")[-1] for r in order]
    y = list(range(len(order)))
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.4, 7.2), sharey=True, gridspec_kw={"width_ratios": [1.3, 1]})
    a.barh(y, [r["sgs_m"] for r in order], color=OI["vermillion"], label="Sgs, strict candidate (Target A)")
    a.barh(y, [r["recon_pos_m"] for r in order], color="none", edgecolor=OI["blue"], linewidth=0.6,
           hatch="..", label="RECON_2OF3 positive metres (proposed, not approved)")
    a.set_yticks(y)
    a.set_yticklabels(names, fontsize=4.6)
    a.invert_yaxis()
    a.set_xlabel("Apparent along-hole metres (denominator: logged metres per hole)")
    a.legend(frameon=False, fontsize=5.5, loc="lower right")
    a.set_title("A. Graphitic intersections by hole")
    frac = [(r["sgs_m"] / r["logged_m"]) if r["logged_m"] else 0.0 for r in order]
    b.scatter(frac, y, s=10, color=OI["vermillion"], zorder=3)
    b.hlines(y, 0, frac, color="#DDDDDD", lw=0.6)
    b.set_xlim(0, 1)
    b.set_xlabel("Sgs fraction of logged metres")
    b.set_title("B. Strict fraction")
    header(fig, "F06", "Graphitic (Sgs) apparent thickness and proportion by hole")
    fig.subplots_adjust(top=0.92, bottom=0.07, left=0.08, right=0.98, wspace=0.08)
    footer(fig, key, "apparent thickness, not true stratigraphic thickness")
    return [("F06_graphitic_by_hole", fig)]


def f07(rows: dict, key: str) -> list:
    data = rows["F07_depth_weathering.sql"]
    bins = sorted({r["depth_bin_from_m"] for r in data})
    classes = ["cw", "hw", "mw", "sw", "MISSING"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    width = 4.0
    bottoms = [0.0] * len(bins)
    for cls in classes:
        vals = []
        for b_ in bins:
            match = [r for r in data if r["depth_bin_from_m"] == b_ and r["weathering_class"] == cls]
            vals.append(match[0]["n_strict_positive"] if match else 0)
        if any(vals):
            ax.bar([b_ + 2.5 for b_ in bins], vals, bottom=bottoms, width=width, color=WEATHER_COLOUR[cls],
                   label=f"weathering {cls}", edgecolor="white", linewidth=0.3)
            bottoms = [bt + v for bt, v in zip(bottoms, vals)]
    totals = [sum(r["n_all"] for r in data if r["depth_bin_from_m"] == b_) for b_ in bins]
    ax.step([b_ for b_ in bins] + [bins[-1] + 5], totals + [totals[-1]], where="post", color="black", lw=0.8,
            label="all intervals in bin (denominator)")
    ax.set_xlabel("Measured depth bin (m; midpoint, 5-m bins)")
    ax.set_ylabel("Strict graphitic intervals (n)")
    ax.legend(frameon=False, fontsize=6, ncol=2)
    ax.set_xticks(bins)
    header(fig, "F07", "Graphitic (Sgs) intervals by measured depth and weathering")
    fig.subplots_adjust(top=0.88, bottom=0.14, left=0.1, right=0.98)
    footer(fig, key, "weathering 'fr' is not used in the logging; missing weathering shown separately")
    return [("F07_depth_weathering", fig)]


def f08(rows: dict, key: str) -> list:
    points, regional, lines = rows["F08_plan_graphite.sql"], rows["F01_regional.sql"], rows["F08_lines.sql"]
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    xs = [p["easting_m"] for p in points]
    ys = [p["northing_m"] for p in points]
    pad = 350
    extent = (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)
    _polygons(ax, regional, extent)
    zero = [p for p in points if not p["sgs_fraction"]]
    ax.scatter([p["easting_m"] for p in zero], [p["northing_m"] for p in zero], s=14, facecolors="none",
               edgecolors="#666666", zorder=3, label="no Sgs logged")
    pos = [p for p in points if p["sgs_fraction"]]
    sc = ax.scatter([p["easting_m"] for p in pos], [p["northing_m"] for p in pos],
                    s=[10 + 1.2 * p["logged_m"] for p in pos], c=[p["sgs_fraction"] for p in pos],
                    cmap="viridis", vmin=0, vmax=1, edgecolor="black", linewidth=0.3, zorder=4)
    for line in lines:
        ax.text(extent[0] + 40, line["nominal_northing_m"] + 25, line["line_code"].replace("NOM_N", "N "),
                fontsize=6, color="#333333")
    cbar = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Sgs fraction of logged metres (strict)", fontsize=7)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_aspect("equal")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.tick_params(labelsize=6)
    ax.set_xlabel("Easting (m, UTM 30N; provisional)")
    ax.set_ylabel("Northing (m, UTM 30N; provisional)")
    ax.legend(loc="upper right", frameon=False, fontsize=6)
    header(fig, "F08", "Plan map of graphitic fraction by collar and provisional drill line")
    fig.subplots_adjust(top=0.92, bottom=0.10, left=0.10, right=0.98)
    footer(fig, key, "marker size proportional to logged metres; line labels provisional")
    return [("F08_plan_graphitic_fraction", fig)]


def f09(rows: dict, key: str) -> list:
    data = rows["F09_sections.sql"]
    lines = OrderedDict()
    for r in data:
        lines.setdefault(r["line_code"], OrderedDict()).setdefault(r["hole_id"], []).append(r)
    fig, axes = plt.subplots(len(lines), 1, figsize=(7.4, 9.4), sharex=True)
    if len(lines) == 1:
        axes = [axes]
    for ax, (line, holes) in zip(axes, lines.items()):
        nominal = next(iter(holes.values()))[0]["nominal_northing_m"]
        for hole, items in holes.items():
            ax.plot([i["easting_m"] for i in items], [i["z_relative_m"] for i in items], color="#BBBBBB", lw=0.6)
            for state in ("UNRESOLVED", "NEGATIVE", "POSITIVE"):
                pts = [i for i in items if i["strict_state"] == state]
                if pts:
                    ax.scatter([p["easting_m"] for p in pts], [p["z_relative_m"] for p in pts], s=6,
                               color=STATE_COLOUR[state], zorder=3)
            top = items[0]
            ax.text(top["easting_m"], 1.0, hole.split(" ")[-1], fontsize=4.2, ha="center", va="bottom")
        ax.axhline(0, color="black", lw=0.5, ls=":")
        ax.set_ylabel("Relative Z (m)", fontsize=6)
        ax.set_title(f"{line.replace('NOM_N', 'N ')} (nominal Northing {nominal:.0f} m; {len(holes)} holes)", fontsize=7)
        ax.tick_params(labelsize=6)
    axes[-1].set_xlabel("Easting (m, UTM 30N; provisional)")
    axes[-1].ticklabel_format(style="plain", useOffset=False)
    handles = [Line2D([0], [0], marker="o", ls="", color=STATE_COLOUR[s], label=lbl)
               for s, lbl in (("POSITIVE", "Sgs (strict)"), ("NEGATIVE", "other valid code"),
                              ("UNRESOLVED", "unresolved"))]
    axes[0].legend(handles=handles, loc="lower left", frameon=False, fontsize=6, ncol=3)
    header(fig, "F09", "Relative-Z sections by provisional drill line (no interpolation)")
    fig.subplots_adjust(top=0.94, bottom=0.09, left=0.10, right=0.98, hspace=0.55)
    footer(fig, key, "collar elevation assumed common; vertical axis is depth below collar")
    return [("F09_relative_sections", fig)]


FIGURE_RENDERERS = {"F01": f01, "F02": f02, "F03": f03, "F04": f04, "F05": f05, "F06": f06, "F07": f07,
                    "F08": f08, "F09": f09}

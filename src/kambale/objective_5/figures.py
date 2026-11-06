"""Objective 5 figure renderers O5-F01..F10. Every figure reads only its registered SQL against the Objective 5 database.

A figure whose required rows are missing is registered NOT_SUPPORTED with the reason. Every footer states the relative depth
convention, that the uncertainty is model-based (not geostatistical), and that both model selections are INCONCLUSIVE.
F08-F10 add the scenario-analysis statement (lateral range assumed; relative grid volume, not a resource).
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
from matplotlib.colors import ListedColormap, to_rgba  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

from kambale.objective_5.config import (CLASS_ABSENT, CLASS_NO_SUPPORT, CLASS_PRESENT, CLASS_UNCERTAIN,  # noqa: E402
                                        O5_FIGURE_DIR, O5_SQL_DIR, PROJECT_ROOT, StopError, sha256_bytes, utc_now)
from kambale.objective_5.db import connect_o5  # noqa: E402

BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
GREY = "#BDBDBD"
INK = "#222222"
MUTED = "#555555"
CLASS_COLOURS = {CLASS_PRESENT: BLUE, CLASS_ABSENT: "#C9D6E3", CLASS_UNCERTAIN: ORANGE, CLASS_NO_SUPPORT: "#4D4D4D"}
CLASS_LABEL = {CLASS_PRESENT: "CONFIDENT_PRESENT", CLASS_ABSENT: "CONFIDENT_ABSENT (light grey-blue)",
               CLASS_UNCERTAIN: "UNCERTAIN", CLASS_NO_SUPPORT: "NO_SUPPORT (dark grey)"}
CLASS_ORDER = [CLASS_PRESENT, CLASS_ABSENT, CLASS_UNCERTAIN, CLASS_NO_SUPPORT]
SLICE_DEPTHS_M = (5.0, 10.0, 20.0, 30.0, 40.0)
LINE_COUNT = 5
SECTION_LINE = "NOM_N1112140"
SCENARIO_STATEMENT = "Scenario analysis: lateral range assumed, not estimated; relative grid volume, not a resource."
FOOTER = ("Depth is relative to the local collar (z_relative_m, straight-hole convention, PROVISIONAL_RELATIVE); absolute "
          "elevation is not used. Uncertainty is model-based (not geostatistical). Both model selections are INCONCLUSIVE "
          "against their runner-up.")

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.2, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "figure.dpi": 100,
    "savefig.dpi": 200, "legend.frameon": False,
})
KM = FuncFormatter(lambda v, _pos: f"{v / 1000.0:.2f}")


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


def _meta(conn) -> dict:
    return {r["meta_key"]: json.loads(r["meta_value"]) for r in conn.execute("SELECT * FROM grid_meta")}


def _layer_for(conn, z: float) -> tuple[int, float]:
    rows = conn.execute("SELECT iz, z_relative_m FROM grid_layers ORDER BY iz").fetchall()
    best = min(rows, key=lambda r: abs(r["z_relative_m"] - z))
    return int(best["iz"]), float(best["z_relative_m"])


def _plan_extent(meta):
    nE, nN = int(meta["n_easting"]), int(meta["n_northing"])
    return (meta["origin_easting_m"], meta["origin_easting_m"] + nE * meta["cell_easting_m"],
            meta["origin_northing_m"], meta["origin_northing_m"] + nN * meta["cell_northing_m"])


def _plan_array(rows, meta, key, transform=None):
    """Plan image (rows = northing index, columns = easting index); NaN where no value."""
    nE, nN = int(meta["n_easting"]), int(meta["n_northing"])
    img = np.full((nN, nE), np.nan)
    for r in rows:
        v = r[key]
        if v is not None:
            img[int(r["iy"]), int(r["ix"])] = transform(v) if transform else float(v)
    return img


def _section_array(rows, meta, key, transform=None):
    """Section image with depth increasing downwards (rows = depth index, columns = easting index)."""
    nE, nZ = int(meta["n_easting"]), int(meta["n_z"])
    img = np.full((nZ, nE), np.nan)
    for r in rows:
        v = r[key]
        if v is not None:
            img[int(r["iz"]), int(r["ix"])] = transform(v) if transform else float(v)
    return img[::-1]


def _section_extent(meta):
    nE = int(meta["n_easting"])
    x0 = meta["origin_easting_m"]
    zlo, zhi = (float(v) for v in meta["z_range_m"])
    return (x0, x0 + nE * meta["cell_easting_m"], -zlo, -zhi)


def _save(fig, figure_id, stem) -> Path:
    O5_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = O5_FIGURE_DIR / f"{figure_id}_{stem}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _grid_geometry(extent, nrows, ncols, width_in, left_in, right_in, top_in, bottom_in, wgap_in, hgap_in):
    """Figure height (inches) and panel size so equal-aspect map panels keep the map's own shape."""
    x0, x1, y0, y1 = extent
    pw = (width_in - left_in - right_in - wgap_in * (ncols - 1)) / ncols
    ph = pw * (y1 - y0) / (x1 - x0)
    height = top_in + nrows * ph + (nrows - 1) * hgap_in + bottom_in
    return height, pw, ph


def _receipt(conn):
    row = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
    if row is None:
        raise StopError("no receipt: run the import first")
    return dict(row)


def _class_code(label) -> float:
    return float(CLASS_ORDER.index(label)) if label in CLASS_ORDER else np.nan


def _rgba(code_img):
    """RGBA image of class codes; NaN is transparent."""
    out = np.zeros(code_img.shape + (4,))
    for k, c in enumerate(CLASS_ORDER):
        out[code_img == k] = to_rgba(CLASS_COLOURS[c])
    out[np.isnan(code_img)] = (0, 0, 0, 0)
    return out


def _class_handles(extra_hatch=False):
    handles = [Patch(facecolor=CLASS_COLOURS[c], edgecolor=GREY, label=CLASS_LABEL[c]) for c in CLASS_ORDER]
    if extra_hatch:
        handles.append(Patch(facecolor="white", edgecolor=INK, hatch="////", label="Above weathering front"))
    return handles


def f01(conn, q, receipt, meta):
    rows = conn.execute(q["plan_zones"], {"iz": _layer_for(conn, -5.0)[0]}).fetchall()
    collars = conn.execute(q["collars"]).fetchall()
    if not rows:
        raise NotSupported("no grid cells")
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    colours = {"INTERPOLATION": BLUE, "EXTRAPOLATION": "#9ECAE1", "NO_SUPPORT": "#FFFFFF"}
    for zone in ("EXTRAPOLATION", "INTERPOLATION"):
        pts = [r for r in rows if r["zone"] == zone]
        ax.scatter([r["easting_m"] for r in pts], [r["northing_m"] for r in pts], s=1.2, marker="s",
                   color=colours[zone], linewidths=0, label=f"{zone.title()} zone")
    lines = sorted({c["line_code"] for c in collars})
    for line in lines:
        sub = sorted([c for c in collars if c["line_code"] == line], key=lambda c: c["easting_m"])
        ax.plot([c["easting_m"] for c in sub], [c["northing_m"] for c in sub], color=MUTED, lw=0.6, zorder=3)
    ax.scatter([c["easting_m"] for c in collars], [c["northing_m"] for c in collars], s=9, color=INK, zorder=4,
               label="Collars (71 holes)")
    ax.set_aspect("equal")
    ax.xaxis.set_major_formatter(KM)
    ax.yaxis.set_major_formatter(KM)
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.set_xlabel("Easting (km, EPSG:32630)")
    ax.set_ylabel("Northing (km)")
    ax.set_title("Support zones in plan, with collars and drill lines")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), markerscale=3)
    # Size the figure to the plan's own aspect (equal-aspect map), so no empty bands above or below the map.
    ax.autoscale_view()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    plot_w = 7.2 * (0.97 - 0.1)
    height = plot_w * (y1 - y0) / (x1 - x0) + 0.45 + 0.6
    fig.set_size_inches(7.2, height)
    fig.subplots_adjust(left=0.1, right=0.97, top=1 - 0.45 / height, bottom=0.6 / height)
    return _save(fig, "O5-F01", "support_zones_plan"), len(rows)


def _slice_figure(conn, q, query_name, receipt, meta, figure_id, stem, title, cmap, label, vmin, vmax, categorical=False):
    panels = []
    for z in SLICE_DEPTHS_M:
        iz, zc = _layer_for(conn, -z)
        rows = conn.execute(q[query_name], {"iz": iz}).fetchall()
        panels.append((z, zc, rows))
    # Two rows of three: the sixth slot carries the class legend (categorical) or stays empty.
    extent = _plan_extent(meta)
    W, L, T, B, WG, HG, R = 9.6, 0.75, 0.85, 0.6, 0.22, 0.4, 1.2
    H, pw, ph = _grid_geometry(extent, 2, 3, W, L, R, T, B, WG, HG)
    grid_right = L + 3 * pw + 2 * WG
    fig, axes = plt.subplots(2, 3, figsize=(W, H), sharex=True, sharey=True)
    fig.subplots_adjust(left=L / W, right=grid_right / W, top=1 - T / H, bottom=B / H,
                        wspace=WG / pw, hspace=HG / ph)
    flat = axes.ravel()
    last = None
    for ax, (z, zc, rows) in zip(flat, panels):
        if categorical:
            code = np.full((int(meta["n_northing"]), int(meta["n_easting"])), np.nan)
            above = np.zeros(code.shape, dtype=bool)
            for r in rows:
                code[int(r["iy"]), int(r["ix"])] = _class_code(r["class_label"])
                above[int(r["iy"]), int(r["ix"])] = bool(r["above_front"])
            last = ax.imshow(_rgba(code), origin="lower", extent=extent, interpolation="nearest")
            if above.any():
                xc = meta["origin_easting_m"] + (np.arange(code.shape[1]) + 0.5) * meta["cell_easting_m"]
                yc = meta["origin_northing_m"] + (np.arange(code.shape[0]) + 0.5) * meta["cell_northing_m"]
                ax.contourf(xc, yc, above.astype(float), levels=[0.5, 1.5], colors="none", hatches=["////"])
        else:
            img = _plan_array(rows, meta, "value")
            last = ax.imshow(np.ma.masked_invalid(img), origin="lower", extent=extent, cmap=cmap, vmin=vmin,
                             vmax=vmax, interpolation="nearest")
        ax.set_title(f"z = -{z:g} m (layer {zc:g} m)")
        ax.set_aspect("equal")
        ax.xaxis.set_major_formatter(KM)
        ax.yaxis.set_major_formatter(KM)
        ax.xaxis.set_major_locator(MaxNLocator(3))
        ax.yaxis.set_major_locator(MaxNLocator(3))
    for ax in axes[1, :]:
        ax.set_xlabel("Easting (km)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Northing (km)")
    if categorical:
        flat[5].axis("off")
        flat[5].legend(handles=_class_handles(extra_hatch=True), loc="center", frameon=False, fontsize=6.5)
    else:
        flat[5].axis("off")
        flat[5].legend(handles=[Patch(facecolor="white", edgecolor=GREY, label="Blank cells: NO_SUPPORT (no probability)")],
                       loc="center", frameon=False, fontsize=6.5)
        cax = fig.add_axes([(grid_right + 0.3) / W, B / H, 0.16 / W, (2 * ph + HG) / H])
        cbar = fig.colorbar(last, cax=cax)
        cbar.set_label(label)
    fig.suptitle(title, y=1 - 0.25 / H)
    count = sum(len(r) for _, _, r in panels)
    return _save(fig, figure_id, stem), count


def f06(conn, q, receipt, meta):
    collars = conn.execute("SELECT line_code, AVG(northing_m) AS n FROM collars GROUP BY line_code ORDER BY line_code"
                           ).fetchall()
    lines = collars[:LINE_COUNT]
    if not lines:
        raise NotSupported("no drill lines")
    nN = int(meta["n_northing"])
    extent = _section_extent(meta)
    fig, axes = plt.subplots(len(lines), 3, figsize=(7.2, 2.75 * len(lines) + 1.5), squeeze=False)
    fig.subplots_adjust(left=0.12, right=0.80, top=0.9, bottom=0.1, hspace=0.45, wspace=0.28)
    total = 0
    prob_im = width_im = None
    for k, line in enumerate(lines):
        iy = int(np.clip(round((line["n"] - meta["origin_northing_m"]) / meta["cell_northing_m"] - 0.5), 0, nN - 1))
        cells = conn.execute(q["section_cells"], {"iy": iy}).fetchall()
        logged = conn.execute(q["section_logged"], {"line": line["line_code"]}).fetchall()
        total += len(cells)
        ax_p, ax_w, ax_c = axes[k]
        p_img = _section_array(cells, meta, "p_selected")
        w_img = _section_array(cells, meta, "interval_width")
        c_img = _section_array(cells, meta, "class_label", transform=_class_code)
        prob_im = ax_p.imshow(np.ma.masked_invalid(p_img), origin="upper", extent=extent, cmap="viridis", vmin=0,
                              vmax=1, aspect="auto", interpolation="nearest")
        width_im = ax_w.imshow(np.ma.masked_invalid(w_img), origin="upper", extent=extent, cmap="magma_r", vmin=0,
                               vmax=1, aspect="auto", interpolation="nearest")
        ax_c.imshow(_rgba(c_img), origin="upper", extent=extent, aspect="auto", interpolation="nearest")
        if logged:
            ax_p.scatter([l["easting_m"] for l in logged], [-l["z_relative_m"] for l in logged],
                         c=[l["indicator"] for l in logged], cmap=ListedColormap(["#FFFFFF", "#000000"]), s=4,
                         edgecolors=INK, linewidths=0.2, vmin=0, vmax=1)
        for ax in (ax_p, ax_w, ax_c):
            ax.set_ylim(extent[2], extent[3])
            ax.xaxis.set_major_formatter(KM)
            ax.xaxis.set_major_locator(MaxNLocator(3))
            ax.set_xlabel("Easting (km)")
        ax_p.set_ylabel(f"{line['line_code']}\nDepth below collar (m)")
        if k == 0:
            ax_p.set_title("Probability (dots: logged labels)")
            ax_w.set_title("Bootstrap interval width")
            ax_c.set_title("Class")
    cax_p = fig.add_axes([0.83, 0.12, 0.018, 0.78])
    cax_w = fig.add_axes([0.92, 0.12, 0.018, 0.78])
    fig.colorbar(prob_im, cax=cax_p, label="p (selected)")
    fig.colorbar(width_im, cax=cax_w, label="p_hi minus p_lo")
    fig.legend(handles=_class_handles(), loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.02), fontsize=6.5)
    fig.suptitle("Along-line sections: probability, interval width and class", y=0.985)
    fig.text(0.5, 0.945, "Each row is one drill line; cells are those nearest the line's mean northing; each cell is a "
                         "10 x 2 m rectangle.", ha="center", fontsize=6.5, color=MUTED)
    return _save(fig, "O5-F06", "along_line_sections"), total


def f07(conn, q, receipt, meta):
    rows = conn.execute(q["cells_3d"]).fetchall()
    if not rows:
        raise NotSupported("no INTERPOLATION cells in CONFIDENT_PRESENT or UNCERTAIN")
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    fig = plt.figure(figsize=(7.2, 5.6))
    ax = fig.add_subplot(111, projection="3d")
    for cls_name, colour in ((CLASS_UNCERTAIN, ORANGE), (CLASS_PRESENT, BLUE)):
        pts = [r for r in rows if r["class_label"] == cls_name]
        if pts:
            ax.scatter([p["easting_m"] for p in pts], [p["northing_m"] for p in pts],
                       [-p["z_relative_m"] for p in pts], s=1.5, color=colour, alpha=0.6, label=cls_name)
    ax.set_xlabel("Easting (km)")
    ax.set_ylabel("Northing (km)")
    ax.set_zlabel("Depth below collar (m)")
    ax.xaxis.set_major_formatter(KM)
    ax.yaxis.set_major_formatter(KM)
    ax.invert_zaxis()
    ax.set_title("INTERPOLATION zone: CONFIDENT_PRESENT and UNCERTAIN cells\n"
                 "Only cells within 25 m of a collar; depth-extrapolated cells excluded for confident classes.",
                 fontsize=7)
    ax.legend(loc="upper left", markerscale=4)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.08)
    return _save(fig, "O5-F07", "three_d_interpolation"), len(rows)


def _scenario_labels(conn):
    return [dict(r) for r in conn.execute("SELECT scenario_id, horizontal_range_m, feasibility, expected_volume_m3, "
                                          "volume_p50_m3 FROM sim_scenarios ORDER BY horizontal_range_m").fetchall()]


def f08(conn, q, receipt, meta):
    scen = _scenario_labels(conn)
    feas = [s for s in scen if s["feasibility"] == "FEASIBLE"]
    rows = conn.execute(q["volumes"]).fetchall()
    if not rows:
        raise NotSupported("no realisations: run the simulate stage")
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 5.6), sharex=True)   # common volume axis so scenarios compare
    fig.subplots_adjust(left=0.11, right=0.98, top=0.87, bottom=0.14, wspace=0.35, hspace=0.5)
    flat = axes.ravel()
    for ax in flat[len(scen):]:
        ax.axis("off")
    for ax in flat:
        ax.tick_params(labelbottom=True)
    for ax, s in zip(flat, scen):
        if s["feasibility"] != "FEASIBLE":
            ax.axis("off")
            ax.text(0.5, 0.5, f"{s['scenario_id']}\nINFEASIBLE: not run", ha="center", va="center", fontsize=7)
            continue
        vols = np.array([r["volume_m3"] for r in rows if r["scenario_id"] == s["scenario_id"]]) / 1e6
        exp = s["expected_volume_m3"] / 1e6
        p10, p50, p90 = np.percentile(vols, [10, 50, 90])
        ax.hist(vols, bins=20, color=BLUE, alpha=0.85, edgecolor="white", linewidth=0.4)
        ax.axvspan(p10, p90, color=GREY, alpha=0.35, lw=0, label="P10 to P90")
        ax.axvline(exp, color=ORANGE, lw=1.6, ls="--", label="expected sum(m) x 200")
        ax.axvline(p50, color=INK, lw=0.9, label="P50")
        ax.set_title(f"{s['scenario_id']}: a_h = {s['horizontal_range_m']:g} m")
        ax.set_xlabel("Grid volume (10^6 m3, relative)")
        ax.set_ylabel("Realisations")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    handles, labels = flat[0].get_legend_handles_labels()
    if len(scen) < len(flat):   # the unused sixth slot carries the legend, not a blank axis
        flat[len(scen)].legend(handles=handles, labels=labels, loc="center", fontsize=7, frameon=False)
    else:
        fig.legend(handles=handles, labels=labels, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.05), fontsize=6.5)
    fig.suptitle("Graphitic grid volume per scenario (100 realisations each)", y=0.975)
    return _save(fig, "O5-F08", "volume_distribution_by_scenario"), len(rows)


def f09(conn, q, receipt, meta):
    rows = conn.execute(q["connectivity"]).fetchall()
    if not rows:
        raise NotSupported("no realisations: run the simulate stage")
    scen = [s for s in _scenario_labels(conn) if s["feasibility"] == "FEASIBLE"]
    labels = [f"{s['horizontal_range_m']:g}" for s in scen]
    comp = [[r["n_components"] for r in rows if r["scenario_id"] == s["scenario_id"]] for s in scen]
    share = [[r["largest_share"] for r in rows if r["scenario_id"] == s["scenario_id"] and r["largest_share"] is not None]
             for s in scen]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.9))
    fig.subplots_adjust(left=0.11, right=0.98, top=0.82, bottom=0.2, wspace=0.32)
    for ax, data, ttl, ylab in ((ax1, comp, "Connected components (26-neighbour)", "Components per realisation"),
                                (ax2, share, "Largest component, share of positive",
                                 "Largest-component share")):
        ax.boxplot(data, tick_labels=labels, whis=(10, 90), showfliers=False, patch_artist=True,
                   boxprops={"facecolor": "#D9E8F3", "edgecolor": INK, "linewidth": 0.6},
                   medianprops={"color": BLUE, "linewidth": 1.2}, whiskerprops={"color": INK, "linewidth": 0.6},
                   capprops={"color": INK, "linewidth": 0.6})
        ax.set_title(ttl)
        ax.set_xlabel("Horizontal range a_h (m), assumed")
        ax.set_ylabel(ylab)
    ax2.set_ylim(0, 1)
    fig.suptitle("Connectivity per scenario: whiskers P10 to P90, box P25 to P75, line P50", y=0.97, fontsize=9)
    return _save(fig, "O5-F09", "connectivity_by_scenario"), len(rows)


def f10(conn, q, receipt, meta):
    scen = [s for s in _scenario_labels(conn) if s["feasibility"] == "FEASIBLE"]
    if not scen:
        raise NotSupported("no feasible scenario: run the simulate stage")
    line = conn.execute(q["section_line"], {"line": SECTION_LINE}).fetchone()
    if line is None or line["northing_m"] is None:
        raise NotSupported(f"line {SECTION_LINE} has no collars")
    counts = conn.execute("SELECT line_code, SUM(indicator) AS pos, COUNT(*) AS n FROM observations "
                          "WHERE in_binary_target = 1 GROUP BY line_code ORDER BY pos DESC").fetchone()
    nN = int(meta["n_northing"])
    iy = int(np.clip(round((line["northing_m"] - meta["origin_northing_m"]) / meta["cell_northing_m"] - 0.5), 0, nN - 1))
    logged = conn.execute(q["section_logged"], {"line": SECTION_LINE}).fetchall()
    extent = _section_extent(meta)
    fig, axes = plt.subplots(len(scen), 2, figsize=(7.4, 1.95 * len(scen) + 1.2), squeeze=False)
    fig.subplots_adjust(left=0.1, right=0.9, top=0.93, bottom=0.12, hspace=0.45, wspace=0.12)
    total = 0
    freq_im = None
    for k, s in enumerate(scen):
        rows = conn.execute(q["section_scenario"], {"scenario": s["scenario_id"], "iy": iy}).fetchall()
        total += len(rows)
        ax_r, ax_f = axes[k]
        r1 = _section_array(rows, meta, "realisation_1")
        fr = _section_array(rows, meta, "frequency")
        ax_r.imshow(np.ma.masked_invalid(r1), origin="upper", extent=extent, aspect="auto",
                    cmap=ListedColormap(["#FFFFFF", BLUE]), vmin=0, vmax=1, interpolation="nearest")
        freq_im = ax_f.imshow(np.ma.masked_invalid(fr), origin="upper", extent=extent, aspect="auto", cmap="magma",
                              vmin=0, vmax=1, interpolation="nearest")
        for ax in (ax_r, ax_f):
            ax.set_ylim(extent[2], extent[3])
            if logged:   # the simulation domain lies within 25 m of the collars, so crop to the drilled part of the line
                xs = [l["easting_m"] for l in logged]
                ax.set_xlim(min(xs) - 40.0, max(xs) + 40.0)
            ax.xaxis.set_major_formatter(KM)
            ax.xaxis.set_major_locator(MaxNLocator(4))
            ax.set_xlabel("Easting (km)")
            if logged:
                ax.scatter([l["easting_m"] for l in logged], [-l["z_relative_m"] for l in logged],
                           c=[l["indicator"] for l in logged], cmap=ListedColormap(["#FFFFFF", "#000000"]), s=1.2,
                           edgecolors=INK, linewidths=0.1, vmin=0, vmax=1)
        ax_r.set_ylabel(f"{s['scenario_id']}\na_h {s['horizontal_range_m']:g} m\nDepth (m)")
        if k == 0:
            ax_r.set_title("Realisation 1 (blue: positive; dots: logged)")
            ax_f.set_title("Frequency of positive outcomes (100)")
    fig.colorbar(freq_im, ax=axes[:, 1].tolist(), fraction=0.05, pad=0.04, label="frequency")
    fig.suptitle(f"Scenario realisations and frequency along {SECTION_LINE}", y=0.985)
    return _save(fig, "O5-F10", "realisation_and_frequency_section"), total


FIGURES = OrderedDict([
    ("O5-F01", ("Support zones in plan", "O5-F01.sql")),
    ("O5-F02", ("Probability depth slices", "O5-F02.sql")),
    ("O5-F03", ("Bootstrap interval width depth slices", "O5-F03.sql")),
    ("O5-F04", ("Model disagreement depth slices", "O5-F04.sql")),
    ("O5-F05", ("Class depth slices with weathering-front tag", "O5-F05.sql")),
    ("O5-F06", ("Along-line sections", "O5-F06.sql")),
    ("O5-F07", ("Three-dimensional view", "O5-F07.sql")),
    ("O5-F08", ("Graphitic grid volume distribution per scenario", "O5-F08.sql")),
    ("O5-F09", ("Connectivity per scenario", "O5-F09.sql")),
    ("O5-F10", ("Realisation and frequency section per scenario", "O5-F10.sql")),
])


def render_all(o5_path=None) -> dict:
    conn = connect_o5(o5_path)
    try:
        receipt = _receipt(conn)
        meta = _meta(conn)
        summary = {}
        conn.execute("DELETE FROM figure_sql_registry")
        conn.execute("DELETE FROM figure_registry")
        created = utc_now()
        sql_dir = O5_SQL_DIR / "figures"
        specs = {
            "O5-F01": ("O5-F01.sql", lambda q: f01(conn, q, receipt, meta)),
            "O5-F02": ("O5-F02.sql", lambda q: _slice_figure(conn, q, "slice_probability", receipt, meta, "O5-F02",
                                                             "probability_depth_slices",
                                                             "Probability of the selected model, depth slices",
                                                             "viridis", "p (selected)", 0, 1)),
            "O5-F03": ("O5-F03.sql", lambda q: _slice_figure(conn, q, "slice_width", receipt, meta, "O5-F03",
                                                             "interval_width_depth_slices",
                                                             "Bootstrap 90 per cent interval width, depth slices",
                                                             "magma_r", "p_hi minus p_lo", 0, 1)),
            "O5-F04": ("O5-F04.sql", lambda q: _slice_figure(conn, q, "slice_disagreement", receipt, meta, "O5-F04",
                                                             "disagreement_depth_slices",
                                                             "Model disagreement |p selected - p runner-up|",
                                                             "cividis", "disagreement", 0, 1)),
            "O5-F05": ("O5-F05.sql", lambda q: _slice_figure(conn, q, "slice_class", receipt, meta, "O5-F05",
                                                             "class_depth_slices",
                                                             "Classes at the 0.5 threshold, with weathering-front tag",
                                                             None, None, None, None, categorical=True)),
            "O5-F06": ("O5-F06.sql", lambda q: f06(conn, q, receipt, meta)),
            "O5-F07": ("O5-F07.sql", lambda q: f07(conn, q, receipt, meta)),
            "O5-F08": ("O5-F08.sql", lambda q: f08(conn, q, receipt, meta)),
            "O5-F09": ("O5-F09.sql", lambda q: f09(conn, q, receipt, meta)),
            "O5-F10": ("O5-F10.sql", lambda q: f10(conn, q, receipt, meta)),
        }
        for fid, (title, _) in FIGURES.items():
            sql_path = sql_dir / specs[fid][0]
            queries = load_queries(sql_path)
            try:
                path, n = specs[fid][1](queries)
                status, reason = "GENERATED", f"rendered from {sql_path.name}; {n} rows"
            except NotSupported as exc:
                path, n, status, reason = None, 0, "NOT_SUPPORTED", str(exc)
            caption = f"{title}. {FOOTER}"
            if fid in ("O5-F08", "O5-F09", "O5-F10"):
                caption += f" {SCENARIO_STATEMENT}"
            conn.execute("INSERT OR REPLACE INTO figure_registry (figure_id, title, status, reason, caption, created_utc) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (fid, title, status, reason, caption, created))
            for qname, text in queries.items():
                conn.execute("INSERT INTO figure_sql_registry (figure_id, query_name, sql_path, sql_sha256, params_json, "
                             "row_count) VALUES (?, ?, ?, ?, ?, ?)",
                             (fid, qname, _rel(sql_path), sha256_bytes(sql_path.read_bytes()), "{}", n))
            if path is not None:
                conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_id, sha256, "
                             "bytes, created_utc) VALUES (?, 'FIGURE', ?, ?, ?, ?)",
                             (_rel(path), fid, sha256_bytes(path.read_bytes()), path.stat().st_size, created))
            summary[fid] = {"status": status, "reason": reason, "file": _rel(path) if path else None}
        return summary
    finally:
        conn.close()

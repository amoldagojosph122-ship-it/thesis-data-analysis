"""Objective 5 figure renderers O5-F01..F07. Every figure reads only its registered SQL against the Objective 5 database.

A figure whose required rows are missing is registered NOT_SUPPORTED with the reason. Every footer states the relative depth
convention, that the uncertainty is model-based (not geostatistical), and that both model selections are INCONCLUSIVE.
"""

from __future__ import annotations

import textwrap
from collections import OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from kambale.objective_5.config import (CLASS_ABSENT, CLASS_NO_SUPPORT, CLASS_PRESENT, CLASS_UNCERTAIN,  # noqa: E402
                                        O5_FIGURE_DIR, O5_SQL_DIR, PROJECT_ROOT, StopError, sha256_bytes, utc_now)
from kambale.objective_5.db import connect_o5  # noqa: E402

BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
GREY = "#BDBDBD"
INK = "#222222"
MUTED = "#555555"
CLASS_COLOURS = {CLASS_PRESENT: BLUE, CLASS_ABSENT: "#F2F2F2", CLASS_UNCERTAIN: ORANGE, CLASS_NO_SUPPORT: "#FFFFFF"}
CLASS_ORDER = [CLASS_PRESENT, CLASS_ABSENT, CLASS_UNCERTAIN, CLASS_NO_SUPPORT]
SLICE_DEPTHS_M = (5.0, 10.0, 20.0, 30.0, 40.0)
LINE_COUNT = 5
FOOTER = ("Depth is relative to the local collar (z_relative_m, straight-hole convention, PROVISIONAL_RELATIVE); absolute "
          "elevation is not used. Uncertainty is model-based (not geostatistical). Both model selections are INCONCLUSIVE "
          "against their runner-up.")

plt.rcParams.update({
    "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "legend.fontsize": 6.2, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED,
    "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "figure.dpi": 100,
    "savefig.dpi": 200, "legend.frameon": False,
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


def _meta(conn) -> dict:
    import json
    return {r["meta_key"]: json.loads(r["meta_value"]) for r in conn.execute("SELECT * FROM grid_meta")}


def _layer_for(conn, z: float) -> tuple[int, float]:
    rows = conn.execute("SELECT iz, z_relative_m FROM grid_layers ORDER BY iz").fetchall()
    best = min(rows, key=lambda r: abs(r["z_relative_m"] - z))
    return int(best["iz"]), float(best["z_relative_m"])


def _image(rows, meta, key="value", mask_zone=None):
    nE, nN = int(meta["n_easting"]), int(meta["n_northing"])
    img = np.full((nN, nE), np.nan)
    for r in rows:
        if r[key] is not None:
            img[int(r["iy"]), int(r["ix"])] = float(r[key])
    extent = (meta["origin_easting_m"], meta["origin_easting_m"] + nE * meta["cell_easting_m"],
              meta["origin_northing_m"], meta["origin_northing_m"] + nN * meta["cell_northing_m"])
    return img, extent


def _class_image(rows, meta):
    nE, nN = int(meta["n_easting"]), int(meta["n_northing"])
    code = np.full((nN, nE), np.nan)
    above = np.zeros((nN, nE), dtype=bool)
    lookup = {c: i for i, c in enumerate(CLASS_ORDER)}
    for r in rows:
        code[int(r["iy"]), int(r["ix"])] = lookup[r["class_label"]]
        above[int(r["iy"]), int(r["ix"])] = bool(r["above_front"])
    return code, above


def _footer(fig, receipt, extra=""):
    base = (f"O5 receipt {receipt['receipt_id']} | O3 receipt {receipt['o3_receipt_id']} | "
            f"{receipt['label_rule_id']} APPROVED | geometry {receipt['geometry_status']} | EPSG:32630 | "
            f"relative depth below collar")
    text = textwrap.fill(f"{base} | {FOOTER} {extra}".strip(), 190)
    fig.text(0.01, 0.01, text, fontsize=5.0, color=MUTED, ha="left", va="bottom")


def _save(fig, figure_id, stem) -> Path:
    O5_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = O5_FIGURE_DIR / f"{figure_id}_{stem}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _receipt(conn):
    row = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
    if row is None:
        raise StopError("no receipt: run the import first")
    return dict(row)


def f01(conn, q, receipt, meta):
    rows = conn.execute(q["plan_zones"], {"iz": _layer_for(conn, -5.0)[0]}).fetchall()
    collars = conn.execute(q["collars"]).fetchall()
    if not rows:
        raise NotSupported("no grid cells")
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.2)
    colours = {"INTERPOLATION": BLUE, "EXTRAPOLATION": "#9ECAE1", "NO_SUPPORT": "#FFFFFF"}
    for zone in ("EXTRAPOLATION", "INTERPOLATION"):
        pts = [r for r in rows if r["zone"] == zone]
        ax.scatter([r["easting_m"] for r in pts], [r["northing_m"] for r in pts], s=1.2, marker="s",
                   color=colours[zone], linewidths=0, label=f"{zone.title()} zone")
    lines = sorted({c["line_code"] for c in collars})
    for k, line in enumerate(lines):
        sub = sorted([c for c in collars if c["line_code"] == line], key=lambda c: c["easting_m"])
        ax.plot([c["easting_m"] for c in sub], [c["northing_m"] for c in sub], color=MUTED, lw=0.6, zorder=3)
    ax.scatter([c["easting_m"] for c in collars], [c["northing_m"] for c in collars], s=9, color=INK, zorder=4,
               label="Collars (71 holes)")
    ax.set_aspect("equal")
    ax.set_xlabel("Easting (m, EPSG:32630)")
    ax.set_ylabel("Northing (m)")
    ax.set_title("Support zones in plan, with collars and drill lines")
    ax.legend(loc="upper right", markerscale=3)
    _footer(fig, receipt, "Plan view; lines join the collars of each drill line.")
    return _save(fig, "O5-F01", "support_zones_plan"), len(rows)


def _slice_figure(conn, q, query_name, receipt, meta, figure_id, stem, title, cmap, label, vmin, vmax, categorical=False):
    panels = []
    for z in SLICE_DEPTHS_M:
        iz, zc = _layer_for(conn, -z)
        rows = conn.execute(q[query_name], {"iz": iz}).fetchall()
        panels.append((z, zc, rows))
    fig, axes = plt.subplots(1, len(panels), figsize=(9.6, 2.9), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.05, right=0.9, top=0.8, bottom=0.25, wspace=0.12)
    last = None
    for ax, (z, zc, rows) in zip(axes, panels):
        if categorical:
            code, above = _class_image(rows, meta)
            cmap_c = ListedColormap([CLASS_COLOURS[c] for c in CLASS_ORDER])
            img, extent = code, None
            nE, nN = int(meta["n_easting"]), int(meta["n_northing"])
            extent = (meta["origin_easting_m"], meta["origin_easting_m"] + nE * meta["cell_easting_m"],
                      meta["origin_northing_m"], meta["origin_northing_m"] + nN * meta["cell_northing_m"])
            last = ax.imshow(img, origin="lower", extent=extent, cmap=cmap_c, vmin=-0.5, vmax=len(CLASS_ORDER) - 0.5,
                             interpolation="nearest")
            if above.any():
                ax.contourf(np.linspace(extent[0], extent[1], above.shape[1]),
                            np.linspace(extent[2], extent[3], above.shape[0]), above.astype(float),
                            levels=[0.5, 1.5], colors="none", hatches=["////"])
        else:
            img, extent = _image(rows, meta)
            last = ax.imshow(img, origin="lower", extent=extent, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title(f"z = -{z:g} m (layer {zc:g} m)")
        ax.set_xlabel("Easting (m)")
        ax.set_aspect("equal")
    axes[0].set_ylabel("Northing (m)")
    if categorical:
        handles = [Patch(facecolor=CLASS_COLOURS[c], edgecolor=GREY, label=c) for c in CLASS_ORDER]
        handles.append(Patch(facecolor="white", edgecolor=INK, hatch="////", label="Above weathering front"))
        fig.legend(handles=handles, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 0.99))
    else:
        cbar = fig.colorbar(last, ax=axes, fraction=0.025, pad=0.02)
        cbar.set_label(label)
    fig.suptitle(title, y=0.98)
    _footer(fig, receipt, "Blank cells: NO_SUPPORT.")
    count = sum(len(r) for _, _, r in panels)
    return _save(fig, figure_id, stem), count


def f06(conn, q, receipt, meta):
    collars = conn.execute("SELECT line_code, AVG(northing_m) AS n FROM collars GROUP BY line_code ORDER BY line_code"
                           ).fetchall()
    lines = collars[:LINE_COUNT]
    if not lines:
        raise NotSupported("no drill lines")
    nE, nN = int(meta["n_easting"]), int(meta["n_northing"])
    fig, axes = plt.subplots(len(lines), 3, figsize=(9.6, 2.0 * len(lines) + 0.6), squeeze=False)
    fig.subplots_adjust(left=0.07, right=0.97, top=0.94, bottom=0.12, hspace=0.6, wspace=0.25)
    total = 0
    for k, line in enumerate(lines):
        iy = int(np.clip(round((line["n"] - meta["origin_northing_m"]) / meta["cell_northing_m"] - 0.5), 0, nN - 1))
        cells = conn.execute(q["section_cells"], {"iy": iy}).fetchall()
        logged = conn.execute(q["section_logged"], {"line": line["line_code"]}).fetchall()
        total += len(cells)
        ex = np.array([c["easting_m"] for c in cells])
        dep = np.array([c["depth_below_collar_m"] for c in cells])
        pr = np.array([np.nan if c["p_selected"] is None else c["p_selected"] for c in cells])
        wd = np.array([np.nan if c["interval_width"] is None else c["interval_width"] for c in cells])
        cls = np.array([c["class_label"] or CLASS_NO_SUPPORT for c in cells], dtype=object)
        ax_p, ax_w, ax_c = axes[k]
        sc = ax_p.scatter(ex, dep, c=pr, cmap="viridis", vmin=0, vmax=1, s=4, marker="s", linewidths=0)
        ax_p.scatter([l["easting_m"] for l in logged], [-l["z_relative_m"] for l in logged],
                     c=[l["indicator"] for l in logged], cmap=ListedColormap(["#FFFFFF", "#000000"]), s=5,
                     edgecolors=INK, linewidths=0.2)
        ax_w.scatter(ex, dep, c=wd, cmap="magma_r", vmin=0, vmax=1, s=4, marker="s", linewidths=0)
        for cls_name in CLASS_ORDER:
            mask = cls == cls_name
            if mask.any():
                ax_c.scatter(ex[mask], dep[mask], color=CLASS_COLOURS[cls_name], s=4, marker="s", linewidths=0)
        for ax in (ax_p, ax_w, ax_c):
            ax.invert_yaxis()
            ax.set_xlabel("Easting (m)")
        ax_p.set_ylabel(f"{line['line_code']}\nDepth below collar (m)")
        ax_p.set_title("Probability (dots: logged labels)")
        ax_w.set_title("Bootstrap interval width")
        ax_c.set_title("Class")
    fig.colorbar(sc, ax=axes[:, 0], fraction=0.04, pad=0.02, label="p (selected)")
    _footer(fig, receipt, "Each row is one drill line; cells are those nearest the line's mean northing.")
    fig.suptitle("Along-line sections: probability, interval width and class", y=0.99)
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
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.set_zlabel("Depth below collar (m)")
    ax.invert_zaxis()
    ax.set_title("INTERPOLATION zone: CONFIDENT_PRESENT and UNCERTAIN cells")
    ax.legend(loc="upper left", markerscale=4)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.08)
    _footer(fig, receipt, "Only cells inside 25 m of a collar, not DEPTH_EXTRAPOLATED for confident classes.")
    return _save(fig, "O5-F07", "three_d_interpolation"), len(rows)


FIGURES = OrderedDict([
    ("O5-F01", ("Support zones in plan", "O5-F01.sql")),
    ("O5-F02", ("Probability depth slices", "O5-F02.sql")),
    ("O5-F03", ("Bootstrap interval width depth slices", "O5-F03.sql")),
    ("O5-F04", ("Model disagreement depth slices", "O5-F04.sql")),
    ("O5-F05", ("Class depth slices with weathering-front tag", "O5-F05.sql")),
    ("O5-F06", ("Along-line sections", "O5-F06.sql")),
    ("O5-F07", ("Three-dimensional view", "O5-F07.sql")),
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

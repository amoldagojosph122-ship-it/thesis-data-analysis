"""Figure and table registry: runs the SQL for each output, renders it, and records every hash in SQLite.

Outputs: figures/objective_1|2/<stem>.{svg,pdf,png} and tables/objective_1|2/<stem>.{csv,md,tex}.
A registry row is written for each SQL file (figure_query_registry) and each output (figure_export_manifest).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from kambale import figures as F
from kambale.config import CODE_VERSION, FIGURES_DIR, PROJECT_ROOT, SQL_FIGURES_DIR, TABLES_DIR
from kambale.db import connect, sha256_text, utc_now


@dataclass(frozen=True)
class Spec:
    figure_id: str
    objective: str
    kind: str
    title: str
    caption: str
    stage_status: str
    geometry_status: str
    label_status: str
    denominator: str
    sql: tuple[str, ...]


FIGURE_SPECS = {
    "F01": Spec("F01", "O1", "FIGURE", "Collar location map",
                "Collar plan with approved drill-line groups on UTM zone 30N coordinates (adopted UTM pair; "
                "alternate Easting/Northing pair differs by median 3.2 m, max 13.3 m). Background: regional "
                "1:1,000,000 polygons (context only). Scale bar 500 m. Datum WGS 84 confirmed (2026-11-05).",
                "PROVISIONAL", "plan coordinates PROVISIONAL; no RL", "not used", "71 collars (holes)",
                ("F01_collar_plan.sql", "F01_regional.sql")),
    "F02": Spec("F02", "O1", "FIGURE", "Drill-hole length distribution",
                "Distribution of drilled lengths (max_depth) for 71 holes and per approved drill line. "
                "Total 1,910 m logged at 1-m support (interval count equals metres).",
                "VERIFIED", "not used", "not used", "71 holes; 1,910 m", ("F02_hole_lengths.sql",)),
    "F03": Spec("F03", "O1", "FIGURE", "Completeness and QA/QC summary",
                "A: non-blank share of each raw field, from the stored raw payloads. B: checks with FAIL results "
                "and their flagged record counts, coloured by severity. Full list in T01 part C.",
                "VERIFIED", "not used", "not used", "rows per raw sheet (71 / 71 / 1,910)",
                ("F03_completeness.sql", "F03_qc_summary.sql")),
    "F04": Spec("F04", "O1", "FIGURE", "Three-dimensional drill traces and interval strips",
                "A: interval midpoints in 3-D with RELATIVE Z (metres below collar), coloured by strict candidate "
                "state. B: 1-m strips per hole by approved drill line. Vertical positions are not elevations; "
                "no collar RL exists in the workbook.",
                "PROVISIONAL", "relative Z only; surveyed elevation BLOCKED; DEM not drawn", "STRICT_SGS_v1 (PROPOSED)",
                "1,910 intervals; 71 holes", ("F04_3d_intervals.sql", "F04_strip_logs.sql")),
    "F05": Spec("F05", "O2", "FIGURE", "Lithology frequency and logged metres",
                "Frequency of each rock_type1 code as logged (count and metres). Grey bars are codes not in the "
                "legend or blank; these are not mapped to any meaning.",
                "VERIFIED", "not used", "codes as logged", "1,910 intervals; 1,910 m",
                ("F05_rock_usage.sql", "F05_missing_codes.sql")),
    "F06": Spec("F06", "O2", "FIGURE", "Graphitic apparent thickness and proportion by hole",
                "Strict graphitic (rock_type1 = Sgs) apparent along-hole metres by hole, with the approved "
                "Target B (DESIGN_8_2_v1) graphitic metres outlined. Denominator: logged metres per hole. Thickness is apparent, "
                "not true stratigraphic thickness. Logged indicators are not graphite assays.",
                "PROVISIONAL", "not used", "STRICT_SGS_v1 PROPOSED; DESIGN_8_2_v1 APPROVED",
                "logged metres per hole (sum 1,910 m)", ("F06_hole_graphite.sql",)),
    "F07": Spec("F07", "O2", "FIGURE", "Graphitic intervals by depth and weathering",
                "Strict graphitic intervals per 5-m measured-depth bin, stacked by weathering class. The black "
                "line gives all intervals per bin (denominator). Depth is measured depth, not elevation.",
                "PROVISIONAL", "measured depth (no elevation)", "STRICT_SGS_v1 PROPOSED",
                "all intervals per depth bin", ("F07_depth_weathering.sql",)),
    "F08": Spec("F08", "O2", "FIGURE", "Plan map of graphitic fraction",
                "Collar plan coloured by strict graphitic fraction of logged metres; marker size shows logged "
                "metres. Hollow markers: no Sgs logged. Drill-line labels are the approved nominal-Northing groups.",
                "PROVISIONAL", "plan coordinates PROVISIONAL", "STRICT_SGS_v1 PROPOSED",
                "logged metres per hole", ("F08_plan_graphite.sql", "F01_regional.sql", "F08_lines.sql")),
    "F09": Spec("F09", "O2", "FIGURE", "Relative-Z sections by drill line",
                "Holes projected onto their approved E-W drill line (all end-of-hole azimuths are 090). Points "
                "are logged 1-m midpoints with relative Z (metres from each collar). No geology is interpolated "
                "between holes. The provisional DEM collar elevations are not drawn.",
                "PROVISIONAL", "relative Z; DEM elevation not drawn", "STRICT_SGS_v1 PROPOSED",
                "1,910 intervals across 5 lines", ("F09_sections.sql",)),
}

TABLE_SPECS = {
    "T01": Spec("T01", "O1", "TABLE", "Workbook inventory, reconciliation and integrity checks",
                "Part A: sheet inventory. Part B: raw-to-curated reconciliation against ThesisDesign.docx values "
                "(comparison only). Part C: QA/QC issues. Part D: stored SQL integrity and test results.",
                "VERIFIED", "not used", "not used", "raw and curated counts",
                ("T01_inventory.sql", "T01_reconciliation.sql", "T01_qc_issues.sql", "T01_integrity.sql")),
    "T02": Spec("T02", "O1", "TABLE", "Lithological code dictionary and graphitic-evidence disagreement",
                "Part A: legend codes with usage, including unsupported codes. Part B: indicator patterns and "
                "review status. Ambiguous records are for geological review; no rule is approved.",
                "PROVISIONAL", "not used", "PROPOSED", "1,910 intervals",
                ("T02_code_dictionary.sql", "T02_label_disagreement.sql")),
    "T03": Spec("T03", "O2", "TABLE", "Graphitic-domain evidence and ambiguity by hole and drill line",
                "Part A: per hole metres for each indicator, Target B (DESIGN_8_2_v1) graphitic and ambiguous metres, unresolved metres, "
                "conflicts and unresolved codes. Part B: the same by approved drill line.",
                "PROVISIONAL", "not used", "PROPOSED", "logged metres per hole and line",
                ("T03_hole_evidence.sql", "T03_line_evidence.sql")),
    "T04": Spec("T04", "O1", "TABLE", "Trace-excluded sensitivity of the earlier candidate RECON_2OF3_v1",
                "Part A: state pairs for RECON_2OF3_v1 and its trace-excluded variant RECON_2OF3_NOTRACE_v1. "
                "Part B: intervals whose state changes, by hole. Sensitivity analysis only; both rules are PROPOSED.",
                "PROVISIONAL", "not used", "PROPOSED (sensitivity)", "logged metres per hole",
                ("T04_transitions.sql", "T04_by_hole.sql")),
}

DEFERRED_IDS = {
    "D01": ("O2", "Directional indicator variograms and anisotropy", "Stage B; needs approved label rule and training-only fitting"),
    "D02": ("O2", "Indicator semivariogram fits and variogram admissibility", "Stage B; needs validated pair support"),
    "D03": ("O3", "Indicator kriging probability maps (M1)", "Stage B; needs fitted training-only variogram"),
    "D04": ("O3", "Random Forest and XGBoost predictions (M2)", "Stage B; needs grouped spatial folds"),
    "D05": ("O3", "Hybrid ML-indicator residual model (M3)", "Stage B; needs residual variogram from training data"),
    "D06": ("O4", "Confusion matrices and threshold-based classification metrics", "Stage B; needs out-of-fold predictions"),
    "D07": ("O4", "Calibration curves and calibration intercept/slope", "Stage B; needs held-out predictions"),
    "D08": ("O4", "ROC and PR curves for model comparison", "Stage B; needs held-out predictions"),
    "D09": ("O5", "Predictive probability volumes and 3-D graphitic probability", "Stage B; needs final model and approved geometry"),
    "D10": ("O5", "Entropy maps and uncertainty volumes", "Stage B; needs probability volumes"),
    "D11": ("O5", "Sequential indicator simulation realizations", "Stage B; needs SIS validation gates"),
    "D12": ("O1", "Absolute 3-D elevation model and georeferenced volume",
            "Needs an approved collar RL, or an approved DEM method with a verified vertical datum"),
    "D13": ("O1", "Grade, tonnage or resource estimates", "Not in scope: no graphite assays or TGC in workbook"),
}


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def load_sql(name: str) -> str:
    return (SQL_FIGURES_DIR / name).read_text(encoding="utf-8")


def run_sql(conn, name: str) -> tuple[list[dict], str, list[str]]:
    text = load_sql(name)
    cursor = conn.execute(text)
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, r)) for r in cursor.fetchall()]
    return rows, sha256_text(text), columns


def _active(conn) -> tuple[int, str]:
    row = conn.execute("SELECT dataset_version_id, dataset_version_key FROM dataset_versions WHERE status = 'ACTIVE'"
                       ).fetchone()
    if row is None:
        raise RuntimeError("no ACTIVE dataset version; run `kambale build` first")
    return row[0], row[1]


def _check_version(version: str) -> None:
    if version not in ("active", None):
        raise SystemExit("only --version active is supported: obj1_master views resolve the ACTIVE version. "
                         "Re-activate an archived version by running `kambale build` on the same source.")


def _open_run(conn, command: str, dv: int, args: dict) -> int:
    return conn.execute("INSERT INTO analysis_runs (command, args_json, code_version, dataset_version_id, started_utc, "
                        "status) VALUES (?, ?, ?, ?, ?, 'RUNNING')",
                        (command, json.dumps(args, sort_keys=True), CODE_VERSION, dv, utc_now())).lastrowid


def _register(conn, spec: Spec, created: str) -> None:
    conn.execute(
        "INSERT INTO figure_registry (figure_id, objective, kind, title, caption, stage_status, geometry_status, "
        "label_status, denominator, sql_file, renderer, created_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(figure_id) DO UPDATE SET title = excluded.title, caption = excluded.caption, "
        "stage_status = excluded.stage_status, geometry_status = excluded.geometry_status, "
        "label_status = excluded.label_status, denominator = excluded.denominator, sql_file = excluded.sql_file, "
        "renderer = excluded.renderer, created_utc = excluded.created_utc",
        (spec.figure_id, spec.objective, spec.kind, spec.title, spec.caption, spec.stage_status,
         spec.geometry_status, spec.label_status, spec.denominator, ";".join(spec.sql),
         "kambale.figures", created))


def register_deferred(conn) -> None:
    created = utc_now()
    for code, (objective, title, prerequisite) in DEFERRED_IDS.items():
        conn.execute(
            "INSERT INTO figure_registry (figure_id, objective, kind, title, caption, stage_status, geometry_status, "
            "label_status, denominator, sql_file, renderer, created_utc) VALUES (?, ?, 'FIGURE', ?, ?, 'DEFERRED', "
            "'not applicable', 'not applicable', 'none (no output produced)', 'none', 'none', ?) "
            "ON CONFLICT(figure_id) DO UPDATE SET title = excluded.title, caption = excluded.caption, "
            "stage_status = 'DEFERRED', created_utc = excluded.created_utc",
            (code, objective, title, f"Deferred. Prerequisite: {prerequisite}.", created))


def _record_outputs(conn, figure_id: str, dv: int, run: int, sql_rows: dict, outputs: list[Path], module_sha: str,
                    sql_names: tuple[str, ...]) -> None:
    query_ids = {}
    for name in sql_names:
        rows, sha = sql_rows[name][0], sql_rows[name][1]
        cur = conn.execute("INSERT OR IGNORE INTO figure_query_registry (figure_id, dataset_version_id, sql_file, "
                           "sql_sha256, row_count, query_run_utc, analysis_run_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (figure_id, dv, name, sha, len(rows), utc_now(), run))
        query_ids[name] = cur.lastrowid or conn.execute(
            "SELECT figure_query_id FROM figure_query_registry WHERE figure_id = ? AND dataset_version_id = ? AND "
            "sql_sha256 = ? AND analysis_run_id = ?", (figure_id, dv, sha, run)).fetchone()[0]
    primary = query_ids[sql_names[0]]
    for path in outputs:
        fmt = path.suffix.lstrip(".").upper()
        conn.execute(
            "INSERT INTO figure_export_manifest (figure_id, output_path, output_format, output_sha256, output_bytes, "
            "dataset_version_id, figure_query_id, renderer_sha256, exported_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(figure_id, output_path) DO UPDATE SET output_format = excluded.output_format, "
            "output_sha256 = excluded.output_sha256, output_bytes = excluded.output_bytes, "
            "dataset_version_id = excluded.dataset_version_id, figure_query_id = excluded.figure_query_id, "
            "renderer_sha256 = excluded.renderer_sha256, exported_utc = excluded.exported_utc",
            (figure_id, _rel(path), fmt, _sha_file(path), path.stat().st_size, dv, primary, module_sha, utc_now()))


def _save_figure(fig, folder: Path, stem: str) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    path = folder / f"{stem}.svg"
    fig.savefig(path, metadata={"Date": None})
    out.append(path)
    path = folder / f"{stem}.pdf"
    fig.savefig(path, metadata={"CreationDate": None, "ModDate": None})
    out.append(path)
    path = folder / f"{stem}.png"
    fig.savefig(path, dpi=300, metadata={"Software": None})
    out.append(path)
    return out


def render_figures(db_path: Path, ids: list[str] | None, version: str = "active") -> dict:
    _check_version(version)
    conn = connect(db_path)
    dv, key = _active(conn)
    ids = ids or list(FIGURE_SPECS)
    unknown = [i for i in ids if i not in FIGURE_SPECS]
    if unknown:
        return {"refused": unknown, "reason": "not a Stage A figure; deferred items are listed in DEFERRED_FIGURES.md"}
    run = _open_run(conn, "plot", dv, {"figures": ids})
    module_sha = _sha_file(Path(F.__file__))
    created = utc_now()
    results = {}
    try:
        register_deferred(conn)
        for fid in ids:
            spec = FIGURE_SPECS[fid]
            sql_rows = {name: run_sql(conn, name) for name in spec.sql}
            rows = {name: sql_rows[name][0] for name in spec.sql}
            drawn = F.FIGURE_RENDERERS[fid](rows, key[:12])
            folder = FIGURES_DIR / ("objective_1" if spec.objective == "O1" else "objective_2")
            outputs = []
            for stem, fig in drawn:
                outputs.extend(_save_figure(fig, folder, stem))
                F.plt.close(fig)
            _register(conn, spec, created)
            _record_outputs(conn, fid, dv, run, sql_rows, outputs, module_sha, spec.sql)
            results[fid] = [_rel(p) for p in outputs]
        conn.execute("UPDATE analysis_runs SET finished_utc = ?, status = 'VERIFIED', message = ? "
                     "WHERE analysis_run_id = ?", (utc_now(), f"rendered {len(ids)} figure(s)", run))
    except Exception as exc:
        conn.execute("UPDATE analysis_runs SET finished_utc = ?, status = 'FAILED', message = ? "
                     "WHERE analysis_run_id = ?", (utc_now(), str(exc)[:1000], run))
        raise
    finally:
        conn.close()
    return {"dataset_version_key": key, "analysis_run_id": run, "outputs": results}


def _write_table(folder: Path, stem: str, columns: list[str], rows: list[list], caption: str) -> list[Path]:
    import csv

    folder.mkdir(parents=True, exist_ok=True)
    out = []
    csv_path = folder / f"{stem}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)
    out.append(csv_path)
    md_path = folder / f"{stem}.md"
    md = [f"**{caption}**", "", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    md += ["| " + " | ".join("" if v is None else str(v).replace("|", "/") for v in r) + " |" for r in rows]
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    out.append(md_path)
    tex_path = folder / f"{stem}.tex"
    tex = ["\\begin{table}[htbp]", "\\centering", f"\\caption{{{_tex(caption)}}}", "\\begin{tabular}{" + "l" * len(columns) + "}",
           "\\toprule", " & ".join(_tex(c) for c in columns) + " \\\\", "\\midrule"]
    tex += [" & ".join(_tex("" if v is None else str(v)) for v in r) + " \\\\" for r in rows]
    tex += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    tex_path.write_text("\n".join(tex) + "\n", encoding="utf-8")
    out.append(tex_path)
    return out


def _tex(text: str) -> str:
    for a, b in (("\\", "\\textbackslash{}"), ("&", "\\&"), ("%", "\\%"), ("_", "\\_"), ("#", "\\#"), ("$", "\\$"),
                 ("{", "\\{"), ("}", "\\}"), ("~", "\\textasciitilde{}"), ("^", "\\textasciicircum{}")):
        text = text.replace(a, b)
    return text


def render_tables(db_path: Path, version: str = "active") -> dict:
    _check_version(version)
    conn = connect(db_path)
    dv, key = _active(conn)
    run = _open_run(conn, "tables", dv, {"tables": list(TABLE_SPECS)})
    created = utc_now()
    module_sha = _sha_file(Path(__file__))
    results = {}
    try:
        for tid, spec in TABLE_SPECS.items():
            sql_rows = {name: run_sql(conn, name) for name in spec.sql}
            folder = TABLES_DIR / ("objective_1" if spec.objective == "O1" else "objective_2")
            outputs = []
            for name in spec.sql:
                rows, _, columns = sql_rows[name]
                body = [[r[c] for c in columns] for r in rows]
                stem = name.replace(".sql", "")
                outputs.extend(_write_table(folder, stem, columns, body, f"{tid}: {spec.title}"
                                            f" [{name.replace('.sql', '')}] (obj1_master {key[:12]}; PROVISIONAL "
                                            f"where labels or coordinates are used)"))
            _register(conn, spec, created)
            _record_outputs(conn, tid, dv, run, sql_rows, outputs, module_sha, spec.sql)
            results[tid] = [_rel(p) for p in outputs]
        conn.execute("UPDATE analysis_runs SET finished_utc = ?, status = 'VERIFIED', message = ? "
                     "WHERE analysis_run_id = ?", (utc_now(), f"rendered {len(TABLE_SPECS)} table(s)", run))
    except Exception as exc:
        conn.execute("UPDATE analysis_runs SET finished_utc = ?, status = 'FAILED', message = ? "
                     "WHERE analysis_run_id = ?", (utc_now(), str(exc)[:1000], run))
        raise
    finally:
        conn.close()
    return {"analysis_run_id": run, "outputs": results}

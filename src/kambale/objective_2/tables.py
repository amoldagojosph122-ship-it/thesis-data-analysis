"""Objective 2 table renderers (specification 06, section 5).

Each table is written as CSV, Markdown and LaTeX from the rows of its registered SQL file in sql/objective_2/tables/, run
against the latest receipt. A table with no rows is registered NOT_SUPPORTED with its reason and no files are written.
Numbers are formatted from the SQL result without re-computation, so the files match the database rows exactly.
"""

from __future__ import annotations

import csv
import io
from collections import OrderedDict
from pathlib import Path

from kambale.objective_2.config import O2_DB_PATH, O2_SQL_DIR, O2_TABLE_DIR, PROJECT_ROOT, StopError, sha256_bytes, utc_now
from kambale.objective_2.db import connect_o2
from kambale.objective_2.figures import load_queries

TABLES = OrderedDict([
    ("O2-T01", ("Hole and line geological summary with support", "O2_T01_hole_line_summary", "O2-T01.sql",
                "Binary counts exclude AMBIGUOUS and UNRESOLVED intervals, which are reported in their own columns. "
                "Lengths are metres, depth is relative to collar and coordinates are UTM 30N metres.")),
    ("O2-T02", ("Indicator prevalence, ambiguity and missingness by line", "O2_T02_prevalence_by_line", "O2-T02.sql",
                "Prevalence is the positive share of binary intervals. Missingness counts blank rock codes and blank "
                "weathering codes.")),
    ("O2-T03", ("Variogram fitting report", "O2_T03_variogram_fit_report", "O2-T03.sql",
                "Leave-one-line-out refits are summarised by the envelope columns. Ranges are metres; nugget and sill are "
                "indicator units; p(1 - p) is the marginal variance.")),
    ("O2-T04", ("Handoff contract and open items", "O2_T04_handoff_contract", "O2-T04.sql",
                "The handoff is for Objective 3 only. Full-data parameters are never supplied for test folds, and "
                "every open item is listed with its status.")),
    ("O2-T05", ("Weathering front continuity and interpolation check", "O2_T05_weathering_continuity", "O2-T05.sql",
                "Front = shallowest interval with weathering code mw or sw, depth in metres relative to collar. Interpolation "
                "is inverse-distance (power 2, 8 nearest holes); skill ratio = IDW RMSE / training-mean RMSE; interpolable when "
                "the ratio is at most 0.8. Configuration 5 is a sensitivity stage and writes no handoff.")),
    ("O2-T06", ("Structural-frame alignment score by apparent dip, selection-null p-value and leave-one-line-out dips",
                "O2_T06_structural_alignment", "O2-T06.sql",
                'Alignment score A(d) = 1 - mean semivariance at the first two supported bins divided by p(1 - p), for within-line between-hole pairs with |ds| at most 3 m. The selection-null p-value uses 500 circular down-hole shifts with the whole grid rescored. The DEM_ABSOLUTE frame is sensitivity only and sets no decision.')),
    ("O2-T07", ("Structural-frame fit at the selected dip and between-line report", "O2_T07_structural_fit_between_line",
                "O2-T07.sql", 'Fits use the configuration-5 rules at the selected dip. A range is STABLE only when every leave-one-line-out refit is FITTED with a range ratio between 0.5 and 2.0. The between-line report is REPORT_ONLY and carries no fit.')),
])
WIDE_TEXT = {"detail", "reason", "rationale", "projection_basis"}
TEX_SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
               "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        return "0" if text in ("", "-0") else text
    return str(value)


def _tex_escape(text: str) -> str:
    return "".join(TEX_SPECIAL.get(ch, ch) for ch in text)


def _csv(columns: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    for r in rows:
        writer.writerow([_cell(r[c]) for c in columns])
    return buf.getvalue()


def _markdown(columns: list[str], rows: list[dict], title: str, note: str, table_id: str, receipt_id: int) -> str:
    out = [f"# {table_id}. {title}", "", note, f"Source: sql/objective_2/tables/{table_id}.sql, receipt {receipt_id}, "
           f"{len(rows)} rows.", "", "| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_cell(r[c]).replace("|", "\\|") for c in columns) + " |")
    return "\n".join(out) + "\n"


def _latex(columns: list[str], rows: list[dict], title: str, note: str, table_id: str, receipt_id: int) -> str:
    spec = "".join(r"p{0.42\linewidth}" if c in WIDE_TEXT else "l" for c in columns)
    out = ["\\begin{table}[ht]", "\\centering", "\\footnotesize",
           f"\\caption{{{_tex_escape(table_id + '. ' + title)}. {_tex_escape(note)} Receipt {receipt_id}.}}",
           f"\\label{{tab:{table_id}}}", f"\\begin{{tabular}}{{{spec}}}", "\\toprule",
           " & ".join(_tex_escape(c) for c in columns) + " \\\\", "\\midrule"]
    for r in rows:
        out.append(" & ".join(_tex_escape(_cell(r[c])) for c in columns) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    return "\n".join(out)


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def render_all(o2_path=O2_DB_PATH, table_ids: list[str] | None = None) -> dict:
    conn = connect_o2(o2_path)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise StopError("no receipt: run the import first")
        rid = receipt["receipt_id"]
        created = utc_now()
        summary = {}
        for tid, (title, stem, sql_file, note) in TABLES.items():
            if table_ids and tid not in table_ids:
                continue
            sql_path = O2_SQL_DIR / "tables" / sql_file
            queries = load_queries(sql_path)
            if len(queries) != 1:
                raise StopError(f"{sql_file} must define exactly one named query")
            (query_name, text), = queries.items()
            rows = [dict(r) for r in conn.execute(text, {"receipt_id": rid}).fetchall()]
            if rows:
                status, reason = "GENERATED", "rendered from the registered query"
            else:
                status, reason = "NOT_SUPPORTED", "the registered query returned no rows for this receipt"
            conn.execute("DELETE FROM table_query_registry WHERE table_id = ?", (tid,))
            conn.execute("INSERT OR REPLACE INTO table_registry (table_id, title, status, sql_path, row_count, reason) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (tid, title, status, _rel(sql_path), len(rows), reason))
            conn.execute("INSERT INTO table_query_registry (table_id, query_name, sql_path, sql_sha256, params_json, row_count) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (tid, query_name, _rel(sql_path), sha256_bytes(sql_path.read_bytes()),
                          '{"receipt_id": %d}' % rid, len(rows)))
            if status == "NOT_SUPPORTED":
                summary[tid] = {"status": status, "reason": reason}
                continue
            columns = list(rows[0].keys())
            O2_TABLE_DIR.mkdir(parents=True, exist_ok=True)
            outputs = {
                "csv": _csv(columns, rows),
                "md": _markdown(columns, rows, title, note, tid, rid),
                "tex": _latex(columns, rows, title, note, tid, rid),
            }
            files = []
            for ext, content in outputs.items():
                path = O2_TABLE_DIR / f"{stem}.{ext}"
                path.write_text(content, encoding="utf-8", newline="\n")
                files.append(path)
                conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_sha256, "
                             "receipt_id, created_utc) VALUES (?, 'TABLE', ?, ?, ?)",
                             (_rel(path), sha256_bytes(path.read_bytes()), rid, created))
            summary[tid] = {"status": status, "row_count": len(rows), "files": [_rel(p) for p in files]}
        return summary
    finally:
        conn.close()

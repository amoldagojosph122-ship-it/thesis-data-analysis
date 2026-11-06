"""Objective 4 table renderers (CSV, Markdown and LaTeX from one registered query each)."""

from __future__ import annotations

import csv
import io
from collections import OrderedDict
from pathlib import Path

from kambale.objective_4.config import (O4_DB_PATH, O4_SQL_DIR, O4_TABLE_DIR, PROJECT_ROOT, StopError, sha256_bytes,
                                        utc_now)
from kambale.objective_4.db import connect_o4
from kambale.objective_4.figures import load_queries

TABLES = OrderedDict([
    ("O4-T01", ("Main evaluation summary", "O4_T01_evaluation_summary", "O4-T01.sql",
                "Brier is the primary endpoint; the equal-hole weighting is a sensitivity analysis. Coverage is the "
                "share of held-out intervals with a prediction. M1 has no prediction; M3 is the fallback identical to "
                "M2_RF and is not ranked.")),
    ("O4-T02", ("Fold-by-fold scores", "O4_T02_fold_scores", "O4-T02.sql",
                "Each row is one held-out line. Metrics are interval-weighted; AUC is undefined for a one-class fold "
                "and is left empty. Thresholds are the frozen Objective 3 values.")),
    ("O4-T03", ("Confusion matrices and threshold provenance", "O4_T03_confusion", "O4-T03.sql",
                "The pooled matrix sums the fold-specific confusion counts; the threshold is therefore NULL and the "
                "source records that the fold-specific thresholds were summed.")),
    ("O4-T04", ("Paired difference uncertainty and weighting sensitivity", "O4_T04_paired_uncertainty", "O4-T04.sql",
                "Sign convention: delta Brier = Brier(model_a) - Brier(model_b); negative means model_a is better. "
                "The primary interval is the 95% hole-cluster bootstrap; the line-level interval is a five-line "
                "sensitivity analysis.")),
    ("O4-T05", ("Final model-selection decision and handoff", "O4_T05_decision", "O4-T05.sql",
                "The decision policy was predeclared. An INCONCLUSIVE label means the point estimate selected the "
                "model but the uncertainty or fold consistency does not support a credible improvement claim.")),
])
WIDE_TEXT = {"reason", "notes", "definition", "detail"}
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


def _csv(columns, rows) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(columns)
    for r in rows:
        writer.writerow([_cell(r[c]) for c in columns])
    return buf.getvalue()


def _markdown(columns, rows, title, note, table_id, receipt_id) -> str:
    out = [f"# {table_id}. {title}", "", note,
           f"Source: sql/objective_4/tables/{table_id}.sql, receipt {receipt_id}, {len(rows)} rows.", "",
           "| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_cell(r[c]).replace("|", "\\|") for c in columns) + " |")
    return "\n".join(out) + "\n"


def _latex(columns, rows, title, note, table_id, receipt_id) -> str:
    spec = "".join(r"p{0.3\linewidth}" if c in WIDE_TEXT else "l" for c in columns)
    out = ["\\begin{table}[ht]", "\\centering", "\\scriptsize",
           f"\\caption{{{_tex_escape(table_id + '. ' + title)}. {_tex_escape(note)} Receipt {receipt_id}.}}",
           f"\\label{{tab:{table_id}}}", f"\\begin{{tabular}}{{{spec}}}", "\\toprule",
           " & ".join(_tex_escape(c) for c in columns) + " \\\\", "\\midrule"]
    for r in rows:
        out.append(" & ".join(_tex_escape(_cell(r[c])) for c in columns) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    return "\n".join(out)


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def render_all(o4_path=None, table_ids=None) -> dict:
    conn = connect_o4(o4_path or O4_DB_PATH)
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
            sql_path = O4_SQL_DIR / "tables" / sql_file
            queries = load_queries(sql_path)
            if len(queries) != 1:
                raise StopError(f"{sql_file} must define exactly one named query")
            (query_name, text), = queries.items()
            rows = [dict(r) for r in conn.execute(text).fetchall()]
            status = "GENERATED" if rows else "NOT_SUPPORTED"
            reason = "rendered from the registered query" if rows else "the registered query returned no rows"
            conn.execute("DELETE FROM table_sql_registry WHERE table_id = ?", (tid,))
            conn.execute("INSERT OR REPLACE INTO table_registry (table_id, title, status, row_count, reason, created_utc) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (tid, title, status, len(rows), reason, created))
            conn.execute("INSERT INTO table_sql_registry (table_id, query_name, sql_path, sql_sha256, params_json, row_count) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (tid, query_name, _rel(sql_path), sha256_bytes(sql_path.read_bytes()), "{}", len(rows)))
            if not rows:
                summary[tid] = {"status": status, "reason": reason}
                continue
            columns = list(rows[0].keys())
            O4_TABLE_DIR.mkdir(parents=True, exist_ok=True)
            outputs = {"csv": _csv(columns, rows), "md": _markdown(columns, rows, title, note, tid, rid),
                       "tex": _latex(columns, rows, title, note, tid, rid)}
            files = []
            for ext, content in outputs.items():
                path = O4_TABLE_DIR / f"{stem}.{ext}"
                path.write_text(content, encoding="utf-8", newline="\n")
                files.append(path)
                conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_id, "
                             "sha256, bytes, created_utc) VALUES (?, 'TABLE', ?, ?, ?, ?)",
                             (_rel(path), tid, sha256_bytes(path.read_bytes()), path.stat().st_size, created))
            summary[tid] = {"status": status, "row_count": len(rows), "files": [_rel(p) for p in files]}
        return summary
    finally:
        conn.close()

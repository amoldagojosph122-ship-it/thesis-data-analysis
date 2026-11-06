"""Objective 3 table renderers (specification 06, section 5).

Each table is written as CSV, Markdown and LaTeX from the single registered query in sql/objective_3/tables/. A table with
no rows is registered NOT_SUPPORTED and no files are written. Numbers are formatted from the SQL result without
re-computation.
"""

from __future__ import annotations

import csv
import io
from collections import OrderedDict
from pathlib import Path

from kambale.objective_3.config import (O3_DB_PATH, O3_SQL_DIR, O3_TABLE_DIR, PROJECT_ROOT, StopError, sha256_bytes,
                                        utc_now)
from kambale.objective_3.db import connect_o3
from kambale.objective_3.figures import load_queries

TABLES = OrderedDict([
    ("O3-T01", ("Model definitions, predictors, target version and sample support", "O3_T01_model_support", "O3-T01.sql",
                "Predictors are restricted to the three safe coordinates; target-derived and logged-only fields are listed "
                "as non-predictors. Sample support is the outer training fold, never the held-out line.")),
    ("O3-T02", ("Split-plan, fold and family hyperparameters, covariance selection and calibration diagnostics",
                "O3_T02_fit_diagnostics", "O3-T02.sql",
                "Both validation tiers are shown. Inner scores are whole-hole cross-validation log losses. The M1 and M3 "
                "covariance rows give the covariance chosen by inner CV; a pure-nugget choice carries no fitted parameter.")),
    ("O3-T03", ("Out-of-fold completeness and leakage audit, both split plans", "O3_T03_completeness_leakage",
                "O3-T03.sql",
                "Expected rows are the held-out intervals of each fold of each split plan. A completed candidate has a "
                "prediction or an explicit failure record for every held-out interval. Leakage rows are the audit log.")),
    ("O3-T04", ("Model artifact and reproducibility registry", "O3_T04_artifact_registry", "O3-T04.sql",
                "Artifacts are parameter and provenance records with a SHA-256 hash. The final full-data refit remains "
                "PENDING_O4 until Objective 4 locks model selection.")),
])
WIDE_TEXT = {"detail", "reason", "rationale", "hyperparameters_json", "item"}
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
           f"Source: sql/objective_3/tables/{table_id}.sql, receipt {receipt_id}, {len(rows)} rows.", "",
           "| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_cell(r[c]).replace("|", "\\|") for c in columns) + " |")
    return "\n".join(out) + "\n"


def _latex(columns, rows, title, note, table_id, receipt_id) -> str:
    spec = "".join(r"p{0.34\linewidth}" if c in WIDE_TEXT else "l" for c in columns)
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


def render_all(o3_path=O3_DB_PATH, table_ids: list[str] | None = None, split_plan_id: str | None = None) -> dict:
    conn = connect_o3(o3_path)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise StopError("no receipt: run the import first")
        rid = receipt["receipt_id"]
        plan = split_plan_id or conn.execute("SELECT split_plan_id FROM spatial_split_plans WHERE primary_plan = 1").fetchone()[0]
        created = utc_now()
        summary = {}
        for tid, (title, stem, sql_file, note) in TABLES.items():
            if table_ids and tid not in table_ids:
                continue
            sql_path = O3_SQL_DIR / "tables" / sql_file
            queries = load_queries(sql_path)
            if len(queries) != 1:
                raise StopError(f"{sql_file} must define exactly one named query")
            (query_name, text), = queries.items()
            rows = [dict(r) for r in conn.execute(text, {"receipt_id": rid, "split_plan_id": plan}).fetchall()]
            status = "GENERATED" if rows else "NOT_SUPPORTED"
            reason = "rendered from the registered query" if rows else "the registered query returned no rows"
            conn.execute("DELETE FROM table_sql_registry WHERE table_id = ?", (tid,))
            conn.execute("INSERT OR REPLACE INTO table_registry (table_id, title, status, row_count, reason, created_utc) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (tid, title, status, len(rows), reason, created))
            conn.execute("INSERT INTO table_sql_registry (table_id, query_name, sql_path, sql_sha256, params_json, row_count) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (tid, query_name, _rel(sql_path), sha256_bytes(sql_path.read_bytes()),
                          '{"receipt_id": %d, "split_plan_id": "%s"}' % (rid, plan), len(rows)))
            if not rows:
                summary[tid] = {"status": status, "reason": reason}
                continue
            columns = list(rows[0].keys())
            O3_TABLE_DIR.mkdir(parents=True, exist_ok=True)
            outputs = {"csv": _csv(columns, rows), "md": _markdown(columns, rows, title, note, tid, rid),
                       "tex": _latex(columns, rows, title, note, tid, rid)}
            files = []
            for ext, content in outputs.items():
                path = O3_TABLE_DIR / f"{stem}.{ext}"
                path.write_text(content, encoding="utf-8", newline="\n")
                files.append(path)
                conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_id, "
                             "sha256, bytes, created_utc) VALUES (?, 'TABLE', ?, ?, ?, ?)",
                             (_rel(path), tid, sha256_bytes(path.read_bytes()), path.stat().st_size, created))
            summary[tid] = {"status": status, "row_count": len(rows), "files": [_rel(p) for p in files]}
        return summary
    finally:
        conn.close()

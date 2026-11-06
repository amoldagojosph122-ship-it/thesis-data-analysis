"""Objective 5 table renderers O5-T01..T06 (CSV, Markdown and LaTeX from one registered query each)."""

from __future__ import annotations

import csv
import io
from collections import OrderedDict
from pathlib import Path

from kambale.objective_5.config import O5_SQL_DIR, O5_TABLE_DIR, PROJECT_ROOT, StopError, sha256_bytes, utc_now
from kambale.objective_5.db import connect_o5
from kambale.objective_5.figures import load_queries

TABLES = OrderedDict([
    ("O5-T01", ("Cell counts and relative grid volume by class, zone and depth band", "O5_T01_class_by_zone_band",
                "O5-T01.sql",
                "Volumes are relative grid volumes (cells times the cell volume in the grid metadata) in the relative "
                "frame; they are not resource volumes. Depth bands are relative depth below collar. CONFIDENT_ABSENT "
                "above the weathering front means not logged as graphitic.")),
    ("O5-T02", ("Sensitivity of the class counts to the decision threshold", "O5_T02_threshold_sensitivity",
                "O5-T02.sql",
                "HEADLINE is the configured decision threshold. SENSITIVITY_PREVALENCE applies the same rule at the "
                "training prevalence. The sensitivity table is not used in the headline classes.")),
    ("O5-T03", ("Validated skill carried from Objective 4 beside the class counts", "O5_T03_validation_with_classes",
                "O5-T03.sql",
                "Pooled interval-weighted Brier and ROC-AUC are Objective 4 values, carried without recomputation. The "
                "interval is the Objective 4 hole-cluster interval of the Brier difference (selected minus runner-up).")),
    ("O5-T04", ("Final-refit record", "O5_T04_final_refits", "O5-T04.sql",
                "Full-data fits on all binary intervals. In-sample Brier and AUC are fit diagnostics only, not validation. "
                "full_data_matches_o3_mode compares the full-data hyperparameters with the most frequent Objective 3 "
                "per-fold choice.")),
    ("O5-T05", ("Scenario simulation summary (assumed lateral range)", "O5_T05_scenario_summary", "O5-T05.sql",
                "Scenario analysis: the lateral range is assumed, not estimated, and scenarios are never pooled. Volumes are "
                "relative grid volumes of the simulated domain (INTERPOLATION, SUPPORTED cells), not resources. A scenario "
                "with a_h <= a_d cos(60) is INFEASIBLE and is not run.")),
    ("O5-T06", ("Scenario reproduction checks", "O5_T06_reproduction_checks", "O5-T06.sql",
                "Mean simulated frequency against the mean local mean over the domain (WARN above 0.05). Down-hole indicator "
                "semivariogram of realisations 1-5 against the data semivariogram on the Objective 2 lag bins; reported, not "
                "gated.")),
])
WIDE_TEXT = {"reason", "notes", "statement", "caption", "hyperparameters_json", "predictors_json", "artifact_path"}
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
           f"Source: sql/objective_5/tables/{table_id}.sql, receipt {receipt_id}, {len(rows)} rows.", "",
           "| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_cell(r[c]).replace("|", "\\|") for c in columns) + " |")
    return "\n".join(out) + "\n"


def _latex(columns, rows, title, note, table_id, receipt_id) -> str:
    spec = "".join(r"p{0.3\linewidth}" if c in WIDE_TEXT else "l" for c in columns)
    out = ["\\begin{table}[ht]", "\\centering", "\\scriptsize",
           f"\\caption{{{_tex_escape(table_id + '. ' + title)}. {_tex_escape(note)} Receipt {receipt_id}.}}",
           f"\\label{{tab:{table_id.replace('-', '')}}}", f"\\begin{{tabular}}{{{spec}}}", "\\toprule",
           " & ".join(_tex_escape(c) for c in columns) + " \\\\", "\\midrule"]
    for r in rows:
        out.append(" & ".join(_tex_escape(_cell(r[c])) for c in columns) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    return "\n".join(out)


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def render_all(o5_path=None, table_ids=None) -> dict:
    conn = connect_o5(o5_path)
    try:
        receipt = conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise StopError("no receipt: run the import first")
        rid = receipt["receipt_id"]
        created = utc_now()
        summary = {}
        conn.execute("DELETE FROM table_sql_registry")
        conn.execute("DELETE FROM table_registry")
        for tid, (title, stem, sql_file, note) in TABLES.items():
            if table_ids and tid not in table_ids:
                continue
            sql_path = O5_SQL_DIR / "tables" / sql_file
            queries = load_queries(sql_path)
            if len(queries) != 1:
                raise StopError(f"{sql_file} must define exactly one named query")
            (query_name, text), = queries.items()
            rows = [dict(r) for r in conn.execute(text).fetchall()]
            status = "GENERATED" if rows else "NOT_SUPPORTED"
            reason = "rendered from the registered query" if rows else "the registered query returned no rows"
            conn.execute("INSERT OR REPLACE INTO table_registry (table_id, title, status, row_count, reason, created_utc) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (tid, title, status, len(rows), reason, created))
            conn.execute("INSERT INTO table_sql_registry (table_id, query_name, sql_path, sql_sha256, params_json, row_count) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (tid, query_name, _rel(sql_path), sha256_bytes(sql_path.read_bytes()), "{}", len(rows)))
            if not rows:
                summary[tid] = {"status": status, "reason": reason}
                continue
            columns = list(rows[0].keys())
            O5_TABLE_DIR.mkdir(parents=True, exist_ok=True)
            outputs = {"csv": _csv(columns, rows), "md": _markdown(columns, rows, title, note, tid, rid),
                       "tex": _latex(columns, rows, title, note, tid, rid)}
            files = []
            for ext, content in outputs.items():
                path = O5_TABLE_DIR / f"{stem}.{ext}"
                path.write_text(content, encoding="utf-8", newline="\n")
                files.append(path)
                conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_id, "
                             "sha256, bytes, created_utc) VALUES (?, 'TABLE', ?, ?, ?, ?)",
                             (_rel(path), tid, sha256_bytes(path.read_bytes()), path.stat().st_size, created))
            summary[tid] = {"status": status, "row_count": len(rows), "files": [_rel(p) for p in files]}
        return summary
    finally:
        conn.close()

"""Mode B: regenerate every analysis output from the copied repository and compare it with the original outputs.

Method
  1. Copy the repository (same exclusions as gates).
  2. In the copy, delete the Objective 2, 3, 4 (both tiers) and 5 databases, and every file under figures/ and tables/
     (all objectives). The reports/ folders are kept.
  3. Run the pipeline in order, each step as a subprocess in the copy with its own log file:
       O1 plot --all, O1 tables (O1 verify runs last: it runs the full test suite, which needs every database)
       O2 all, O3 all, O4 tier 1 all, O4 tier 2 all, O5 all
     Each `all` command imports its inputs from the databases built earlier in the same run.
  4. Stop at the first non-zero exit code and report it.
  5. Compare every CSV under the real tables/ folder with the copy's file at the same path, and list the figure
     files that exist in the copy after the run.

Scope of the Objective 1 database
  The Objective 1 database (kambale_thesis.sqlite) is KEPT in the copy and is not rebuilt from the raw workbook. Its
  supervisor approvals are recorded in it as human decisions (label rule, coordinate pair, datum, drill-line groups,
  DEM choice). A rebuild would discard them, so the reproduction covers the analysis from Objective 1's approved state
  onward. Objective 1's figures and tables are regenerated from that database.

Known limits
  - reports/objective_2/PYTEST_OUTPUT.txt and reports/objective_3/PYTEST_OUTPUT.txt are not regenerated; the reports
    use the recorded files in the copy.
  - The comparison is value-level. Volatile columns (timestamps, hashes, run identifiers, paths, durations) may differ
    and are reported as IDENTICAL_EXCEPT_VOLATILE rather than DIFFERENT.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

from kambale.notebook._copy import copy_env, copy_repo, in_copy, run_command
from kambale.notebook.gates import _remove_tree
from kambale.notebook.paths import DB_PATHS, FIGURES_DIR, PROJECT_ROOT, TABLES_DIR

VOLATILE_PATTERN = re.compile(
    r"_utc$|utc|sha256|hash|receipt|runtime|seconds|elapsed|duration|code_commit|created|started|finished|"
    r"timestamp|artifact|path$",
    re.IGNORECASE,
)

STEP_COLUMNS = ["step", "command", "seconds", "exit_code", "log"]
TABLE_COLUMNS = ["objective", "table_file", "rows_original", "rows_reproduced", "status", "differing_columns"]
FIGURE_COLUMNS = ["objective", "figure_id", "file", "regenerated"]
OK_STATUSES = ("IDENTICAL", "IDENTICAL_EXCEPT_VOLATILE")

SCOPE_NOTE = (
    "Objective 1 master database kept, not rebuilt from the raw workbook: its supervisor approvals (label rule, "
    "coordinate pair, datum, drill-line groups, DEM choice) are recorded in it as human decisions. Objective 1 figures "
    "and tables are regenerated from that database; Objectives 2 to 5 are regenerated from their inputs."
)

# step name, arguments after `python`
PIPELINE = [
    ("O1 figures (plot --all)", ["-m", "kambale.cli", "--db", "database/kambale_thesis.sqlite", "plot", "--all"]),
    ("O1 tables", ["-m", "kambale.cli", "--db", "database/kambale_thesis.sqlite", "tables"]),
    ("O2 all", ["-m", "kambale.objective_2", "all"]),
    ("O3 all", ["-m", "kambale.objective_3", "all"]),
    ("O4 tier 1 all", ["-m", "kambale.objective_4", "--tier", "1", "all"]),
    ("O4 tier 2 all", ["-m", "kambale.objective_4", "--tier", "2", "all"]),
    ("O5 all", ["-m", "kambale.objective_5", "all"]),
    # O1 verify runs the whole pytest suite, which needs every objective database, so it goes last.
    ("O1 verify", ["-m", "kambale.cli", "--db", "database/kambale_thesis.sqlite", "verify"]),
]

DATABASES_TO_DELETE = ("o2", "o3", "o4_t1", "o4_t2", "o5")


def is_volatile(column: str) -> bool:
    return bool(VOLATILE_PATTERN.search(str(column)))


def _values_equal(a: pd.Series, b: pd.Series, rtol: float, atol: float) -> bool:
    if len(a) != len(b):
        return False
    numeric = pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b)
    if numeric:
        x = a.to_numpy(dtype=float)
        y = b.to_numpy(dtype=float)
        return bool(np.all(np.isclose(x, y, rtol=rtol, atol=atol, equal_nan=True)))
    return all(_text(p) == _text(q) for p, q in zip(a, b))


def _text(value) -> str:
    return "<NA>" if pd.isna(value) else str(value)


def compare_tables(original: pd.DataFrame, reproduced: pd.DataFrame, rtol: float = 1e-9,
                   atol: float = 1e-12) -> tuple[str, list[str]]:
    """Classify the difference between two tables.

    Returns (status, differing_columns). Status is IDENTICAL, IDENTICAL_EXCEPT_VOLATILE (only volatile columns differ)
    or DIFFERENT (any analysis column differs, or the columns or row counts differ). Floats compare with rtol and atol.
    """
    if list(original.columns) != list(reproduced.columns):
        diff = sorted(set(original.columns) ^ set(reproduced.columns), key=str)
        return "DIFFERENT", [str(c) for c in diff] or ["COLUMN_ORDER"]
    if len(original) != len(reproduced):
        return "DIFFERENT", ["ROW_COUNT"]
    hard: list[str] = []
    volatile: list[str] = []
    for col in original.columns:
        if _values_equal(original[col], reproduced[col], rtol, atol):
            continue
        (volatile if is_volatile(col) else hard).append(str(col))
    if hard:
        return "DIFFERENT", hard
    if volatile:
        return "IDENTICAL_EXCEPT_VOLATILE", volatile
    return "IDENTICAL", []


def _objective_of(path: Path, root: Path) -> str:
    rel = path.relative_to(root).parts
    folder = rel[1] if len(rel) > 1 else ""
    match = re.match(r"objective_(\d)", folder)
    label = f"O{match.group(1)}" if match else folder
    if len(rel) > 2 and rel[2] in ("tier_1", "tier_2"):
        label += f" tier {rel[2][-1]}"
    return label


def _delete_outputs(copy_root: Path) -> list[str]:
    removed = []
    for key in DATABASES_TO_DELETE:
        target = in_copy(copy_root, DB_PATHS[key])
        if target.exists():
            target.unlink()
            removed.append(target.name)
    for folder in (in_copy(copy_root, FIGURES_DIR), in_copy(copy_root, TABLES_DIR)):
        if folder.exists():
            for file in folder.rglob("*"):
                if file.is_file():
                    file.unlink()
                    removed.append(file.relative_to(copy_root).as_posix())
    return removed


def _run_pipeline(copy_root: Path, logs: Path, log) -> list[dict]:
    env = copy_env(copy_root)
    steps = []
    for i, (name, args) in enumerate(PIPELINE, start=1):
        log(f"[{i}/{len(PIPELINE)}] {name} ...")
        result = run_command(args, copy_root, env)
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        log_path = logs / f"{i:02d}_{slug}.log"
        log_path.write_text(f"$ python {' '.join(args)}\nexit code {result['exit_code']}\n\n"
                            f"--- stdout ---\n{result['stdout']}\n--- stderr ---\n{result['stderr']}\n",
                            encoding="utf-8")
        steps.append({"step": name, "command": "python " + " ".join(args), "seconds": result["seconds"],
                      "exit_code": result["exit_code"], "log": log_path.relative_to(copy_root).as_posix()})
        log(f"    exit {result['exit_code']} in {result['seconds']} s")
        if result["exit_code"] != 0:
            log(f"    stopped: {name} exited with code {result['exit_code']}")
            break
    return steps


def _compare_tables(copy_root: Path) -> pd.DataFrame:
    rows = []
    for original in sorted(TABLES_DIR.rglob("*.csv")):
        rel = original.relative_to(PROJECT_ROOT).as_posix()
        reproduced_path = in_copy(copy_root, original)
        objective = _objective_of(original, PROJECT_ROOT)
        if not reproduced_path.exists():
            rows.append({"objective": objective, "table_file": rel, "rows_original": len(pd.read_csv(original)),
                         "rows_reproduced": None, "status": "MISSING", "differing_columns": ""})
            continue
        try:
            a = pd.read_csv(original)
            b = pd.read_csv(reproduced_path)
        except Exception as exc:
            rows.append({"objective": objective, "table_file": rel, "rows_original": None, "rows_reproduced": None,
                         "status": "DIFFERENT", "differing_columns": f"UNREADABLE: {type(exc).__name__}"})
            continue
        status, columns = compare_tables(a, b)
        rows.append({"objective": objective, "table_file": rel, "rows_original": len(a), "rows_reproduced": len(b),
                     "status": status, "differing_columns": "; ".join(columns)})
    return pd.DataFrame(rows, columns=TABLE_COLUMNS)


def _figures(copy_root: Path) -> pd.DataFrame:
    rows = []
    for original in sorted(FIGURES_DIR.rglob("*")):
        if not original.is_file() or original.suffix.lower() not in (".svg", ".png", ".pdf"):
            continue
        rel = original.relative_to(PROJECT_ROOT).as_posix()
        objective = _objective_of(original, PROJECT_ROOT)
        if re.match(r"F\d\d_", original.name):
            objective = "O1"  # Objective 1 figures F05 to F09 sit in figures/objective_2
        rows.append({"objective": objective, "figure_id": original.stem, "file": rel,
                     "regenerated": "yes" if in_copy(copy_root, original).exists() else "no"})
    return pd.DataFrame(rows, columns=FIGURE_COLUMNS)


def _verdict(steps: list[dict], tables: pd.DataFrame) -> str:
    failed = [s for s in steps if s["exit_code"] != 0]
    if failed:
        return (f"Not reproduced: step '{failed[0]['step']}' exited with code {failed[0]['exit_code']}; "
                "see its log in _reproduce_logs.")
    if len(steps) < len(PIPELINE):
        return "Not reproduced: the pipeline did not run to the end."
    total = len(tables)
    ok = int(tables["status"].isin(OK_STATUSES).sum()) if total else 0
    volatile = int((tables["status"] == "IDENTICAL_EXCEPT_VOLATILE").sum()) if total else 0
    text = f"Reproduced: {ok} of {total} tables identical in every analysis value"
    if volatile:
        text += f" ({volatile} differ only in volatile columns such as timestamps or hashes)"
    if ok < total:
        text += f"; {total - ok} differ or are missing"
    return text + "."


def reproduce(workdir: Path | None = None, keep: bool = True, log=print) -> dict:
    """Regenerate all outputs in a copy and compare them with the original tables.

    workdir is the copy's root: created when missing, must be empty when present; None creates a folder under the
    system temp directory. keep=True (default) leaves the copy and its _reproduce_logs folder in place.
    Returns a dict with keys workdir, steps, tables, figures, verdict and scope_note.
    """
    if workdir is None:
        workdir = Path(tempfile.mkdtemp(prefix="kambale_reproduce_"))
    copy_root = copy_repo(Path(workdir))
    logs = copy_root / "_reproduce_logs"
    logs.mkdir(exist_ok=True)
    try:
        removed = _delete_outputs(copy_root)
        log(f"deleted {len(removed)} database and output files in the copy")
        start = time.time()
        steps = _run_pipeline(copy_root, logs, log)
        log(f"pipeline finished in {round(time.time() - start, 1)} s")
        steps_frame = pd.DataFrame(steps, columns=STEP_COLUMNS)
        tables = _compare_tables(copy_root)
        figures = _figures(copy_root)
        verdict = _verdict(steps, tables)
        return {"workdir": copy_root, "steps": steps_frame, "tables": tables, "figures": figures,
                "verdict": verdict, "scope_note": SCOPE_NOTE}
    finally:
        if not keep:
            _remove_tree(copy_root)

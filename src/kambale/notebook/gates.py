"""Mode A: run every objective's verify command on a copy of the repository and collect the gate results.

Why a copy: each verify command writes its results into its own database, so running it in the real repository would
change the database hashes that downstream receipts record. Running in a copy leaves the real files untouched.

Why this order: downstream first (O5, O4 tier 2, O4 tier 1, O3, O2, O1). Each verify rewrites only its own database.
O5's gate G01 compares the O2, O3, O4 tier 1 and tier 2 and thesis database files with the hashes recorded when O5 was
imported, so O5 must verify before any upstream verify changes those files. Each upstream verify then runs only after
every downstream verify that reads its database has finished. The Objective 1 verify runs last and also runs the pytest
suite of the copy.

Gate rows come from gate_results (Objectives 2 to 5, selected by the run id the verify command reports) and from
validation_test_results (Objective 1, the rows written by that verify call).
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from kambale.notebook._copy import copy_env, copy_repo, in_copy, run_command
from kambale.notebook.paths import DB_PATHS
from kambale.notebook.readonly import connect_ro

GATE_COLUMNS = ["objective", "gate_id", "name", "status", "detail"]
OBJECTIVE_ORDER = ["O1", "O2", "O3", "O4 tier 1", "O4 tier 2", "O5"]
RUN_ORDER = ["o5", "o4_t2", "o4_t1", "o3", "o2", "o1"]  # downstream first; see module docstring

# key, objective label, arguments after `python`
VERIFY_STEPS = {
    "o5": ("O5", ["-m", "kambale.objective_5", "verify"]),
    "o4_t2": ("O4 tier 2", ["-m", "kambale.objective_4", "--tier", "2", "verify"]),
    "o4_t1": ("O4 tier 1", ["-m", "kambale.objective_4", "--tier", "1", "verify"]),
    "o3": ("O3", ["-m", "kambale.objective_3", "verify"]),
    "o2": ("O2", ["-m", "kambale.objective_2", "verify"]),
    "o1": ("O1", ["-m", "kambale.cli", "--db", "database/kambale_thesis.sqlite", "verify"]),
}


def _parse_json(stdout: str) -> dict | None:
    """The verify commands print one JSON object whose first line starts with '{'."""
    match = re.search(r"^\{", stdout, re.MULTILINE)
    if match is None:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(stdout[match.start():])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _gate_rows_from_db(db_path: Path, run_id: int, objective: str) -> list[dict]:
    conn = connect_ro(db_path)
    try:
        rows = conn.execute("SELECT gate_id, gate_name, status, detail FROM gate_results WHERE run_id = ? "
                            "ORDER BY gate_id", (run_id,)).fetchall()
    finally:
        conn.close()
    return [{"objective": objective, "gate_id": r["gate_id"], "name": r["gate_name"], "status": r["status"],
             "detail": r["detail"]} for r in rows]


def _max_rowid(db_path: Path) -> int:
    conn = connect_ro(db_path)
    try:
        return conn.execute("SELECT COALESCE(MAX(rowid), 0) FROM validation_test_results").fetchone()[0]
    finally:
        conn.close()


def _o1_rows(db_path: Path, after_rowid: int, objective: str, result: dict) -> list[dict]:
    conn = connect_ro(db_path)
    try:
        rows = conn.execute("SELECT rowid, test_group, test_name, expected, observed, outcome, detail "
                            "FROM validation_test_results WHERE rowid > ? ORDER BY rowid", (after_rowid,)).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        detail = f"expected {r['expected']}; observed {r['observed']}"
        if r["detail"]:
            detail += f"; {r['detail']}"
        out.append({"objective": objective, "gate_id": r["test_group"], "name": r["test_name"],
                    "status": r["outcome"], "detail": detail})
    failures = result.get("failures")
    out.append({"objective": objective, "gate_id": "O1-FAILURES", "name": "failures counted by verify",
                "status": "PASS" if failures == 0 else "FAIL",
                "detail": f"failures={failures}; pytest={result.get('pytest')}"})
    return out


def run_verify_steps(copy_root: Path, env: dict) -> tuple[list[dict], list[dict]]:
    """Run the six verify commands in RUN_ORDER inside copy_root. Returns (gate rows, step records)."""
    rows: list[dict] = []
    steps: list[dict] = []
    for key in RUN_ORDER:
        label, args = VERIFY_STEPS[key]
        db_copy = in_copy(copy_root, DB_PATHS[key])
        before = _max_rowid(db_copy) if key == "o1" else None
        result = run_command(args, copy_root, env)
        steps.append({"objective": label, "command": "python " + " ".join(args), "seconds": result["seconds"],
                      "exit_code": result["exit_code"]})
        parsed = _parse_json(result["stdout"])
        if parsed is None:
            tail = (result["stderr"] or result["stdout"])[-800:]
            rows.append({"objective": label, "gate_id": "STEP", "name": "verify command produced no JSON result",
                         "status": "ERROR", "detail": f"exit {result['exit_code']}: {tail}"})
            continue
        if key == "o1":
            rows.extend(_o1_rows(db_copy, before, label, parsed))
            continue
        run_id = (parsed.get("verify") or {}).get("run_id")
        if run_id is None:
            rows.append({"objective": label, "gate_id": "STEP", "name": "no run id in verify output",
                         "status": "ERROR", "detail": f"exit {result['exit_code']}"})
        else:
            rows.extend(_gate_rows_from_db(db_copy, run_id, label))
    return rows, steps


def _remove_tree(root: Path) -> None:
    """Delete a working copy; on Windows clear read-only flags and retry once, since locked files can linger."""
    import os, stat, time

    def _onerror(func, path, _exc):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass

    for _ in range(2):
        shutil.rmtree(root, onerror=_onerror)
        if not Path(root).exists():
            return
        time.sleep(2)


def run_gates(workdir: Path | None = None, keep: bool = False) -> pd.DataFrame:
    """Run the six verify commands on a copy of the repository and return one row per gate.

    workdir is the copy's root folder: created when missing, must be empty when present. When workdir is None a fresh
    folder is created under the system temp directory. With keep=False the copy folder is deleted at the end; with
    keep=True it is left in place. The step records (command, seconds, exit code) are kept in frame.attrs["steps"].
    """
    if workdir is None:
        workdir = Path(tempfile.mkdtemp(prefix="kambale_gates_"))
    copy_root = copy_repo(Path(workdir))
    try:
        rows, steps = run_verify_steps(copy_root, copy_env(copy_root))
        frame = pd.DataFrame(rows, columns=GATE_COLUMNS)
        frame["_order"] = frame["objective"].map({label: i for i, label in enumerate(OBJECTIVE_ORDER)})
        frame = frame.sort_values(["_order", "gate_id"], kind="stable").drop(columns="_order").reset_index(drop=True)
        frame.attrs["steps"] = steps
        frame.attrs["copy_root"] = str(copy_root)
        return frame
    finally:
        if not keep:
            _remove_tree(copy_root)

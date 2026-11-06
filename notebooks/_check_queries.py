#!/usr/bin/env python
"""Test every SQL query and every code cell of the results notebook without the helper package.

The check imports the cell list from build_notebook.py, then executes the code cells in order against the real
databases. Queries run through a local read-only wrapper (sqlite3 with uri mode=ro). The helper functions of
kambale.notebook (environment, gates, receipts, reproduce) are replaced by stubs, so this check does not depend on
their implementation; they are tested when the notebook itself is executed.

Usage:
    python notebooks/_check_queries.py [--log PATH]

The log (default: the system temporary folder) records each query's shape and first rows, so that the numbers can be
reviewed. Exit status is 1 when any code cell raises.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
import traceback
import types
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import build_notebook  # noqa: E402  (the cell list is defined at import time; nothing is written)

DB = {
    "o1": REPO / "database" / "kambale_thesis.sqlite",
    "o2": REPO / "database" / "kambale_obj2_spatial.sqlite",
    "o3": REPO / "database" / "kambale_obj3_models.sqlite",
    "o4_t1": REPO / "database" / "kambale_obj4_validation.sqlite",
    "o4_t2": REPO / "database" / "kambale_obj4_validation_tier2.sqlite",
    "o5": REPO / "database" / "kambale_obj5_uncertainty.sqlite",
}
FIGURES = {
    "o1": REPO / "figures" / "objective_1",
    "o2": REPO / "figures" / "objective_2",
    "o3": REPO / "figures" / "objective_3",
    "o4_t1": REPO / "figures" / "objective_4" / "tier_1",
    "o4_t2": REPO / "figures" / "objective_4" / "tier_2",
    "o5": REPO / "figures" / "objective_5",
}

LOG_ROWS: list[str] = []
DISPLAY_LOG: list[str] = []
QUERY_COUNT = {"n": 0}


def ro_query(key: str, sql: str) -> pd.DataFrame:
    """Read-only query. The connection is opened with mode=ro and nothing is written."""
    if key not in DB:
        raise KeyError(f"unknown database key {key!r}")
    uri = "file:" + DB[key].as_posix() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        frame = pd.read_sql_query(sql, conn)
    QUERY_COUNT["n"] += 1
    head = " ".join(sql.split())[:110]
    LOG_ROWS.append(f"## [{key}] rows={len(frame)} cols={len(frame.columns)} :: {head}")
    LOG_ROWS.append(frame.head(12).to_string(index=False, max_colwidth=60))
    LOG_ROWS.append("")
    return frame


def build_stub_package(real_helpers: bool = False) -> None:
    """Register kambale.notebook.* stand-ins so that the notebook imports resolve during this check.

    With real_helpers=True the real paths, readonly, env and receipts modules are used; run_gates and reproduce are
    always stubbed here because they copy the repository and rerun the pipelines (about an hour for reproduce).
    """
    try:
        import IPython.display  # noqa: F401  (available in any Jupyter environment)
    except ImportError:
        ipy = types.ModuleType("IPython")
        disp = types.ModuleType("IPython.display")

        class _Obj:
            def __init__(self, data=None, **kwargs):
                self.data = data
                DISPLAY_LOG.append(f"[{type(self).__name__}] {data}")

            def __repr__(self):
                return f"<{type(self).__name__}: {str(self.data)[:60]!r}>"

        disp.Markdown = type("Markdown", (_Obj,), {})
        disp.HTML = type("HTML", (_Obj,), {})
        disp.Image = type("Image", (_Obj,), {})
        disp.display = lambda *objs, **kwargs: [print(o if isinstance(o, (str, int, float)) else repr(o)[:200])
                                                for o in objs]
        ipy.display = disp
        sys.modules["IPython"] = ipy
        sys.modules["IPython.display"] = disp
    pkg = types.ModuleType("kambale.notebook")
    paths = types.ModuleType("kambale.notebook.paths")
    paths.DB_PATHS = {k: v for k, v in DB.items()}
    paths.OUTPUT_DIRS = {k: {"figures": v, "tables": v, "reports": v} for k, v in FIGURES.items()}
    paths.CONFIG_FILES = {}
    readonly = types.ModuleType("kambale.notebook.readonly")
    readonly.query = ro_query
    readonly.list_tables = lambda key: []
    env = types.ModuleType("kambale.notebook.env")
    env.environment_summary = lambda: {"python": sys.version.split()[0], "note": "stub in _check_queries"}
    env.config_receipts = lambda: pd.DataFrame(columns=["config", "committed"])
    env.database_manifest_check = lambda: pd.DataFrame(columns=["database", "status"])
    receipts = types.ModuleType("kambale.notebook.receipts")
    receipts.receipt_check = lambda: pd.DataFrame(columns=["receipt", "status"])
    gates = types.ModuleType("kambale.notebook.gates")
    gates.run_gates = lambda: pd.DataFrame(columns=["objective", "gate_id", "name", "status", "detail"])
    reproduce_mod = types.ModuleType("kambale.notebook.reproduce")
    reproduce_mod.reproduce = lambda: {"workdir": "", "steps": [], "tables": [], "figures": [],
                                       "verdict": "not run in _check_queries", "scope_note": ""}
    stubs = {
        "kambale.notebook": pkg, "kambale.notebook.paths": paths, "kambale.notebook.readonly": readonly,
        "kambale.notebook.env": env, "kambale.notebook.receipts": receipts, "kambale.notebook.gates": gates,
        "kambale.notebook.reproduce": reproduce_mod,
    }
    if real_helpers:
        # The real modules are imported by the notebook itself; only the slow steps stay stubbed.
        sys.path.insert(0, str(REPO / "src"))
        for name in ("kambale.notebook", "kambale.notebook.paths", "kambale.notebook.readonly",
                     "kambale.notebook.env", "kambale.notebook.receipts"):
            stubs.pop(name)
    for name, module in stubs.items():
        sys.modules[name] = module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_log = Path(tempfile.gettempdir()) / "kambale_check_queries.log"
    parser.add_argument("--log", default=str(default_log), help="where to write the query log")
    parser.add_argument("--real-helpers", action="store_true",
                        help="use the real kambale.notebook paths, readonly, env and receipts modules")
    args = parser.parse_args()

    missing = [k for k, p in DB.items() if not p.exists()]
    if missing:
        print("missing databases:", missing)
        return 1
    build_stub_package(real_helpers=args.real_helpers)

    namespace: dict = {"__name__": "__notebook_check__"}
    failures: list[str] = []
    for index, (kind, source, tags) in enumerate(build_notebook.CELLS):
        if kind != "code":
            continue
        if "parameters" in tags:
            exec(compile(source, f"<cell {index}>", "exec"), namespace)
            namespace["RUN_GATES"] = False  # gates are slow; the full run is done when the notebook is executed
            namespace["MODE"] = "present"
            continue
        first = source.strip().splitlines()[0][:70]
        try:
            exec(compile(source, f"<cell {index}>", "exec"), namespace)
        except Exception as exc:  # report every failing cell, then continue with the next
            failures.append(f"cell {index} ({first}): {type(exc).__name__}: {exc}")
            LOG_ROWS.append(f"!! cell {index} failed: {exc}")
            LOG_ROWS.append(traceback.format_exc(limit=3))

    Path(args.log).write_text("\n".join(LOG_ROWS) + "\n\n==== rendered Markdown and HTML ====\n"
                              + "\n\n".join(DISPLAY_LOG), encoding="utf-8")
    print(f"code cells checked: {sum(1 for k, _, _ in build_notebook.CELLS if k == 'code')}")
    print(f"read-only queries executed: {QUERY_COUNT['n']}")
    print(f"log written: {args.log}")
    if failures:
        print("FAILED CELLS:")
        for line in failures:
            print("  -", line)
        return 1
    print("all code cells ran without error")
    return 0


if __name__ == "__main__":
    sys.exit(main())

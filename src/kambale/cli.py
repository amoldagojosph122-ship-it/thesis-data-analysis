"""Command-line entry point: `python -m kambale.cli <command>` or `kambale <command>`.

Commands
  build                 Run the transactional ETL from data/raw/ into database/kambale_thesis.sqlite.
  verify                Run SQL integrity, reconciliation and figure-provenance checks; store results.
  plot --figure ID      Render one figure (F01..F09) from the active version. `--all` renders every Stage A figure.
  tables                Render T01..T03 (CSV, Markdown, LaTeX).
  report                Write reports/QAQC_REPORT.md, FIGURE_MANIFEST.csv, DEFERRED_FIGURES.md, data/derived CSVs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kambale.config import DB_PATH


def _cmd_build(args) -> int:
    from kambale.build import build

    summary = build(db_path=Path(args.db))
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def _cmd_verify(args) -> int:
    from kambale.verify import run_verification

    result = run_verification(Path(args.db))
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result["failures"] == 0 else 1


def _cmd_plot(args) -> int:
    from kambale.registry import render_figures

    ids = None if args.all else [args.figure]
    if not args.all and not args.figure:
        print("error: give --figure ID or --all", file=sys.stderr)
        return 2
    results = render_figures(Path(args.db), ids, version=args.version)
    print(json.dumps(results, indent=2, sort_keys=True, default=str))
    return 0


def _cmd_tables(args) -> int:
    from kambale.registry import render_tables

    results = render_tables(Path(args.db), version=args.version)
    print(json.dumps(results, indent=2, sort_keys=True, default=str))
    return 0


def _cmd_report(args) -> int:
    from kambale.reports import write_reports

    results = write_reports(Path(args.db))
    print(json.dumps(results, indent=2, sort_keys=True, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kambale", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(DB_PATH), help="path to obj1_master SQLite file")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="run the ETL (idempotent)").set_defaults(func=_cmd_build)
    sub.add_parser("verify", help="run integrity and reconciliation checks").set_defaults(func=_cmd_verify)

    plot = sub.add_parser("plot", help="render Stage A figures from SQLite")
    plot.add_argument("--figure", help="figure ID, e.g. F06")
    plot.add_argument("--all", action="store_true", help="render every Stage A figure")
    plot.add_argument("--version", default="active", help="dataset version: 'active' (default) or a version key prefix")
    plot.set_defaults(func=_cmd_plot)

    tables = sub.add_parser("tables", help="render T01..T03")
    tables.add_argument("--version", default="active")
    tables.set_defaults(func=_cmd_tables)

    sub.add_parser("report", help="write reports and manifests").set_defaults(func=_cmd_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

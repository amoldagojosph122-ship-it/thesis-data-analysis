"""Command-line entry point for the notebook helpers.

  python -m kambale.notebook gates [--workdir DIR] [--no-keep]
  python -m kambale.notebook reproduce [--workdir DIR] [--no-keep]

Both commands run on a copy of the repository (never on the real databases or outputs). --workdir names the copy's
folder (created when missing, must be empty when present). By default the copy is kept and the CSV summaries are
written to <workdir>/_reproduce_summary/. --no-keep deletes the copy at the end and only prints the results.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path


def _summary_dir(workdir: Path) -> Path:
    folder = workdir / "_reproduce_summary"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _cmd_gates(args) -> int:
    from kambale.notebook.gates import run_gates

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="kambale_gates_"))
    frame = run_gates(workdir=workdir, keep=not args.no_keep)
    pd_print(frame)
    for step in frame.attrs.get("steps", []):
        print(f"  {step['objective']}: exit {step['exit_code']} in {step['seconds']} s  ({step['command']})")
    if not args.no_keep:
        frame.to_csv(_summary_dir(workdir) / "gates.csv", index=False)
        print(f"\ncopy kept at {workdir}; summary written to {workdir / '_reproduce_summary' / 'gates.csv'}")
    return 0 if not (frame["status"] == "ERROR").any() else 1


def _cmd_reproduce(args) -> int:
    from kambale.notebook.reproduce import reproduce

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="kambale_reproduce_"))
    result = reproduce(workdir=workdir, keep=not args.no_keep, log=lambda m: print(m, flush=True))
    print()
    print("STEPS")
    pd_print(result["steps"])
    print("\nTABLES")
    pd_print(result["tables"])
    print(f"\nFIGURES: {int((result['figures']['regenerated'] == 'yes').sum())} of {len(result['figures'])} "
          "figure files regenerated")
    print(f"\nSCOPE: {result['scope_note']}")
    print(f"\nVERDICT: {result['verdict']}")
    if not args.no_keep:
        folder = _summary_dir(workdir)
        result["steps"].to_csv(folder / "steps.csv", index=False)
        result["tables"].to_csv(folder / "tables.csv", index=False)
        result["figures"].to_csv(folder / "figures.csv", index=False)
        (folder / "verdict.txt").write_text(result["verdict"] + "\n", encoding="utf-8")
        print(f"summary written to {folder}")
    return 0 if result["verdict"].startswith("Reproduced") else 1


def pd_print(frame) -> None:
    import pandas as pd

    with pd.option_context("display.max_columns", None, "display.width", 250, "display.max_colwidth", 120):
        print(frame.to_string(index=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m kambale.notebook")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func, text in (("gates", _cmd_gates, "run every verify command on a copy and list the gates"),
                             ("reproduce", _cmd_reproduce, "regenerate all outputs on a copy and compare them")):
        p = sub.add_parser(name, help=text)
        p.add_argument("--workdir", default=None, help="folder for the copy (created when missing)")
        p.add_argument("--no-keep", action="store_true", help="delete the copy at the end")
        p.set_defaults(func=func)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

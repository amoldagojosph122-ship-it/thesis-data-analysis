"""Command-line entry point: python -I -m kambale.objective_2 <command>.

`all` runs import, analyse, extension, weathering, structural, verify, figures, tables, verify, report and verify, in that order. A verify step that
finds a STOP gate ends the run before anything after it is written (specification 03). Every command prints a JSON summary
and exits with status 1 when a STOP gate fails.
"""

from __future__ import annotations

import argparse
import json
import sys

from kambale.objective_2 import analysis, importer, verify
from kambale.objective_2.config import StopError


def _verify_step(summary: dict, key: str) -> bool:
    """Runs the gate runner, records its outcome under key, and returns True when a gate stopped the run."""
    result = verify.run()
    summary[key] = {"run_id": result["run_id"], "stopped": result["stopped"],
                    "handoff_rows_withdrawn": result["handoff_rows_withdrawn"],
                    "gates": {g["gate_id"]: g["status"] for g in result["gates"]}}
    return result["stopped"]


def _finish(summary: dict, status: int) -> int:
    print(json.dumps(summary, indent=2, default=str))
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kambale.objective_2")
    parser.add_argument("command", choices=["import", "analyse", "extension", "weathering", "structural", "figures", "tables", "report", "verify", "all"])
    args = parser.parse_args(argv)
    command = args.command
    summary: dict = {}
    try:
        if command in ("import", "all"):
            summary["import"] = importer.import_snapshot()
        if command in ("analyse", "all"):
            summary["analyse"] = analysis.run()
        if command in ("extension", "all"):
            from kambale.objective_2 import extension
            summary["extension"] = extension.run()
        if command in ("weathering", "all"):
            from kambale.objective_2 import weathering
            summary["weathering"] = weathering.run()
        if command in ("structural", "all"):
            from kambale.objective_2 import structural
            summary["structural"] = structural.run()
        if command == "verify" and _verify_step(summary, "verify"):
            return _finish(summary, 1)
        if command == "all" and _verify_step(summary, "verify_before_exports"):
            return _finish(summary, 1)
        if command in ("figures", "all"):
            from kambale.objective_2 import figures
            summary["figures"] = figures.render_all()
        if command in ("tables", "all"):
            from kambale.objective_2 import tables
            summary["tables"] = tables.render_all()
        if command == "all" and _verify_step(summary, "verify_after_exports"):
            return _finish(summary, 1)
        if command in ("report", "all"):
            from kambale.objective_2 import report
            summary["report"] = report.write_all()
        if command == "all" and _verify_step(summary, "verify_after_report"):
            return _finish(summary, 1)
    except StopError as exc:
        summary["stop"] = str(exc)
        return _finish(summary, 1)
    return _finish(summary, 0)


if __name__ == "__main__":
    sys.exit(main())

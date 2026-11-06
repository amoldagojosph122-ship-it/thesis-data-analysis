"""Command-line entry point: python -I -m kambale.objective_4 <command>."""

from __future__ import annotations

import argparse
import json
import sys

from kambale.objective_4 import evaluation, importer, verify
from kambale.objective_4.config import StopError


def _verify_step(summary, key):
    result = verify.run()
    summary[key] = {"run_id": result["run_id"], "stopped": result["stopped"],
                    "gates": {g["gate_id"]: g["status"] for g in result["gates"]}}
    return result["stopped"]


def _finish(summary, status):
    print(json.dumps(summary, indent=2, default=str))
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kambale.objective_4")
    parser.add_argument("command", choices=["import", "evaluate", "figures", "tables", "report", "verify", "all"])
    args = parser.parse_args(argv)
    command = args.command
    summary = {}
    try:
        if command in ("import", "all"):
            summary["import"] = importer.import_snapshot()
        if command in ("evaluate", "all"):
            summary["evaluate"] = evaluation.run()
        if command == "verify" and _verify_step(summary, "verify"):
            return _finish(summary, 1)
        if command == "all" and _verify_step(summary, "verify_before_exports"):
            return _finish(summary, 1)
        if command in ("figures", "all"):
            from kambale.objective_4 import figures
            summary["figures"] = figures.render_all()
        if command in ("tables", "all"):
            from kambale.objective_4 import tables
            summary["tables"] = tables.render_all()
        if command == "all" and _verify_step(summary, "verify_after_exports"):
            return _finish(summary, 1)
        if command in ("report", "all"):
            from kambale.objective_4 import report
            summary["report"] = report.write_all()
        if command == "all" and _verify_step(summary, "verify_after_report"):
            return _finish(summary, 1)
    except StopError as exc:
        summary["stop"] = str(exc)
        return _finish(summary, 1)
    return _finish(summary, 0)


if __name__ == "__main__":
    sys.exit(main())

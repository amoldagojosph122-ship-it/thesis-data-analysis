"""Command-line entry point: python -I -m kambale.objective_2 <command>.

Commands run in the order given in specification 04 section 7. Every command prints a JSON summary and exits with
status 1 when a STOP gate fails.
"""

from __future__ import annotations

import argparse
import json
import sys

from kambale.objective_2 import analysis, importer, verify
from kambale.objective_2.config import StopError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kambale.objective_2")
    parser.add_argument("command", choices=["import", "analyse", "extension", "figures", "tables", "report", "verify", "all"])
    args = parser.parse_args(argv)
    summary: dict = {}
    try:
        if args.command in ("import", "all"):
            summary["import"] = importer.import_snapshot()
        if args.command in ("analyse", "all"):
            summary["analyse"] = analysis.run()
        if args.command in ("extension", "all"):
            from kambale.objective_2 import extension
            summary["extension"] = extension.run()
        if args.command in ("figures", "all"):
            from kambale.objective_2 import figures
            summary["figures"] = figures.render_all()
        if args.command in ("tables", "all"):
            from kambale.objective_2 import tables
            summary["tables"] = tables.render_all()
        if args.command in ("report", "all"):
            from kambale.objective_2 import report
            summary["report"] = report.write_all()
        if args.command in ("verify", "all"):
            result = verify.run()
            summary["verify"] = {"run_id": result["run_id"], "stopped": result["stopped"],
                                 "gates": {g["gate_id"]: g["status"] for g in result["gates"]}}
            if result["stopped"]:
                print(json.dumps(summary, indent=2, default=str))
                return 1
    except StopError as exc:
        summary["stop"] = str(exc)
        print(json.dumps(summary, indent=2, default=str))
        return 1
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

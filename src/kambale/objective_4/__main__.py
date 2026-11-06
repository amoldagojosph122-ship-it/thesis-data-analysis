"""Command-line entry point: python -I -m kambale.objective_4 <command> [--tier {1,2}].

--tier is applied to the environment before any stage module is imported, so config.py resolves the tier's config file,
database and output directories once for the whole run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

COMMANDS = ("import", "evaluate", "figures", "tables", "report", "verify", "all")


def _verify_step(summary, key):
    from kambale.objective_4 import verify
    result = verify.run()
    summary[key] = {"run_id": result["run_id"], "stopped": result["stopped"],
                    "gates": {g["gate_id"]: g["status"] for g in result["gates"]}}
    return result["stopped"]


def _finish(summary, status):
    print(json.dumps(summary, indent=2, default=str))
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(prog="kambale.objective_4")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--tier", type=int, choices=(1, 2), default=1,
                        help="1 = TIER_1_EXTRAPOLATION (leave one line out); 2 = TIER_2_INTERPOLATION (interleaved holes)")
    args = parser.parse_args(argv)
    os.environ["KAMBALE_O4_TIER"] = str(args.tier)

    from kambale.objective_4 import config, evaluation, importer
    from kambale.objective_4.config import StopError
    if config.TIER != str(args.tier):  # pragma: no cover - guards against a config imported earlier with another tier
        raise RuntimeError(f"configuration already loaded for tier {config.TIER}; run one tier per process")

    command = args.command
    summary = {"tier": args.tier}
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

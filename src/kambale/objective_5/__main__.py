"""Command-line entry point: python -I -m kambale.objective_5 <command>.

`all` runs import, refit, grid, bootstrap, classify, verify, figures, tables, verify, report and verify, in that order. It
does not run simulate (part 2). A verify step that finds a STOP gate ends the run before anything after it is written.
Every command prints a JSON summary and exits with status 1 when a STOP gate or StopError occurs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

COMMANDS = ("import", "refit", "grid", "bootstrap", "classify", "simulate", "figures", "tables", "report", "verify", "all")


def _verify_step(summary: dict, key: str) -> bool:
    from kambale.objective_5 import verify
    result = verify.run()
    summary[key] = {"run_id": result["run_id"], "stopped": result["stopped"],
                    "gates": {g["gate_id"]: g["status"] for g in result["gates"]}}
    return result["stopped"]


def _finish(summary: dict, status: int) -> int:
    print(json.dumps(summary, indent=2, default=str))
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kambale.objective_5")
    parser.add_argument("command", choices=COMMANDS)
    args = parser.parse_args(argv)
    command = args.command
    summary: dict = {}
    from kambale.objective_5.config import StopError, load_config, O5_CONFIG_PATH
    from kambale.objective_5.db import connect_o5
    try:
        cfg, _ = load_config(O5_CONFIG_PATH)
        if command == "simulate":
            from kambale.objective_5 import simulate
            simulate.run()
        if command in ("import", "all"):
            from kambale.objective_5 import importer
            summary["import"] = importer.import_inputs()
        if command in ("refit", "all"):
            from kambale.objective_5 import refit
            o5 = connect_o5()
            try:
                summary["refit"] = [{k: r[k] for k in ("tier", "role", "model_id", "params", "calibration",
                                                       "in_sample_brier", "in_sample_auc", "artifact", "sha256")}
                                    | {"o3_matches": r["o3"]["matches"], "o3_mode": r["o3"]["mode"]}
                                    for r in refit.refit_all(o5, cfg)]
            finally:
                o5.close()
        if command in ("grid", "all"):
            from kambale.objective_5 import grid
            o5 = connect_o5()
            try:
                summary["grid"] = grid.build_cells(o5, cfg)
            finally:
                o5.close()
        if command in ("bootstrap", "all"):
            from kambale.objective_5 import bootstrap
            o5 = connect_o5()
            try:
                t0 = time.time()
                summary["bootstrap"] = bootstrap.run_bootstrap(o5, cfg)
                summary["bootstrap"]["wall_clock_s"] = round(time.time() - t0, 1)
            finally:
                o5.close()
        if command in ("classify", "all"):
            from kambale.objective_5 import classify
            o5 = connect_o5()
            try:
                summary["classify"] = classify.classify_all(o5, cfg)
            finally:
                o5.close()
        if command == "verify" and _verify_step(summary, "verify"):
            return _finish(summary, 1)
        if command == "all" and _verify_step(summary, "verify_before_exports"):
            return _finish(summary, 1)
        if command in ("figures", "all"):
            from kambale.objective_5 import figures
            summary["figures"] = figures.render_all()
        if command in ("tables", "all"):
            from kambale.objective_5 import tables
            summary["tables"] = tables.render_all()
        if command == "all" and _verify_step(summary, "verify_after_exports"):
            return _finish(summary, 1)
        if command in ("report", "all"):
            from kambale.objective_5 import report
            summary["report"] = report.write_all()
        if command == "all" and _verify_step(summary, "verify_after_report"):
            return _finish(summary, 1)
    except StopError as exc:
        summary["stop"] = str(exc)
        return _finish(summary, 1)
    return _finish(summary, 0)


if __name__ == "__main__":
    sys.exit(main())

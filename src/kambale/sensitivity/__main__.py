"""Command-line entry point: python -m kambale.sensitivity front-surface [--quick]."""

from __future__ import annotations

import argparse
import sys

from kambale.objective_3.config import StopError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m kambale.sensitivity")
    sub = parser.add_subparsers(dest="command", required=True)
    fs = sub.add_parser("front-surface", help="weathering-front surface sensitivity analysis")
    fs.add_argument("--quick", action="store_true",
                    help="one plan, baseline surface only, 50 bootstrap replicates; outputs go to the system temp dir")
    args = parser.parse_args(argv)
    from kambale.sensitivity.front_surface import run
    try:
        run(quick=bool(args.quick))
    except StopError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

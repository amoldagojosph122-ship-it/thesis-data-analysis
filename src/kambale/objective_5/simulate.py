"""Scenario simulation (sequential indicator simulation with a locally varying mean). Part 2.

The command is registered so that the CLI shape is fixed, but the scenario_simulation section of the configuration is not
run in part 1. Nothing in this module writes to the database.
"""

from __future__ import annotations

from kambale.objective_5.config import StopError

PART2_MESSAGE = ("simulate: not implemented in part 1; the scenario_simulation section (O5-T05, O5-T06, O5-F08..F10) "
                 "is part 2 of the Objective 5 stage")


def run(*args, **kwargs):
    raise StopError(PART2_MESSAGE)

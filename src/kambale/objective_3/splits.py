"""CLI-facing spatial split stage.

The implementation lives in `features.py`: the observation snapshot, the safe predictor matrix, the two fold plans and
their audit. This module exists so the command name `splits` and the module layout in the specification remain stable.
"""

from __future__ import annotations

from kambale.objective_3.features import (Observations, build_split_plan, fold_membership, load_observations,
                                          safe_feature_names, run)

__all__ = ["Observations", "build_split_plan", "fold_membership", "load_observations", "safe_feature_names", "run"]

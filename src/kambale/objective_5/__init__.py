"""Objective 5: model-based three-dimensional uncertainty of graphitic-domain occurrence.

Part 1 reads the locked Objective 3 model pipeline and the Objective 4 locked handoffs read-only, refits the selected and
runner-up models once on all binary intervals, and maps probability, bootstrap interval, entropy and model disagreement on
a relative 10 x 10 x 2 m grid, restricted by lateral distance to the validated support zones. The scenario simulation
(part 2, simulate.py) is a scenario analysis with an assumed lateral range.
"""

O5_CODE_VERSION = "5.2.0-part2"
O5_SCHEMA_VERSION = "O5-SCHEMA-2026.11.06-2"

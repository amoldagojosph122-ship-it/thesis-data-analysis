# Objective 4 outputs: TIER_2_INTERPOLATION

Independent spatial validation and probability-based performance evaluation of the frozen Objective 3 predictions for the claim: skill when predicting an undrilled position between drilled holes of the same line (one hole spacing)

Database: database/kambale_obj4_validation_tier2.sqlite. Split plan: O3-SPLIT-HOLE-IL-2.

Current status: exit conditions met.
Locked model choice: M2_HGB_WF (INCONCLUSIVE, POINT_ESTIMATE_WITH_CAVEAT).

Contents:

- RUN_REPORT.md: the evaluation, its uncertainty, power and the locked decision.
- BLOCKED_OR_DEFERRED.md: every warning, failure and deferred item.
- DATA_LINEAGE.json: upstream receipts, configuration, code and output hashes.
- FIGURE_MANIFEST.csv: SHA-256 for every figure, table and report file.
- figures/objective_4/tier_2 and tables/objective_4/tier_2: the outputs.

Reproduce with the commands in RUN_REPORT.md section 14.

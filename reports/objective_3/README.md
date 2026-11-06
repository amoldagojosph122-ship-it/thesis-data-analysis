# Objective 3 outputs

Indicator geostatistics, machine learning and hybrid occurrence models at the Kambale deposit. The stage reads Objective 1 (geology, labels, geometry) and Objective 2 (support and the continuity handoff) read-only and writes database/kambale_obj3_models.sqlite.

Current status: exit conditions met.
Handoff to Objective 4: out-of-fold predictions and failure masks frozen.
Objective 2 continuity handoff: NOT_IDENTIFIABLE (candidate family NONE).

Contents:

- RUN_REPORT.md: the run, its models, gates, limitations and the Objective 4 handoff.
- BLOCKED_OR_DEFERRED.md: every warning, failure, skip and deferred item.
- DATA_LINEAGE.json: upstream receipts, configuration, code and output hashes.
- FIGURE_MANIFEST.csv: SHA-256 and registered SQL for every figure and table file.
- ../../figures/objective_3 and ../../tables/objective_3: the outputs.

Reproduce with the commands in RUN_REPORT.md section 12.

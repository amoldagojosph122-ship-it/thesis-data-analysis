# Compatibility Addendum — Objective 1 Master Prompt for the New Five-Database Architecture

**Effective priority:** Read this addendum and `Kambale_Five_Database_Architecture_and_Execution_Order.md` **after** `Kambale_Thesis_Database_First_SpecKit_Prompt.md`; where they differ on the number/authority of databases, this addendum controls. All five approved synopsis objectives remain word-for-word unchanged.

## Necessary revision to the original Objective 1 specification

1. Retain the actual existing Objective 1 database path `database/kambale_thesis.sqlite` unless a formal and verified path migration is performed. The logical alias is `obj1_master`. It is the sole canonical geological database for raw workbook sources, corrected/curated observations, approved graphitic classifications, collar/survey interpretations, geometry versions and QA/QC decisions.
2. **Do not implement full Objective 2–5 model, variogram, validation or uncertainty tables in Objective 1.** The original Objective 1 prompt mentioned future extension tables and a `Stage B` interface. Treat those as **contracts and/or compatibility views only**, not as a directive to populate those tables in the O1 database. Separate databases own those derived outputs: `kambale_obj2_spatial.sqlite`, `kambale_obj3_models.sqlite`, `kambale_obj4_validation.sqlite`, and `kambale_obj5_uncertainty.sqlite`.
3. If Objective 1 has already implemented empty forward-looking tables, **do not destructively delete them**. Mark them as deprecated/no-new-writes, and move ownership of future populated output to the relevant objective's SQLite file. If modelling data have already been written into O1, record and verify a lossless, versioned migration before deprecation.
4. Add an Objective 1 `dataset_export_receipts` mechanism exposing versioned, hash-verifiable extraction contracts for later objectives. Each receipt includes canonical dataset ID, source workbook SHA-256, approved geological label rule/version, interval/hole IDs, coordinate/geometry version and vertical datum status, selected SQL hash, export row-count and ordered-identifier/content digest, export timestamp, and status. Do not copy or reassign original geological observations as the canonical truth in downstream databases.
5. Enforce **read-only** Objective 1 access from Objective 2–5 processing. SQLite foreign keys cannot reference external database files, so all cross-database ID/hash/cardinality compatibility tests must be explicitly implemented and logged in the receiving database.
6. Each objective owns its own SQLite database, stage-specific plots/tables, schema and figure SQL, and `STOP/WARN/SKIP` scientific-gate logs. Every exported item includes a chain of receipts back to the Objective 1 source data.
7. Modify the Objective 1 handover report to specify the verified master DB path, actual table/view names and read-only SQL extraction interface. Downstream coding agents must discover actual schema rather than assume the name of every table in the original prompt.

## Scientific safeguards unchanged

- Missing collar RL/elevation is never silently replaced with zero or invented absolute Z.
- Domain occurrence is a geological logged indicator, **not** graphite grade/TGC.
- Any reconciled graphite label rule requires documented geological verification, with unresolved intervals kept separate.
- A visually polished plot does not establish geological continuity or predictive accuracy.
- Preserve raw spreadsheet observations and their SHA-256; idempotent ETL and downstream invalidation are mandatory.

## Recommended implementation order

O1 geology and QA/QC approval → O2 spatial description and indicator variography → O3 leak-free fold-based modelling and out-of-fold predictions → O4 independent-style spatial CV evaluation and locked model selection → O3 final selected model refit → O5 probabilistic 3-D grids, uncertainty and qualified geological visualization.

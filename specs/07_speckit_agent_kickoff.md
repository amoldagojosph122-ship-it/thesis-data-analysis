# 07 Spec Kit agent kickoff (Stage A)

## Official Spec Kit state

- CLI: `specify` (specify-cli 1.2.2 installed with uv tool). Verified by `specify version`.
- Initialised: `specify init --here --force --integration claude --non-interactive` (existing files were backed up before running; no existing file was modified).
- Installed: `.specify/` (constitution template, templates, scripts, workflow) and `.claude/skills/speckit-*` (constitution, specify, clarify, plan, checklist, tasks, analyze, implement, converge, taskstoissues).
- Constitution: `.specify/memory/constitution.md` version 1.0.0 (7 principles, 2 technology and workflow sections, governance).
- Feature: `specs/001-kambale-o1-stage-a/` with `spec.md` (5 user stories, FR-001 to FR-022, SC-001 to SC-008), `plan.md` (constitution check, structure, design decisions), `tasks.md` (50 tasks with evidence rules).

## Dependency-ordered task list and status

| Phase | Tasks | Status |
|---|---|---|
| 1 Setup and provenance | T001-T007 | Done (environment, raw copy, configs) |
| 2 Database contract | T008-T015 | Done (migrations 0001-0008; triggers) |
| 3 Ingestion and curation | T016-T021 | Done |
| 4 QA/QC and label candidates | T022-T027 | Done (ambiguity export written) |
| 5 Geometry | T028-T032 | Done (regional context included) |
| 6 Build and views | T033-T035 | Done (idempotence tested; verify command) |
| 7 Figures and tables | T036-T043 | Done (F01-F09, T01-T03, deferred catalogue) |
| 8 Tests and verification | T044-T046 | Done for tests; regeneration hash check via test |
| 9 Reports and handover | T047-T050 | Reports written; this handover is the final step |

Items in `tasks.md` are not all ticked; the evidence for each completed item is the command output listed in this handover.

## Commands to reproduce

```bash
.venv/Scripts/python.exe -m kambale.cli build
.venv/Scripts/python.exe -m kambale.cli verify
.venv/Scripts/python.exe -m kambale.cli plot --all
.venv/Scripts/python.exe -m kambale.cli tables
.venv/Scripts/python.exe -m kambale.cli report
.venv/Scripts/python.exe -m pytest -q
```

## Evidence required before a task is ticked

- The command named in the task is run in the current session.
- Its output (row counts, hashes, pytest summary) is recorded in `validation_test_results` (verify) or in the report.
- Any task not run is marked NOT_RUN, not PASS.

## Handover to Stage B (the next objective)

- Read-only contract: `dataset_export_receipts` (per export: source SHA-256, label rule ID and status, geometry build, CRS, vertical status, selected SQL hash, row count, ordered-identifier digest).
- Stage B must not start until: a label rule is approved (`label_reviews`), coordinates and datum are confirmed, drill lines are approved, and collar RL or a DEM method is supplied.
- Stage B outputs go to `database/kambale_obj2_spatial.sqlite` and later databases. Objective 1 tables stay read-only. Blocking triggers in obj1_master stay in place.
- Spec Kit feature for Objective 2 should be created with `/speckit-specify` (or the CLI equivalent) and must start from the constitution and this handover.

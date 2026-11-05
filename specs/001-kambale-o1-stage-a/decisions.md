# Decision log: Stage A choices reviewed with the author (2026-11-05)

These are the author's working choices. They do not approve any label rule. A rule becomes APPROVED only after a supervising geologist records an APPROVE_RULE review in `label_reviews` (enforced by trigger).

| # | Choice | Decision | Effect in the current build |
|---|---|---|---|
| D1 | Target A (primary strict label) | STRICT_SGS_v1 (rock code Sgs) | 529 positives, 1,368 negatives, 13 unresolved. Status PROPOSED. |
| D2 | Target B (reconciled candidate) | RECON_2OF3_v1 kept as the reconciled candidate | 562 positives, 1,289 negatives, 59 unresolved. Status PROPOSED. |
| D3 | "Traces of graphite" comments | Counted as evidence and flagged for review. Sensitivity: RECON_2OF3_NOTRACE_v1 built (see D7). | Unchanged for RECON_2OF3_v1. Flag `comment_trace_qualified` shown in T03 and the ambiguity export. |
| D4 | `fsc` intervals (12, 12KBRB 061, 1-13 m) | Left unresolved; not mapped to `Fsc` | UNSUPPORTED; label UNRESOLVED for every rule. |
| D5 | Blank rock code (12KBRB 005, 8-9 m) | Left unresolved until confirmed; an OVERRIDE_LABEL review would be the route if confirmed | MISSING; label UNRESOLVED for every rule. |
| D6 | Horizontal pair for geometry | UTM pair (UTMEasting/UTMNorthing), provisional; Easting/Northing kept as alternate | `coordinate_decisions` status PROVISIONAL. |
| D7 | Trace-excluded sensitivity (built on request, 2026-11-05) | RECON_2OF3_NOTRACE_v1 added as a SENSITIVITY rule (status PROPOSED) | Against RECON_2OF3_v1: 527 positives (35 become UNRESOLVED), 1,310 negatives (21 UNRESOLVED become negative), 73 unresolved. Table T04. |

**Correction recorded with D7.** The trace flag first matched any comment containing both "trace" and "graphit." Two intervals, "graphitic schist with traces of epidot," were wrongly flagged. The flag now requires graphite within the same phrase, so 56 intervals are flagged (previously 58). This does not change RECON_2OF3_v1 or the 126 conflicts.

## Open items still pending (not decided here)

- Datum of the UTM pair (WGS 84 declared; unverified).
- Dip and azimuth convention, and whether the end-of-hole orientation applies to the whole hole.
- Whether a blank mineral field means "not logged" (current rule) or "not assessed."
- Drill-line grouping (five nominal Northing groups, provisional).
- Collar RL or DEM method (required before any absolute 3-D product).
- Relocation of Objective 2 descriptive outputs into `kambale_obj2_spatial.sqlite` when Objective 2 starts.

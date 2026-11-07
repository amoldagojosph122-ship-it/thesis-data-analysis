# Collar elevations (RL): what is needed and what happens next

## Current state (checked 2026-11-05)

- The raw workbook `data/raw/Kambale RAB_Collar_Sampling_Geology_2012a_corrected_2026-11-05_rock_codes.xlsx`, sheet `Collars`,
  has an `RL` column. It is empty for all 71 holes, so the elevation exists as a field but has no values.
- Without collar elevations, depth is measured from each collar, and the lateral analysis assumes that collars at similar
  depth have similar elevations. Absolute elevation is not used anywhere in Objective 2 (gate G03).
- The Copernicus GLO-30 DEM (approved as a provisional source in Objective 1) is a surface model that includes vegetation and
  buildings. No error has been measured for this site, and its vertical error is typically several metres. That is comparable
  to or larger than the 3 m depth-matching tolerance, so it cannot replace surveyed collar elevations.

## What is needed for each of the 71 holes

- `RL`: the collar elevation in metres, with the vertical reference stated (for example the Ghana vertical datum, or the
  local benchmark used in the survey).
- The survey method (DGPS, total station, or other) and the date of the survey.
- The estimated vertical accuracy in metres, and the surveyor or contractor.
- The source document (survey report, page, or file name).

HoleIDs run from 12KBRB 001 to 12KBRB 071, as listed in the `Collars` sheet.

## Procedure once the values arrive

1. Send the values and their source document. Do not overwrite the raw copy. Send either a corrected workbook or a table.
2. Objective 1 (Stage A) creates a new immutable raw copy and a new ETL version. The vertical reference is verified, and the
   elevation source is approved with its vertical datum and approver, following the Stage A rules for `elevation_sources`.
3. Objective 2 then gets a new predeclared configuration. It first uses absolute elevation only as a sensitivity that tests
   the equal-collar-elevation assumption. It becomes a basis only if that sensitivity supports it. Gates G03 and G22 are
   reworded for that configuration, and the analysis is rerun under it.

## What does not change until then

- The results stand on relative depth, and the configuration-2 handoff decision stands.

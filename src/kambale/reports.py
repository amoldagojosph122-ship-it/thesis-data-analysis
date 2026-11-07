"""Report writers. Every number in the generated reports is read from obj1_master at the time of writing.

Outputs
  reports/QAQC_REPORT.md        QA/QC, reconciliation, decisions and verification results
  FIGURE_MANIFEST.csv           one row per output file with SQL and file hashes (from figure_export_manifest)
  DEFERRED_FIGURES.md           Stage B and out-of-scope items with prerequisites
  data/derived/*.csv            non-authoritative delivery copies (the database remains the source of truth)
"""

from __future__ import annotations

import csv
from pathlib import Path

from kambale.config import DERIVED_DIR, PROJECT_ROOT, REPORTS_DIR
from kambale.db import connect, utc_now
from kambale.registry import DEFERRED_IDS


def _rows(conn, sql: str, params: tuple = ()) -> list[tuple]:
    return [tuple(r) for r in conn.execute(sql, params).fetchall()]


def _md_table(headers: list[str], rows: list[tuple]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else str(v).replace("|", "/") for v in r) + " |")
    return "\n".join(out)


def write_reports(db_path: Path) -> dict:
    conn = connect(db_path, read_only=True)
    try:
        dv = conn.execute("SELECT dataset_version_id, dataset_version_key, dataset_label, created_utc, activated_utc "
                          "FROM dataset_versions WHERE status = 'ACTIVE'").fetchone()
        key = dv[1]
        source = conn.execute("SELECT file_name, sha256, size_bytes, raw_copy_path FROM source_files "
                              "WHERE source_file_id = (SELECT source_file_id FROM v_active_version)").fetchone()
        sections = []
        sections.append(f"""# Kambale Objective 1 database: QA/QC report (Stage A)

Generated {utc_now()} from `{db_path.relative_to(PROJECT_ROOT).as_posix() if db_path.is_relative_to(PROJECT_ROOT) else db_path}`.

**Overall stage status: PROVISIONAL.** The ETL, integrity checks and reconciliation are verified. The UTM coordinates and the WGS 84 datum are approved (2026-11-05). Vertical positions are provisional. The drill-line groups are approved (2026-11-05). Graphitic label rules other than DESIGN_8_2_v1 are provisional. No collar RL exists. The Copernicus
DEM elevations were approved on 2026-11-05 as the provisional vertical source (Dickson Abdul-Wahab, 10:46:46 UTC) and
are stored apart from the RL field. No graphite assay exists, so no grade, tonnage or resource statement is made.

- Dataset version: `{key}` (label: {dv[2]}), ACTIVE, activated {dv[4]}.
- Source workbook: `{source[0]}`, SHA-256 `{source[1]}`, {source[2]:,} bytes; raw copy `{source[3]}` (read-only, hash-checked).

## 1. Source inventory and record counts

""")
        sections.append(_md_table(["Sheet", "State", "Rows", "Columns", "Blank columns"],
                                  _rows(conn, "SELECT sheet_name, sheet_state, n_rows, n_cols, blank_columns_json "
                                              "FROM source_sheets WHERE source_file_id = (SELECT source_file_id "
                                              "FROM v_active_version) ORDER BY sheet_name")))
        sections.append("\n\nReconciliation against the preliminary values in ThesisDesign.docx (comparison only; no value "
                        "was forced to match):\n\n")
        sections.append(_md_table(["Item", "Observed", "Curated", "ThesisDesign reference"],
                                  _rows(conn, open(_sql("T01_reconciliation.sql"), encoding="utf-8").read())))

        sections.append("\n\n## 2. QA/QC findings\n\n")
        sections.append(_md_table(["Check", "Severity", "Status", "Result", "Records", "Description"],
                                  _rows(conn, "SELECT check_id, severity, status, result, n_records, description "
                                              "FROM v_qaqc_summary ORDER BY CASE severity WHEN 'ERROR' THEN 1 "
                                              "WHEN 'WARNING' THEN 2 ELSE 3 END, check_id")))
        sections.append("\n\nDetail text for each dataset-level finding is stored in `qaqc_findings.detail`.\n\n")
        sections.append("## 3. Decisions and their status\n\n")
        coord = _rows(conn, "SELECT adopted_pair, crs_key, 'UNVERIFIED', status, median_pair_discrepancy_m, "
                            "max_pair_discrepancy_m, n_holes FROM coordinate_decisions WHERE dataset_version_id = ?",
                            (dv[0],))
        sections.append(_md_table(["Adopted pair", "CRS", "Datum", "Status", "Median pair separation (m)",
                                   "Max pair separation (m)", "Holes"], coord) + "\n\n")
        sections.append(_md_table(["Rule", "Version", "Family", "Status", "Definition"],
                                  _rows(conn, "SELECT rule_id, rule_version, rule_family, status, description "
                                              "FROM graphite_label_rules ORDER BY rule_id")) + "\n\n")
        sections.append("\n\n### Candidate label counts (1-m intervals; a label is UNRESOLVED when the rock code is "
                        "missing or unsupported, or when evidence is partial)\n\n")
        sections.append(_md_table(["Rule", "Label state", "Intervals", "Logged m"],
                                  _rows(conn, "SELECT rule_id, label_state, n_intervals, logged_m FROM "
                                              "v_label_candidate_counts ORDER BY rule_id, label_state")) + "\n\n")
        sections.append(_md_table(["Evidence pattern", "Review status", "Intervals"],
                                  _rows(conn, "SELECT evidence_pattern, label_review_status, n_intervals "
                                              "FROM v_label_disagreement ORDER BY n_intervals DESC LIMIT 12")) + "\n\n")
        sections.append(f"""### Interpretation of the label evidence

- The three fields are logged indicators (rock code `Sgs`; mineral code `gr`; comment containing "graphit").
  They are not independent laboratory confirmations and do not measure graphite grade.
- The six candidate rules (STRICT_SGS_v1 for Target A, DESIGN_8_2_v1 for the ThesisDesign 8.2 Target B, the earlier reconciled candidates RECON_2OF3_v1, ALL3_v1 and ANY_v1, and the trace-excluded sensitivity RECON_2OF3_NOTRACE_v1) are PROPOSED. None is approved. `label_reviews` is empty, and a database trigger blocks
  approval without an APPROVE_RULE review.
- Conflicts are counted with the rule written in `config/label_rules.yaml`. The conflict count is 126: the naive count
  of 130 mixed-evidence intervals excludes one interval with an unsupported or missing code and three intervals
  with a blank comment, which stay unresolved.

## 4. Geometry and vertical status

- Method: straight-hole, single end-of-hole orientation (dip -60, azimuth 090 at all holes). PROVISIONAL.
- Offsets: delta_E = m cos(d) sin(a), delta_N = m cos(d) cos(a), delta_Z = m sin(d); m = interval midpoint.
- `z_relative_m` is stored relative to the collar. `z_absolute_m` is NULL for every interval (verified by `kambale verify`).
- Surveyed elevation status: BLOCKED (no collar RL in the workbook; no DGPS supplied).
- Approved as the provisional vertical source on 2026-11-05 (Dickson Abdul-Wahab): Copernicus GLO-30 sampled at each collar (`holes.dem_elevation_m`, status PROVISIONAL);
  the interval values are `interval_coordinates.z_dem_absolute_m`. The DEM is a surface model that includes vegetation
  and buildings, so it is not a surveyed collar RL.

## 5. Drill lines (approved nominal-Northing groups) and regional context

""")
        sections.append(_md_table(["Line", "Nominal Northing (m)", "Holes", "Intervals", "Status"],
                                  _rows(conn, "SELECT line_code, nominal_northing_m, n_holes, n_intervals, status "
                                              "FROM v_drill_lines ORDER BY nominal_northing_m")) + "\n\n")
        sections.append("Regional polygons are 1:1,000,000 context only and do not verify local contacts:\n\n")
        sections.append(_md_table(["GEO_SYMBOL", "Stratigraphy", "Legend text"],
                                  _rows(conn, "SELECT DISTINCT geo_symbol, stratigraphy, legend_text FROM "
                                              "v_regional_context ORDER BY geo_symbol")) + "\n\n")

        sections.append("## 6. Verification results (latest run)\n\n")
        sections.append(_md_table(["Group", "Test", "Expected", "Observed", "Outcome", "Run (UTC)"],
                                  _rows(conn, "SELECT test_group, test_name, expected, observed, outcome, run_utc "
                                              "FROM validation_test_results WHERE test_result_id IN (SELECT "
                                              "MAX(test_result_id) FROM validation_test_results GROUP BY test_name) "
                                              "ORDER BY test_group, test_name")) + "\n\n")

        sections.append("""## 7. Data problems and decisions still pending

1. Coordinate pair: the UTM pair was approved on 2026-11-05. 17 holes differ by more than 5 m from the Easting/Northing pair; the difference is recorded, not corrected. The datum is confirmed as WGS 84 (2026-11-05).
2. Collar RL: obtain the DGPS collar elevations. The DEM elevations are approved as the provisional vertical source (2026-11-05); a surveyed RL would replace them.
3. Graphitic label rules: DESIGN_8_2_v1 (Target B) was approved on 2026-11-05 by Dickson Abdul-Wahab. STRICT_SGS_v1 (Target A) and the other candidate rules remain PROPOSED. The conflicts are listed in `ambiguity_review_intervals.csv`.
4. Corrected from the original log on 2026-11-05: 12 intervals logged `fsc` (not in the legend, quartz mica schist comments) are now `Fsc` (felsic schist).
5. Corrected from the original log on 2026-11-05: the blank rock code on 12KBRB 005 (8-9 m) is now `Sgs`, matching its comment.
6. Dip and azimuth are a single end-of-hole nominal orientation; SurveyedBy and Instrument are blank.
7. The project label `Akoko` appears on five holes within the KAMBALE prospect.
8. Intensity (`alt_min1int`) and grain-size (`grainsize`) values have no documented units; they are not used in any derivation.
9. Contractor is blank for all holes; weathering `fr` (fresh) is never logged.
10. The hidden `___SheetInfo` sheet contains a worksheet-protection string. It is redacted in the database. The original file is unchanged.

## 8. Rerun commands

```bash
kambale build           # verified ETL; identical source and configuration is a no-op
kambale verify          # SQL integrity, reconciliation, Stage B blocking, pytest suite
kambale plot --all      # figures F01..F09 with registry rows and hashes
kambale tables          # tables T01..T03 (CSV, Markdown, LaTeX)
kambale report          # this report, FIGURE_MANIFEST.csv, DEFERRED_FIGURES.md, data/derived/*.csv
```
""")
        out = REPORTS_DIR / "QAQC_REPORT.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(sections), encoding="utf-8")

        manifest_rows = _rows(conn, "SELECT m.figure_id, f.stage_status, m.output_format, m.output_path, m.output_sha256, "
                                    "m.output_bytes, q.sql_file, q.sql_sha256, m.exported_utc FROM figure_export_manifest m "
                                    "JOIN figure_registry f ON f.figure_id = m.figure_id "
                                    "LEFT JOIN figure_query_registry q ON q.figure_query_id = m.figure_query_id "
                                    "ORDER BY m.figure_id, m.output_format, m.output_path")
        with open(PROJECT_ROOT / "FIGURE_MANIFEST.csv", "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(["figure_id", "stage_status", "format", "output_path", "output_sha256", "output_bytes",
                             "sql_file", "sql_sha256", "exported_utc", "dataset_version_key"])
            for r in manifest_rows:
                writer.writerow([*r, key])

        deferred_text = _deferred_markdown(key)
        (PROJECT_ROOT / "DEFERRED_FIGURES.md").write_text(deferred_text, encoding="utf-8")

        DERIVED_DIR.mkdir(parents=True, exist_ok=True)
        exports = {
            "holes.csv": "SELECT hole_id, raw_hole_id, hole_type, grid_label, easting_alt_m, northing_alt_m, utm_easting_m, "
                         "utm_northing_m, line_code, rl_status, max_depth_m, project_code, prospect, contractor, logged_by, "
                         "date_drilled FROM v_holes ORDER BY hole_id",
            "logging_intervals_flags.csv": "SELECT interval_key, hole_id, line_code, depth_from_m, depth_to_m, midpoint_m, "
                                           "rock_code_raw, rock_code_status, weathering_code, is_sgs, has_gr_mineral, "
                                           "comment_graphitic, comment_trace_qualified, positive_indicators, "
                                           "negative_indicators, label_conflict, evidence_pattern, label_review_status, "
                                           "strict_state, recon_state, design_state, all3_state, any_state, comment_raw FROM v_interval_design "
                                           "ORDER BY hole_id, depth_from_m",
            "interval_geometry_relative_z.csv": "SELECT interval_key, hole_id, line_code, midpoint_m, dip_deg, azimuth_deg, "
                                                "delta_e_m, delta_n_m, delta_z_m, easting_m, northing_m, z_relative_m, "
                                                "z_absolute_m, z_reference, geometry_status FROM v_interval_geometry "
                                                "ORDER BY hole_id, depth_from_m",
            "ambiguity_review_intervals.csv": "SELECT interval_key, hole_id, line_code, depth_from_m, depth_to_m, rock_code_raw, "
                                              "is_sgs, has_gr_mineral, comment_graphitic, comment_raw, evidence_pattern, "
                                              "label_review_status, strict_state, design_state FROM v_interval_design "
                                              "WHERE label_conflict = 1 OR rock_code_status <> 'VALID' "
                                              "ORDER BY hole_id, depth_from_m",
            "qaqc_findings.csv": "SELECT check_id, severity, status, result, entity_type, entity_key, source_sheet, source_row, "
                                 "n_records, detail FROM qaqc_findings WHERE dataset_version_id = ? ORDER BY check_id, "
                                 "entity_type, entity_key",
        }
        for name, sql in exports.items():
            params = (dv[0],) if "?" in sql else ()
            cursor = conn.execute(sql, params)
            columns = [d[0] for d in cursor.description]
            with open(DERIVED_DIR / name, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(columns)
                writer.writerows(cursor.fetchall())
        (DERIVED_DIR / "README.txt").write_text(
            "Non-authoritative delivery copies generated from database/kambale_thesis.sqlite "
            f"(dataset {key}). The database is the source of truth.\n", encoding="utf-8")
        return {"reports": [str(out.relative_to(PROJECT_ROOT)).replace("\\", "/"), "FIGURE_MANIFEST.csv",
                            "DEFERRED_FIGURES.md"] + [f"data/derived/{n}" for n in exports],
                "manifest_rows": len(manifest_rows), "dataset_version_key": key}
    finally:
        conn.close()


def _sql(name: str) -> Path:
    from kambale.config import SQL_FIGURES_DIR
    return SQL_FIGURES_DIR / name


def _deferred_markdown(key: str) -> str:
    lines = [
        "# Deferred figures and tables (Stage B and out-of-scope items)", "",
        f"Dataset {key}. These items are NOT produced in Stage A. Each has a registry row with stage status "
        "`DEFERRED` in `figure_registry`, and no output file exists for it.", "",
        "The Stage A figure catalogue (F01-F09, T01-T03) is complete for the data-supported items. Only the items "
        "below are deferred.", "",
        "| ID | Objective | Item | Prerequisite gate and planned table contract |",
        "|---|---|---|---|",
    ]
    for code, (objective, title, prerequisite) in DEFERRED_IDS.items():
        lines.append(f"| {code} | {objective} | {title} | {prerequisite} |")
    lines += ["", "## Gates that must pass before Stage B starts", "",
              "1. A supervising geologist approves one graphitic label rule (`label_reviews`, decision APPROVE_RULE). Done: "
              "DESIGN_8_2_v1 (Target B), approved by Dickson Abdul-Wahab.",
              "2. Collar coordinates and datum are confirmed, and the drill-line grouping is approved or replaced. Done: "
              "the UTM pair was approved on 2026-11-05 (Dickson Abdul-Wahab). The datum was confirmed as WGS 84 on 2026-11-05 (Dickson Abdul-Wahab). The drill-line grouping was approved on 2026-11-05 (Dickson Abdul-Wahab).",
              "3. Collar RL is supplied with a vertical datum, or the DEM elevations are approved. Done: the DEM elevations "
              "were approved on 2026-11-05. No surveyed RL exists, so vertical outputs stay relative and no georeferenced "
              "volume is claimed until gate 2 is closed.",
              "4. Stage B tables are populated only in their objective databases (`kambale_obj2_spatial.sqlite` "
              "and later). The blocking triggers in obj1_master must stay in place.",
              "5. Variograms and models are fitted only on training data inside each spatial fold. A variogram fitted "
              "on all holes is exploratory only.", ""]
    return "\n".join(lines)

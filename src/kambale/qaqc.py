"""QA/QC checks. Each check returns findings with severity, status and result.

Severity: ERROR (affected records are quarantined or unresolved), WARNING (retained and qualified),
INFO (fact recorded). Status: BLOCKED (an output cannot be produced), PROVISIONAL (usable with a stated
qualifier), APPROVED (passes with no pending decision).
Nothing in this module mutates the raw data. Corrections are never made; exclusions are recorded.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from kambale.curate import CuratedData, normalise_hole_id
from kambale.geometry import on_five_metre_grid

# ThesisDesign.docx reports these for the workbook. They are used ONLY to reconcile, never to force results.
THESIS_EXPECTED = {"holes": 71, "survey_records": 71, "intervals": 1910, "sgs_intervals": 529,
                   "evidence_3": 476, "evidence_2": 87, "evidence_1": 43, "evidence_0": 1304}

CHECKS = [
    ("QC-SRC-HASH", "Provenance", "Workbook SHA-256 equals raw copy SHA-256", "ERROR",
     "Stop the build (FAILED)", "hashlib.sha256 over source and data/raw copy"),
    ("QC-SHEET-INVENTORY", "Provenance", "Sheet inventory, states and hidden reference sheets", "INFO",
     "None", "openpyxl sheet_state and dimensions"),
    ("QC-ROW-RECON", "Provenance", "Data-row counts per sheet recomputed from the workbook", "INFO",
     "None", "count of non-blank rows below header"),
    ("QC-BLANK-ROWS", "Provenance", "Fully blank rows skipped during ingestion", "INFO",
     "None", "rows with all cells blank"),
    ("QC-HOLEID-DUP", "Identifiers", "Duplicate normalised HoleID in Collars", "ERROR",
     "Duplicate collar quarantined", "Counter over normalised HoleID"),
    ("QC-HOLEID-RAW", "Identifiers", "Raw HoleID spelling differs from normalised form", "INFO",
     "Raw spelling retained", "compare raw and normalised strings"),
    ("QC-ORPHAN-LOG", "Referential", "Logging interval whose hole is not in Collars", "ERROR",
     "Interval quarantined", "set difference of normalised IDs"),
    ("QC-ORPHAN-SURVEY", "Referential", "Survey record whose hole is not in Collars", "ERROR",
     "Survey quarantined", "set difference of normalised IDs"),
    ("QC-NO-LOG", "Referential", "Collar with no logging intervals", "WARNING",
     "Hole retained without intervals", "collar IDs not in logging"),
    ("QC-NO-SURVEY", "Referential", "Collar with no survey record", "WARNING",
     "Hole retained; geometry not built", "collar IDs not in surveys"),
    ("QC-DEPTH-INTERVAL", "Depth", "Non-numeric, negative or DEPTH_FROM >= DEPTH_TO intervals", "ERROR",
     "Interval quarantined", "per-row numeric and ordering test"),
    ("QC-OVERLAP", "Depth", "Overlapping logging intervals within a hole", "ERROR",
     "Overlapping interval quarantined", "sort by depth and compare with previous end"),
    ("QC-GAP", "Depth", "Gaps between consecutive logging intervals or first interval not at 0 m", "WARNING",
     "Gap recorded; no interpolation", "sort by depth and compare with previous end"),
    ("QC-SUPPORT", "Depth", "Sample support: interval length distribution", "INFO",
     "Support recorded in denominators", "distribution of DEPTH_TO - DEPTH_FROM"),
    ("QC-LOG-END", "Depth", "Logged end depth versus collar max_depth", "WARNING",
     "Recorded; ERROR if logging exceeds max_depth", "max(DEPTH_TO) per hole versus max_depth"),
    ("QC-DUP-LOG", "Duplicates", "Duplicate logging interval (hole, DEPTH_FROM)", "ERROR",
     "Duplicate quarantined", "Counter over (hole, from)"),
    ("QC-DUP-SURVEY", "Duplicates", "Duplicate survey station (hole, depth)", "ERROR",
     "Duplicate quarantined", "Counter over (hole, depth)"),
    ("QC-SURVEY-RANGE", "Survey", "Dip outside [-90, 0] or azimuth outside [0, 360)", "ERROR",
     "Survey station quarantined", "range test under adopted convention"),
    ("QC-SURVEY-DEPTH", "Survey", "Survey depth versus collar max_depth", "WARNING",
     "Recorded", "compare survey depth with max_depth"),
    ("QC-SURVEY-STATIONS", "Survey", "Number and type of survey stations per hole", "WARNING",
     "Geometry provisional (straight-hole assumption)", "count of stations per hole"),
    ("QC-SURVEY-META", "Survey", "SurveyedBy and Instrument blank in source", "WARNING",
     "Convention cannot be validated against source metadata", "blank-cell test"),
    ("QC-SURVEY-UNIFORM", "Survey", "Dip and azimuth identical across all holes", "WARNING",
     "Nominal orientation assumed; geometry PROVISIONAL", "distinct value count"),
    ("QC-RL", "Vertical", "Collar RL present", "WARNING",
     "Absolute elevation BLOCKED; relative Z only", "blank RL test"),
    ("QC-CONTRACTOR", "Metadata", "Contractor blank in source", "INFO",
     "None (not used)", "blank-cell test"),
    ("QC-PROJECT", "Metadata", "Project code inconsistent with prospect", "WARNING",
     "Recorded for review", "Project value versus majority prospect group"),
    ("QC-DATE", "Metadata", "DateDrilled parses under the explicit format %d-%m-%Y", "ERROR",
     "Hole quarantined if unparsed", "strptime with explicit format"),
    ("QC-COORD-PAIR", "Coordinates", "Discrepancy between UTM and Easting/Northing pairs", "WARNING",
     "Pair decision recorded; PROVISIONAL", "Euclidean distance per hole"),
    ("QC-COORD-NODES", "Coordinates", "Values on 5 m grid nodes by pair", "INFO",
     "Evidence for pair interpretation only", "value modulo 5 m"),
    ("QC-CRS", "Coordinates", "CRS declared and datum verified", "WARNING",
     "Coordinate status PROVISIONAL", "Grid label and regional .prj"),
    ("QC-CRS-PLAUSIBILITY", "Coordinates", "Transformed collar location lies in the expected region", "INFO",
     "Plausibility only; not datum verification", "pyproj UTM 30N to WGS 84 lat/lon"),
    ("QC-NN-SPACING", "Coordinates", "Median nearest-neighbour collar spacing", "INFO",
     "Recorded for grid support", "nearest neighbour on UTM pair"),
    ("QC-LINES", "Geometry", "Nominal Northing groups and provisional drill lines", "WARNING",
     "Plan map shows lines as provisional", "distinct Northing values"),
    ("QC-REGIONAL", "Context", "Collars inside regional 1:1,000,000 polygons", "INFO",
     "Context only; not local geology", "shapely intersection"),
    ("QC-CODE-ROCK-UNSUPPORTED", "Codes", "rock_type1 code not in logging legend", "ERROR",
     "Label UNRESOLVED for every rule; code retained raw", "legend membership"),
    ("QC-CODE-ROCK-MISSING", "Codes", "rock_type1 blank", "WARNING",
     "Label UNRESOLVED for every rule", "blank-cell test"),
    ("QC-CODE-WEATHER-MISSING", "Codes", "weathering blank", "WARNING",
     "Weathering class MISSING in summaries", "blank-cell test"),
    ("QC-CODE-COLOUR-MISSING", "Codes", "colour1 blank", "INFO",
     "Recorded as missing", "blank-cell test"),
    ("QC-COMMENT-MISSING", "Codes", "Comment blank", "WARNING",
     "Comment term evidence absent; label 0 not assigned", "blank-cell test"),
    ("QC-LEGEND-AGREE", "Codes", "Legend and hidden reference lists agree", "WARNING",
     "Discrepancies listed; legend is the working reference", "set comparison"),
    ("QC-LEGEND-UNUSED", "Codes", "Legend codes never used in logging", "INFO",
     "Recorded; retained in dictionary", "usage count"),
    ("QC-BLANK-COLUMNS", "Codes", "Columns with no data in source", "INFO",
     "Not used in derivations", "blank-column test"),
    ("QC-GRAINSIZE", "Codes", "grainsize values present without documented unit", "WARNING",
     "Stored raw; not used", "distinct values"),
    ("QC-INTENSITY", "Codes", "alt_min1int present without alt_min1 code", "WARNING",
     "Intensity retained; unit undocumented", "pairwise null test"),
    ("QC-INTENSITY-UNITS", "Codes", "alt_min1int unit undocumented", "WARNING",
     "Intensity not used for labels", "documentation check"),
    ("QC-WEATHER-UNUSED", "Codes", "Legend weathering codes never used", "INFO",
     "Fresh class absent from data", "usage count"),
    ("QC-COMMENT-TRACE", "Labels", "Graphite comment qualified by 'trace' (false-positive review)", "WARNING",
     "Flag only; label rules not altered", "regex test"),
    ("QC-LABEL-CONFLICT", "Labels", "Intervals with mixed graphite evidence", "WARNING",
     "Label review required; not resolved by software", "evidence pattern"),
    ("QC-LABEL-RECON", "Labels", "Evidence distribution versus ThesisDesign.docx", "INFO",
     "Reconciliation only", "counts by positive indicators"),
    ("QC-SGS-COUNT", "Labels", "Sgs interval count versus ThesisDesign.docx", "INFO",
     "Reconciliation only", "count of rock_type1 = Sgs"),
    ("QC-QUARANTINE", "Curation", "Records excluded from curated tables by a hard rule", "ERROR",
     "Excluded record kept in raw tables and listed here", "rule-based exclusion log"),
]


@dataclass
class Finding:
    check_id: str
    severity: str
    status: str
    result: str
    entity_type: str
    entity_key: str
    detail: str
    source_sheet: str | None = None
    source_row: int | None = None
    n_records: int = 0
    action: str | None = None
    rationale: str | None = None


def _f(check, severity, status, result, entity_type="DATASET", entity_key="", detail="", sheet=None, row=None,
       n=0, action=None, rationale=None) -> Finding:
    return Finding(check, severity, status, result, entity_type, entity_key, detail, sheet, row, n, action,
                   rationale)


def _status_for(severity: str, result: str) -> str:
    if result == "PASS":
        return "APPROVED"
    return {"ERROR": "BLOCKED", "WARNING": "PROVISIONAL", "INFO": "PROVISIONAL"}[severity]


def run_checks(data: CuratedData, evidence: list[dict], context: dict) -> list[Finding]:
    """Run every check. `evidence` items carry interval_key, label_review_status and pattern fields.

    `context` supplies: source_hash, raw_hash, sheet_info, line_summary, pair_stats, nn_median_m,
    crs_status, regional (summary dict), plausibility (lat/lon range), grid_nodes (counts).
    """
    out: list[Finding] = []
    add = out.append

    # ---- provenance ------------------------------------------------------------------------------------
    same = context["source_hash"] == context["raw_hash"]
    add(_f("QC-SRC-HASH", "ERROR", _status_for("ERROR", "PASS" if same else "FAIL"),
           "PASS" if same else "FAIL", detail=f"sha256={context['source_hash']}"))
    hidden = [s for s, state in context["sheet_states"].items() if state != "visible"]
    add(_f("QC-SHEET-INVENTORY", "INFO", "APPROVED", "PASS",
           detail=f"sheets={len(context['sheet_states'])}; hidden={', '.join(sorted(hidden)) or 'none'}"))
    counts = context["row_counts"]
    add(_f("QC-ROW-RECON", "INFO", "APPROVED", "PASS",
           detail="; ".join(f"{k}={v}" for k, v in counts.items())))
    skipped = sum(data.skipped_blank_rows.values())
    add(_f("QC-BLANK-ROWS", "INFO", "APPROVED", "PASS", n=skipped, detail=f"blank rows skipped={skipped}"))

    # ---- identifiers and referential integrity --------------------------------------------------------
    raw_collar_ids = [normalise_hole_id(r["values"]["HoleID"]) for r in data.raw["Collars"]]
    dup = [k for k, v in Counter(raw_collar_ids).items() if v > 1]
    add(_f("QC-HOLEID-DUP", "ERROR", _status_for("ERROR", "FAIL" if dup else "PASS"),
           "FAIL" if dup else "PASS", n=len(dup), detail=f"duplicates={dup}"))
    spelling = [r["values"]["HoleID"] for r in data.raw["Collars"]
                if str(r["values"]["HoleID"]) != normalise_hole_id(r["values"]["HoleID"])]
    add(_f("QC-HOLEID-RAW", "INFO", "PROVISIONAL" if spelling else "APPROVED", "FAIL" if spelling else "PASS",
           n=len(spelling), detail=f"raw spellings differing from normalised form={len(spelling)}"))

    collar_set = set(raw_collar_ids)
    log_ids = [normalise_hole_id(r["values"]["HOLEID"]) for r in data.raw["Logging"]]
    orphan_log = sorted(set(log_ids) - collar_set)
    add(_f("QC-ORPHAN-LOG", "ERROR", _status_for("ERROR", "FAIL" if orphan_log else "PASS"),
           "FAIL" if orphan_log else "PASS", n=len(orphan_log), detail=f"orphan hole IDs={orphan_log}"))
    survey_ids = [normalise_hole_id(r["values"]["HoleID"]) for r in data.raw["Surveys"]]
    orphan_survey = sorted(set(survey_ids) - collar_set)
    add(_f("QC-ORPHAN-SURVEY", "ERROR", _status_for("ERROR", "FAIL" if orphan_survey else "PASS"),
           "FAIL" if orphan_survey else "PASS", n=len(orphan_survey), detail=f"orphan survey IDs={orphan_survey}"))
    no_log = sorted(collar_set - set(log_ids))
    add(_f("QC-NO-LOG", "WARNING", _status_for("WARNING", "FAIL" if no_log else "PASS"),
           "FAIL" if no_log else "PASS", n=len(no_log), detail=f"collars without logs={no_log}"))
    no_survey = sorted(collar_set - set(survey_ids))
    add(_f("QC-NO-SURVEY", "WARNING", _status_for("WARNING", "FAIL" if no_survey else "PASS"),
           "FAIL" if no_survey else "PASS", n=len(no_survey), detail=f"collars without surveys={no_survey}"))

    # ---- depth -----------------------------------------------------------------------------------------
    bad_depth = [q for q in data.quarantine if q["sheet"] == "Logging" and "interval" in q["reason"]
                 and "overlaps" not in q["reason"]]
    add(_f("QC-DEPTH-INTERVAL", "ERROR", _status_for("ERROR", "FAIL" if bad_depth else "PASS"),
           "FAIL" if bad_depth else "PASS", n=len(bad_depth), detail=f"invalid intervals={len(bad_depth)}"))
    overlaps = [q for q in data.quarantine if "overlaps" in q["reason"]]
    add(_f("QC-OVERLAP", "ERROR", _status_for("ERROR", "FAIL" if overlaps else "PASS"),
           "FAIL" if overlaps else "PASS", n=len(overlaps), detail=f"overlapping intervals={len(overlaps)}"))
    gaps, first_not_zero = _gap_scan(data)
    add(_f("QC-GAP", "WARNING", _status_for("WARNING", "FAIL" if (gaps or first_not_zero) else "PASS"),
           "FAIL" if (gaps or first_not_zero) else "PASS", n=len(gaps) + len(first_not_zero),
           detail=f"gaps={len(gaps)}; holes not starting at 0 m={len(first_not_zero)}"))
    lengths = Counter(round(i["interval_length_m"], 6) for i in data.intervals)
    add(_f("QC-SUPPORT", "INFO", "APPROVED", "PASS", n=len(data.intervals),
           detail=f"interval lengths (m): {dict(sorted(lengths.items()))}"))
    log_end = _log_end_scan(data)
    over = [h for h, (end, md) in log_end.items() if end > md + 1e-6]
    under = [h for h, (end, md) in log_end.items() if end < md - 1e-6]
    add(_f("QC-LOG-END", "ERROR" if over else "WARNING",
           _status_for("ERROR" if over else "WARNING", "FAIL" if (over or under) else "PASS"),
           "FAIL" if (over or under) else "PASS", n=len(over) + len(under),
           detail=f"logging exceeds max_depth={over}; logging shorter than max_depth={under}"))

    dup_log = [k for k, v in Counter((i["hole_id"], i["depth_from_m"]) for i in data.intervals).items() if v > 1]
    add(_f("QC-DUP-LOG", "ERROR", _status_for("ERROR", "FAIL" if dup_log else "PASS"),
           "FAIL" if dup_log else "PASS", n=len(dup_log), detail=f"duplicate (hole, from) keys={len(dup_log)}"))
    dup_survey = [k for k, v in Counter((s["hole_id"], s["depth_m"]) for s in data.surveys).items() if v > 1]
    add(_f("QC-DUP-SURVEY", "ERROR", _status_for("ERROR", "FAIL" if dup_survey else "PASS"),
           "FAIL" if dup_survey else "PASS", n=len(dup_survey), detail=f"duplicate survey keys={len(dup_survey)}"))

    # ---- surveys ---------------------------------------------------------------------------------------
    range_q = [q for q in data.quarantine if q["sheet"] == "Surveys"]
    add(_f("QC-SURVEY-RANGE", "ERROR", _status_for("ERROR", "FAIL" if range_q else "PASS"),
           "FAIL" if range_q else "PASS", n=len(range_q), detail=f"survey rows outside convention={len(range_q)}"))
    survey_depth = {}
    for s in data.surveys:
        survey_depth.setdefault(s["hole_id"], []).append(s)
    mismatch = []
    for c in data.collars:
        stations = survey_depth.get(c["hole_id"], [])
        if stations and any(abs(st["depth_m"] - c["max_depth_m"]) > 1e-6 for st in stations):
            mismatch.append(c["hole_id"])
    add(_f("QC-SURVEY-DEPTH", "WARNING", _status_for("WARNING", "FAIL" if mismatch else "PASS"),
           "FAIL" if mismatch else "PASS", n=len(mismatch), detail=f"survey depth differs from max_depth={mismatch}"))
    single = sum(1 for h, st in survey_depth.items() if len(st) == 1)
    multi = sum(1 for h, st in survey_depth.items() if len(st) > 1)
    add(_f("QC-SURVEY-STATIONS", "WARNING", "PROVISIONAL", "FAIL", n=single,
           detail=f"holes with one station={single}; with several={multi}; no down-hole survey series; "
                  f"straight-hole assumption applied"))
    meta_blank = all(s["surveyed_by"] is None and s["instrument"] is None for s in data.surveys)
    add(_f("QC-SURVEY-META", "WARNING", "PROVISIONAL" if meta_blank else "APPROVED", "FAIL" if meta_blank else "PASS",
           n=len(data.surveys), detail="SurveyedBy and Instrument blank for all surveys" if meta_blank else "present"))
    dips = {s["dip_deg"] for s in data.surveys}
    azs = {s["azimuth_deg"] for s in data.surveys}
    uniform = len(dips) == 1 and len(azs) == 1
    add(_f("QC-SURVEY-UNIFORM", "WARNING", "PROVISIONAL" if uniform else "APPROVED",
           "FAIL" if uniform else "PASS", n=len(data.surveys),
           detail=f"distinct dips={sorted(dips)}; distinct azimuths={sorted(azs)}"))

    # ---- vertical, metadata, dates --------------------------------------------------------------------
    rl_blank = [c["hole_id"] for c in data.collars if c["rl_status"] == "MISSING"]
    add(_f("QC-RL", "WARNING", "BLOCKED" if rl_blank else "APPROVED", "FAIL" if rl_blank else "PASS",
           n=len(rl_blank), detail=f"collar RL missing for {len(rl_blank)} of {len(data.collars)} holes; "
                                   f"absolute elevation BLOCKED; relative Z only"))
    contractor_blank = sum(1 for c in data.collars if c["contractor"] is None)
    add(_f("QC-CONTRACTOR", "INFO", "PROVISIONAL" if contractor_blank else "APPROVED",
           "FAIL" if contractor_blank else "PASS", n=contractor_blank,
           detail=f"contractor blank for {contractor_blank} holes"))
    prospects = Counter(c["prospect"] for c in data.collars)
    main_prospect = prospects.most_common(1)[0][0] if prospects else None
    odd_project = [(c["hole_id"], c["project_code"]) for c in data.collars
                   if c["project_code"] != "Wa" and c["prospect"] == main_prospect]
    add(_f("QC-PROJECT", "WARNING", "PROVISIONAL" if odd_project else "APPROVED",
           "FAIL" if odd_project else "PASS", n=len(odd_project),
           detail=f"project labels other than 'Wa' within prospect {main_prospect}: {odd_project}"))
    date_bad = [q for q in data.quarantine if q["sheet"] == "Collars" and "format" in q["reason"]]
    parsed = sum(1 for c in data.collars if c["date_drilled"])
    add(_f("QC-DATE", "ERROR", _status_for("ERROR", "FAIL" if date_bad else "PASS"),
           "FAIL" if date_bad else "PASS", n=parsed,
           detail=f"DateDrilled parsed with %d-%m-%Y for {parsed} holes; unparsed={len(date_bad)}"))

    # ---- coordinates -----------------------------------------------------------------------------------
    stats = context["pair_stats"]
    add(_f("QC-COORD-PAIR", "WARNING", "PROVISIONAL", "FAIL" if stats["n_over_5m"] else "PASS",
           n=stats["n_over_5m"],
           detail=(f"holes={stats['n']}; median separation={stats['median_m']} m; max={stats['max_m']} m; "
                   f"holes >5 m={stats['n_over_5m']}; mean dE={stats['mean_d_e_m']} m, dN={stats['mean_d_n_m']} m; "
                   f"sd dE={stats['sd_d_e_m']} m, dN={stats['sd_d_n_m']} m (no systematic shift)")))
    for row in context["pair_rows"]:
        if row["horizontal_m"] > 5.0:
            add(_f("QC-COORD-PAIR", "WARNING", "PROVISIONAL", "FAIL", entity_type="HOLE", entity_key=row["hole_id"],
                   sheet="Collars", n=1, detail=f"pair separation {row['horizontal_m']:.2f} m",
                   action="REVIEW_REQUIRED",
                   rationale="Adopted UTM pair retained; alternate pair kept in holes; supervisor confirmation required"))
    grid = context["grid_nodes"]
    add(_f("QC-COORD-NODES", "INFO", "APPROVED", "PASS",
           detail=(f"Easting/Northing pair on 5 m nodes: {grid['alt_both']} of {grid['n']} holes; "
                   f"UTM pair on 5 m nodes: {grid['utm_both']} of {grid['n']} holes")))
    crs = context["crs_status"]
    add(_f("QC-CRS", "WARNING", "PROVISIONAL", "FAIL", detail=crs))
    plaus = context["plausibility"]
    add(_f("QC-CRS-PLAUSIBILITY", "INFO", "APPROVED" if plaus["inside"] else "PROVISIONAL",
           "PASS" if plaus["inside"] else "FAIL", detail=plaus["text"]))
    add(_f("QC-NN-SPACING", "INFO", "APPROVED", "PASS", detail=f"median nearest-neighbour spacing={context['nn_median_m']:.2f} m"))
    lines = context["line_summary"]
    add(_f("QC-LINES", "WARNING", "PROVISIONAL", "FAIL", n=len(lines),
           detail="; ".join(f"{l['line_code']}: {l['n_holes']} holes" for l in lines)))
    reg = context["regional"]
    add(_f("QC-REGIONAL", "INFO", "APPROVED", "PASS", n=reg["n_polygons"],
           detail=(f"regional polygons intersecting collar buffer={reg['n_polygons']}; "
                   f"codes={reg['codes']}; collars inside a mapped polygon={reg['collars_inside']} of {reg['n_collars']}")))

    # ---- codes -----------------------------------------------------------------------------------------
    rock_unsupported = [i for i in context["interval_status"] if i["rock_code_status"] == "UNSUPPORTED"]
    for i in rock_unsupported:
        add(_f("QC-CODE-ROCK-UNSUPPORTED", "ERROR", "BLOCKED", "FAIL", entity_type="INTERVAL",
               entity_key=i["interval_key"], sheet="Logging", row=i["source_row"], n=1,
               detail=f"rock_type1 '{i['rock_code_raw']}' is not in the logging legend (case-sensitive)",
               action="NULL_LABEL_UNRESOLVED",
               rationale="Retained raw; not mapped to any legend meaning; unresolved for every label rule"))
    add(_f("QC-CODE-ROCK-UNSUPPORTED", "ERROR", _status_for("ERROR", "FAIL" if rock_unsupported else "PASS"),
           "FAIL" if rock_unsupported else "PASS", n=len(rock_unsupported),
           detail=f"unsupported rock codes={len(rock_unsupported)}; codes={sorted({i['rock_code_raw'] for i in rock_unsupported})}"))
    rock_missing = [i for i in context["interval_status"] if i["rock_code_status"] == "MISSING"]
    for i in rock_missing:
        add(_f("QC-CODE-ROCK-MISSING", "WARNING", "PROVISIONAL", "FAIL", entity_type="INTERVAL",
               entity_key=i["interval_key"], sheet="Logging", row=i["source_row"], n=1,
               detail=f"rock_type1 blank; comment='{i['comment_raw']}'",
               action="NULL_LABEL_UNRESOLVED", rationale="No code assigned; comment evidence not used to infer a code"))
    add(_f("QC-CODE-ROCK-MISSING", "WARNING", _status_for("WARNING", "FAIL" if rock_missing else "PASS"),
           "FAIL" if rock_missing else "PASS", n=len(rock_missing), detail=f"blank rock codes={len(rock_missing)}"))
    wmiss = [i for i in context["interval_status"] if i["weathering_code"] is None]
    add(_f("QC-CODE-WEATHER-MISSING", "WARNING", _status_for("WARNING", "FAIL" if wmiss else "PASS"),
           "FAIL" if wmiss else "PASS", n=len(wmiss), detail=f"blank weathering={len(wmiss)}"))
    cmiss = [i for i in context["interval_status"] if i["colour1_code"] is None]
    add(_f("QC-CODE-COLOUR-MISSING", "INFO", "PROVISIONAL" if cmiss else "APPROVED", "FAIL" if cmiss else "PASS",
           n=len(cmiss), detail=f"blank colour1={len(cmiss)}"))
    comment_missing = [i for i in context["interval_status"] if i["comment_raw"] is None]
    for i in comment_missing:
        add(_f("QC-COMMENT-MISSING", "WARNING", "PROVISIONAL", "FAIL", entity_type="INTERVAL",
               entity_key=i["interval_key"], sheet="Logging", row=i["source_row"], n=1,
               detail="comment cell is empty in the workbook", action="REVIEW_REQUIRED",
               rationale="Enter the logged comment from the original log. The rock code and neighbouring comments are not used to infer it."))
    add(_f("QC-COMMENT-MISSING", "WARNING", _status_for("WARNING", "FAIL" if comment_missing else "PASS"),
           "FAIL" if comment_missing else "PASS", n=len(comment_missing), detail=f"blank comments={len(comment_missing)}"))
    legend = context["legend"]
    agree = not legend["legend_only"] and not legend["reference_only"]
    add(_f("QC-LEGEND-AGREE", "WARNING", "APPROVED" if agree else "PROVISIONAL", "PASS" if agree else "FAIL",
           detail=f"legend-only codes={legend['legend_only']}; reference-only codes={legend['reference_only']}"))
    add(_f("QC-LEGEND-UNUSED", "INFO", "APPROVED", "PASS",
           n=len(legend["unused_rock"]), detail=f"unused RockType legend codes={len(legend['unused_rock'])}"))
    blanks = data.blank_columns
    add(_f("QC-BLANK-COLUMNS", "INFO", "APPROVED", "PASS",
           detail="; ".join(f"{k}: {', '.join(v) or 'none'}" for k, v in blanks.items())))
    grain = context["grain_values"]
    add(_f("QC-GRAINSIZE", "WARNING", "PROVISIONAL", "FAIL" if grain["n"] else "PASS", n=grain["n"],
           detail=f"grainsize values={grain['n']}; distinct={grain['distinct']}; unit undocumented; not used"))
    intensity = context["intensity"]
    add(_f("QC-INTENSITY", "WARNING", "PROVISIONAL" if intensity["orphans"] else "APPROVED",
           "FAIL" if intensity["orphans"] else "PASS", n=intensity["orphans"],
           detail=f"alt_min1int without alt_min1 code={intensity['orphans']}; alt_min1int entries={intensity['n']}"))
    add(_f("QC-INTENSITY-UNITS", "WARNING", "PROVISIONAL", "FAIL",
           detail="alt_min1int unit not documented in workbook; values not used for labels"))
    unused_weather = legend["unused_weathering"]
    add(_f("QC-WEATHER-UNUSED", "INFO", "APPROVED", "PASS", n=len(unused_weather),
           detail=f"legend weathering codes unused={unused_weather}"))
    trace_n = sum(1 for e in evidence if e["comment_trace_qualified"])
    add(_f("QC-COMMENT-TRACE", "WARNING", "PROVISIONAL" if trace_n else "APPROVED", "FAIL" if trace_n else "PASS",
           n=trace_n, detail=f"comments with graphite term and 'trace' qualifier={trace_n} (false-positive review)"))

    # ---- labels ----------------------------------------------------------------------------------------
    conflicts = [e for e in evidence if e["label_conflict"]]
    for e in conflicts:
        add(_f("QC-LABEL-CONFLICT", "WARNING", "PROVISIONAL", "FAIL", entity_type="INTERVAL",
               entity_key=e["interval_key"], sheet="Logging", row=e["source_row"], n=1,
               detail=e["rationale"], action="REVIEW_REQUIRED",
               rationale="Disagreement reported for geological review; no label chosen by software"))
    add(_f("QC-LABEL-CONFLICT", "WARNING", _status_for("WARNING", "FAIL" if conflicts else "PASS"),
           "FAIL" if conflicts else "PASS", n=len(conflicts), detail=f"conflicting intervals={len(conflicts)}"))
    patterns = Counter(e["positive_indicators"] for e in evidence)
    expected = {3: THESIS_EXPECTED["evidence_3"], 2: THESIS_EXPECTED["evidence_2"],
                1: THESIS_EXPECTED["evidence_1"], 0: THESIS_EXPECTED["evidence_0"]}
    same_recon = all(patterns.get(k, 0) == v for k, v in expected.items())
    add(_f("QC-LABEL-RECON", "INFO", "APPROVED" if same_recon else "PROVISIONAL", "PASS" if same_recon else "FAIL",
           n=len(evidence), detail=("evidence distribution by positive indicators: "
                                    + ", ".join(f"{k}={patterns.get(k, 0)}" for k in (3, 2, 1, 0))
                                    + f"; ThesisDesign.docx expectation 476/87/43/1304 "
                                    + ("reproduced" if same_recon else "NOT reproduced; difference must be explained"))))
    sgs_n = sum(1 for e in evidence if e["is_sgs"] == 1)
    add(_f("QC-SGS-COUNT", "INFO", "APPROVED" if sgs_n == THESIS_EXPECTED["sgs_intervals"] else "PROVISIONAL",
           "PASS" if sgs_n == THESIS_EXPECTED["sgs_intervals"] else "FAIL", n=sgs_n,
           detail=f"rock_type1 = Sgs intervals={sgs_n} (ThesisDesign.docx: 529)"))

    for q in data.quarantine:
        add(_f("QC-QUARANTINE", "ERROR", "BLOCKED", "FAIL", entity_type=q["entity_type"],
               entity_key=f"{q['entity_key']}#{q['sheet']}{q['row']}", sheet=q["sheet"], row=q["row"], n=1,
               detail=q["reason"], action="QUARANTINED",
               rationale="Excluded from curated tables; raw row retained unchanged in raw_* tables"))
    add(_f("QC-QUARANTINE", "ERROR", _status_for("ERROR", "FAIL" if data.quarantine else "PASS"),
           "FAIL" if data.quarantine else "PASS", n=len(data.quarantine),
           detail=f"records quarantined={len(data.quarantine)}"))

    return out


def _gap_scan(data: CuratedData) -> tuple[list[tuple], list[str]]:
    by_hole = defaultdict(list)
    for i in data.intervals:
        by_hole[i["hole_id"]].append(i)
    gaps, first = [], []
    for hole, items in by_hole.items():
        items.sort(key=lambda r: r["depth_from_m"])
        if items[0]["depth_from_m"] != 0:
            first.append(hole)
        for a, b in zip(items, items[1:]):
            if b["depth_from_m"] != a["depth_to_m"]:
                gaps.append((hole, a["depth_to_m"], b["depth_from_m"]))
    return gaps, first


def _log_end_scan(data: CuratedData) -> dict[str, tuple[float, float]]:
    end = {}
    for i in data.intervals:
        end[i["hole_id"]] = max(end.get(i["hole_id"], 0.0), i["depth_to_m"])
    return {c["hole_id"]: (end.get(c["hole_id"], 0.0), c["max_depth_m"]) for c in data.collars}


def check_catalogue_rows() -> list[dict]:
    return [{"check_id": c[0], "category": c[1], "description": c[2], "default_severity": c[3],
             "scope_if_failed": c[4], "method": c[5]} for c in CHECKS]


def grid_nodes(collars: list[dict]) -> dict:
    return {"n": len(collars),
            "alt_both": sum(1 for c in collars if on_five_metre_grid(c["easting_alt_m"])
                            and on_five_metre_grid(c["northing_alt_m"])),
            "utm_both": sum(1 for c in collars if on_five_metre_grid(c["utm_easting_m"])
                            and on_five_metre_grid(c["utm_northing_m"]))}

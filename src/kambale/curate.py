"""Curation: turn raw sheet grids into normalised, validated records.

Nothing here writes to the database. Records that fail a hard rule are returned in `quarantine`
(never silently dropped) and become ERROR findings in qaqc.py. Raw values are kept alongside
normalised ones so that every curated field can be traced to its source cell.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from kambale.config import LEGEND_DOMAINS
from kambale.source import SheetGrid, blank_columns

COLLAR_HEADER_ROW = 1
SURVEY_HEADER_ROW = 1
LOGGING_HEADER_ROW = 1
LEGEND_HEADER_ROW = 2
REFERENCE_HEADER_ROW = 2
DATE_FORMAT = "%d-%m-%Y"

COLLAR_FIELDS = ("HoleID", "Grid", "HoleType", "Northing", "Easting", "RL", "UTMNorthing", "UTMEasting",
                 "max_depth", "Project", "Prospect", "Contractor", "LoggedBy", "DateDrilled")
SURVEY_FIELDS = ("HoleID", "depth", "dip", "azimuth", "SurveyedBy", "Instrument")
LOGGING_FIELDS = ("HOLEID", "DEPTH_FROM", "DEPTH_TO", "rock_type1", "colour1", "colour2", "weathering",
                  "grainsize", "structure", "alt_min1", "alt_min1int", "alt_min2", "alt_min2int", "sul_min1",
                  "sul_min1pc", "vn_type", "vn_pc", "Comment", "sample_quality")


@dataclass
class CuratedData:
    raw: dict[str, list[dict]] = field(default_factory=dict)       # sheet -> raw row dicts (values + payload)
    collars: list[dict] = field(default_factory=list)
    surveys: list[dict] = field(default_factory=list)
    intervals: list[dict] = field(default_factory=list)
    codes: list[dict] = field(default_factory=list)
    reference_values: list[dict] = field(default_factory=list)
    quarantine: list[dict] = field(default_factory=list)
    blank_columns: dict[str, list[str]] = field(default_factory=dict)
    header_names: dict[str, list[str]] = field(default_factory=dict)
    skipped_blank_rows: dict[str, int] = field(default_factory=dict)
    sheet_info: list[dict] = field(default_factory=list)
    collar_ids: set[str] = field(default_factory=set)
    legend_index: dict[tuple[str, str], dict] = field(default_factory=dict)
    rock_codes: dict[str, str] = field(default_factory=dict)
    weathering_codes: dict[str, str] = field(default_factory=dict)
    hidden_reference_domains: dict[str, list[str]] = field(default_factory=dict)
    legend_only_codes: list[tuple[str, str]] = field(default_factory=list)
    reference_only_codes: list[tuple[str, str]] = field(default_factory=list)


def normalise_hole_id(value) -> str:
    """Trim, collapse internal whitespace and upper-case. The raw spelling is kept separately."""
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.strip()).upper()


def is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def clean_text(value) -> str | None:
    if is_blank(value):
        return None
    return str(value).strip()


def to_float(value) -> float | None:
    """Return a float, None for blank, or raise ValueError for a non-numeric entry."""
    if is_blank(value):
        return None
    if isinstance(value, bool):
        raise ValueError(f"boolean in numeric field: {value!r}")
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        number = float(str(value).strip())
    if math.isnan(number) or math.isinf(number):
        raise ValueError(f"non-finite value: {value!r}")
    return number


def parse_drill_date(value) -> tuple[str | None, str | None]:
    """Parse DateDrilled with the explicit format %d-%m-%Y. Returns (iso_date, error)."""
    if is_blank(value):
        return None, None
    if isinstance(value, datetime):
        return value.date().isoformat(), None
    if isinstance(value, date):
        return value.isoformat(), None
    try:
        return datetime.strptime(str(value).strip(), DATE_FORMAT).date().isoformat(), None
    except ValueError:
        return None, f"not in explicit format {DATE_FORMAT}: {value!r}"


def jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def payload(values: dict) -> str:
    return json.dumps({k: jsonable(v) for k, v in values.items()}, ensure_ascii=False, sort_keys=True)


def interval_key(hole_id: str, depth_from: float) -> str:
    return f"{hole_id}@{'%g' % depth_from}"


def _rows_as_dicts(sheet: SheetGrid, header_row: int, fields: tuple[str, ...]):
    header = sheet.header(header_row)
    index = {name: header.index(name) for name in fields if name in header}
    missing = [name for name in fields if name not in index]
    if missing:
        raise ValueError(f"{sheet.name}: expected header fields missing: {missing}")
    for excel_row, values in sheet.data_rows(header_row):
        record = {name: (values[pos] if pos < len(values) else None) for name, pos in index.items()}
        yield excel_row, record


def curate(sheets: dict[str, SheetGrid]) -> CuratedData:
    data = CuratedData()

    # ---- hidden and visible sheet inventory -------------------------------------------------------------
    for name, sheet in sheets.items():
        data.header_names[name] = sheet.header(1 if name in ("Collars", "Surveys", "Logging") else 2)
    data.blank_columns["Collars"] = blank_columns(sheets["Collars"], COLLAR_HEADER_ROW)
    data.blank_columns["Surveys"] = blank_columns(sheets["Surveys"], SURVEY_HEADER_ROW)
    data.blank_columns["Logging"] = blank_columns(sheets["Logging"], LOGGING_HEADER_ROW)

    # ---- collars --------------------------------------------------------------------------------------
    collars_sheet = sheets["Collars"]
    data.raw["Collars"] = []
    for excel_row, rec in _rows_as_dicts(collars_sheet, COLLAR_HEADER_ROW, COLLAR_FIELDS):
        data.raw["Collars"].append({"source_row": excel_row, "values": rec, "payload": payload(rec)})
        hole_id = normalise_hole_id(rec["HoleID"])
        problems = []
        try:
            max_depth = to_float(rec["max_depth"])
        except ValueError as exc:
            max_depth, problems = None, [f"max_depth {exc}"]
        if max_depth is None or max_depth <= 0:
            problems.append("max_depth missing or non-positive")
        iso_date, date_error = parse_drill_date(rec["DateDrilled"])
        if date_error:
            problems.append(date_error)
        for name in ("Northing", "Easting", "UTMNorthing", "UTMEasting"):
            try:
                to_float(rec[name])
            except ValueError as exc:
                problems.append(f"{name} {exc}")
        if problems:
            data.quarantine.append({"entity_type": "HOLE", "entity_key": hole_id, "sheet": "Collars",
                                    "row": excel_row, "reason": "; ".join(problems)})
            continue
        data.collars.append({
            "hole_id": hole_id,
            "raw_hole_id": "" if rec["HoleID"] is None else str(rec["HoleID"]),
            "source_row": excel_row,
            "hole_type": clean_text(rec["HoleType"]) or "UNKNOWN",
            "grid_label": clean_text(rec["Grid"]) or "UNKNOWN",
            "easting_alt_m": to_float(rec["Easting"]),
            "northing_alt_m": to_float(rec["Northing"]),
            "utm_easting_m": to_float(rec["UTMEasting"]),
            "utm_northing_m": to_float(rec["UTMNorthing"]),
            "rl_raw": rec["RL"],
            "rl_status": "MISSING" if is_blank(rec["RL"]) else "PRESENT",
            "rl_m": None if is_blank(rec["RL"]) else to_float(rec["RL"]),
            "max_depth_m": max_depth,
            "project_code": clean_text(rec["Project"]),
            "prospect": clean_text(rec["Prospect"]),
            "contractor": clean_text(rec["Contractor"]),
            "logged_by": clean_text(rec["LoggedBy"]),
            "date_drilled": iso_date,
            "date_drilled_raw": "" if rec["DateDrilled"] is None else str(rec["DateDrilled"]),
        })

    data.collar_ids = {c["hole_id"] for c in data.collars}

    # ---- surveys ---------------------------------------------------------------------------------------
    data.raw["Surveys"] = []
    for excel_row, rec in _rows_as_dicts(sheets["Surveys"], SURVEY_HEADER_ROW, SURVEY_FIELDS):
        data.raw["Surveys"].append({"source_row": excel_row, "values": rec, "payload": payload(rec)})
        hole_id = normalise_hole_id(rec["HoleID"])
        try:
            depth = to_float(rec["depth"])
            dip = to_float(rec["dip"])
            azimuth = to_float(rec["azimuth"])
        except ValueError as exc:
            data.quarantine.append({"entity_type": "SURVEY", "entity_key": hole_id, "sheet": "Surveys",
                                    "row": excel_row, "reason": f"non-numeric survey value: {exc}"})
            continue
        problems = []
        if depth is None or depth <= 0:
            problems.append("depth missing or non-positive")
        if dip is None or not (-90.0 <= dip <= 0.0):
            problems.append(f"dip {dip} outside adopted range [-90, 0] (negative downward)")
        if azimuth is None or not (0.0 <= azimuth < 360.0):
            problems.append(f"azimuth {azimuth} outside adopted range [0, 360)")
        if problems:
            data.quarantine.append({"entity_type": "SURVEY", "entity_key": hole_id, "sheet": "Surveys",
                                    "row": excel_row, "reason": "; ".join(problems)})
            continue
        data.surveys.append({
            "hole_id": hole_id, "source_row": excel_row, "depth_m": depth, "dip_deg": dip,
            "azimuth_deg": azimuth,
            "surveyed_by": clean_text(rec["SurveyedBy"]), "instrument": clean_text(rec["Instrument"]),
        })

    # ---- logging intervals -----------------------------------------------------------------------------
    data.raw["Logging"] = []
    rock_codes = {}
    weathering_codes = {}
    for excel_row, rec in _rows_as_dicts(sheets["Logging"], LOGGING_HEADER_ROW, LOGGING_FIELDS):
        data.raw["Logging"].append({"source_row": excel_row, "values": rec, "payload": payload(rec)})
        hole_id = normalise_hole_id(rec["HOLEID"])
        try:
            depth_from = to_float(rec["DEPTH_FROM"])
            depth_to = to_float(rec["DEPTH_TO"])
            grain = to_float(rec["grainsize"])
            alt1_int = to_float(rec["alt_min1int"])
            alt2_int = to_float(rec["alt_min2int"])
            sul_pc = to_float(rec["sul_min1pc"])
            vn_pc = to_float(rec["vn_pc"])
        except ValueError as exc:
            data.quarantine.append({"entity_type": "INTERVAL", "entity_key": hole_id, "sheet": "Logging",
                                    "row": excel_row, "reason": f"non-numeric depth or value: {exc}"})
            continue
        if depth_from is None or depth_to is None or depth_from < 0 or depth_to <= depth_from:
            data.quarantine.append({"entity_type": "INTERVAL", "entity_key": f"{hole_id}@{rec['DEPTH_FROM']}",
                                    "sheet": "Logging", "row": excel_row,
                                    "reason": f"invalid depth interval from={rec['DEPTH_FROM']} to={rec['DEPTH_TO']}"})
            continue
        data.intervals.append({
            "hole_id": hole_id, "source_row": excel_row,
            "depth_from_m": depth_from, "depth_to_m": depth_to,
            "interval_length_m": depth_to - depth_from, "midpoint_m": (depth_from + depth_to) / 2.0,
            "interval_key": interval_key(hole_id, depth_from),
            "rock_code_raw": None if is_blank(rec["rock_type1"]) else str(rec["rock_type1"]),
            "colour1_code": clean_text(rec["colour1"]), "colour2_code": clean_text(rec["colour2"]),
            "weathering_code": clean_text(rec["weathering"]),
            "grainsize_raw": grain, "structure_code": clean_text(rec["structure"]),
            "alt_min1_code": clean_text(rec["alt_min1"]), "alt_min1_int": alt1_int,
            "alt_min2_code": clean_text(rec["alt_min2"]), "alt_min2_int": alt2_int,
            "sul_min1_code": clean_text(rec["sul_min1"]), "sul_min1_pc": sul_pc,
            "vn_type": clean_text(rec["vn_type"]), "vn_pc": vn_pc,
            "comment_raw": None if is_blank(rec["Comment"]) else str(rec["Comment"]),
            "sample_quality_code": clean_text(rec["sample_quality"]),
        })

    # Overlap / gap checks are per hole on the accepted intervals; violations are quarantined.
    by_hole: dict[str, list[dict]] = {}
    for interval in data.intervals:
        by_hole.setdefault(interval["hole_id"], []).append(interval)
    kept: list[dict] = []
    for hole_id, items in by_hole.items():
        items.sort(key=lambda r: (r["depth_from_m"], r["depth_to_m"]))
        previous_to = None
        for interval in items:
            if previous_to is not None and interval["depth_from_m"] < previous_to:
                data.quarantine.append({"entity_type": "INTERVAL", "entity_key": interval["interval_key"],
                                        "sheet": "Logging", "row": interval["source_row"],
                                        "reason": f"overlaps previous interval ending {previous_to}"})
                continue
            kept.append(interval)
            previous_to = interval["depth_to_m"]
    data.intervals = sorted(kept, key=lambda r: (r["hole_id"], r["depth_from_m"]))

    # ---- legend and reference lists ---------------------------------------------------------------------
    legend = sheets["Logging Legend"]
    legend_header = legend.header(LEGEND_HEADER_ROW)
    col = {name: legend_header.index(name) for name in ("Legend Reference", "Legend Value", "Description")}
    data.raw["Logging Legend"] = []
    legend_index: dict[tuple[str, str], dict] = {}
    for excel_row, values in legend.data_rows(LEGEND_HEADER_ROW):
        reference = clean_text(values[col["Legend Reference"]])
        value = clean_text(values[col["Legend Value"]])
        description = clean_text(values[col["Description"]])
        raw = {"legend_reference": reference, "legend_value": values[col["Legend Value"]],
               "description": values[col["Description"]]}
        data.raw["Logging Legend"].append({"source_row": excel_row, "values": raw, "payload": payload(raw)})
        if reference is None or value is None:
            data.quarantine.append({"entity_type": "CODE", "entity_key": f"row{excel_row}", "sheet": "Logging Legend",
                                    "row": excel_row, "reason": "legend row without reference or value"})
            continue
        legend_index[(reference, value)] = {"code_domain": reference, "code": value,
                                            "description": description or "", "legend_source_row": excel_row}
        if reference == "RockType":
            rock_codes[value] = description or ""
        if reference == "Weathering":
            weathering_codes[value] = description or ""

    reference_sheet_domains = {}
    for sheet_name in ("___LoggingReferences", "___SurveyReferences", "___CollarReferences", "___SheetInfo"):
        sheet = sheets.get(sheet_name)
        if sheet is None:
            continue
        if sheet_name == "___SheetInfo":
            for row_number in sorted(sheet.rows):
                values = sheet.rows[row_number]
                label = clean_text(values[0]) if values else None
                if label is None:
                    continue
                redact = "password" in label.lower()
                data.sheet_info.append({"sheet": sheet_name, "row": row_number, "label": label,
                                        "value": "[REDACTED: sheet-protection string present in source]" if redact
                                        else ("" if is_blank(values[1] if len(values) > 1 else None)
                                              else str(values[1])),
                                        "redacted": 1 if redact else 0})
            continue
        header = sheet.header(REFERENCE_HEADER_ROW)
        for column_index, column_name in enumerate(header):
            if not column_name:
                continue
            ordinal = 0
            for row_number in sorted(sheet.rows):
                if row_number <= REFERENCE_HEADER_ROW:
                    continue
                values = sheet.rows[row_number]
                cell = values[column_index] if column_index < len(values) else None
                if is_blank(cell):
                    continue
                ordinal += 1
                data.reference_values.append({"sheet": sheet_name, "row": row_number, "column": column_name,
                                              "ordinal": ordinal, "value": str(cell).strip(), "redacted": 0})
            if sheet_name == "___LoggingReferences":
                reference_sheet_domains[column_name] = [r["value"] for r in data.reference_values
                                                        if r["sheet"] == sheet_name and r["column"] == column_name]

    # Code dictionary rows: legend entries, plus a flag for agreement with the hidden reference lists.
    for (domain, value), entry in sorted(legend_index.items()):
        hidden = reference_sheet_domains.get(domain, [])
        data.codes.append({**entry,
                           "in_logging_legend": 1,
                           "in_hidden_reference": 1 if value in hidden else 0})
    data.legend_index = legend_index
    data.rock_codes = rock_codes
    data.weathering_codes = weathering_codes
    data.hidden_reference_domains = reference_sheet_domains
    data.legend_only_codes = sorted((d, v) for (d, v) in legend_index
                                    if v not in reference_sheet_domains.get(d, []))
    legend_pairs = set(legend_index)
    data.reference_only_codes = sorted((d, v) for d, vs in reference_sheet_domains.items()
                                       for v in vs if (d, v) not in legend_pairs)

    for name in ("Collars", "Surveys", "Logging"):
        data.skipped_blank_rows[name] = (sheets[name].max_row - 1) - len(data.raw[name])
    return data

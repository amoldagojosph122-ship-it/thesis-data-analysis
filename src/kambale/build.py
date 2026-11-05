"""Transactional ETL that builds obj1_master from the raw workbook copy.

Flow (one IMMEDIATE transaction after the run is recorded):
  hash and verify raw copy -> read cells -> curate -> insert raw rows (immutable, once per source)
  -> insert version-scoped curated rows -> evidence and candidate labels -> straight-hole geometry
  -> regional context -> QA/QC findings -> archive previous ACTIVE version, activate new one
  -> record export receipts (views now resolve to the new version) -> FK and integrity checks -> commit.

The dataset_version_key hashes the source SHA-256, ETL version and every configuration file that defines
a derivation. An identical key is a no-op (or re-activation of an archived identical version); it never
creates duplicate rows.
"""

from __future__ import annotations

import json
import sqlite3
import statistics
from dataclasses import asdict
from pathlib import Path

import yaml
from pyproj import Transformer

from kambale import geometry, labels, qaqc, regional
from kambale.config import CONFIG_DIR, DB_PATH, ETL_VERSION, PROJECT_ROOT, RAW_COPY_PATH, SOURCE_PATH
from kambale.curate import curate
from kambale.db import connect, fk_violations, integrity, migrate, sha256_text, utc_now
from kambale.source import ensure_raw_copy, read_workbook, sha256_file


class BuildStop(RuntimeError):
    """A STOP condition: the build is refused and the previous ACTIVE version is left untouched."""


def _load_config() -> dict:
    coordinate = yaml.safe_load((CONFIG_DIR / "coordinate_decisions.yaml").read_text(encoding="utf-8"))
    thresholds = yaml.safe_load((CONFIG_DIR / "qaqc_thresholds.yaml").read_text(encoding="utf-8"))
    label_set_version, rules = labels.load_rules(CONFIG_DIR / "label_rules.yaml")
    return {"coordinate": coordinate, "thresholds": thresholds, "label_set_version": label_set_version,
            "rules": rules}


def dataset_version_key(source_sha256: str, config: dict) -> str:
    material = {
        "source_sha256": source_sha256,
        "etl_version": ETL_VERSION,
        "label_set_version": config["label_set_version"],
        "rules": [asdict(r) for r in config["rules"]],
        "coordinate": config["coordinate"],
        "thresholds": config["thresholds"],
    }
    return sha256_text(json.dumps(material, sort_keys=True, ensure_ascii=False))


def build(db_path: Path = DB_PATH, source_path: Path = SOURCE_PATH, raw_copy: Path = RAW_COPY_PATH,
          shapefile: Path | None = None) -> dict:
    started = utc_now()
    conn = connect(db_path)
    try:
        applied = migrate(conn)
        source_hash = ensure_raw_copy(source_path, raw_copy)
        config = _load_config()
        key = dataset_version_key(source_hash, config)
        existing = conn.execute(
            "SELECT dataset_version_id, status FROM dataset_versions WHERE dataset_version_key = ?", (key,)
        ).fetchone()
        if existing is not None:
            if existing["status"] == "ACTIVE":
                return {"status": "NOOP_IDENTICAL", "dataset_version_id": existing["dataset_version_id"],
                        "dataset_version_key": key, "migrations_applied": applied}
            return _reactivate(conn, existing["dataset_version_id"], key, applied)

        source_file_id = _upsert_source_file(conn, source_hash, source_path, raw_copy)
        run_id = conn.execute(
            "INSERT INTO ingestion_runs (source_file_id, started_utc, etl_version, dataset_version_key, status) "
            "VALUES (?, ?, ?, ?, 'RUNNING')", (source_file_id, started, ETL_VERSION, key)).lastrowid
        try:
            summary = _full_build(conn, source_file_id, source_path, raw_copy, source_hash, key, config)
        except Exception as exc:
            conn.execute("UPDATE ingestion_runs SET finished_utc = ?, status = 'FAILED', message = ? "
                         "WHERE ingestion_run_id = ?", (utc_now(), str(exc)[:1000], run_id))
            raise
        conn.execute("UPDATE ingestion_runs SET finished_utc = ?, status = 'VERIFIED', message = ? "
                     "WHERE ingestion_run_id = ?",
                     (utc_now(), json.dumps(summary["counts"], sort_keys=True), run_id))
        summary["migrations_applied"] = applied
        return summary
    finally:
        conn.close()


def _reactivate(conn, dataset_version_id: int, key: str, applied: list[str]) -> dict:
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("UPDATE dataset_versions SET status = 'ARCHIVED', archived_utc = ? WHERE status = 'ACTIVE'",
                     (utc_now(),))
        conn.execute("UPDATE dataset_versions SET status = 'ACTIVE', activated_utc = ? "
                     "WHERE dataset_version_id = ?", (utc_now(), dataset_version_id))
        if fk_violations(conn) or integrity(conn) != "ok":
            raise BuildStop("integrity check failed on re-activation")
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    return {"status": "REACTIVATED", "dataset_version_id": dataset_version_id, "dataset_version_key": key,
            "migrations_applied": applied}


def _upsert_source_file(conn, source_hash, source_path, raw_copy) -> int:
    row = conn.execute("SELECT source_file_id FROM source_files WHERE sha256 = ?", (source_hash,)).fetchone()
    if row:
        return row["source_file_id"]
    cur = conn.execute(
        "INSERT INTO source_files (file_name, original_path, raw_copy_path, sha256, size_bytes, first_seen_utc, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (Path(source_path).name, str(source_path), str(raw_copy.relative_to(PROJECT_ROOT)).replace("\\", "/"),
         source_hash, Path(raw_copy).stat().st_size, utc_now(),
         "Original Excel workbook; raw copy is read-only and verified against this hash"))
    return cur.lastrowid


def _full_build(conn, source_file_id, source_path, raw_copy, source_hash, key, config) -> dict:
    created = utc_now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        sheets = read_workbook(raw_copy)
        data = curate(sheets)
        _record_sheets(conn, source_file_id, sheets, data)
        raw_ids = _insert_raw(conn, source_file_id, data)

        rules = config["rules"]
        rule_versions = {r.rule_id: r.rule_version for r in rules}
        coordinate = config["coordinate"]
        cur = conn.execute(
            "INSERT INTO dataset_versions (dataset_version_key, dataset_label, source_file_id, etl_version, "
            "rule_versions_json, coordinate_decision_json, status, created_utc) VALUES (?, ?, ?, ?, ?, ?, 'BUILDING', ?)",
            (key, f"obj1_master ETL {ETL_VERSION} key {key[:12]}", source_file_id, ETL_VERSION,
             json.dumps({"label_set_version": config["label_set_version"], "rules": rule_versions}, sort_keys=True),
             json.dumps(coordinate, sort_keys=True, ensure_ascii=False), created))
        dv = cur.lastrowid

        # ---- geometry inputs first (lines and coordinates are needed by holes and intervals) ----------
        lines = geometry.assign_drill_lines(data.collars)
        pairs = geometry.pair_discrepancies(data.collars)
        pair_stats = geometry.pair_statistics(pairs)
        points = [(c["utm_easting_m"], c["utm_northing_m"]) for c in data.collars]
        nn = geometry.nearest_neighbour_spacing(points)

        # ---- curated core ---------------------------------------------------------------------------------
        _insert_drill_lines(conn, dv, lines, data)
        _insert_holes(conn, dv, data, lines, raw_ids)
        survey_kind = _insert_surveys(conn, dv, data, raw_ids)
        _insert_codes(conn, dv, data)
        interval_ids = _insert_intervals(conn, dv, data, raw_ids)

        # ---- labels -----------------------------------------------------------------------------------
        legend_rock = {c["code"] for c in data.codes if c["code_domain"] == "RockType"}
        interval_status = _interval_status(data, legend_rock)
        evidence_rows = _insert_labels(conn, dv, data, interval_ids, rules, legend_rock)

        # ---- geometry -----------------------------------------------------------------------------
        build_id, geometry_count = _insert_geometry(conn, dv, data, interval_ids, survey_kind, pairs, pair_stats,
                                                    coordinate)

        # ---- regional context -----------------------------------------------------------------------
        regional_summary = _insert_regional(conn, data, config)

        # ---- QA/QC ------------------------------------------------------------------------------------
        context = _qaqc_context(data, sheets, source_hash, pairs, pair_stats, nn, lines, regional_summary,
                                interval_status, legend_rock)
        findings = qaqc.run_checks(data, evidence_rows, context)
        _insert_findings(conn, dv, findings)

        # ---- activate, then derive receipts from the active version ----------------------------------
        conn.execute("UPDATE dataset_versions SET status = 'ARCHIVED', archived_utc = ? WHERE status = 'ACTIVE'",
                     (created,))
        conn.execute("UPDATE dataset_versions SET status = 'ACTIVE', activated_utc = ?, overall_status = 'PROVISIONAL' "
                     "WHERE dataset_version_id = ?", (utc_now(), dv))
        receipts = _insert_receipts(conn, dv, source_hash, key, build_id)

        violations = fk_violations(conn)
        if violations:
            raise BuildStop(f"foreign_key_check returned {len(violations)} rows: {violations[:5]}")
        check = integrity(conn)
        if check != "ok":
            raise BuildStop(f"integrity_check returned {check!r}")
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise

    counts = {
        "raw_collars": len(data.raw["Collars"]), "raw_surveys": len(data.raw["Surveys"]),
        "raw_logging": len(data.raw["Logging"]), "raw_legend": len(data.raw["Logging Legend"]),
        "holes": len(data.collars), "survey_stations": len(data.surveys), "logging_intervals": len(data.intervals),
        "geological_codes": len(data.codes), "drill_lines": len(set(v["line_code"] for v in lines.values())),
        "geometry_intervals": geometry_count, "qaqc_findings": len(findings), "receipts": receipts,
        "quarantined": len(data.quarantine),
    }
    return {"status": "VERIFIED_NEW_VERSION", "dataset_version_id": dv, "dataset_version_key": key,
            "counts": counts, "overall_status": "PROVISIONAL",
            "label_rules": [r.rule_id for r in rules], "geometry_build_id": build_id}


# ----------------------------------------------------------------------------------------------------------
def _record_sheets(conn, source_file_id, sheets, data):
    for name, sheet in sheets.items():
        conn.execute(
            "INSERT OR IGNORE INTO source_sheets (source_file_id, sheet_name, sheet_state, n_rows, n_cols, "
            "header_json, blank_columns_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source_file_id, name, sheet.state, sheet.max_row, sheet.max_col,
             json.dumps(data.header_names.get(name, []), ensure_ascii=False),
             json.dumps(data.blank_columns.get(name, []), ensure_ascii=False)))


def _insert_raw(conn, source_file_id, data) -> dict:
    ids: dict[tuple[str, int], int] = {}
    specs = {
        "Collars": ("raw_collars", ["HoleID", "Grid", "HoleType", "Northing", "Easting", "RL", "UTMNorthing",
                                    "UTMEasting", "max_depth", "Project", "Prospect", "Contractor", "LoggedBy",
                                    "DateDrilled"]),
        "Surveys": ("raw_surveys", ["HoleID", "depth", "dip", "azimuth", "SurveyedBy", "Instrument"]),
        "Logging": ("raw_logging", ["HOLEID", "DEPTH_FROM", "DEPTH_TO", "rock_type1", "colour1", "colour2",
                                    "weathering", "grainsize", "structure", "alt_min1", "alt_min1int", "alt_min2",
                                    "alt_min2int", "sul_min1", "sul_min1pc", "vn_type", "vn_pc", "Comment",
                                    "sample_quality"]),
    }
    for sheet, (table, columns) in specs.items():
        for row in data.raw[sheet]:
            values = [row["values"][c] for c in columns]
            cols = ", ".join(f'"{c}"' for c in columns)
            marks = ", ".join("?" for _ in columns)
            conn.execute(
                f"INSERT OR IGNORE INTO {table} (source_file_id, source_sheet, source_row, {cols}, payload_json) "
                f"VALUES (?, ?, ?, {marks}, ?)",
                (source_file_id, sheet, row["source_row"], *values, row["payload"]))
            raw_id = conn.execute(
                f"SELECT rowid FROM {table} WHERE source_file_id = ? AND source_sheet = ? AND source_row = ?",
                (source_file_id, sheet, row["source_row"])).fetchone()[0]
            ids[(sheet, row["source_row"])] = raw_id
            conn.execute("INSERT OR IGNORE INTO raw_row_map (source_file_id, source_sheet, source_row, raw_table, "
                         "raw_rowid) VALUES (?, ?, ?, ?, ?)",
                         (source_file_id, sheet, row["source_row"], table, raw_id))
    for row in data.raw["Logging Legend"]:
        v = row["values"]
        conn.execute("INSERT OR IGNORE INTO raw_geological_legend (source_file_id, source_sheet, source_row, "
                     "legend_reference, legend_value, description, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (source_file_id, "Logging Legend", row["source_row"], v["legend_reference"], v["legend_value"],
                      v["description"], row["payload"]))
        ids[("Logging Legend", row["source_row"])] = conn.execute(
            "SELECT rowid FROM raw_geological_legend WHERE source_file_id = ? AND source_row = ?",
            (source_file_id, row["source_row"])).fetchone()[0]
    for ref in data.reference_values:
        conn.execute("INSERT OR IGNORE INTO raw_reference_lists (source_file_id, source_sheet, source_row, column_name, "
                     "ordinal, value, redacted) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (source_file_id, ref["sheet"], ref["row"], ref["column"], ref["ordinal"], ref["value"],
                      ref["redacted"]))
    for info in data.sheet_info:
        conn.execute("INSERT OR IGNORE INTO raw_reference_lists (source_file_id, source_sheet, source_row, column_name, "
                     "ordinal, value, redacted) VALUES (?, ?, ?, ?, 1, ?, ?)",
                     (source_file_id, info["sheet"], info["row"], info["label"], info["value"], info["redacted"]))
    return ids


def _insert_drill_lines(conn, dv, lines, data):
    counts = {}
    for interval in data.intervals:
        hole = lines[interval["hole_id"]]["line_code"]
        counts[hole] = counts.get(hole, 0) + 1
    by_line: dict[str, dict] = {}
    for hole_id, info in lines.items():
        entry = by_line.setdefault(info["line_code"], {"nominal": info["nominal_northing_m"], "holes": 0})
        entry["holes"] += 1
    for code, entry in sorted(by_line.items()):
        conn.execute("INSERT INTO drill_lines (dataset_version_id, line_code, nominal_northing_m, n_holes, n_intervals, "
                     "grouping_method, status) VALUES (?, ?, ?, ?, ?, ?, 'PROVISIONAL')",
                     (dv, code, entry["nominal"], entry["holes"], counts.get(code, 0),
                      "Exact nominal Northing (Collars.Northing) cluster; not an approved spatial split"))


def _insert_holes(conn, dv, data, lines, raw_ids):
    for c in data.collars:
        info = lines[c["hole_id"]]
        conn.execute(
            "INSERT INTO holes (dataset_version_id, hole_id, raw_hole_id, raw_collars_id, hole_type, grid_label, "
            "easting_alt_m, northing_alt_m, utm_easting_m, utm_northing_m, line_code, rl_status, rl_m, max_depth_m, "
            "project_code, prospect, contractor, logged_by, date_drilled, date_drilled_raw) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (dv, c["hole_id"], c["raw_hole_id"], raw_ids[("Collars", c["source_row"])], c["hole_type"],
             c["grid_label"], c["easting_alt_m"], c["northing_alt_m"], c["utm_easting_m"], c["utm_northing_m"],
             info["line_code"], c["rl_status"], c["rl_m"], c["max_depth_m"], c["project_code"], c["prospect"],
             c["contractor"], c["logged_by"], c["date_drilled"], c["date_drilled_raw"]))


def _insert_surveys(conn, dv, data, raw_ids) -> dict[str, str]:
    per_hole: dict[str, list[dict]] = {}
    for s in data.surveys:
        per_hole.setdefault(s["hole_id"], []).append(s)
    max_depth = {c["hole_id"]: c["max_depth_m"] for c in data.collars}
    kinds = {}
    for hole_id, stations in per_hole.items():
        if len(stations) > 1:
            kinds[hole_id] = "MULTI_STATION"
        elif abs(stations[0]["depth_m"] - max_depth[hole_id]) < 1e-6:
            kinds[hole_id] = "END_OF_HOLE_ONLY"
        else:
            kinds[hole_id] = "SINGLE_STATION_OTHER"
    for s in data.surveys:
        conn.execute(
            "INSERT INTO survey_stations (dataset_version_id, hole_id, raw_surveys_id, depth_m, dip_deg, azimuth_deg, "
            "station_kind, surveyed_by, instrument, convention_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PROVISIONAL')",
            (dv, s["hole_id"], raw_ids[("Surveys", s["source_row"])], s["depth_m"], s["dip_deg"], s["azimuth_deg"],
             kinds[s["hole_id"]], s["surveyed_by"], s["instrument"]))
    return kinds


def _insert_codes(conn, dv, data):
    for code in data.codes:
        conn.execute(
            "INSERT INTO geological_code_dictionary (dataset_version_id, code_domain, code, description, "
            "legend_source_row, in_logging_legend, in_hidden_reference) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (dv, code["code_domain"], code["code"], code["description"], code["legend_source_row"],
             code["in_logging_legend"], code["in_hidden_reference"]))


def _insert_intervals(conn, dv, data, raw_ids) -> dict[str, int]:
    legend_rock = {c["code"]: c["description"] for c in data.codes if c["code_domain"] == "RockType"}
    legend_weather = {c["code"] for c in data.codes if c["code_domain"] == "Weathering"}
    ids = {}
    for i in data.intervals:
        status = labels.rock_status(i["rock_code_raw"], set(legend_rock))
        if i["weathering_code"] is None:
            weather_status = "MISSING"
        else:
            weather_status = "VALID" if i["weathering_code"] in legend_weather else "UNSUPPORTED"
        cur = conn.execute(
            "INSERT INTO logging_intervals (dataset_version_id, interval_key, hole_id, raw_logging_id, source_row, "
            "depth_from_m, depth_to_m, interval_length_m, midpoint_m, rock_code_raw, rock_code_status, rock_description, "
            "colour1_code, colour2_code, weathering_code, weathering_status, grainsize_raw, structure_code, "
            "alt_min1_code, alt_min1_int, alt_min2_code, alt_min2_int, sul_min1_code, sul_min1_pc, vn_type, vn_pc, "
            "comment_raw, sample_quality_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?)",
            (dv, i["interval_key"], i["hole_id"], raw_ids[("Logging", i["source_row"])], i["source_row"],
             i["depth_from_m"], i["depth_to_m"], i["interval_length_m"], i["midpoint_m"], i["rock_code_raw"], status,
             legend_rock.get(i["rock_code_raw"]) if status == "VALID" else None,
             i["colour1_code"], i["colour2_code"], i["weathering_code"], weather_status, i["grainsize_raw"],
             i["structure_code"], i["alt_min1_code"], i["alt_min1_int"], i["alt_min2_code"], i["alt_min2_int"],
             i["sul_min1_code"], i["sul_min1_pc"], i["vn_type"], i["vn_pc"], i["comment_raw"],
             i["sample_quality_code"]))
        ids[i["interval_key"]] = cur.lastrowid
    return ids


def _interval_status(data, legend_rock) -> list[dict]:
    out = []
    for i in data.intervals:
        status = labels.rock_status(i["rock_code_raw"], legend_rock)
        out.append({"interval_key": i["interval_key"], "rock_code_status": status, "rock_code_raw": i["rock_code_raw"],
                    "source_row": i["source_row"], "weathering_code": i["weathering_code"],
                    "colour1_code": i["colour1_code"], "comment_raw": i["comment_raw"]})
    return out


def _insert_labels(conn, dv, data, interval_ids, rules, legend_rock) -> list[dict]:
    for rule in rules:
        conn.execute(
            "INSERT OR IGNORE INTO graphite_label_rules (rule_id, rule_version, rule_family, description, "
            "definition_sha256, status, created_utc) VALUES (?, ?, ?, ?, ?, 'PROPOSED', ?)",
            (rule.rule_id, rule.rule_version, rule.family, rule.description, rule.definition_sha256, utc_now()))
    evidence_out = []
    for i in data.intervals:
        status = labels.rock_status(i["rock_code_raw"], legend_rock)
        ev = labels.evidence(i, status)
        interval_id = interval_ids[i["interval_key"]]
        conn.execute(
            "INSERT INTO interval_label_evidence (dataset_version_id, interval_id, rock_code_status, is_sgs, "
            "has_gr_mineral, comment_present, comment_graphitic, comment_trace_qualified, comment_term, "
            "positive_indicators, negative_indicators, label_conflict, evidence_pattern, label_review_status, rationale) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (dv, interval_id, ev["rock_code_status"], ev["is_sgs"], ev["has_gr_mineral"], ev["comment_present"],
             ev["comment_graphitic"], ev["comment_trace_qualified"], ev["comment_term"], ev["positive_indicators"],
             ev["negative_indicators"], ev["label_conflict"], ev["evidence_pattern"], ev["label_review_status"],
             ev["rationale"]))
        for rule in rules:
            label, state = labels.rule_label(rule, ev)
            conn.execute(
                "INSERT INTO interval_labels (dataset_version_id, interval_id, rule_id, label, label_state, "
                "rule_status_at_derivation) VALUES (?, ?, ?, ?, ?, 'PROPOSED')",
                (dv, interval_id, rule.rule_id, label, state))
        evidence_out.append({**ev, "interval_key": i["interval_key"], "source_row": i["source_row"]})
    return evidence_out


def _insert_geometry(conn, dv, data, interval_ids, survey_kind, pairs, pair_stats, coordinate):
    crs_key = coordinate["crs_key"]
    conn.execute(
        "INSERT OR IGNORE INTO coordinate_system_registry (crs_key, authority_code, crs_name, projection, zone, "
        "datum_name, datum_status, horizontal_units, evidence, status) VALUES "
        "('EPSG:32630', '32630', 'WGS 84 / UTM zone 30N (declared)', 'Transverse Mercator', '30N', 'UNVERIFIED', "
        "'UNVERIFIED', 'm', 'Collars.Grid = UTM_30N; regional geology_polygon.prj = WGS_1984_UTM_Zone_30N', 'PROVISIONAL')")
    cur = conn.execute(
        "INSERT INTO coordinate_decisions (dataset_version_id, adopted_pair, crs_key, units, transform_chain, rationale, "
        "n_holes, median_pair_discrepancy_m, max_pair_discrepancy_m, status) VALUES (?, 'UTM_EASTING_NORTHING', ?, 'm', "
        "?, ?, ?, ?, ?, 'PROVISIONAL')",
        (dv, crs_key, coordinate["transform_chain"], " ".join(coordinate["rationale"].split()),
         pair_stats["n"], pair_stats["median_m"], pair_stats["max_m"]))
    decision_id = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO geometry_builds (dataset_version_id, coordinate_decision_id, elevation_source_id, method, "
        "convention_text, angle_status, geometry_status, n_intervals, created_utc) VALUES (?, ?, 1, "
        "'STRAIGHT_HOLE_EOH_ORIENTATION', ?, 'PROVISIONAL', 'PROVISIONAL_RELATIVE', ?, ?)",
        (dv, decision_id, json.dumps(coordinate["geometry"], sort_keys=True, ensure_ascii=False),
         len(data.intervals), utc_now()))
    build_id = cur.lastrowid
    collar = {c["hole_id"]: c for c in data.collars}
    surveys = {}
    for s in data.surveys:
        surveys.setdefault(s["hole_id"], []).append(s)
    written = 0
    for i in data.intervals:
        stations = surveys.get(i["hole_id"], [])
        if len(stations) != 1:
            continue  # no straight-hole orientation available; reported by QA/QC (QC-NO-SURVEY / QC-SURVEY-STATIONS)
        c = collar[i["hole_id"]]
        s = stations[0]
        off = geometry.straight_hole_offsets(i["midpoint_m"], s["dip_deg"], s["azimuth_deg"])
        e = c["utm_easting_m"] + off.delta_e
        n = c["utm_northing_m"] + off.delta_n
        conn.execute(
            "INSERT INTO interval_coordinates (geometry_build_id, interval_id, midpoint_m, dip_deg, azimuth_deg, "
            "delta_e_m, delta_n_m, delta_z_m, easting_m, northing_m, z_relative_m, z_reference, z_absolute_m, "
            "elevation_source_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RELATIVE_TO_COLLAR', NULL, 1)",
            (build_id, interval_ids[i["interval_key"]], i["midpoint_m"], s["dip_deg"], s["azimuth_deg"],
             off.delta_e, off.delta_n, off.delta_z, round(e, 4), round(n, 4), off.delta_z))
        written += 1
    return build_id, written


def _insert_regional(conn, data, config) -> dict:
    collars_utm = [(c["utm_easting_m"], c["utm_northing_m"]) for c in data.collars]
    source_hash, rows, summary = regional.extract_context(
        collars_utm, float(config["thresholds"]["regional_buffer_m"]))
    for r in rows:
        conn.execute(
            "INSERT OR IGNORE INTO regional_geology_context (source_sha256, feature_index, geo_symbol, stratigraphy, "
            "legend_text, metamorphism, geom_wkt, centroid_e_m, centroid_n_m, intersects_collar_buffer, scale_note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (source_hash, r["feature_index"], r["geo_symbol"], r["stratigraphy"], r["legend_text"], r["metamorphism"],
             r["geom_wkt"], r["centroid_e_m"], r["centroid_n_m"], r["intersects_collar_buffer"], r["scale_note"]))
    summary["source_sha256"] = source_hash
    return summary


def _qaqc_context(data, sheets, source_hash, pairs, pair_stats, nn, lines, regional_summary, interval_status,
                  legend_rock) -> dict:
    line_counts: dict[str, int] = {}
    for info in lines.values():
        line_counts[info["line_code"]] = line_counts.get(info["line_code"], 0) + 1
    line_summary = [{"line_code": k, "n_holes": v} for k, v in sorted(line_counts.items())]
    legend_codes_used = {i["rock_code_raw"] for i in data.intervals if i["rock_code_raw"] is not None}
    weather_used = {i["weathering_code"] for i in data.intervals if i["weathering_code"] is not None}
    unused_rock = sorted(c for c in legend_rock if c not in legend_codes_used)
    unused_weather = sorted(c["code"] for c in data.codes if c["code_domain"] == "Weathering"
                            and c["code"] not in weather_used)
    grain = [i["grainsize_raw"] for i in data.intervals if i["grainsize_raw"] is not None]
    intensity_rows = [i for i in data.intervals if i["alt_min1_int"] is not None]
    crs_text = ("Declared EPSG:32630 (WGS 84 / UTM 30N) from Grid label UTM_30N and regional .prj; "
                "datum not verified in workbook")
    transformer = Transformer.from_crs(32630, 4326, always_xy=True)
    lons, lats = [], []
    for c in data.collars:
        lon, lat = transformer.transform(c["utm_easting_m"], c["utm_northing_m"])
        lons.append(lon)
        lats.append(lat)
    inside = (min(lats) >= 4.5 and max(lats) <= 11.5 and min(lons) >= -3.5 and max(lons) <= 1.5)
    plaus_text = (f"UTM 30N collars transform to lat {min(lats):.4f} to {max(lats):.4f} N and lon "
                  f"{min(lons):.4f} to {max(lons):.4f} E; inside approximate Ghana extent (lat 4.5-11.5 N, "
                  f"lon 3.5 W-1.5 E). Plausibility only; does not verify datum.")
    return {
        "source_hash": source_hash,
        "raw_hash": sha256_file(RAW_COPY_PATH),
        "sheet_states": {name: sheet.state for name, sheet in sheets.items()},
        "row_counts": {"Collars": len(data.raw["Collars"]), "Surveys": len(data.raw["Surveys"]),
                       "Logging": len(data.raw["Logging"]), "Logging Legend": len(data.raw["Logging Legend"])},
        "pair_rows": pairs,
        "pair_stats": pair_stats,
        "nn_median_m": statistics.median(nn),
        "grid_nodes": qaqc.grid_nodes(data.collars),
        "crs_status": crs_text,
        "plausibility": {"inside": inside, "text": plaus_text},
        "line_summary": line_summary,
        "regional": regional_summary,
        "interval_status": interval_status,
        "legend": {"legend_only": [f"{d}:{v}" for d, v in data.legend_only_codes],
                   "reference_only": [f"{d}:{v}" for d, v in data.reference_only_codes],
                   "unused_rock": unused_rock, "unused_weathering": unused_weather},
        "grain_values": {"n": len(grain), "distinct": sorted(set(grain))},
        "intensity": {"n": len(intensity_rows),
                      "orphans": sum(1 for i in intensity_rows if i["alt_min1_code"] is None)},
    }


def _insert_findings(conn, dv, findings):
    for check in qaqc.check_catalogue_rows():
        conn.execute("INSERT OR IGNORE INTO qaqc_checks (check_id, category, description, default_severity, "
                     "scope_if_failed, method) VALUES (?, ?, ?, ?, ?, ?)",
                     (check["check_id"], check["category"], check["description"], check["default_severity"],
                      check["scope_if_failed"], check["method"]))
    now = utc_now()
    for f in findings:
        cur = conn.execute(
            "INSERT INTO qaqc_findings (dataset_version_id, check_id, severity, status, result, entity_type, entity_key, "
            "source_sheet, source_row, n_records, detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (dv, f.check_id, f.severity, f.status, f.result, f.entity_type, f.entity_key, f.source_sheet,
             f.source_row, f.n_records, f.detail))
        if f.action:
            conn.execute("INSERT INTO qaqc_resolutions (finding_id, action, decided_by, decided_utc, rationale) "
                         "VALUES (?, ?, ?, ?, ?)",
                         (cur.lastrowid, f.action, f"pipeline:{ETL_VERSION}", now, f.rationale or ""))


def _insert_receipts(conn, dv, source_hash, key, build_id) -> int:
    count = 0

    def view_text(name: str) -> str:
        return conn.execute("SELECT sql FROM sqlite_master WHERE type = 'view' AND name = ?", (name,)).fetchone()[0]

    def digest(values: list[str]) -> str:
        return sha256_text("\n".join(values))

    rule_ids = [r[0] for r in conn.execute("SELECT rule_id FROM graphite_label_rules ORDER BY rule_id")]
    for rule_id in rule_ids:
        keys = [r[0] for r in conn.execute(
            "SELECT i.interval_key FROM v_label_candidates c JOIN v_intervals i ON i.interval_id = c.interval_id "
            "WHERE c.rule_id = ? ORDER BY i.interval_key", (rule_id,))]
        status = conn.execute("SELECT status FROM graphite_label_rules WHERE rule_id = ?", (rule_id,)).fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO dataset_export_receipts (dataset_version_id, canonical_dataset_id, "
            "source_workbook_sha256, label_rule_id, label_rule_status, geometry_build_id, crs_key, vertical_datum_status, "
            "export_name, selected_sql_sha256, row_count, ordered_id_digest, status, exported_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, 'EPSG:32630', 'NO_ELEVATION_SOURCE_RELATIVE_Z_ONLY', ?, ?, ?, ?, 'PROVISIONAL', ?)",
            (dv, f"obj1_master:{key[:12]}", source_hash, rule_id, status, build_id, f"interval_labels:{rule_id}",
             sha256_text(view_text("v_label_candidates") + rule_id), len(keys), digest(keys), utc_now()))
        count += 1
    for name, view, label_rule in (("interval_flags", "v_interval_flags", None),
                                   ("hole_summary", "v_hole_graphite", None),
                                   ("interval_geometry", "v_interval_geometry", None)):
        if view == "v_interval_flags":
            keys = [r[0] for r in conn.execute("SELECT interval_key FROM v_interval_flags ORDER BY interval_key")]
        elif view == "v_hole_graphite":
            keys = [r[0] for r in conn.execute("SELECT hole_id FROM v_hole_graphite ORDER BY hole_id")]
        else:
            keys = [r[0] for r in conn.execute("SELECT interval_key FROM v_interval_geometry ORDER BY interval_key")]
        conn.execute(
            "INSERT OR IGNORE INTO dataset_export_receipts (dataset_version_id, canonical_dataset_id, "
            "source_workbook_sha256, label_rule_id, label_rule_status, geometry_build_id, crs_key, vertical_datum_status, "
            "export_name, selected_sql_sha256, row_count, ordered_id_digest, status, exported_utc) "
            "VALUES (?, ?, ?, ?, ?, ?, 'EPSG:32630', 'NO_ELEVATION_SOURCE_RELATIVE_Z_ONLY', ?, ?, ?, ?, 'PROVISIONAL', ?)",
            (dv, f"obj1_master:{key[:12]}", source_hash, label_rule, None, build_id, name,
             sha256_text(view_text(view)), len(keys), digest(keys), utc_now()))
        count += 1
    return count

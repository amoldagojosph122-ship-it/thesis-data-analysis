"""Read-only import of the active Objective 1 snapshot, with source receipts and the input gates G01 to G06."""

from __future__ import annotations

import json
from pathlib import Path

from kambale.objective_2.config import (StopError, UPSTREAM_DB_PATH, code_commit, load_config, sha256_text, utc_now)
from kambale.objective_2.db import connect_o2, connect_upstream_readonly

REQUIRED_VIEWS = ("v_active_version", "v_interval_geometry", "v_interval_design", "v_drill_lines", "v_holes", "v_survey")
REQUIRED_TABLES = ("graphite_label_rules", "coordinate_decisions", "coordinate_system_registry", "geometry_builds")
REQUIRED_COLUMNS = {
    "v_interval_geometry": ("interval_id", "interval_key", "hole_id", "line_code", "depth_from_m", "depth_to_m",
                            "midpoint_m", "interval_length_m", "rock_code_raw", "rock_code_status", "weathering_code",
                            "easting_m", "northing_m", "z_relative_m", "z_absolute_m", "geometry_status"),
    "v_interval_design": ("interval_id", "design_state", "design_label"),
    "v_holes": ("hole_id", "line_code", "utm_easting_m", "utm_northing_m", "max_depth_m"),
    "v_survey": ("hole_id", "dip_deg", "azimuth_deg"),
}

# Specification 04, section 3. The text is hashed and stored as selection_query_sha256.
IMPORT_QUERY = """SELECT g.interval_id, g.interval_key, g.hole_id, g.line_code, g.depth_from_m, g.depth_to_m,
       g.midpoint_m, g.interval_length_m AS support_length_m, g.weathering_code,
       g.rock_code_raw, g.rock_code_status, g.easting_m, g.northing_m, g.z_relative_m,
       g.geometry_status, d.design_state AS label_state, d.design_label AS indicator
FROM v_interval_geometry g
JOIN v_interval_design d ON d.interval_id = g.interval_id
ORDER BY g.interval_key"""


def _check_objects(up) -> None:
    present = {r[0] for r in up.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    for name in REQUIRED_VIEWS + REQUIRED_TABLES:
        if name not in present:
            raise StopError(f"upstream object missing: {name}")
    for view, cols in REQUIRED_COLUMNS.items():
        have = {r[1] for r in up.execute(f"PRAGMA table_info({view})")}
        for col in cols:
            if col not in have:
                raise StopError(f"upstream column missing: {view}.{col}")


def _gates(up, label_rule_id: str) -> dict:
    """Input gates G01 to G06 on the upstream snapshot. Returns the values stored in source_receipts."""
    version = up.execute("SELECT dataset_version_id, dataset_version_key, etl_version FROM v_active_version").fetchone()
    if version is None:
        raise StopError("no ACTIVE upstream dataset version")
    vid = version["dataset_version_id"]
    rule = up.execute("SELECT status, definition_sha256 FROM graphite_label_rules WHERE rule_id = ?",
                      (label_rule_id,)).fetchone()
    if rule is None or rule["status"] != "APPROVED":
        raise StopError(f"G02 label rule {label_rule_id} is not APPROVED")
    coord = up.execute("SELECT status FROM coordinate_decisions WHERE dataset_version_id = ?", (vid,)).fetchone()
    if coord is None or coord["status"] != "APPROVED":
        raise StopError("G04 coordinate decision is not APPROVED")
    datum = up.execute("SELECT datum_status FROM coordinate_system_registry WHERE crs_key = 'EPSG:32630'").fetchone()
    if datum is None or datum["datum_status"] != "VERIFIED":
        raise StopError("G04 datum is not VERIFIED for EPSG:32630")
    lines = up.execute("SELECT COUNT(*) AS n, SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) AS a FROM v_drill_lines").fetchone()
    if lines["n"] == 0 or lines["n"] != lines["a"]:
        raise StopError("G05 drill-line grouping is not fully APPROVED")
    geom = up.execute("SELECT geometry_build_id, geometry_status FROM geometry_builds WHERE dataset_version_id = ?",
                      (vid,)).fetchone()
    if geom is None or geom["geometry_status"] != "PROVISIONAL_RELATIVE":
        raise StopError("G03 geometry status is not PROVISIONAL_RELATIVE")
    absolute = up.execute("SELECT COUNT(*) FROM v_interval_geometry WHERE z_absolute_m IS NOT NULL").fetchone()[0]
    if absolute != 0:
        raise StopError("G03 z_absolute_m is populated; absolute elevations must not enter Objective 2")
    support = up.execute("SELECT COUNT(*) FROM v_interval_geometry WHERE ABS(interval_length_m - 1.0) > 1e-9").fetchone()[0]
    if support != 0:
        raise StopError("G06 interval support differs from 1 m")
    return {
        "version": dict(version), "rule": dict(rule), "geometry_build_id": geom["geometry_build_id"],
        "geometry_status": geom["geometry_status"], "lines_approved": lines["a"],
    }


def import_snapshot(upstream: Path = UPSTREAM_DB_PATH, o2_path: Path | None = None,
                    config_path: Path | None = None) -> dict:
    """Verify the upstream gates and store the receipt and observations. Re-running with the same content reuses the receipt."""
    from kambale.objective_2.config import O2_CONFIG_PATH, O2_DB_PATH
    config, config_sha = load_config(config_path or O2_CONFIG_PATH)
    label_rule_id = config["label_rule"]["id"]
    up = connect_upstream_readonly(upstream)
    try:
        _check_objects(up)
        gates = _gates(up, label_rule_id)
        rows = [dict(r) for r in up.execute(IMPORT_QUERY)]
        holes = [dict(r) for r in up.execute("SELECT hole_id, line_code, utm_easting_m, utm_northing_m, max_depth_m FROM v_holes ORDER BY hole_id")]
        orientation = [tuple(r) for r in up.execute("SELECT DISTINCT dip_deg, azimuth_deg FROM v_survey")]
        expected = up.execute("SELECT COUNT(*) FROM v_interval_geometry").fetchone()[0]
    finally:
        up.close()
    if len(rows) != expected:
        raise StopError(f"G01 row count {len(rows)} differs from upstream {expected}")

    canonical = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    content_sha = sha256_text(canonical)
    ordered_digest = sha256_text("\n".join(r["interval_key"] for r in rows))
    query_sha = sha256_text(IMPORT_QUERY)

    conn = connect_o2(o2_path or O2_DB_PATH)
    try:
        existing = conn.execute("SELECT receipt_id FROM source_receipts WHERE upstream_dataset_version_key = ? AND content_sha256 = ?",
                                (gates["version"]["dataset_version_key"], content_sha)).fetchone()
        run_id = conn.execute("INSERT INTO stage_runs (run_kind, config_version, config_sha256, started_utc, status, code_commit, note) "
                              "VALUES ('IMPORT', ?, ?, ?, 'RUNNING', ?, ?)",
                              (config["config_version"], config_sha, utc_now(), code_commit(),
                               "reused receipt" if existing else "new receipt")).lastrowid
        if existing:
            receipt_id = existing["receipt_id"]
            reused = True
        else:
            conn.execute("BEGIN IMMEDIATE")
            try:
                receipt_id = conn.execute(
                    "INSERT INTO source_receipts (upstream_logical_name, upstream_path, upstream_dataset_version_id, "
                    "upstream_dataset_version_key, upstream_etl_version, label_rule_id, label_rule_status, "
                    "label_rule_definition_sha256, geometry_build_id, geometry_status, crs_key, crs_datum_status, "
                    "coordinate_pair_status, drill_line_status, vertical_basis, content_sha256, row_count, ordered_id_digest, "
                    "selection_query_sha256, imported_utc, code_commit) "
                    "VALUES ('obj1_master', ?, ?, ?, ?, ?, 'APPROVED', ?, ?, 'PROVISIONAL_RELATIVE', 'EPSG:32630', 'VERIFIED', "
                    "'APPROVED', 'APPROVED', 'RELATIVE_TO_COLLAR', ?, ?, ?, ?, ?, ?)",
                    (UPSTREAM_DB_PATH.as_posix(), gates["version"]["dataset_version_id"], gates["version"]["dataset_version_key"],
                     gates["version"]["etl_version"], label_rule_id, gates["rule"]["definition_sha256"],
                     gates["geometry_build_id"], content_sha, len(rows), ordered_digest, query_sha, utc_now(),
                     code_commit())).lastrowid
                for r in rows:
                    binary = r["label_state"] in ("POSITIVE", "NEGATIVE")
                    conn.execute(
                        "INSERT INTO analysis_observations (receipt_id, upstream_interval_id, upstream_interval_key, hole_id, "
                        "line_code, depth_from_m, depth_to_m, support_length_m, midpoint_m, weathering_code, rock_code_raw, "
                        "rock_code_status, label_state, in_binary_target, indicator, easting_m, northing_m, z_relative_m, "
                        "geometry_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (receipt_id, r["interval_id"], r["interval_key"], r["hole_id"], r["line_code"], r["depth_from_m"],
                         r["depth_to_m"], r["support_length_m"], r["midpoint_m"], r["weathering_code"], r["rock_code_raw"],
                         r["rock_code_status"], r["label_state"], 1 if binary else 0,
                         int(r["indicator"]) if binary else None, r["easting_m"], r["northing_m"], r["z_relative_m"],
                         r["geometry_status"]))
                for h in holes:
                    conn.execute("INSERT INTO collar_locations (receipt_id, hole_id, line_code, utm_easting_m, utm_northing_m, "
                                 "max_depth_m) VALUES (?, ?, ?, ?, ?, ?)",
                                 (receipt_id, h["hole_id"], h["line_code"], h["utm_easting_m"], h["utm_northing_m"],
                                  h["max_depth_m"]))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            reused = False
        conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ?, receipt_id = ? WHERE run_id = ?",
                     (utc_now(), receipt_id, run_id))
    finally:
        conn.close()
    return {"receipt_id": receipt_id, "run_id": run_id, "reused": reused, "row_count": len(rows),
            "content_sha256": content_sha, "dataset_version_id": gates["version"]["dataset_version_id"],
            "label_rule_id": label_rule_id, "orientation": orientation, "n_holes": len(holes)}

"""Read-only import of the active Objective 1 snapshot and the Objective 2 handoff, with receipts and input gates."""

from __future__ import annotations

import json
from pathlib import Path

from kambale.objective_3.config import (O2_DB_PATH, O3_DB_PATH, StopError, UPSTREAM_DB_PATH, code_commit, load_config,
                                        sha256_text, utc_now)
from kambale.objective_3.db import connect_o3, connect_readonly

REQUIRED_O1_VIEWS = ("v_active_version", "v_interval_geometry", "v_interval_design", "v_drill_lines", "v_holes", "v_survey")
REQUIRED_O1_TABLES = ("graphite_label_rules", "coordinate_decisions", "coordinate_system_registry", "geometry_builds",
                      "coordinate_pair_approvals", "drill_line_approvals", "label_reviews")
REQUIRED_COLUMNS = {
    "v_interval_geometry": ("interval_id", "interval_key", "hole_id", "line_code", "depth_from_m", "depth_to_m",
                            "midpoint_m", "interval_length_m", "rock_code_raw", "rock_code_status", "weathering_code",
                            "easting_m", "northing_m", "z_relative_m", "z_absolute_m", "geometry_status"),
    "v_interval_design": ("interval_id", "design_state", "design_label"),
    "v_holes": ("hole_id", "line_code", "utm_easting_m", "utm_northing_m", "max_depth_m"),
    "v_survey": ("hole_id", "dip_deg", "azimuth_deg"),
}

IMPORT_QUERY = """SELECT g.interval_id, g.interval_key, g.hole_id, g.line_code, g.depth_from_m, g.depth_to_m,
       g.midpoint_m, g.interval_length_m AS support_length_m, g.weathering_code,
       g.rock_code_raw, g.rock_code_status, g.easting_m, g.northing_m, g.z_relative_m,
       g.geometry_status, d.design_state AS label_state, d.design_label AS indicator
FROM v_interval_geometry g
JOIN v_interval_design d ON d.interval_id = g.interval_id
ORDER BY g.interval_key"""

FEATURES = (
    # feature_id, name, source_table, units, dtype, available_at_prediction, basis, designation, rationale
    ("F_EASTING", "easting_m", "analysis_observations", "m", "REAL", 1,
     "UTM 30N easting is defined for every observation and every held-out interval in an existing hole.",
     "SAFE", "Planar coordinate; not derived from the target."),
    ("F_NORTHING", "northing_m", "analysis_observations", "m", "REAL", 1,
     "UTM 30N northing is defined for every observation and every held-out interval in an existing hole.",
     "SAFE", "Planar coordinate; not derived from the target."),
    ("F_ZREL", "z_relative_m", "analysis_observations", "m", "REAL", 1,
     "Metres relative to collar; defined for every held-out interval because the collar and straight-hole geometry exist.",
     "SAFE", "Relative vertical position; z_absolute_m is never used."),
    ("F_HOLE", "hole_id", "analysis_observations", None, "TEXT", 0,
     "Identifier; held-out holes would be unseen categories.",
     "IDENTIFIER", "Using it would memorise holes and leak the spatial split."),
    ("F_LINE", "line_code", "analysis_observations", None, "TEXT", 0,
     "Identifier and the outer split variable.",
     "IDENTIFIER", "Using it would leak the held-out line identity."),
    ("F_ROCK", "rock_code_raw", "analysis_observations", None, "TEXT", 0,
     "Logged lithology exists only where a hole exists and is direct label evidence.",
     "TARGET_DERIVED", "The approved rule classifies graphite from rock type and mineral evidence."),
    ("F_ROCKSTATUS", "rock_code_status", "analysis_observations", None, "TEXT", 0,
     "Log quality flag; exists only at logged intervals.",
     "TARGET_DERIVED", "Rock-code validity is part of the label rule."),
    ("F_WEATHER", "weathering_code", "analysis_observations", None, "TEXT", 0,
     "Weathering is logged only where a hole exists and is absent at prediction voxels.",
     "LOG_ONLY", "Not a mapped covariate; using it would not be deployable."),
    ("F_LABEL", "label_state", "analysis_observations", None, "TEXT", 0,
     "The approved label state.",
     "TARGET_DERIVED", "Direct target."),
    ("F_INDICATOR", "indicator", "analysis_observations", None, "INTEGER", 0,
     "The binary target.",
     "TARGET_DERIVED", "Direct target."),
    ("F_BINARY", "in_binary_target", "analysis_observations", None, "INTEGER", 0,
     "Target eligibility flag.",
     "TARGET_DERIVED", "Direct target."),
    ("F_DESIGNLABEL", "design_label", "v_interval_design", None, "INTEGER", 0,
     "The approved rule's binary output.",
     "TARGET_DERIVED", "Direct target."),
    ("F_SGS", "is_sgs", "v_interval_design", None, "INTEGER", 0,
     "Rock-type indicator that contributes to the label.",
     "TARGET_DERIVED", "Label evidence."),
    ("F_GRMIN", "has_gr_mineral", "v_interval_design", None, "INTEGER", 0,
     "Mineral evidence that contributes to the label.",
     "TARGET_DERIVED", "Label evidence."),
    ("F_COMMENT", "comment_raw", "v_interval_design", None, "TEXT", 0,
     "Free-text geological comment; part of the label evidence.",
     "TARGET_DERIVED", "Label evidence."),
    ("F_POSIND", "positive_indicators", "v_interval_design", None, "INTEGER", 0,
     "Count of positive label indicators.",
     "TARGET_DERIVED", "Label evidence."),
    ("F_NEGIND", "negative_indicators", "v_interval_design", None, "INTEGER", 0,
     "Count of negative label indicators.",
     "TARGET_DERIVED", "Label evidence."),
    ("F_PATTERN", "evidence_pattern", "v_interval_design", None, "TEXT", 0,
     "Encoded combination of label evidence.",
     "TARGET_DERIVED", "Label evidence."),
    ("F_DEPTHFROM", "depth_from_m", "analysis_observations", "m", "REAL", 0,
     "Along-hole depth; defined only inside a hole and collinear with z_relative_m under the straight-hole model.",
     "LOG_ONLY", "Redundant with z_relative_m and tied to sampling geometry."),
    ("F_DEPTHTO", "depth_to_m", "analysis_observations", "m", "REAL", 0,
     "Along-hole depth; defined only inside a hole and collinear with z_relative_m under the straight-hole model.",
     "LOG_ONLY", "Redundant with z_relative_m and tied to sampling geometry."),
    ("F_MID", "midpoint_m", "analysis_observations", "m", "REAL", 0,
     "Along-hole midpoint; defined only inside a hole.",
     "LOG_ONLY", "Redundant with z_relative_m and tied to sampling geometry."),
    ("F_LENGTH", "interval_length_m", "analysis_observations", "m", "REAL", 0,
     "Support length; constant 1 m.",
     "LOG_ONLY", "No predictive content."),
    ("F_SUPPORT", "support_length_m", "analysis_observations", "m", "REAL", 0,
     "Support length; constant 1 m.",
     "LOG_ONLY", "No predictive content."),
    ("F_INTERVALID", "upstream_interval_id", "analysis_observations", None, "INTEGER", 0,
     "Identifier.",
     "IDENTIFIER", "Would memorise individual intervals."),
    ("F_INTERVALKEY", "upstream_interval_key", "analysis_observations", None, "TEXT", 0,
     "Identifier.",
     "IDENTIFIER", "Would memorise individual intervals."),
)

FAMILIES = (
    ("BASE_PREVALENCE", "Training prevalence", "TrainingPrevalence", "BASELINE",
     "P(I=1) = training prevalence",
     "Constant probability equal to the training-fold prevalence. Sanity baseline for every fold.",
     "Uses the training label only; no predictor."),
    ("BASE_LOGISTIC", "Logistic regression", "#LogisticRegression", "BASELINE",
     "P(I=1 | easting, northing, z_relative)",
     "L2 logistic regression on the three safe coordinates, with standardisation refitted inside each fold.",
     "Safe predictors only; no target-derived feature."),
    ("M2_RF", "Random forest", "RandomForestClassifier", "M2",
     "P(I=1 | easting, northing, z_relative)",
     "Random forest on the three safe coordinates. Hyperparameters selected by inner whole-hole CV.",
     "Safe predictors only; no target-derived feature."),
    ("M2_HGB", "Gradient boosting", "HistGradientBoostingClassifier", "M2",
     "P(I=1 | easting, northing, z_relative)",
     "Histogram gradient boosting on the three safe coordinates. Audited fallback for XGBoost, which is not installed.",
     "Safe predictors only; no target-derived feature."),
    ("M1_IK", "Indicator kriging", "SimpleIndicatorKriging", "M1",
     "P(I=1 | training indicator variogram)",
     "Simple indicator kriging with a variogram and kriging neighbourhood fitted on the outer training fold only.",
     "The variogram is fitted on training observations only; test labels never enter the fit."),
    ("M3_HYBRID", "Hybrid residual model", "HybridResidualKriging", "M3",
     "P(I=1 | trend + kriged residual)",
     "ML trend from the selected M2 candidate plus a kriged residual from an inner cross-fitted residual variogram. "
     "When the residual variogram is not supported, the run is recorded as an ML-only fallback, not a hybrid success.",
     "Trend and residual variogram are training-only; test labels are never used for fitting or selection."),
)


def _check_objects(up) -> None:
    present = {r[0] for r in up.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    for name in REQUIRED_O1_VIEWS + REQUIRED_O1_TABLES:
        if name not in present:
            raise StopError(f"upstream object missing: {name}")
    for view, cols in REQUIRED_COLUMNS.items():
        have = {r[1] for r in up.execute(f"PRAGMA table_info({view})")}
        for col in cols:
            if col not in have:
                raise StopError(f"upstream column missing: {view}.{col}")


def _o1_gates(up, label_rule_id: str) -> dict:
    version = up.execute("SELECT dataset_version_id, dataset_version_key, etl_version FROM v_active_version").fetchone()
    if version is None:
        raise StopError("no ACTIVE upstream dataset version")
    vid = version["dataset_version_id"]
    rule = up.execute("SELECT status, definition_sha256 FROM graphite_label_rules WHERE rule_id = ?",
                      (label_rule_id,)).fetchone()
    if rule is None or rule["status"] != "APPROVED":
        raise StopError(f"label rule {label_rule_id} is not APPROVED")
    coord = up.execute("SELECT status FROM coordinate_decisions WHERE dataset_version_id = ?", (vid,)).fetchone()
    if coord is None or coord["status"] != "APPROVED":
        raise StopError("coordinate decision is not APPROVED")
    datum = up.execute("SELECT datum_status FROM coordinate_system_registry WHERE crs_key = 'EPSG:32630'").fetchone()
    if datum is None or datum["datum_status"] != "VERIFIED":
        raise StopError("datum is not VERIFIED for EPSG:32630")
    lines = up.execute("SELECT COUNT(*) AS n, SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) AS a "
                       "FROM v_drill_lines").fetchone()
    if lines["n"] == 0 or lines["n"] != lines["a"]:
        raise StopError("drill-line grouping is not fully APPROVED")
    geom = up.execute("SELECT geometry_build_id, geometry_status FROM geometry_builds WHERE dataset_version_id = ?",
                      (vid,)).fetchone()
    if geom is None or geom["geometry_status"] != "PROVISIONAL_RELATIVE":
        raise StopError("geometry status is not PROVISIONAL_RELATIVE")
    absolute = up.execute("SELECT COUNT(*) FROM v_interval_geometry WHERE z_absolute_m IS NOT NULL").fetchone()[0]
    if absolute != 0:
        raise StopError("z_absolute_m is populated; absolute elevations must not enter Objective 3")
    support = up.execute("SELECT COUNT(*) FROM v_interval_geometry WHERE ABS(interval_length_m - 1.0) > 1e-9").fetchone()[0]
    if support != 0:
        raise StopError("interval support differs from 1 m")
    approval = up.execute("SELECT COUNT(*) FROM coordinate_pair_approvals").fetchone()[0]
    if approval == 0:
        raise StopError("the UTM coordinate pair has no approval record")
    return {"version": dict(version), "rule": dict(rule), "geometry_build_id": geom["geometry_build_id"],
            "geometry_status": geom["geometry_status"], "lines_approved": lines["a"]}


def _o2_handoff(o2_path: Path) -> dict:
    o2 = connect_readonly(o2_path)
    try:
        receipt = o2.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise StopError("Objective 2 has no source receipt")
        handoff = o2.execute("SELECT * FROM continuity_handoff_decisions WHERE receipt_id = ? "
                             "ORDER BY handoff_id DESC LIMIT 1", (receipt["receipt_id"],)).fetchone()
        if handoff is None:
            raise StopError("Objective 2 has no continuity handoff for its latest receipt")
        return {"receipt": dict(receipt), "handoff": dict(handoff)}
    finally:
        o2.close()


def _seed_reference_rows(conn, receipt_id: int, receipt: dict) -> None:
    for feature_id, name, source, units, dtype, available, basis, designation, rationale in FEATURES:
        conn.execute(
            "INSERT OR IGNORE INTO feature_registry (feature_id, name, source_table, units, data_type, "
            "available_at_prediction, availability_basis, leakage_designation, rationale) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (feature_id, name, source, units, dtype, available, basis, designation, rationale))
    for family_id, name, model_class, role, estimand, description, leakage_note in FAMILIES:
        conn.execute(
            "INSERT OR IGNORE INTO model_families (family_id, name, model_class, role, estimand, description, leakage_note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (family_id, name, model_class, role, estimand, description, leakage_note))


def import_snapshot(upstream: Path = UPSTREAM_DB_PATH, o2_path: Path = O2_DB_PATH,
                    o3_path: Path | None = None, config_path: Path | None = None) -> dict:
    """Verify predecessor gates and store the receipt, snapshot, target, label, geometry and feature registry.

    Re-running with the same content reuses the receipt. The canonical content hash is computed with the same
    serialisation as Objective 2, so an identical hash demonstrates that the two stages read the same upstream rows.
    """
    config, config_sha = load_config(config_path)
    label_rule_id = config["target"]["label_rule_id"]
    up = connect_readonly(upstream)
    try:
        _check_objects(up)
        gates = _o1_gates(up, label_rule_id)
        rows = [dict(r) for r in up.execute(IMPORT_QUERY)]
        expected = up.execute("SELECT COUNT(*) FROM v_interval_geometry").fetchone()[0]
    finally:
        up.close()
    if len(rows) != expected:
        raise StopError(f"row count {len(rows)} differs from upstream {expected}")
    o2 = _o2_handoff(o2_path)
    if o2["receipt"]["upstream_dataset_version_key"] != gates["version"]["dataset_version_key"]:
        raise StopError("Objective 2 receipt does not reference the active Objective 1 version")
    if o2["receipt"]["label_rule_id"] != label_rule_id:
        raise StopError("Objective 2 receipt uses a different label rule")

    canonical = "\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) for r in rows)
    content_sha = sha256_text(canonical)
    ordered_digest = sha256_text("\n".join(r["interval_key"] for r in rows))
    query_sha = sha256_text(IMPORT_QUERY)

    conn = connect_o3(o3_path)
    try:
        existing = conn.execute("SELECT receipt_id FROM source_receipts WHERE upstream_dataset_version_key = ? "
                                "AND content_sha256 = ?",
                                (gates["version"]["dataset_version_key"], content_sha)).fetchone()
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, started_utc, status, code_commit, note) "
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
                    "coordinate_pair_status, drill_line_status, vertical_basis, o2_logical_name, o2_path, o2_receipt_id, "
                    "o2_content_sha256, o2_handoff_id, o2_handoff_status, o2_candidate_family, content_sha256, row_count, "
                    "ordered_id_digest, selection_query_sha256, imported_utc, code_commit) "
                    "VALUES ('obj1_master', ?, ?, ?, ?, ?, 'APPROVED', ?, ?, 'PROVISIONAL_RELATIVE', 'EPSG:32630', "
                    "'VERIFIED', 'APPROVED', 'APPROVED', 'RELATIVE_TO_COLLAR', 'obj2_spatial', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (upstream.as_posix(), gates["version"]["dataset_version_id"],
                     gates["version"]["dataset_version_key"], gates["version"]["etl_version"], label_rule_id,
                     gates["rule"]["definition_sha256"], gates["geometry_build_id"], o2_path.as_posix(),
                     o2["receipt"]["receipt_id"], o2["receipt"]["content_sha256"], o2["handoff"]["handoff_id"],
                     o2["handoff"]["decision_status"], o2["handoff"]["candidate_family"], content_sha, len(rows),
                     ordered_digest, query_sha, utc_now(), code_commit())).lastrowid
                for r in rows:
                    binary = r["label_state"] in ("POSITIVE", "NEGATIVE")
                    conn.execute(
                        "INSERT INTO analysis_observations (receipt_id, upstream_interval_id, upstream_interval_key, "
                        "hole_id, line_code, depth_from_m, depth_to_m, support_length_m, midpoint_m, easting_m, northing_m, "
                        "z_relative_m, label_state, in_binary_target, indicator, geometry_status, rock_code_raw, "
                        "rock_code_status, weathering_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (receipt_id, r["interval_id"], r["interval_key"], r["hole_id"], r["line_code"], r["depth_from_m"],
                         r["depth_to_m"], r["support_length_m"], r["midpoint_m"], r["easting_m"], r["northing_m"],
                         r["z_relative_m"], r["label_state"], 1 if binary else 0,
                         int(r["indicator"]) if binary else None, r["geometry_status"], r["rock_code_raw"],
                         r["rock_code_status"], r["weathering_code"]))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            reused = False

        counts = {state: n for state, n in conn.execute(
            "SELECT label_state, COUNT(*) FROM analysis_observations WHERE receipt_id = ? GROUP BY label_state", (receipt_id,))}
        target_id = f"TARGET-{label_rule_id}-{receipt_id}"
        conn.execute(
            "INSERT OR IGNORE INTO target_registries (target_id, receipt_id, label_rule_id, label_rule_status, "
            "positive_state, negative_state, excluded_states_json, binary_n, positive_n, negative_n, ambiguous_n, "
            "unresolved_n, created_utc) VALUES (?, ?, ?, 'APPROVED', 'POSITIVE', 'NEGATIVE', ?, ?, ?, ?, ?, ?, ?)",
            (target_id, receipt_id, label_rule_id, json.dumps(config["target"]["excluded_states"]),
             counts.get("POSITIVE", 0) + counts.get("NEGATIVE", 0), counts.get("POSITIVE", 0),
             counts.get("NEGATIVE", 0), counts.get("AMBIGUOUS", 0), counts.get("UNRESOLVED", 0), utc_now()))
        conn.execute(
            "INSERT OR IGNORE INTO label_versions (label_version_id, receipt_id, rule_id, rule_status, definition_sha256, "
            "positive_state, negative_state, excluded_states_json, binary_n, positive_n, negative_n, ambiguous_n, "
            "unresolved_n, frozen_utc) VALUES (?, ?, ?, 'APPROVED', ?, 'POSITIVE', 'NEGATIVE', ?, ?, ?, ?, ?, ?, ?)",
            (f"LABEL-{label_rule_id}-{receipt_id}", receipt_id, label_rule_id, gates["rule"]["definition_sha256"],
             json.dumps(config["target"]["excluded_states"]), counts.get("POSITIVE", 0) + counts.get("NEGATIVE", 0),
             counts.get("POSITIVE", 0), counts.get("NEGATIVE", 0), counts.get("AMBIGUOUS", 0),
             counts.get("UNRESOLVED", 0), utc_now()))
        conn.execute(
            "INSERT OR IGNORE INTO geometry_versions (geometry_version_id, receipt_id, geometry_build_id, geometry_status, "
            "crs_key, datum_status, vertical_basis, z_absolute_used, created_utc) "
            "VALUES (?, ?, ?, 'PROVISIONAL_RELATIVE', 'EPSG:32630', 'VERIFIED', 'RELATIVE_TO_COLLAR', 0, ?)",
            (f"GEOM-{gates['geometry_build_id']}-{receipt_id}", receipt_id, gates["geometry_build_id"], utc_now()))
        _seed_reference_rows(conn, receipt_id, {**gates, **o2})
        conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ?, receipt_id = ? WHERE run_id = ?",
                     (utc_now(), receipt_id, run_id))
        return {"receipt_id": receipt_id, "run_id": run_id, "reused": reused, "row_count": len(rows),
                "content_sha256": content_sha, "o2_content_sha256": o2["receipt"]["content_sha256"],
                "target_id": target_id, "counts": counts}
    finally:
        conn.close()

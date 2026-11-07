"""Gate outcomes and structural checks on the built database (specification 03). Each test is named for the gate it checks."""

import shutil
import sqlite3

import pytest

from kambale.objective_2 import verify
from kambale.objective_2.config import O2_CONFIG_PATH, O2_DB_PATH, UPSTREAM_DB_PATH, load_config
from kambale.objective_2.db import connect_upstream_readonly

EXIT_GATES = ("G01", "G02", "G03", "G07", "G08", "G14", "G19", "G25", "G26", "G27", "G28", "G29", "G30")
needs_upstream = pytest.mark.skipif(not UPSTREAM_DB_PATH.exists(), reason="Objective 1 database is required")


def _latest_verify(o2_ro):
    return o2_ro.execute("SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'VERIFY'").fetchone()[0]


def _gate_detail(o2_ro, gate_id):
    return o2_ro.execute("SELECT detail FROM gate_results WHERE run_id = ? AND gate_id = ?",
                         (_latest_verify(o2_ro), gate_id)).fetchone()[0]


def test_latest_verify_meets_exit_conditions(o2_ro):
    rows = o2_ro.execute("SELECT gate_id, status FROM gate_results WHERE run_id = ?", (_latest_verify(o2_ro),)).fetchall()
    status = {r["gate_id"]: r["status"] for r in rows}
    assert [g for g in EXIT_GATES if status.get(g) != "PASS"] == []


@needs_upstream
def test_crs_status_recorded(o2_ro, receipt_id):  # G04
    row = o2_ro.execute("SELECT crs_key, crs_datum_status, coordinate_pair_status FROM source_receipts WHERE receipt_id = ?",
                        (receipt_id,)).fetchone()
    assert row["crs_key"] == "EPSG:32630"
    assert row["crs_datum_status"] == "VERIFIED"
    assert row["coordinate_pair_status"] == "APPROVED"


def test_each_hole_one_line(o2_ro, receipt_id):  # G05
    bad = o2_ro.execute("SELECT COUNT(*) FROM (SELECT hole_id FROM analysis_observations WHERE receipt_id = ? "
                        "GROUP BY hole_id HAVING COUNT(DISTINCT line_code) > 1)", (receipt_id,)).fetchone()[0]
    assert bad == 0


def test_bins_positive_width(o2_ro, receipt_id):  # G07
    bad = o2_ro.execute("SELECT COUNT(*) FROM variogram_lag_bins b JOIN variogram_experiments e ON e.experiment_id = b.experiment_id "
                        "WHERE e.receipt_id = ? AND b.lag_to_m <= b.lag_from_m", (receipt_id,)).fetchone()[0]
    assert bad == 0


def test_exclusion_identity(o2_ro, receipt_id):  # G08
    bad = o2_ro.execute("SELECT COUNT(*) FROM hole_occurrence_summaries WHERE receipt_id = ? "
                        "AND n_intervals <> binary_n + ambiguous_n + unresolved_n", (receipt_id,)).fetchone()[0]
    bad += o2_ro.execute("SELECT COUNT(*) FROM line_occurrence_summaries WHERE receipt_id = ? "
                         "AND n_intervals <> binary_n + ambiguous_n + unresolved_n", (receipt_id,)).fetchone()[0]
    assert bad == 0


@needs_upstream
def test_declared_orientation_matches_survey(receipt_id):  # G09
    config, _ = load_config(O2_CONFIG_PATH)
    declared = (config["geometry"]["declared_dip_deg"], config["geometry"]["declared_azimuth_deg"])
    up = connect_upstream_readonly(UPSTREAM_DB_PATH)
    try:
        orient = {tuple(r) for r in up.execute("SELECT DISTINCT dip_deg, azimuth_deg FROM v_survey")}
    finally:
        up.close()
    assert orient == {declared}


def test_class_imbalance_reported(o2_ro, receipt_id):  # G10
    rows = o2_ro.execute("SELECT line_code, graphitic_fraction_binary FROM line_occurrence_summaries WHERE receipt_id = ?",
                         (receipt_id,)).fetchall()
    assert rows
    detail = _gate_detail(o2_ro, "G10")
    for r in rows:
        if r["graphitic_fraction_binary"] is not None and r["graphitic_fraction_binary"] < 0.10:
            assert r["line_code"] in detail


def test_direction_skip_recorded(o2_ro, receipt_id):  # G12
    rows = o2_ro.execute("SELECT direction_id, status, reason FROM direction_registry WHERE receipt_id = ?", (receipt_id,)).fetchall()
    assert rows and all(r["reason"] for r in rows)
    assert all("required" in r["reason"] for r in rows if r["status"] == "SKIPPED")


def test_marginal_departure_reported(o2_ro):  # G17
    missing = o2_ro.execute("SELECT COUNT(*) FROM variogram_fits WHERE fit_status = 'FITTED' AND marginal_departure IS NULL").fetchone()[0]
    assert missing == 0


def test_anisotropy_requires_support(o2_ro, receipt_id):  # G18
    claimed = o2_ro.execute("SELECT COUNT(*) FROM anisotropy_diagnostics WHERE receipt_id = ? AND decision = 'ANISOTROPY_SUPPORTED'",
                            (receipt_id,)).fetchone()[0]
    assert claimed == 0


def test_base_excludes_within_hole(o2_ro, receipt_id):  # G19
    bad = o2_ro.execute("SELECT COUNT(*) FROM variogram_experiments WHERE receipt_id = ? AND variant = 'BASE' "
                        "AND direction_id <> 'DOWNHOLE_WITHIN' AND within_hole_pairs <> 'EXCLUDED'", (receipt_id,)).fetchone()[0]
    assert bad == 0


def test_sensitivity_complete(o2_ro, receipt_id):  # G20
    config, _ = load_config(O2_CONFIG_PATH)
    run = o2_ro.execute("SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'ANALYSE' AND receipt_id = ?", (receipt_id,)).fetchone()[0]
    found = {r[0] for r in o2_ro.execute("SELECT variant_name FROM sensitivity_runs WHERE run_id = ?", (run,)).fetchall()}
    assert {e["name"] for e in config["sensitivity"]} <= found


def test_sections_labelled_relative(o2_ro, receipt_id):  # G21
    rows = o2_ro.execute("SELECT vertical_basis, observed_or_inferred FROM geological_section_registry WHERE receipt_id = ?",
                         (receipt_id,)).fetchall()
    assert all(r["vertical_basis"] == "RELATIVE_DEPTH" for r in rows)


def test_no_absolute_elevation_products(o2_ro):  # G22
    found = []
    for (table,) in o2_ro.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
        for col in o2_ro.execute(f"PRAGMA table_info({table})").fetchall():
            if "absolute" in col["name"].lower():
                found.append(f"{table}.{col['name']}")
    assert found == []


def test_no_inferred_contacts(o2_ro, receipt_id):  # G23
    bad = o2_ro.execute("SELECT COUNT(*) FROM geological_section_registry WHERE receipt_id = ? "
                        "AND observed_or_inferred <> 'OBSERVED_LOG_ONLY'", (receipt_id,)).fetchone()[0]
    assert bad == 0


def test_synthetic_not_exported(o2_ro):  # G24
    receipts = o2_ro.execute("SELECT COUNT(*) FROM source_receipts WHERE upstream_logical_name <> 'obj1_master'").fetchone()[0]
    exports = o2_ro.execute("SELECT COUNT(*) FROM export_manifests WHERE LOWER(artifact_path) LIKE '%synthetic%'").fetchone()[0]
    assert receipts == 0 and exports == 0


def test_sections_are_observed_log_only(o2_ro, receipt_id):  # G23 companion check on section status values
    rows = o2_ro.execute("SELECT observed_or_inferred FROM geological_section_registry WHERE receipt_id = ?", (receipt_id,)).fetchall()
    assert all(r[0] == "OBSERVED_LOG_ONLY" for r in rows)


def _copy_of_database(tmp_path):
    """A copy of the built database. The gate tests change the copy, never the Objective 2 database."""
    target = tmp_path / "o2_copy.sqlite"
    shutil.copy(O2_DB_PATH, target)
    return target


@needs_upstream
def test_receipt_row_count_mismatch_stops(tmp_path):  # G01, row count against the receipt (specification 04, section 9)
    db = _copy_of_database(tmp_path)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE source_receipts SET row_count = row_count - 1")
    conn.commit()
    conn.close()
    result = verify.run(o2_path=db, upstream=UPSTREAM_DB_PATH)
    g01 = next(g for g in result["gates"] if g["gate_id"] == "G01")
    assert g01["status"] == "STOP"
    assert "vs receipt" in g01["detail"]


@needs_upstream
def test_stop_withdraws_handoff(tmp_path):  # a STOP writes no handoff (specification 06, section 3.6)
    db = _copy_of_database(tmp_path)
    conn = sqlite3.connect(db)
    conn.execute("UPDATE source_receipts SET content_sha256 = 'corrupted'")
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM continuity_handoff_decisions").fetchone()[0] == 1
    conn.close()
    result = verify.run(o2_path=db, upstream=UPSTREAM_DB_PATH)
    assert result["stopped"]
    assert result["handoff_rows_withdrawn"] == 1
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM continuity_handoff_decisions").fetchone()[0] == 0
    conn.close()

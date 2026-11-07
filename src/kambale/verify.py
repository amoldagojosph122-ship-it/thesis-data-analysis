"""Verification: SQL integrity, reconciliation, raw immutability, Stage B blocking, and the pytest suite.

Every result is written to validation_test_results. A result that was not executed is recorded as NOT_RUN.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from kambale.config import PROJECT_ROOT
from kambale.db import connect, fk_violations, integrity, utc_now

THESIS_REFERENCE = {"Holes": 71, "Survey stations": 71, "Logging intervals": 1910, "Sgs intervals": 529,
                    "Holes intersecting Sgs": 42}


def _record(conn, run, dv, group, name, expected, observed, outcome, detail=""):
    conn.execute("INSERT INTO validation_test_results (run_utc, dataset_version_id, test_group, test_name, expected, "
                 "observed, outcome, detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 (run, dv, group, name, str(expected), str(observed), outcome, detail))


def run_verification(db_path: Path, with_pytest: bool = True) -> dict:
    conn = connect(db_path)
    run = utc_now()
    dv = conn.execute("SELECT dataset_version_id FROM dataset_versions WHERE status = 'ACTIVE'").fetchone()
    if dv is None:
        raise RuntimeError("no ACTIVE dataset version; run `kambale build` first")
    dv = dv[0]
    failures = 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        violations = fk_violations(conn)
        ok = not violations
        failures += 0 if ok else 1
        _record(conn, run, dv, "SQL_INTEGRITY", "PRAGMA foreign_key_check", "0 rows", f"{len(violations)} rows",
                "PASS" if ok else "FAIL")
        check = integrity(conn)
        _record(conn, run, dv, "SQL_INTEGRITY", "PRAGMA integrity_check", "ok", check,
                "PASS" if check == "ok" else "FAIL")
        if check != "ok":
            failures += 1

        raw_ok = True
        for table, column in (("raw_collars", "HoleID"), ("raw_surveys", "HoleID"), ("raw_logging", "HOLEID")):
            try:
                conn.execute(f"UPDATE {table} SET \"{column}\" = \"{column}\" WHERE rowid = 1")
                raw_ok = False
            except Exception:
                pass
        _record(conn, run, dv, "SQL_INTEGRITY", "raw_* UPDATE rejected by trigger", "rejected", "rejected" if raw_ok
                else "accepted", "PASS" if raw_ok else "FAIL")
        failures += 0 if raw_ok else 1

        blockers = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger' "
                                "AND name LIKE 'future_%_blocked'").fetchone()[0]
        future_rows = sum(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
                          ("spatial_folds", "variogram_runs", "variogram_points", "model_runs", "model_predictions",
                           "model_evaluation_metrics", "probability_calibration", "uncertainty_voxels",
                           "simulation_runs"))
        future_ok = blockers == 9 and future_rows == 0
        _record(conn, run, dv, "SQL_INTEGRITY", "Stage B contract tables: blocking triggers present and empty",
                "9 triggers; 0 rows", f"{blockers} triggers; {future_rows} rows", "PASS" if future_ok else "FAIL")
        failures += 0 if future_ok else 1

        counts = {
            "Holes": conn.execute("SELECT COUNT(*) FROM v_holes").fetchone()[0],
            "Survey stations": conn.execute("SELECT COUNT(*) FROM v_survey").fetchone()[0],
            "Logging intervals": conn.execute("SELECT COUNT(*) FROM v_intervals").fetchone()[0],
            "Sgs intervals": conn.execute("SELECT COUNT(*) FROM v_label_evidence WHERE is_sgs = 1").fetchone()[0],
            "Holes intersecting Sgs": conn.execute("SELECT COUNT(*) FROM v_hole_graphite WHERE sgs_n > 0").fetchone()[0],
        }
        for name, observed in counts.items():
            expected = THESIS_REFERENCE[name]
            outcome = "PASS" if observed == expected else "WARN"
            _record(conn, run, dv, "RECONCILIATION", name, expected, observed, outcome,
                    "ThesisDesign.docx preliminary value (reconciliation only)")
        z_bad = conn.execute("SELECT COUNT(*) FROM interval_coordinates WHERE z_absolute_m IS NOT NULL").fetchone()[0]
        _record(conn, run, dv, "SQL_INTEGRITY", "z_absolute_m non-null rows", 0, z_bad, "PASS" if z_bad == 0 else "FAIL")
        failures += 0 if z_bad == 0 else 1
        lith_intervals = conn.execute("SELECT COUNT(*) FROM v_intervals").fetchone()[0]
        lith_rows = conn.execute("SELECT COUNT(*) FROM v_lithology_refinement").fetchone()[0]
        lith_ok = lith_rows == lith_intervals
        _record(conn, run, dv, "SQL_INTEGRITY", "one lithology refinement row per active interval", lith_intervals, lith_rows,
                "PASS" if lith_ok else "FAIL")
        failures += 0 if lith_ok else 1
        dem_holes = conn.execute("SELECT COUNT(*) FROM holes WHERE dataset_version_id = "
                                 "(SELECT dataset_version_id FROM v_active_version) AND dem_elevation_m IS NOT NULL"
                                 ).fetchone()[0]
        dem_ok = dem_holes == counts["Holes"]
        _record(conn, run, dv, "SQL_INTEGRITY", "collars with a provisional DEM elevation", counts["Holes"], dem_holes,
                "PASS" if dem_ok else "FAIL")
        failures += 0 if dem_ok else 1
        active_geometry = ("geometry_build_id IN (SELECT geometry_build_id FROM geometry_builds "
                           "WHERE dataset_version_id = (SELECT dataset_version_id FROM v_active_version))")
        geometry_rows = conn.execute(f"SELECT COUNT(*) FROM interval_coordinates WHERE {active_geometry}").fetchone()[0]
        z_dem_rows = conn.execute(f"SELECT COUNT(*) FROM interval_coordinates WHERE {active_geometry} "
                                  "AND z_dem_absolute_m IS NOT NULL").fetchone()[0]
        z_dem_ok = z_dem_rows == geometry_rows
        _record(conn, run, dv, "SQL_INTEGRITY", "interval rows with a provisional DEM elevation", geometry_rows,
                z_dem_rows, "PASS" if z_dem_ok else "FAIL")
        failures += 0 if z_dem_ok else 1
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise

    pytest_summary = None
    if with_pytest:
        pytest_summary = _run_pytest()
        outcome = "PASS" if pytest_summary["returncode"] == 0 else "FAIL"
        failures += 0 if outcome == "PASS" else 1
        _record(conn, utc_now(), dv, "PYTEST", "pytest suite (tests/)", "0 failed",
                pytest_summary["summary"], outcome, "\n".join(pytest_summary["tail"])[-1500:])
    else:
        _record(conn, utc_now(), dv, "PYTEST", "pytest suite (tests/)", "run", "not run in this call", "NOT_RUN")
    conn.close()
    return {"dataset_version_id": dv, "failures": failures, "run_utc": run,
            "pytest": None if pytest_summary is None else pytest_summary["summary"],
            "reconciliation": counts}


def _run_pytest() -> dict:
    proc = subprocess.run([sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "--tb=short", "-p", "no:cacheprovider"],
                          cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=900)
    lines = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ln.strip()]
    summary = lines[-1] if lines else "no output"
    return {"returncode": proc.returncode, "summary": summary, "tail": lines}

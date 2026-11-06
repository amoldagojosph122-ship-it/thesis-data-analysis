"""Configuration 3 extension and the STRICT_SGS_v1 comparator (exploratory; specification 06, section 3.7).

These tests read the configuration-3 stage run from the built database. The comparator agrees with DESIGN on the DESIGN
binary sample, so the agreement test documents a reported finding; if the labels change, that test is expected to fail.
"""

import hashlib

from kambale.objective_2.extension import EXT_CONFIG_PATH

V3 = "O2-CFG-2026.11.05-3"


def _ext_run(o2_ro):
    return o2_ro.execute("SELECT run_id, config_sha256 FROM stage_runs WHERE run_kind = 'SENSITIVITY' AND config_version = ? "
                         "ORDER BY run_id DESC LIMIT 1", (V3,)).fetchone()


def test_extension_config_is_predeclared(o2_ro):
    run = _ext_run(o2_ro)
    assert run is not None
    assert hashlib.sha256(EXT_CONFIG_PATH.read_bytes()).hexdigest() == run["config_sha256"]


def test_comparator_labels_cover_all_intervals(o2_ro, receipt_id):
    total = o2_ro.execute("SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = ?", (receipt_id,)).fetchone()[0]
    labelled = o2_ro.execute("SELECT COUNT(*) FROM comparator_observations WHERE receipt_id = ? AND rule_id = 'STRICT_SGS_v1'",
                             (receipt_id,)).fetchone()[0]
    assert labelled == total == 1910


def test_strict_matches_design_on_shared_sample(o2_ro, receipt_id):
    disagree = o2_ro.execute("SELECT COUNT(*) FROM analysis_observations a JOIN comparator_observations c "
                             "ON c.receipt_id = a.receipt_id AND c.upstream_interval_id = a.upstream_interval_id "
                             "WHERE a.receipt_id = ? AND a.in_binary_target = 1 AND c.indicator <> a.indicator",
                             (receipt_id,)).fetchone()[0]
    assert disagree == 0


def test_strict_comparator_not_used_for_handoff(o2_ro, receipt_id):
    via_comparator = o2_ro.execute("SELECT COUNT(*) FROM continuity_handoff_decisions h JOIN variogram_fits f ON f.fit_id = h.fit_id "
                                   "JOIN variogram_experiments e ON e.experiment_id = f.experiment_id "
                                   "WHERE h.receipt_id = ? AND e.label_rule_id = 'STRICT_SGS_v1'", (receipt_id,)).fetchone()[0]
    rows = o2_ro.execute("SELECT COUNT(*) FROM continuity_handoff_decisions WHERE receipt_id = ?", (receipt_id,)).fetchone()[0]
    assert via_comparator == 0
    assert rows == 1


def test_extension_lag_setting(o2_ro, receipt_id):
    rows = o2_ro.execute("SELECT lag_width_m, lag_max_m FROM variogram_experiments WHERE receipt_id = ? AND config_version = ? "
                         "AND label_rule_id = 'DESIGN_8_2_v1' AND experiment_id NOT IN (SELECT experiment_id FROM sensitivity_runs "
                         "WHERE changed_factor = 'excluded_line')", (receipt_id, V3)).fetchall()
    assert rows
    assert all(r[0] == 50.0 and r[1] == 2000.0 for r in rows)


def test_extension_loo_complete(o2_ro, receipt_id):
    run = _ext_run(o2_ro)["run_id"]
    lines = o2_ro.execute("SELECT COUNT(DISTINCT line_code) FROM analysis_observations WHERE receipt_id = ? AND in_binary_target = 1",
                          (receipt_id,)).fetchone()[0]
    refits = o2_ro.execute("SELECT COUNT(*) FROM sensitivity_runs WHERE run_id = ? AND changed_factor = 'excluded_line'",
                           (run,)).fetchone()[0]
    assert refits == 2 * lines

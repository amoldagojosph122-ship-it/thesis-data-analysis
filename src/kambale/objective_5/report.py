"""Writes reports/objective_5/RUN_REPORT.md from the Objective 5 database and the predeclared configuration."""

from __future__ import annotations

import json

import numpy as np

from kambale.objective_5.config import (EXTRAPOLATION, INTERPOLATION, O5_CONFIG_PATH, O5_REPORT_DIR, PROJECT_ROOT,
                                        StopError, load_config, sha256_file, utc_now)
from kambale.objective_5.db import connect_o5


def _table(headers, rows) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))
                                      for v in r) + " |")
    return out


CONFIDENT_CLASS_PARAGRAPH = (
    "Confident classes depend on the width of the bootstrap interval of the zone's model. The tier-1 logistic model is "
    "smooth and its bootstrap intervals are narrow, so CONFIDENT classes in the EXTRAPOLATION zone reflect a stable simple "
    "trend, not better knowledge: its validated skill (tier 1) is lower than the tier-2 model's. EXTRAPOLATION-zone classes "
    "must be read with the tier-1 validation in O5-T03 and the model-disagreement map, and are not comparable with "
    "INTERPOLATION-zone classes.")


def _scenario_section(conn, cfg) -> list[str]:
    scfg = cfg["scenario_simulation"]
    out = ["## 10. Scenario simulation (scenario analysis; lateral range assumed, not estimated)", "",
           f"Sequential indicator simulation with a locally varying mean (tier-2 M2_HGB_WF, calibrated), residual "
           f"simple kriging with up to {scfg['kriging']['max_conditioning_data']} conditioning data and "
           f"{scfg['kriging']['max_previously_simulated']} previously simulated nodes within anisotropy-scaled distance "
           f"1.0, {scfg['n_realisations']} realisations per scenario, seed {scfg['seed']}. Vertical range set so that the "
           "range along the hole direction (plunge 60 degrees) equals the fitted down-hole practical range. This is a "
           "scenario analysis: each lateral range is assumed, scenarios are reported separately and never pooled.", ""]
    scen = conn.execute("SELECT * FROM sim_scenarios ORDER BY horizontal_range_m").fetchall()
    if not scen:
        return out + ["The scenario simulation has not been run.", ""]
    meta = {r["meta_key"]: json.loads(r["meta_value"]) for r in conn.execute("SELECT * FROM sim_run_meta")}
    rows = []
    for r in scen:
        if r["feasibility"] == "INFEASIBLE":
            rows.append((r["scenario_id"], r["horizontal_range_m"], "INFEASIBLE (not run)", None, None, None, None,
                         None, None, None, None))
            continue
        rows.append((r["scenario_id"], r["horizontal_range_m"], r["vertical_range_m"], r["volume_p10_m3"],
                     r["volume_p50_m3"], r["volume_p90_m3"], r["expected_volume_m3"], r["components_p50"],
                     r["largest_share_p10"], r["largest_share_p50"], r["largest_share_p90"]))
    out += ["| scenario | a_h (m) | a_v (m) | volume P10 (m3) | volume P50 (m3) | volume P90 (m3) | expected sum(m) x 200 "
            "(m3) | components P50 | largest share P10 | P50 | P90 |", "|" + "|".join("---" for _ in range(11)) + "|"]
    for row in rows:
        out.append("| " + " | ".join("" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v)) for v in row)
                   + " |")
    out += [""]
    feas = [r for r in scen if r["feasibility"] == "FEASIBLE"]
    out += ["Reproduction and gates per scenario:", ""]
    out += ["| scenario | mean simulated frequency | mean local mean | difference | frequency status | SK fallbacks | "
            "neighbourless node visits (sum over realisations) | exact neighbour searches (sum) | downhole max abs diff (supported bins) | runtime (s) |",
            "|" + "|".join("---" for _ in range(10)) + "|"]
    for r in feas:
        out.append(f"| {r['scenario_id']} | {r['mean_frequency']:.4f} | {r['mean_local_mean']:.4f} | "
                   f"{r['mean_frequency_diff']:+.4f} | {r['frequency_status']} | {r['sk_fallbacks']} | "
                   f"{r['sk_neighbourless_nodes']} | {r['exact_neighbour_searches']} | "
                   f"{r['downhole_max_abs_diff']:.4f} | {r['runtime_s']:.0f} |")
    out += [""]
    if feas:
        p50 = [r["volume_p50_m3"] for r in feas]
        exp = [r["expected_volume_m3"] for r in feas]
        share50 = [r["largest_share_p50"] for r in feas]
        comp50 = [r["components_p50"] for r in feas]
        out += [f"Spread across scenarios (the finding): the median simulated volume ranges from {min(p50):.4g} to "
                f"{max(p50):.4g} m3 over the {len(feas)} feasible scenarios, against an expected volume of "
                f"{min(exp):.4g} to {max(exp):.4g} m3. The median largest-component share ranges from {min(share50):.3f} "
                f"to {max(share50):.3f} and the median component count from {min(comp50):.0f} to {max(comp50):.0f}. "
                "The result is this spread, which depends on the assumed lateral range; it is not one volume.", ""]
    out += [f"Data semivariance recomputed here against the stored Objective 2 DOWNHOLE_WITHIN bins: maximum absolute "
            f"difference {float(meta['data_vs_o2_max_abs_diff']):.2e}. Down-hole reproduction per scenario is in "
            "O5-T06 (lags 1, 5, 10, 20 and 30 m, and the maximum over supported bins).", ""]
    out += ["Scenario claims: " + " ".join(scfg["claims"].split()), ""]
    return out


def write_all(o5_path=None) -> dict:
    cfg, cfg_sha = load_config(O5_CONFIG_PATH)
    conn = connect_o5(o5_path)
    try:
        receipt = dict(conn.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone() or {})
        if not receipt:
            raise StopError("no receipt: run the import first")
        run = conn.execute("SELECT MAX(run_id) FROM stage_runs WHERE run_kind = 'VERIFY'").fetchone()[0]
        meta = {r["meta_key"]: json.loads(r["meta_value"]) for r in conn.execute("SELECT * FROM grid_meta")}
        lines = [f"# Objective 5 run report: model-based three-dimensional uncertainty (part 1)", "",
                 f"Configuration {cfg['config_version']} (supersedes {cfg['supersedes']}); SHA-256 of the configuration bytes "
                 f"{cfg_sha}. Generated {utc_now()}. Relative depth below collar throughout; absolute elevation is not used.",
                 "", "Status: parts 1 and 2 of the predeclared stage. Part 2 is a scenario analysis with an assumed lateral "
                     "range (section 10).", ""]

        lines += ["## 1. Inputs and receipts", ""]
        files = conn.execute("SELECT role, path, bytes, sha256 FROM input_files ORDER BY role").fetchall()
        lines += _table(["role", "path", "bytes", "SHA-256"], [(f["role"], f["path"], f["bytes"], f["sha256"])
                                                              for f in files])
        lines += ["", f"Objective 3 receipt {receipt['o3_receipt_id']}: {receipt['n_intervals']} logged intervals, "
                      f"{receipt['n_binary']} binary intervals (DESIGN_8_2_v1), {receipt['n_holes']} holes, prevalence "
                      f"{receipt['prevalence']:.4f}.", ""]
        handoffs = conn.execute("SELECT * FROM handoffs ORDER BY tier").fetchall()
        lines += ["Locked handoffs (selected and runner-up read from the Objective 4 comparison_decisions rows "
                  "with role SELECTED and COMPARATOR):", ""]
        lines += _table(["tier", "selected", "runner-up", "match", "improvement status", "delta Brier (sel - ru)",
                         "95% interval"],
                        [(h["tier"], h["selected_model_id"], h["runner_up_model_id"], h["match_status"],
                          h["improvement_status"], h["delta_brier"],
                          f"[{h['delta_brier_ci_low']:.5f}, {h['delta_brier_ci_high']:.5f}]") for h in handoffs])
        dh = conn.execute("SELECT * FROM downhole_variogram WHERE check_id = 1").fetchone()
        if dh is not None:
            lines += ["", f"Down-hole variogram (Objective 2 fit {dh['o2_fit_id']}, {dh['model']}): nugget "
                          f"{dh['nugget']:.6f}, structured sill {dh['structured_sill']:.6f}, practical range "
                          f"{dh['practical_range_m']:.4f} m; maximum absolute difference from the predeclared values "
                          f"{dh['max_abs_difference']:.2e} (status {dh['status']})."]
        lines += [""]

        lines += ["## 2. Final refits", "",
                  "Each selected and runner-up model was refitted once on all binary intervals with the Objective 3 rules. "
                  "In-sample Brier and AUC are fit diagnostics only.", ""]
        refits = conn.execute("SELECT * FROM final_refits ORDER BY tier, CASE role WHEN 'SELECTED' THEN 0 ELSE 1 END"
                              ).fetchall()
        lines += _table(["tier", "role", "model", "hyperparameters", "calibration", "intercept", "slope",
                         "in-sample Brier", "in-sample AUC"],
                        [(r["tier"], r["role"], r["model_id"], r["hyperparameters_json"], r["calibration_status"],
                          r["calibration_intercept"], r["calibration_slope"], r["in_sample_brier"], r["in_sample_auc"])
                         for r in refits])
        lines += ["", "Full-data hyperparameters against the most frequent Objective 3 per-fold choice:", ""]
        lines += _table(["tier", "model", "folds", "O3 most frequent", "count", "tied modes", "matches"],
                        [(r["tier"], r["model_id"], r["o3_folds_selected"], r["o3_most_frequent_json"],
                          r["o3_most_frequent_count"], r["o3_modes_tied"], "yes" if r["full_data_matches_o3_mode"] else "no")
                         for r in refits])
        lines += [""]

        lines += ["## 3. Grid and zones", "",
                  f"Grid: {meta['n_easting']} x {meta['n_northing']} x {meta['n_z']} cells = {meta['n_cells']} cells; "
                  f"cell {meta['cell_easting_m']:g} x {meta['cell_northing_m']:g} x {meta['cell_z_m']:g} m; cell volume "
                  f"{meta['cell_volume_m3']:g} m3 (relative grid volume only). Origin E {meta['origin_easting_m']:g}, "
                  f"N {meta['origin_northing_m']:g}; margin {meta['margin_m']:g} m around the {meta['collars']} collars.", ""]
        zones = conn.execute("SELECT zone, COUNT(*) AS cells, SUM(CASE WHEN depth_support = 'DEPTH_EXTRAPOLATED' THEN 1 "
                             "ELSE 0 END) AS depth_ext FROM grid_cells GROUP BY zone ORDER BY zone").fetchall()
        vol = meta["cell_volume_m3"]
        lines += _table(["zone", "cells", "relative volume (m3)", "DEPTH_EXTRAPOLATED cells"],
                        [(z["zone"], z["cells"], z["cells"] * vol, z["depth_ext"]) for z in zones]) + [""]

        lines += ["## 4. Classes", ""]
        classes = conn.execute("SELECT zone, class_label, COUNT(*) AS cells, SUM(above_weathering_front) AS above "
                               "FROM grid_cells GROUP BY zone, class_label ORDER BY zone, class_label").fetchall()
        lines += _table(["zone", "class", "cells", "relative volume (m3)", "cells above weathering front"],
                        [(c["zone"], c["class_label"], c["cells"], c["cells"] * vol, c["above"]) for c in classes]) + [""]
        sens = conn.execute("SELECT zone, class_at_prevalence AS cls, COUNT(*) AS cells FROM grid_cells "
                            "GROUP BY zone, class_at_prevalence ORDER BY zone, cls").fetchall()
        rule = conn.execute("SELECT * FROM classification_rules LIMIT 1").fetchone()
        if rule is not None:
            lines += [f"Sensitivity at the training prevalence {rule['prevalence_threshold']:.4f} (headline threshold "
                      f"{rule['decision_threshold']:g}):", ""]
            lines += _table(["zone", "class at prevalence", "cells"], [(s["zone"], s["cls"], s["cells"]) for s in sens])
            lines += [""]

        lines += [CONFIDENT_CLASS_PARAGRAPH, ""]

        lines += ["## 5. Interval width and disagreement by zone", "",
                  "Median and 90th percentile over the supported cells of each zone.", ""]
        stats = []
        for zone in (INTERPOLATION, EXTRAPOLATION):
            rows = conn.execute("SELECT interval_width, disagreement, p_selected FROM grid_cells WHERE zone = ?",
                                (zone,)).fetchall()
            w = np.array([r["interval_width"] for r in rows], dtype=float)
            d = np.array([r["disagreement"] for r in rows], dtype=float)
            stats.append((zone, float(np.median(w)), float(np.percentile(w, 90)), float(np.median(d)),
                          float(np.percentile(d, 90))))
        lines += _table(["zone", "width median", "width P90", "disagreement median", "disagreement P90"], stats) + [""]

        lines += ["## 6. Carried validation (Objective 4, not recomputed)", ""]
        cv = conn.execute("SELECT tier, role, model_id, metric_id, value, n FROM carried_validation "
                          "WHERE weighting = 'INTERVAL' ORDER BY tier, role, metric_id").fetchall()
        lines += _table(["tier", "role", "model", "metric", "pooled value (interval-weighted)", "n"],
                        [(c["tier"], c["role"], c["model_id"], c["metric_id"], c["value"], c["n"]) for c in cv]) + [""]

        lines += ["## 7. Bootstrap", ""]
        boots = conn.execute("SELECT * FROM bootstrap_summary ORDER BY zone").fetchall()
        lines += _table(["zone", "model", "replicates", "successful", "fraction", "runtime (s)", "status"],
                        [(b["zone"], b["model_id"], b["n_replicates"], b["n_success"], b["success_fraction"],
                          b["runtime_s"], b["status"]) for b in boots]) + [""]

        lines += ["## 8. Gates", ""]
        gates = []
        if run is not None:
            gates = conn.execute("SELECT gate_id, gate_name, status, detail FROM gate_results WHERE run_id = ? "
                                 "ORDER BY gate_id", (run,)).fetchall()
        lines += _table(["gate", "name", "status", "detail"], [(g["gate_id"], g["gate_name"], g["status"], g["detail"])
                                                            for g in gates]) + [""]

        lines += ["## 9. Figures and tables", ""]
        figs = conn.execute("SELECT figure_id, title, status, reason FROM figure_registry ORDER BY figure_id").fetchall()
        tabs = conn.execute("SELECT table_id, title, status, row_count FROM table_registry ORDER BY table_id").fetchall()
        lines += _table(["id", "title", "status", "detail"], [(f["figure_id"], f["title"], f["status"], f["reason"])
                                                           for f in figs])
        lines += [""] + _table(["id", "title", "status", "rows"], [(t["table_id"], t["title"], t["status"], t["row_count"])
                                                                for t in tabs]) + [""]
        lines += _scenario_section(conn, cfg)

        lines += ["## 11. Claims not permitted", ""]
        lines += [f"- {claim}" for claim in cfg["claims_not_permitted"]] + [""]
        O5_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = O5_REPORT_DIR / "RUN_REPORT.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return {"path": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256_file(path)}
    finally:
        conn.close()

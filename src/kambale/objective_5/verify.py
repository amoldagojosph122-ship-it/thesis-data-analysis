"""Gate runner for Objective 5 part 1. Each gate recomputes what it checks from the source, not from the stored outputs.

STOP gates halt a run. WARN gates are reported and do not change the outputs. The scenario gates of the configuration
belong to part 2 and are not evaluated here.
"""

from __future__ import annotations

import json

import numpy as np

from kambale.objective_3 import weathering_front as o3_front
from kambale.objective_3.config import load_config as load_o3_config
from kambale.objective_5.classify import classify_arrays
from kambale.objective_5.config import (CLASS_ABSENT, CLASS_PRESENT, EXTRAPOLATION, INTERPOLATION, NO_SUPPORT,
                                        O3_CONFIG_PATH, O3_DB_PATH, O2_DB_PATH, PROJECT_ROOT, THESIS_DB_PATH,
                                        code_commit, load_config, sha256_file, utc_now, zone_limits, O5_CONFIG_PATH)
from kambale.objective_5.db import connect_o5, connect_readonly
from kambale.objective_5.bootstrap import quantise, dequantise
from kambale.objective_5.grid import DEPTH_EXTRAPOLATED, SUPPORTED
from kambale.objective_5.importer import check_downhole, check_handoff_match, DOWNHOLE_TOLERANCE, parse_downhole_experiment
from kambale.objective_5.refit import front_settings

ALLOWED_PREDICTORS = {"easting_m", "northing_m", "z_relative_m", "depth_below_weathering_front_m"}
FORBIDDEN_COLUMN_TOKENS = ("elev", "dem_", "rl_m", "absolute")
FRONT_TOLERANCE = 1e-9


def _g(gate_id, name, status, scope, detail):
    return {"gate_id": gate_id, "gate_name": name, "status": status, "scope": scope, "detail": detail}


def _independent_hole_fronts(rows, front_codes) -> dict:
    """Observed front per hole, recomputed here from the stored intervals (own implementation of the Objective 3 rule)."""
    codes = set(front_codes)
    per_hole: dict = {}
    for r in rows:
        per_hole.setdefault(r["hole_id"], []).append(r)
    out = {}
    for hole, items in per_hole.items():
        front = [it for it in items if it["weathering_code"] in codes]
        if not front:
            continue
        mid = np.array([it["midpoint_m"] for it in items], dtype=np.float64)
        zr = np.array([it["z_relative_m"] for it in items], dtype=np.float64)
        slope = float(np.sum(mid * zr) / np.sum(mid * mid))
        first = min(front, key=lambda it: it["depth_from_m"])
        out[hole] = (first["easting_m"], first["northing_m"], slope * first["depth_from_m"])
    return out


def run(o5_path=None, config_path=None) -> dict:
    cfg, cfg_sha = load_config(config_path or O5_CONFIG_PATH)
    o5 = connect_o5(o5_path)
    try:
        receipt = o5.execute("SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
        if receipt is None:
            raise RuntimeError("no receipt: run the import first")
        run_id = o5.execute("INSERT INTO stage_runs (run_kind, config_version, config_sha256, started_utc, status, "
                            "code_commit, note) VALUES ('VERIFY', ?, ?, ?, 'RUNNING', ?, 'gate runner')",
                            (cfg["config_version"], cfg_sha, utc_now(), code_commit())).lastrowid
        created = utc_now()
        gates = []
        o3_cfg, _ = load_o3_config(O3_CONFIG_PATH)
        inputs = cfg["inputs"]

        # G01 input receipts
        bad = []
        for row in o5.execute("SELECT role, path, sha256 FROM input_files"):
            p = PROJECT_ROOT / row["path"]
            if not p.exists() or sha256_file(p) != row["sha256"]:
                bad.append(row["role"])
        gates.append(_g("G01", "Input file receipts", "PASS" if not bad else "STOP", "input",
                        f"{len(bad)} input files differ from their receipts" + (f": {bad}" if bad else "")))

        # G02 handoffs
        required = inputs["require_handoff_match"]
        g02_detail = []
        g02_ok = True
        for item in inputs["handoffs"]:
            tier = item["tier"]
            o4 = connect_readonly(PROJECT_ROOT / item["database"])
            try:
                sel = o4.execute("SELECT model_id FROM comparison_decisions WHERE role = 'SELECTED'").fetchone()[0]
                ru = o4.execute("SELECT model_id FROM comparison_decisions WHERE role = 'COMPARATOR'").fetchone()[0]
            finally:
                o4.close()
            try:
                check_handoff_match(tier, sel, ru, required)
            except Exception as exc:  # StopError
                g02_ok = False
                g02_detail.append(str(exc))
            stored = o5.execute("SELECT match_status FROM handoffs WHERE tier = ?", (tier,)).fetchone()
            if stored is None or stored["match_status"] != "MATCH":
                g02_ok = False
                g02_detail.append(f"{tier} stored handoff is not MATCH")
        gates.append(_g("G02", "Locked handoff receipts match configuration", "PASS" if g02_ok else "STOP", "input",
                        "; ".join(g02_detail) if g02_detail else "selected and runner-up models match for both tiers"))

        # G03 down-hole variogram
        dh = o5.execute("SELECT * FROM downhole_variogram WHERE check_id = 1").fetchone()
        g03 = "STOP"
        g03_detail = "no down-hole record"
        if dh is not None:
            o2 = connect_readonly(O2_DB_PATH)
            try:
                direction, cver = parse_downhole_experiment(inputs["downhole_variogram"]["experiment"])
                fit = o2.execute(
                    "SELECT f.fit_id, f.model, f.objective_value FROM variogram_fits f JOIN variogram_experiments e "
                    "ON e.experiment_id = f.experiment_id WHERE e.direction_id = ? AND e.config_version = ? AND "
                    "e.variant = 'BASE' AND f.fit_status = 'FITTED' AND f.fit_id = ?",
                    (direction, cver, dh["o2_fit_id"])).fetchone()
                params = {r["parameter"]: float(r["estimate"]) for r in o2.execute(
                    "SELECT parameter, estimate FROM variogram_fit_parameters WHERE fit_id = ?", (dh["o2_fit_id"],))}
            finally:
                o2.close()
            try:
                if fit is None:
                    raise ValueError("the recorded down-hole fit is not a FITTED BASE fit of the named configuration")
                exp = inputs["downhole_variogram"]["expected_values"]
                worst = check_downhole({"model": fit["model"], "nugget": params["nugget"],
                                        "structured_sill": params["structured_sill"],
                                        "practical_range_m": params["range_m"]}, exp, DOWNHOLE_TOLERANCE)
                g03 = "PASS"
                g03_detail = f"fit {dh['o2_fit_id']} {fit['model']}; maximum absolute difference {worst:.2e}"
            except Exception as exc:
                g03_detail = str(exc)
        gates.append(_g("G03", "Down-hole variogram parameters", g03, "input", g03_detail))

        # G04 no absolute elevation
        cols = [r[1] for r in o5.execute("PRAGMA table_info(grid_cells)")]
        bad_cols = [c for c in cols if any(t in c.lower() for t in FORBIDDEN_COLUMN_TOKENS)]
        pred_bad = []
        for r in o5.execute("SELECT tier, role, predictors_json FROM final_refits"):
            names = set(json.loads(r["predictors_json"]))
            if not names <= ALLOWED_PREDICTORS or "z_relative_m" not in names:
                pred_bad.append(f"{r['tier']} {r['role']}")
        gates.append(_g("G04", "No absolute elevation used", "PASS" if not bad_cols and not pred_bad else "STOP",
                        "geometry", f"grid columns with elevation tokens: {bad_cols}; refits with other predictors: "
                                    f"{pred_bad}; vertical axis is z_relative_m"))

        # G05 probabilities
        bad_p = o5.execute(
            "SELECT COUNT(*) FROM grid_cells WHERE zone <> 'NO_SUPPORT' AND (p_selected IS NULL OR p_runner_up IS NULL "
            "OR p_lo IS NULL OR p_hi IS NULL OR p_selected < 0 OR p_selected > 1 OR p_runner_up < 0 OR p_runner_up > 1 "
            "OR p_lo < 0 OR p_hi > 1 OR p_lo > p_hi)").fetchone()[0]
        gates.append(_g("G05", "Probabilities in [0, 1] and present for every supported cell",
                        "PASS" if bad_p == 0 else "STOP", "cells", f"{bad_p} supported cells violate the rule"))

        # G06 bootstrap success
        boots = o5.execute("SELECT zone, n_replicates, n_success, success_fraction FROM bootstrap_summary").fetchall()
        bcfg = cfg["uncertainty_measures"]["hole_bootstrap"]
        ok6 = len(boots) == 2 and all(b["n_replicates"] == int(bcfg["n_replicates"]) and
                                      b["success_fraction"] >= float(bcfg["min_successful_fraction"]) for b in boots)
        gates.append(_g("G06", "Bootstrap success fraction", "PASS" if ok6 else "STOP", "bootstrap",
                        "; ".join(f"{b['zone']}: {b['n_success']}/{b['n_replicates']}" for b in boots)))

        # G07 weathering front recomputed from observed fronts (independent rule and reference IDW loop)
        front_codes = list(o3_cfg["features"]["derived"]["depth_below_weathering_front_m"]["front_codes"])
        obs_rows = o5.execute("SELECT * FROM observations ORDER BY upstream_interval_id").fetchall()
        ref_fronts = _independent_hole_fronts(obs_rows, front_codes)
        stored_fronts = {r["hole_id"]: (r["easting_m"], r["northing_m"], r["front_z_m"]) for r in
                         o5.execute("SELECT * FROM hole_fronts")}
        fronts_ok = set(ref_fronts) == set(stored_fronts) and all(
            max(abs(a - b) for a, b in zip(ref_fronts[h], stored_fronts[h])) <= FRONT_TOLERANCE for h in ref_fronts)
        fs = front_settings(o3_cfg)
        names = sorted(ref_fronts)
        pts = np.array([[ref_fronts[h][0], ref_fronts[h][1]] for h in names])
        vals = np.array([ref_fronts[h][2] for h in names])
        cells = o5.execute("SELECT cell_id, ix, iy, centre_easting_m, centre_northing_m, z_relative_m, "
                           "depth_below_weathering_front_m FROM grid_cells").fetchall()
        keys = {}
        xy_list = []
        for c in cells:
            k = (c["ix"], c["iy"])
            if k not in keys:
                keys[k] = len(xy_list)
                xy_list.append((c["centre_easting_m"], c["centre_northing_m"]))
        ref_surface = np.array([o3_front.idw(pts, vals, np.array([q]), fs["power"], fs["k"], fs["coincident"])[0]
                                for q in xy_list])
        max_front_diff = 0.0
        for c in cells:
            ref = ref_surface[keys[(c["ix"], c["iy"])]] - c["z_relative_m"]
            max_front_diff = max(max_front_diff, abs(ref - c["depth_below_weathering_front_m"]))
        front_status = "PASS" if fronts_ok and max_front_diff <= FRONT_TOLERANCE else "STOP"
        gates.append(_g("G07", "Weathering front on the grid recomputed from observed hole fronts", front_status,
                        "geometry", f"{len(names)} observed fronts; {len(xy_list)} horizontal cells; maximum absolute "
                                    f"difference {max_front_diff:.2e} (tolerance {FRONT_TOLERANCE:g}); front table "
                                    f"matches recomputation: {fronts_ok}"))

        # G08 NO_SUPPORT cells
        bad8 = o5.execute("SELECT COUNT(*) FROM grid_cells WHERE zone = 'NO_SUPPORT' AND (p_selected IS NOT NULL OR "
                          "p_runner_up IS NOT NULL OR p_lo IS NOT NULL OR class_label <> 'NO_SUPPORT')").fetchone()[0]
        gates.append(_g("G08", "NO_SUPPORT cells carry no probability or confident class", "PASS" if bad8 == 0 else
                        "STOP", "cells", f"{bad8} NO_SUPPORT cells carry a probability or a class other than NO_SUPPORT"))

        # G09 grid counts
        meta = {r["meta_key"]: json.loads(r["meta_value"]) for r in o5.execute("SELECT * FROM grid_meta")}
        n_expected = meta["n_easting"] * meta["n_northing"] * meta["n_z"]
        n_rows = o5.execute("SELECT COUNT(*) FROM grid_cells").fetchone()[0]
        n_layers = o5.execute("SELECT COUNT(*) FROM grid_layers").fetchone()[0]
        n_distinct = o5.execute("SELECT COUNT(DISTINCT ix || ',' || iy || ',' || iz) FROM grid_cells").fetchone()[0]
        gates.append(_g("G09", "Grid cell counts consistent", "PASS" if n_rows == n_expected == n_distinct and
                        n_layers == meta["n_z"] else "STOP", "grid",
                        f"{n_rows} cells stored; {n_expected} expected from the axes; {n_distinct} distinct; "
                        f"{n_layers} layers"))

        # G10 zones recomputed from collar coordinates of the thesis database (brute force)
        thesis = connect_readonly(THESIS_DB_PATH)
        try:
            version = o5.execute("SELECT dataset_version_id FROM collars LIMIT 1").fetchone()[0]
            col = thesis.execute("SELECT utm_easting_m, utm_northing_m FROM holes WHERE dataset_version_id = ?",
                                 (version,)).fetchall()
        finally:
            thesis.close()
        cxy = np.array([[r[0], r[1]] for r in col], dtype=np.float64)
        limits = zone_limits(cfg)
        xy_arr = np.array(xy_list, dtype=np.float64)
        dmin = np.empty(xy_arr.shape[0])
        for a in range(0, xy_arr.shape[0], 4000):
            blk = xy_arr[a:a + 4000]
            dd = np.sqrt(((blk[:, None, :] - cxy[None, :, :]) ** 2).sum(axis=2))
            dmin[a:a + 4000] = dd.min(axis=1)
        zone_ref_xy = np.where(dmin <= limits[INTERPOLATION], INTERPOLATION,
                               np.where(dmin <= limits[EXTRAPOLATION], EXTRAPOLATION, NO_SUPPORT)).astype(object)
        stored_zone = {r["cell_id"]: r["zone"] for r in o5.execute("SELECT cell_id, zone FROM grid_cells")}
        cell_xy = np.array([keys[(c["ix"], c["iy"])] for c in cells], dtype=np.int64)
        zone_ref_cells = zone_ref_xy[cell_xy]
        zone_stored = np.array([stored_zone[c["cell_id"]] for c in cells], dtype=object)
        mismatch = int(np.sum(zone_ref_cells != zone_stored))
        gates.append(_g("G10", "Zones recomputed from collar coordinates", "PASS" if mismatch == 0 else "STOP", "zones",
                        f"{len(col)} collars (brute force, thesis database); {mismatch} cells differ from the stored zone"))

        # G11 depth support recomputed (brute force neighbourhood)
        deep = {r["hole_id"]: r["zmin"] for r in o5.execute(
            "SELECT hole_id, MIN(z_relative_m) AS zmin FROM observations WHERE in_binary_target = 1 GROUP BY hole_id")}
        hole_ids = sorted(deep)
        hxy = np.array([[r["easting_m"], r["northing_m"]] for r in o5.execute(
            "SELECT hole_id, easting_m, northing_m FROM collars ORDER BY hole_id")])
        hz = np.array([deep[h] for h in hole_ids])
        radius = float(cfg["support_zones"]["depth_support"]["neighbourhood_m"])
        dep_mismatch = 0
        stored_dep = {r["cell_id"]: r["depth_support"] for r in o5.execute("SELECT cell_id, depth_support FROM grid_cells")}
        per_xy_ref = {}
        for key, idx in keys.items():
            q = np.array(xy_list[idx])
            dd = np.sqrt(((hxy - q) ** 2).sum(axis=1))
            within = dd <= radius
            deepest = hz[within].min() if within.any() else hz[int(np.argmin(dd))]
            per_xy_ref[key] = deepest
        for c in cells:
            zz = c["z_relative_m"]
            ref = DEPTH_EXTRAPOLATED if zz < per_xy_ref[(c["ix"], c["iy"])] else SUPPORTED
            if ref != stored_dep[c["cell_id"]]:
                dep_mismatch += 1
        gates.append(_g("G11", "Depth support recomputed", "PASS" if dep_mismatch == 0 else "STOP", "zones",
                        f"{dep_mismatch} cells differ from the recomputed depth-support flag"))

        # G12 artifacts
        art_bad = []
        for r in o5.execute("SELECT tier, role, artifact_path, artifact_sha256 FROM final_refits"):
            p = PROJECT_ROOT / r["artifact_path"]
            if not p.exists() or sha256_file(p) != r["artifact_sha256"]:
                art_bad.append(f"{r['tier']} {r['role']}")
        gates.append(_g("G12", "Final model artifacts match their SHA-256 records", "PASS" if not art_bad else "STOP",
                        "artifacts", f"{len(art_bad)} artifacts differ" + (f": {art_bad}" if art_bad else "")))

        # G13 classification truth (recomputed from stored probabilities)
        rows = o5.execute("SELECT zone, depth_support, p_lo, p_hi, disagreement, class_label FROM grid_cells").fetchall()
        lo = np.array([np.nan if r["p_lo"] is None else r["p_lo"] for r in rows])
        hi = np.array([np.nan if r["p_hi"] is None else r["p_hi"] for r in rows])
        dis = np.array([np.nan if r["disagreement"] is None else r["disagreement"] for r in rows])
        zone_arr = np.array([r["zone"] for r in rows], dtype=object)
        dep_arr = np.array([r["depth_support"] for r in rows], dtype=object)
        stored_cls = np.array([r["class_label"] for r in rows], dtype=object)
        recomputed = classify_arrays(lo, hi, dis, zone_arr, dep_arr, cfg["classification"]["decision_threshold"],
                                     cfg["classification"]["disagreement_limit"])
        cls_bad = int(np.sum(recomputed != stored_cls))
        gates.append(_g("G13", "Classification recomputed from stored probabilities", "PASS" if cls_bad == 0 else "STOP",
                        "classes", f"{cls_bad} cells differ from the recomputed class"))

        # G14 carried validation equals Objective 4 pooled values
        cv_bad = 0
        for item in inputs["handoffs"]:
            o4 = connect_readonly(PROJECT_ROOT / item["database"])
            try:
                for r in o5.execute("SELECT * FROM carried_validation WHERE tier = ?", (item["tier"],)):
                    v = o4.execute("SELECT value FROM pooled_metrics WHERE model_id = ? AND metric_id = ? AND weighting = ?",
                                   (r["model_id"], r["metric_id"], r["weighting"])).fetchone()
                    if v is None or abs((v[0] or 0.0) - (r["value"] or 0.0)) > 1e-12:
                        cv_bad += 1
            finally:
                o4.close()
        gates.append(_g("G14", "Carried Objective 4 validation equals the source", "PASS" if cv_bad == 0 else "STOP",
                        "validation", f"{cv_bad} carried values differ from the Objective 4 pooled metrics"))

        # G15 quantisation round trip
        sample = np.random.default_rng(1).uniform(0, 1, 200000)
        err = float(np.max(np.abs(dequantise(quantise(sample)) - sample)))
        gates.append(_g("G15", "uint8 quantisation round trip", "PASS" if err <= 1.0 / 510.0 + 1e-15 else "STOP",
                        "bootstrap", f"maximum round-trip error {err:.6f} (limit 1/510 = {1 / 510:.6f})"))

        # WARN gates
        mismatched = o5.execute("SELECT tier, role, model_id, hyperparameters_json, o3_most_frequent_json, "
                                "o3_folds_selected FROM final_refits WHERE full_data_matches_o3_mode = 0").fetchall()
        gates.append(_g("W01", "Full-data hyperparameters versus the most frequent Objective 3 fold choice",
                        "WARN" if mismatched else "PASS", "hyperparameters",
                        "; ".join(f"{m['tier']} {m['model_id']}: full {m['hyperparameters_json']} vs O3 mode "
                                  f"{m['o3_most_frequent_json']} ({m['o3_folds_selected']} folds)" for m in mismatched)
                        or "all full-data choices equal the most frequent Objective 3 fold choice"))
        iz = o5.execute("SELECT COUNT(*) AS n, SUM(CASE WHEN depth_support = 'DEPTH_EXTRAPOLATED' THEN 1 ELSE 0 END) AS d "
                        "FROM grid_cells WHERE zone = 'INTERPOLATION'").fetchone()
        share = (iz["d"] or 0) / iz["n"] if iz["n"] else 0.0
        gates.append(_g("W02", "Share of INTERPOLATION cells that are DEPTH_EXTRAPOLATED",
                        "WARN" if share > 0.5 else "PASS", "zones", f"{share:.3f} of {iz['n']} interpolation cells"))

        stopped = any(g["status"] == "STOP" for g in gates)
        for g in gates:
            o5.execute("INSERT INTO gate_results (run_id, gate_id, gate_name, status, scope, detail, created_utc) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?)", (run_id, g["gate_id"], g["gate_name"], g["status"], g["scope"],
                                                        g["detail"], created))
        o5.execute("UPDATE stage_runs SET status = ?, finished_utc = ? WHERE run_id = ?",
                   ("STOPPED" if stopped else "COMPLETED", utc_now(), run_id))
        return {"run_id": run_id, "stopped": stopped, "gates": gates}
    finally:
        o5.close()


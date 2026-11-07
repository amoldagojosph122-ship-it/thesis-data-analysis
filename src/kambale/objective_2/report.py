"""Objective 2 reports, lineage and manifests (specification 04, section 8; specification 06, section 2).

Writes reports/objective_2/README.md, RUN_REPORT.md, BLOCKED_OR_DEFERRED.md, DATA_LINEAGE.json and FIGURE_MANIFEST.csv.
Every number in the reports is read from the database, or from the tables already rendered from it. Manifest rows are
written for each report file (kind REPORT) and for the two manifest files (kind MANIFEST), so that verify G30 re-checks
them. The gate table is taken from the latest VERIFY run, which `all` runs before this command; `all` then runs verify once
more to re-check the hashes of these files.
"""

from __future__ import annotations

import csv
import importlib.metadata
import io
import json
import platform

from kambale.objective_2 import O2_CODE_VERSION, O2_SCHEMA_VERSION
from kambale.objective_2.config import (O2_CONFIG_PATH, O2_DB_PATH, O2_FIGURE_DIR, O2_REPORT_DIR, O2_TABLE_DIR, PROJECT_ROOT,
                                        StopError, UPSTREAM_DB_PATH, code_commit, load_config, sha256_bytes, utc_now)
from kambale.objective_2.db import connect_o2
from kambale.objective_2.figures import FIGURES
from kambale.objective_2.tables import TABLES

EXIT_GATES = ("G01", "G02", "G03", "G07", "G08", "G14", "G19", "G25", "G26", "G27", "G28", "G29", "G30")
PYTEST_OUTPUT = O2_REPORT_DIR / "PYTEST_OUTPUT.txt"
SUPERSEDED_NOTE = (
    "Configuration O2-CFG-2026.11.05-1 measured every between-hole lag in three dimensions and used three-dimensional "
    "distances for the directional classes. Its first analysis gave a between-hole variogram with all 25 lag bins supported "
    "and gamma between 0.15 and 0.24, close to p(1 - p); the exponential fit's range sat at the 10 m lower bound with a "
    "structured sill near zero. The within-hole fit had a range near 15 m and a sill near 0.177. The azimuth class at 90 "
    "degrees was supported with its range at the lower bound, and the other three azimuth classes were skipped. Its "
    "handoff decision (PROVISIONAL) was judged invalid, because the three-dimensional lag mixes depth separation into the "
    "between-hole structure. That run is not used anywhere in this report. Its configuration file is kept at "
    "config/objective_2/superseded/variogram_config_O2-CFG-2026.11.05-1.yaml; its database was set aside and is not part of "
    "the deliverables.")
DEVIATIONS = (
    "The first analysis under configuration 1 was judged invalid after inspection (section 4); configuration 2 was written "
    "before any configuration-2 result was computed.",
    "The first configuration-2 analysis stopped on a coding error (every sensitivity value was converted to a number, so the "
    "text value for within-hole inclusion raised an error). The partial database was set aside and the import and analysis were "
    "repeated from an empty database.",
    "The first handoff rationale stated only that no lateral model was FITTED. The rationale now lists each model's reason; "
    "the decision is unchanged.",
    "The gate set was extended after the first VERIFY run to cover the stage exit requirements of specification 03 (G07, "
    "G15, G18, G21 to G24), G05 and G06 were brought into line with the specification wording, and G28 now covers tables. "
    "Gate results shown here come from the final VERIFY run before this report was written.",
    "The table query registry was added (schema O2-SCHEMA-2026.11.05-3) so that every table has a registered SQL hash, "
    "as figures already had.",
    "Figures were re-rendered several times for layout only (label placement, explicit margins, legend contents). The data "
    "rows were not changed between renders.",
    "The sensitivity variant STRICT_SUPPORT_200_PAIRS did not change any supported bin: the 200-pair threshold is not binding "
    "for the lateral family, whose bins hold at least 1,559 pairs each. The binding support constraint is the independent "
    "hole-pair threshold. The result is reported as found; the configuration was not altered after the run.",
    "Anisotropy is not evaluated. The azimuth fits are not leave-one-line-out tested, so no range ratio is claimed.",
    "The independent comparison with scikit-gstat was denied by the permission system once. It was run after the user "
    "approved it in chat; its result is in section 13.",
    "A Stage A test rewrote three tracked F06 figures in the Objective 2 folder during a full test run. They were restored from "
    "git, and the test now renders into a temporary folder.",
    "Configuration 3 was written before it ran and was not changed afterwards. Its comparator sample is the DESIGN binary set. "
    "STRICT agrees with DESIGN on that set, so the comparator does not test the 81 intervals that DESIGN excludes; a comparator "
    "on the full STRICT sample would need a further predeclared version.",
    "Configuration O2-CFG-2026.11.05-4 adds one SKIP record for the tentative geologic orientation factor that specification 02 "
    "section 10 names. No numeric setting changed. Configuration 2 is kept in config/objective_2/superseded/. The rebuilt database "
    "was compared with the configuration-2 build, and its experiments, fits and handoff are identical (decisions.md, O2-D15).",
    "The run order of `all` changed. Gates run before any figure or table is written, again before the report, and once more "
    "after the report (decisions.md, O2-D16). A STOP withdraws the receipt's handoff rows. Analysis rows are written once per "
    "receipt, so a withdrawn handoff needs a rebuild from an empty database.",
    "Gate G01 now also checks the row count against the receipt and every observed hole identifier against the upstream v_holes "
    "(specification 04, section 9). It previously checked only the version key and the content hash (decisions.md, O2-D17).",
    "Specifications 01, 03, 04 and 06 were corrected to the implemented command set, the nine figures, the within-hole pair flag "
    "and the gate numbers (decisions.md, O2-D17). Stage A's figures F05 to F09 are still under figures/objective_2: the Stage A "
    "registry tags F05 to F08 as Objective 2, and the Objective 1 database records the F05 and F06 outputs there. Moving them "
    "would change those database rows, so the move is left for a decision (decisions.md, O2-D14).",
    "The official Spec Kit initialisation (specify init) and the agent-side Spec Kit commands were not run. Re-initialising an "
    "existing project risks overwriting its templates. Specifications 01 to 07 and the task table in specification 07 are the "
    "record instead (specification 07, section 1a).")


def _rows(conn, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _one(conn, sql: str, params: tuple = ()) -> dict:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row else {}


def _f(value, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _md_body(path) -> list[str]:
    """A rendered table's Markdown without its title line."""
    return path.read_text(encoding="utf-8").splitlines()[1:]


def _rel(path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _versions() -> list[str]:
    out = []
    for pkg in ("numpy", "scipy", "matplotlib", "PyYAML", "pytest"):
        try:
            out.append(f"{pkg} {importlib.metadata.version(pkg)}")
        except importlib.metadata.PackageNotFoundError:
            out.append(f"{pkg} not installed")
    return out


def _independent_check_status() -> str:
    path = O2_REPORT_DIR / "INDEPENDENT_CHECK.txt"
    if not path.exists():
        return ("scikit-gstat was installed with uv into a scratch directory outside the project environment, because "
                "installing it into the project environment would downgrade scipy from 1.18.0 to 1.16.3. The comparison has "
                "not been run")
    result = next((line for line in path.read_text(encoding="utf-8").splitlines()
                   if line.startswith("Maximum absolute difference")), "result line not found")
    return ("scikit-gstat was installed with uv into a scratch directory outside the project environment, because installing "
            "it into the project environment would downgrade scipy from 1.18.0 to 1.16.3. The comparison ran after the user "
            "approved it in chat, on the three-dimensional omnidirectional experiment with within-hole pairs included, which "
            "scikit-gstat's Matheron estimator also uses. " + result + " The lateral basis is not compared directly, because "
            "scikit-gstat cannot restrict pairs to a relative-depth band. Both use the same estimator, so the agreement is "
            "evidence for the pair counting and the binning")


def write_all(o2_path=O2_DB_PATH) -> dict:
    cfg, cfg_sha = load_config(O2_CONFIG_PATH)
    conn = connect_o2(o2_path)
    try:
        rc = _one(conn, "SELECT * FROM source_receipts ORDER BY receipt_id DESC LIMIT 1")
        if not rc:
            raise StopError("no receipt: run the import first")
        rid = rc["receipt_id"]
        created = utc_now()
        ir = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'IMPORT' AND receipt_id = ? ORDER BY run_id DESC LIMIT 1", (rid,))
        an = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'ANALYSE' AND receipt_id = ? ORDER BY run_id DESC LIMIT 1", (rid,))
        vr = _one(conn, "SELECT * FROM stage_runs WHERE run_kind = 'VERIFY' ORDER BY run_id DESC LIMIT 1")
        if not vr:
            raise StopError("no VERIFY run: run verify before report")
        gates = _rows(conn, "SELECT gate_id, gate_name, status, scope, detail FROM gate_results WHERE run_id = ? ORDER BY gate_id",
                      (vr["run_id"],))
        status = {g["gate_id"]: g["status"] for g in gates}
        exit_failed = [g for g in EXIT_GATES if status.get(g) != "PASS"]
        handoff = _one(conn, "SELECT * FROM continuity_handoff_decisions WHERE receipt_id = ? ORDER BY handoff_id DESC LIMIT 1", (rid,))
        occ = _one(conn, "SELECT (SELECT COUNT(*) FROM collar_locations WHERE receipt_id = :r) AS holes, "
                         "(SELECT COUNT(DISTINCT line_code) FROM collar_locations WHERE receipt_id = :r) AS lines, "
                         "(SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = :r) AS intervals, "
                         "(SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = :r AND in_binary_target = 1) AS binary_n, "
                         "(SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = :r AND label_state = 'POSITIVE') AS positive_n, "
                         "(SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = :r AND label_state = 'NEGATIVE') AS negative_n, "
                         "(SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = :r AND label_state = 'AMBIGUOUS') AS ambiguous_n, "
                         "(SELECT COUNT(*) FROM analysis_observations WHERE receipt_id = :r AND label_state = 'UNRESOLVED') AS unresolved_n",
                    {"r": rid})
        line_prev = _rows(conn, "SELECT line_code, n_holes, binary_n, positive_n, graphitic_fraction_binary AS fraction "
                                "FROM line_occurrence_summaries WHERE receipt_id = ? ORDER BY line_code", (rid,))
        stats = {(s["stat_group"], s["stat_name"]): s["stat_value"] for s in _rows(
            conn, "SELECT stat_group, stat_name, stat_value FROM spatial_support_statistics WHERE receipt_id = ?", (rid,))}
        base_exp = {r["direction_id"]: r for r in _rows(
            conn, "SELECT e.experiment_id, e.direction_id, "
                  "(SELECT COUNT(*) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS supported, "
                  "(SELECT MIN(gamma) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS gmin, "
                  "(SELECT MAX(gamma) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS gmax "
                  "FROM variogram_experiments e WHERE e.receipt_id = ? AND e.variant = 'BASE'", (rid,))}
        lateral_pairs = _one(conn, "SELECT MIN(n_pairs) AS pmin, MAX(n_pairs) AS pmax, MIN(n_independent_hole_pairs) AS hmin, "
                                   "MAX(n_independent_hole_pairs) AS hmax FROM pair_sampling_diagnostics WHERE receipt_id = ? "
                                   "AND direction_id = 'LATERAL_BETWEEN' AND support_status = 'SUPPORTED'", (rid,))
        downhole = _rows(conn, "SELECT f.model, f.fit_status, p.parameter, p.estimate FROM variogram_fit_parameters p "
                               "JOIN variogram_fits f ON f.fit_id = p.fit_id JOIN variogram_experiments e ON e.experiment_id = f.experiment_id "
                               "WHERE e.receipt_id = ? AND e.direction_id = 'DOWNHOLE_WITHIN' AND e.variant = 'BASE' ORDER BY f.model, p.parameter",
                         (rid,))
        dh = {(r["model"], r["parameter"]): r["estimate"] for r in downhole}
        sens = _rows(conn, "SELECT s.variant_name, s.changed_factor, s.changed_value, s.status, s.reason, "
                           "(SELECT COUNT(*) FROM variogram_lag_bins b WHERE b.experiment_id = s.experiment_id AND b.supported = 1) AS supported "
                           "FROM sensitivity_runs s WHERE s.run_id = ? AND s.changed_factor <> 'excluded_line' ORDER BY s.sensitivity_id",
                     (an.get("run_id", -1),))
        loo = _rows(conn, "SELECT variant_name, reason FROM sensitivity_runs WHERE run_id = ? AND changed_factor = 'excluded_line' "
                          "ORDER BY sensitivity_id", (an.get("run_id", -1),))
        aniso = _rows(conn, "SELECT direction_a, direction_b, support_status, decision, reason FROM anisotropy_diagnostics "
                            "WHERE receipt_id = ?", (rid,))
        figures = _rows(conn, "SELECT figure_id, title, status, reason, caption FROM figure_registry ORDER BY figure_id")
        tables = _rows(conn, "SELECT table_id, title, status, row_count, reason FROM table_registry ORDER BY table_id")
        table_names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()]
        table_counts = [{"name": name, "n": conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]} for name in table_names]
        pytest_text = PYTEST_OUTPUT.read_text(encoding="utf-8").strip() if PYTEST_OUTPUT.exists() else (
            "Not recorded in this report. Run pytest with its output written to reports/objective_2/PYTEST_OUTPUT.txt, "
            "then run report again.")

        # Figures and tables first, so that the manifest and lineage can list their hashes.
        manifest_rows = []
        for fig in figures:
            if fig["status"] != "GENERATED":
                continue
            stem = FIGURES[fig["figure_id"]][1]
            for ext in ("svg", "pdf", "png"):
                path = O2_FIGURE_DIR / f"{stem}.{ext}"
                queries = _rows(conn, "SELECT query_name, sql_path, sql_sha256, row_count FROM figure_query_registry "
                                      "WHERE figure_id = ? ORDER BY query_name", (fig["figure_id"],))
                manifest_rows.append({"artifact_path": _rel(path), "kind": "FIGURE", "id": fig["figure_id"],
                                      "format": ext.upper(), "sha256": sha256_bytes(path.read_bytes()),
                                      "bytes": path.stat().st_size, "sql_path": queries[0]["sql_path"],
                                      "sql_sha256": queries[0]["sql_sha256"],
                                      "queries": ";".join(f"{q['query_name']}={q['row_count']}" for q in queries)})
        for tab in tables:
            if tab["status"] != "GENERATED":
                continue
            stem = TABLES[tab["table_id"]][1]
            for ext in ("csv", "md", "tex"):
                path = O2_TABLE_DIR / f"{stem}.{ext}"
                queries = _rows(conn, "SELECT query_name, sql_path, sql_sha256, row_count FROM table_query_registry "
                                      "WHERE table_id = ?", (tab["table_id"],))
                manifest_rows.append({"artifact_path": _rel(path), "kind": "TABLE", "id": tab["table_id"],
                                      "format": ext.upper(), "sha256": sha256_bytes(path.read_bytes()),
                                      "bytes": path.stat().st_size, "sql_path": queries[0]["sql_path"],
                                      "sql_sha256": queries[0]["sql_sha256"],
                                      "queries": ";".join(f"{q['query_name']}={q['row_count']}" for q in queries)})

        O2_REPORT_DIR.mkdir(parents=True, exist_ok=True)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["artifact_path", "kind", "id", "format", "sha256", "bytes", "sql_path",
                                                 "sql_sha256", "queries"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest_rows)
        manifest_path = O2_REPORT_DIR / "FIGURE_MANIFEST.csv"
        manifest_path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

        # Blocked or deferred items.
        open_items = [g for g in gates if g["status"] in ("WARN", "SKIP", "DOWNGRADE", "STOP")]
        skipped_sens = [s for s in sens if s["status"] == "SKIPPED"]
        not_supported = [f for f in figures if f["status"] == "NOT_SUPPORTED"] + [t for t in tables if t["status"] == "NOT_SUPPORTED"]
        blocked = [
            "# Objective 2: blocked, skipped and deferred items", "",
            f"Gate results are from VERIFY run {vr['run_id']}. Every WARN, SKIP, DOWNGRADE and STOP is listed.", "",
            "## Gates with a warning or a skip", "", "| gate | status | detail |", "|---|---|---|",
            *[f"| {g['gate_id']} {g['gate_name']} | {g['status']} | {g['detail']} |" for g in open_items],
            "", "## Sensitivity entries not run", "", *[f"- {s['variant_name']}: {s['reason']}" for s in skipped_sens],
            "", "## Figures and tables not supported", "",
            *([f"- {f.get('figure_id', f.get('table_id'))}: {f['reason']}" for f in not_supported] or ["- none"]),
            "", "## Independent checks", "",
            "- Independent comparison with scikit-gstat: " + _independent_check_status() + ".", "",
            "## Deferred work (not performed in this stage)", "",
            "- Lag window: configuration 3 tested lags to 2000 m as an exploratory extension (RUN_REPORT.md section 5.7). "
            "No range is identified inside that window. The median collar-pair separation is "
            f"{_f(stats.get(('COLLAR_PAIR', 'median')), 0)} m.",
            "- Anisotropy: not evaluated. The azimuth fits are not leave-one-line-out tested, and no direction is supported "
            "in both opposite classes.",
            "- Leave-one-line-out refits for the azimuth families: not assessed (exploratory families).",
            "- Absolute elevation and the DEM: not used. Collar RL is missing from the source data (gate G03), and the DEM is "
            "provisional.",
            "- STRICT_SGS_v1 comparator: run under configuration 3 as authorised (RUN_REPORT.md section 5.7). The rule stays "
            "PROPOSED; the authorisation covers the comparator run only. A comparator on the full STRICT sample of 1910 "
            "intervals is not run.",
            "- Collar elevations: the RL column of the raw Collars sheet is empty for all 71 holes. The data request is in "
            "COLLAR_RL_REQUEST.md.",
            "- Objective 3 modelling: not started. The handoff contract is in RUN_REPORT.md section 11.",
            "- On-line versus between-line pairs (master prompt, step 4): not computed. Pairs are split only into within-hole and "
            "between-hole. This needs a further predeclared configuration.",
            "- Projected sections with line orientation and projection offset (master prompt, step 3): not produced. O2-F04 shows "
            "observed hole strips only.",
            "- Official Spec Kit initialisation (specify init) and the agent-side commands: not run (specification 07, section 1a).",
            "- Commit and push of the Objective 2 work: not done. It waits for the user's instruction.", ""]
        blocked_path = O2_REPORT_DIR / "BLOCKED_OR_DEFERRED.md"
        blocked_path.write_text("\n".join(blocked), encoding="utf-8", newline="\n")

        # Run report.
        lines = [
            "# Objective 2 run report: spatial distribution, geological controls and indicator variography", "",
            f"Configuration {cfg['config_version']} (SHA-256 {cfg_sha[:12]}), code {O2_CODE_VERSION}, schema {O2_SCHEMA_VERSION}, "
            f"commit {code_commit() or 'not available'}. Import run {ir.get('run_id')}, analysis run {an.get('run_id')}, "
            f"gate run {vr['run_id']}. Report written {created}.", "",
            "## 1. Status", "",
            ("Stage exit conditions (specification 03, section 6): every required gate is PASS." if not exit_failed else
             "Stage exit conditions NOT met. Gates not PASS: " + ", ".join(exit_failed) + "."),
            f"Handoff decision for Objective 3: {handoff.get('decision_status', 'none')} "
            f"(candidate family {handoff.get('candidate_family', 'none')}). Full-data parameters for test folds: "
            f"{handoff.get('full_data_parameters_for_test_folds', 'n/a')}.", "",
            "## 2. Inputs and receipt", "",
            f"- Objective 1 snapshot: {rc['upstream_path']} (read-only; dataset version {rc['upstream_dataset_version_id']}, "
            f"ETL {rc['upstream_etl_version']}, content SHA-256 {rc['content_sha256'][:12]}).",
            f"- Intervals imported: {rc['row_count']} (each 1 m); holes {occ['holes']}; drill lines {occ['lines']}.",
            f"- Label rule {rc['label_rule_id']} {rc['label_rule_status']}; binary target {occ['binary_n']} intervals "
            f"({occ['positive_n']} POSITIVE, {occ['negative_n']} NEGATIVE); excluded {occ['ambiguous_n']} AMBIGUOUS and "
            f"{occ['unresolved_n']} UNRESOLVED.",
            f"- Geometry {rc['geometry_status']}: straight holes at dip {cfg['geometry']['declared_dip_deg']:g}, azimuth "
            f"{cfg['geometry']['declared_azimuth_deg']:g}; collar elevation absent; depth relative to collar.",
            f"- Coordinates {rc['crs_key']} with datum {rc['crs_datum_status']}; coordinate pair {rc['coordinate_pair_status']}; "
            f"drill lines {rc['drill_line_status']}.", "",
            "## 3. Configuration", "",
            f"Predeclared version {cfg['config_version']} supersedes {cfg.get('supersedes')}. Revision: "
            f"{' '.join(str(cfg['revision_reason']).split())} Correction history (configuration 1 to 2): "
            f"{' '.join(str(cfg['correction_reason']).split())}", "",
            "## 4. Superseded configuration (recorded, not used)", "", SUPERSEDED_NOTE, "",
            "## 5. Results", "",
            "### 5.1 Occurrence and geological controls", "",
            f"- Positive share of binary intervals: {occ['positive_n'] / occ['binary_n']:.3f} overall. By line the positive share "
            f"ranges from {min(r['fraction'] for r in line_prev):.3f} ({min(line_prev, key=lambda r: r['fraction'])['line_code']}) "
            f"to {max(r['fraction'] for r in line_prev):.3f} ({max(line_prev, key=lambda r: r['fraction'])['line_code']}). "
            "This between-line difference is the strongest occurrence contrast in the data; whether it reflects zones, sampling "
            "or geology is not resolved.",
            "- Depth and weathering summaries are in figure O2-F03 and table O2-T02.", "",
            "### 5.2 Support", "",
            f"- Nearest-collar distance: median {_f(stats.get(('COLLAR_NEAREST', 'median')), 1)} m (5th to 95th percentile "
            f"{_f(stats.get(('COLLAR_NEAREST', 'p05')), 1)} to {_f(stats.get(('COLLAR_NEAREST', 'p95')), 1)} m).",
            f"- Collar-pair separation: median {_f(stats.get(('COLLAR_PAIR', 'median')), 0)} m (5th to 95th percentile "
            f"{_f(stats.get(('COLLAR_PAIR', 'p05')), 0)} to {_f(stats.get(('COLLAR_PAIR', 'p95')), 0)} m).",
            f"- Lateral pairs in supported bins: {lateral_pairs.get('pmin')} to {lateral_pairs.get('pmax')} per bin; independent "
            f"hole pairs {lateral_pairs.get('hmin')} to {lateral_pairs.get('hmax')} per bin (thresholds 100 pairs and 10 hole pairs).",
            "", "### 5.3 Variograms and fits", "",
            f"- Lateral between-hole (handoff basis): {base_exp['LATERAL_BETWEEN']['supported']} supported bins; gamma "
            f"{_f(base_exp['LATERAL_BETWEEN']['gmin'])} to {_f(base_exp['LATERAL_BETWEEN']['gmax'])}; marginal variance p(1 - p) "
            f"{_f(p_one_minus_p(conn, rid), 4)}. Both models are NOT_IDENTIFIABLE: the best non-negative fit is a pure nugget, "
            "confirmed by a profile over all candidate ranges (tests/objective_2/test_fitting.py).",
            f"- Three-dimensional between-hole (reported only): {base_exp['OMNI_3D_BETWEEN']['supported']} supported bins; gamma "
            f"{_f(base_exp['OMNI_3D_BETWEEN']['gmin'])} to {_f(base_exp['OMNI_3D_BETWEEN']['gmax'])}; NOT_IDENTIFIABLE.",
            f"- Within-hole (downhole): {base_exp['DOWNHOLE_WITHIN']['supported']} supported bins. Spherical range "
            f"{_f(dh.get(('spherical', 'range_m')), 1)} m, sill {_f(dh.get(('spherical', 'structured_sill')))}, nugget "
            f"{_f(dh.get(('spherical', 'nugget')))}; exponential range {_f(dh.get(('exponential', 'range_m')), 1)} m, sill "
            f"{_f(dh.get(('exponential', 'structured_sill')))}, nugget {_f(dh.get(('exponential', 'nugget')))}. Within-hole "
            "continuity is identified and is reported separately from between-hole structure.",
            "- Horizontal azimuth (exploratory): " + "; ".join(
                f"{d} {base_exp[d]['supported']} supported bins" for d in sorted(base_exp) if d.startswith("LAT_AZ")) +
            ". No azimuth fit is FITTED.", "",
            "Fit-by-fit identifiability and stability are in table O2-T03 (below).", "",
            "### 5.4 Leave-one-line-out", "",
            f"- The lateral basis was refitted once per line ({len(loo) // 2} lines, two models each). The base fits are not FITTED, "
            "so the stability status is NOT_ASSESSED; no envelope is claimed.", "",
            "### 5.5 Sensitivity", "", "| variant | factor | value | status | supported bins | reason |", "|---|---|---|---|---|---|",
            *[f"| {s['variant_name']} | {s['changed_factor']} | {s['changed_value']} | {s['status']} | "
              f"{'' if s['supported'] is None else s['supported']} | {s['reason']} |" for s in sens], "",
            "### 5.6 Anisotropy", "",
            *[f"- {a['direction_a']} against {a['direction_b']}: {a['support_status']}, decision {a['decision']}; {a['reason']}."
              for a in aniso], "",
            *_extension_section(conn, rid),
            *_weathering_section(conn, rid),
            *_structural_section(conn, rid),
            "## 6. Gate results (VERIFY run " + str(vr["run_id"]) + ")", "",
            "| gate | name | status | detail |", "|---|---|---|---|",
            *[f"| {g['gate_id']} | {g['gate_name']} | {g['status']} | {g['detail']} |" for g in gates], "",
            "## 7. Tables", "", *[f"- {t['table_id']}: {t['status']}, {t['row_count']} rows; {t['title']}." for t in tables], "",
            "### O2-T03 variogram fitting report", "", *_md_body(O2_TABLE_DIR / f"{TABLES['O2-T03'][1]}.md"), "",
            "### O2-T04 handoff contract and open items", "", *_md_body(O2_TABLE_DIR / f"{TABLES['O2-T04'][1]}.md"), "",
            "Table O2-T01 (hole and line summary) and table O2-T02 (prevalence by line) are in tables/objective_2 as CSV, "
            "Markdown and LaTeX.", "",
            "## 8. Figures", "",
            *[f"- {f['figure_id']} ({f['status']}): {f['title']}. {f['caption']}" for f in figures], "",
            "## 9. Tests", "", "```text", pytest_text, "```", "",
            "## 10. Deviations and corrections in this stage", "", *[f"- {d}" for d in DEVIATIONS], "",
            "## 11. Objective 3 handoff contract", "",
            f"- Decision: {handoff.get('decision_status')}. Candidate family: {handoff.get('candidate_family')}.",
            "- Parameters: none are supplied. The lateral family did not yield a FITTED, stable model, so no search range or "
            "leave-one-line-out envelope is handed over.",
            "- Full-data parameters for test folds: 0. Any Objective 3 variogram must be refitted inside each outer training fold.",
            "- Allowed: models without a geostatistical continuity term, judged against the gates and the untouched test folds.",
            "- Not allowed: between-hole continuity parameters from these fits, and any claim of spatial continuity between holes.",
            "- Within-hole continuity (downhole range about 15 to 24 m) is a descriptive result. It is not a between-hole basis.",
            f"- Lag setting recorded for reference: {handoff.get('lag_setting_json', '')}", "",
            "## 12. Limitations", "",
            "- Relative depth only: collar elevations are absent, so absolute elevation and the DEM are not used.",
            "- One orientation for all holes (dip -60, azimuth 090): geology cannot be separated from the sampling direction.",
            "- Five drill lines; the between-line contrast is large and its cause is not resolved.",
            "- The lateral window (20 m bins to 500 m) excludes most collar pairs; regional structure beyond it is not assessed.",
            *[f"- Line {r['line_code']} has {r['n_holes']} holes ({r['binary_n']} binary intervals). Any statement about that line "
              "rests on those collars. No gate issues a WARN for it, and no direction is FITTED, so no fitted range depends on it."
              for r in line_prev if r["n_holes"] <= 3], "",
            "## 13. Commands and environment", "", "```bash",
            "./.venv/Scripts/python.exe -I -m kambale.objective_2 all",
            "./.venv/Scripts/python.exe -I -m pytest -o addopts= -q tests/objective_2 > reports/objective_2/PYTEST_OUTPUT.txt",
            "./.venv/Scripts/python.exe -I -m kambale.objective_2 report",
            "./.venv/Scripts/python.exe -I -m kambale.objective_2 verify", "```", "",
            "`all` runs import, analyse, extension, weathering, structural, verify, figures, tables, verify, report and verify. The stages "
            "can also be run one at a time with `import`, `analyse`, `extension`, `weathering`, `structural`, `figures`, `tables`, `report` and `verify`. The report reads "
            "PYTEST_OUTPUT.txt, so the test run comes before the second report.", "",
            f"Python {platform.python_version()} on {platform.system()} {platform.release()}; " + ", ".join(_versions()) + ".",
            f"Independent check: {_independent_check_status()}. It is run from a scratch directory outside the project environment: "
            "`./.venv/Scripts/python.exe -I -m kambale.objective_2.independent_check --site <scratch-directory>`.", "",
            "## 14. Database row counts and receipt hashes", "", "| table | rows |", "|---|---|",
            *[f"| {t['name']} | {t['n']} |" for t in table_counts], "",
            f"Receipt {rc['receipt_id']}: content SHA-256 {rc['content_sha256']}; ordered identifier digest "
            f"{rc['ordered_id_digest']}; selection query SHA-256 {rc['selection_query_sha256']}. Counts are taken when this report "
            "is written.", ""]
        run_path = O2_REPORT_DIR / "RUN_REPORT.md"
        run_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")

        readme = [
            "# Objective 2 outputs", "",
            "Spatial distribution, geological controls and indicator variography of graphitic domains at the Kambale deposit. "
            "The stage reads the Objective 1 database read-only and writes database/kambale_obj2_spatial.sqlite.", "",
            f"Current status: " + ("exit conditions met." if not exit_failed else "exit conditions not met (see RUN_REPORT.md)."),
            f"Handoff decision: {handoff.get('decision_status')}.", "",
            "Contents:", "",
            "- RUN_REPORT.md: the full record of the run, its results, gates, deviations and the Objective 3 handoff contract.",
            "- BLOCKED_OR_DEFERRED.md: every warning, skip and deferred item.",
            "- COLLAR_RL_REQUEST.md: what is needed to add surveyed collar elevations, and the procedure.",
            "- DATA_LINEAGE.json: upstream receipt, label rule, configuration, code and run identifiers, with output hashes.",
            "- FIGURE_MANIFEST.csv: SHA-256 hashes and registered SQL for every figure and table file.",
            "- ../../figures/objective_2 and ../../tables/objective_2: the figures (SVG, PDF, PNG) and tables (CSV, Markdown, LaTeX).", "",
            "Reproduce with the commands in RUN_REPORT.md section 13."]
        (O2_REPORT_DIR / "README.md").write_text("\n".join(readme), encoding="utf-8", newline="\n")

        lineage = {
            "stage": "Objective 2", "generated_utc": created, "code_version": O2_CODE_VERSION,
            "schema_version": O2_SCHEMA_VERSION, "code_commit": code_commit(),
            "upstream": {"logical_name": rc["upstream_logical_name"], "path": rc["upstream_path"],
                         "dataset_version_id": rc["upstream_dataset_version_id"],
                         "dataset_version_key": rc["upstream_dataset_version_key"],
                         "etl_version": rc["upstream_etl_version"], "content_sha256": rc["content_sha256"],
                         "row_count": rc["row_count"], "ordered_id_digest": rc["ordered_id_digest"],
                         "selection_query_sha256": rc["selection_query_sha256"], "read_only": True},
            "label_rule": {"id": rc["label_rule_id"], "status": rc["label_rule_status"],
                           "definition_sha256": rc["label_rule_definition_sha256"]},
            "geometry": {"build_id": rc["geometry_build_id"], "status": rc["geometry_status"], "crs": rc["crs_key"],
                         "datum_status": rc["crs_datum_status"], "coordinate_pair_status": rc["coordinate_pair_status"],
                         "drill_line_status": rc["drill_line_status"], "vertical_basis": rc["vertical_basis"]},
            "configuration": {"version": cfg["config_version"], "sha256": cfg_sha, "supersedes": cfg.get("supersedes")},
            "runs": {"import": ir.get("run_id"), "analyse": an.get("run_id"), "verify": vr["run_id"]},
            "outputs": [{"path": m["artifact_path"], "kind": m["kind"], "id": m["id"], "sha256": m["sha256"]}
                        for m in manifest_rows] + [
                {"path": _rel(manifest_path), "kind": "MANIFEST", "id": "FIGURE_MANIFEST", "sha256": sha256_bytes(manifest_path.read_bytes())},
                {"path": _rel(run_path), "kind": "REPORT", "id": "RUN_REPORT", "sha256": sha256_bytes(run_path.read_bytes())},
                {"path": _rel(blocked_path), "kind": "REPORT", "id": "BLOCKED_OR_DEFERRED", "sha256": sha256_bytes(blocked_path.read_bytes())}],
        }
        lineage_path = O2_REPORT_DIR / "DATA_LINEAGE.json"
        lineage_path.write_text(json.dumps(lineage, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8", newline="\n")

        exports = [(run_path, "REPORT"), (blocked_path, "REPORT"), (O2_REPORT_DIR / "README.md", "REPORT"),
                   (manifest_path, "MANIFEST"), (lineage_path, "MANIFEST")]
        if (O2_REPORT_DIR / "INDEPENDENT_CHECK.txt").exists():
            exports.append((O2_REPORT_DIR / "INDEPENDENT_CHECK.txt", "REPORT"))
        exports.append((O2_REPORT_DIR / "COLLAR_RL_REQUEST.md", "REPORT"))
        for path, kind in exports:
            conn.execute("INSERT OR REPLACE INTO export_manifests (artifact_path, artifact_kind, artifact_sha256, receipt_id, "
                         "created_utc) VALUES (?, ?, ?, ?, ?)", (_rel(path), kind, sha256_bytes(path.read_bytes()), rid, created))
        return {"reports": [_rel(p) for p, _ in exports], "figure_manifest_rows": len(manifest_rows),
                "exit_conditions_met": not exit_failed, "gate_run": vr["run_id"]}
    finally:
        conn.close()


def _extension_section(conn, rid: int) -> list[str]:
    """Section 5.7 of the run report: the configuration-3 extension and the STRICT comparator, read from the database."""
    from kambale.objective_2.extension import EXT_CONFIG_PATH
    ext_cfg, _ = load_config(EXT_CONFIG_PATH)
    head = ["### 5.7 Configuration 3 extension and STRICT comparator (exploratory)", ""]
    run = _one(conn, "SELECT run_id, config_sha256, note FROM stage_runs WHERE run_kind = 'SENSITIVITY' AND config_version = ? "
                     "ORDER BY run_id DESC LIMIT 1", (ext_cfg["config_version"],))
    if not run:
        return head + ["Not run.", ""]
    rows = _rows(conn, "SELECT e.label_rule_id, e.lag_width_m, e.lag_max_m, "
                       "(SELECT COUNT(*) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS supported, "
                       "(SELECT MIN(gamma) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS gmin, "
                       "(SELECT MAX(gamma) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS gmax, "
                       "(SELECT f.fit_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'spherical') AS sph, "
                       "(SELECT f.fit_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'exponential') AS expo, "
                       "(SELECT f.stability_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'spherical') AS sph_stab, "
                       "(SELECT f.stability_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'exponential') AS expo_stab "
                       "FROM variogram_experiments e WHERE e.receipt_id = ? AND e.config_version = ? "
                       "AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s WHERE s.experiment_id = e.experiment_id "
                       "AND s.changed_factor = 'excluded_line') ORDER BY e.label_rule_id, e.lag_max_m",
                 (rid, ext_cfg["config_version"]))
    loo = _rows(conn, "SELECT variant_name, reason FROM sensitivity_runs WHERE run_id = ? AND changed_factor = 'excluded_line' "
                      "ORDER BY sensitivity_id", (run["run_id"],))
    loo_fitted = sum(1 for r in loo if r["reason"].startswith("FITTED"))
    join = ("FROM analysis_observations a JOIN comparator_observations c ON c.receipt_id = a.receipt_id "
            "AND c.upstream_interval_id = a.upstream_interval_id WHERE a.receipt_id = ?")
    disagree = _one(conn, f"SELECT COUNT(*) AS n {join} AND a.in_binary_target = 1 AND c.indicator <> a.indicator", (rid,))["n"]
    excluded = {r["label_state"]: r["n"] for r in _rows(
        conn, f"SELECT c.label_state, COUNT(*) AS n {join} AND a.in_binary_target = 0 GROUP BY c.label_state", (rid,))}
    handoff = _one(conn, "SELECT decision_status FROM continuity_handoff_decisions WHERE receipt_id = ? "
                         "ORDER BY handoff_id DESC LIMIT 1", (rid,))
    any_fitted = any("FITTED" in (r["sph"], r["expo"]) for r in rows if r["label_rule_id"] == "DESIGN_8_2_v1")
    reading = ("a DESIGN model is FITTED in the extension; see the table." if any_fitted else
               "no DESIGN model is FITTED in the extension. The fits run to the window limit or show no structure beyond the "
               "nugget, and the leave-one-line-out refits do not pass the rules, so a longer window does not identify a range.")
    return head + [
        f"Configuration {ext_cfg['config_version']} (SHA-256 {run['config_sha256'][:12]}), stage run {run['run_id']}: {run['note']}.", "",
        "| label rule | lag setting | supported bins | gamma range | spherical | exponential | stability (spherical / exponential) |",
        "|---|---|---|---|---|---|---|",
        *[f"| {r['label_rule_id']} | {r['lag_width_m']:g} m bins to {r['lag_max_m']:g} m | {r['supported']} | "
          f"{_f(r['gmin'], 3)} to {_f(r['gmax'], 3)} | {r['sph']} | {r['expo']} | {r['sph_stab']} / {r['expo_stab']} |"
          for r in rows],
        "",
        f"Leave-one-line-out refits of the DESIGN extension: {len(loo)} refit rows, {loo_fitted} FITTED.", "",
        f"Reading: {reading}",
        f"The STRICT comparator disagrees with DESIGN on {disagree} of the DESIGN binary intervals. On the "
        f"{sum(excluded.values())} intervals that DESIGN leaves ambiguous, STRICT gives "
        + ", ".join(f"{n} {s}" for s, n in sorted(excluded.items())) + ".",
        f"Neither result changes the configuration-2 handoff ({handoff.get('decision_status', 'none')}), which stands as recorded.",
        ""]


def _weathering_section(conn, rid: int) -> list[str]:
    """Section 5.8 of the run report: the configuration-5 weathering front and fresh-rock variography, read from the database."""
    from kambale.objective_2.weathering import WEATHERING_CONFIG_PATH
    w_cfg, _ = load_config(WEATHERING_CONFIG_PATH)
    version = w_cfg["config_version"]
    head = ["### 5.8 Configuration 5: weathering front and fresh-rock variography", ""]
    run = _one(conn, "SELECT run_id, config_sha256, note FROM stage_runs WHERE run_kind = 'SENSITIVITY' AND config_version = ? "
                     "ORDER BY run_id DESC LIMIT 1", (version,))
    if not run:
        return head + ["Not run.", ""]
    diag = _rows(conn, "SELECT stat_group, stat_name, stat_value, n_basis FROM weathering_front_diagnostics "
                       "WHERE receipt_id = ? AND config_version = ?", (rid, version))
    stat = {(d["stat_group"], d["stat_name"]): d["stat_value"] for d in diag}
    schemes = sorted({d["stat_group"] for d in diag if d["stat_group"].startswith("INTERPOLATION_")})
    fv = _rows(conn, "SELECT bin_index, lag_from_m, lag_to_m, n_hole_pairs, gamma, supported FROM weathering_front_variogram "
                     "WHERE receipt_id = ? AND config_version = ? ORDER BY bin_index", (rid, version))
    fresh = _rows(conn, "SELECT e.experiment_id, e.direction_id, "
                        "(SELECT COUNT(*) FROM variogram_lag_bins b WHERE b.experiment_id = e.experiment_id AND b.supported = 1) AS supported, "
                        "(SELECT f.fit_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'spherical') AS sph, "
                        "(SELECT f.fit_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'exponential') AS expo, "
                        "(SELECT f.stability_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'spherical') AS sph_stab, "
                        "(SELECT f.stability_status FROM variogram_fits f WHERE f.experiment_id = e.experiment_id AND f.model = 'exponential') AS expo_stab "
                        "FROM variogram_experiments e WHERE e.receipt_id = ? AND e.config_version = ? "
                        "AND NOT EXISTS (SELECT 1 FROM sensitivity_runs s WHERE s.experiment_id = e.experiment_id "
                        "AND s.changed_factor = 'excluded_line') ORDER BY e.direction_id", (rid, version))
    decisions = _rows(conn, "SELECT variant_name, reason FROM sensitivity_runs WHERE run_id = ? "
                            "AND changed_factor = 'sample_and_vertical_pairing' ORDER BY sensitivity_id", (run["run_id"],))
    loo = _rows(conn, "SELECT variant_name, reason FROM sensitivity_runs WHERE run_id = ? AND changed_factor = 'excluded_line' "
                      "ORDER BY sensitivity_id", (run["run_id"],))
    weath = _rows(conn, "SELECT weathering_code, label_state, n_intervals FROM weathering_cross_tabs WHERE receipt_id = ? "
                        "AND weathering_code IN ('cw','hw')", (rid,))
    logged = sum(w["n_intervals"] for w in weath)
    positive = sum(w["n_intervals"] for w in weath if w["label_state"] == "POSITIVE")
    handoff = _one(conn, "SELECT decision_status FROM continuity_handoff_decisions WHERE receipt_id = ? "
                         "ORDER BY handoff_id DESC LIMIT 1", (rid,))
    scheme_lines = []
    for sg in schemes:
        name = sg.replace("INTERPOLATION_", "").replace("_", " ").lower()
        flag = stat.get((sg, "interpolable"))
        scheme_lines.append(f"| {name} | {_f(stat.get((sg, 'rmse_idw_m')), 2)} | "
                            f"{_f(stat.get((sg, 'rmse_training_mean_m')), 2)} | {_f(stat.get((sg, 'skill_ratio')), 3)} | "
                            f"{'INTERPOLABLE' if flag == 1.0 else 'NOT INTERPOLABLE'} |")
    supported_lags = [f"{b['lag_from_m']:g} to {b['lag_to_m']:g}" for b in fv if b["supported"]]
    dec_text = "; ".join(f"{d['variant_name'].split(':')[-1]} {d['reason'].rsplit('decision ', 1)[-1]}" for d in decisions)
    return head + [
        f"Configuration {version} (SHA-256 {run['config_sha256'][:12]}), stage run {run['run_id']}: {run['note']}.", "",
        "Front definition: the shallowest interval with weathering code mw or sw in each hole, at its relative depth on the "
        "straight hole. Holes with a cw or hw interval below the front are reported, not redefined.", "",
        f"Holes with a front: {_f(stat.get(('FRONT_SUMMARY', 'n_holes')), 0)}; without: "
        f"{_f(stat.get(('FRONT_SUMMARY', 'n_holes_without_front')), 0)}. Front relative elevation mean "
        f"{_f(stat.get(('FRONT_SUMMARY', 'mean_front_z_relative_m')), 2)} m, sd "
        f"{_f(stat.get(('FRONT_SUMMARY', 'sd_front_z_relative_m')), 2)} m, range "
        f"{_f(stat.get(('FRONT_SUMMARY', 'min_front_z_relative_m')), 2)} to "
        f"{_f(stat.get(('FRONT_SUMMARY', 'max_front_z_relative_m')), 2)} m. Holes with a cw or hw interval below the front: "
        f"{_f(stat.get(('FRONT_SUMMARY', 'n_holes_with_reversals')), 0)}.", "",
        f"Along-line adjacent holes ({_f(stat.get(('ALONG_LINE_ADJACENT', 'n_adjacent_pairs')), 0)} pairs): median absolute "
        f"front difference {_f(stat.get(('ALONG_LINE_ADJACENT', 'median_abs_front_difference_m')), 2)} m, 90th percentile "
        f"{_f(stat.get(('ALONG_LINE_ADJACENT', 'p90_abs_front_difference_m')), 2)} m, maximum "
        f"{_f(stat.get(('ALONG_LINE_ADJACENT', 'max_abs_front_difference_m')), 2)} m; median collar distance "
        f"{_f(stat.get(('ALONG_LINE_ADJACENT', 'median_collar_distance_m')), 0)} m.", "",
        "| scheme | IDW RMSE (m) | training-mean RMSE (m) | skill ratio | decision (threshold 0.8) |", "|---|---|---|---|---|",
        *scheme_lines, "",
        f"Front semivariogram (between holes, 25 m bins to 500 m): {len(supported_lags)} of {len(fv)} bins supported "
        "(at least 10 hole pairs)" + (f"; supported lags (m): {', '.join(supported_lags)}." if supported_lags else "."), "",
        "| experiment | supported bins | spherical | exponential | stability (spherical / exponential) |",
        "|---|---|---|---|---|",
        *[f"| {r['direction_id']} | {r['supported']} | {r['sph']} | {r['expo']} | {r['sph_stab']} / {r['expo_stab']} |"
          for r in fresh], "",
        f"Leave-one-line-out refits of the fresh-rock experiments: {len(loo)} refit rows, "
        f"{sum(1 for r in loo if r['reason'].startswith('FITTED'))} FITTED.", "",
        f"Decisions (fresh rock): {dec_text}.", "",
        f"Observability: {positive} of {logged} intervals logged cw or hw carry a POSITIVE DESIGN label. This is a limit of "
        "logging in strongly weathered material; it is not a finding that weathered rock is non-graphitic, and no interval is "
        "relabelled.", "",
        f"Configuration 5 writes no handoff row; the configuration-2 handoff ({handoff.get('decision_status', 'none')}) stands "
        "as recorded.", ""]


def _structural_section(conn, rid: int) -> list[str]:
    """Section 5.9 of the run report: the configuration-6 structural frame, read from the database."""
    from kambale.objective_2.structural import DECISION_PROVISIONAL, read_structural_config
    s_cfg, _, _ = read_structural_config()
    version = s_cfg["config_version"]
    head = ["### 5.9 Configuration 6: structural frame (apparent-dip search, selection null, between-line report)", ""]
    run = _one(conn, "SELECT run_id, config_sha256, note FROM stage_runs WHERE run_kind = 'SENSITIVITY' AND config_version = ? "
                     "AND receipt_id = ? ORDER BY run_id DESC LIMIT 1", (version, rid))
    if not run:
        return head + ["Not run.", ""]
    nulls = _rows(conn, "SELECT n.sample_id, n.frame_id, n.selected_dip_deg, n.observed_max_alignment, n.null_p95_max, n.p_value, "
                        "n.n_permutations, n.n_null_valid, "
                        "(SELECT a.alignment_score FROM structural_alignment_scores a WHERE a.receipt_id = n.receipt_id "
                        " AND a.config_version = n.config_version AND a.sample_id = n.sample_id AND a.frame_id = n.frame_id "
                        " AND a.dip_deg = n.selected_dip_deg) AS a_sel, "
                        "(SELECT a.alignment_score FROM structural_alignment_scores a WHERE a.receipt_id = n.receipt_id "
                        " AND a.config_version = n.config_version AND a.sample_id = n.sample_id AND a.frame_id = n.frame_id "
                        " AND a.dip_deg = 0.0) AS a_zero "
                        "FROM structural_null_summary n WHERE n.receipt_id = ? AND n.config_version = ? "
                        "ORDER BY n.sample_id, n.frame_id", (rid, version))
    lolo = _rows(conn, "SELECT sample_id, frame_id, excluded_line, lolo_dip_deg, within_tolerance FROM structural_lolo_dips "
                       "WHERE receipt_id = ? AND config_version = ? ORDER BY sample_id, frame_id, excluded_line", (rid, version))
    decisions = _rows(conn, "SELECT sample_id, decision, reason FROM structural_decisions WHERE receipt_id = ? AND config_version = ? "
                            "ORDER BY sample_id", (rid, version))
    fits = _rows(conn, "SELECT sample_id, frame_id, model, fit_status, nugget, structured_sill, range_m, stability_status, "
                       "range_ratio_min, range_ratio_max, reason FROM structural_fits WHERE receipt_id = ? AND config_version = ? "
                       "ORDER BY sample_id, frame_id, model", (rid, version))
    between = _rows(conn, "SELECT sample_id, frame_id, lag_from_m, lag_to_m, n_pairs, n_independent_hole_pairs, gamma, supported "
                          "FROM structural_between_line WHERE receipt_id = ? AND config_version = ? "
                          "ORDER BY sample_id, frame_id, lag_from_m", (rid, version))
    digests = _one(conn, "SELECT COUNT(*) AS n, COALESCE(SUM(n_within_hole_pairs), 0) AS within, "
                         "COALESCE(SUM(n_within_hole_candidates_excluded), 0) AS excluded FROM structural_pair_digests "
                         "WHERE receipt_id = ? AND config_version = ?", (rid, version))
    handoff = _one(conn, "SELECT decision_status FROM continuity_handoff_decisions WHERE receipt_id = ? "
                         "ORDER BY handoff_id DESC LIMIT 1", (rid,))
    out = head + [
        f"Configuration {version} (SHA-256 {run['config_sha256'][:12]}), stage run {run['run_id']}: {run['note']}.", "",
        f"Dip grid {s_cfg['frame']['apparent_dip_grid_deg'][0]:g} to {s_cfg['frame']['apparent_dip_grid_deg'][-1]:g} degrees in "
        f"{len(s_cfg['frame']['apparent_dip_grid_deg'])} steps. Pairs: within-line between-hole, |ds| at most "
        f"{s_cfg['pairing']['within_line_between_hole']['max_abs_ds_m']:g} m, lag |dt| binned "
        f"{s_cfg['pairing']['within_line_between_hole']['lag_width_m']:g} m to "
        f"{s_cfg['pairing']['within_line_between_hole']['lag_max_m']:g} m. Null: circular down-hole shift, "
        f"{nulls[0]['n_permutations'] if nulls else 'n/a'} permutations, whole grid rescored. Same-hole pairs in the experiments: "
        f"{digests['within']}; same-hole candidates excluded before the experiments: {digests['excluded']}.", "",
        "| sample | frame | selected dip (deg) | A at selected dip | A at dip 0 | null 95th percentile of max | null p-value | "
        "lines within 10 deg of full dip | decision |",
        "|---|---|---|---|---|---|---|---|---|"]
    dec = {d["sample_id"]: d["decision"] for d in decisions}
    for n in nulls:
        within = sum(1 for r in lolo if r["sample_id"] == n["sample_id"] and r["frame_id"] == n["frame_id"]
                     and r["within_tolerance"] == 1)
        out.append(f"| {n['sample_id']} | {n['frame_id']} | {n['selected_dip_deg']:+g} | {_f(n['a_sel'], 4)} | "
                   f"{_f(n['a_zero'], 4)} | {_f(n['null_p95_max'], 4)} | {_f(n['p_value'], 4)} | {within} of {sum(1 for r in lolo if r['sample_id'] == n['sample_id'] and r['frame_id'] == n['frame_id'])} | "
                   f"{dec.get(n['sample_id'], 'sensitivity only') if n['frame_id'] == 'RELATIVE' else 'sensitivity only'} |")
    out += ["", "Leave-one-line-out dips (degrees):", ""]
    for r in lolo:
        out.append(f"- {r['sample_id']}, {r['frame_id']}, without {r['excluded_line']}: "
                   f"{'none' if r['lolo_dip_deg'] is None else format(r['lolo_dip_deg'], '+g')}"
                   f" ({'within' if r['within_tolerance'] else 'outside'} 10 degrees of the full dip).")
    out += ["", "Fits at the selected dip (sill and nugget in indicator units; range in metres):", "",
            "| sample | frame | model | fit status | nugget | structured sill | range | leave-one-line-out stability | range ratio min to max |",
            "|---|---|---|---|---|---|---|---|---|"]
    for f in fits:
        out.append(f"| {f['sample_id']} | {f['frame_id']} | {f['model']} | {f['fit_status']} | {_f(f['nugget'], 4)} | "
                   f"{_f(f['structured_sill'], 4)} | {_f(f['range_m'], 1)} | {f['stability_status']} | "
                   f"{_f(f['range_ratio_min'], 2)} to {_f(f['range_ratio_max'], 2)} |")
    out += ["", "Between-line along-strike report (REPORT_ONLY, RELATIVE frame, selected dip; no fit):", ""]
    for b in between:
        if b["frame_id"] != "RELATIVE":
            continue
        out.append(f"- {b['sample_id']}, lag {b['lag_from_m']:g} to {b['lag_to_m']:g} m: {b['n_pairs']} pairs, "
                   f"{b['n_independent_hole_pairs']} independent hole pairs, gamma "
                   f"{_f(b['gamma'], 3)}, {'supported' if b['supported'] else 'below 100 pairs'}.")
    out += ["", "Decisions (RELATIVE frame, structural frame): " + "; ".join(
        f"{d['sample_id']} {d['decision']} ({d['reason']})" for d in decisions) + ".", "",
        "The DEM_ABSOLUTE frame is sensitivity only and sets no decision. "
        f"Configuration 6 writes no handoff row; the configuration-2 handoff ({handoff.get('decision_status', 'none')}) stands "
        "as recorded.", "",
        "Claims not permitted by configuration 6 (from its claims_not_permitted list):", ""]
    out += [f"- {c}" for c in s_cfg["claims_not_permitted"]]
    out += ["", f"Decision label for a PROVISIONAL result: {DECISION_PROVISIONAL}. It supplies a structural-frame across-strike "
            "covariance only; no along-strike range is identified.", ""]
    return out


def p_one_minus_p(conn, rid: int) -> float:
    row = _one(conn, "SELECT AVG(indicator) * (1.0 - AVG(indicator)) AS pq FROM analysis_observations "
                     "WHERE receipt_id = ? AND in_binary_target = 1", (rid,))
    return float(row["pq"])

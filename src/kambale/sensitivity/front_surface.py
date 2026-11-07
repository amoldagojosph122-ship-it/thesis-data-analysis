"""Weathering-front surface sensitivity analysis.

The Objective 3 depth-below-weathering-front predictor interpolates hole front heights with inverse-distance weighting
(power 2, 8 neighbours). This module refits the three weathering-front candidates (BASE_LOGISTIC_WF, M2_RF_WF,
M2_HGB_WF) under alternative surfaces, using the same outer folds, inner tuning, calibration and seed as Objective 3,
and compares their held-out Brier scores with the baseline surface. The specification is
config/sensitivity/front_surface_config.yaml; nothing is written to any database.

The per-candidate numeric path reproduces Objective 3 (training._standard_candidate) without database writes. The
baseline surface must reproduce the stored Objective 3 calibrated out-of-fold probabilities to 1e-9, otherwise the run
stops before any output is written.
"""

from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import time
from pathlib import Path

import numpy as np
import yaml

from kambale.config import CONFIG_DIR, FIGURES_DIR, REPORTS_DIR, TABLES_DIR
from kambale.objective_3 import models, weathering_front
from kambale.objective_3.config import (O3_CONFIG_PATH, O3_DB_PATH, StopError, code_commit, load_config,
                                        sha256_bytes, sha256_file, utc_now)
from kambale.objective_3.features import load_observations
from kambale.objective_3.training import _index_of, _membership

SPEC_PATH = CONFIG_DIR / "sensitivity" / "front_surface_config.yaml"
PLANS = ("O3-SPLIT-LODO-1", "O3-SPLIT-HOLE-IL-2")
SETTING = {
    "O3-SPLIT-LODO-1": "Prediction to a new drill line",
    "O3-SPLIT-HOLE-IL-2": "Prediction between holes on the same line",
}
REFITTED = ("BASE_LOGISTIC_WF", "M2_RF_WF", "M2_HGB_WF")
REFERENCES = ("BASE_PREVALENCE", "BASE_LOGISTIC", "M2_RF", "M2_HGB", "M1_IK")
PARENT = {"BASE_LOGISTIC_WF": "BASE_LOGISTIC", "M2_RF_WF": "M2_RF", "M2_HGB_WF": "M2_HGB"}
PARENT_COLUMN = {"BASE_LOGISTIC_WF": "wf_beats_parent_logistic", "M2_RF_WF": "wf_beats_parent_rf",
                 "M2_HGB_WF": "wf_beats_parent_hgb"}
SCHEMES = ("LEAVE_ONE_HOLE_OUT", "LEAVE_ONE_LINE_OUT")
TOLERANCE = 1e-9
QUICK_REPLICATES = 50
ACCEPTANCE_SHOWN = 20


def _log(t0: float, message: str) -> None:
    print(f"[{time.time() - t0:8.1f} s] {message}", flush=True)


# ----------------------------------------------------------------------------------------------------------------------
# Specification
# ----------------------------------------------------------------------------------------------------------------------

def load_spec() -> tuple[dict, str, bool]:
    """Parse the specification file; return (spec, SHA-256 of the bytes, repaired flag, always False)."""
    raw = SPEC_PATH.read_bytes()
    return yaml.safe_load(raw.decode("utf-8")), sha256_bytes(raw), False


def ordered_variants(spec: dict, quick: bool) -> list[dict]:
    """Baseline first, then the alternatives in declared order. Quick mode keeps the baseline only."""
    variants = [dict(v) for v in spec["surface_variants"]]
    base = [v for v in variants if v["role"] == "BASELINE"]
    if len(base) != 1:
        raise StopError("exactly one surface variant must carry role BASELINE")
    alt = [v for v in variants if v["role"] != "BASELINE"]
    ordered = base + alt
    return ordered[:1] if quick else ordered


def connect_readonly(path: Path) -> sqlite3.Connection:
    """Open the Objective 3 database with a read-only URI. Rows are addressable by name."""
    uri = f"{Path(path).resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------------------------------------------------------------------------------------------------
# Surfaces
# ----------------------------------------------------------------------------------------------------------------------

def _constant_mean_feature(obs, train_idx, test_idx, fronts: dict) -> dict:
    """Mean front of the other usable training holes (training rows) or of all usable training holes (test rows),
    minus z_relative_m. Test holes never contribute. Same return structure as weathering_front.feature_for_fold."""
    train_idx = np.asarray(train_idx, dtype=np.int64)
    test_idx = np.asarray(test_idx, dtype=np.int64)
    training_holes = sorted({obs.holes[int(h)] for h in obs.hole[train_idx]})
    usable = [h for h in training_holes if h in fronts]
    if not usable:
        raise StopError("no training hole has a weathering front in this outer fold")
    fz = {h: float(fronts[h][2]) for h in usable}
    Z = obs.X[:, 2]
    train_vals = np.full(train_idx.size, np.nan, dtype=np.float64)
    train_hole_of = np.array([obs.holes[int(h)] for h in obs.hole[train_idx]], dtype=object)
    for h in set(train_hole_of.tolist()):
        others = [g for g in usable if g != h]
        if not others:
            raise StopError(f"no other training front to average for hole {h}")
        mean_others = float(np.mean([fz[g] for g in others]))
        rows = np.where(train_hole_of == h)[0]
        train_vals[rows] = mean_others - Z[train_idx[rows]]
    mean_all = float(np.mean([fz[g] for g in usable]))
    test_vals = mean_all - Z[test_idx]
    if not (np.all(np.isfinite(train_vals)) and np.all(np.isfinite(test_vals))):
        raise StopError("the constant-mean front is undefined for some rows")
    return {"train": train_vals, "test": test_vals, "surface_holes": usable, "training_holes": training_holes}


def variant_feature(obs, train_idx, test_idx, fronts: dict, variant: dict, coincident: float) -> dict:
    """Per-fold depth-below-front values for one surface variant, shaped like weathering_front.feature_for_fold."""
    method = variant["method"]
    if method == "INVERSE_DISTANCE":
        return weathering_front.feature_for_fold(
            obs, train_idx, test_idx, fronts, power=float(variant["power"]), k=int(variant["n_neighbours"]),
            coincident=coincident)
    if method == "CONSTANT_MEAN":
        return _constant_mean_feature(obs, train_idx, test_idx, fronts)
    raise StopError(f"unknown surface method {method}")


def _predict_front(train_holes, fronts: dict, query_xy, variant: dict, coincident: float) -> float:
    vals = np.array([fronts[g][2] for g in train_holes], dtype=np.float64)
    if variant["method"] == "CONSTANT_MEAN":
        return float(np.mean(vals))
    pts = np.array([fronts[g][:2] for g in train_holes], dtype=np.float64)
    return float(weathering_front.idw(pts, vals, np.asarray(query_xy, dtype=np.float64).reshape(1, 2),
                                      float(variant["power"]), int(variant["n_neighbours"]), coincident)[0])


def front_skill_rows(fronts: dict, line_of_hole: dict, variants: list[dict], coincident: float) -> list[dict]:
    """Leave-one-hole-out and leave-one-line-out RMSE of each surface for the observed hole front heights, against the
    training-mean reference built from the same training holes."""
    holes = sorted(fronts)
    rows = []
    for variant in variants:
        for scheme in SCHEMES:
            if scheme == "LEAVE_ONE_HOLE_OUT":
                groups = [([h], [g for g in holes if g != h]) for h in holes]
            else:
                lines = sorted({line_of_hole[h] for h in holes})
                groups = [([h for h in holes if line_of_hole[h] == ln], [h for h in holes if line_of_hole[h] != ln])
                          for ln in lines]
            err_v, err_m = [], []
            for test, train in groups:
                if not train:
                    raise StopError(f"{scheme}: no training hole remains for a held-out group")
                mean_train = float(np.mean([fronts[g][2] for g in train]))
                for h in test:
                    observed = float(fronts[h][2])
                    err_v.append(_predict_front(train, fronts, fronts[h][:2], variant, coincident) - observed)
                    err_m.append(mean_train - observed)
            rmse_v = float(np.sqrt(np.mean(np.square(err_v))))
            rmse_m = float(np.sqrt(np.mean(np.square(err_m))))
            rows.append({"variant": variant["variant_id"], "scheme": scheme, "rmse_variant_m": rmse_v,
                         "rmse_mean_m": rmse_m, "skill_ratio": rmse_v / rmse_m})
    return rows


# ----------------------------------------------------------------------------------------------------------------------
# Candidate refits (Objective 3 numeric path without database writes)
# ----------------------------------------------------------------------------------------------------------------------

def reproduce_candidate(candidate: str, X_train, y_train, hole_train, X_test, config: dict, seed: int) -> np.ndarray:
    """Calibrated held-out probabilities for one candidate, as training._standard_candidate computes them."""
    eps = float(config["calibration"]["clip_epsilon"])
    trials = []
    for params in models.grid(candidate, config):
        cv = models.inner_cv(X_train, y_train, hole_train, candidate, params, config, seed)
        trials.append({"params": params, **cv})
    selection = models.select_trials(trials)
    if selection["status"] != "COMPLETED":
        raise StopError(f"{candidate}: {selection['reason']}")
    chosen = selection["trial"]
    estimator = models.make_estimator(candidate, chosen["params"], config, seed)
    estimator.fit(X_train, y_train)
    raw_test = np.clip(models.predict_positive(estimator, X_test), eps, 1.0 - eps)
    raw_inner = np.clip(chosen["p"], eps, 1.0 - eps)
    if candidate in config["calibration"]["apply_to"]:
        cal = models.platt_fit(y_train, raw_inner, config)
        if cal["status"] == "FITTED":
            return models.platt_apply(raw_test, cal, eps)
    return raw_test.copy()


def plan_vectors(obs, plan_id: str, folds: list[dict], index: dict, variant: dict, fronts: dict, coincident: float,
                 config: dict, seed: int, t0: float) -> dict:
    """Aligned held-out probability vector (length n) for each refitted candidate under one surface variant."""
    n = obs.n
    vec = {c: np.full(n, np.nan, dtype=np.float64) for c in REFITTED}
    fold_data = []
    for fold in folds:
        tr = np.array([index[i] for i in fold["train"]], dtype=np.int64)
        te = np.array([index[i] for i in fold["test"]], dtype=np.int64)
        feat = variant_feature(obs, tr, te, fronts, variant, coincident)
        fold_data.append((tr, te, feat))
    for candidate in REFITTED:
        for tr, te, feat in fold_data:
            X_tr = np.column_stack([obs.X[tr], feat["train"]])
            X_te = np.column_stack([obs.X[te], feat["test"]])
            vec[candidate][te] = reproduce_candidate(candidate, X_tr, obs.y[tr], obs.hole[tr], X_te, config, seed)
        _log(t0, f"{plan_id} | {variant['variant_id']} | {candidate} done ({len(fold_data)} folds)")
    for c in REFITTED:
        if not np.all(np.isfinite(vec[c])):
            raise StopError(f"{plan_id} {variant['variant_id']} {c}: some observations were not predicted")
    return vec


def stored_vectors(conn, obs, plan_id: str, families, index: dict) -> dict:
    """Stored Objective 3 p_calibrated for each family, aligned to the observation order, with label checks."""
    out = {}
    for fam in families:
        rows = conn.execute(
            "SELECT observation_id, true_label, p_calibrated FROM predictions_oof "
            "WHERE split_plan_id = ? AND family_id = ?", (plan_id, fam)).fetchall()
        if len(rows) != obs.n:
            raise StopError(f"{plan_id} {fam}: {len(rows)} stored predictions, expected {obs.n}")
        vec = np.full(obs.n, np.nan, dtype=np.float64)
        for r in rows:
            i = index[int(r["observation_id"])]
            if int(r["true_label"]) != int(obs.y[i]):
                raise StopError(f"{plan_id} {fam}: stored label differs from the observation label")
            vec[i] = float(r["p_calibrated"])
        if not np.all(np.isfinite(vec)):
            raise StopError(f"{plan_id} {fam}: stored predictions do not cover every observation")
        out[fam] = vec
    return out


def acceptance_check(plan_id: str, vec: dict, stored: dict) -> dict:
    """Baseline versus stored Objective 3 probabilities. Raises with the differences when any exceeds the tolerance."""
    maxima, bad_lines = {}, []
    for c in REFITTED:
        d = np.abs(vec[c] - stored[c])
        maxima[c] = float(np.max(d))
        for i in np.where(d > TOLERANCE)[0][:ACCEPTANCE_SHOWN]:
            bad_lines.append(f"  {plan_id} {c} row {int(i)}: reproduced {vec[c][i]!r} stored {stored[c][i]!r} "
                             f"diff {d[i]!r}")
    if bad_lines:
        raise StopError("baseline does not reproduce the stored Objective 3 predictions (tolerance "
                        f"{TOLERANCE:g}); maximum absolute differences {maxima}\n" + "\n".join(bad_lines))
    return maxima


# ----------------------------------------------------------------------------------------------------------------------
# Metrics, bootstrap, selection, conclusion
# ----------------------------------------------------------------------------------------------------------------------

def brier(p, y) -> float:
    return float(np.mean((np.asarray(p, dtype=np.float64) - y) ** 2))


def draw_replicates(hole: np.ndarray, n_replicates: int, rng: np.random.Generator) -> list[np.ndarray]:
    """Hole-cluster bootstrap index sets: each replicate draws the same number of holes with replacement and keeps all
    intervals of every drawn hole."""
    uniq = np.unique(hole)
    idx_by_unit = {u: np.where(hole == u)[0] for u in uniq}
    reps = []
    for _ in range(int(n_replicates)):
        sample = rng.choice(len(uniq), size=len(uniq), replace=True)
        reps.append(np.concatenate([idx_by_unit[uniq[k]] for k in sample]))
    return reps


def paired_interval(y, p_variant, p_baseline, reps: list[np.ndarray], confidence: float = 0.95) -> dict:
    """Variant minus baseline Brier difference on the full sample, with the percentile interval over the replicate
    index sets. The same replicate sets are used for every pair."""
    sq_v = (np.asarray(p_variant, dtype=np.float64) - y) ** 2
    sq_b = (np.asarray(p_baseline, dtype=np.float64) - y) ** 2
    point = float(np.mean(sq_v) - np.mean(sq_b))
    diffs = np.array([np.mean(sq_v[idx]) - np.mean(sq_b[idx]) for idx in reps], dtype=np.float64)
    lo_q = (1.0 - confidence) / 2.0 * 100.0
    lo, hi = np.percentile(diffs, [lo_q, 100.0 - lo_q])
    status = "RESOLVED" if (lo > 0 or hi < 0) else "UNRESOLVED"
    return {"diff": point, "ci_low": float(lo), "ci_high": float(hi), "status": status}


def conclusion_for(n_resolved: int, n_selection_changes: int) -> str:
    """ROBUST: no resolved difference and the lowest-Brier model is the Objective 4 selection under every variant.
    SELECTION_SENSITIVE: no resolved difference, but the lowest-Brier model changes under at least one variant.
    PERFORMANCE_SENSITIVE: at least one resolved paired difference."""
    if n_resolved > 0:
        return "PERFORMANCE_SENSITIVE"
    if n_selection_changes > 0:
        return "SELECTION_SENSITIVE"
    return "ROBUST"


def lowest_model(brier_by_model: dict) -> tuple[str, float]:
    name = min(brier_by_model, key=lambda m: (brier_by_model[m], m))
    return name, brier_by_model[name]


# ----------------------------------------------------------------------------------------------------------------------
# Output writers
# ----------------------------------------------------------------------------------------------------------------------

TABLE_COLUMNS = {
    "S01_front_skill": ["variant", "scheme", "rmse_variant_m", "rmse_mean_m", "skill_ratio"],
    "S02_brier_by_variant": ["plan", "prediction_setting", "variant", "model", "brier"],
    "S03_paired_vs_baseline": ["plan", "setting", "candidate", "variant", "brier_variant", "brier_baseline", "diff",
                               "ci_low", "ci_high", "status"],
    "S04_selection_by_variant": ["plan", "setting", "variant", "lowest_brier_model", "lowest_brier", "o4_selected",
                                 "same_as_o4", "wf_beats_parent_logistic", "wf_beats_parent_rf", "wf_beats_parent_hgb"],
    "S05_conclusion": ["plan", "setting", "conclusion", "n_resolved", "n_selection_changes"],
}


def _fmt_md(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.5f}"
    return str(value).replace("|", "/")


def md_table(columns: list[str], rows: list[dict]) -> str:
    head = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(_fmt_md(r[c]) for c in columns) + " |" for r in rows]
    return "\n".join([head, sep] + body) + "\n"


def write_table(directory: Path, name: str, rows: list[dict]) -> None:
    columns = TABLE_COLUMNS[name]
    with open(directory / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: ("" if r[c] is None else r[c]) for c in columns})
    (directory / f"{name}.md").write_text(md_table(columns, rows), encoding="utf-8")


def write_figures(figure_dir: Path, variant_ids: list[str], brier_by: dict, skill_rows: list[dict], plans) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10})
    fig, axes = plt.subplots(1, len(plans), figsize=(6.2 * len(plans), 5.6), sharey=True)
    axes = np.atleast_1d(axes)
    x = np.arange(len(variant_ids))
    handles, labels = [], []
    for ax, plan in zip(axes, plans):
        for c, colour in zip(REFITTED, ("#1f77b4", "#d62728", "#2ca02c")):
            line, = ax.plot(x, [brier_by[plan]["variants"][v][c] for v in variant_ids], marker="o", color=colour,
                            label=f"{c} (refitted)")
            if ax is axes[0]:
                handles.append(line)
                labels.append(f"{c} (refitted)")
        for ref, style, colour in (("BASE_LOGISTIC", "--", "0.35"), ("M2_RF", "--", "0.55"),
                                   ("M2_HGB", "--", "0.20"), ("BASE_PREVALENCE", ":", "0.45")):
            value = brier_by[plan]["references"][ref]
            line = ax.axhline(value, linestyle=style, color=colour, linewidth=1.2)
            if ax is axes[0]:
                handles.append(line)
                labels.append(f"{ref} (reference)")
        ax.set_title(SETTING[plan], fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels(variant_ids, rotation=35, ha="right")
        ax.set_xlabel("Front surface variant")
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("Held-out Brier score (lower is better)")
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(figure_dir / f"SF01_front_surface_sensitivity.{ext}", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    width = 0.38
    xs = np.arange(len(variant_ids))
    for k, scheme in enumerate(SCHEMES):
        vals = [next(r["skill_ratio"] for r in skill_rows if r["variant"] == v and r["scheme"] == scheme)
                for v in variant_ids]
        ax.bar(xs + (k - 0.5) * width, vals, width, label=scheme.replace("_", " ").title().replace("Out", "out"))
    ax.axhline(1.0, color="0.2", linestyle="-", linewidth=1.0, label="1.0: no better than training mean")
    ax.axhline(0.8, color="0.2", linestyle="--", linewidth=1.0, label="0.8: 20 per cent lower error")
    ax.set_xticks(xs)
    ax.set_xticklabels(variant_ids, rotation=35, ha="right")
    ax.set_xlabel("Front surface variant")
    ax.set_ylabel("Skill ratio: RMSE(variant) / RMSE(training mean)")
    ax.set_title("Front-height interpolation skill by surface variant", fontsize=11)
    ax.set_ylim(0.0, 1.85)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper left", ncol=2, frameon=False, fontsize=9)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(figure_dir / f"SF02_front_skill.{ext}", dpi=200)
    plt.close(fig)


def _interpretation(skill_rows, paired_rows, selection_rows, conclusions, baseline_id) -> list[str]:
    lines = []
    base_skill = [r for r in skill_rows if r["variant"] == baseline_id]
    for r in base_skill:
        lines.append(f"- Baseline surface, {r['scheme'].replace('_', ' ').lower()}: RMSE of the predicted front height is "
                     f"{r['rmse_variant_m']:.2f} m against {r['rmse_mean_m']:.2f} m for the training mean "
                     f"(skill ratio {r['skill_ratio']:.2f}). A ratio below 1 means the surface predicts held-out front "
                     "heights better than the training mean.")
    for c in conclusions:
        plan = c["plan"]
        rows = [r for r in paired_rows if r["plan"] == plan]
        resolved = [r for r in rows if r["status"] == "RESOLVED"]
        sel = [r for r in selection_rows if r["plan"] == plan]
        lowest_base = next(r["lowest_brier_model"] for r in sel if r["variant"] == baseline_id)
        o4_model = sel[0]["o4_selected"]
        changed = sorted({r["variant"] for r in sel if r["lowest_brier_model"] != lowest_base and r["variant"] != baseline_id})
        lines.append(f"- {c['setting']} ({plan}): {len(resolved)} of {len(rows)} paired differences from the baseline "
                     f"surface are resolved (95 per cent hole-cluster interval excludes zero). The lowest-Brier model "
                     f"under the baseline surface is {lowest_base}, the Objective 4 selection is "
                     f"{o4_model}. The lowest-Brier model changes under "
                     f"{len(changed)} alternative surface(s){': ' + ', '.join(changed) if changed else ''}.")
        if rows:
            big = max(rows, key=lambda r: abs(r["diff"]))
            lines.append(f"  The largest paired difference is {big['candidate']} under {big['variant']}: "
                         f"{big['diff']:+.5f} in Brier score (interval {big['ci_low']:+.5f} to {big['ci_high']:+.5f}).")
        lines.append(f"  Conclusion for this setting: {c['conclusion']}.")
    lines.append("- Lowest-Brier model changes are reported as they occur. The Objective 4 comparisons among the leading "
                 "models were themselves unresolved, so a change of lowest-Brier model is not read as a better model.")
    return lines


def _md_report(path: Path, meta: dict, acceptance: dict, tables: dict, figures_rel: dict, conclusions: list[dict],
               interpretation: list[str]) -> None:
    out = []
    out.append("# Weathering-front surface sensitivity analysis\n")
    out.append("This analysis asks whether the Objective 3 weathering-front predictor depends on how the front height is "
               "interpolated between drill holes. The baseline surface is the one used in Objective 3 (inverse-distance "
               "weighting, power 2, 8 nearest holes). Each alternative surface refits the three weathering-front "
               "candidates with the same outer folds, inner tuning, calibration and random seed. The analysis changes "
               "no Objective 3, 4 or 5 result.\n")
    out.append("## Run record\n")
    out.append(md_table(["item", "value"], [{"item": k, "value": v} for k, v in meta.items()]))
    out.append("\n## Baseline reproduction\n")
    out.append("The baseline surface was refitted and its calibrated held-out probabilities were compared with the stored "
               f"Objective 3 values, aligned by observation. The tolerance is {TOLERANCE:g}.\n")
    acc_rows = [{"plan": p, "candidate": c, "max_abs_diff": d, "result": "PASS"}
                for p, cands in acceptance.items() for c, d in cands.items()]
    out.append(md_table(["plan", "candidate", "max_abs_diff", "result"], acc_rows))
    out.append("\n## Tables\n")
    titles = {
        "S01_front_skill": "S01. Front-height interpolation skill by surface variant",
        "S02_brier_by_variant": "S02. Held-out Brier score by surface variant and model",
        "S03_paired_vs_baseline": "S03. Paired Brier difference from the baseline surface (variant minus baseline)",
        "S04_selection_by_variant": "S04. Lowest-Brier model by surface variant",
        "S05_conclusion": "S05. Conclusion by prediction setting",
    }
    for name in TABLE_COLUMNS:
        out.append(f"### {titles[name]}\n")
        out.append(md_table(TABLE_COLUMNS[name], tables[name]))
        out.append("")
    out.append("## Figures\n")
    out.append(f"![Held-out Brier by surface variant]({figures_rel['SF01']})\n")
    out.append(f"Figure SF01 (also as PDF: {figures_rel['SF01_pdf']}). Each panel is one prediction setting; each point is "
               "one refitted candidate under one surface; dashed lines are the reference models, dotted line is the "
               "prevalence baseline.\n")
    out.append(f"![Front-height interpolation skill]({figures_rel['SF02']})\n")
    out.append(f"Figure SF02 (also as PDF: {figures_rel['SF02_pdf']}). Skill ratio below 1 is better than the training "
               "mean; the 0.8 line marks a 20 per cent reduction in error.\n")
    out.append("## Conclusion by setting\n")
    for c in conclusions:
        out.append(f"- **{c['setting']}** ({c['plan']}): {c['conclusion']}. {c['n_resolved']} paired difference(s) "
                   f"resolved; the lowest-Brier model changed under {c['n_selection_changes']} surface variant(s) "
                   "compared with the Objective 4 selection.")
    out.append("\n## Interpretation\n")
    out.extend(interpretation)
    out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


# ----------------------------------------------------------------------------------------------------------------------
# Main run
# ----------------------------------------------------------------------------------------------------------------------

def run(quick: bool = False) -> dict:
    t0 = time.time()
    run_utc = utc_now()
    spec, spec_sha, repaired = load_spec()
    o3_config, o3_config_sha = load_config(O3_CONFIG_PATH)
    o3_db_sha_before = sha256_file(O3_DB_PATH)
    variants = ordered_variants(spec, quick)
    plans = [PLANS[0]] if quick else list(PLANS)
    options = spec.get("surface_variants_options") or {}
    if "coincident_distance_m" not in options:
        raise StopError("coincident_distance_m is missing from the sensitivity specification")
    coincident = float(options["coincident_distance_m"])
    bootstrap = spec["evaluation"]["bootstrap"]
    n_rep = QUICK_REPLICATES if quick else int(bootstrap["n_replicates"])
    boot_seed = int(bootstrap["seed"])
    confidence = float(bootstrap["confidence"])
    derived = o3_config["features"]["derived"]["depth_below_weathering_front_m"]
    front_codes = list(derived["front_codes"])
    seed_fit = int(o3_config["seeds"][0])
    o4_selected = spec["objective_4_selected"]
    _log(t0, f"specification {spec['config_version']} sha256 {spec_sha[:16]}... "
             f"(repaired reading: {repaired}); variants {[v['variant_id'] for v in variants]}; plans {plans}")

    conn = connect_readonly(O3_DB_PATH)
    try:
        row = conn.execute("SELECT MAX(receipt_id) AS r FROM source_receipts").fetchone()
        receipt_id = int(row["r"])
        obs = load_observations(conn, receipt_id, o3_config)
        fronts = weathering_front.hole_fronts(conn, receipt_id, front_codes)
        line_of_hole = {r["hole_id"]: r["line_code"] for r in conn.execute(
            "SELECT DISTINCT hole_id, line_code FROM analysis_observations WHERE receipt_id = ?", (receipt_id,))}
        _log(t0, f"receipt {receipt_id}: {obs.n} binary observations, {len(obs.holes)} holes, {len(fronts)} holes "
                 "with a weathering front")

        skill_rows = front_skill_rows(fronts, line_of_hole, variants, coincident)
        _log(t0, "front skill computed")

        index = _index_of(obs)
        vectors: dict = {}      # plan -> variant -> candidate -> vector
        stored: dict = {}       # plan -> family -> vector
        acceptance: dict = {}   # plan -> candidate -> max abs diff
        for plan_id in plans:
            folds = _membership(conn, plan_id)
            stored[plan_id] = stored_vectors(conn, obs, plan_id, list(REFITTED) + list(REFERENCES), index)
            vectors[plan_id] = {}
            for k, variant in enumerate(variants):
                vec = plan_vectors(obs, plan_id, folds, index, variant, fronts, coincident, o3_config, seed_fit, t0)
                vectors[plan_id][variant["variant_id"]] = vec
                if k == 0:
                    acceptance[plan_id] = acceptance_check(plan_id, vec, stored[plan_id])
                    _log(t0, f"{plan_id}: baseline reproduces stored predictions; max abs diff "
                             + ", ".join(f"{c} {d:.3g}" for c, d in acceptance[plan_id].items()))

        # Metrics
        brier_by: dict = {}
        for plan_id in plans:
            y = obs.y.astype(np.float64)
            brier_by[plan_id] = {
                "variants": {v: {c: brier(vectors[plan_id][v][c], y) for c in REFITTED}
                             for v in vectors[plan_id]},
                "references": {r: brier(stored[plan_id][r], y) for r in REFERENCES},
            }

        paired_rows, selection_rows, conclusions = [], [], []
        baseline_id = variants[0]["variant_id"]
        for plan_id in plans:
            y = obs.y.astype(np.float64)
            rng = np.random.default_rng(boot_seed)
            reps = draw_replicates(obs.hole, n_rep, rng)
            _log(t0, f"{plan_id}: {len(reps)} hole-cluster replicate index sets drawn")
            base_vec = vectors[plan_id][baseline_id]
            for variant in variants[1:]:
                for c in REFITTED:
                    res = paired_interval(y, vectors[plan_id][variant["variant_id"]][c], base_vec[c], reps, confidence)
                    paired_rows.append({
                        "plan": plan_id, "setting": SETTING[plan_id], "candidate": c,
                        "variant": variant["variant_id"],
                        "brier_variant": brier_by[plan_id]["variants"][variant["variant_id"]][c],
                        "brier_baseline": brier_by[plan_id]["variants"][baseline_id][c],
                        "diff": res["diff"], "ci_low": res["ci_low"], "ci_high": res["ci_high"],
                        "status": res["status"]})
            n_resolved = sum(1 for r in paired_rows if r["plan"] == plan_id and r["status"] == "RESOLVED")
            n_changes = 0
            for variant in variants:
                v = variant["variant_id"]
                models_b = {c: brier_by[plan_id]["variants"][v][c] for c in REFITTED}
                models_b.update(brier_by[plan_id]["references"])
                lowest, lowest_val = lowest_model(models_b)
                wf = {PARENT[c]: brier_by[plan_id]["variants"][v][c] < brier_by[plan_id]["references"][PARENT[c]]
                      for c in REFITTED}
                if lowest != o4_selected[plan_id]:
                    n_changes += 1
                selection_rows.append({
                    "plan": plan_id, "setting": SETTING[plan_id], "variant": v, "lowest_brier_model": lowest,
                    "lowest_brier": lowest_val, "o4_selected": o4_selected[plan_id],
                    "same_as_o4": lowest == o4_selected[plan_id],
                    "wf_beats_parent_logistic": wf["BASE_LOGISTIC"], "wf_beats_parent_rf": wf["M2_RF"],
                    "wf_beats_parent_hgb": wf["M2_HGB"]})
            conclusions.append({"plan": plan_id, "setting": SETTING[plan_id],
                                "conclusion": conclusion_for(n_resolved, n_changes),
                                "n_resolved": n_resolved, "n_selection_changes": n_changes,
                                "n_pairs": len(variants[1:]) * len(REFITTED)})
            _log(t0, f"{plan_id}: conclusion {conclusions[-1]['conclusion']}")

        skill_for_json = skill_rows
        brier_rows = []
        for plan_id in plans:
            for v in [x["variant_id"] for x in variants]:
                for c in REFITTED:
                    brier_rows.append({"plan": plan_id, "prediction_setting": SETTING[plan_id], "variant": v,
                                       "model": c, "brier": brier_by[plan_id]["variants"][v][c]})
            for r in REFERENCES:
                brier_rows.append({"plan": plan_id, "prediction_setting": SETTING[plan_id],
                                   "variant": "not applicable", "model": r,
                                   "brier": brier_by[plan_id]["references"][r]})

        o3_db_sha_after = sha256_file(O3_DB_PATH)
        if o3_db_sha_after != o3_db_sha_before:
            raise StopError("the Objective 3 database file changed during the run")
        duration = time.time() - t0

        if quick:
            base_dir = Path(tempfile.gettempdir()) / "kambale_sensitivity_quick"
            tables_dir = base_dir / "tables"
            figures_dir = base_dir / "figures"
            reports_dir = base_dir / "reports"
        else:
            tables_dir = TABLES_DIR / "sensitivity" / "front_surface"
            figures_dir = FIGURES_DIR / "sensitivity"
            reports_dir = REPORTS_DIR / "sensitivity"
        for d in (tables_dir, figures_dir, reports_dir):
            d.mkdir(parents=True, exist_ok=True)

        tables = {"S01_front_skill": skill_for_json, "S02_brier_by_variant": brier_rows,
                  "S03_paired_vs_baseline": paired_rows, "S04_selection_by_variant": selection_rows,
                  "S05_conclusion": conclusions}
        for name, rows in tables.items():
            write_table(tables_dir, name, rows)
        variant_ids = [v["variant_id"] for v in variants]
        write_figures(figures_dir, variant_ids, brier_by, skill_rows, plans)

        interpretation = _interpretation(skill_rows, paired_rows, selection_rows, conclusions, baseline_id)
        meta = {
            "sensitivity configuration version": spec["config_version"],
            "sensitivity configuration SHA-256": spec_sha,
            "sensitivity configuration reading": ("two keys at list indentation read as written; file not edited"
                                                  if repaired else "as written"),
            "Objective 3 database SHA-256 (before and after the run)": o3_db_sha_before,
            "Objective 3 configuration version": o3_config["config_version"],
            "Objective 3 configuration SHA-256": o3_config_sha,
            "code commit": code_commit() or "unavailable",
            "receipt used": receipt_id,
            "run started (UTC)": run_utc,
            "run duration (seconds)": round(duration, 1),
            "mode": "quick check (one plan, baseline only, 50 replicates; outputs in temp folder)" if quick else "full run",
            "bootstrap": f"hole-cluster, {n_rep} replicates, seed {boot_seed}, {confidence:.0%} interval",
        }
        figures_rel = {"SF01": "../../figures/sensitivity/SF01_front_surface_sensitivity.png",
                       "SF01_pdf": "../../figures/sensitivity/SF01_front_surface_sensitivity.pdf",
                       "SF02": "../../figures/sensitivity/SF02_front_skill.png",
                       "SF02_pdf": "../../figures/sensitivity/SF02_front_skill.pdf"}
        _md_report(reports_dir / "FRONT_SURFACE_SENSITIVITY.md", meta, acceptance, tables, figures_rel, conclusions,
                   interpretation)

        summary = {
            "config_version": spec["config_version"], "config_sha256": spec_sha,
            "o3_db_sha256": o3_db_sha_before, "o3_config_version": o3_config["config_version"],
            "code_commit": code_commit(), "run_utc": run_utc, "duration_seconds": round(duration, 1),
            "quick": bool(quick), "bootstrap_replicates": n_rep, "bootstrap_seed": boot_seed,
            "acceptance_max_abs_diff": acceptance, "acceptance_tolerance": TOLERANCE,
            "front_skill": [{k: r[k] for k in ("variant", "scheme", "rmse_variant_m", "rmse_mean_m", "skill_ratio")}
                            for r in skill_rows],
            "brier": brier_rows, "paired_vs_baseline": paired_rows, "selection": selection_rows,
            "conclusions": [{k: c[k] for k in ("plan", "setting", "conclusion", "n_resolved", "n_selection_changes")}
                            for c in conclusions],
        }
        (reports_dir / "front_surface_results.json").write_text(json.dumps(summary, indent=2, default=float) + "\n",
                                                               encoding="utf-8")
        _log(t0, f"outputs written to {tables_dir.parent}")
        return summary
    finally:
        conn.close()

"""Safe predictor matrix, observation snapshot and the frozen spatial split plans for Objective 3.

The feature registry in the database is the authority: only features with `available_at_prediction = 1` and
`leakage_designation = 'SAFE'` may enter a model. The columns of the TREND predictor set are read from the observation
table; the derived weathering-front predictor is computed per outer fold (weathering_front.py) and is checked in the
registry here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from kambale.objective_3.config import StopError, load_config

TREND_COLUMNS = ("easting_m", "northing_m", "z_relative_m")


@dataclass
class Observations:
    ids: np.ndarray            # upstream interval identifiers, ascending
    X: np.ndarray             # (n, 3) TREND predictors: easting_m, northing_m, z_relative_m
    y: np.ndarray             # (n,) binary target
    hole: np.ndarray          # (n,) integer hole index
    line: np.ndarray          # (n,) integer line index
    holes: list
    lines: list
    feature_names: list

    @property
    def n(self) -> int:
        return int(self.y.size)

    @property
    def p(self) -> float:
        return float(self.y.mean())


def predictor_sets(config: dict) -> dict:
    return {name: list(cols) for name, cols in config["features"]["predictor_sets"].items()}


def check_predictor_registry(conn, config: dict) -> None:
    """Every column of every predictor set must be SAFE and available in the registry, or the run stops."""
    rows = {r["name"]: dict(r) for r in conn.execute(
        "SELECT name, available_at_prediction, leakage_designation, source_table FROM feature_registry")}
    needed = set()
    for cols in predictor_sets(config).values():
        needed.update(cols)
    for name in sorted(needed):
        row = rows.get(name)
        if row is None:
            raise StopError(f"predictor {name} is not in the feature registry")
        if row["available_at_prediction"] != 1 or row["leakage_designation"] != "SAFE":
            raise StopError(f"predictor {name} is not SAFE and available at prediction ({row['leakage_designation']})")


def safe_feature_names(conn, config: dict) -> list[str]:
    """Columns of the TREND predictor set (the base set every candidate contains)."""
    check_predictor_registry(conn, config)
    base = predictor_sets(config)["TREND"]
    if tuple(base) != TREND_COLUMNS:
        raise StopError("the TREND predictor set must be easting_m, northing_m, z_relative_m")
    return base


def load_observations(conn, receipt_id: int, config: dict) -> Observations:
    """Binary observations of one receipt, in upstream interval order, with the TREND columns."""
    names = safe_feature_names(conn, config)
    rows = conn.execute(
        "SELECT upstream_interval_id, hole_id, line_code, " + ", ".join(names) +
        ", indicator FROM analysis_observations WHERE receipt_id = ? AND in_binary_target = 1 "
        "ORDER BY upstream_interval_id", (receipt_id,)).fetchall()
    if not rows:
        raise StopError("no binary observations for this receipt")
    holes = sorted({r["hole_id"] for r in rows})
    lines = sorted({r["line_code"] for r in rows})
    hole_index = {h: i for i, h in enumerate(holes)}
    line_index = {ln: i for i, ln in enumerate(lines)}
    return Observations(
        ids=np.array([r["upstream_interval_id"] for r in rows], dtype=np.int64),
        X=np.array([[r[name] for name in names] for r in rows], dtype=np.float64),
        y=np.array([r["indicator"] for r in rows], dtype=np.int64),
        hole=np.array([hole_index[r["hole_id"]] for r in rows], dtype=np.int64),
        line=np.array([line_index[r["line_code"]] for r in rows], dtype=np.int64),
        holes=holes, lines=lines, feature_names=names,
    )


def hole_collars(obs: Observations) -> dict:
    """Collar proxy per hole index: the shallowest interval's (easting, northing), i.e. the maximum z_relative_m.

    A straight hole's shallowest interval lies within one metre of its collar, so it stands in for the collar.
    """
    out = {}
    for h in range(len(obs.holes)):
        idx = np.where(obs.hole == h)[0]
        best = idx[int(np.argmax(obs.X[idx, 2]))]
        out[h] = (float(obs.X[best, 0]), float(obs.X[best, 1]))
    return out


def interleaved_assignment(obs: Observations, n_folds: int) -> dict:
    """Hole index -> fold (1-based). Within each line, holes are ordered by collar easting, ties by hole identifier; the
    k-th hole (k from 0) goes to fold (k mod n_folds) + 1."""
    collars = hole_collars(obs)
    line_of = {}
    for h in range(len(obs.holes)):
        line_of[h] = int(obs.line[np.where(obs.hole == h)[0][0]])
    assignment = {}
    for line in sorted(set(line_of.values())):
        holes = [h for h in range(len(obs.holes)) if line_of[h] == line]
        order = sorted(holes, key=lambda h: (collars[h][0], obs.holes[h]))
        for k, h in enumerate(order):
            assignment[h] = (k % n_folds) + 1
    return assignment


def fold_membership(obs: Observations, plan: dict) -> list[dict]:
    """Fold assignment rows for one split plan.

    LEAVE_ONE_DRILL_LINE_OUT: one fold per line; the held-out line is the test fold.
    GROUP_K_FOLD_BY_HOLE: whole holes are assigned to folds by descending interval count, ties by sorted hole id.
    INTERLEAVED_HOLES_WITHIN_LINE: whole holes are assigned within each line in collar-easting order (interleaved_assignment).
    """
    method = plan["method"]
    if method == "LEAVE_ONE_DRILL_LINE_OUT":
        folds = []
        for f, line_index in enumerate(sorted(set(int(v) for v in obs.line)), start=1):
            test = obs.line == line_index
            folds.append({"fold_id": f, "test": test, "test_line": obs.lines[line_index]})
        return folds
    if method == "GROUP_K_FOLD_BY_HOLE":
        n_folds = int(plan["n_folds"])
        per_hole = np.bincount(obs.hole, minlength=len(obs.holes))
        order = sorted(range(len(obs.holes)), key=lambda h: (-per_hole[h], obs.holes[h]))
        fold_of_hole: dict[int, int] = {}
        load = [0] * n_folds
        for h in order:
            f = min(range(n_folds), key=lambda k: (load[k], k))
            fold_of_hole[h] = f + 1
            load[f] += int(per_hole[h])
        folds = []
        for f in range(1, n_folds + 1):
            test = np.array([fold_of_hole[int(h)] == f for h in obs.hole], dtype=bool)
            folds.append({"fold_id": f, "test": test, "test_line": None})
        return folds
    if method == "INTERLEAVED_HOLES_WITHIN_LINE":
        n_folds = int(plan["n_folds"])
        assignment = interleaved_assignment(obs, n_folds)
        folds = []
        for f in range(1, n_folds + 1):
            test = np.array([assignment[int(h)] == f for h in obs.hole], dtype=bool)
            folds.append({"fold_id": f, "test": test, "test_line": None})
        return folds
    raise StopError(f"unknown split method {method}")


def _plan_hash(rows: list[tuple]) -> str:
    from kambale.objective_3.config import sha256_text
    return sha256_text("\n".join(f"{plan}:{fold}:{oid}:{role}" for plan, fold, oid, role in rows))


def build_split_plan(conn, receipt_id: int, obs: Observations, plan: dict, primary: bool, created: str) -> dict:
    """Write one split plan, every membership row and the fold audit. Refuses to overwrite a frozen plan.

    All membership and audit rows are written in one transaction. Autocommit per row is prohibitively slow on Windows.
    """
    split_plan_id = plan["split_plan_id"]
    existing = conn.execute("SELECT plan_sha256 FROM spatial_split_plans WHERE split_plan_id = ?",
                            (split_plan_id,)).fetchone()
    folds = fold_membership(obs, plan)
    rows = []
    for fold in folds:
        for i in range(obs.n):
            rows.append((split_plan_id, fold["fold_id"], int(obs.ids[i]), "TEST" if fold["test"][i] else "TRAIN"))
    plan_sha = _plan_hash(rows)
    if existing and existing["plan_sha256"] != plan_sha:
        raise StopError(f"split plan {split_plan_id} is frozen with a different hash")

    collar = hole_collars(obs)
    by_id = {int(v): i for i, v in enumerate(obs.ids)}
    membership_rows = []
    for p, f, oid, role in rows:
        i = by_id[oid]
        membership_rows.append((p, f, oid, obs.holes[int(obs.hole[i])], obs.lines[int(obs.line[i])], role))

    audits = []
    for fold in folds:
        f = fold["fold_id"]
        test, train = fold["test"], ~fold["test"]
        test_lines = sorted({obs.lines[int(v)] for v in obs.line[test]})
        train_lines = sorted({obs.lines[int(v)] for v in obs.line[train]})
        test_holes = sorted({obs.holes[int(v)] for v in obs.hole[test]})
        train_holes = sorted({obs.holes[int(v)] for v in obs.hole[train]})
        disjoint = not (set(test_holes) & set(train_holes))
        both_train = len(set(obs.y[train].tolist())) == 2
        both_test = len(set(obs.y[test].tolist())) == 2
        min_dist = None
        if test_holes and train_holes:
            xt = np.array([collar[obs.holes.index(h)] for h in test_holes])
            xr = np.array([collar[obs.holes.index(h)] for h in train_holes])
            d2 = ((xt[:, None, 0] - xr[None, :, 0]) ** 2 + (xt[:, None, 1] - xr[None, :, 1]) ** 2)
            min_dist = float(np.sqrt(d2.min()))
        status = "PASS" if disjoint and both_train and both_test else "WARN"
        if not disjoint:
            status = "STOP"
        reason = (f"{len(test_lines)} test line(s); {len(test_holes)} test holes; "
                  f"minimum collar distance between test and training holes {min_dist:.1f} m" if min_dist is not None
                  else "no test or no training rows")
        if not both_test:
            reason += "; WARN: a test fold does not carry both classes"
        audits.append((split_plan_id, f, int(train.sum()), int(test.sum()), int(obs.y[train].sum()),
                       int(obs.y[test].sum()), len(train_holes), len(test_holes), len(train_lines), len(test_lines),
                       int(disjoint), int(both_train), int(both_test), min_dist, status, reason))

    if not existing:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "INSERT INTO spatial_split_plans (split_plan_id, receipt_id, method, n_folds, primary_plan, seed, "
                "frozen_utc, plan_sha256, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (split_plan_id, receipt_id, plan["method"], len(folds), 1 if primary else 0, int(plan["seed"]),
                 created, plan_sha, plan.get("note", plan.get("claim", ""))))
            conn.executemany(
                "INSERT INTO split_membership (split_plan_id, fold_id, observation_id, hole_id, line_code, role) "
                "VALUES (?, ?, ?, ?, ?, ?)", membership_rows)
            conn.executemany(
                "INSERT OR IGNORE INTO split_audit (split_plan_id, fold_id, n_train, n_test, train_positive, "
                "test_positive, train_holes, test_holes, train_lines, test_lines, disjoint, both_classes_train, "
                "both_classes_test, min_train_test_collar_distance_m, status, reason) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", audits)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return {"split_plan_id": split_plan_id, "plan_sha256": plan_sha, "n_folds": len(folds),
            "primary_plan": int(bool(primary)),
            "audits": [{"fold_id": a[1], "n_train": a[2], "n_test": a[3], "test_positive": a[5], "status": a[14]}
                       for a in audits]}


def run(receipt_id: int | None = None, config_path=None, o3_path=None) -> dict:
    from kambale.objective_3.config import O3_DB_PATH, O3_CONFIG_PATH, code_commit, utc_now
    from kambale.objective_3.db import connect_o3
    config, config_sha = load_config(config_path or O3_CONFIG_PATH)
    conn = connect_o3(o3_path or O3_DB_PATH)
    try:
        if receipt_id is None:
            row = conn.execute("SELECT receipt_id FROM source_receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
            if row is None:
                raise StopError("no receipt: run the import first")
            receipt_id = row["receipt_id"]
        obs = load_observations(conn, receipt_id, config)
        tiers = config["splits"]["tiers"]
        primary_ids = [t["split_plan_id"] for t in tiers if int(t["primary_plan"]) == 1]
        if len(primary_ids) != 1:
            raise StopError("the configuration must declare exactly one primary split plan")
        run_id = conn.execute(
            "INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, started_utc, status, "
            "code_commit, note) VALUES ('SPLITS', ?, ?, ?, ?, 'RUNNING', ?, 'frozen spatial fold plans')",
            (config["config_version"], config_sha, receipt_id, utc_now(), code_commit())).lastrowid
        created = utc_now()
        plans = [build_split_plan(conn, receipt_id, obs, tier, int(tier["primary_plan"]) == 1, created)
                 for tier in tiers]
        conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ?, split_plan_id = ? WHERE run_id = ?",
                     (utc_now(), primary_ids[0], run_id))
        primary = next(p for p in plans if p["split_plan_id"] == primary_ids[0])
        return {"run_id": run_id, "receipt_id": receipt_id, "primary": primary,
                "plans": plans}
    finally:
        conn.close()

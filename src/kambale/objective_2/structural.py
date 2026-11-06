"""Configuration 6: indicator variography in a structural (dipping-plane) frame.

The predeclared file config/objective_2/structural_config_O2-CFG-2026.11.06-6.yaml defines the run. Within each drill line
(an east-west section) between-hole pairs are formed on a plane of apparent dip d: s = z cos d + x sin d (position across
the layering) and t = x cos d - z sin d (position along the plane). Pairs must lie within |ds| <= 3 m and are binned by |dt|.
The alignment score A(d) = 1 - mean(gamma at the first two supported bins) / p(1 - p) selects the dip. The selection is
tested against a circular down-hole shift null that rescores the whole dip grid in every permutation.

The stage writes its own rows under a SENSITIVITY stage run and never writes a continuity handoff row. Pair sets depend
only on geometry, so they are enumerated once per dip and frame; under permutation only the indicator vector changes.
"""

from __future__ import annotations

import hashlib
import math
import re

import numpy as np
import yaml

from kambale.config import CONFIG_DIR
from kambale.objective_2 import fitting
from kambale.objective_2.config import (O2_CONFIG_PATH, O2_DB_PATH, UPSTREAM_DB_PATH, StopError, code_commit, load_config,
                                        sha256_bytes, utc_now)
from kambale.objective_2.db import connect_o2, connect_upstream_readonly
from kambale.objective_2.pairs import bin_edges
from kambale.objective_2.weathering import WEATHERING_CONFIG_PATH, hole_bootstrap, weighted_gamma

STRUCTURAL_CONFIG_PATH = CONFIG_DIR / "objective_2" / "structural_config_O2-CFG-2026.11.06-6.yaml"
FIT_MODELS = ("spherical", "exponential")
FRESH_CODES = ("mw", "sw")                  # config: sample rule "weathering code is mw or sw"
SAMPLE_ALL, SAMPLE_FRESH = "ALL_BINARY", "FRESH"
FRAME_RELATIVE, FRAME_DEM = "RELATIVE", "DEM_ABSOLUTE"
ZERO_TOLERANCE_M = 1e-6
# Stated in prose in the configuration (dip_selection.dip_stability.rule and gates.WARN); there is no numeric key for them.
LOLO_TOLERANCE_DEG = 10.0
LOLO_MIN_LINES = 4
EDGE_DIP_DEG = 80.0
FRAME_DIP_GAP_DEG = 20.0
DECISION_PROVISIONAL = "PROVISIONAL (structural frame)"
DECISION_NOT_IDENTIFIABLE = "NOT_IDENTIFIABLE (structural frame)"
PURPOSE_SELECTED, PURPOSE_HORIZONTAL = "SELECTED", "HORIZONTAL_CONTROL"
STAGE_NOTE = "configuration 6: structural-frame indicator variography (dip search, circular down-hole null)"


_BLOCK_START = re.compile(r"(^|[:\-])\s[>|][-+0-9]*\s*(#.*)?$")
_ITEM = re.compile(r"^(\s*)- (.*)$")
_KEY = re.compile(r"^(\s*)([A-Za-z_][\w\-]*): (.*)$")


def _needs_quotes(text: str) -> bool:
    """A plain scalar that PyYAML cannot read: it contains ': ' or starts with a block or flow indicator."""
    return (": " in text or text.startswith("|") or text.startswith(">")) and not text.startswith(("[", "{", '"', "'"))


def _quote(text: str) -> str:
    body, comment = text, ""
    if " #" in text:
        body, comment = text.split(" #", 1)
        comment = " #" + comment
    body = body.rstrip()
    return '"' + body.replace("\\", "\\\\").replace('"', '\\"') + '"' + comment


def repair_plain_scalars(raw: str) -> tuple[str, list[str]]:
    """Quotes the plain prose scalars of the structural configuration that PyYAML rejects, in memory only.

    Lines inside block scalars are copied unchanged. A plain scalar that continues onto more-indented lines is joined before
    it is quoted. Returns the repaired text and one entry per repaired scalar, giving the line number and the original text.
    """
    lines = raw.split("\n")
    out: list[str] = []
    fixes: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if not stripped or stripped.startswith("#"):
            out.append(line)
            i += 1
            continue
        if _BLOCK_START.search(line.rstrip()):
            out.append(line)
            i += 1
            while i < n and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > indent):
                out.append(lines[i])
                i += 1
            continue
        item = _ITEM.match(line)
        key = _KEY.match(line)
        item_key = _KEY.match(item.group(2)) if item else None
        if item_key:
            prefix, text, text_indent = f"{item.group(1)}- {item_key.group(2)}: ", item_key.group(3), indent
        elif item:
            prefix, text, text_indent = f"{item.group(1)}- ", item.group(2), indent
        elif key:
            prefix, text, text_indent = f"{key.group(1)}{key.group(2)}: ", key.group(3), indent
        else:
            out.append(line)
            i += 1
            continue
        j = i + 1
        parts = [text]
        while j < n and lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) > text_indent \
                and not _ITEM.match(lines[j]) and not _KEY.match(lines[j]) and not lines[j].lstrip().startswith("#"):
            parts.append(lines[j].strip())
            j += 1
        full = " ".join(parts)
        if _needs_quotes(full):
            fixes.append(f"line {i + 1}: {full[:90]!r}")
            out.append(prefix + _quote(full))
            i = j
        else:
            out.extend(lines[i:j])
            i = j
    return "\n".join(out), fixes


def read_structural_config(path=STRUCTURAL_CONFIG_PATH) -> tuple[dict, str, list[str]]:
    """The predeclared configuration, its SHA-256 (of the exact file bytes) and the list of in-memory scalar repairs.

    The file is read as written. Only when PyYAML rejects it are prose scalars quoted in memory (see repair_plain_scalars);
    the repairs are returned so that they are reported. The file itself is never changed.
    """
    raw = path.read_bytes()
    sha = sha256_bytes(raw)
    text = raw.decode("utf-8")
    try:
        return yaml.safe_load(text), sha, []
    except yaml.YAMLError:
        repaired, fixes = repair_plain_scalars(text)
        return yaml.safe_load(repaired), sha, fixes


# ---------------------------------------------------------------------------------------------------------------------
# Coordinates
# ---------------------------------------------------------------------------------------------------------------------

def plane_coordinates(x, z, dip_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """s = z cos d + x sin d and t = x cos d - z sin d for apparent dip d in degrees (positive dips toward east)."""
    d = math.radians(dip_deg)
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    return z * math.cos(d) + x * math.sin(d), x * math.cos(d) - z * math.sin(d)


# ---------------------------------------------------------------------------------------------------------------------
# Data: binary intervals with both vertical frames
# ---------------------------------------------------------------------------------------------------------------------

class Base:
    """Binary intervals of one receipt in upstream interval order, with the RELATIVE and DEM_ABSOLUTE vertical frames."""

    def __init__(self, uid, hole, line, x, y, z, I, depth, weath, holes, lines):
        self.uid, self.hole, self.line, self.x, self.y, self.z = uid, hole, line, x, y, z
        self.I, self.depth, self.weath, self.holes, self.lines = I, depth, weath, holes, lines


def load_base(conn, rid: int) -> Base:
    gbid = conn.execute("SELECT geometry_build_id FROM source_receipts WHERE receipt_id = ?", (rid,)).fetchone()[0]
    rows = [dict(r) for r in conn.execute(
        "SELECT upstream_interval_id, hole_id, line_code, depth_from_m, easting_m, northing_m, z_relative_m, indicator, "
        "weathering_code FROM analysis_observations WHERE receipt_id = ? AND in_binary_target = 1 "
        "ORDER BY upstream_interval_id", (rid,))]
    if not rows:
        raise StopError("no binary interval in the receipt")
    # DEM_ABSOLUTE: interval_coordinates.z_dem_absolute_m of the receipt's geometry build, joined on the upstream interval id
    # (the same key the Objective 2 importer stores as upstream_interval_id). Read-only.
    up = connect_upstream_readonly(UPSTREAM_DB_PATH)
    try:
        dem = {int(r[0]): (r[1], r[2], r[3], r[4]) for r in up.execute(
            "SELECT interval_id, z_dem_absolute_m, z_relative_m, easting_m, northing_m FROM interval_coordinates "
            "WHERE geometry_build_id = ?", (gbid,))}
    finally:
        up.close()
    z_dem = []
    for r in rows:
        u = dem.get(r["upstream_interval_id"])
        if u is None or u[0] is None:
            raise StopError(f"interval {r['upstream_interval_id']} has no DEM elevation in geometry build {gbid}")
        if max(abs(u[1] - r["z_relative_m"]), abs(u[2] - r["easting_m"]), abs(u[3] - r["northing_m"])) > 1e-6:
            raise StopError("upstream interval_coordinates disagree with analysis_observations")
        z_dem.append(u[0])
    hole_names = sorted({r["hole_id"] for r in rows})
    line_names = sorted({r["line_code"] for r in rows})
    hidx = {h: k for k, h in enumerate(hole_names)}
    lidx = {ln: k for k, ln in enumerate(line_names)}
    return Base(
        uid=np.array([r["upstream_interval_id"] for r in rows], dtype=np.int64),
        hole=np.array([hidx[r["hole_id"]] for r in rows], dtype=np.int64),
        line=np.array([lidx[r["line_code"]] for r in rows], dtype=np.int64),
        x=np.array([r["easting_m"] for r in rows], dtype=np.float64),
        y=np.array([r["northing_m"] for r in rows], dtype=np.float64),
        z={FRAME_RELATIVE: np.array([r["z_relative_m"] for r in rows], dtype=np.float64),
           FRAME_DEM: np.array(z_dem, dtype=np.float64)},
        I=np.array([r["indicator"] for r in rows], dtype=np.int64),
        depth=np.array([r["depth_from_m"] for r in rows], dtype=np.float64),
        weath=[r["weathering_code"] for r in rows], holes=hole_names, lines=line_names)


class Sample:
    def __init__(self, sample_id: str, base: Base):
        mask = np.ones(base.uid.size, dtype=bool) if sample_id == SAMPLE_ALL else \
            np.array([w in FRESH_CODES for w in base.weath], dtype=bool)
        if not mask.any():
            raise StopError(f"sample {sample_id} is empty")
        hk = np.unique(base.hole[mask])
        lk = np.unique(base.line[mask])
        self.sample_id = sample_id
        self.uid = base.uid[mask]
        self.hole = np.searchsorted(hk, base.hole[mask]).astype(np.int64)
        self.line = np.searchsorted(lk, base.line[mask]).astype(np.int64)
        self.x, self.y = base.x[mask], base.y[mask]
        self.z = {f: v[mask] for f, v in base.z.items()}
        self.I = base.I[mask]
        self.depth = base.depth[mask]
        self.holes = [base.holes[k] for k in hk]
        self.lines = [base.lines[k] for k in lk]

    @property
    def p(self) -> float:
        return float(self.I.mean())


# ---------------------------------------------------------------------------------------------------------------------
# Pairs, alignment and selection
# ---------------------------------------------------------------------------------------------------------------------

def make_geo(i, j, b, hi, hj, line, edges, n_holes: int, rules: dict, n_within_in_experiment: int = 0,
             n_within_excluded: int = 0) -> dict:
    """A pair set with its bin counts, independent hole pair counts and support flags. Depends on geometry only."""
    nb = len(edges) - 1
    b = np.asarray(b, dtype=np.int64)
    n = np.bincount(b, minlength=nb).astype(np.int64)
    lo = np.minimum(hi, hj).astype(np.int64)
    up = np.maximum(hi, hj).astype(np.int64)
    key = np.unique(b * (n_holes * n_holes) + lo * n_holes + up)
    nhp = np.bincount(key // (n_holes * n_holes), minlength=nb).astype(np.int64)
    supported = (n >= rules["min_pairs"]) & (nhp >= rules["min_hole_pairs"])
    return {"i": i, "j": j, "bin": b, "hi": hi, "hj": hj, "line": line, "nb": nb, "n": n, "nhp": nhp,
            "supported": supported, "edges": edges, "K": n_holes, "rules": rules,
            "n_within_in_experiment": n_within_in_experiment, "n_within_excluded": n_within_excluded}


def upper_triangle(n: int) -> tuple[np.ndarray, np.ndarray]:
    return np.triu_indices(n, k=1)


def dip_geo(sample: Sample, z: np.ndarray, dip_deg: float, tri, edges, rules: dict, max_abs_ds: float) -> dict:
    """Within-line between-hole pairs on the plane of apparent dip dip_deg. Same-hole pairs are never formed; the number of
    same-hole pairs that met the band and were excluded is kept as a diagnostic."""
    I0, J0 = tri
    s_i, t_i = plane_coordinates(sample.x, z, dip_deg)
    ds = s_i[J0] - s_i[I0]
    lag = np.abs(t_i[J0] - t_i[I0])
    band = (np.abs(ds) <= max_abs_ds) & (lag > ZERO_TOLERANCE_M) & (lag >= edges[0]) & (lag < edges[-1])
    cand = band & (sample.line[I0] == sample.line[J0])
    same_hole = sample.hole[I0] == sample.hole[J0]
    n_excluded = int(np.count_nonzero(cand & same_hole))
    keep = np.nonzero(cand & ~same_hole)[0]
    i, j = I0[keep], J0[keep]
    b = np.searchsorted(edges, lag[keep], side="right").astype(np.int64) - 1
    within_in = int(np.count_nonzero(sample.hole[i] == sample.hole[j]))
    return make_geo(i, j, b, sample.hole[i], sample.hole[j], sample.line[i], edges, len(sample.holes), rules,
                    within_in, n_excluded)


def subset_geo(g: dict, mask: np.ndarray) -> dict:
    return make_geo(g["i"][mask], g["j"][mask], g["bin"][mask], g["hi"][mask], g["hj"][mask], g["line"][mask],
                    g["edges"], g["K"], g["rules"])


def gamma_of(g: dict, I: np.ndarray) -> np.ndarray:
    """EQUAL_PAIR semivariance per bin: gamma = 0.5 * mean((I_a - I_b)^2). NaN where a bin has no pairs."""
    diff = (I[g["i"]] != I[g["j"]]).astype(np.float64)
    nd = np.bincount(g["bin"], weights=diff, minlength=g["nb"])
    return np.where(g["n"] > 0, nd / (2.0 * np.maximum(g["n"], 1)), np.nan)


def first_two(g: dict) -> np.ndarray:
    return np.nonzero(g["supported"])[0][:2]


def alignment(g: dict, I: np.ndarray, pq: float, bins: np.ndarray) -> float:
    """A = 1 - mean(gamma over the given bins) / p(1 - p). NaN when fewer than two bins are given."""
    if bins.size < 2:
        return float("nan")
    return 1.0 - float(np.mean(gamma_of(g, I)[bins])) / pq


def select_dip(scores: dict) -> float | None:
    """Largest finite A; ties go to the dip closest to 0 (a tie between +d and -d goes to -d, the smaller value)."""
    finite = {d: a for d, a in scores.items() if a is not None and math.isfinite(a)}
    if not finite:
        return None
    best = max(finite.values())
    return min((d for d, a in finite.items() if a >= best - 1e-12), key=lambda d: (abs(d), d))


def pair_digest(sample: Sample, g: dict) -> tuple[str, int]:
    """SHA-256 of the sorted pair identifiers (upstream interval ids, smaller first). Used to check the pair set."""
    arr = np.stack([sample.uid[g["i"]], sample.uid[g["j"]]], axis=1).astype("<i8").reshape(-1, 2)
    order = np.lexsort((arr[:, 1], arr[:, 0]))
    return hashlib.sha256(arr[order].tobytes()).hexdigest(), int(arr.shape[0])


# ---------------------------------------------------------------------------------------------------------------------
# Circular down-hole shift null
# ---------------------------------------------------------------------------------------------------------------------

class HoleOrder:
    """Intervals sorted by hole and then depth, with the start and length of each hole's block."""

    def __init__(self, hole: np.ndarray, depth: np.ndarray, n_holes: int):
        self.order = np.lexsort((depth, hole))
        self.counts = np.bincount(hole, minlength=n_holes).astype(np.int64)
        self.starts = np.concatenate(([0], np.cumsum(self.counts)[:-1])).astype(np.int64)
        self.hs = hole[self.order]
        self.pos = np.arange(self.order.size, dtype=np.int64) - self.starts[self.hs]


def circular_shift(I: np.ndarray, ho: HoleOrder, rng: np.random.Generator) -> np.ndarray:
    """Each hole's indicator sequence (ordered by depth) is rotated by its own random offset in 0 .. n_hole - 1."""
    k = rng.integers(0, ho.counts)
    src = ho.starts[ho.hs] + (ho.pos + k[ho.hs]) % ho.counts[ho.hs]
    out = np.empty_like(I)
    out[ho.order] = I[ho.order][src]
    return out


def null_p_value(observed_max: float, null_max: np.ndarray, n_perm: int) -> float:
    """p = (1 + count(null_max >= observed_max)) / (n_perm + 1). Permutations without a valid score are not counted."""
    valid = np.isfinite(null_max)
    return (1 + int(np.count_nonzero(null_max[valid] >= observed_max))) / (n_perm + 1)


# ---------------------------------------------------------------------------------------------------------------------
# Fits, bootstrap and the between-line report
# ---------------------------------------------------------------------------------------------------------------------

def fit_models(g: dict, I: np.ndarray, p: float, cfg: dict) -> dict:
    gam = gamma_of(g, I)
    sup = g["supported"]
    edges = g["edges"]
    centres = 0.5 * (edges[:-1] + edges[1:])
    if not sup.any():
        return {m: {"model": m, "status": "NOT_IDENTIFIABLE", "reason": "no supported bins", "params": None,
                    "n_bins": 0, "objective": None, "lower_bounds": None, "upper_bounds": None} for m in FIT_MODELS}
    a_min, a_max = float(centres[sup][0]), float(edges[-1])
    gsup = np.where(sup, gam, np.nan)
    return {m: fitting.fit(centres, gsup, g["n"], m, p, a_min=a_min, a_max=a_max, min_bins=cfg["min_bins_fit"],
                           min_sill_fraction=cfg["min_sill_fraction"]) for m in FIT_MODELS}


def band_for(g: dict, I: np.ndarray, cfg: dict) -> dict:
    diff = (I[g["i"]] != I[g["j"]]).astype(np.float64)
    pairs = {"bin": g["bin"], "diff": diff, "hi": g["hi"], "hj": g["hj"], "nb": g["nb"]}
    return hole_bootstrap(pairs, g["K"], n_replicates=cfg["boot_replicates"], seed=cfg["boot_seed"],
                          confidence=cfg["boot_confidence"])


def between_line(sample: Sample, z: np.ndarray, dip_deg: float, tri, cfg: dict) -> list[dict]:
    """REPORT_ONLY: pairs between holes on different lines at the selected dip, |ds| <= band, lag = |northing difference|."""
    I0, J0 = tri
    s_i, _ = plane_coordinates(sample.x, z, dip_deg)
    ds = np.abs(s_i[J0] - s_i[I0])
    lag = np.abs(sample.y[J0] - sample.y[I0])
    cand = (sample.line[I0] != sample.line[J0]) & (ds <= cfg["max_abs_ds"])
    out = []
    for a, b in cfg["between_bins"]:
        m = cand & (lag >= a) & (lag < b)
        ii, jj = I0[m], J0[m]
        n = int(ii.size)
        nd = int(np.count_nonzero(sample.I[ii] != sample.I[jj]))
        lo = np.minimum(sample.hole[ii], sample.hole[jj])
        hi = np.maximum(sample.hole[ii], sample.hole[jj])
        nhp = int(np.unique(lo * len(sample.holes) + hi).size) if n else 0
        out.append({"lag_from_m": float(a), "lag_to_m": float(b), "n_pairs": n, "n_hole_pairs": nhp, "n_diff": nd,
                    "gamma": (nd / (2.0 * n)) if n else None, "supported": int(n >= cfg["between_min_pairs"])})
    return out


# ---------------------------------------------------------------------------------------------------------------------
# One sample in one frame
# ---------------------------------------------------------------------------------------------------------------------

def analyse_frame(sample: Sample, frame: str, cfg: dict, tri) -> dict:
    z = sample.z[frame]
    p = sample.p
    pq = p * (1.0 - p)
    edges = cfg["edges"]
    geos = {d: dip_geo(sample, z, d, tri, edges, cfg["rules"], cfg["max_abs_ds"]) for d in cfg["grid"]}
    bins = {d: first_two(geos[d]) for d in cfg["grid"]}
    scores = {d: alignment(geos[d], sample.I, pq, bins[d]) for d in cfg["grid"]}
    sel = select_dip(scores)
    if sel is None:
        raise StopError(f"{sample.sample_id} {frame}: no dip in the grid has two supported bins")
    obs_max = max(a for a in scores.values() if math.isfinite(a))

    # Selection null: circular down-hole shift, whole grid rescored each permutation, supported bins as observed.
    ho = HoleOrder(sample.hole, sample.depth, len(sample.holes))
    rng = np.random.default_rng(cfg["seed"])
    null_max = np.full(cfg["n_perm"], np.nan)
    for r in range(cfg["n_perm"]):
        In = circular_shift(sample.I, ho, rng)
        vals = [alignment(geos[d], In, pq, bins[d]) for d in cfg["grid"]]
        finite = [v for v in vals if math.isfinite(v)]
        null_max[r] = max(finite) if finite else np.nan
    valid = np.isfinite(null_max)
    p_value = null_p_value(obs_max, null_max, cfg["n_perm"])
    p95 = float(np.percentile(null_max[valid], 95))

    # Leave-one-line-out dip.
    lolo = {}
    for li, line in enumerate(sample.lines):
        sc = {}
        for d in cfg["grid"]:
            gl = subset_geo(geos[d], geos[d]["line"] != li)
            sc[d] = alignment(gl, sample.I, pq, first_two(gl))
        lolo[line] = select_dip(sc)
    within = {ln: (v is not None and abs(v - sel) <= LOLO_TOLERANCE_DEG + 1e-9) for ln, v in lolo.items()}

    # Fits at the selected dip, leave-one-line-out refits and the hole bootstrap band.
    g_sel = geos[sel]
    fits = fit_models(g_sel, sample.I, p, cfg)
    fits_loo = []
    for li in range(len(sample.lines)):
        gl = subset_geo(g_sel, g_sel["line"] != li)
        fits_loo.append(fit_models(gl, sample.I, p, cfg))
    stabs = {m: fitting.stability(fits[m], [f[m] for f in fits_loo], low=cfg["range_low"], high=cfg["range_high"])
             for m in FIT_MODELS}
    bands = {}
    for label, dip in ((PURPOSE_SELECTED, sel), (PURPOSE_HORIZONTAL, 0.0)):
        bands[label] = {"dip": dip, "geo": geos[dip], "band": band_for(geos[dip], sample.I, cfg)}
    bins_out = []
    for label in (PURPOSE_SELECTED, PURPOSE_HORIZONTAL):
        g = bands[label]["geo"]
        gam = gamma_of(g, sample.I)
        for k in range(g["nb"]):
            bb = bands[label]["band"]
            bins_out.append({"purpose": label, "dip": bands[label]["dip"], "bin": k, "lag_from": float(edges[k]),
                             "lag_to": float(edges[k + 1]), "centre": float(0.5 * (edges[k] + edges[k + 1])),
                             "n_pairs": int(g["n"][k]), "n_hole_pairs": int(g["nhp"][k]),
                             "gamma": float(gam[k]) if g["supported"][k] else None,
                             "supported": int(g["supported"][k]),
                             "lower": _nf(bb["lower"][k]), "upper": _nf(bb["upper"][k]),
                             "median": _nf(bb["median"][k]), "n_rep": int(bb["n_used"][k])})

    # Between-line report at the selected dip.
    between = between_line(sample, z, sel, tri, cfg)

    # Digests of every dip's pair set (the d = 0 digest is checked by gate G34).
    digests = {d: pair_digest(sample, geos[d]) for d in cfg["grid"]}

    stable_models = [m for m in FIT_MODELS if fits[m]["status"] == "FITTED" and stabs[m]["status"] == "STABLE"]
    n_within = sum(within.values())
    decision = DECISION_PROVISIONAL if (p_value < cfg["alpha"] and n_within >= LOLO_MIN_LINES and stable_models) \
        else DECISION_NOT_IDENTIFIABLE
    return {
        "sample_id": sample.sample_id, "frame_id": frame, "p": p, "pq": pq, "selected_dip": sel,
        "scores": scores, "n_supported": {d: int(geos[d]["supported"].sum()) for d in cfg["grid"]},
        "n_pairs": {d: int(geos[d]["n"].sum()) for d in cfg["grid"]},
        "within_in_experiment": {d: geos[d]["n_within_in_experiment"] for d in cfg["grid"]},
        "within_excluded": {d: geos[d]["n_within_excluded"] for d in cfg["grid"]},
        "digests": digests, "observed_max": obs_max, "null_max": null_max, "null_p95": p95, "p_value": p_value,
        "n_null_valid": int(valid.sum()), "lolo": lolo, "lolo_within": within, "lines_within": n_within,
        "fits": fits, "fits_loo_ranges": {m: [f[m]["params"][2] if f[m]["status"] == "FITTED" else None
                                             for f in fits_loo] for m in FIT_MODELS},
        "stability": stabs, "bins": bins_out, "between": between, "decision": decision,
        "stable_models": stable_models,
    }


def _nf(x) -> float | None:
    x = float(x)
    return None if math.isnan(x) else x


def _config(cfg: dict) -> dict:
    """Numbers used by the stage, all read from the predeclared configuration."""
    frame = cfg["frame"]
    pw = cfg["pairing"]["within_line_between_hole"]
    bl = cfg["pairing"]["between_line_along_strike"]
    sn = cfg["dip_selection"]["selection_null"]
    mf = cfg["model_fitting"]
    hb = mf["hole_bootstrap"]
    return {
        "grid": [float(d) for d in frame["apparent_dip_grid_deg"]],
        "max_abs_ds": float(pw["max_abs_ds_m"]), "lag_width": float(pw["lag_width_m"]), "lag_max": float(pw["lag_max_m"]),
        "edges": bin_edges(float(pw["lag_width_m"]), float(pw["lag_max_m"])),
        "rules": {"min_pairs": int(pw["min_pairs_per_bin"]), "min_hole_pairs": int(pw["min_independent_hole_pairs_per_bin"])},
        "min_bins_fit": int(pw["min_supported_bins_for_fit"]),
        "n_perm": int(sn["n_permutations"]), "seed": int(sn["seed"]), "alpha": float(sn["alpha"]),
        "min_sill_fraction": float(mf["min_structured_sill_fraction"]),
        "range_low": float(mf["stable_if_range_ratio_between"][0]), "range_high": float(mf["stable_if_range_ratio_between"][1]),
        "boot_replicates": int(hb["n_replicates"]), "boot_seed": int(hb["seed"]), "boot_confidence": float(hb["confidence"]),
        "between_bins": [(float(a), float(b)) for a, b in bl["lag_bins_m"]],
        "between_min_pairs": int(bl["min_pairs_per_bin"]),
        "frames": [v["frame_id"] for v in frame["vertical_frames"]],
    }


# ---------------------------------------------------------------------------------------------------------------------
# Database writes
# ---------------------------------------------------------------------------------------------------------------------

def _write(conn, rid: int, version: str, sample: str, res: dict, cfg: dict) -> None:
    frame = res["frame_id"]
    sel = res["selected_dip"]
    for d in cfg["grid"]:
        a = res["scores"][d]
        conn.execute("INSERT INTO structural_alignment_scores (receipt_id, config_version, sample_id, frame_id, dip_deg, "
                     "n_supported_bins, n_pairs, alignment_score, is_selected, is_horizontal_control) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (rid, version, sample, frame, d, res["n_supported"][d], res["n_pairs"][d],
                      _nf(a) if a is not None else None, int(d == sel), int(d == 0.0)))
        digest, n = res["digests"][d]
        conn.execute("INSERT INTO structural_pair_digests (receipt_id, config_version, sample_id, frame_id, dip_deg, n_pairs, "
                     "n_within_hole_pairs, n_within_hole_candidates_excluded, pair_digest) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (rid, version, sample, frame, d, n, res["within_in_experiment"][d], res["within_excluded"][d],
                      digest))
    conn.execute("INSERT INTO structural_null_summary (receipt_id, config_version, sample_id, frame_id, selected_dip_deg, "
                 "observed_max_alignment, null_p95_max, n_permutations, null_seed, n_null_valid, p_value, alpha, "
                 "max_abs_ds_m, lag_width_m, lag_max_m, bootstrap_replicates, bootstrap_seed) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (rid, version, sample, frame, sel, res["observed_max"], res["null_p95"], cfg["n_perm"], cfg["seed"],
                  res["n_null_valid"], res["p_value"], cfg["alpha"], cfg["max_abs_ds"], cfg["lag_width"], cfg["lag_max"],
                  cfg["boot_replicates"], cfg["boot_seed"]))
    for line, dip in res["lolo"].items():
        conn.execute("INSERT INTO structural_lolo_dips (receipt_id, config_version, sample_id, frame_id, excluded_line, "
                     "full_dip_deg, lolo_dip_deg, within_tolerance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (rid, version, sample, frame, line, sel, dip, int(res["lolo_within"][line])))
    for b in res["bins"]:
        conn.execute("INSERT INTO structural_variogram_bins (receipt_id, config_version, sample_id, frame_id, purpose, dip_deg, "
                     "bin_index, lag_from_m, lag_to_m, lag_centre_m, n_pairs, n_independent_hole_pairs, gamma, supported, "
                     "gamma_lower, gamma_upper, gamma_median, n_band_replicates) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (rid, version, sample, frame, b["purpose"], b["dip"], b["bin"], b["lag_from"], b["lag_to"], b["centre"],
                      b["n_pairs"], b["n_hole_pairs"], b["gamma"], b["supported"], b["lower"], b["upper"], b["median"],
                      b["n_rep"]))
    for m in FIT_MODELS:
        f = res["fits"][m]
        st = res["stability"][m]
        par = f["params"] if f["status"] == "FITTED" else None
        ranges = [r for r in res["fits_loo_ranges"][m] if r is not None]
        ratios = [r / par[2] for r in ranges] if (par is not None and ranges) else []
        conn.execute("INSERT INTO structural_fits (receipt_id, config_version, sample_id, frame_id, model, selected_dip_deg, "
                     "fit_status, reason, nugget, structured_sill, range_m, n_bins_used, objective_value, stability_status, "
                     "stability_reason, range_ratio_min, range_ratio_max) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (rid, version, sample, frame, m, sel, f["status"], f["reason"],
                      _nf(par[0]) if par is not None else None, _nf(par[1]) if par is not None else None,
                      _nf(par[2]) if par is not None else None, int(f["n_bins"]),
                      _nf(f["objective"]) if f.get("objective") is not None else None, st["status"], st["reason"],
                      min(ratios) if ratios else None, max(ratios) if ratios else None))
    for bl in res["between"]:
        conn.execute("INSERT INTO structural_between_line (receipt_id, config_version, sample_id, frame_id, selected_dip_deg, "
                     "lag_from_m, lag_to_m, n_pairs, n_independent_hole_pairs, n_different_class, gamma, supported) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (rid, version, sample, frame, sel, bl["lag_from_m"], bl["lag_to_m"], bl["n_pairs"], bl["n_hole_pairs"],
                      bl["n_diff"], bl["gamma"], bl["supported"]))


def _write_decision(conn, rid: int, version: str, sample: str, res: dict, cfg: dict) -> None:
    p_ok = res["p_value"] < cfg["alpha"]
    dip_ok = res["lines_within"] >= LOLO_MIN_LINES
    fit_ok = bool(res["stable_models"])
    range_ok = fit_ok
    reason = (f"selection-null p = {res['p_value']:.4f} ({'below' if p_ok else 'not below'} {cfg['alpha']}); "
              f"{res['lines_within']} of {len(res['lolo'])} leave-one-line-out dips within {LOLO_TOLERANCE_DEG:g} degrees "
              f"(need {LOLO_MIN_LINES}); stable FITTED model: {', '.join(res['stable_models']) or 'none'}; "
              f"decision {res['decision']}")
    conn.execute("INSERT INTO structural_decisions (receipt_id, config_version, sample_id, frame_id, decision, p_value_below_alpha, "
                 "dip_stable, lines_within_tolerance, stable_fitted_model, range_stable, reason) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (rid, version, sample, FRAME_RELATIVE, res["decision"], int(p_ok), int(dip_ok), res["lines_within"],
                  ", ".join(res["stable_models"]) or None, int(range_ok), reason))


def _check_bins(sample: Sample, res_geo: dict, I: np.ndarray) -> None:
    """The bootstrap weighted semivariance with unit multiplicities must equal the plain EQUAL_PAIR value."""
    band_plain = weighted_gamma({"bin": res_geo["bin"], "diff": (I[res_geo["i"]] != I[res_geo["j"]]).astype(np.float64),
                                 "hi": res_geo["hi"], "hj": res_geo["hj"], "nb": res_geo["nb"]}, np.ones(res_geo["K"]))
    sup = res_geo["supported"]
    if sup.any() and not np.allclose(band_plain[sup], gamma_of(res_geo, I)[sup], rtol=1e-9, atol=1e-12):
        raise StopError("weighted and plain semivariance disagree at the selected dip")


# ---------------------------------------------------------------------------------------------------------------------
# Stage
# ---------------------------------------------------------------------------------------------------------------------

def run(o2_path=O2_DB_PATH, config_path=STRUCTURAL_CONFIG_PATH, base_config_path=O2_CONFIG_PATH) -> dict:
    cfg_file, cfg_sha, repairs = read_structural_config(config_path)
    weathering_cfg, _ = load_config(WEATHERING_CONFIG_PATH)
    if cfg_file.get("extends") != weathering_cfg["config_version"]:
        raise StopError(f"{cfg_file['config_version']} extends {cfg_file.get('extends')}, not configuration "
                        f"{weathering_cfg['config_version']}")
    version = cfg_file["config_version"]
    cfg = _config(cfg_file)
    conn = connect_o2(o2_path)
    try:
        rid = conn.execute("SELECT MAX(receipt_id) FROM source_receipts").fetchone()[0]
        if rid is None:
            raise StopError("no receipt: run the import first")
        done = conn.execute("SELECT COUNT(*) FROM structural_alignment_scores WHERE receipt_id = ? AND config_version = ?",
                            (rid, version)).fetchone()[0]
        if done:
            raise StopError(f"configuration {version} has already run on receipt {rid}")
        base = load_base(conn, rid)
        results = {}
        conn.execute("BEGIN IMMEDIATE")
        try:
            run_id = conn.execute("INSERT INTO stage_runs (run_kind, config_version, config_sha256, receipt_id, started_utc, "
                                  "status, code_commit, note) VALUES ('SENSITIVITY', ?, ?, ?, ?, 'RUNNING', ?, ?)",
                                  (version, cfg_sha, rid, utc_now(), code_commit(), STAGE_NOTE + (f"; in-memory YAML scalar repairs: {len(repairs)}" if repairs else ""))).lastrowid
            for sid in (SAMPLE_ALL, SAMPLE_FRESH):
                sample = Sample(sid, base)
                tri = upper_triangle(sample.uid.size)
                for frame in cfg["frames"]:
                    res = analyse_frame(sample, frame, cfg, tri)
                    sel_geo = dip_geo(sample, sample.z[frame], res["selected_dip"], tri, cfg["edges"], cfg["rules"],
                                      cfg["max_abs_ds"])
                    _check_bins(sample, sel_geo, sample.I)
                    _write(conn, rid, version, sid, res, cfg)
                    if frame == FRAME_RELATIVE:
                        _write_decision(conn, rid, version, sid, res, cfg)
                    results[(sid, frame)] = res
            conn.execute("UPDATE stage_runs SET status = 'COMPLETED', finished_utc = ?, note = ? WHERE run_id = ?",
                         (utc_now(), STAGE_NOTE + "; no handoff row written" + (f"; in-memory YAML scalar "
                          f"repairs: {len(repairs)}" if repairs else ""), run_id))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    summary = {}
    for (sid, frame), r in results.items():
        summary.setdefault(sid, {})[frame] = {
            "selected_dip_deg": r["selected_dip"], "alignment_selected": _nf(r["scores"][r["selected_dip"]]),
            "alignment_dip0": _nf(r["scores"][0.0]), "observed_max": _nf(r["observed_max"]),
            "p_value": r["p_value"], "null_p95_max": _nf(r["null_p95"]), "n_null_valid": r["n_null_valid"],
            "lolo_dips": r["lolo"], "lines_within_tolerance": r["lines_within"],
            "fits": {m: {"status": r["fits"][m]["status"], "reason": r["fits"][m]["reason"],
                         "params": [float(v) for v in r["fits"][m]["params"]] if r["fits"][m]["status"] == "FITTED" else None,
                         "stability": r["stability"][m]["status"]} for m in FIT_MODELS},
            "between_line": r["between"], "decision": r["decision"] if frame == FRAME_RELATIVE else "sensitivity only"}
    return {"run_id": run_id, "receipt_id": rid, "config_version": version, "config_sha256": cfg_sha,
            "yaml_repairs_in_memory": repairs, "samples": summary, "handoff_rows_written": 0}

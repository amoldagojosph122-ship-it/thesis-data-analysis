"""Configuration 6 (structural frame): unit tests on synthetic data and on the predeclared configuration file.

No test here opens the Objective 2 database. The stage itself is exercised by the structural command and by gates G32 to G37.
"""

import math

import numpy as np

from kambale.objective_2 import structural
from kambale.objective_2.pairs import bin_edges

EDGES = bin_edges(20.0, 500.0)
RULES = {"min_pairs": 100, "min_hole_pairs": 10}


def _synthetic(z_of_interval, n_per_line=12, n_lines=2, depth_n=60, spacing=10.0):
    """Vertical 1 m holes on east-west lines. z_of_interval(x, z, line) gives the indicator of each interval."""
    uid, hole, line, xs, ys, zs, I, depth = [], [], [], [], [], [], [], []
    holes, lines = [], []
    k = 0
    for li in range(n_lines):
        lines.append(f"L{li}")
        for hi in range(n_per_line):
            hole_index = len(holes)
            holes.append(f"H{li}{hi}")
            x = 1000.0 + hi * spacing
            y = 5000.0 + 100.0 * li
            for d in range(depth_n):
                z = -(d + 0.5)
                uid.append(k)
                hole.append(hole_index)
                line.append(li)
                xs.append(x)
                ys.append(y)
                zs.append(z)
                I.append(int(z_of_interval(x, z, li)))
                depth.append(float(d))
                k += 1
    base = structural.Base(
        uid=np.array(uid, dtype=np.int64), hole=np.array(hole, dtype=np.int64), line=np.array(line, dtype=np.int64),
        x=np.array(xs), y=np.array(ys), z={"RELATIVE": np.array(zs), "DEM_ABSOLUTE": np.array(zs) + 300.0},
        I=np.array(I, dtype=np.int64), depth=np.array(depth), weath=["mw"] * len(uid), holes=holes, lines=lines)
    return structural.Sample("ALL_BINARY", base)


def _config(grid):
    return {"grid": grid, "edges": EDGES, "rules": RULES, "max_abs_ds": 3.0, "min_bins_fit": 5,
            "min_sill_fraction": 0.05, "n_perm": 60, "seed": 20261108, "alpha": 0.05, "range_low": 0.5,
            "range_high": 2.0, "boot_replicates": 20, "boot_seed": 20261108, "boot_confidence": 0.95,
            "between_bins": [(50.0, 150.0), (150.0, 250.0)], "between_min_pairs": 100, "lag_width": 20.0,
            "lag_max": 500.0, "frames": ["RELATIVE", "DEM_ABSOLUTE"]}


def test_coordinate_transform_at_zero_dip_is_identity():
    x = np.array([1.0, 25.0, -7.5])
    z = np.array([-3.0, -40.0, -0.5])
    s, t = structural.plane_coordinates(x, z, 0.0)
    assert np.allclose(s, z)
    assert np.allclose(t, x)


def test_coordinate_transform_rotates_by_the_apparent_dip():
    s, t = structural.plane_coordinates(np.array([10.0]), np.array([0.0]), 30.0)
    assert s[0] == 10.0 * math.sin(math.radians(30.0))
    assert t[0] == 10.0 * math.cos(math.radians(30.0))


def test_no_within_hole_pairs_enter_an_experiment():
    sample = _synthetic(lambda x, z, li: int(-z) // 7 % 2)
    tri = structural.upper_triangle(sample.uid.size)
    for dip in (-40.0, 0.0, 60.0):
        g = structural.dip_geo(sample, sample.z["RELATIVE"], dip, tri, EDGES, RULES, 3.0)
        assert g["n_within_in_experiment"] == 0
        assert np.all(g["hi"] != g["hj"])
        assert np.all(sample.line[g["i"]] == sample.line[g["j"]])


def test_zero_dip_pair_set_equals_the_within_line_dz_set():
    rng = np.random.default_rng(3)
    sample = _synthetic(lambda x, z, li: rng.integers(0, 2))
    tri = structural.upper_triangle(sample.uid.size)
    g = structural.dip_geo(sample, sample.z["RELATIVE"], 0.0, tri, EDGES, RULES, 3.0)
    got = {(int(a), int(b)) for a, b in zip(g["i"], g["j"])}
    z, x, line, hole = sample.z["RELATIVE"], sample.x, sample.line, sample.hole
    want = set()
    n = sample.uid.size
    for a in range(n):
        for b in range(a + 1, n):
            if line[a] != line[b] or hole[a] == hole[b]:
                continue
            if abs(z[b] - z[a]) > 3.0:
                continue
            lag = abs(x[b] - x[a])
            if 1e-6 < lag < 500.0:
                want.add((a, b))
    assert got == want
    assert len(got) > 0


def test_circular_shift_preserves_each_holes_prevalence_and_is_a_rotation():
    rng = np.random.default_rng(11)
    sample = _synthetic(lambda x, z, li: 0)
    sample.I = rng.integers(0, 2, size=sample.I.size).astype(np.int64)
    ho = structural.HoleOrder(sample.hole, sample.depth, len(sample.holes))
    shifted = structural.circular_shift(sample.I, ho, np.random.default_rng(5))
    for h in range(len(sample.holes)):
        idx = np.nonzero(sample.hole == h)[0]
        order = idx[np.argsort(sample.depth[idx])]
        before = sample.I[order]
        after = shifted[order]
        assert before.sum() == after.sum()
        assert any(np.array_equal(np.roll(before, k), after) for k in range(before.size))
    assert shifted.sum() == sample.I.sum()


def test_horizontal_layer_selects_dip_zero():
    sample = _synthetic(lambda x, z, li: int(-z // 15) % 2)
    tri = structural.upper_triangle(sample.uid.size)
    res = structural.analyse_frame(sample, "RELATIVE", _config([float(d) for d in range(-80, 81, 10)]), tri)
    assert res["selected_dip"] == 0.0


def test_layer_dipping_forty_degrees_east_is_recovered_within_ten_degrees():
    dip = 40.0
    width = 15.0

    def indicator(x, z, li):
        s = z * math.cos(math.radians(dip)) + x * math.sin(math.radians(dip))
        return int(math.floor(-s / width)) % 2

    sample = _synthetic(indicator)
    tri = structural.upper_triangle(sample.uid.size)
    res = structural.analyse_frame(sample, "RELATIVE", _config([float(d) for d in range(-80, 81, 10)]), tri)
    assert abs(res["selected_dip"] - dip) <= 10.0


def test_selection_ties_go_to_the_dip_closest_to_zero():
    assert structural.select_dip({-40.0: 0.5, 0.0: 0.2, 40.0: 0.5}) == -40.0
    assert structural.select_dip({-40.0: 0.1, 0.0: 0.5, 40.0: 0.5}) == 0.0
    assert structural.select_dip({-40.0: 0.1, 0.0: 0.2, 10.0: 0.2, 40.0: 0.5}) == 40.0
    assert structural.select_dip({-40.0: float("nan"), 0.0: float("nan")}) is None


def test_null_p_value_formula():
    null = np.array([0.1, 0.6, 0.5, np.nan])
    # observed 0.5: null values 0.6 and 0.5 are at least as large; the NaN is not a valid permutation
    assert structural.null_p_value(0.5, null, 4) == (1 + 2) / (4 + 1)
    assert structural.null_p_value(0.99, np.array([0.1, 0.2]), 2) == (1 + 0) / (2 + 1)


def test_pair_digest_is_independent_of_pair_order():
    sample = _synthetic(lambda x, z, li: 0, n_per_line=4, depth_n=10)
    tri = structural.upper_triangle(sample.uid.size)
    g = structural.dip_geo(sample, sample.z["RELATIVE"], 0.0, tri, EDGES, RULES, 3.0)
    d1, n1 = structural.pair_digest(sample, g)
    perm = np.random.default_rng(1).permutation(g["i"].size)
    shuffled = structural.make_geo(g["i"][perm], g["j"][perm], g["bin"][perm], g["hi"][perm], g["hj"][perm], g["line"][perm],
                                   EDGES, g["K"], RULES)
    d2, n2 = structural.pair_digest(sample, shuffled)
    assert (d1, n1) == (d2, n2)


def test_predeclared_configuration_reads_with_numbers_as_written():
    cfg, sha, repairs = structural.read_structural_config()
    frame = cfg["frame"]
    assert cfg["config_version"] == "O2-CFG-2026.11.06-6"
    assert [float(d) for d in frame["apparent_dip_grid_deg"]] == [float(d) for d in range(-80, 81, 10)]
    pw = cfg["pairing"]["within_line_between_hole"]
    assert (pw["max_abs_ds_m"], pw["lag_width_m"], pw["lag_max_m"]) == (3.0, 20.0, 500.0)
    assert cfg["dip_selection"]["selection_null"]["seed"] == 20261108
    assert cfg["dip_selection"]["selection_null"]["n_permutations"] == 500
    assert len(sha) == 64
    # The file is not valid YAML as written; each in-memory repair quotes one prose scalar and is reported.
    assert len(repairs) >= 1

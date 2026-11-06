"""Model fitting, identifiability and stability (specification 02, sections 5 to 7; specification 03, G13 to G16)."""

import numpy as np
import pytest
from scipy.optimize import nnls

from kambale.objective_2 import fitting, variogram
from kambale.objective_2.config import O2_CONFIG_PATH, O2_DB_PATH, load_config


def test_fit_recovers_known_spherical():
    h = np.arange(10.0, 500.0, 20.0)
    truth = (0.05, 0.10, 150.0)
    g = fitting.gamma_model(h, "spherical", *truth)
    res = fitting.fit(h, g, np.full(h.size, 500.0), "spherical", 0.3, a_min=10.0, a_max=500.0, min_bins=5)
    assert res["status"] == "FITTED"
    assert res["params"] == pytest.approx(truth, rel=2e-2)


def test_fit_admissibility():
    assert fitting.admissible(0.1, 0.05, 50.0)
    assert not fitting.admissible(0.1, -0.01, 50.0)
    assert not fitting.admissible(0.1, 0.05, 0.0)
    assert not fitting.admissible(float("nan"), 0.05, 50.0)


def test_nonidentifiable_reported():
    res = fitting.fit(np.array([10.0, 30.0]), np.array([0.2, 0.19]), np.array([100.0, 100.0]), "exponential", 0.3,
                      a_min=10.0, a_max=500.0, min_bins=5)
    assert res["status"] == "NOT_IDENTIFIABLE"
    assert res["params"] is None


def test_insufficient_bins_not_identifiable():
    res = fitting.fit(np.array([10.0, 30.0]), np.array([0.2, 0.19]), np.array([100.0, 100.0]), "spherical", 0.3,
                      a_min=10.0, a_max=500.0, min_bins=5)
    assert res["status"] == "NOT_IDENTIFIABLE" and res["params"] is None


def test_pure_nugget_is_not_identifiable():
    h = np.arange(10.0, 500.0, 20.0)
    res = fitting.fit(h, np.full(h.size, 0.15), np.full(h.size, 300.0), "spherical", 0.3, a_min=10.0, a_max=500.0,
                      min_bins=5)
    assert res["status"] == "NOT_IDENTIFIABLE"
    assert "sill" in res["reason"] or "range" in res["reason"]


def test_stability_rule():
    base = {"status": "FITTED", "params": (0.05, 0.10, 100.0)}
    inside = [{"status": "FITTED", "params": (0.05, 0.10, r)} for r in (80.0, 120.0, 190.0)]
    outside = inside[:2] + [{"status": "FITTED", "params": (0.05, 0.10, 300.0)}]
    assert fitting.stability(base, inside)["status"] == "STABLE"
    assert fitting.stability(base, outside)["status"] == "UNSTABLE"
    assert fitting.stability({"status": "NOT_IDENTIFIABLE"}, inside)["status"] == "NOT_ASSESSED"


@pytest.mark.skipif(not O2_DB_PATH.exists(), reason="Objective 2 database not built")
def test_lateral_profile_confirms_pure_nugget(o2_ro, receipt_id):
    """Independent check on the stored lateral fit: over every candidate range, the best non-negative weighted least
    squares solution has no structured sill, and its objective equals the stored objective."""
    config, _ = load_config(O2_CONFIG_PATH)
    spec = {s.name: s for s in variogram.base_specs(config)}["LATERAL_BETWEEN"]
    res = variogram.compute(variogram.load_observations(o2_ro, receipt_id), spec)
    m = res["supported"]
    h, g, n = res["centres"][m], res["gamma"][m], res["n_pairs"][m].astype(float)
    w = np.sqrt(n / g ** 2)
    best, best_c1 = np.inf, None
    for a in np.arange(10.0, 500.0 + 1e-9, 2.5):
        B = np.column_stack([np.ones_like(h), fitting.gamma_model(h, "spherical", 0.0, 1.0, a)])
        c, r = nnls(w[:, None] * B, w * g)
        if r * r < best:
            best, best_c1 = r * r, c[1]
    assert best_c1 == pytest.approx(0.0, abs=1e-9)
    stored = o2_ro.execute("SELECT f.objective_value FROM variogram_fits f JOIN variogram_experiments e "
                           "ON e.experiment_id = f.experiment_id WHERE e.receipt_id = ? AND e.variant = 'BASE' "
                           "AND e.direction_id = 'LATERAL_BETWEEN' AND f.model = 'spherical'", (receipt_id,)).fetchone()[0]
    assert stored == pytest.approx(best, rel=1e-6)

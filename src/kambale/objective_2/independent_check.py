"""Independent check of the experimental semivariogram against scikit-gstat (specification 06, section 1).

scikit-gstat is not part of the project environment: installing it there would change the scipy version that the
environment is verified with. It is imported from an explicit site directory given on the command line. The check uses
the three-dimensional omnidirectional experiment with within-hole pairs included, because the Matheron estimator in
scikit-gstat uses every pair. Semivariance is compared bin by bin with the stored estimator. The outcome is written to
reports/objective_2/INDEPENDENT_CHECK.txt, and the run report quotes it.

Usage: python -I -m kambale.objective_2.independent_check --site <site-directory>
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sqlite3
import sys

import numpy as np

from kambale.objective_2 import variogram
from kambale.objective_2.config import O2_CONFIG_PATH, O2_DB_PATH, O2_REPORT_DIR, load_config, utc_now

TOLERANCE = 1e-9


def run(site_dir: str | None, o2_path=O2_DB_PATH, config_path=O2_CONFIG_PATH) -> dict:
    if site_dir:
        sys.path.insert(0, site_dir)
    try:
        import skgstat
    except ImportError as exc:
        return {"status": "NOT_RUN", "reason": f"scikit-gstat could not be imported: {exc}"}
    config, _ = load_config(config_path)
    base = next(s for s in variogram.base_specs(config) if s.name == "OMNI_3D_BETWEEN")
    spec = dataclasses.replace(base, within="INCLUDED", min_pairs=1, min_hole_pairs=0, variant="BASE")
    conn = sqlite3.connect(f"{o2_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rid = conn.execute("SELECT MAX(receipt_id) FROM source_receipts").fetchone()[0]
        obs = variogram.load_observations(conn, rid)
    finally:
        conn.close()
    ours = variogram.compute(obs, spec)
    V = skgstat.Variogram(coordinates=obs.X, values=obs.I.astype(np.float64), n_lags=len(spec.edges) - 1,
                          maxlag=spec.lag_max_m, bin_func="even", estimator="matheron", use_nugget=False)
    skg = np.asarray(V.experimental, dtype=np.float64)
    ours_gamma = np.asarray(ours["gamma"], dtype=np.float64)
    n = min(len(skg), len(ours_gamma))
    diff = np.abs(skg[:n] - ours_gamma[:n])
    worst = float(np.nanmax(diff)) if np.any(np.isfinite(diff)) else float("nan")
    agree = bool(len(skg) == len(ours_gamma) and np.allclose(skg, ours_gamma, rtol=0.0, atol=TOLERANCE, equal_nan=True))
    result = {"status": "PASS" if agree else "FAIL", "skgstat_version": getattr(skgstat, "__version__", "unknown"),
              "bins_ours": int(len(ours_gamma)), "bins_skgstat": int(len(skg)), "max_abs_difference": worst,
              "tolerance": TOLERANCE, "intervals": int(obs.I.size), "receipt_id": int(rid),
              "config_version": config["config_version"], "site_dir": site_dir or "(environment)",
              "checked_utc": utc_now()}
    O2_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "Independent check of the experimental semivariogram against scikit-gstat", "",
        f"Checked at {result['checked_utc']} for configuration {result['config_version']}, receipt {rid}, "
        f"{result['intervals']} binary intervals.",
        f"scikit-gstat {result['skgstat_version']}, imported from {result['site_dir']} (outside the project environment).",
        "Experiment: OMNI_3D_BETWEEN with within-hole pairs included, 20 m bins to 500 m, equal-pair (Matheron) estimator.",
        f"Bins: ours {result['bins_ours']}, scikit-gstat {result['bins_skgstat']}.",
        f"Maximum absolute difference in semivariance: {worst:.3e} (tolerance {TOLERANCE:.0e}). Result: {result['status']}.",
        "", "Our semivariance, first five bins: " + ", ".join(f"{v:.6f}" for v in ours_gamma[:5]),
        "scikit-gstat semivariance, first five bins: " + ", ".join(f"{v:.6f}" for v in skg[:5]),
        "", "The lateral basis is not compared directly, because scikit-gstat cannot restrict pairs to a relative-depth band.",
        "Both use the same estimator, so the agreement is evidence for the pair counting and the binning.",
    ]
    (O2_REPORT_DIR / "INDEPENDENT_CHECK.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kambale.objective_2.independent_check")
    parser.add_argument("--site", default=None, help="directory holding the scikit-gstat installation")
    args = parser.parse_args(argv)
    result = run(args.site)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in ("PASS", "NOT_RUN") else 1


if __name__ == "__main__":
    sys.exit(main())

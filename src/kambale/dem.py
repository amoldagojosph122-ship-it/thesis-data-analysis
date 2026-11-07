"""Provisional collar elevations from a digital elevation model (DEM).

A DEM is used only because the workbook has no surveyed collar RL. The DEM file is checked against its
SHA-256 before use. Each collar is sampled by bilinear interpolation after its UTM coordinates are
transformed to WGS 84. The values are PROVISIONAL and are stored apart from the surveyed RL field.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from pyproj import Transformer

from kambale.config import CONFIG_DIR, PROJECT_ROOT

GEOTIFF_PIXEL_SCALE = 33550  # ModelPixelScaleTag
GEOTIFF_TIEPOINT = 33922     # ModelTiepointTag


def load_config(path: Path = CONFIG_DIR / "dem.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_geotiff(path: Path) -> tuple[np.ndarray, float, float, float]:
    """Elevation grid, and (x0, y0, pixel size in degrees): the north-west corner of pixel (0, 0)."""
    with Image.open(path) as im:
        scale = im.tag_v2[GEOTIFF_PIXEL_SCALE]
        tie = im.tag_v2[GEOTIFF_TIEPOINT]
        grid = np.asarray(im, dtype=np.float64).copy()
    if abs(scale[0] - scale[1]) > 1e-12:
        raise ValueError("only square pixels are supported")
    return grid, float(tie[3]), float(tie[4]), float(scale[0])


def sample_bilinear(grid: np.ndarray, x0: float, y0: float, pixel: float, lon: float, lat: float) -> float:
    """Bilinear value at a geographic position. Pixel centres sit half a pixel inside the corner (PixelIsArea)."""
    col = (lon - x0) / pixel - 0.5
    row = (y0 - lat) / pixel - 0.5
    c0, r0 = math.floor(col), math.floor(row)
    if c0 < 0 or r0 < 0 or c0 + 1 >= grid.shape[1] or r0 + 1 >= grid.shape[0]:
        raise ValueError(f"position {lon:.6f}, {lat:.6f} is outside the DEM")
    dc, dr = col - c0, row - r0
    top = grid[r0, c0] * (1 - dc) + grid[r0, c0 + 1] * dc
    bottom = grid[r0 + 1, c0] * (1 - dc) + grid[r0 + 1, c0 + 1] * dc
    value = top * (1 - dr) + bottom * dr
    if not math.isfinite(value):
        raise ValueError(f"no DEM value at {lon:.6f}, {lat:.6f}")
    return float(value)


def collar_elevations(collars, config: dict) -> dict[str, float]:
    """Provisional elevation (m) for each collar. Each collar needs hole_id, utm_easting_m and utm_northing_m."""
    path = PROJECT_ROOT / config["file"]
    if sha256_file(path) != config["sha256"]:
        raise ValueError(f"DEM file does not match config/dem.yaml: {path}")
    grid, x0, y0, pixel = read_geotiff(path)
    transform = Transformer.from_crs(config["crs_projected"], config["crs_geographic"], always_xy=True)
    elevations = {}
    for c in collars:
        lon, lat = transform.transform(c["utm_easting_m"], c["utm_northing_m"])
        elevations[c["hole_id"]] = round(sample_bilinear(grid, x0, y0, pixel, lon, lat), 2)
    return elevations

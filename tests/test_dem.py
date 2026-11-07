"""Provisional DEM elevations: bilinear sampling, the file check, and the downloaded tile in data/dem."""

import numpy as np
import pytest

from kambale import dem
from kambale.config import PROJECT_ROOT

GRID = np.array([[0.0, 1.0, 2.0],
                 [10.0, 11.0, 12.0],
                 [20.0, 21.0, 22.0]])


def test_a_pixel_centre_returns_its_cell_value():
    # North-west corner at (0, 0) with 1-degree cells, so the centre of cell (row 1, column 1) is (1.5, -1.5).
    assert dem.sample_bilinear(GRID, 0.0, 0.0, 1.0, 1.5, -1.5) == 11.0


def test_a_point_between_four_centres_takes_their_mean():
    assert dem.sample_bilinear(GRID, 0.0, 0.0, 1.0, 1.0, -1.0) == pytest.approx(5.5)


def test_a_point_outside_the_grid_is_refused():
    with pytest.raises(ValueError, match="outside the DEM"):
        dem.sample_bilinear(GRID, 0.0, 0.0, 1.0, 2.6, -1.0)


def test_a_dem_file_that_does_not_match_the_config_is_refused(tmp_path):
    path = tmp_path / "not_the_dem.tif"
    path.write_bytes(b"not a DEM")
    config = {"file": str(path), "sha256": "0" * 64, "crs_projected": "EPSG:32630", "crs_geographic": "EPSG:4326"}
    with pytest.raises(ValueError, match="does not match"):
        dem.collar_elevations([{"hole_id": "H1", "utm_easting_m": 500000.0, "utm_northing_m": 1000000.0}], config)


def test_the_downloaded_tile_matches_the_hash_and_size_recorded_in_the_config():
    config = dem.load_config()
    path = PROJECT_ROOT / config["file"]
    assert path.stat().st_size == config["file_bytes"]
    assert dem.sha256_file(path) == config["sha256"]


def test_the_tile_has_the_declared_extent_and_cell_size():
    config = dem.load_config()
    grid, x0, y0, pixel = dem.read_geotiff(PROJECT_ROOT / config["file"])
    assert grid.shape == (3600, 3600)
    assert (x0, y0) == (-3.0, 11.0)
    assert pixel == pytest.approx(1 / 3600)

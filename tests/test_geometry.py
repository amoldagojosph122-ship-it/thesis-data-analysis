"""Straight-hole geometry unit cases (cardinal directions, dips, null absolute elevation)."""

import math
import sqlite3

import pytest

from kambale.geometry import assign_drill_lines, straight_hole_offsets


@pytest.mark.parametrize("azimuth, expected_e, expected_n", [
    (0.0, 0.0, 1.0),      # north
    (90.0, 1.0, 0.0),     # east
    (180.0, 0.0, -1.0),   # south
    (270.0, -1.0, 0.0),   # west
])
def test_cardinal_azimuths_follow_sin_and_cos(azimuth, expected_e, expected_n):
    vertical = straight_hole_offsets(10.0, -90.0, azimuth)
    assert vertical.delta_e == pytest.approx(0.0, abs=1e-9)
    assert vertical.delta_n == pytest.approx(0.0, abs=1e-9)
    assert vertical.delta_z == pytest.approx(-10.0)
    flat = straight_hole_offsets(10.0, -0.0001, azimuth)
    assert flat.delta_e == pytest.approx(10.0 * expected_e, abs=1e-3)
    assert flat.delta_n == pytest.approx(10.0 * expected_n, abs=1e-3)


def test_dip_minus_60_east_matches_hand_calculation():
    off = straight_hole_offsets(10.5, -60.0, 90.0)
    assert off.delta_e == pytest.approx(10.5 * math.cos(math.radians(-60)) * math.sin(math.radians(90)), abs=1e-4)
    assert off.delta_e == pytest.approx(5.25, abs=1e-4)
    assert off.delta_n == pytest.approx(0.0, abs=1e-4)
    assert off.delta_z == pytest.approx(10.5 * math.sin(math.radians(-60)), abs=1e-4)


def test_negative_dip_gives_negative_z():
    off = straight_hole_offsets(4.0, -45.0, 0.0)
    assert off.delta_z < 0
    assert off.delta_n > 0


def test_out_of_convention_inputs_are_refused():
    with pytest.raises(ValueError):
        straight_hole_offsets(1.0, 10.0, 90.0)
    with pytest.raises(ValueError):
        straight_hole_offsets(1.0, -60.0, 360.0)


def test_drill_lines_group_by_exact_northing():
    collars = [{"hole_id": "A", "northing_alt_m": 100.0}, {"hole_id": "B", "northing_alt_m": 100.0},
               {"hole_id": "C", "northing_alt_m": 200.0}]
    lines = assign_drill_lines(collars)
    assert lines["A"]["line_code"] == lines["B"]["line_code"] == "NOM_N100"
    assert lines["C"]["line_code"] == "NOM_N200"


def test_absolute_elevation_is_never_populated(built_db):
    conn = sqlite3.connect(built_db)
    try:
        non_null = conn.execute("SELECT COUNT(*) FROM interval_coordinates WHERE z_absolute_m IS NOT NULL").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM interval_coordinates").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM elevation_sources WHERE status = 'APPROVED'").fetchone()[0]
    finally:
        conn.close()
    assert total == 1910
    assert non_null == 0
    assert approved == 0

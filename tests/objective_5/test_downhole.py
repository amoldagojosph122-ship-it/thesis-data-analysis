"""Down-hole variogram parameter check and the parsing of the configured experiment reference."""

import pytest

from kambale.objective_5.config import StopError
from kambale.objective_5.importer import check_downhole, parse_downhole_experiment

EXPECTED = {"model": "exponential", "nugget": 0.012760, "structured_sill": 0.213132, "practical_range_m": 23.5297}


def _found(**kw):
    base = {"model": "exponential", "nugget": 0.0127604, "structured_sill": 0.2131319, "practical_range_m": 23.52968}
    base.update(kw)
    return base


def test_matching_parameters_pass_and_report_worst_difference():
    worst = check_downhole(_found(), EXPECTED, tolerance=1e-4)
    assert worst < 1e-4


def test_parameter_outside_tolerance_raises_stop():
    with pytest.raises(StopError):
        check_downhole(_found(nugget=0.0130), EXPECTED, tolerance=1e-4)


def test_model_name_mismatch_raises_stop():
    with pytest.raises(StopError):
        check_downhole(_found(model="spherical"), EXPECTED, tolerance=1e-4)


def test_range_difference_just_inside_tolerance_passes():
    check_downhole(_found(practical_range_m=23.5297 + 9e-5), EXPECTED, tolerance=1e-4)


def test_experiment_reference_is_parsed():
    assert parse_downhole_experiment("DOWNHOLE_WITHIN, config O2-CFG-2026.11.05-4") == (
        "DOWNHOLE_WITHIN", "O2-CFG-2026.11.05-4")
    with pytest.raises(StopError):
        parse_downhole_experiment("not a reference")

"""Power labels, pair status and the predeclared improvement rule on synthetic values (no database)."""

import pytest

from kambale.objective_4.decision import comparator_status, improvement_status
from kambale.objective_4.evaluation import power_label


def test_resolved_when_interval_excludes_zero_on_either_side():
    assert power_label(0.01, 0.03, False) == ("RESOLVED", None)
    assert power_label(-0.03, -0.01, False) == ("RESOLVED", None)


def test_unresolved_reports_half_width_as_smallest_detectable_difference():
    label, half = power_label(-0.02, 0.01, False)
    assert label == "UNRESOLVED"
    assert half == pytest.approx(0.015)


def test_identical_has_no_interval_even_if_bounds_given():
    assert power_label(None, None, True) == ("IDENTICAL", None)
    assert power_label(-0.1, 0.1, True) == ("IDENTICAL", None)


def test_missing_interval_is_not_estimable():
    assert power_label(None, None, False) == ("NOT_ESTIMABLE", None)


def test_supported_requires_every_condition():
    status, _ = improvement_status(-0.01, -0.02, -0.001, 4, 4, True, True, True)
    assert status == "SUPPORTED_IMPROVEMENT"


@pytest.mark.parametrize("kwargs", [
    dict(hi=0.001),                       # interval includes zero
    dict(folds_better=3),                 # fold consistency below four of five
    dict(calibration_ok=False),
    dict(discrimination_ok=False),
    dict(coverage_ok=False),
])
def test_any_failed_condition_is_not_supported(kwargs):
    base = dict(point=-0.01, lo=-0.02, hi=-0.001, folds_better=4, fold_min=4, calibration_ok=True,
                discrimination_ok=True, coverage_ok=True)
    base.update(kwargs)
    status, _ = improvement_status(base["point"], base["lo"], base["hi"], base["folds_better"], base["fold_min"],
                                   base["calibration_ok"], base["discrimination_ok"], base["coverage_ok"])
    assert status == "INCONCLUSIVE"


def test_non_negative_point_is_no_improvement():
    assert improvement_status(0.0, -0.1, 0.1, 5, 4, True, True, True)[0] == "NO_IMPROVEMENT"
    assert improvement_status(0.02, 0.01, 0.03, 5, 4, True, True, True)[0] == "NO_IMPROVEMENT"


def test_comparator_status_resolved_only_when_interval_above_zero():
    assert comparator_status(0.001, 0.02)[0] == "NO_IMPROVEMENT"
    assert comparator_status(-0.001, 0.02)[0] == "INCONCLUSIVE"

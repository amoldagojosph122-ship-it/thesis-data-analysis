"""Entropy in bits and the classification truth table."""

import numpy as np
import pytest

from kambale.objective_5.classify import classify_arrays
from kambale.objective_5.config import CLASS_ABSENT, CLASS_NO_SUPPORT, CLASS_PRESENT, CLASS_UNCERTAIN, EXTRAPOLATION, \
    INTERPOLATION, NO_SUPPORT
from kambale.objective_5.grid import DEPTH_EXTRAPOLATED, SUPPORTED, entropy_bits


def test_entropy_half_is_one_bit():
    assert entropy_bits([0.5])[0] == pytest.approx(1.0, abs=1e-15)


def test_entropy_is_zero_at_certainty_and_symmetric():
    h = entropy_bits([0.0, 1.0, 0.2, 0.8])
    assert h[0] == 0.0 and h[1] == 0.0
    assert h[2] == pytest.approx(h[3], abs=1e-15)
    assert h[2] == pytest.approx(0.7219280948873623, abs=1e-12)


TRUTH = [
    # p_lo, p_hi, disagreement, zone, depth support, expected class   (threshold 0.5, limit 0.2)
    (0.60, 0.80, 0.05, INTERPOLATION, SUPPORTED, CLASS_PRESENT),
    (0.50, 0.90, 0.05, INTERPOLATION, SUPPORTED, CLASS_PRESENT),        # p_lo equal to the threshold
    (0.30, 0.49, 0.05, INTERPOLATION, SUPPORTED, CLASS_ABSENT),
    (0.10, 0.50, 0.05, INTERPOLATION, SUPPORTED, CLASS_UNCERTAIN),      # p_hi equal to the threshold is not absent
    (0.60, 0.80, 0.20, INTERPOLATION, SUPPORTED, CLASS_UNCERTAIN),      # disagreement equal to the limit
    (0.30, 0.49, 0.25, INTERPOLATION, SUPPORTED, CLASS_UNCERTAIN),
    (0.60, 0.80, 0.05, EXTRAPOLATION, DEPTH_EXTRAPOLATED, CLASS_UNCERTAIN),  # depth-extrapolated cannot be confident
    (0.10, 0.20, 0.05, EXTRAPOLATION, DEPTH_EXTRAPOLATED, CLASS_UNCERTAIN),
    (0.10, 0.20, 0.05, EXTRAPOLATION, SUPPORTED, CLASS_ABSENT),
    (np.nan, np.nan, np.nan, NO_SUPPORT, SUPPORTED, CLASS_NO_SUPPORT),
]


@pytest.mark.parametrize("p_lo,p_hi,dis,zone,depth,expected", TRUTH)
def test_classification_truth_table(p_lo, p_hi, dis, zone, depth, expected):
    out = classify_arrays([p_lo], [p_hi], [dis], [zone], [depth], threshold=0.5, limit=0.2)
    assert out[0] == expected


def test_threshold_is_a_parameter():
    out = classify_arrays([0.29], [0.35], [0.0], [INTERPOLATION], [SUPPORTED], threshold=0.28, limit=0.2)
    assert out[0] == CLASS_PRESENT
    out = classify_arrays([0.25], [0.35], [0.0], [INTERPOLATION], [SUPPORTED], threshold=0.5, limit=0.2)
    assert out[0] == CLASS_ABSENT

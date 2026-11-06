"""Identity rule on synthetic probabilities (no database)."""

import numpy as np

from kambale.objective_4.importer import identity_records


def _probs(vectors):
    return {m: {i: float(p) for i, p in enumerate(v)} for m, v in vectors.items()}


def test_identical_pair_is_flagged_and_reference_is_earlier_model():
    probs = _probs({"A": [0.1, 0.4, 0.7], "B": [0.1, 0.4, 0.7], "C": [0.2, 0.3, 0.9]})
    pairs, refs = identity_records(["A", "B", "C"], probs, [0, 1, 2])
    by = {(p["model_a"], p["model_b"]): p for p in pairs}
    assert by[("A", "B")]["identical"] == 1
    assert by[("A", "C")]["identical"] == 0
    assert refs == {"A": None, "B": "A", "C": None}


def test_nearest_earlier_identical_model_is_the_reference():
    # C equals both A and B, so the nearest earlier identical model (B) is the reference.
    probs = _probs({"A": [0.1, 0.5], "B": [0.2, 0.6], "C": [0.2, 0.6]})
    pairs, refs = identity_records(["A", "B", "C"], probs, [0, 1])
    assert refs["C"] == "B"
    assert {(p["model_a"], p["model_b"]) for p in pairs if p["identical"]} == {("B", "C")}


def test_tolerance_is_applied():
    probs = _probs({"A": [0.1, 0.5], "B": [0.1 + 5e-13, 0.5]})
    _, refs = identity_records(["A", "B"], probs, [0, 1])
    assert refs["B"] == "A"
    probs = _probs({"A": [0.1, 0.5], "B": [0.1 + 1e-9, 0.5]})
    _, refs = identity_records(["A", "B"], probs, [0, 1])
    assert refs["B"] is None


def test_missing_common_observations_are_not_identical():
    probs = _probs({"A": [0.1], "B": [0.1]})
    pairs, refs = identity_records(["A", "B"], {"A": {0: 0.1}, "B": {}}, [0], )
    assert refs["B"] is None and pairs[0]["max_abs_difference"] is None

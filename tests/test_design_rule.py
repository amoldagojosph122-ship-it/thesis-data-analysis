"""Target B as set out in ThesisDesign section 8.2 (DESIGN_8_2_v1): states and the AMBIGUOUS state."""

import pytest

from kambale.labels import RuleDef, evidence, rock_status, rule_label

LEGEND = {"Sgs", "Sbs", "Rso", "Fsc"}
DESIGN = RuleDef("DESIGN_8_2_v1", "1.0.0", "RECONCILED", "DESIGN_8_2", None, "test", "x", 0)


def interval(code="Sbs", alt1=None, alt2=None, comment=None):
    return {"rock_code_raw": code, "alt_min1_code": alt1, "alt_min2_code": alt2, "comment_raw": comment}


def state(code, alt1, comment, rule=DESIGN):
    ev = evidence(interval(code, alt1=alt1, comment=comment), rock_status(code, LEGEND))
    return rule_label(rule, ev)


@pytest.mark.parametrize("code, alt1, comment, expected", [
    ("Sgs", "gr", "Sedimentary graphitic schist", (1, "POSITIVE")),
    ("Sgs", None, "Sedimentary graphitic schist", (1, "POSITIVE")),   # a blank graphite field is not counted against graphite
    ("Sgs", "gr", None, (1, "POSITIVE")),                              # a blank comment is allowed for Sgs
    ("Sgs", None, None, (None, "AMBIGUOUS")),                          # one indicator only
    ("Sgs", "gr", "Sedimentary biotite schist", (None, "AMBIGUOUS")),  # the comment names another lithology
    ("Sbs", "gr", "Sedimentary graphitic schist", (None, "AMBIGUOUS")),  # the code disagrees with the evidence
    ("Sbs", None, "Sedimentary biotite schist", (0, "NEGATIVE")),
    ("Sbs", None, None, (None, "UNRESOLVED")),                          # a non-Sgs interval with a blank comment
])
def test_design_8_2_states(code, alt1, comment, expected):
    assert state(code, alt1, comment) == expected


def test_design_8_2_unsupported_and_missing_codes_are_unresolved():
    for code in ("fsc", None):
        assert state(code, "gr", "graphitic schist") == (None, "UNRESOLVED")


def test_only_the_design_rule_produces_ambiguous():
    comments = (None, "Sedimentary graphitic schist", "Sedimentary biotite schist")
    rules = (RuleDef("S", "1", "STRICT", "STRICT_CODE", None, "t", "x"),
             RuleDef("M1", "1", "TEST", "MIN_POSITIVE", 1, "t", "x"),
             RuleDef("M2", "1", "TEST", "MIN_POSITIVE", 2, "t", "x"),
             RuleDef("M3", "1", "TEST", "MIN_POSITIVE", 3, "t", "x"))
    for code in ("Sgs", "Sbs", "fsc"):
        for alt1 in (None, "gr"):
            for comment in comments:
                for rule in rules:
                    assert state(code, alt1, comment, rule)[1] != "AMBIGUOUS"

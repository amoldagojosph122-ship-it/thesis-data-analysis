"""Label evidence and candidate rule logic (pure functions), plus reconciliation with a direct workbook recount."""

import sys
from pathlib import Path

import pytest

from kambale.labels import RuleDef, evidence, rock_status, rule_label

LEGEND = {"Sgs", "Sbs", "Rso", "Fsc"}


def interval(code="Sbs", alt1=None, alt2=None, comment=None):
    return {"rock_code_raw": code, "alt_min1_code": alt1, "alt_min2_code": alt2, "comment_raw": comment}


def rule(rule_id, logic, k=None):
    return RuleDef(rule_id, "1.0.0", "TEST", logic, k, "test", "x")


@pytest.mark.parametrize("comment, graphitic, trace, term", [
    ("Sedimentary graphitic schist", 1, 0, "graphitic"),
    ("Sedimentary biotite schist with traces of graphite", 1, 1, "graphite"),
    ("Sedimentary biotite schist", 0, 0, None),
    ("quartz mica schist", 0, 0, None),
])
def test_comment_text_evidence(comment, graphitic, trace, term):
    ev = evidence(interval("Sbs", comment=comment), rock_status("Sbs", LEGEND))
    assert ev["comment_graphitic"] == graphitic
    assert ev["comment_trace_qualified"] == trace
    assert ev["comment_term"] == term


def test_unsupported_code_is_unresolved_for_every_rule():
    ev = evidence(interval("fsc", alt1="gr", comment="graphitic schist"), rock_status("fsc", LEGEND))
    assert ev["rock_code_status"] == "UNSUPPORTED"
    assert ev["is_sgs"] is None
    assert ev["label_review_status"] == "UNRESOLVED_CODE"
    for logic, k in (("STRICT_CODE", None), ("MIN_POSITIVE", 1), ("MIN_POSITIVE", 2)):
        assert rule_label(rule("R", logic, k), ev) == (None, "UNRESOLVED")


def test_missing_code_is_missing_not_negative():
    assert rock_status(None, LEGEND) == "MISSING"


def test_strict_rule_maps_sgs_and_other_codes():
    sgs = evidence(interval("Sgs", comment="Sedimentary graphitic schist"), "VALID")
    sbs = evidence(interval("Sbs", comment="Sedimentary biotite schist"), "VALID")
    assert rule_label(rule("S", "STRICT_CODE"), sgs) == (1, "POSITIVE")
    assert rule_label(rule("S", "STRICT_CODE"), sbs) == (0, "NEGATIVE")


def test_two_of_three_requires_two_positives_and_zero_for_negative():
    one = evidence(interval("Sgs", alt1=None, comment="biotite schist"), "VALID")
    three = evidence(interval("Sgs", alt1="gr", comment="graphitic schist"), "VALID")
    none = evidence(interval("Sbs", comment="biotite schist"), "VALID")
    r2 = rule("R2", "MIN_POSITIVE", 2)
    assert rule_label(r2, one) == (None, "UNRESOLVED")
    assert rule_label(r2, three) == (1, "POSITIVE")
    assert rule_label(r2, none) == (0, "NEGATIVE")


def test_blank_comment_prevents_negative_label():
    ev = evidence(interval("Sbs", comment=None), "VALID")
    assert ev["comment_present"] == 0
    assert rule_label(rule("R2", "MIN_POSITIVE", 2), ev) == (None, "UNRESOLVED")


def test_conflict_flag_is_mixed_evidence():
    ev = evidence(interval("Sbs", alt1="gr", comment="Sedimentary biotite schist with traces of graphite"), "VALID")
    assert ev["positive_indicators"] == 2
    assert ev["label_conflict"] == 1
    assert ev["label_review_status"] == "CONFLICT_REVIEW_REQUIRED"


def notrace_rule():
    return RuleDef("RECON_2OF3_NOTRACE_v1", "1.0.0", "SENSITIVITY", "MIN_POSITIVE", 2, "test", "x",
                   exclude_trace_comments=True)


def test_trace_flag_requires_graphite_in_the_same_phrase():
    flag = lambda text: evidence(interval("Sbs", comment=text), "VALID")["comment_trace_qualified"]  # noqa: E731
    assert flag("Sedimentary graphitic schist with traces of epidot") == 0
    assert flag("Sedimentary biotite schist with traces of graphite") == 1
    assert flag("Sedimentary biotite schist,small traces of graphite") == 1


def test_trace_excluded_rule_makes_trace_only_comment_negative():
    ev = evidence(interval("Sbs", comment="Sedimentary biotite schist with traces of graphite"), "VALID")
    assert rule_label(rule("R2", "MIN_POSITIVE", 2), ev) == (None, "UNRESOLVED")
    assert rule_label(notrace_rule(), ev) == (0, "NEGATIVE")


def test_trace_excluded_rule_drops_positive_that_relies_on_trace():
    ev = evidence(interval("Sbs", alt1="gr", comment="Sedimentary biotite schist with traces of graphite"), "VALID")
    assert rule_label(rule("R2", "MIN_POSITIVE", 2), ev) == (1, "POSITIVE")
    assert rule_label(notrace_rule(), ev) == (None, "UNRESOLVED")


def test_trace_excluded_rule_keeps_graphitic_code_with_trace_comment_positive():
    ev = evidence(interval("Sgs", alt1="gr", comment="Sedimentary graphitic schist with traces of graphite"), "VALID")
    assert rule_label(notrace_rule(), ev) == (1, "POSITIVE")


def test_evidence_distribution_reconciles_with_workbook_recount():
    """Recount the indicators directly from the workbook. Compare with ThesisDesign.docx (reconciliation only)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from kambale.config import RAW_COPY_PATH
    from kambale.curate import curate
    from kambale.source import read_workbook

    data = curate(read_workbook(RAW_COPY_PATH))
    legend = {c["code"] for c in data.codes if c["code_domain"] == "RockType"}
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for i in data.intervals:
        ev = evidence(i, rock_status(i["rock_code_raw"], legend))
        counts[ev["positive_indicators"]] += 1
    # Six comments (decision D15): rows 251-253 add a third positive indicator, and rows 505-507 add none.
    # Rock codes from the original log (decision D19): the blank code on row 177 is Sgs with a graphitic comment.
    assert counts == {3: 480, 2: 83, 1: 43, 0: 1304}

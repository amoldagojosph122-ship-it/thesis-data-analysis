import pytest
from openpyxl import load_workbook

from kambale.lithology import (
    DEFAULT_WORKBOOK,
    NAME_PATTERN,
    SUBORDINATE_MINERALS,
    classify,
    lithology_of,
    normalise,
    read_intervals,
    read_legend,
    refine,
)

LEGEND = {
    "Fpg": "pegmatite",
    "Fsc": "Felsic schist",
    "Lcs": "Clay - saprolitic",
    "Rso": "Soil/Loam general",
    "Sbs": "meta-sediment biotite schist",
    "Sgs": "meta-sediment graphite schist",
    "Sqs": "Quartz sericite schist/rock",
    "Ssu": "Sedimentary rock undifferentiated",
}


def test_normalise_removes_depth_and_fixes_spelling():
    assert normalise("Sedimemtary biotite schist,with quartz present @ 24-26m") == \
        "sedimentary biotite schist with quartz present"


def test_normalise_drops_trailing_with():
    assert normalise("Saprolitic clay with") == "saprolitic clay"


def test_lithology_is_read_from_comment():
    assert lithology_of("sedimentary biotite schist with quartz present") == "Sbs"
    assert lithology_of("quartz sericite schist") == "Sqs"
    assert lithology_of("felsic pegmatites") == "Fpg"
    assert lithology_of("traces of epidote") is None


def test_refined_code_puts_subordinate_mineral_first_and_rock_last():
    assert refine("Sbs", "qz") == "Sqzbs"
    assert refine("Fpg", "ep") == "Feppg"
    assert refine("Sgs", "ep") == "Sepgs"
    assert refine("Lcs", "ep") == "Lepcs"


def test_trace_epidote_is_refined_firmly():
    res = classify("Fpg", LEGEND, "Felsic pegmatites,traces of epidot")
    assert res["status"] == "REFINED"
    assert res["refined"] == "Feppg"
    assert res["base"] == "Fpg"


def test_quartz_present_is_refined_as_subordinate_under_the_accepted_convention():
    res = classify("Sbs", LEGEND, "Sedimentary biotite schist with quartz present")
    assert res["status"] == "REFINED"
    assert res["refined"] == "Sqzbs"
    assert "accepted convention" in res["notes"]


def test_graphite_is_never_encoded():
    res = classify("Sbs", LEGEND, "Sedimentary biotite schist with traces of graphite")
    assert res["status"] == "UNCHANGED"
    assert res["refined"] == "Sbs"
    assert "not encoded" in res["notes"]


def test_quartz_and_graphite_keeps_quartz_only_in_the_code():
    res = classify("Sbs", LEGEND, "Sedimentary biotite schist with quartz present and graphite")
    assert res["refined"] == "Sqzbs"
    assert "graphite named" in res["notes"]


def test_conflicting_lithology_is_kept_and_not_renamed():
    res = classify("Sgs", LEGEND, "Sedimentary biotite schist")
    assert res["status"] == "CONFLICT_REVIEW"
    assert res["refined"] == "Sgs"


def test_quartz_schist_already_names_quartz():
    res = classify("Sqs", LEGEND, "Quartz sericite schist")
    assert res["status"] == "UNCHANGED"
    assert res["refined"] == "Sqs"


def test_quartz_vein_is_not_a_matrix_mineral():
    res = classify("Lcs", LEGEND, "Saprolitic clay with glassy quartz vein present")
    assert res["status"] == "NOT_REFINED_VEIN"
    assert res["refined"] == "Lcs"


def test_blank_comment_stands_on_code_alone():
    res = classify("Sgs", LEGEND, "")
    assert res["status"] == "UNCHANGED_NO_COMMENT"
    assert res["refined"] == "Sgs"


def test_unsupported_code_stays_unresolved_and_case_variant_is_noted():
    res = classify("fsc", LEGEND, "quartz mica schist")
    assert res["status"] == "UNRESOLVED_UNSUPPORTED_CODE"
    assert res["base"] == ""
    assert "case differs" in res["notes"]


def test_missing_code_stays_unresolved():
    res = classify(None, LEGEND, "Sedimentary graphitic schist")
    assert res["status"] == "UNRESOLVED_MISSING_CODE"
    assert res["refined"] == ""


def test_two_matrix_minerals_are_sent_for_review():
    res = classify("Sbs", LEGEND, "Sedimentary biotite schist with quartz present, traces of epidot")
    assert res["status"] == "REVIEW_MULTIPLE_MODIFIERS"
    assert res["refined"] == "Sbs"


def split_name(name):
    """The tokens after the group letter: subordinate minerals, then the principal rock."""
    body = name[1:]
    return [body[i:i + 2] for i in range(0, len(body), 2)]


def test_name_has_no_hyphens_and_one_capital_group_letter():
    for name in ["Sbs", "Sqzbs", "Sepbs", "Feppg", "Lepcs"]:
        assert NAME_PATTERN.fullmatch(name), name
    for name in ["S-qz-bs", "sqzbs", "SQZBS", "Sqzb", "Sqz1bs"]:
        assert not NAME_PATTERN.fullmatch(name), name


def test_only_approved_minerals_are_subordinate_and_gs_is_excluded():
    assert set(SUBORDINATE_MINERALS) == {"qz", "ep"}
    assert "gs" not in SUBORDINATE_MINERALS


@pytest.mark.parametrize("code, comment, expected", [
    ("Sbs", "Sedimentary biotite schist with quartz present", "Sqzbs"),
    ("Sbs", "Sedimentary biotite schist with traces of epidote", "Sepbs"),
    ("Fpg", "Felsic pegmatites,traces of epidot", "Feppg"),
    ("Sgs", "Sedimentary graphitic schist with quartz present", "Sqzgs"),
    ("Lcs", "Saprolitic clay, traces of epidot @11m", "Lepcs"),
    ("Sqs", "Quartz sericite schist,traces of epidot @14m", "Sepqs"),
])
def test_refined_name_is_group_then_minerals_then_principal_rock(code, comment, expected):
    res = classify(code, LEGEND, comment)
    assert res["refined"] == expected
    assert NAME_PATTERN.fullmatch(expected)
    tokens = split_name(expected)
    assert expected[0] == code[0]
    assert tokens[-1] == code[1:]
    assert all(t in SUBORDINATE_MINERALS for t in tokens[:-1])


def test_subordinate_tokens_are_workbook_mineral_codes():
    if not DEFAULT_WORKBOOK.exists():
        pytest.skip("verified workbook copy not present")
    wb = load_workbook(DEFAULT_WORKBOOK, read_only=True, data_only=True)
    minerals = {str(r[2]) for r in wb["Logging Legend"].iter_rows(values_only=True) if r[1] == "RTMineral"}
    wb.close()
    assert set(SUBORDINATE_MINERALS) <= minerals


def test_every_refined_name_in_the_workbook_passes_the_format_check():
    if not DEFAULT_WORKBOOK.exists():
        pytest.skip("verified workbook copy not present")
    wb = load_workbook(DEFAULT_WORKBOOK, read_only=True, data_only=True)
    legend = read_legend(wb)
    intervals = read_intervals(wb)
    wb.close()
    checked = 0
    for _hole, _from, _to, code, raw in intervals:
        res = classify(code, legend, raw)
        if res["status"] == "REFINED_GENERAL":
            assert res["refined"] in legend and NAME_PATTERN.fullmatch(res["refined"]), res["refined"]
            continue
        if res["status"] != "REFINED":
            continue
        name = res["refined"]
        checked += 1
        assert NAME_PATTERN.fullmatch(name), name
        tokens = split_name(name)
        assert tokens[-1] == code[1:], name
        assert all(t in SUBORDINATE_MINERALS for t in tokens[:-1]), name
    assert checked > 0


def test_transported_gravels_on_rso_maps_to_rgv():
    res = classify("Rso", LEGEND, "Transported gravels")
    assert res["status"] == "REFINED_GENERAL"
    assert res["refined"] == "Rgv"
    assert res["base"] == "Rso"


def test_transported_gravels_on_saprolitic_clay_stays_a_conflict():
    res = classify("Lcs", LEGEND, "Transported gravels")
    assert res["status"] == "CONFLICT_REVIEW"
    assert res["refined"] == "Lcs"

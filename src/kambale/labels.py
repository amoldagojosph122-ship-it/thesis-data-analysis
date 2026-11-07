"""Graphitic label evidence and candidate rules (pure functions, no database access).

Evidence fields are logged indicators. They are not independent laboratory confirmations and are not
graphite grade. Candidate rules return UNRESOLVED whenever the rock code is missing or unsupported.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

GRAPHIT_RE = re.compile(r"graphit", re.IGNORECASE)
GRAPHITIC_RE = re.compile(r"graphitic", re.IGNORECASE)
GRAPHITE_RE = re.compile(r"graphite", re.IGNORECASE)
# "trace" must qualify graphite within the same phrase: "traces of graphite", "small traces of graphite".
# "graphitic schist with traces of epidot" is NOT a trace-qualified graphite mention.
TRACE_GRAPHITE_RE = re.compile(r"\btrace[s]?\b[^,;@]{0,30}?\bgraphit", re.IGNORECASE)
GRAPHITE_MINERAL_CODE = "gr"
SGS_CODE = "Sgs"


@dataclass(frozen=True)
class RuleDef:
    rule_id: str
    rule_version: str
    family: str
    logic: str                # STRICT_CODE, MIN_POSITIVE or DESIGN_8_2
    min_positive: int | None
    description: str
    definition_sha256: str
    exclude_trace_comments: bool = False  # sensitivity: trace-qualified comments are not positive evidence


def load_rules(path: Path) -> tuple[str, list[RuleDef]]:
    """Load candidate rules from YAML. The definition hash is taken over canonical JSON of each rule."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = []
    for item in document["rules"]:
        canonical = json.dumps(item, sort_keys=True, ensure_ascii=False)
        rules.append(RuleDef(
            rule_id=item["rule_id"],
            rule_version=str(item["rule_version"]),
            family=item["family"],
            logic=item["logic"],
            min_positive=item.get("min_positive"),
            description=" ".join(str(item["description"]).split()),
            definition_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            exclude_trace_comments=bool(item.get("exclude_trace_comments", False)),
        ))
    if len({r.rule_id for r in rules}) != len(rules):
        raise ValueError("duplicate rule_id in label_rules.yaml")
    return str(document["label_rule_set_version"]), rules


def rock_status(code: str | None, legend_rock_codes: set[str]) -> str:
    if code is None:
        return "MISSING"
    return "VALID" if code in legend_rock_codes else "UNSUPPORTED"


def evidence(interval: dict, status: str) -> dict:
    """Evidence for one interval. `interval` is a curated logging record (see curate.py)."""
    code = interval["rock_code_raw"]
    is_sgs = (1 if code == SGS_CODE else 0) if status == "VALID" else None
    has_gr = 1 if GRAPHITE_MINERAL_CODE in (interval["alt_min1_code"], interval["alt_min2_code"]) else 0
    comment = interval["comment_raw"]
    comment_present = 1 if comment is not None and comment.strip() != "" else 0
    comment_graphitic = 1 if comment_present and GRAPHIT_RE.search(comment) else 0
    comment_trace = 1 if comment_graphitic and TRACE_GRAPHITE_RE.search(comment) else 0
    if comment_graphitic and GRAPHITIC_RE.search(comment):
        term = "graphitic"
    elif comment_graphitic and GRAPHITE_RE.search(comment):
        term = "graphite"
    else:
        term = None

    positives = [is_sgs == 1, has_gr == 1, comment_graphitic == 1]
    positives_no_trace = [is_sgs == 1, has_gr == 1, comment_graphitic == 1 and comment_trace == 0]
    negatives = [is_sgs == 0, has_gr == 0, comment_present == 1 and comment_graphitic == 0]
    n_pos, n_neg = sum(positives), sum(negatives)
    n_pos_no_trace = sum(positives_no_trace)

    tokens = [name for name, flag in (("SGS", is_sgs == 1), ("GR", has_gr == 1), ("CMT", comment_graphitic == 1))
              if flag]
    pattern = "+".join(tokens) if tokens else "NONE"
    if status != "VALID":
        pattern += f"|ROCK_{status}"

    conflict = 1 if (n_pos >= 1 and n_neg >= 1) else 0

    if status != "VALID":
        review = "UNRESOLVED_CODE"
    elif conflict:
        review = "CONFLICT_REVIEW_REQUIRED"
    elif n_pos == 3:
        review = "CONSISTENT_POSITIVE"
    elif n_pos == 0 and comment_present:
        review = "CONSISTENT_NEGATIVE"
    elif n_pos == 0:
        review = "UNRESOLVED_NO_COMMENT"
    else:
        review = "UNRESOLVED_PARTIAL_EVIDENCE"

    rock_text = f"rock {code}" if code is not None else "rock MISSING"
    if status == "UNSUPPORTED":
        rock_text += " (not in legend)"
    gr_text = "gr logged" if has_gr else "gr not logged"
    if comment_graphitic:
        cmt_text = f"comment mentions {term}" + (" with trace qualifier" if comment_trace else "")
    elif comment_present:
        cmt_text = "comment without graphite term"
    else:
        cmt_text = "no comment"
    rationale = f"{rock_text}; {gr_text}; {cmt_text}"

    return {
        "rock_code_status": status,
        "is_sgs": is_sgs,
        "has_gr_mineral": has_gr,
        "comment_present": comment_present,
        "comment_graphitic": comment_graphitic,
        "comment_trace_qualified": comment_trace,
        "comment_term": term,
        "positive_indicators": n_pos,
        "positive_indicators_no_trace": n_pos_no_trace,
        "negative_indicators": n_neg,
        "label_conflict": conflict,
        "evidence_pattern": pattern,
        "label_review_status": review,
        "rationale": rationale,
    }


def design_8_2(ev: dict) -> tuple[int | None, str]:
    """Target B as set out in ThesisDesign section 8.2 (the reconciled target of the review form).

    Graphitic: Sgs with at least one further indicator and no conflicting description.
    Non-graphitic: a valid non-Sgs code, no graphite indicator and a comment.
    Ambiguous: one indicator only, or the code and the other evidence disagree.
    Unresolved: a non-Sgs interval with a blank comment (missing or unsupported codes are handled by rule_label).

    A blank graphite field means "not logged", so it is not counted as evidence against graphite.
    """
    if not ev["is_sgs"] and not ev["comment_present"]:
        return None, "UNRESOLVED"
    if ev["positive_indicators"] == 0:
        return 0, "NEGATIVE"
    conflict = (not ev["is_sgs"]) or (ev["comment_present"] == 1 and ev["comment_graphitic"] == 0)
    if conflict or ev["positive_indicators"] == 1:
        return None, "AMBIGUOUS"
    return 1, "POSITIVE"


def rule_label(rule: RuleDef, ev: dict) -> tuple[int | None, str]:
    """Apply one candidate rule. Returns (label, state): POSITIVE, NEGATIVE, UNRESOLVED or AMBIGUOUS."""
    if ev["rock_code_status"] != "VALID":
        return None, "UNRESOLVED"
    if rule.logic == "STRICT_CODE":
        label = int(ev["is_sgs"])
        return label, ("POSITIVE" if label == 1 else "NEGATIVE")
    if rule.logic == "MIN_POSITIVE":
        positives = ev["positive_indicators_no_trace"] if rule.exclude_trace_comments else ev["positive_indicators"]
        if positives >= rule.min_positive:
            return 1, "POSITIVE"
        if positives == 0 and ev["comment_present"]:
            return 0, "NEGATIVE"
        return None, "UNRESOLVED"
    if rule.logic == "DESIGN_8_2":
        return design_8_2(ev)
    raise ValueError(f"unknown rule logic {rule.logic!r} for {rule.rule_id}")

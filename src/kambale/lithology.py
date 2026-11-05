"""Descriptive lithology codes refined from the logged comments.

Base codes from the logging legend are kept, and the label logic keeps using them.
A refined code adds each matrix mineral named in the comment: the subordinate
mineral code sits after the group letter and before the rock letters, so the
principal rock stays last (Sbs + quartz -> Sqzbs). Quartz is qz and epidote is ep,
the workbook's own RTMineral codes.

Graphite is never part of a refined code. It is label evidence, and encoding it
would make the graphitic label depend on the code that the label defines.

compute() is pure: it classifies intervals and never touches files or the
database. The workbook path (run) writes review files; the database build uses
compute() directly. The rules are digested by convention_sha256(), which enters
the dataset version key, so a rule change always produces a new dataset version.
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# The read-only copy in data/raw is the verified source the database was built from.
# The root workbook can be re-saved by hand, which changes its bytes but not its cells.
DEFAULT_WORKBOOK = PROJECT_ROOT / "data" / "raw" / "Kambale RAB_Collar_Sampling_Geology_2012a.xlsx"
WORKBOOK_SHA256 = "a449097f669b9a449d06acfdb31c62ccbc688936c90254a829ecade2b95dbfb6"
LITHOLOGY_CONVENTION_VERSION = "LITHO-2026.11.05"

# Spelling corrections applied before matching. Each correction is noted.
TYPO_FIXES = {
    "sedimemtary": "sedimentary",
    "biotiite": "biotite",
    "pesent": "present",
    "epidot": "epidote",
}
TYPO_RE = re.compile(r"\b(?:" + "|".join(TYPO_FIXES) + r")\b")

# Lithology named in a comment, checked in order. Each maps to a code.
LITHOLOGY_PATTERNS = [
    (re.compile(r"quartz sericite schist|sericite quartz schist"), "Sqs"),
    (re.compile(r"biotite schist"), "Sbs"),
    (re.compile(r"graphitic schist"), "Sgs"),
    (re.compile(r"felsic pegmatite"), "Fpg"),
    (re.compile(r"saprolitic clay"), "Lcs"),
    (re.compile(r"transported gravels"), "Rgv"),
    (re.compile(r"sedimentary rock undifferentiated"), "Ssu"),
    (re.compile(r"quartz mica schist"), "fsc"),
]

# Minerals already in a base code's name, so naming them again adds nothing.
ALREADY_NAMED = {"Sqs": {"quartz"}}

# Subordinate minerals allowed in a name, by workbook mineral code (RTMineral).
# 'gs' is left out because it is also the graphite-schist core in Sgs.
SUBORDINATE_MINERALS = {"qz": "quartz", "ep": "epidote"}

# A name has no hyphens: one capital group letter, then two-letter tokens, with the
# principal rock code last (Sqzbs = group S, quartz qz, biotite schist bs).
NAME_PATTERN = re.compile(r"[A-Z](?:[a-z]{2})+")

# A general code may be refined to a specific legend code that the comment names.
# Only the principal rock changes, and the logged code stays for labels.
GENERAL_TO_SPECIFIC = {"Rso": {"Rgv"}}

DEPTH_NOTE = re.compile(r"@\s*\d+(?:\s*-\s*\d+)?\s*m\b")
QUARTZ_PRESENT = re.compile(r"\bquartz present\b")
TRACE_EPIDOTE = re.compile(r"\btraces?\s+(?:of\s+)?epidote\b")
EPIDOTE = re.compile(r"\bepidote\b")
GRAPHITE = re.compile(r"\bgraphite\b")
GRAPHITE_TRACE = re.compile(r"\btraces?\b[^,;]{0,30}?\bgraphite\b")
VEIN = re.compile(r"\bvein\b")
TRAILING_WITH = re.compile(r"\bwith\s*$")
REGEXES = {"DEPTH_NOTE": DEPTH_NOTE, "QUARTZ_PRESENT": QUARTZ_PRESENT, "TRACE_EPIDOTE": TRACE_EPIDOTE,
           "EPIDOTE": EPIDOTE, "GRAPHITE": GRAPHITE, "GRAPHITE_TRACE": GRAPHITE_TRACE, "VEIN": VEIN,
           "TRAILING_WITH": TRAILING_WITH, "TYPO": TYPO_RE}

REASON = {
    "UNCHANGED": "The comment agrees with the code and names no matrix mineral, so the code stands.",
    "UNCHANGED_NO_COMMENT": "No comment. The code stands alone, so the label uses the code only.",
    "REFINED": "A matrix mineral is named and treated as subordinate, as a trace or (by the accepted convention) as present. A refined code is given; the base code stays with the label.",
    "REFINED_GENERAL": "The logged code is the general regolith code Rso, and the comment names transported gravel, which is the legend code Rgv. Rgv is the refined code; the logged code stays for labels. Chosen on 2026-11-05.",
    "CONFLICT_REVIEW": "The comment names a different lithology from the code. The code is kept and not renamed. Flagged for review.",
    "NOT_REFINED_VEIN": "The comment names a vein. A vein is a feature, not a matrix mineral, so nothing is encoded.",
    "REVIEW_MULTIPLE_MODIFIERS": "More than one matrix mineral is named and their order is not defined. Flagged for review; the code is kept.",
    "UNRESOLVED_UNSUPPORTED_CODE": "The code is not in the legend, so it cannot be refined and stays unresolved.",
    "UNRESOLVED_MISSING_CODE": "The rock code is blank, so it cannot be refined and stays unresolved.",
}
REVIEW_STATUSES = {
    "CONFLICT_REVIEW",
    "REVIEW_MULTIPLE_MODIFIERS",
    "NOT_REFINED_VEIN",
    "UNRESOLVED_UNSUPPORTED_CODE",
    "UNRESOLVED_MISSING_CODE",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convention_sha256() -> str:
    """Digest of every rule the refinement uses. It enters the dataset version key."""
    material = {
        "version": LITHOLOGY_CONVENTION_VERSION,
        "typo_fixes": TYPO_FIXES,
        "lithology_patterns": [[p.pattern, c] for p, c in LITHOLOGY_PATTERNS],
        "already_named": {k: sorted(v) for k, v in ALREADY_NAMED.items()},
        "subordinate_minerals": SUBORDINATE_MINERALS,
        "general_to_specific": {k: sorted(v) for k, v in GENERAL_TO_SPECIFIC.items()},
        "name_pattern": NAME_PATTERN.pattern,
        "regexes": {name: pattern.pattern for name, pattern in REGEXES.items()},
    }
    text = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalise(comment: str) -> str:
    """Lower case, depth notes removed, commas and spacing tidied, spelling fixed."""
    text = DEPTH_NOTE.sub(" ", comment.lower()).replace(",", " ")
    text = TYPO_RE.sub(lambda m: TYPO_FIXES[m.group(0)], text)
    text = re.sub(r"\s+", " ", text).strip()
    return TRAILING_WITH.sub("", text).strip()


def lithology_of(norm: str) -> str | None:
    """The legend code of the lithology the comment names, if any."""
    for pattern, code in LITHOLOGY_PATTERNS:
        if pattern.search(norm):
            return code
    return None


def matrix_minerals(norm: str, base: str) -> list[tuple[str, str, str]]:
    """(mineral, code, abundance) for each matrix mineral the comment names."""
    named = []
    if QUARTZ_PRESENT.search(norm) and "quartz" not in ALREADY_NAMED.get(base, set()):
        named.append(("quartz", "qz", "present"))
    if TRACE_EPIDOTE.search(norm):
        named.append(("epidote", "ep", "trace"))
    elif EPIDOTE.search(norm):
        named.append(("epidote", "ep", "present"))
    return named


def refine(base: str, letter: str) -> str:
    """Subordinate mineral code after the group letter, before the rock letters."""
    return base[0] + letter + base[1:]


def classify(code: str | None, legend: dict[str, str], raw: str) -> dict:
    """Decide the refined code and status for one (rock code, comment) pair."""
    norm = normalise(raw)
    notes: list[str] = []
    if TYPO_RE.search(raw.lower()):
        notes.append("spelling corrected")
    if TRAILING_WITH.search(raw.strip().lower()):
        notes.append("comment ends in 'with'")
    if GRAPHITE_TRACE.search(norm):
        notes.append("graphite (trace) named: label evidence, not encoded")
    elif GRAPHITE.search(norm):
        notes.append("graphite named: label evidence, not encoded")

    lith = lithology_of(norm) or ""
    mins = matrix_minerals(norm, code or "")
    matrix = "; ".join(f"{name} ({abundance})" for name, _, abundance in mins)

    if code and code not in legend:
        twins = [k for k in legend if k.lower() == code.lower()]
        if twins:
            notes.append(f"legend has '{twins[0]}': case differs")

    if not code:
        status, refined, base = "UNRESOLVED_MISSING_CODE", "", ""
    elif code not in legend:
        status, refined, base = "UNRESOLVED_UNSUPPORTED_CODE", code, ""
    elif code in GENERAL_TO_SPECIFIC and lith in GENERAL_TO_SPECIFIC[code]:
        status, refined, base = "REFINED_GENERAL", lith, code
        notes.append(f"logged general code {code}; comment names {lith}")
    elif lith and lith != code:
        status, refined, base = "CONFLICT_REVIEW", code, code
        notes.append(f"comment names {lith}, code is {code}")
    elif VEIN.search(norm) and not mins:
        status, refined, base = "NOT_REFINED_VEIN", code, code
    elif len(mins) > 1:
        status, refined, base = "REVIEW_MULTIPLE_MODIFIERS", code, code
    elif mins:
        _, letter, abundance = mins[0]
        status = "REFINED"
        refined, base = refine(code, letter), code
        if abundance == "present":
            notes.append("abundance not logged: present treated as subordinate (accepted convention)")
    else:
        status = "UNCHANGED" if norm else "UNCHANGED_NO_COMMENT"
        refined, base = code, code

    return {
        "status": status,
        "refined": refined,
        "base": base,
        "lithology": lith,
        "matrix": matrix,
        "notes": "; ".join(notes),
    }


def read_legend(wb) -> dict[str, str]:
    legend = {}
    for row in list(wb["Logging Legend"].iter_rows(values_only=True))[2:]:
        row = list(row) + [None] * 4
        if row[1] == "RockType" and row[2] is not None:
            legend[str(row[2])] = str(row[3]).strip()
    return legend


def read_intervals(wb) -> list[tuple]:
    rows = list(wb["Logging"].iter_rows(values_only=True))
    ix = {h: i for i, h in enumerate(rows[0])}
    intervals = []
    for row in rows[1:]:
        if row[ix["HOLEID"]] is None:
            continue
        code = row[ix["rock_type1"]]
        raw = (row[ix["Comment"]] or "").strip()
        intervals.append((row[ix["HOLEID"]], row[ix["DEPTH_FROM"]], row[ix["DEPTH_TO"]], code, raw))
    return intervals


def compute(legend: dict[str, str], intervals: list[dict]) -> dict:
    """Classify every interval. Pure: no files and no database.

    Each interval is a dict with interval_key, hole_id, depth_from, depth_to, rock_code and comment
    (None or blank for an empty comment).
    """
    counts = collections.Counter((iv["rock_code"], iv["comment"] or "") for iv in intervals)
    results = {key: classify(key[0], legend, key[1]) for key in counts}

    change_rows = []
    for (code, raw), n in sorted(counts.items(), key=lambda kv: (str(kv[0][0]), -kv[1])):
        res = results[(code, raw)]
        change_rows.append({
            "original_code": code or "(blank)",
            "original_description": legend.get(code, "not in legend") if code else "(blank)",
            "comment_as_logged": raw,
            "comment_normalised": normalise(raw),
            "comment_lithology": res["lithology"],
            "matrix_minerals": res["matrix"],
            "status": res["status"],
            "refined_code": res["refined"],
            "intervals": n,
            "reason": REASON[res["status"]],
            "notes": res["notes"],
        })

    interval_rows = []
    for iv in intervals:
        raw = iv["comment"] or ""
        res = results[(iv["rock_code"], raw)]
        interval_rows.append({
            "interval_key": iv["interval_key"],
            "hole_id": iv["hole_id"],
            "depth_from": iv["depth_from"],
            "depth_to": iv["depth_to"],
            "label_code": iv["rock_code"] or "",
            "comment_as_logged": raw,
            "comment_normalised": normalise(raw),
            "comment_lithology": res["lithology"],
            "matrix_minerals": res["matrix"],
            "refinement_status": res["status"],
            "refined_code": res["refined"],
            "base_code": res["base"],
            "reason": REASON[res["status"]],
            "notes": res["notes"],
        })

    return {
        "change_rows": change_rows,
        "interval_rows": interval_rows,
        "dictionary": build_dictionary(change_rows, legend),
        "problems": verify(legend, results),
    }


def run(workbook: Path, out_dir: Path) -> dict:
    """Read the verified workbook copy and write the review files."""
    before = sha256(workbook)
    if before != WORKBOOK_SHA256:
        raise ValueError(f"workbook hash differs from the verified copy: {before}")

    wb = load_workbook(workbook, read_only=True, data_only=True)
    legend = read_legend(wb)
    rows = read_intervals(wb)
    wb.close()
    intervals = [
        {"interval_key": f"{hole}@{float(dfrom):g}", "hole_id": hole, "depth_from": dfrom, "depth_to": dto,
         "rock_code": code, "comment": raw}
        for hole, dfrom, dto, code, raw in rows
    ]

    result = compute(legend, intervals)
    after = sha256(workbook)
    target_a = sum(1 for iv in intervals if iv["rock_code"] == "Sgs")

    write_csv(out_dir / "reports" / "Lithology_Change_Log.csv", result["change_rows"])
    write_csv(out_dir / "data" / "derived" / "lithology_refined_intervals.csv", result["interval_rows"])
    write_csv(out_dir / "reports" / "Lithology_Code_Dictionary_Revised.csv", result["dictionary"])
    write_markdown(out_dir / "reports" / "Lithology_Redefinition.md", result["change_rows"], result["dictionary"],
                   len(intervals), target_a, before, after, result["problems"])

    return {
        "intervals": len(intervals),
        "pairs": len({(iv["rock_code"], iv["comment"] or "") for iv in intervals}),
        "target_a": target_a,
        "problems": result["problems"],
        "hash_unchanged": before == after,
        "status_counts": collections.Counter(
            {s: sum(r["intervals"] for r in result["change_rows"] if r["status"] == s) for s in REASON}),
    }


def verify(legend: dict[str, str], results: dict) -> list[str]:
    """Refined codes must not collide with legend codes, and each must name one base."""
    problems = []
    bases: dict[str, set] = collections.defaultdict(set)
    for (code, _raw), res in results.items():
        refined = res["refined"]
        if res["status"] == "REFINED" and refined and refined != code:
            if refined in legend:
                problems.append(f"refined code {refined} is already a legend code")
            bases[refined].add(code)
    for refined, base_codes in bases.items():
        if len(base_codes) > 1:
            problems.append(f"refined code {refined} maps to more than one base: {sorted(base_codes)}")
    return problems


def build_dictionary(change_rows: list[dict], legend: dict[str, str]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in change_rows:
        refined = row["refined_code"] or "(none)"
        g = grouped.setdefault(refined, {"base": set(), "minerals": set(), "statuses": set(),
                                         "intervals": 0, "notes": set()})
        if row["original_code"] != "(blank)":
            g["base"].add(row["original_code"])
        if row["matrix_minerals"]:
            g["minerals"].add(row["matrix_minerals"])
        g["statuses"].add(row["status"])
        g["intervals"] += row["intervals"]
        if row["status"] in REVIEW_STATUSES or row["notes"]:
            g["notes"].add(row["status"])

    out = []
    for refined in sorted(grouped, key=lambda r: (r == "(none)", r)):
        g = grouped[refined]
        base = "; ".join(sorted(g["base"])) or "(blank)"
        basis = ("unresolved" if g["statuses"] <= {"UNRESOLVED_UNSUPPORTED_CODE", "UNRESOLVED_MISSING_CODE"}
                 else "review" if g["statuses"] & {"CONFLICT_REVIEW", "REVIEW_MULTIPLE_MODIFIERS", "NOT_REFINED_VEIN"}
                 else "confirmed")
        desc = legend.get(base, "not in legend") if base in legend else ("not in legend" if base != "(blank)" else "(blank)")
        out.append({
            "refined_code": refined,
            "base_code": base,
            "base_description": desc,
            "refined_description": legend.get(refined, ""),
            "matrix_minerals_named": " | ".join(sorted(g["minerals"])),
            "basis": basis,
            "intervals": g["intervals"],
            "label_code_used": base,
        })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(lines)


def write_markdown(path: Path, change_rows, dictionary, n_intervals, target_a, before, after, problems) -> None:
    status_totals = collections.Counter()
    for r in change_rows:
        status_totals[r["status"]] += r["intervals"]
    flagged = [r for r in change_rows if r["status"] in REVIEW_STATUSES]

    parts = [
        "# Lithology code redefinition",
        "",
        "Generated by `kambale.lithology` from the logging comments. The workbook is read only.",
        "",
        "## Rules applied",
        "",
        "1. Base legend codes are kept. The label logic uses the logged code unchanged.",
        "2. A refined code adds each matrix mineral named in the comment. The subordinate mineral code sits after the group letter and before the rock letters, so the principal rock stays last (Sbs with quartz -> Sqzbs). Quartz is qz and epidote is ep, the workbook's own RTMineral codes.",
        "3. A matrix mineral named as a trace is subordinate. A mineral named as present, with no abundance, is also treated as subordinate. This is the convention accepted on 2026-11-05; the abundance is not logged, so each such case is recorded in the notes.",
        "4. Graphite is never encoded. It is label evidence, and encoding it would make the graphitic label depend on the code it defines.",
        "5. Where the comment names a different lithology from the code, the code is kept and flagged. Nothing is renamed to settle a conflict.",
        "6. Spelling corrections and depth notes are recorded and do not change the code.",
        "7. A general code can be refined to the specific legend code its comment names. Rso with transported gravels becomes Rgv. The logged code stays for labels. This is the one rule where the principal rock changes; it was chosen on 2026-11-05.",
        "",
        f"## Status by interval ({n_intervals} intervals)",
        "",
        md_table(["Status", "Intervals"], [[s, status_totals[s]] for s in REASON if status_totals[s]]),
        "",
        "## Revised code dictionary",
        "",
        md_table(["Refined code", "Base (label) code", "Description", "Matrix minerals named", "Basis", "Intervals"],
                 [[d["refined_code"], d["base_code"], d["base_description"], d["matrix_minerals_named"],
                   d["basis"], d["intervals"]] for d in dictionary]),
        "",
        "## Flagged for manual review",
        "",
        md_table(["Original code", "Comment (normalised)", "Status", "Intervals", "Reason"],
                 [[r["original_code"], r["comment_normalised"] or "(blank)", r["status"], r["intervals"], r["reason"]]
                  for r in flagged]),
        "",
        "## Verification",
        "",
        f"- Workbook SHA-256 before the run: `{before}`",
        f"- Workbook SHA-256 after the run: `{after}` ({'unchanged' if before == after else 'CHANGED'})",
        f"- Target A (rock code Sgs) count: {target_a}",
        f"- Collision and base checks: {'passed' if not problems else '; '.join(problems)}",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    workbook = Path(argv[0]) if argv else DEFAULT_WORKBOOK
    result = run(workbook, PROJECT_ROOT)
    print(f"intervals: {result['intervals']}  distinct pairs: {result['pairs']}")
    print(f"Target A (Sgs) count: {result['target_a']}")
    print(f"workbook hash unchanged: {result['hash_unchanged']}")
    print(f"checks: {'passed' if not result['problems'] else result['problems']}")
    for status, n in result["status_counts"].items():
        if n:
            print(f"  {status:28} {n:5d}")


if __name__ == "__main__":
    main()

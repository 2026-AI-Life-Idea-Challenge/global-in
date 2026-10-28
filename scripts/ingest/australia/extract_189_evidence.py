
"""
Australia subclass 189 - Points-tested stream
Official-source evidence and policy candidate extraction.

No executable eligibility decision rules are created.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / "data/raw/australia/employment"
OUTPUT = (
    ROOT
    / "data/processed/australia/employment"
    / "subclass_189_points_tested_evidence_draft.json"
)

PREFIX = "subclass_189_points_tested"

SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/Visa-subsite/"
    "Pages/work/189-skilled-independent-points-tested.aspx"
)

TABS = [
    "about_this_visa",
    "eligibility",
    "step_by_step",
    "when_you_have_this_visa",
]

HEADINGS = [
    ("current_visa", "Have this visa"),
    ("invitation", "Be invited to apply"),
    ("skills_assessment", "Have a suitable skills assessment"),
    ("age", "Be this age"),
    ("points", "Be able to score 65 points or more"),
    ("english", "Have this level of English language"),
    ("eligible_occupation", "Meet the skills requirement"),
    ("health", "Meet our health requirement"),
    ("character", "Meet our character requirement"),
    (
        "government_debt",
        "Have paid back your debt to the Australian government",
    ),
    (
        "australian_values_statement",
        "Sign the Australian values statement",
    ),
    (
        "immigration_history",
        "Not have had a visa cancelled or a previous application refused",
    ),
]

REVIEW_GROUPS = {
    "invitation_and_eoi": [
        "skillselect_expression_of_interest",
        "invitation_required",
        "invitation_validity",
    ],
    "points": [
        "minimum_65_points",
        "invitation_score_may_exceed_65",
        "evidence_for_points_claims",
    ],
    "occupation_and_assessment": [
        "subclass_189_eligible_occupation_list",
        "suitable_skills_assessment",
        "assessment_validity",
    ],
    "age": [
        "age_at_invitation",
        "age_limit",
    ],
    "english": [
        "competent_english_at_invitation",
        "accepted_tests_and_exemptions",
    ],
}


def load_sources():
    sources = {}
    contents = {}
    lines_by_tab = {}

    for tab in TABS:
        path = RAW_DIR / f"{PREFIX}_{tab}.txt"
        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")

        if len(content) <= 1000:
            raise ValueError(f"Source too short: {tab}")

        if any(
            marker in content.lower()
            for marker in ("<!doctype", "<html", "<script")
        ):
            raise ValueError(f"HTML source detected: {tab}")

        if (
            "Skilled Independent visa (subclass 189)"
            not in content
            or "Points-tested stream" not in content
        ):
            raise ValueError(f"Wrong visa or stream: {tab}")

        contents[tab] = content
        lines_by_tab[tab] = content.splitlines()

        sources[tab] = {
            "source_file": path.relative_to(ROOT).as_posix(),
            "source_url": SOURCE_URL,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "char_count": len(content),
            "review_status": "needs_review",
        }

    if len(set(contents.values())) != len(TABS):
        raise ValueError("Duplicate source tab contents")

    return sources, lines_by_tab


def extract_eligibility(lines, source_sha256):
    positions = []

    for topic, heading in HEADINGS:
        matches = [
            i for i, line in enumerate(lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Eligibility heading mismatch: {heading} / {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Eligibility headings out of order")

    end_matches = [
        i for i, line in enumerate(lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(end_matches) != 1:
        raise ValueError("Eligibility end marker mismatch")

    final_end = end_matches[0]

    if final_end <= positions[-1]:
        raise ValueError("Invalid eligibility boundary")

    sections = []
    evidence = []
    policies = []

    for index, (topic, heading) in enumerate(HEADINGS):
        start = positions[index]
        end = (
            positions[index + 1]
            if index + 1 < len(positions)
            else final_end
        )

        original_text = "\n".join(lines[start:end]).strip()

        if not original_text.startswith(heading):
            raise ValueError(f"Invalid section: {heading}")

        body_lines = original_text.splitlines()[1:]
        has_detail = any(line.strip() for line in body_lines)

        detail_status = (
            "present_in_eligibility_tab"
            if has_detail
            else "detail_missing_in_eligibility_tab"
        )

        section_id = f"AU_189_PT_ELIG_{index + 1:02d}"

        sections.append({
            "section_id": section_id,
            "topic": topic,
            "heading": heading,
            "source_tab": "eligibility",
            "start_line": start + 1,
            "end_line": end,
            "source_sha256": source_sha256,
            "original_text": original_text,
            "detail_status": detail_status,
            "review_status": "needs_review",
        })

        evidence.append({
            "evidence_id": f"AU_189_PT_EVD_{index + 1:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "exact_quote": original_text,
            "start_line": start + 1,
            "end_line": end,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"AU_189_PT_POL_{index + 1:02d}",
            "program": PREFIX,
            "topic": topic,
            "source_section_id": section_id,
            "source_text": original_text,
            "detail_status": detail_status,
            "requirement_type": "needs_review",
            "exception_review_status": "needs_review",
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    return sections, evidence, policies


def extract_steps(lines):
    positions = []

    for number in range(1, 6):
        heading = f"Step {number}"
        matches = [
            i for i, line in enumerate(lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Application step mismatch: {heading} / {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Application steps out of order")

    footer_matches = [
        i for i in range(positions[-1] + 1, len(lines))
        if lines[i].strip().startswith((
            "pop-up content starts",
            "Tell us what you think of this page",
            "Last updated:",
        ))
    ]

    final_end = (
        min(footer_matches)
        if footer_matches
        else len(lines)
    )

    steps = []

    for index, start in enumerate(positions):
        end = (
            positions[index + 1]
            if index + 1 < len(positions)
            else final_end
        )

        original_text = "\n".join(lines[start:end]).strip()

        if not original_text.startswith(f"Step {index + 1}"):
            raise ValueError("Empty application step")

        steps.append({
            "step_number": index + 1,
            "source_tab": "step_by_step",
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "review_status": "needs_review",
        })

    return steps


def main():
    sources, lines_by_tab = load_sources()

    sections, evidence, policies = extract_eligibility(
        lines_by_tab["eligibility"],
        sources["eligibility"]["source_sha256"],
    )

    steps = extract_steps(lines_by_tab["step_by_step"])

    review_groups = {
        name: {
            "review_points": points,
            "eligibility_rule": None,
            "review_status": "needs_review",
        }
        for name, points in REVIEW_GROUPS.items()
    }

    result = {
        "program": PREFIX,
        "visa_subclass": "189",
        "stream": "points_tested",
        "pathway_type": "independent_skilled_permanent",
        "official_sources": sources,
        "eligibility_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "application_steps": steps,
        "conditional_requirements": review_groups,
        "occupation_list_policy": {
            "source_topic": "eligible_occupation",
            "reuse_subclass_482_csol": False,
            "applicable_list": "needs_review",
            "review_status": "needs_review",
        },
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # Integrity checks before saving
    if not (
        len(sources) == 4
        and len(sections) == 12
        and len(evidence) == 12
        and len(policies) == 12
        and len(steps) == 5
        and len(review_groups) == 5
    ):
        raise ValueError("189 data count mismatch")

    if any(
        a["end_line"] + 1 != b["start_line"]
        for a, b in zip(sections, sections[1:])
    ):
        raise ValueError("189 eligibility section boundary gap")

    missing_details = [
        s["topic"]
        for s in sections
        if s["detail_status"] == "detail_missing_in_eligibility_tab"
    ]

    expected_missing = [
        "current_visa",
        "invitation",
        "skills_assessment",
        "age",
    ]

    if missing_details != expected_missing:
        raise ValueError(
            "Unexpected eligibility detail structure: "
            f"{missing_details}"
        )

    if any(
        p["eligibility_rule"] is not None
        or p["approved_for_eligibility_decision"]
        for p in policies
    ):
        raise ValueError("Unapproved executable rule detected")

    if len({p["policy_id"] for p in policies}) != 12:
        raise ValueError("Duplicate policy IDs")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== 189 POINTS-TESTED ===")
    print("SOURCE TABS:", len(sources))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("APPLICATION STEPS:", len(steps))
    print("REVIEW GROUPS:", len(review_groups))
    print("DETAILS MISSING IN ELIGIBILITY:", len(missing_details))
    print("MISSING TOPICS:", missing_details)
    print("OCCUPATION LIST: NEEDS_REVIEW")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_189_points_tested"])


"""
Australia subclass 190 - Skilled Nominated visa

Extract official-source evidence and policy candidates.
State/territory nomination rules remain pending review.

No executable eligibility decision rules are created.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = ROOT / "data/raw/australia/employment"

OUTPUT = (
    ROOT
    / "data/processed/australia/employment"
    / "subclass_190_evidence_draft.json"
)

PREFIX = "subclass_190"

SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/skilled-nominated-190"
)

TABS = [
    "about_this_visa",
    "eligibility",
    "step_by_step",
    "when_you_have_this_visa",
]

HEADINGS = [
    ("qualifying_visa", "Have this visa"),
    ("invitation", "Be invited to apply"),
    ("state_nomination", "Be nominated"),
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
]

STATES_TERRITORIES = [
    "Australian Capital Territory",
    "New South Wales",
    "Northern Territory",
    "Queensland",
    "South Australia",
    "Tasmania",
    "Victoria",
    "Western Australia",
]

REVIEW_GROUPS = {
    "qualifying_visa": [
        "substantive_or_eligible_bridging_visa",
        "subclass_491_or_494_three_year_requirement",
    ],
    "invitation_and_eoi": [
        "skillselect_eoi_submission",
        "invitation_required",
        "nomination_before_invitation",
    ],
    "state_nomination": [
        "state_or_territory_agency_nomination",
        "state_specific_nomination_criteria",
        "nomination_withdrawal",
    ],
    "skills_assessment": [
        "suitable_skills_assessment",
        "assessment_at_invitation",
        "assessment_within_invitation_period",
        "three_year_assessment_validity",
        "shorter_assessment_validity",
        "medical_and_legal_practitioner_alternatives",
        "cricos_qualification_requirement",
    ],
    "age": [
        "under_45_at_invitation",
        "turning_45_after_invitation",
    ],
    "points": [
        "minimum_65_points",
        "invitation_required_points",
        "evidence_for_eoi_claims",
    ],
    "english": [
        "competent_english_at_invitation",
    ],
    "eligible_occupation": [
        "subclass_190_applicable_occupation_list",
        "occupation_list_version",
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
            raise ValueError(f"190 source too short: {tab}")

        if any(
            marker in content.lower()
            for marker in ("<!doctype", "<html", "<script")
        ):
            raise ValueError(f"190 HTML source detected: {tab}")

        if not re.search(
            r"\bsubclass\s+190\b",
            content,
            flags=re.IGNORECASE,
        ):
            raise ValueError(f"190 visa number missing: {tab}")

        if "Skilled Nominated visa" not in content:
            raise ValueError(f"190 visa name missing: {tab}")

        contents[tab] = content
        lines_by_tab[tab] = content.splitlines()

        sources[tab] = {
            "source_file": path.relative_to(ROOT).as_posix(),
            "source_url": SOURCE_URL,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "char_count": len(content),
            "review_status": "needs_review",
        }

    if len(set(contents.values())) != 4:
        raise ValueError("190 duplicate source tabs")

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
                f"190 heading mismatch: {heading}: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("190 eligibility heading order mismatch")

    end_matches = [
        i for i, line in enumerate(lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(end_matches) != 1:
        raise ValueError("190 eligibility footer mismatch")

    final_end = end_matches[0]

    if final_end <= positions[-1]:
        raise ValueError("190 invalid eligibility boundary")

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

        original_text = "\n".join(
            lines[start:end]
        ).strip()

        if not original_text.startswith(heading):
            raise ValueError(f"190 invalid section: {heading}")

        body_lines = original_text.splitlines()[1:]

        if not any(line.strip() for line in body_lines):
            raise ValueError(
                f"190 eligibility detail missing: {heading}"
            )

        section_id = f"AU_190_ELIG_{index + 1:02d}"

        sections.append({
            "section_id": section_id,
            "topic": topic,
            "heading": heading,
            "source_tab": "eligibility",
            "source_sha256": source_sha256,
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "detail_status": "present_in_eligibility_tab",
            "review_status": "needs_review",
        })

        evidence.append({
            "evidence_id": f"AU_190_EVD_{index + 1:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "exact_quote": original_text,
            "start_line": start + 1,
            "end_line": end,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"AU_190_POL_{index + 1:02d}",
            "program": PREFIX,
            "topic": topic,
            "source_section_id": section_id,
            "source_text": original_text,
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
                f"190 application step mismatch: "
                f"{heading}: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("190 application step order mismatch")

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

        original_text = "\n".join(
            lines[start:end]
        ).strip()

        if not original_text.startswith(f"Step {index + 1}"):
            raise ValueError(
                f"190 empty application step: {index + 1}"
            )

        steps.append({
            "step_number": index + 1,
            "source_tab": "step_by_step",
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "review_status": "needs_review",
        })

    return steps


def build_nomination_data(sections):
    nomination_section = next(
        section
        for section in sections
        if section["topic"] == "state_nomination"
    )

    original_text = nomination_section["original_text"]

    missing_states = [
        state
        for state in STATES_TERRITORIES
        if state not in original_text
    ]

    if missing_states:
        raise ValueError(
            f"190 state list incomplete: {missing_states}"
        )

    return {
        "nomination_required": True,
        "nomination_source_section_id": (
            nomination_section["section_id"]
        ),
        "states_and_territories": [
            {
                "name": state,
                "specific_nomination_criteria": None,
                "review_status": "needs_review",
            }
            for state in STATES_TERRITORIES
        ],
        "nomination_withdrawal": {
            "requires_review": True,
            "source_section_id": nomination_section["section_id"],
        },
        "review_status": "needs_review",
    }


def main():
    sources, lines_by_tab = load_sources()

    sections, evidence, policies = extract_eligibility(
        lines_by_tab["eligibility"],
        sources["eligibility"]["source_sha256"],
    )

    steps = extract_steps(
        lines_by_tab["step_by_step"]
    )

    nomination = build_nomination_data(sections)

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
        "visa_subclass": "190",
        "stream": "skilled_nominated",
        "pathway_type": "state_nominated_skilled_permanent",
        "official_sources": sources,
        "eligibility_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "application_steps": steps,
        "state_territory_nomination": nomination,
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

    # Consolidated integrity checks
    if not (
        len(sources) == 4
        and len(sections) == 12
        and len(evidence) == 12
        and len(policies) == 12
        and len(steps) == 5
        and len(review_groups) == 8
        and len(nomination["states_and_territories"]) == 8
    ):
        raise ValueError("190 data count mismatch")

    if any(
        a["end_line"] + 1 != b["start_line"]
        for a, b in zip(sections, sections[1:])
    ):
        raise ValueError(
            "190 eligibility section boundary gap"
        )

    if len({
        item["policy_id"]
        for item in policies
    }) != 12:
        raise ValueError("190 duplicate policy IDs")

    if any(
        policy["eligibility_rule"] is not None
        or policy["approved_for_eligibility_decision"]
        for policy in policies
    ):
        raise ValueError(
            "190 unapproved executable policy detected"
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== 190 SKILLED NOMINATED ===")
    print("SOURCE TABS:", len(sources))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("APPLICATION STEPS:", len(steps))
    print("REVIEW GROUPS:", len(review_groups))
    print(
        "STATES AND TERRITORIES:",
        len(nomination["states_and_territories"]),
    )
    print("NOMINATION: NEEDS_REVIEW")
    print("OCCUPATION LIST: NEEDS_REVIEW")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_190"])

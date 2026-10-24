
"""
Australia subclass 407 - Training visa.

Extract source-linked evidence, policy candidates and
application steps from four official page captures.

No executable eligibility rules are approved.
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
    / "subclass_407_evidence_draft.json"
)

PREFIX = "subclass_407"
SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/training-407"
)

TABS = [
    "about_this_visa",
    "eligibility",
    "step_by_step",
    "when_you_have_this_visa",
]

HEADINGS = [
    ("approved_sponsor", "Have an approved sponsor"),
    ("approved_nomination", "Have an approved nomination"),
    ("age", "Be this age"),
    ("qualifying_visa", "Have this visa"),
    ("health", "Meet our health requirement"),
    ("character", "Meet our character requirement"),
    ("health_insurance", "Have adequate health insurance"),
    ("genuine_temporary_entrant", "Be a genuine temporary entrant"),
    ("english", "Have this level of English language"),
    (
        "australian_values_statement",
        "Sign the Australian values statement",
    ),
    (
        "government_debt",
        "Have paid back your debt to the Australian Government",
    ),
    (
        "immigration_history",
        "Not had a visa cancelled or an application refused",
    ),
    ("best_interests_of_child", "Best interests of the child"),
]

TRAINING_TYPES = [
    {
        "type_id": "registration",
        "official_text": "Occupational training required for registration",
    },
    {
        "type_id": "skills_improvement",
        "official_text": (
            "Occupational training to improve skills "
            "in an eligible occupation"
        ),
    },
    {
        "type_id": "overseas_capacity_building",
        "official_text": (
            "Occupational training for capacity building overseas."
        ),
    },
]

REVIEW_GROUPS = {
    "sponsorship_and_nomination": [
        "approved_temporary_activities_sponsor",
        "approved_nomination_before_application",
        "commonwealth_government_agency_exception",
        "training_type_specific_nomination",
    ],
    "training_purpose": [
        "occupational_training_for_registration",
        "training_in_eligible_occupation",
        "capacity_building_overseas",
        "training_program_evidence",
    ],
    "age": [
        "usually_at_least_18_at_decision",
        "under_18_child_best_interests",
    ],
    "qualifying_visa": [
        "eligible_substantive_visa",
        "excluded_subclass_403_domestic_worker",
        "excluded_subclass_771",
        "excluded_special_purpose_visa",
        "last_substantive_visa_conditions",
        "28_day_application_window",
    ],
    "english": [
        "functional_english",
        "acceptable_evidence",
    ],
    "temporary_intention": [
        "genuine_temporary_entrant",
        "visa_conditions_compliance",
    ],
    "health_insurance": [
        "adequate_cover_whole_stay",
        "medically_necessary_treatment_and_transport",
        "reciprocal_healthcare_agreements",
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

        if not 1000 < len(content) < 100000:
            raise ValueError(f"407 invalid source size: {tab}")

        if any(
            marker in content.lower()
            for marker in ("<!doctype", "<html", "<script")
        ):
            raise ValueError(f"407 HTML source detected: {tab}")

        if not (
            re.search(
                r"\bsubclass\s+407\b",
                content,
                flags=re.IGNORECASE,
            )
            and re.search(
                r"\bTraining visa\b",
                content,
                flags=re.IGNORECASE,
            )
        ):
            raise ValueError(f"407 wrong visa source: {tab}")

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
        raise ValueError("407 duplicate source tabs")

    return sources, lines_by_tab


def extract_eligibility(lines, source_sha256):
    positions = []

    for topic, heading in HEADINGS:
        matches = [
            index for index, line in enumerate(lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"407 heading mismatch: {heading}: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("407 eligibility heading order mismatch")

    footer_matches = [
        index for index, line in enumerate(lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(footer_matches) != 1:
        raise ValueError("407 eligibility footer mismatch")

    final_end = footer_matches[0]

    if final_end <= positions[-1]:
        raise ValueError("407 invalid eligibility boundary")

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
            raise ValueError(f"407 invalid section: {heading}")

        if not any(
            line.strip()
            for line in original_text.splitlines()[1:]
        ):
            raise ValueError(f"407 missing section details: {heading}")

        section_id = f"AU_407_ELIG_{index + 1:02d}"

        sections.append({
            "section_id": section_id,
            "topic": topic,
            "heading": heading,
            "source_tab": "eligibility",
            "source_sha256": source_sha256,
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "review_status": "needs_review",
        })

        evidence.append({
            "evidence_id": f"AU_407_EVD_{index + 1:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "exact_quote": original_text,
            "start_line": start + 1,
            "end_line": end,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"AU_407_POL_{index + 1:02d}",
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
        matches = [
            index for index, line in enumerate(lines)
            if line.strip() == f"Step {number}"
        ]

        if len(matches) != 1:
            raise ValueError(
                f"407 Step {number} mismatch: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("407 application step order mismatch")

    footer_matches = [
        index
        for index in range(positions[-1] + 1, len(lines))
        if lines[index].strip().startswith((
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

        text = "\n".join(lines[start:end]).strip()

        if not text.startswith(f"Step {index + 1}"):
            raise ValueError(f"407 empty Step {index + 1}")

        steps.append({
            "step_number": index + 1,
            "source_tab": "step_by_step",
            "start_line": start + 1,
            "end_line": end,
            "original_text": text,
            "review_status": "needs_review",
        })

    return steps


def extract_training_types(sections):
    nomination = next(
        section
        for section in sections
        if section["topic"] == "approved_nomination"
    )

    text = nomination["original_text"]

    if "There are 3 types of occupational training" not in text:
        raise ValueError("407 training type introduction missing")

    result = []

    for training_type in TRAINING_TYPES:
        if training_type["official_text"] not in text:
            raise ValueError(
                f"407 training type missing: {training_type['type_id']}"
            )

        result.append({
            **training_type,
            "source_section_id": nomination["section_id"],
            "specific_requirements": None,
            "eligibility_rule": None,
            "review_status": "needs_review",
        })

    return result


def main():
    sources, lines_by_tab = load_sources()

    sections, evidence, policies = extract_eligibility(
        lines_by_tab["eligibility"],
        sources["eligibility"]["source_sha256"],
    )

    steps = extract_steps(lines_by_tab["step_by_step"])
    training_types = extract_training_types(sections)

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
        "visa_subclass": "407",
        "stream": "training",
        "pathway_type": "temporary_occupational_training",
        "official_sources": sources,
        "eligibility_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "application_steps": steps,
        "training_types": training_types,
        "conditional_requirements": review_groups,
        "sponsorship_nomination_policy": {
            "approved_sponsor_required": True,
            "approved_nomination_before_application": True,
            "commonwealth_agency_nomination_exception": {
                "requires_review": True,
                "eligibility_rule": None,
            },
            "source_section_ids": [
                section["section_id"]
                for section in sections
                if section["topic"] in (
                    "approved_sponsor",
                    "approved_nomination",
                )
            ],
            "review_status": "needs_review",
        },
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    if not (
        len(sources) == 4
        and len(sections) == 13
        and len(evidence) == 13
        and len(policies) == 13
        and len(steps) == 5
        and len(training_types) == 3
        and len(review_groups) == 7
    ):
        raise ValueError("407 data count mismatch")

    if any(
        left["end_line"] + 1 != right["start_line"]
        for left, right in zip(sections, sections[1:])
    ):
        raise ValueError("407 eligibility section boundary gap")

    if len({p["policy_id"] for p in policies}) != 13:
        raise ValueError("407 duplicate policy IDs")

    if any(
        p["eligibility_rule"] is not None
        or p["approved_for_eligibility_decision"]
        for p in policies
    ):
        raise ValueError("407 unapproved executable rule detected")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== 407 TRAINING VISA ===")
    print("SOURCE TABS:", len(sources))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("APPLICATION STEPS:", len(steps))
    print("TRAINING TYPES:", len(training_types))
    print("REVIEW GROUPS:", len(review_groups))
    print("SPONSORSHIP AND NOMINATION: NEEDS_REVIEW")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
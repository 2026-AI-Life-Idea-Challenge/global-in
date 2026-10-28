
"""
Australia - Subclass 417 First Working Holiday visa.

Extract official evidence and policy candidates.
All eligibility rules remain unapproved pending legal review.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = ROOT / "data/raw/australia/working_holiday"

OUTPUT = (
    ROOT
    / "data/processed/australia/working_holiday"
    / "subclass_417_first_evidence_draft.json"
)

PREFIX = "subclass_417_first"

SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/work-holiday-417/"
    "first-working-holiday-417"
)

TABS = [
    "about_this_visa",
    "eligibility",
    "step_by_step",
    "when_you_have_this_visa",
]

HEADINGS = [
    ("passport", "Hold this passport"),
    ("age", "Be this age"),
    ("previous_visas", "Previous visas"),
    ("financial_capacity", "Have enough money"),
    ("health", "Meet the health requirement"),
    ("character", "Meet the character requirement"),
    (
        "government_debt",
        "Pay your debts to the Australian Government",
    ),
    (
        "immigration_history",
        "Not had a visa cancelled or an application refused",
    ),
    (
        "australian_values",
        "Sign the Australian values statement",
    ),
]

REVIEW_GROUPS = {
    "passport_and_nationality": {
        "topics": ["passport"],
        "review_points": [
            "eligible_passport_countries",
            "citizenship_and_valid_passport",
            "special_passport_conditions",
        ],
    },
    "age_by_nationality": {
        "topics": ["age"],
        "review_points": [
            "country_specific_age_limit",
            "18_to_30_or_18_to_35",
            "application_deadline_in_australian_time",
            "age_at_application_vs_decision",
        ],
    },
    "previous_visa_history": {
        "topics": ["previous_visas", "immigration_history"],
        "review_points": [
            "previous_entry_on_417",
            "previous_entry_on_462",
            "prior_visa_refusal",
            "prior_visa_cancellation",
        ],
    },
    "financial_capacity": {
        "topics": ["financial_capacity"],
        "review_points": [
            "initial_support_funds",
            "usual_aud_5000_guidance",
            "onward_travel_fare",
            "acceptable_financial_evidence",
        ],
    },
    "health_character_and_values": {
        "topics": [
            "health",
            "character",
            "government_debt",
            "australian_values",
        ],
        "review_points": [
            "health_requirement",
            "character_requirement",
            "australian_government_debt",
            "australian_values_statement",
        ],
    },
}


def load_sources():
    sources = {}
    lines_by_tab = {}
    contents = []

    for tab in TABS:
        path = RAW_DIR / f"{PREFIX}_{tab}.txt"

        if not path.is_file():
            raise FileNotFoundError(path)

        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")

        if len(text) <= 1000:
            raise ValueError(f"Source too short: {tab}")

        if not re.search(r"subclass\s+417", text, re.I):
            raise ValueError(f"Wrong visa subclass: {tab}")

        if not re.search(
            r"First Working Holiday visa", text, re.I
        ):
            raise ValueError(f"Wrong visa stream: {tab}")

        if re.search(
            r"<!DOCTYPE|<html|<script", text, re.I
        ):
            raise ValueError(f"HTML detected: {tab}")

        contents.append(text.strip())
        lines_by_tab[tab] = text.splitlines()

        sources[tab] = {
            "source_file": path.relative_to(ROOT).as_posix(),
            "source_url": SOURCE_URL,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "char_count": len(text),
            "review_status": "needs_review",
        }

    if len(set(contents)) != len(TABS):
        raise ValueError("Duplicate source tabs")

    return sources, lines_by_tab


def extract_eligibility(lines, source_sha256):
    positions = []

    for topic, heading in HEADINGS:
        matches = [
            i
            for i, line in enumerate(lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Eligibility heading mismatch: {heading} -> {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Eligibility headings out of order")

    footer = [
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(footer) != 1 or footer[0] <= positions[-1]:
        raise ValueError("Eligibility footer mismatch")

    sections = []
    evidence = []
    policies = []

    for index, (topic, heading) in enumerate(HEADINGS):
        start = positions[index]

        end = (
            positions[index + 1]
            if index + 1 < len(positions)
            else footer[0]
        )

        text = "\n".join(lines[start:end]).strip()

        if not text.startswith(heading):
            raise ValueError(f"Invalid heading: {heading}")

        if len(text.splitlines()) < 2:
            raise ValueError(f"Missing detail: {heading}")

        number = index + 1
        section_id = f"AU_417_FIRST_ELIG_{number:02d}"

        sections.append({
            "section_id": section_id,
            "topic": topic,
            "heading": heading,
            "source_tab": "eligibility",
            "source_sha256": source_sha256,
            "start_line": start + 1,
            "end_line": end,
            "original_text": text,
            "review_status": "needs_review",
        })

        evidence.append({
            "evidence_id": f"AU_417_FIRST_EVD_{number:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "start_line": start + 1,
            "end_line": end,
            "exact_quote": text,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"AU_417_FIRST_POL_{number:02d}",
            "program": PREFIX,
            "topic": topic,
            "source_section_id": section_id,
            "source_text": text,
            "requirement_type": "needs_review",
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    return sections, evidence, policies


def extract_application_steps(lines):
    positions = []

    for number in range(1, 6):
        matches = [
            i
            for i, line in enumerate(lines)
            if line.strip() == f"Step {number}"
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Application Step {number} mismatch: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Application steps out of order")

    footer_candidates = [
        i
        for i in range(positions[-1] + 1, len(lines))
        if lines[i].strip().startswith((
            "pop-up content starts",
            "Tell us what you think of this page",
            "Last updated:",
        ))
    ]

    final_end = (
        min(footer_candidates)
        if footer_candidates
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

        if len(original_text.splitlines()) < 2:
            raise ValueError(
                f"Missing application Step {index + 1} details"
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


def extract_age_guidance(sections):
    section = next(
        s for s in sections if s["topic"] == "age"
    )

    entries = []

    for line in section["original_text"].splitlines():
        match = re.fullmatch(
            r"(.+?)\s*[-–]\s*18 to (30|35) years",
            line.strip(),
        )

        if match:
            entries.append({
                "passport_country": match.group(1).strip(),
                "minimum_age": 18,
                "maximum_age": int(match.group(2)),
                "source_section_id": section["section_id"],
                "eligibility_rule": None,
                "review_status": "needs_review",
            })

    if len(entries) != 19:
        raise ValueError(
            f"Expected 19 country age entries, got {len(entries)}"
        )

    return entries


def main():
    sources, lines_by_tab = load_sources()

    sections, evidence, policies = extract_eligibility(
        lines_by_tab["eligibility"],
        sources["eligibility"]["source_sha256"],
    )

    steps = extract_application_steps(
        lines_by_tab["step_by_step"]
    )

    age_guidance = extract_age_guidance(sections)

    topic_map = {
        section["topic"]: section["section_id"]
        for section in sections
    }

    review_groups = {}

    for name, config in REVIEW_GROUPS.items():
        review_groups[name] = {
            "source_section_ids": [
                topic_map[topic]
                for topic in config["topics"]
            ],
            "review_points": config["review_points"],
            "eligibility_rule": None,
            "review_status": "needs_review",
        }

    result = {
        "program": PREFIX,
        "visa_subclass": "417",
        "stream": "first_working_holiday",
        "pathway_type": "working_holiday",
        "official_sources": sources,
        "eligibility_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "application_steps": steps,
        "conditional_requirements": review_groups,
        "country_age_guidance": age_guidance,
        "financial_guidance": {
            "usual_initial_funds_aud": 5000,
            "onward_travel_fare": "additional",
            "source_section_id": topic_map["financial_capacity"],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "previous_entry_restrictions": {
            "visa_subclasses": ["417", "462"],
            "restriction": "previous_entry",
            "source_section_id": topic_map["previous_visas"],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    if not (
        len(sources) == 4
        and len(sections) == 9
        and len(evidence) == 9
        and len(policies) == 9
        and len(steps) == 5
        and len(review_groups) == 5
        and len(age_guidance) == 19
    ):
        raise ValueError("417 First count mismatch")

    if any(
        p["eligibility_rule"] is not None
        or p["approved_for_eligibility_decision"]
        for p in policies
    ):
        raise ValueError("Unapproved eligibility policy detected")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== 417 FIRST WORKING HOLIDAY ===")
    print("SOURCE TABS:", len(sources))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("APPLICATION STEPS:", len(steps))
    print("COUNTRY AGE ENTRIES:", len(age_guidance))
    print("REVIEW GROUPS:", len(review_groups))
    print("FINANCIAL GUIDANCE: AUD 5000 + ONWARD FARE")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_417_first"])

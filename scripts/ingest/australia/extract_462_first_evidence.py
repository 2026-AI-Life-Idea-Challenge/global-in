
"""
Australia - Subclass 462 First Work and Holiday visa.

Extract source-linked evidence, policy candidates, application steps,
eligible passport countries, ballot countries and support-letter countries.

Country-specific education requirements remain unapproved because the
copied HTML table may have lost its original row/column relationships.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / "data/raw/australia/work_and_holiday"
OUTPUT = (
    ROOT / "data/processed/australia/work_and_holiday"
    / "subclass_462_first_evidence_draft.json"
)

PREFIX = "subclass_462_first"

SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/work-holiday-462/"
    "first-work-holiday-462"
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
    ("education", "Meet our education requirement"),
    ("english", "Have this level of English language"),
    ("government_support", "Have a letter of support"),
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
    "passport_and_ballot": {
        "topics": ["passport"],
        "review_points": [
            "eligible_passport_countries",
            "valid_passport_and_citizenship",
            "china_india_vietnam_ballot",
            "ballot_selection_and_validity",
            "country_specific_application_arrangements",
        ],
    },
    "age_and_previous_visas": {
        "topics": ["age", "previous_visas"],
        "review_points": [
            "age_18_to_30_inclusive",
            "aest_aedt_application_deadline",
            "previous_entry_on_417_or_462",
        ],
    },
    "country_specific_education": {
        "topics": ["education"],
        "review_points": [
            "education_requirement_by_passport_country",
            "accepted_tertiary_qualifications",
            "completed_undergraduate_study",
            "special_country_education_requirements",
            "html_table_row_alignment",
            "embassy_guidance",
        ],
    },
    "functional_english": {
        "topics": ["english"],
        "review_points": [
            "functional_english",
            "passport_based_exemptions",
            "english_medium_study",
            "approved_tests",
            "test_within_12_months",
        ],
    },
    "government_support_letter": {
        "topics": ["government_support"],
        "review_points": [
            "support_letter_required_countries",
            "malaysia_good_conduct_certificate",
            "document_issuer_and_validity",
        ],
    },
    "financial_capacity": {
        "topics": ["financial_capacity"],
        "review_points": [
            "usual_initial_funds_aud_5000",
            "onward_travel_fare",
            "accepted_funding_evidence",
        ],
    },
    "health_character_and_other": {
        "topics": [
            "health",
            "character",
            "government_debt",
            "immigration_history",
            "australian_values",
        ],
        "review_points": [
            "health_requirement",
            "character_requirement",
            "australian_government_debt",
            "prior_visa_refusal_or_cancellation",
            "australian_values_statement",
        ],
    },
}

EXPECTED_BALLOT_COUNTRIES = [
    "China, People's Republic of",
    "India",
    "Vietnam",
]

EXPECTED_SUPPORT_COUNTRIES = [
    "Ecuador",
    "Greece",
    "Indonesia",
    "Malaysia (Good Conduct Certificate)",
    "Mongolia",
    "Peru",
    "Poland",
    "San Marino",
    "Slovenia",
    "Thailand",
    "Türkiye",
]


def load_sources():
    sources = {}
    lines_by_tab = {}
    contents = []

    for tab in TABS:
        path = RAW_DIR / f"{PREFIX}_{tab}.txt"

        if not path.is_file():
            raise FileNotFoundError(path)

        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")
        lines = content.splitlines()
        page_header = "\n".join(lines[:35])

        if len(content) <= 1000:
            raise ValueError(f"Source too short: {tab}")

        if not re.search(r"subclass\s+462", content, re.I):
            raise ValueError(f"Wrong subclass: {tab}")

        if not re.search(
            r"\bFirst Work and Holiday visa\b",
            page_header,
            re.I,
        ):
            raise ValueError(f"Wrong visa stream: {tab}")

        if re.search(
            r"<!DOCTYPE|<html|<script",
            content,
            re.I,
        ):
            raise ValueError(f"HTML detected: {tab}")

        contents.append(content.strip())
        lines_by_tab[tab] = lines

        sources[tab] = {
            "source_file": path.relative_to(ROOT).as_posix(),
            "source_url": SOURCE_URL,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "char_count": len(content),
            "review_status": "needs_review",
        }

    if len(set(contents)) != len(TABS):
        raise ValueError("Duplicate 462 First source tabs")

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
                f"Eligibility heading mismatch: {heading}: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Eligibility heading order mismatch")

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

        original_text = "\n".join(lines[start:end]).strip()

        if not original_text.startswith(heading):
            raise ValueError(f"Invalid section: {heading}")

        if len(original_text.splitlines()) < 2:
            raise ValueError(f"Missing detail: {heading}")

        number = index + 1
        section_id = f"AU_462_FIRST_ELIG_{number:02d}"

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
            "evidence_id": f"AU_462_FIRST_EVD_{number:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "start_line": start + 1,
            "end_line": end,
            "exact_quote": original_text,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"AU_462_FIRST_POL_{number:02d}",
            "program": PREFIX,
            "topic": topic,
            "source_section_id": section_id,
            "source_text": original_text,
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
        raise ValueError("Application step order mismatch")

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
                f"Missing Step {index + 1} details"
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


def extract_country_guidance(sections):
    by_topic = {
        section["topic"]: section
        for section in sections
    }

    passport = by_topic["passport"]
    lines = passport["original_text"].splitlines()

    start = next(
        i for i, line in enumerate(lines)
        if "one of these countries:" in line
    ) + 1

    end = next(
        i for i in range(start, len(lines))
        if lines[i].strip().startswith("Note:")
    )

    countries = [
        line.strip()
        for line in lines[start:end]
        if line.strip()
    ]

    if len(countries) != 30 or len(set(countries)) != 30:
        raise ValueError(
            f"Eligible passport country mismatch: {len(countries)}"
        )

    if not all(
        country in countries
        for country in EXPECTED_BALLOT_COUNTRIES
    ):
        raise ValueError("Ballot countries missing from passport list")

    passport_text = passport["original_text"]

    if not (
        re.search(r"\bballot\b", passport_text, re.I)
        and re.search(
            r"China, India and Vietnam passport holders",
            passport_text,
            re.I,
        )
    ):
        raise ValueError("Ballot requirement missing")

    support = by_topic["government_support"]
    support_text = support["original_text"]

    actual_support = [
        line.strip()
        for line in support_text.splitlines()[2:]
        if line.strip()
    ]

    if actual_support != EXPECTED_SUPPORT_COUNTRIES:
        raise ValueError(
            "Government support country list mismatch: "
            + repr(actual_support)
        )

    return {
        "eligible_passport_countries": {
            "source_section_id": passport["section_id"],
            "countries": countries,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "ballot_countries": {
            "source_section_id": passport["section_id"],
            "countries": EXPECTED_BALLOT_COUNTRIES,
            "requirement": "pre_application_ballot_selection",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "government_support_countries": {
            "source_section_id": support["section_id"],
            "countries_or_documents": actual_support,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }


def extract_special_conditions(sections):
    by_topic = {
        section["topic"]: section
        for section in sections
    }

    age = by_topic["age"]
    previous = by_topic["previous_visas"]
    education = by_topic["education"]
    english = by_topic["english"]
    finances = by_topic["financial_capacity"]

    age_text = age["original_text"]
    previous_text = previous["original_text"]
    english_text = english["original_text"]
    finance_text = finances["original_text"]

    if not re.search(
        r"18 to 30 years old\s*\(inclusive\)",
        age_text,
        re.I,
    ):
        raise ValueError("Age requirement missing")

    if not (
        re.search(r"subclass 462", previous_text, re.I)
        and re.search(r"subclass 417", previous_text, re.I)
    ):
        raise ValueError("Previous visa conditions missing")

    if not (
        re.search(r"Functional English", english_text, re.I)
        and re.search(r"12 months", english_text, re.I)
    ):
        raise ValueError("English conditions missing")

    if not (
        re.search(r"AUD\s*5,000", finance_text, re.I)
        and "fare" in finance_text.lower()
    ):
        raise ValueError("Financial guidance missing")

    return {
        "age": {
            "source_section_id": age["section_id"],
            "minimum_age": 18,
            "maximum_age": 30,
            "deadline_timezone": "AEST/AEDT",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "previous_visas": {
            "source_section_id": previous["section_id"],
            "previous_entry_subclasses": ["417", "462"],
            "restriction_type": "previous_entry",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "country_specific_education": {
            "source_section_id": education["section_id"],
            "raw_table_text": education["original_text"],
            "country_rule_mapping": None,
            "reason": "copied_table_structure_requires_validation",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "functional_english": {
            "source_section_id": english["section_id"],
            "level": "Functional English",
            "test_max_age_months_at_application": 12,
            "passport_and_study_exemptions": "review_source_text",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "financial_guidance": {
            "source_section_id": finances["section_id"],
            "usual_initial_funds_aud": 5000,
            "onward_travel_fare": "additional",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }


def main():
    sources, lines_by_tab = load_sources()

    sections, evidence, policies = extract_eligibility(
        lines_by_tab["eligibility"],
        sources["eligibility"]["source_sha256"],
    )

    steps = extract_application_steps(
        lines_by_tab["step_by_step"]
    )

    country_guidance = extract_country_guidance(sections)
    special_conditions = extract_special_conditions(sections)

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
        "visa_subclass": "462",
        "stream": "first_work_and_holiday",
        "pathway_type": "work_and_holiday",
        "official_sources": sources,
        "eligibility_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "application_steps": steps,
        "conditional_requirements": review_groups,
        "country_guidance": country_guidance,
        "special_conditions": special_conditions,
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    if not (
        len(sources) == 4
        and len(sections) == 12
        and len(evidence) == 12
        and len(policies) == 12
        and len(steps) == 5
        and len(review_groups) == 7
        and len(
            country_guidance["eligible_passport_countries"]["countries"]
        ) == 30
        and len(
            country_guidance["ballot_countries"]["countries"]
        ) == 3
        and len(
            country_guidance[
                "government_support_countries"
            ]["countries_or_documents"]
        ) == 11
    ):
        raise ValueError("462 First data count mismatch")

    if any(
        left["end_line"] + 1 != right["start_line"]
        for left, right in zip(sections, sections[1:])
    ):
        raise ValueError("Eligibility section boundary mismatch")

    if len({
        policy["policy_id"]
        for policy in policies
    }) != len(policies):
        raise ValueError("Duplicate policy IDs")

    if any(
        policy["eligibility_rule"] is not None
        or policy["approved_for_eligibility_decision"]
        for policy in policies
    ):
        raise ValueError("Unapproved policy detected")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== 462 FIRST WORK AND HOLIDAY ===")
    print("SOURCE TABS:", len(sources))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("APPLICATION STEPS:", len(steps))
    print(
        "PASSPORT COUNTRIES:",
        len(country_guidance["eligible_passport_countries"]["countries"]),
    )
    print(
        "BALLOT COUNTRIES:",
        len(country_guidance["ballot_countries"]["countries"]),
    )
    print(
        "SUPPORT LETTER COUNTRIES:",
        len(
            country_guidance[
                "government_support_countries"
            ]["countries_or_documents"]
        ),
    )
    print("REVIEW GROUPS:", len(review_groups))
    print("EDUCATION TABLE MAPPING: NEEDS_REVIEW")
    print("FUNCTIONAL ENGLISH: NEEDS_REVIEW")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_462_first"])

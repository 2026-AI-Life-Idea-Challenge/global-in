
"""
Australia - Subclass 462 Third Work and Holiday visa.

Extract source-linked evidence, policy candidates, application
steps and conditional requirements from official page captures.

All policy candidates require legal review before use in
automated eligibility decisions.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = ROOT / "data/raw/australia/work_and_holiday"

OUTPUT = (
    ROOT / "data/processed/australia/work_and_holiday"
    / "subclass_462_third_evidence_draft.json"
)

PREFIX = "subclass_462_third"

SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/work-holiday-462/"
    "third-work-and-holiday-462"
)

TABS = [
    "about_this_visa",
    "eligibility",
    "step_by_step",
    "when_you_have_this_visa",
]

HEADINGS = [
    ("passport", "Have this passport"),
    ("previous_visa", "Current or previous visa"),
    ("financial_capacity", "Have enough money"),
    ("specified_work", "Specified subclass 462 work"),
    ("age", "Be this age"),
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
]

REVIEW_GROUPS = {
    "passport_and_nationality": {
        "topics": ["passport"],
        "review_points": [
            "eligible_passport_countries",
            "citizenship_and_valid_passport",
            "passport_country_name_normalisation",
            "country_specific_conditions",
        ],
    },
    "previous_visa_and_location": {
        "topics": ["previous_visa"],
        "review_points": [
            "previous_second_subclass_462_visa",
            "qualifying_bridging_visa",
            "previous_462_visa_condition_compliance",
            "substantive_visa_for_onshore_application",
            "less_than_28_days_since_expiry",
        ],
    },
    "specified_subclass_462_work": {
        "topics": ["specified_work"],
        "review_points": [
            "six_months_specified_subclass_462_work",
            "eligible_work_categories",
            "eligible_regions",
            "work_period_calculation",
            "accepted_work_evidence",
        ],
    },
    "age_requirement": {
        "topics": ["age"],
        "review_points": [
            "age_18_to_30_inclusive",
            "aest_aedt_application_deadline",
            "age_at_application_vs_decision",
        ],
    },
    "financial_capacity": {
        "topics": ["financial_capacity"],
        "review_points": [
            "usual_aud_5000_initial_funds",
            "onward_travel_fare",
            "onshore_vs_offshore_evidence",
        ],
    },
    "health_character_and_history": {
        "topics": [
            "health",
            "character",
            "government_debt",
            "immigration_history",
        ],
        "review_points": [
            "health_requirement",
            "character_requirement",
            "australian_government_debt",
            "previous_visa_cancellation",
            "previous_application_refusal",
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
        content = raw.decode("utf-8-sig")
        lines = content.splitlines()
        header = "\n".join(lines[:35])

        if len(content) <= 1000:
            raise ValueError(f"Source too short: {tab}")

        if not re.search(r"subclass\s+462", content, re.I):
            raise ValueError(f"Wrong subclass: {tab}")

        if not re.search(
            r"\bThird Work and Holiday visa\b",
            header,
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
        raise ValueError("Duplicate source tabs")

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
                f"Eligibility heading mismatch: {heading}: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Eligibility headings out of order")

    footers = [
        i for i, line in enumerate(lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(footers) != 1 or footers[0] <= positions[-1]:
        raise ValueError("Eligibility footer mismatch")

    sections = []
    evidence = []
    policies = []

    for index, (topic, heading) in enumerate(HEADINGS):
        start = positions[index]

        end = (
            positions[index + 1]
            if index + 1 < len(positions)
            else footers[0]
        )

        original_text = "\n".join(lines[start:end]).strip()

        if not original_text.startswith(heading):
            raise ValueError(f"Invalid section: {heading}")

        if len(original_text.splitlines()) < 2:
            raise ValueError(f"Missing details: {heading}")

        number = index + 1
        section_id = f"AU_462_THIRD_ELIG_{number:02d}"

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
            "evidence_id": f"AU_462_THIRD_EVD_{number:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "start_line": start + 1,
            "end_line": end,
            "exact_quote": original_text,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"AU_462_THIRD_POL_{number:02d}",
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
            i for i, line in enumerate(lines)
            if line.strip() == f"Step {number}"
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Step {number} mismatch: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Application step order mismatch")

    footer_candidates = [
        i for i in range(positions[-1] + 1, len(lines))
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


def extract_passport_countries(section):
    lines = section["original_text"].splitlines()

    starts = [
        i for i, line in enumerate(lines)
        if "one of these countries:" in line
    ]

    if len(starts) != 1:
        raise ValueError("Passport country list start missing")

    countries = [
        line.strip()
        for line in lines[starts[0] + 1:]
        if line.strip()
    ]

    if len(countries) != 30:
        raise ValueError(
            f"Passport country count mismatch: {len(countries)}"
        )

    if len(set(countries)) != 30:
        raise ValueError("Duplicate passport countries")

    return {
        "source_section_id": section["section_id"],
        "countries_as_published": countries,
        "normalised_country_mapping": None,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }


def extract_special_conditions(sections):
    by_topic = {
        section["topic"]: section
        for section in sections
    }

    previous = by_topic["previous_visa"]
    financial = by_topic["financial_capacity"]
    work = by_topic["specified_work"]
    age = by_topic["age"]

    previous_text = previous["original_text"]
    financial_text = financial["original_text"]
    work_text = work["original_text"]
    age_text = age["original_text"]

    if not all([
        re.search(
            r"second Work and Holiday visa\s*\(subclass 462\)",
            previous_text,
            re.I,
        ),
        re.search(
            r"bridging visa that came into effect",
            previous_text,
            re.I,
        ),
        re.search(r"28 days", previous_text, re.I),
        re.search(
            r"complied with all the conditions",
            previous_text,
            re.I,
        ),
    ]):
        raise ValueError(
            "Second visa or bridging visa conditions missing"
        )

    if not re.search(
        r"6 months of specified subclass 462 work",
        work_text,
        re.I,
    ):
        raise ValueError("Six-month work requirement missing")

    if not (
        re.search(r"AUD\s*5,000", financial_text, re.I)
        and "fare" in financial_text.lower()
    ):
        raise ValueError("Financial guidance missing")

    if not re.search(
        r"18 to 30 years old\s*\(inclusive\)",
        age_text,
        re.I,
    ):
        raise ValueError("Age requirement missing")

    return {
        "previous_visa_conditions": {
            "source_section_id": previous["section_id"],
            "prior_visa_subclass": "462",
            "prior_visa_sequence": "second",
            "qualifying_bridging_visa": {
                "description": (
                    "Bridging visa that came into effect when "
                    "the second subclass 462 visa expired"
                ),
                "eligibility_rule": None,
                "review_status": "needs_review",
            },
            "previous_462_visa_condition_compliance": True,
            "onshore_application": {
                "substantive_visa_or_recent_expiry": True,
                "mentioned_days": 28,
                "operator_and_boundary": "review_source_text",
            },
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "specified_work": {
            "source_section_id": work["section_id"],
            "standard_requirement": {
                "duration": "6 months",
                "work_type": "specified subclass 462 work",
            },
            "eligible_jobs_and_locations": None,
            "duration_calculation": None,
            "accepted_evidence": None,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "age": {
            "source_section_id": age["section_id"],
            "minimum_age": 18,
            "maximum_age": 30,
            "application_deadline_timezone": "AEST/AEDT",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "financial_guidance": {
            "source_section_id": financial["section_id"],
            "usual_initial_funds_aud": 5000,
            "onward_travel_fare": "additional",
            "onshore_offshore_evidence": "review_source_text",
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

    by_topic = {
        section["topic"]: section
        for section in sections
    }

    topic_map = {
        topic: section["section_id"]
        for topic, section in by_topic.items()
    }

    passport_countries = extract_passport_countries(
        by_topic["passport"]
    )

    special_conditions = extract_special_conditions(sections)

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
        "stream": "third_work_and_holiday",
        "pathway_type": "work_and_holiday",
        "official_sources": sources,
        "eligibility_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "application_steps": steps,
        "passport_country_guidance": passport_countries,
        "conditional_requirements": review_groups,
        "special_conditions": special_conditions,
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
        and len(
            passport_countries["countries_as_published"]
        ) == 30
        and len(review_groups) == 6
    ):
        raise ValueError("462 Third data count mismatch")

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
        raise ValueError("Unapproved eligibility policy detected")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== 462 THIRD WORK AND HOLIDAY ===")
    print("SOURCE TABS:", len(sources))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("APPLICATION STEPS:", len(steps))
    print(
        "PASSPORT COUNTRIES:",
        len(passport_countries["countries_as_published"]),
    )
    print("REVIEW GROUPS:", len(review_groups))
    print("PREVIOUS SECOND 462 VISA: NEEDS_REVIEW")
    print("SPECIFIED WORK: 6 MONTHS")
    print("BRIDGING VISA CONDITIONS: NEEDS_REVIEW")
    print("ONSHORE APPLICATION: NEEDS_REVIEW")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_462_third"])


"""
Australia - Subclass 417 Third Working Holiday visa.

Extract source-linked evidence, policy candidates, application
steps, country-specific age guidance and conditional requirements.

All rules remain unapproved pending legal review.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = ROOT / "data/raw/australia/working_holiday"

OUTPUT = (
    ROOT / "data/processed/australia/working_holiday"
    / "subclass_417_third_evidence_draft.json"
)

PREFIX = "subclass_417_third"

SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/work-holiday-417/"
    "third-working-holiday-417"
)

TABS = [
    "about_this_visa",
    "eligibility",
    "step_by_step",
    "when_you_have_this_visa",
]

HEADINGS = [
    ("passport", "Hold this passport"),
    ("previous_visa", "Current or previous visa"),
    ("financial_capacity", "Have enough money"),
    ("specified_work", "Specified work"),
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
            "passport_validity",
            "special_passport_conditions",
        ],
    },
    "age_by_nationality": {
        "topics": ["age"],
        "review_points": [
            "country_specific_age_limit",
            "aest_aedt_application_deadline",
            "age_at_application_vs_decision",
        ],
    },
    "previous_visa_and_location": {
        "topics": ["previous_visa"],
        "review_points": [
            "previous_second_subclass_417_visa",
            "qualifying_bridging_visa",
            "second_417_visa_condition_compliance",
            "substantive_visa_for_onshore_application",
            "less_than_28_days_after_substantive_visa_expiry",
        ],
    },
    "specified_work": {
        "topics": ["specified_work"],
        "review_points": [
            "six_months_specified_417_work",
            "eligible_work_types",
            "eligible_regions_and_dates",
            "accepted_work_evidence",
            "uk_passport_exception_from_2024_07_01",
        ],
    },
    "financial_capacity": {
        "topics": ["financial_capacity"],
        "review_points": [
            "usual_aud_5000_initial_funds",
            "onward_travel_fare",
            "onshore_vs_offshore_financial_evidence",
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
            "government_debt",
            "visa_refusal_or_cancellation",
            "australian_values_statement",
        ],
    },
}


def load_sources():
    sources = {}
    contents = []
    lines_by_tab = {}

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

        if not re.search(r"subclass\s+417", content, re.I):
            raise ValueError(f"Wrong subclass: {tab}")

        if not re.search(
            r"\bThird Working Holiday visa\b",
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
        raise ValueError("Duplicate Third 417 source tabs")

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
                f"Heading mismatch: {heading} -> {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Eligibility heading order mismatch")

    footer = [
        i for i, line in enumerate(lines)
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
            raise ValueError(f"Missing details: {heading}")

        number = index + 1
        section_id = f"AU_417_THIRD_ELIG_{number:02d}"

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
            "evidence_id": f"AU_417_THIRD_EVD_{number:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "start_line": start + 1,
            "end_line": end,
            "exact_quote": original_text,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"AU_417_THIRD_POL_{number:02d}",
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

        original_text = "\n".join(
            lines[start:end]
        ).strip()

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


def extract_country_age_guidance(sections):
    section = next(
        s for s in sections if s["topic"] == "age"
    )

    entries = []

    for line in section["original_text"].splitlines():
        match = re.match(
            r"^(.+?)\s*[-–]\s*18 to (30|35) years\b",
            line.strip(),
        )

        if match:
            entries.append({
                "passport_country": match.group(1).strip(),
                "minimum_age": 18,
                "maximum_age": int(match.group(2)),
                "source_section_id": section["section_id"],
                "source_line": line.strip(),
                "eligibility_rule": None,
                "review_status": "needs_review",
            })

    if len(entries) != 19:
        raise ValueError(
            f"Country age entry mismatch: {len(entries)}"
        )

    if len({
        e["passport_country"] for e in entries
    }) != 19:
        raise ValueError("Duplicate country age entries")

    return entries


def extract_special_conditions(sections):
    by_topic = {
        s["topic"]: s
        for s in sections
    }

    visa = by_topic["previous_visa"]
    work = by_topic["specified_work"]
    finances = by_topic["financial_capacity"]

    visa_text = visa["original_text"]
    work_text = work["original_text"]
    finance_text = finances["original_text"]

    if not (
        re.search(
            r"second Working Holiday visa\s*\(subclass 417\)",
            visa_text,
            re.I,
        )
        and re.search(r"bridging visa", visa_text, re.I)
        and re.search(r"28 days", visa_text, re.I)
        and re.search(
            r"complied with all the conditions",
            visa_text,
            re.I,
        )
    ):
        raise ValueError(
            "Second visa, bridging or onshore conditions missing"
        )

    if not (
        re.search(
            r"6 months of specified subclass 417 work",
            work_text,
            re.I,
        )
        and re.search(
            r"UK passport holders",
            work_text,
            re.I,
        )
        and "1 July 2024" in work_text
    ):
        raise ValueError(
            "Specified work or UK exemption missing"
        )

    if not (
        "AUD5,000" in finance_text
        and "fare" in finance_text.lower()
    ):
        raise ValueError("Financial guidance missing")

    return {
        "previous_visa_conditions": {
            "source_section_id": visa["section_id"],
            "prior_subclass": "417",
            "prior_visa_sequence": "second",
            "qualifying_bridging_visa": {
                "description": (
                    "Bridging visa that came into effect when "
                    "the second subclass 417 visa expired"
                ),
                "eligibility_rule": None,
                "review_status": "needs_review",
            },
            "second_visa_conditions_compliance": True,
            "onshore_substantive_visa_or_recent_expiry": {
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
                "work_type": "specified subclass 417 work",
            },
            "uk_passport_exception": {
                "passport": "United Kingdom",
                "application_from": "2024-07-01",
                "requirement_waived": "6 months specified work",
                "additional_conditions": "review_source_text",
            },
            "eligible_jobs_and_locations": None,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "financial_guidance": {
            "source_section_id": finances["section_id"],
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

    age_guidance = extract_country_age_guidance(sections)

    special_conditions = extract_special_conditions(sections)

    topic_map = {
        s["topic"]: s["section_id"]
        for s in sections
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
        "stream": "third_working_holiday",
        "pathway_type": "working_holiday",
        "official_sources": sources,
        "eligibility_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "application_steps": steps,
        "country_age_guidance": age_guidance,
        "conditional_requirements": review_groups,
        "special_conditions": special_conditions,
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    if not (
        len(sources) == 4
        and len(sections) == 10
        and len(evidence) == 10
        and len(policies) == 10
        and len(steps) == 5
        and len(age_guidance) == 19
        and len(review_groups) == 6
    ):
        raise ValueError("417 Third count mismatch")

    if any(
        left["end_line"] + 1 != right["start_line"]
        for left, right in zip(sections, sections[1:])
    ):
        raise ValueError(
            "Eligibility section boundary mismatch"
        )

    if len({
        p["policy_id"] for p in policies
    }) != len(policies):
        raise ValueError("Duplicate policy IDs")

    if any(
        p["eligibility_rule"] is not None
        or p["approved_for_eligibility_decision"]
        for p in policies
    ):
        raise ValueError(
            "Unapproved eligibility policy detected"
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== 417 THIRD WORKING HOLIDAY ===")
    print("SOURCE TABS:", len(sources))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("APPLICATION STEPS:", len(steps))
    print("COUNTRY AGE ENTRIES:", len(age_guidance))
    print("REVIEW GROUPS:", len(review_groups))
    print("SPECIFIED WORK: 6 MONTHS")
    print("UK SPECIFIED WORK EXCEPTION: NEEDS_REVIEW")
    print("BRIDGING VISA CONDITIONS: NEEDS_REVIEW")
    print("ONSHORE APPLICATION CONDITIONS: NEEDS_REVIEW")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_417_third"])

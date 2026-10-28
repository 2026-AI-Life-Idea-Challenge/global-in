
"""
Australia subclass 500 - Student visa.

Extract evidence, policy candidates, application steps
and conditional review groups from official source captures.

No automatic visa-eligibility rules are approved.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / "data/raw/australia/study"
OUTPUT = (
    ROOT / "data/processed/australia/study"
    / "subclass_500_evidence_draft.json"
)

PREFIX = "subclass_500"

SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/student-500"
)

TABS = [
    "about_this_visa",
    "eligibility",
    "step_by_step",
    "when_you_have_this_visa",
]

# Verified against the captured Eligibility page.
HEADINGS = [
    ("school_student_age", "Be a certain age (school student)"),
    (
        "course_enrolment",
        "Be enrolled in a course of study and provide evidence",
    ),
    (
        "under_18_welfare",
        "Make Welfare arrangements if you are under 18 years",
    ),
    ("english", "Meet English language requirements"),
    ("health_insurance", "Have adequate health insurance"),
    ("application_location", "Apply from the right location"),
    (
        "further_student_visa",
        "Meet an exemption to apply for a further student visa in Australia",
    ),
    (
        "family_inclusion",
        "Meet an exemption if you want to include family members",
    ),
    ("financial_capacity", "Have enough money for your stay"),
    ("genuine_student", "Be a genuine student"),
    ("character", "Meet our character requirement"),
    ("health", "Meet our health requirement"),
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

REVIEW_GROUPS = {
    "enrolment_and_coe": {
        "source_topics": ["course_enrolment"],
        "review_points": [
            "cricos_course_registration",
            "confirmation_of_enrolment",
            "coe_validity_at_decision",
            "packaged_courses",
            "course_gap_rules",
            "alternative_enrolment_evidence",
        ],
    },
    "english_requirements": {
        "source_topics": ["english"],
        "review_points": [
            "approved_english_tests",
            "test_score_requirements",
            "test_validity_period",
            "regular_vs_streamlined_evidence",
            "at_home_tests_not_accepted",
            "english_evidence_exemptions",
        ],
    },
    "overseas_student_health_cover": {
        "source_topics": ["health_insurance"],
        "review_points": [
            "oshc_required_period",
            "oshc_start_date",
            "continuous_cover_for_onshore_applicants",
            "oshc_country_exemptions",
            "family_member_cover",
        ],
    },
    "onshore_application_restrictions": {
        "source_topics": [
            "application_location",
            "further_student_visa",
        ],
        "review_points": [
            "changes_effective_2026_10_02",
            "location_at_lodgement",
            "ineligible_prior_visa_subclasses",
            "primary_vs_secondary_student_visa",
            "six_further_student_visa_exemptions",
            "course_completion_exception",
            "course_progression_exception",
            "education_provider_default",
        ],
    },
    "family_inclusion": {
        "source_topics": ["family_inclusion"],
        "review_points": [
            "changes_effective_2026_10_02",
            "five_family_inclusion_exemptions",
            "phd_student",
            "dfat_or_defence_sponsorship",
            "foreign_government_scholarship",
            "pacific_or_asean_nationality",
            "existing_student_family_members",
            "same_time_and_location",
            "eligible_visa_for_onshore_family",
        ],
    },
    "financial_capacity": {
        "source_topics": ["financial_capacity"],
        "review_points": [
            "current_minimum_funds",
            "tuition_and_living_costs",
            "family_costs",
            "accepted_funding_evidence",
        ],
    },
    "genuine_student": {
        "source_topics": ["genuine_student"],
        "review_points": [
            "genuine_student_requirement",
            "primary_purpose_of_study",
            "supporting_evidence",
        ],
    },
    "minor_applicants": {
        "source_topics": [
            "school_student_age",
            "under_18_welfare",
            "best_interests_of_child",
        ],
        "review_points": [
            "minimum_school_student_age",
            "year_level_age_limits",
            "under_18_welfare_arrangements",
            "best_interests_of_child",
        ],
    },
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
            raise ValueError(f"500 invalid source size: {tab}")

        if any(
            marker in content.lower()
            for marker in ("<!doctype", "<html", "<script")
        ):
            raise ValueError(f"500 HTML source detected: {tab}")

        if not (
            re.search(r"\bsubclass\s+500\b", content, re.I)
            and re.search(r"\bStudent visa\b", content, re.I)
        ):
            raise ValueError(f"500 wrong visa source: {tab}")

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
        raise ValueError("500 duplicate source tabs")

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
                f"500 heading mismatch: {heading}: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("500 eligibility heading order mismatch")

    end_matches = [
        i for i, line in enumerate(lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(end_matches) != 1:
        raise ValueError("500 eligibility footer mismatch")

    final_end = end_matches[0]

    if final_end <= positions[-1]:
        raise ValueError("500 invalid eligibility boundary")

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
            raise ValueError(f"500 invalid section: {heading}")

        if not any(
            line.strip()
            for line in original_text.splitlines()[1:]
        ):
            raise ValueError(f"500 missing details: {heading}")

        section_id = f"AU_500_ELIG_{index + 1:02d}"

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
            "evidence_id": f"AU_500_EVD_{index + 1:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "exact_quote": original_text,
            "start_line": start + 1,
            "end_line": end,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"AU_500_POL_{index + 1:02d}",
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
            i for i, line in enumerate(lines)
            if line.strip() == f"Step {number}"
        ]

        if len(matches) != 1:
            raise ValueError(
                f"500 Step {number} mismatch: {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("500 application step order mismatch")

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
            raise ValueError(f"500 empty Step {index + 1}")

        steps.append({
            "step_number": index + 1,
            "source_tab": "step_by_step",
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "review_status": "needs_review",
        })

    return steps


def extract_exemptions(sections):
    by_topic = {
        section["topic"]: section
        for section in sections
    }

    configs = [
        ("further_student_visa", 6),
        ("family_inclusion", 5),
    ]

    result = {}

    for topic, expected_count in configs:
        section = by_topic[topic]

        matches = re.findall(
            r"(?m)^Exemption\s+(\d+)\s*[–-]\s*([^\n]+)",
            section["original_text"],
        )

        numbers = [int(number) for number, _ in matches]

        if numbers != list(range(1, expected_count + 1)):
            raise ValueError(
                f"500 {topic} exemption mismatch: {numbers}"
            )

        result[topic] = {
            "source_section_id": section["section_id"],
            "exemptions": [
                {
                    "number": int(number),
                    "heading": heading.strip(),
                    "specific_conditions": "see_source_section",
                    "eligibility_rule": None,
                    "review_status": "needs_review",
                }
                for number, heading in matches
            ],
            "review_status": "needs_review",
        }

    return result


def main():
    sources, lines_by_tab = load_sources()

    sections, evidence, policies = extract_eligibility(
        lines_by_tab["eligibility"],
        sources["eligibility"]["source_sha256"],
    )

    steps = extract_steps(lines_by_tab["step_by_step"])

    exemptions = extract_exemptions(sections)

    topic_to_section = {
        section["topic"]: section["section_id"]
        for section in sections
    }

    review_groups = {}

    for name, config in REVIEW_GROUPS.items():
        review_groups[name] = {
            "source_section_ids": [
                topic_to_section[topic]
                for topic in config["source_topics"]
            ],
            "review_points": config["review_points"],
            "eligibility_rule": None,
            "review_status": "needs_review",
        }

    result = {
        "program": PREFIX,
        "visa_subclass": "500",
        "stream": "student",
        "pathway_type": "temporary_study",
        "official_sources": sources,
        "eligibility_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "application_steps": steps,
        "conditional_requirements": review_groups,
        "exemption_groups": exemptions,
        "regulatory_changes": {
            "effective_date": "2026-10-02",
            "source_tab": "eligibility",
            "affected_topics": [
                "application_location",
                "further_student_visa",
                "family_inclusion",
                "course_enrolment",
            ],
            "review_status": "needs_review",
        },
        "financial_threshold": {
            "amount": None,
            "currency": "AUD",
            "source_topic": "financial_capacity",
            "review_status": "needs_review",
        },
        "english_score_requirements": {
            "source_topic": "english",
            "specific_scores": None,
            "review_status": "needs_review",
        },
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # Consolidated integrity checks
    if not (
        len(sources) == 4
        and len(sections) == 16
        and len(evidence) == 16
        and len(policies) == 16
        and len(steps) == 5
        and len(review_groups) == 8
        and len(exemptions["further_student_visa"]["exemptions"]) == 6
        and len(exemptions["family_inclusion"]["exemptions"]) == 5
    ):
        raise ValueError("500 data count mismatch")

    if any(
        left["end_line"] + 1 != right["start_line"]
        for left, right in zip(sections, sections[1:])
    ):
        raise ValueError("500 eligibility section boundary gap")

    if len({p["policy_id"] for p in policies}) != 16:
        raise ValueError("500 duplicate policy IDs")

    if any(
        p["eligibility_rule"] is not None
        or p["approved_for_eligibility_decision"]
        for p in policies
    ):
        raise ValueError("500 unapproved executable policy")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== 500 STUDENT VISA ===")
    print("SOURCE TABS:", len(sources))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("APPLICATION STEPS:", len(steps))
    print("REVIEW GROUPS:", len(review_groups))
    print(
        "ONSHORE STUDENT EXEMPTIONS:",
        len(exemptions["further_student_visa"]["exemptions"]),
    )
    print(
        "FAMILY INCLUSION EXEMPTIONS:",
        len(exemptions["family_inclusion"]["exemptions"]),
    )
    print("2026-10-02 CHANGES: NEEDS_REVIEW")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_500"])

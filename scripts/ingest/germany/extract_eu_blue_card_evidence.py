
"""
Germany EU Blue Card (§18g) - Evidence Draft

Source: Make it in Germany, EU Blue Card (2026).

Separate four policy candidate pathways without approving
any automatic eligibility decision.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data/raw/germany/employment"
    / "eu_blue_card_make_it_in_germany_en.txt"
)

OUTPUT = (
    ROOT / "data/processed/germany/employment"
    / "eu_blue_card_evidence_draft.json"
)

SOURCE_URL = (
    "https://www.make-it-in-germany.com/en/"
    "visa-residence/types/eu-blue-card"
)

HEADINGS = [
    ("overview", "What is the EU Blue Card?"),
    (
        "requirements",
        "Overview of the requirements for the EU Blue Card",
    ),
    (
        "young_professionals",
        "EU Blue Card for young professionals",
    ),
    (
        "residence_and_settlement",
        "How to live and work with the EU Blue Card",
    ),
    (
        "change_of_employment",
        "What to consider when changing jobs with the EU Blue Card",
    ),
    (
        "it_without_degree",
        "EU Blue Card without a degree: opportunities for IT specialists",
    ),
    ("online_application", "Apply for the EU Blue Card online"),
]

PATHWAYS = [
    {
        "id": "general",
        "name": "General EU Blue Card",
        "topic": "requirements",
        "start_marker": (
            "You have a German academic qualification"
        ),
        "end_marker": (
            "If you are employed in a shortage occupation"
        ),
        "salary_eur_2026": 50700,
        "review_points": [
            "german_or_comparable_foreign_degree",
            "qualifying_tertiary_level_nonacademic_qualification",
            "qualification_level_iscED_or_EQF_6",
            "job_offer_at_least_six_months",
            "qualification_matching_job",
            "regulated_profession_licence",
            "gross_annual_salary_threshold",
        ],
    },
    {
        "id": "shortage_occupation",
        "name": "EU Blue Card - Shortage Occupations",
        "topic": "requirements",
        "start_marker": (
            "If you are employed in a shortage occupation"
        ),
        "end_marker": None,
        "salary_eur_2026": 45934.20,
        "review_points": [
            "qualifying_degree_or_equivalent_qualification",
            "specific_shortage_occupation",
            "official_detailed_shortage_occupation_list",
            "six_month_employment_requirement",
            "gross_annual_salary_threshold",
            "federal_employment_agency_approval",
        ],
    },
    {
        "id": "young_professional",
        "name": "EU Blue Card - New Labour Market Entrants",
        "topic": "young_professionals",
        "start_marker": (
            "The following applies to new entrants"
        ),
        "end_marker": None,
        "salary_eur_2026": 45934.20,
        "review_points": [
            "last_degree_or_equivalent_qualification",
            "qualification_obtained_less_than_three_years_ago",
            "entry_level_jobs_all_professions",
            "six_month_employment_requirement",
            "gross_annual_salary_threshold",
            "federal_employment_agency_approval",
        ],
    },
    {
        "id": "it_without_degree",
        "name": "EU Blue Card - IT Without Formal Qualification",
        "topic": "it_without_degree",
        "start_marker": (
            "You must be able to demonstrate"
        ),
        "end_marker": (
            "Do you meet the above-mentioned requirements?"
        ),
        "salary_eur_2026": 45934.20,
        "review_points": [
            "it_professional_or_manager_job_offer",
            "six_month_employment_requirement",
            "gross_annual_salary_threshold",
            "three_years_it_experience_within_seven_years",
            "university_level_professional_experience",
            "professional_experience_required_for_employment",
            "agency_approval_applicability_to_verify",
        ],
    },
]

REVIEW_GROUPS = {
    "qualification_recognition": [
        "academic_degree_comparability",
        "tertiary_level_qualification",
        "ISCED_or_EQF_level_6",
        "regulated_profession_licence",
    ],
    "employment_contract": [
        "specific_job_offer",
        "minimum_six_month_employment",
        "qualification_job_match",
        "salary_contract_evidence",
    ],
    "salary_and_special_pathways": [
        "2026_general_salary_threshold",
        "2026_reduced_salary_threshold",
        "shortage_occupation_list",
        "new_entrant_qualification_date",
        "IT_professional_experience",
        "BA_approval_scope",
    ],
    "residence_and_settlement": [
        "contract_duration_plus_six_months",
        "maximum_four_year_validity",
        "A1_and_27_months_settlement",
        "B1_and_21_months_settlement",
        "family_reunification",
    ],
    "employment_change": [
        "change_within_first_year",
        "notification_to_foreigners_authority",
        "new_job_eligibility_check",
    ],
    "application_and_legal_review": [
        "consular_services_portal",
        "visa_vs_residence_permit",
        "annual_salary_threshold_updates",
        "official_law_and_BA_guidance",
    ],
}


def read_source():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()

    if len(text) < 7000:
        raise ValueError("EU Blue Card source unexpectedly short")

    markers = [
        "EU Blue Card",
        "Section 18g",
        "€50,700",
        "€45,934.20",
        "Federal Employment Agency",
        "three of the past seven years",
        "Apply for the EU Blue Card online",
    ]

    for marker in markers:
        if marker not in text:
            raise ValueError(f"Missing source marker: {marker}")

    if re.search(r"<!DOCTYPE|<html|<script", text, re.I):
        raise ValueError("Unexpected HTML source")

    return raw, text, lines


def extract_sections(lines, source_hash):
    # Main content starts after the on-page navigation.
    starts = [
        i for i, line in enumerate(lines)
        if line.strip().startswith(
            "The EU Blue Card (Section 18g"
        )
    ]

    if len(starts) != 1:
        raise ValueError("Main content start not found")

    content_start = starts[0] - 1

    positions = []

    for topic, heading in HEADINGS:
        matches = [
            i for i, line in enumerate(lines)
            if i >= content_start and line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Heading mismatch: {heading} -> {matches}"
            )

        positions.append((topic, heading, matches[0]))

    indices = [position[2] for position in positions]

    if indices != sorted(indices):
        raise ValueError("Section headings out of order")

    ends = [
        i for i, line in enumerate(lines)
        if i > indices[-1]
        and line.strip() == "Information on the web"
    ]

    if len(ends) != 1:
        raise ValueError("Main content end not found")

    sections = []

    for index, (topic, heading, start) in enumerate(positions):
        end = (
            positions[index + 1][2]
            if index + 1 < len(positions)
            else ends[0]
        )

        original_text = "\n".join(lines[start:end]).strip()

        if len(original_text) < 60:
            raise ValueError(f"Section too short: {topic}")

        sections.append({
            "section_id": f"DE_BLUE_CARD_SEC_{index + 1:02d}",
            "topic": topic,
            "heading": heading,
            "source_sha256": source_hash,
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "review_status": "needs_review",
        })

    return sections


def extract_pathway_text(lines, section, config):
    start = section["start_line"] - 1
    end = section["end_line"]

    start_matches = [
        i for i in range(start, end)
        if lines[i].strip().startswith(config["start_marker"])
    ]

    if len(start_matches) != 1:
        raise ValueError(
            f"Pathway start mismatch: {config['id']}"
        )

    quote_start = start_matches[0]

    if config["end_marker"] is None:
        quote_end = end
    else:
        end_matches = [
            i for i in range(quote_start + 1, end)
            if lines[i].strip().startswith(config["end_marker"])
        ]

        if len(end_matches) != 1:
            raise ValueError(
                f"Pathway end mismatch: {config['id']}"
            )

        quote_end = end_matches[0]

    quote = "\n".join(
        lines[quote_start:quote_end]
    ).strip()

    if len(quote) < 80:
        raise ValueError(
            f"Pathway evidence too short: {config['id']}"
        )

    return quote, quote_start + 1, quote_end


def build_pathways(lines, sections):
    by_topic = {
        section["topic"]: section
        for section in sections
    }

    pathways = []
    evidence = []
    policies = []

    for index, config in enumerate(PATHWAYS, 1):
        section = by_topic[config["topic"]]

        quote, first, last = extract_pathway_text(
            lines, section, config
        )

        if (
            f"€{config['salary_eur_2026']:,.0f}" not in quote
            and f"€{config['salary_eur_2026']:,.2f}" not in quote
        ):
            raise ValueError(
                f"Salary marker missing: {config['id']}"
            )

        evidence_id = f"DE_BLUE_CARD_EVD_{index:02d}"
        policy_id = f"DE_BLUE_CARD_POL_{index:02d}"

        evidence.append({
            "evidence_id": evidence_id,
            "pathway": config["id"],
            "source_section_id": section["section_id"],
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": policy_id,
            "pathway": config["id"],
            "source_evidence_id": evidence_id,
            "source_text": quote,
            "requirement_type": "needs_review",
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

        pathways.append({
            "pathway_id": config["id"],
            "name": config["name"],
            "salary_threshold": {
                "year": 2026,
                "currency": "EUR",
                "gross_annual_eur": config["salary_eur_2026"],
                "review_status": "needs_review",
            },
            "source_evidence_id": evidence_id,
            "policy_candidate_id": policy_id,
            "review_points": config["review_points"],
            "eligibility_rule": None,
            "review_status": "needs_review",
        })

    return pathways, evidence, policies


def validate_details(text):
    checks = {
        "contract_six_months": bool(
            re.search(r"at least six months", text, re.I)
        ),
        "qualification": (
            "level 6" in text
            and "at least three years" in text
        ),
        "shortage_ba_approval": (
            "shortage occupation" in text
            and "BA) has approved" in text
        ),
        "new_entrant": (
            "less than three years ago" in text
        ),
        "it_experience": (
            "three of the past seven years" in text
        ),
        "residence_max_four_years": (
            "maximum of four years" in text
        ),
        "settlement_27_months": (
            "After 27 months" in text
        ),
        "settlement_21_months": (
            "after only 21 months" in text
        ),
        "employer_change": (
            "within the first year" in text
        ),
        "online_application": (
            "Consular Services Portal" in text
        ),
    }

    missing = [
        name for name, passed in checks.items()
        if not passed
    ]

    if missing:
        raise ValueError(
            f"Missing source details: {missing}"
        )

    return checks


def main():
    raw, text, lines = read_source()
    source_hash = hashlib.sha256(raw).hexdigest()

    sections = extract_sections(lines, source_hash)

    pathways, evidence, policies = build_pathways(
        lines, sections
    )

    checks = validate_details(text)

    review_groups = {
        name: {
            "review_points": points,
            "eligibility_rule": None,
            "review_status": "needs_review",
        }
        for name, points in REVIEW_GROUPS.items()
    }

    result = {
        "country": "Germany",
        "program": "eu_blue_card",
        "visa_or_residence_title": "EU Blue Card",
        "legal_basis": "AufenthG Section 18g",
        "pathway_type": "employment",
        "official_source": {
            "authority": (
                "German Federal Government - "
                "Make it in Germany"
            ),
            "source_url": SOURCE_URL,
            "source_language": "en",
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "char_count": len(text),
            "line_count": len(lines),
        },
        "evidence_sections": sections,
        "eligibility_pathways": pathways,
        "evidence": evidence,
        "policy_candidates": policies,
        "source_requirement_checks": checks,
        "conditional_requirements": review_groups,
        "salary_reference_year": 2026,
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # Supplementary evidence from the German Embassy in Seoul.
    # Keep the existing four Blue Card pathways unchanged.
    embassy_path = (
        ROOT / "data/raw/germany/employment"
        / "eu_blue_card_seoul_embassy_faq_ko.txt"
    )

    if not embassy_path.is_file():
        raise FileNotFoundError(embassy_path)

    embassy_raw = embassy_path.read_bytes()
    embassy_text = embassy_raw.decode("utf-8-sig")
    embassy_lines = embassy_text.splitlines()
    embassy_hash = hashlib.sha256(embassy_raw).hexdigest()

    required_markers = [
        "구직 및 취업 비자 관련 자주 묻는 질문",
        "블루카드(Blue Card)",
        "ANABIN",
        "고용계약서",
        "취업 제안서",
    ]

    for marker in required_markers:
        if marker not in embassy_text:
            raise ValueError(
                f"Embassy FAQ marker missing: {marker}"
            )

    embassy_source = {
        "authority": "German Embassy in Seoul",
        "source_url": (
            "https://seoul.diplo.de/kr-ko/service/"
            "visa-einreise/2100784-2100784"
        ),
        "source_language": "ko",
        "source_file": embassy_path.relative_to(ROOT).as_posix(),
        "source_sha256": embassy_hash,
        "char_count": len(embassy_text),
        "line_count": len(embassy_lines),
        "review_status": "needs_review",
    }

    faq_ranges = [
        ("general_employment_original_documents", 22, 23),
        ("blue_card_application_and_documents", 28, 34),
    ]

    embassy_evidence = []

    for index, (topic, first, last) in enumerate(
        faq_ranges, 1
    ):
        quote = "\n".join(
            embassy_lines[first - 1:last]
        ).strip()

        if len(quote) < 30:
            raise ValueError(
                f"Embassy evidence too short: {topic}"
            )

        embassy_evidence.append({
            "evidence_id": f"DE_BLUE_CARD_EMBASSY_EVD_{index:02d}",
            "topic": topic,
            "source_file": embassy_source["source_file"],
            "source_sha256": embassy_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["embassy_source"] = embassy_source
    result["embassy_evidence"] = embassy_evidence

    result["embassy_document_review"] = {
        "source_evidence_ids": [
            "DE_BLUE_CARD_EMBASSY_EVD_01",
            "DE_BLUE_CARD_EMBASSY_EVD_02",
        ],
        "documents_to_review": [
            "employment_contract_or_specific_job_offer",
            "degree_recognition_via_anabin_if_applicable",
            "degree_comparison_printout_if_applicable",
            "original_document_submission_requirements",
        ],
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["embassy_scope_notes"] = [
        {
            "topic": "academic_qualification",
            "finding": (
                "Embassy FAQ primarily describes degree-based "
                "Blue Card applications. Do not apply this "
                "requirement to the IT-without-degree pathway."
            ),
            "source_evidence_id": "DE_BLUE_CARD_EMBASSY_EVD_02",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        {
            "topic": "salary",
            "finding": (
                "Embassy FAQ does not state the 2026 salary "
                "amounts. Preserve the federal source values."
            ),
            "source_evidence_id": "DE_BLUE_CARD_EMBASSY_EVD_02",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        {
            "topic": "document_submission",
            "finding": (
                "Original-document guidance is general employment "
                "visa guidance. Verify its applicability to "
                "the current online application process."
            ),
            "source_evidence_id": "DE_BLUE_CARD_EMBASSY_EVD_01",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    ]

    if not (
        len(sections) == 7
        and len(pathways) == 4
        and len(evidence) == 4
        and len(policies) == 4
        and len(review_groups) == 6
        and len(checks) == 10
        and all(checks.values())
    ):
        raise ValueError("Evidence consistency check failed")

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

    print("=== GERMANY EU BLUE CARD EVIDENCE ===")
    print("SOURCE CHARS:", len(text))
    print("SOURCE LINES:", len(lines))
    print("EVIDENCE SECTIONS:", len(sections))
    print("ELIGIBILITY PATHWAYS:", len(pathways))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("SOURCE CHECKS:", len(checks))
    print("REVIEW GROUPS:", len(review_groups))
    print("SALARY REFERENCE YEAR: 2026")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
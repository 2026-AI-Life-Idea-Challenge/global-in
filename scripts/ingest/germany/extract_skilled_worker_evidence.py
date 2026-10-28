
"""
Germany Skilled Worker Visa (§18a / §18b).

Extract source-linked evidence from Make it in Germany.
Keep two legal pathways under one program.

All eligibility candidates require legal review.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data/raw/germany/employment"
    / "skilled_worker_make_it_in_germany_en.txt"
)

OUTPUT = (
    ROOT / "data/processed/germany/employment"
    / "skilled_worker_evidence_draft.json"
)

SOURCE_URL = (
    "https://www.make-it-in-germany.com/en/"
    "visa-residence/types/work-qualified-professionals"
)

SECTION_DEFINITIONS = [
    (
        "overview",
        "Who is the work visa for qualified professionals intended for?",
    ),
    (
        "requirements",
        "Requirements for the work visa for qualified professionals at a glance",
    ),
    (
        "ba_approval",
        "Approval from the Federal Employment Agency required",
    ),
    (
        "residence_prospects",
        "Your opportunities with the work visa for qualified professionals",
    ),
    (
        "online_application",
        "Apply for the work visa for qualified professionals online",
    ),
]

PATHWAYS = [
    {
        "pathway_id": "vocational_training",
        "name": "Skilled Worker with Vocational Training",
        "legal_basis": "AufenthG Section 18a",
        "qualification_to_review": (
            "Recognised qualified vocational training"
        ),
        "application_link_label": (
            "For qualified professionals with vocational training"
        ),
    },
    {
        "pathway_id": "academic_qualification",
        "name": "Skilled Worker with Academic Qualification",
        "legal_basis": "AufenthG Section 18b",
        "qualification_to_review": (
            "German or comparable foreign academic qualification"
        ),
        "application_link_label": (
            "For qualified professionals with a university degree"
        ),
    },
]

REVIEW_GROUPS = {
    "qualification_recognition": [
        "recognised_vocational_qualification_18a",
        "german_or_comparable_academic_degree_18b",
        "qualification_recognition_evidence",
    ],
    "qualified_employment": [
        "specific_job_offer",
        "qualified_position",
        "auxiliary_work_exclusion",
        "qualification_job_match_not_generally_required",
    ],
    "regulated_professions": [
        "professional_practice_licence",
        "regulated_occupation_status",
    ],
    "age_and_financial_security": [
        "over_45_first_employment",
        "2026_gross_salary_55770_eur",
        "adequate_pension_provision_alternative",
    ],
    "federal_employment_agency": [
        "BA_approval_general_requirement",
        "employment_conditions_review",
        "applicable_exceptions",
    ],
    "residence_and_settlement": [
        "maximum_four_year_residence",
        "employment_contract_plus_six_months",
        "settlement_permit_after_three_years",
        "family_reunification",
    ],
    "application_process": [
        "consular_services_portal",
        "degree_based_application",
        "vocational_training_application",
        "current_embassy_document_requirements",
    ],
}

REQUIRED_MARKERS = {
    "section_18a": r"Section 18a",
    "section_18b": r"Section 18b",
    "recognition": r"recognised in Germany",
    "job_offer": r"specific job offer",
    "qualified_employment": r"qualified position",
    "unrelated_job": r"does not have to be related",
    "regulated_licence": r"licence to practise",
    "over_45": r"over the age of 45",
    "salary_2026": r"55,770",
    "pension_alternative": r"adequate pension provision",
    "ba_approval": r"Federal Employment Agency.*approve",
    "four_years": r"maximum of four years",
    "contract_extension": r"additional six months",
    "settlement": r"at least three years",
    "online_application": r"Consular Services Portal",
}


def read_source():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()

    if len(text) < 4000:
        raise ValueError("Skilled Worker source is too short")

    if "Work visa for qualified professionals" not in text:
        raise ValueError("Incorrect visa source")

    if re.search(r"<!DOCTYPE|<html|<script", text, re.I):
        raise ValueError("Unexpected HTML source")

    checks = {}

    for name, pattern in REQUIRED_MARKERS.items():
        matched = bool(re.search(pattern, text, re.I))
        checks[name] = matched

        if not matched:
            raise ValueError(f"Missing source marker: {name}")

    return raw, text, lines, checks


def find_main_sections(lines, source_hash):
    # Main content follows the on-page navigation.
    introduction = [
        i
        for i, line in enumerate(lines)
        if line.strip().startswith(
            "Have you completed academic studies"
        )
    ]

    if len(introduction) != 1:
        raise ValueError("Main content introduction not found")

    content_start = introduction[0] - 1
    positions = []

    for topic, heading in SECTION_DEFINITIONS:
        matches = [
            i
            for i, line in enumerate(lines)
            if i >= content_start
            and line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Section heading mismatch: {heading}: {matches}"
            )

        positions.append((topic, heading, matches[0]))

    indices = [item[2] for item in positions]

    if indices != sorted(indices):
        raise ValueError("Section order mismatch")

    footer = [
        i
        for i, line in enumerate(lines)
        if i > indices[-1]
        and line.strip() == "Information on the web"
    ]

    if len(footer) != 1:
        raise ValueError("Main content footer missing")

    sections = []

    for index, (topic, heading, start) in enumerate(positions):
        end = (
            positions[index + 1][2]
            if index + 1 < len(positions)
            else footer[0]
        )

        original_text = "\n".join(
            lines[start:end]
        ).strip()

        if len(original_text) < 70:
            raise ValueError(f"Section too short: {topic}")

        sections.append({
            "section_id": f"DE_SKILLED_SEC_{index + 1:02d}",
            "topic": topic,
            "heading": heading,
            "start_line": start + 1,
            "end_line": end,
            "source_sha256": source_hash,
            "original_text": original_text,
            "review_status": "needs_review",
        })

    return sections


def requirement_evidence(lines, sections):
    by_topic = {
        section["topic"]: section
        for section in sections
    }

    requirements = by_topic["requirements"]

    # Source-specific end marker: requirements before EU Blue Card info.
    start = requirements["start_line"]
    end = requirements["end_line"]

    extracted = []

    for index in range(start, end):
        value = lines[index].strip()

        if not value:
            continue

        if value.startswith((
            "Do you meet the above requirements?",
            "EU Blue Card:",
            "Here you find an overview",
        )):
            break

        if value.startswith("Requirements for"):
            continue

        extracted.append({
            "source_line": index + 1,
            "exact_quote": value,
        })

    if len(extracted) != 4:
        raise ValueError(
            f"Expected four requirement statements, got {len(extracted)}"
        )

    return extracted


def build_pathways(sections, requirements):
    by_topic = {
        section["topic"]: section
        for section in sections
    }

    eligibility_pathways = []
    evidence = []
    policy_candidates = []

    for index, pathway in enumerate(PATHWAYS, 1):
        pathway_id = pathway["pathway_id"]
        evidence_id = f"DE_SKILLED_EVD_{index:02d}"
        policy_id = f"DE_SKILLED_POL_{index:02d}"

        overview = by_topic["overview"]["original_text"]

        if pathway["legal_basis"].split()[-1] not in overview:
            raise ValueError(
                f"Legal basis not present: {pathway_id}"
            )

        application_text = by_topic[
            "online_application"
        ]["original_text"]

        if pathway["application_link_label"] not in application_text:
            raise ValueError(
                f"Application pathway not present: {pathway_id}"
            )

        source_quotes = [
            {
                "source_section_id": by_topic["overview"]["section_id"],
                "exact_quote": overview,
            },
            {
                "source_section_id": (
                    by_topic["requirements"]["section_id"]
                ),
                "exact_quote": (
                    by_topic["requirements"]["original_text"]
                ),
            },
            {
                "source_section_id": (
                    by_topic["ba_approval"]["section_id"]
                ),
                "exact_quote": (
                    by_topic["ba_approval"]["original_text"]
                ),
            },
        ]

        evidence.append({
            "evidence_id": evidence_id,
            "pathway_id": pathway_id,
            "source_quotes": source_quotes,
            "requirement_lines": requirements,
            "review_status": "needs_review",
        })

        policy_candidates.append({
            "policy_id": policy_id,
            "pathway_id": pathway_id,
            "source_evidence_id": evidence_id,
            "requirement_type": "needs_review",
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

        eligibility_pathways.append({
            **pathway,
            "source_evidence_id": evidence_id,
            "policy_candidate_id": policy_id,
            "eligibility_rule": None,
            "review_status": "needs_review",
        })

    return eligibility_pathways, evidence, policy_candidates


def main():
    raw, text, lines, checks = read_source()
    source_hash = hashlib.sha256(raw).hexdigest()

    sections = find_main_sections(
        lines, source_hash
    )

    requirements = requirement_evidence(
        lines, sections
    )

    pathways, evidence, policies = build_pathways(
        sections, requirements
    )

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
        "program": "skilled_worker",
        "pathway_type": "employment",
        "legal_bases": [
            "AufenthG Section 18a",
            "AufenthG Section 18b",
        ],
        "official_source": {
            "authority": (
                "German Federal Government - Make it in Germany"
            ),
            "source_url": SOURCE_URL,
            "source_language": "en",
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "char_count": len(text),
            "line_count": len(lines),
        },
        "evidence_sections": sections,
        "shared_requirement_evidence": requirements,
        "eligibility_pathways": pathways,
        "evidence": evidence,
        "policy_candidates": policies,
        "source_requirement_checks": checks,
        "conditional_requirements": review_groups,
        "salary_reference": {
            "year": 2026,
            "currency": "EUR",
            "gross_annual_eur": 55770,
            "scope": (
                "First-time employment in Germany "
                "for applicants over 45; "
                "adequate pension provision may be an alternative"
            ),
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "related_program_to_review": "eu_blue_card",
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # Additional evidence from the German Embassy in Seoul.
    # Keep Section 18a and Section 18b pathways unchanged.
    embassy_path = (
        ROOT / "data/raw/germany/employment"
        / "skilled_worker_seoul_embassy_ko.txt"
    )

    if not embassy_path.is_file():
        raise FileNotFoundError(embassy_path)

    embassy_raw = embassy_path.read_bytes()
    embassy_text = embassy_raw.decode("utf-8-sig")
    embassy_lines = embassy_text.splitlines()
    embassy_hash = hashlib.sha256(embassy_raw).hexdigest()

    # The embassy page covers multiple visa categories.
    # Only the employment-visa section is used here.
    source_boundaries = {
        73: "취업 비자",
        113: "기회 카드 (Chancenkarte)",
    }

    for line_number, expected in source_boundaries.items():
        if embassy_lines[line_number - 1].strip() != expected:
            raise ValueError(
                f"Embassy section boundary changed: {line_number}"
            )

    embassy_source = {
        "authority": "German Embassy in Seoul",
        "source_url": (
            "https://seoul.diplo.de/kr-ko/service/"
            "visa-einreise/1890394-1890394"
        ),
        "source_language": "ko",
        "source_file": embassy_path.relative_to(ROOT).as_posix(),
        "source_sha256": embassy_hash,
        "char_count": len(embassy_text),
        "line_count": len(embassy_lines),
        "applicability": (
            "General employment visa guidance; "
            "includes EU Blue Card and skilled workers."
        ),
        "review_status": "needs_review",
    }

    embassy_ranges = [
        ("application_channels", 73, 80),
        ("required_documents", 83, 92),
        ("processing_fees_and_decision", 95, 111),
    ]

    embassy_evidence = []

    for index, (topic, first, last) in enumerate(
        embassy_ranges, 1
    ):
        quote = "\n".join(
            embassy_lines[first - 1:last]
        ).strip()

        if len(quote) < 50:
            raise ValueError(
                f"Embassy evidence unexpectedly short: {topic}"
            )

        embassy_evidence.append({
            "evidence_id": f"DE_SKILLED_EMBASSY_EVD_{index:02d}",
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
        "source_evidence_id": "DE_SKILLED_EMBASSY_EVD_02",
        "documents_to_review": [
            "completed_and_signed_application",
            "valid_passport_and_biographical_page_copy",
            "recent_passport_photos",
            "korean_foreign_registration_card_if_applicable",
            "employment_contract_if_available",
            "employer_declaration_of_employment",
            "academic_or_vocational_qualification_evidence",
            "professional_experience_evidence",
            "curriculum_vitae",
            "employer_invitation_letter",
            "additional_documents_if_requested",
        ],
        "application_method_specific_requirements": True,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["embassy_application_review"] = {
        "source_evidence_ids": [
            "DE_SKILLED_EMBASSY_EVD_01",
            "DE_SKILLED_EMBASSY_EVD_03",
        ],
        "online_application_available": True,
        "in_person_application_option": True,
        "embassy_fee_eur": 75,
        "fee_refundable": False,
        "processing_time_guidance": "4 to 6 weeks",
        "entry_visa_vs_residence_permit": (
            "Embassy guidance mentions a three-month "
            "entry visa after a positive decision. "
            "Distinguish from residence permit validity."
        ),
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["embassy_scope_notes"] = [
        {
            "topic": "shared_employment_guidance",
            "finding": (
                "Embassy section covers EU Blue Card, "
                "academic skilled workers and vocational "
                "skilled workers. Confirm pathway-specific "
                "documents before treating them as mandatory."
            ),
            "review_status": "needs_review",
        },
        {
            "topic": "application_method",
            "finding": (
                "Online portal and in-person submission "
                "may require different submission steps."
            ),
            "review_status": "needs_review",
        },
        {
            "topic": "visa_and_residence_duration",
            "finding": (
                "Three-month entry visa guidance is distinct "
                "from the federal four-year maximum "
                "residence permit guidance."
            ),
            "review_status": "needs_review",
        },
    ]

    if not (
        len(sections) == 5
        and len(requirements) == 4
        and len(pathways) == 2
        and len(evidence) == 2
        and len(policies) == 2
        and len(checks) == 15
        and len(review_groups) == 7
        and all(checks.values())
    ):
        raise ValueError("Skilled Worker consistency check failed")

    if any(
        policy["eligibility_rule"] is not None
        or policy["approved_for_eligibility_decision"]
        for policy in policies
    ):
        raise ValueError("Unapproved policy detected")

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== GERMANY SKILLED WORKER EVIDENCE ===")
    print("SOURCE CHARS:", len(text))
    print("SOURCE LINES:", len(lines))
    print("EVIDENCE SECTIONS:", len(sections))
    print("SHARED REQUIREMENTS:", len(requirements))
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
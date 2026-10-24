
"""
Germany Working Holiday Visa - Evidence Draft
Source: German Embassy in Seoul (Korean guidance)

Extracts source-linked evidence and unapproved policy candidates.
No automatic eligibility rules are generated.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT
    / "data/raw/germany/working_holiday"
    / "working_holiday_seoul_embassy_ko.txt"
)

OUTPUT = (
    ROOT
    / "data/processed/germany/working_holiday"
    / "working_holiday_evidence_draft.json"
)

SOURCE_URL = (
    "https://seoul.diplo.de/kr-ko/service/1694216-1694216"
)

HEADINGS = [
    ("overview", "개요"),
    ("eligibility", "신청자격"),
    ("required_documents", "구비서류"),
    ("fee", "수수료"),
    ("additional_notes", "기타 유의사항"),
]

REVIEW_GROUPS = {
    "nationality_and_age": {
        "sections": ["eligibility"],
        "review_points": [
            "south_korean_nationality",
            "age_18_to_34_at_application",
        ],
    },
    "family_and_health": {
        "sections": ["eligibility"],
        "review_points": [
            "children_not_accompanying",
            "ineligible_spouse_not_accompanying",
            "good_health",
            "medical_certificate_not_required",
        ],
    },
    "financial_evidence": {
        "sections": ["required_documents"],
        "review_points": [
            "minimum_3500_eur",
            "return_ticket_reduction",
            "first_three_months_accommodation_reduction",
            "reduction_combination_requires_review",
            "bank_statement_in_applicant_name",
            "english_statement_issued_within_one_week",
        ],
    },
    "insurance": {
        "sections": ["required_documents"],
        "review_points": [
            "liability_insurance_30000_eur",
            "medical_insurance_30000_eur",
            "accident_insurance_30000_eur",
            "hospital_and_repatriation_coverage",
            "coverage_for_entire_stay",
            "working_holiday_or_overseas_travel_purpose",
        ],
    },
    "application_documents": {
        "sections": ["required_documents"],
        "review_points": [
            "completed_and_signed_application",
            "valid_passport_and_copy",
            "recent_passport_photo",
            "insurance_contract_original",
            "additional_documents_possible",
        ],
    },
    "application_process_and_history": {
        "sections": ["fee", "additional_notes"],
        "review_points": [
            "fee_75_eur_paid_in_krw",
            "fee_nonrefundable",
            "in_person_embassy_application",
            "processing_time_guidance",
            "working_holiday_one_time_only",
            "previous_visa_issuance",
        ],
    },
}

CHECKS = {
    "korean_nationality": ("eligibility", r"대한민국 국적"),
    "minimum_age": ("eligibility", r"18\s*세"),
    "maximum_age": ("eligibility", r"34\s*세"),
    "maximum_stay": ("overview", r"최대\s*12\s*개월"),
    "funds": ("required_documents", r"3,500\s*유로"),
    "reduction": ("required_documents", r"1,000\s*유로"),
    "liability_insurance": (
        "required_documents", r"책임보험",
    ),
    "medical_insurance": (
        "required_documents", r"의료보험",
    ),
    "accident_insurance": (
        "required_documents", r"사고보험",
    ),
    "insurance_amount": (
        "required_documents", r"30,000\s*유로",
    ),
    "application_fee": ("fee", r"75\s*유로"),
    "personal_application": (
        "additional_notes", r"본인이 직접",
    ),
    "one_time_only": (
        "additional_notes", r"1\s*회에 한해서만",
    ),
}


def read_source():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    raw = SOURCE.read_bytes()
    content = raw.decode("utf-8-sig")
    lines = content.splitlines()

    if len(content) < 1500:
        raise ValueError("Source text is unexpectedly short")

    required = [
        "주한",
        "독일연방공화국",
        "워킹홀리데이 비자",
        "신청자격",
        "구비서류",
        "수수료",
    ]

    for item in required:
        if item not in content:
            raise ValueError(f"Missing source marker: {item}")

    if re.search(r"<!DOCTYPE|<html|<script", content, re.I):
        raise ValueError("HTML was copied instead of text")

    return raw, content, lines


def extract_sections(lines, source_hash):
    positions = []

    for topic, heading in HEADINGS:
        matches = [
            index
            for index, line in enumerate(lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Heading mismatch: {heading} -> {matches}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Section headings are out of order")

    footer = [
        index
        for index, line in enumerate(lines)
        if line.strip() == "문의하기(비자)"
    ]

    if len(footer) != 1 or footer[0] <= positions[-1]:
        raise ValueError("Source footer could not be located")

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
            raise ValueError(f"Section mismatch: {heading}")

        if len(original_text) < 30:
            raise ValueError(f"Section unexpectedly short: {heading}")

        number = index + 1
        section_id = f"DE_WH_ELIG_{number:02d}"

        sections.append({
            "section_id": section_id,
            "topic": topic,
            "heading": heading,
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "review_status": "needs_review",
        })

        evidence.append({
            "evidence_id": f"DE_WH_EVD_{number:02d}",
            "source_section_id": section_id,
            "exact_quote": original_text,
            "review_status": "needs_review",
        })

        policies.append({
            "policy_id": f"DE_WH_POL_{number:02d}",
            "source_section_id": section_id,
            "topic": topic,
            "source_text": original_text,
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    return sections, evidence, policies


def validate_requirements(sections):
    by_topic = {
        section["topic"]: section["original_text"]
        for section in sections
    }

    checks = {}

    for key, (topic, pattern) in CHECKS.items():
        found = bool(re.search(pattern, by_topic[topic], re.I))
        checks[key] = found

        if not found:
            raise ValueError(
                f"Source requirement not found: {key}"
            )

    return checks


def build_review_groups(sections):
    section_ids = {
        section["topic"]: section["section_id"]
        for section in sections
    }

    groups = {}

    for name, config in REVIEW_GROUPS.items():
        groups[name] = {
            "source_section_ids": [
                section_ids[topic]
                for topic in config["sections"]
            ],
            "review_points": config["review_points"],
            "eligibility_rule": None,
            "review_status": "needs_review",
        }

    return groups


def main():
    raw, content, lines = read_source()

    source_hash = hashlib.sha256(raw).hexdigest()

    sections, evidence, policies = extract_sections(
        lines, source_hash
    )

    checks = validate_requirements(sections)
    review_groups = build_review_groups(sections)

    result = {
        "country": "Germany",
        "program": "working_holiday",
        "program_type": "visa",
        "source": {
            "authority": "German Embassy in Seoul",
            "source_url": SOURCE_URL,
            "source_language": "ko",
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "char_count": len(content),
            "line_count": len(lines),
        },
        "evidence_sections": sections,
        "evidence": evidence,
        "policy_candidates": policies,
        "source_requirement_checks": checks,
        "conditional_requirements": review_groups,
        "related_sources_to_review": [
            "워킹홀리데이 공동성명, 한국어",
            "영사과 방문 예약",
            "비자신청서 및 Videx 안내",
        ],
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # Historical agreement and 2025 age amendment.
    # Preserve as source-linked evidence, not approved rules.
    agreement_path = (
        ROOT / "data/raw/germany/working_holiday"
        / "working_holiday_joint_declaration_ko.pdf"
    )

    if not agreement_path.is_file():
        raise FileNotFoundError(agreement_path)

    agreement_bytes = agreement_path.read_bytes()

    if not agreement_bytes.startswith(b"%PDF-"):
        raise ValueError("Invalid agreement PDF")

    result["supplementary_agreement"] = {
        "source_file": agreement_path.relative_to(ROOT).as_posix(),
        "source_url": (
            "https://seoul.diplo.de/resource/blob/2705340/"
            "6dfbff4733aaf4417172ddb2aac415c4/"
            "working-holiday-absprache-kor-data.pdf"
        ),
        "source_sha256": hashlib.sha256(
            agreement_bytes
        ).hexdigest(),
        "source_language": "ko",
        "original_agreement_date": "2009-04-19",
        "amendment_correspondence_date": "2024-12-30",
        "amendment_effective_date": "2025-01-01",
        "age_requirement_history": {
            "original": {
                "minimum_age": 18,
                "maximum_age": 30,
                "source_page": 1,
            },
            "amended": {
                "minimum_age": 18,
                "maximum_age": 34,
                "source_pages": [5, 6, 7],
            },
        },
        "amendment_scope": "Article 1(a) age requirement",
        "extraction_method": "visual_source_review",
        "machine_readable_pdf_text": False,
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(sections) == 5
        and len(evidence) == 5
        and len(policies) == 5
        and len(review_groups) == 6
        and all(checks.values())
    ):
        raise ValueError("Evidence consistency check failed")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== GERMANY WORKING HOLIDAY EVIDENCE ===")
    print("SOURCE CHARS:", len(content))
    print("SOURCE LINES:", len(lines))
    print("EVIDENCE SECTIONS:", len(sections))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policies))
    print("SOURCE CHECKS:", len(checks))
    print("REVIEW GROUPS:", len(review_groups))
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

"""
Germany study pathways - official evidence extraction.

Source:
Make it in Germany, Visa for studying.

Creates two separate draft datasets:
1. Study visa - Section 16b
2. Seeking a place in higher education - Section 17(2)

All policy candidates require human/legal review.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data/raw/germany/study"
    / "study_visa_make_it_in_germany_en.txt"
)

OUT_DIR = ROOT / "data/processed/germany/study"

SOURCE_URL = (
    "https://www.make-it-in-germany.com/en/"
    "visa-residence/types/studying"
)

# Ordered main-content headings.
# The same labels may also occur in the page navigation.
HEADINGS = [
    ("study_requirements",
     "Requirements for the visa for studying in Germany"),
    ("study_prospects",
     "Your prospects with the visa for studying"),
    ("study_after_graduation",
     "Successfully graduated - this is how you can stay in Germany"),
    ("study_settlement",
     "Settlement permit after graduating from a German university"),
    ("study_eu_mobility",
     "Explaining mobility in the EU for students from third countries"),
    ("seeking_overview",
     "No place to study yet? Visa for the purpose of seeking a place in higher education"),
    ("seeking_requirements",
     "Requirements for the visa for seeking a place in higher education"),
    ("seeking_prospects",
     "Prospects with the visa for seeking a place in higher education"),
    ("online_application",
     "Apply for the visa for studying online"),
]

PROGRAMS = {
    "study_visa": {
        "legal_basis": "Residence Act (AufenthG) Section 16b",
        "section_topics": [
            "study_requirements",
            "study_prospects",
            "study_after_graduation",
            "study_settlement",
            "study_eu_mobility",
            "online_application",
        ],
        "requirement_topic": "study_requirements",
        "review_groups": {
            "admission_and_preparatory_measures": [
                "university_admission",
                "state_recognition",
                "preparatory_studies",
            ],
            "financial_requirements": [
                "2026_blocked_account_amount",
                "scholarship",
                "declaration_of_commitment",
            ],
            "language_requirements": [
                "course_specific_language_level",
                "language_proof",
            ],
            "residence_and_work": [
                "initial_residence_duration",
                "renewal",
                "working_days_or_hours",
                "student_jobs",
            ],
            "after_graduation_and_mobility": [
                "18_month_jobseeker_residence",
                "conversion_to_work_residence",
                "settlement",
                "eu_student_mobility",
            ],
        },
    },
    "seeking_higher_education_place": {
        "legal_basis": "Residence Act (AufenthG) Section 17(2)",
        "section_topics": [
            "seeking_overview",
            "seeking_requirements",
            "seeking_prospects",
            "online_application",
        ],
        "requirement_topic": "seeking_requirements",
        "review_groups": {
            "education_and_language": [
                "qualifying_school_leaving_certificate",
                "preparatory_course",
                "course_language_requirement",
            ],
            "financial_requirements": [
                "2026_monthly_funds",
                "blocked_account",
                "declaration_of_commitment",
            ],
            "stay_and_work": [
                "nine_month_limit",
                "nonrenewable_same_purpose",
                "20_hours_per_week",
                "trial_work",
                "conversion_to_study_residence",
            ],
        },
    },
}


def load_source():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()

    if len(text) < 5000:
        raise ValueError("Study source unexpectedly short")

    markers = [
        "Visa for studying",
        "Section 16b",
        "Section 17 (2)",
        "€11,904",
        "€1,091",
        "140 full days",
        "nine months",
    ]

    for marker in markers:
        if marker not in text:
            raise ValueError(f"Missing source marker: {marker}")

    if re.search(r"<!DOCTYPE|<html|<script", text, re.I):
        raise ValueError("Unexpected HTML in text source")

    return raw, text, lines


def locate_sections(lines):
    # Ignore the table of contents and navigation.
    content_start = next(
        i for i, line in enumerate(lines)
        if line.startswith("Are you interested in studying in Germany?")
    )

    positions = []

    for topic, heading in HEADINGS:
        matches = [
            i for i, line in enumerate(lines)
            if i > content_start and line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Main-content heading mismatch: {heading}: {matches}"
            )

        positions.append((topic, heading, matches[0]))

    indices = [item[2] for item in positions]

    if indices != sorted(indices):
        raise ValueError("Main-content sections out of order")

    end_markers = [
        i for i, line in enumerate(lines)
        if i > indices[-1] and line.strip() == "Information on the web"
    ]

    if len(end_markers) != 1:
        raise ValueError("Could not locate source content ending")

    content_end = end_markers[0]
    sections = {}

    for index, (topic, heading, start) in enumerate(positions):
        end = (
            positions[index + 1][2]
            if index + 1 < len(positions)
            else content_end
        )

        content = "\n".join(lines[start:end]).strip()

        if len(content) < 80:
            raise ValueError(f"Section too short: {topic}")

        sections[topic] = {
            "topic": topic,
            "heading": heading,
            "start_line": start + 1,
            "end_line": end,
            "original_text": content,
        }

    return sections


def extract_requirement_lines(lines, section):
    start = section["start_line"] - 1
    end = section["end_line"]

    result = []

    for line_index in range(start + 1, end):
        value = lines[line_index].strip()

        if (
            not value
            or value.startswith("Do you meet the above requirements?")
            or value.startswith("Here you find an overview")
        ):
            continue

        result.append({
            "source_line": line_index + 1,
            "original_text": value,
        })

    if len(result) != 3:
        raise ValueError(
            f"Expected 3 requirement lines, found {len(result)} "
            f"in {section['topic']}"
        )

    return result


def build_dataset(program_id, config, lines, sections, source):
    selected = [
        sections[topic]
        for topic in config["section_topics"]
    ]

    evidence = []

    for index, section in enumerate(selected, 1):
        evidence.append({
            "evidence_id": f"DE_{program_id.upper()}_EVD_{index:02d}",
            "topic": section["topic"],
            "heading": section["heading"],
            "source_file": source["source_file"],
            "source_sha256": source["source_sha256"],
            "start_line": section["start_line"],
            "end_line": section["end_line"],
            "exact_quote": section["original_text"],
            "review_status": "needs_review",
        })

    requirement_section = sections[config["requirement_topic"]]
    requirement_lines = extract_requirement_lines(
        lines, requirement_section
    )

    policies = []

    for index, requirement in enumerate(requirement_lines, 1):
        policies.append({
            "policy_id": f"DE_{program_id.upper()}_POL_{index:02d}",
            "topic": config["requirement_topic"],
            "source_line": requirement["source_line"],
            "source_text": requirement["original_text"],
            "requirement_type": "needs_review",
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    review_groups = {
        name: {
            "review_points": points,
            "eligibility_rule": None,
            "review_status": "needs_review",
        }
        for name, points in config["review_groups"].items()
    }

    result = {
        "country": "Germany",
        "program": program_id,
        "pathway_type": "study",
        "legal_basis": config["legal_basis"],
        "official_source": source,
        "evidence": evidence,
        "policy_candidates": policies,
        "conditional_requirements": review_groups,
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    if any(
        item["eligibility_rule"] is not None
        or item["approved_for_eligibility_decision"]
        for item in policies
    ):
        raise ValueError("Unapproved automatic rule detected")

    return result


def main():
    raw, text, lines = load_source()
    sections = locate_sections(lines)

    source = {
        "authority": "German Federal Government - Make it in Germany",
        "source_url": SOURCE_URL,
        "source_language": "en",
        "source_file": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "char_count": len(text),
        "line_count": len(lines),
        "amount_reference_year": 2026,
    }

    datasets = {}

    for program_id, config in PROGRAMS.items():
        datasets[program_id] = build_dataset(
            program_id, config, lines, sections, source
        )

    # Build and validate every dataset before writing any output.

    # Supplementary Korean Embassy guidance for Study Visa only.
    # Keep the Section 17(2) dataset separate.
    embassy_path = (
        ROOT / "data/raw/germany/study"
        / "study_visa_seoul_embassy_ko.txt"
    )

    if not embassy_path.is_file():
        raise FileNotFoundError(embassy_path)

    embassy_raw = embassy_path.read_bytes()
    embassy_text = embassy_raw.decode("utf-8-sig")
    embassy_lines = embassy_text.splitlines()
    embassy_hash = hashlib.sha256(embassy_raw).hexdigest()

    if not (
        "유학생 비자 안내" in embassy_text
        and "입학허가서" in embassy_text
        and "슈페어콘토" in embassy_text
        and "120 일" in embassy_text
        and "240 일" in embassy_text
    ):
        raise ValueError("Embassy study source validation failed")

    embassy_source = {
        "authority": "German Embassy in Seoul",
        "source_url": (
            "https://seoul.diplo.de/kr-ko/service/"
            "visa-einreise/1887970-1887970"
        ),
        "source_language": "ko",
        "source_file": embassy_path.relative_to(ROOT).as_posix(),
        "source_sha256": embassy_hash,
        "char_count": len(embassy_text),
        "line_count": len(embassy_lines),
        "page_publication_date": "2018-10-16",
        "review_status": "needs_review",
    }

    embassy_ranges = [
        ("application_channels", 23, 27),
        ("required_documents", 30, 45),
        ("visa_conditions_and_fees", 47, 58),
    ]

    embassy_evidence = []

    for index, (topic, first, last) in enumerate(
        embassy_ranges, 1
    ):
        original_text = "\n".join(
            embassy_lines[first - 1:last]
        ).strip()

        if len(original_text) < 40:
            raise ValueError(
                f"Embassy evidence too short: {topic}"
            )

        embassy_evidence.append({
            "evidence_id": f"DE_STUDY_EMBASSY_EVD_{index:02d}",
            "topic": topic,
            "source_file": embassy_source["source_file"],
            "source_sha256": embassy_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": original_text,
            "review_status": "needs_review",
        })

    datasets["study_visa"]["embassy_source"] = embassy_source
    datasets["study_visa"]["embassy_evidence"] = embassy_evidence

    datasets["study_visa"]["embassy_document_review"] = {
        "source_evidence_id": "DE_STUDY_EMBASSY_EVD_02",
        "documents_to_review": [
            "completed_and_signed_visa_application",
            "valid_passport_and_biographical_page_copy",
            "foreign_registration_card_if_applicable",
            "recent_passport_photo",
            "university_admission_letter",
            "academic_qualification_evidence",
            "language_test_certificate",
            "instruction_language_confirmation",
            "health_insurance_contract",
            "motivation_letter",
            "accepted_financial_evidence",
        ],
        "additional_documents_may_be_requested": True,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    datasets["study_visa"]["source_differences_to_review"] = [
        {
            "topic": "student_work_allowance",
            "make_it_in_germany": (
                "140 full days / 280 half days per year, "
                "or up to 20 hours per week"
            ),
            "seoul_embassy": (
                "120 full days / 240 half days per year"
            ),
            "embassy_source_lines": [47, 49],
            "interpretation": (
                "Different published guidance; "
                "verify current legal applicability."
            ),
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        {
            "topic": "entry_visa_vs_residence_permit",
            "make_it_in_germany": (
                "Study residence permit initially "
                "usually issued for two years"
            ),
            "seoul_embassy": (
                "Entry visa generally valid for three months"
            ),
            "embassy_source_lines": [55, 55],
            "interpretation": (
                "Different immigration document stages; "
                "do not treat as conflicting duration limits."
            ),
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    ]

    datasets["study_visa"]["embassy_application_review"] = {
        "online_application": True,
        "in_person_submission_option": True,
        "embassy_fee_eur": 75,
        "fee_refundable": False,
        "processing_time_guidance": "approximately 4 weeks",
        "source_evidence_ids": [
            "DE_STUDY_EMBASSY_EVD_01",
            "DE_STUDY_EMBASSY_EVD_03",
        ],
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    if (
        len(datasets["study_visa"]["evidence"]) != 6
        or len(datasets["seeking_higher_education_place"]["evidence"]) != 4
        or any(
            len(dataset["policy_candidates"]) != 3
            for dataset in datasets.values()
        )
    ):
        raise ValueError("Dataset consistency check failed")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for program_id, dataset in datasets.items():
        output = OUT_DIR / f"{program_id}_evidence_draft.json"

        output.write_text(
            json.dumps(dataset, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"=== {program_id.upper()} ===")
        print("SOURCE CHARS:", len(text))
        print("EVIDENCE:", len(dataset["evidence"]))
        print("POLICY CANDIDATES:", len(dataset["policy_candidates"]))
        print(
            "REVIEW GROUPS:",
            len(dataset["conditional_requirements"]),
        )
        print("STATUS: CANDIDATES_NEED_REVIEW")
        print("SAVED:", output.relative_to(ROOT))


if __name__ == "__main__":
    main()
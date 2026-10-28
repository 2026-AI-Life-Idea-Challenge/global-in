
"""
Canada Study Permit — IRCC eligibility evidence.

Extract official eligibility, student responsibilities
and PGWP-related notes without approving legal rules.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data/raw/canada/study"
    / "study_permit_eligibility_ircc_en.txt"
)

OUTPUT = (
    ROOT / "data/processed/canada/study"
    / "study_permit_evidence_draft.json"
)

SOURCE_URL = (
    "https://www.canada.ca/en/"
    "immigration-refugees-citizenship/services/"
    "study-canada/study-permit/eligibility.html"
)

REQUIRED_MARKERS = {
    "dli_enrollment": r"are enrolled at a DLI",
    "tuition": r"your tuition fees",
    "living_expenses": r"living expenses for yourself",
    "return_transportation": r"return transportation",
    "criminal_record": r"no criminal record",
    "police_certificate": r"police certificate \(if required\)",
    "health": r"are in good health",
    "medical_exam": r"medical exam \(if required\)",
    "leave_canada": r"leave Canada when your study permit expires",
    "academic_progress": r"make progress towards completing",
    "permit_conditions": r"respect any conditions",
    "school_change": r"change schools at the post-secondary level",
    "pgwp": r"post-graduation work permit",
}

EVIDENCE_RANGES = [
    ("eligibility_requirements", 26, 36),
    ("student_responsibilities", 37, 49),
    ("pgwp_related_guidance", 50, 55),
]

POLICY_DEFINITIONS = [
    {
        "policy_id": "CA_STUDY_POL_01",
        "topic": "dli_and_enrollment",
        "evidence_topics": ["eligibility_requirements"],
        "conditions_to_review": [
            "enrolled_at_designated_learning_institution",
            "letter_of_acceptance_documentation",
            "institution_and_program_validation",
        ],
    },
    {
        "policy_id": "CA_STUDY_POL_02",
        "topic": "financial_capacity",
        "evidence_topics": ["eligibility_requirements"],
        "conditions_to_review": [
            "tuition_fees",
            "living_expenses_for_applicant",
            "living_expenses_for_accompanying_family",
            "return_transportation",
            "applicable_funding_amount_and_date",
        ],
    },
    {
        "policy_id": "CA_STUDY_POL_03",
        "topic": "admissibility_and_temporary_stay",
        "evidence_topics": ["eligibility_requirements"],
        "conditions_to_review": [
            "criminal_record_and_admissibility",
            "police_certificate_if_required",
            "medical_exam_if_required",
            "departure_at_end_of_authorized_stay",
        ],
    },
    {
        "policy_id": "CA_STUDY_POL_04",
        "topic": "student_responsibilities",
        "evidence_topics": ["student_responsibilities"],
        "conditions_to_review": [
            "progress_towards_program_completion",
            "study_permit_conditions",
            "work_authorization_if_applicable",
            "post_secondary_dli_change_requirements",
            "stop_studying_if_requirements_not_met",
        ],
    },
]

REVIEW_GROUPS = {
    "institution_and_admission": [
        "DLI enrollment",
        "LOA documentation",
        "institution and program status",
    ],
    "financial_capacity": [
        "tuition",
        "living expenses",
        "return transportation",
        "family members",
        "applicable amount and reference date",
    ],
    "admissibility": [
        "criminal history",
        "police certificate if required",
        "medical exam if required",
        "temporary stay conditions",
    ],
    "application_documents": [
        "LOA",
        "PAL or TAL and exemptions",
        "Quebec CAQ if applicable",
        "personalized application documents",
    ],
    "conditions_during_study": [
        "academic progress",
        "work authorization",
        "school changes",
        "permit conditions",
    ],
    "post_graduation_pathway": [
        "PGWP is not automatically granted",
        "PGWP-eligible institution and program",
        "study permit application date relevance",
        "separate PGWP eligibility review",
    ],
}


def load_source():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()

    if len(text) < 2500:
        raise ValueError("Study Permit source unexpectedly short")

    if re.search(r"<!DOCTYPE|<html|<script", text, re.I):
        raise ValueError("Expected plain-text IRCC source")

    expected_lines = {
        26: "Eligibility requirements",
        37: "Your responsibilities as a student",
        50: "Post-graduation work permit",
        62: "Date modified: 2026-01-26",
    }

    for number, expected in expected_lines.items():
        if (
            len(lines) < number
            or lines[number - 1].strip() != expected
        ):
            raise ValueError(
                f"Source layout mismatch at line {number}"
            )

    checks = {
        name: bool(re.search(pattern, text, re.I))
        for name, pattern in REQUIRED_MARKERS.items()
    }

    missing = [
        name for name, passed in checks.items()
        if not passed
    ]

    if missing:
        raise ValueError(f"Missing source markers: {missing}")

    return raw, text, lines, checks


def extract_evidence(lines, source_hash):
    evidence = []

    for index, (topic, first, last) in enumerate(
        EVIDENCE_RANGES, 1
    ):
        quote = "\n".join(
            lines[first - 1:last]
        ).strip()

        if len(quote) < 100:
            raise ValueError(f"Evidence too short: {topic}")

        evidence.append({
            "evidence_id": f"CA_STUDY_EVD_{index:02d}",
            "topic": topic,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "source_sha256": source_hash,
            "review_status": "needs_review",
        })

    return evidence


def build_policy_candidates(evidence):
    evidence_by_topic = {
        item["topic"]: item["evidence_id"]
        for item in evidence
    }

    candidates = []

    for definition in POLICY_DEFINITIONS:
        candidates.append({
            "policy_id": definition["policy_id"],
            "topic": definition["topic"],
            "source_evidence_ids": [
                evidence_by_topic[topic]
                for topic in definition["evidence_topics"]
            ],
            "conditions_to_review": (
                definition["conditions_to_review"]
            ),
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    return candidates


def main():
    raw, text, lines, checks = load_source()
    source_hash = hashlib.sha256(raw).hexdigest()

    evidence = extract_evidence(lines, source_hash)
    candidates = build_policy_candidates(evidence)

    result = {
        "country": "Canada",
        "program": "study_permit",
        "program_category": "study",
        "official_source": {
            "authority": (
                "Immigration, Refugees and Citizenship Canada"
            ),
            "source_url": SOURCE_URL,
            "source_language": "en",
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "char_count": len(text),
            "line_count": len(lines),
            "source_last_modified": "2026-01-26",
        },
        "evidence": evidence,
        "policy_candidates": candidates,
        "source_requirement_checks": checks,
        "conditional_requirements": {
            topic: {
                "review_points": items,
                "eligibility_rule": None,
                "review_status": "needs_review",
            }
            for topic, items in REVIEW_GROUPS.items()
        },
        "financial_requirements_review": {
            "tuition": "required_to_review",
            "living_expenses": "required_to_review",
            "return_transportation": "required_to_review",
            "specific_amount": None,
            "applicable_reference_date": None,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "document_requirements_to_verify": [
            "letter_of_acceptance",
            "pal_tal_or_exemption",
            "quebec_caq_if_applicable",
            "proof_of_funds",
            "police_certificate_if_required",
            "medical_exam_if_required",
        ],
        "related_but_separate_program": {
            "program": "post_graduation_work_permit",
            "abbreviation": "PGWP",
            "source_evidence_id": "CA_STUDY_EVD_03",
            "eligibility_not_automatic": True,
            "review_status": "needs_review",
        },
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }
    
    # Supplementary IRCC Study Permit document evidence.
    # Preserve the existing three eligibility evidence items
    # and four draft policy candidates.

    documents_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_documents_ircc_en.txt"
    )

    if not documents_path.is_file():
        raise FileNotFoundError(documents_path)

    documents_raw = documents_path.read_bytes()
    documents_text = documents_raw.decode("utf-8-sig")
    documents_lines = documents_text.splitlines()
    documents_hash = hashlib.sha256(documents_raw).hexdigest()

    expected_document_lines = {
        29: "Get the right documents",
        33: "Get your letter of acceptance",
        39: "Apply for a provincial or territorial attestation letter",
        45: "Show proof of identity",
        55: "Show proof of funds",
        63: "Get a medical exam",
        72: "Get a police certificate",
        100: "Date modified: 2026-10-06",
    }

    for number, marker in expected_document_lines.items():
        if (
            len(documents_lines) < number
            or marker not in documents_lines[number - 1]
        ):
            raise ValueError(
                f"Study document source layout mismatch: line {number}"
            )

    document_ranges = [
        ("letter_of_acceptance", 29, 37),
        ("pal_tal_and_quebec_caq", 38, 42),
        ("identity_and_financial_proof", 44, 56),
        ("explanation_medical_police_and_minors", 58, 79),
        ("local_visa_office_requirements", 81, 91),
    ]

    document_evidence = []

    for index, (topic, first, last) in enumerate(
        document_ranges, 1
    ):
        quote = "\n".join(
            documents_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Document evidence unexpectedly short: {topic}"
            )

        document_evidence.append({
            "evidence_id": f"CA_STUDY_DOC_EVD_{index:02d}",
            "topic": topic,
            "source_file": documents_path.relative_to(ROOT).as_posix(),
            "source_sha256": documents_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["document_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/study-permit/get-documents.html"
        ),
        "source_language": "en",
        "source_file": documents_path.relative_to(ROOT).as_posix(),
        "source_sha256": documents_hash,
        "char_count": len(documents_text),
        "line_count": len(documents_lines),
        "source_last_modified": "2026-10-06",
        "review_status": "needs_review",
    }

    result["document_evidence"] = document_evidence

    result["document_requirements_review"] = {
        "letter_of_acceptance": {
            "source_evidence_id": "CA_STUDY_DOC_EVD_01",
            "source_classification": "always_required",
            "exceptions_need_review": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "pal_tal": {
            "source_evidence_id": "CA_STUDY_DOC_EVD_02",
            "source_classification": "needed_in_most_cases",
            "exemptions_need_review": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "quebec_caq": {
            "source_evidence_id": "CA_STUDY_DOC_EVD_02",
            "scope": "study_in_quebec",
            "detailed_conditions_need_review": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "identity": {
            "source_evidence_id": "CA_STUDY_DOC_EVD_03",
            "source_classification": "always_required",
            "documents_to_review": [
                "valid_passport_or_travel_document_copy",
                "passport_information_page",
                "passport_photos",
                "family_member_identity_if_applicable",
            ],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "financial_support": {
            "source_evidence_id": "CA_STUDY_DOC_EVD_03",
            "source_classification": "always_required",
            "specific_amount": None,
            "separate_financial_source_required": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "other_documents": {
            "source_evidence_ids": [
                "CA_STUDY_DOC_EVD_04",
                "CA_STUDY_DOC_EVD_05",
            ],
            "recommended": [
                "letter_of_explanation",
            ],
            "conditional": [
                "immigration_medical_exam",
                "police_certificate",
                "custodian_documents_for_applicable_minors",
                "local_visa_office_documents",
                "proof_of_status_in_application_country",
            ],
            "medical_exam_not_universal": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }

    result["document_scope_notes"] = [
        {
            "topic": "loa_exceptions",
            "finding": (
                "The source mentions LOA exceptions but the "
                "copied page does not expand their details."
            ),
            "review_status": "needs_review",
        },
        {
            "topic": "pal_tal_exemptions",
            "finding": (
                "PAL/TAL is needed in most cases. "
                "Confirm exemptions with the dedicated IRCC page."
            ),
            "review_status": "needs_review",
        },
        {
            "topic": "quebec_caq",
            "finding": (
                "Quebec-specific CAQ requirements need "
                "separate review."
            ),
            "review_status": "needs_review",
        },
        {
            "topic": "financial_amounts",
            "finding": (
                "The document overview does not provide "
                "the applicable financial support amount."
            ),
            "review_status": "needs_review",
        },
    ]
    
    # IRCC PAL/TAL evidence integration.
    # The captured page contains collapsed sections.
    # Do not infer exemption or renewal rules from headings.

    pal_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_pal_tal_ircc_en.txt"
    )

    if not pal_path.is_file():
        raise FileNotFoundError(pal_path)

    pal_raw = pal_path.read_bytes()
    pal_text = pal_raw.decode("utf-8-sig")
    pal_lines = pal_text.splitlines()
    pal_hash = hashlib.sha256(pal_raw).hexdigest()

    pal_required_lines = {
        22: "Provincial attestation letter",
        27: "usually required",
        34: "Find out if you need a PAL/TAL",
        47: "issued",
        52: "When to get a new PAL/TAL",
        70: "Date modified: 2026-09-02",
    }

    for number, marker in pal_required_lines.items():
        if (
            len(pal_lines) < number
            or marker not in pal_lines[number - 1]
        ):
            raise ValueError(
                f"PAL/TAL source mismatch at line {number}"
            )

    pal_ranges = [
        ("definition_and_general_requirement", 22, 27),
        ("individualized_requirement_check", 28, 38),
        ("issuance_submission_and_validity", 39, 51),
        ("renewal_scenarios_listed", 52, 63),
    ]

    pal_evidence = []

    for index, (topic, first, last) in enumerate(
        pal_ranges, 1
    ):
        quote = "\n".join(
            pal_lines[first - 1:last]
        ).strip()

        pal_evidence.append({
            "evidence_id": f"CA_STUDY_PAL_EVD_{index:02d}",
            "topic": topic,
            "source_file": pal_path.relative_to(ROOT).as_posix(),
            "source_sha256": pal_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["pal_tal_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/study-permit/get-documents/"
            "provincial-attestation-letter.html"
        ),
        "source_file": pal_path.relative_to(ROOT).as_posix(),
        "source_sha256": pal_hash,
        "source_last_modified": "2026-09-02",
        "char_count": len(pal_text),
        "line_count": len(pal_lines),
        "interactive_details_captured": False,
        "review_status": "needs_review",
    }
    
    # Detailed PAL/TAL evidence from the official HTML.
    # This supplements the collapsed-section TXT evidence.
    from html.parser import HTMLParser

    class VisibleTextParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
            self.hidden_depth = 0

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "noscript"):
                self.hidden_depth += 1
            elif tag in ("p", "li", "div", "h2", "h3", "h4", "br"):
                self.parts.append(" ")

        def handle_endtag(self, tag):
            if tag in ("script", "style", "noscript"):
                self.hidden_depth = max(0, self.hidden_depth - 1)
            elif tag in ("p", "li", "div", "h2", "h3", "h4"):
                self.parts.append(" ")

        def handle_data(self, data):
            if self.hidden_depth == 0:
                self.parts.append(data)

    details_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_pal_tal_official.html"
    )

    if not details_path.is_file():
        raise FileNotFoundError(details_path)

    details_raw = details_path.read_bytes()
    details_hash = hashlib.sha256(details_raw).hexdigest()

    parser = VisibleTextParser()
    parser.feed(
        details_raw.decode("utf-8-sig", errors="replace")
    )

    details_text = re.sub(
        r"\s+", " ", " ".join(parser.parts)
    ).strip()

    detailed_patterns = [
        (
            "pal_tal_exemptions",
            r"You don.t need a PAL or TAL when applying",
        ),
        (
            "graduate_program_exemption",
            r"degree.granting graduate program at the "
            r"master.s or doctoral level at a public DLI",
        ),
        (
            "pal_tal_validity_2026",
            r"until December 31, 2026",
        ),
        (
            "school_change_and_new_pal_tal",
            r"As of January 22, 2025, you must get "
            r"a new PAL/TAL",
        ),
        (
            "extension_and_status_restoration",
            r"If you.re applying for a study permit "
            r"extension at the same DLI",
        ),
    ]

    detailed_evidence = []

    for index, (topic, pattern) in enumerate(
        detailed_patterns, 1
    ):
        match = re.search(pattern, details_text, re.I)

        if not match:
            raise ValueError(
                f"PAL/TAL detailed rule missing: {topic}"
            )

        first = max(0, match.start() - 150)
        last = min(len(details_text), match.end() + 650)

        detailed_evidence.append({
            "evidence_id": f"CA_STUDY_PAL_DETAIL_{index:02d}",
            "topic": topic,
            "source_file": details_path.relative_to(ROOT).as_posix(),
            "source_sha256": details_hash,
            "text_start_offset": first,
            "text_end_offset": last,
            "exact_quote": details_text[first:last],
            "review_status": "needs_review",
        })

    result["pal_tal_detailed_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/study-permit/get-documents/"
            "provincial-attestation-letter.html"
        ),
        "source_file": details_path.relative_to(ROOT).as_posix(),
        "source_sha256": details_hash,
        "source_last_modified": "2026-09-02",
        "review_status": "needs_review",
    }

    result["pal_tal_detailed_evidence"] = detailed_evidence

    if len(detailed_evidence) != 5:
        raise ValueError(
            "PAL/TAL detailed evidence count mismatch"
        )

    result["pal_tal_evidence"] = pal_evidence

    result["pal_tal_detailed_rules_review"] = {
        "exemptions": {
            "rule": None,
            "source_details_missing": True,
            "review_status": "needs_review",
        },
        "validity_2026": {
            "expiry_date": None,
            "source_details_missing": True,
            "review_status": "needs_review",
        },
        "school_change": {
            "rule": None,
            "source_details_missing": True,
            "review_status": "needs_review",
        },
        "study_level_change": {
            "rule": None,
            "source_details_missing": True,
            "review_status": "needs_review",
        },
        "study_permit_extension": {
            "rule": None,
            "source_details_missing": True,
            "review_status": "needs_review",
        },
        "quebec_caq_reuse": {
            "rule": None,
            "source_details_missing": True,
            "review_status": "needs_review",
        },
    }

    if not (
        len(document_evidence) == 5
        and len(result["document_requirements_review"]) == 6
        and len(result["document_scope_notes"]) == 4
        and len(candidates) == 4
    ):
        raise ValueError(
            "Study Permit document integration check failed"
        )
    
    # IRCC Study Permit financial support evidence.
    # Preserve both application-date-specific living cost tables.
    # Amounts are extracted from the captured official source.

    finance_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_financial_support_ircc_en.txt"
    )

    if not finance_path.is_file():
        raise FileNotFoundError(finance_path)

    finance_raw = finance_path.read_bytes()
    finance_text = finance_raw.decode("utf-8-sig")
    finance_lines = finance_text.splitlines()
    finance_hash = hashlib.sha256(finance_raw).hexdigest()

    required_finance_lines = {
        21: "Proof of financial support",
        30: "first year of your studies",
        35: "Common documents",
        77: "September 1, 2026",
        94: "January 1, 2025",
        110: "Quebec",
        119: "Date modified: 2026-08-28",
    }

    for number, marker in required_finance_lines.items():
        if (
            len(finance_lines) < number
            or marker not in finance_lines[number - 1]
        ):
            raise ValueError(
                f"Financial source mismatch at line {number}"
            )

    finance_ranges = [
        ("financial_capacity_general", 21, 33),
        ("accepted_proof_examples", 35, 70),
        ("living_costs_from_2026_09_01", 72, 92),
        ("living_costs_2025_to_2026_08_31", 94, 108),
        ("quebec_separate_requirements", 110, 111),
    ]

    financial_evidence = []

    for index, (topic, first, last) in enumerate(
        finance_ranges, 1
    ):
        quote = "\n".join(
            finance_lines[first - 1:last]
        ).strip()

        if len(quote) < 50:
            raise ValueError(
                f"Financial evidence unexpectedly short: {topic}"
            )

        financial_evidence.append({
            "evidence_id": f"CA_STUDY_FIN_EVD_{index:02d}",
            "topic": topic,
            "source_file": finance_path.relative_to(ROOT).as_posix(),
            "source_sha256": finance_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    def parse_living_cost_table(first, last):
        table_lines = finance_lines[first - 1:last]
        amounts = {}

        for line in table_lines:
            match = re.fullmatch(
                r"\s*([1-7])\s+\$([\d,]+)\s*",
                line,
            )

            if match:
                family_count = int(match.group(1))
                amount = int(
                    match.group(2).replace(",", "")
                )

                if family_count in amounts:
                    raise ValueError(
                        f"Duplicate family count: {family_count}"
                    )

                amounts[family_count] = amount

        additional = re.search(
            r"If more than 7 people, each additional "
            r"family member\s+\$([\d,]+)",
            "\n".join(table_lines),
            re.I,
        )

        if set(amounts) != set(range(1, 8)):
            raise ValueError(
                f"Incomplete financial table: {first}-{last}"
            )

        if not additional:
            raise ValueError(
                f"Additional family amount missing: {first}-{last}"
            )

        return {
            "amounts_by_total_family_members": {
                str(k): v
                for k, v in sorted(amounts.items())
            },
            "additional_amount_per_person_above_seven": int(
                additional.group(1).replace(",", "")
            ),
        }

    living_cost_2026 = parse_living_cost_table(80, 91)
    living_cost_previous = parse_living_cost_table(96, 107)

    result["financial_support_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/study-permit/get-documents/"
            "financial-support.html"
        ),
        "source_file": finance_path.relative_to(ROOT).as_posix(),
        "source_sha256": finance_hash,
        "source_last_modified": "2026-08-28",
        "char_count": len(finance_text),
        "line_count": len(finance_lines),
        "review_status": "needs_review",
    }

    result["financial_support_evidence"] = financial_evidence

    result["financial_living_cost_tables"] = [
        {
            "table_id": "CA_STUDY_LIVING_COST_2026_09",
            "applies_from": "2026-09-01",
            "applies_through": None,
            "geographic_scope": "canada_except_quebec",
            "currency": "CAD",
            "period": "first_year",
            "includes_tuition": False,
            "includes_transportation": False,
            "source_evidence_id": "CA_STUDY_FIN_EVD_03",
            **living_cost_2026,
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        },
        {
            "table_id": "CA_STUDY_LIVING_COST_2025_01",
            "applies_from": "2025-01-01",
            "applies_through": "2026-08-31",
            "geographic_scope": "canada_except_quebec",
            "currency": "CAD",
            "period": "first_year",
            "includes_tuition": False,
            "includes_transportation": False,
            "source_evidence_id": "CA_STUDY_FIN_EVD_04",
            **living_cost_previous,
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        },
    ]

    result["financial_support_conditions_review"] = {
        "general_financial_capacity": {
            "source_evidence_id": "CA_STUDY_FIN_EVD_01",
            "components": [
                "tuition_fees",
                "living_expenses",
                "transportation_to_and_from_canada",
            ],
            "employment_income_in_canada_not_assumed": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "multi_year_studies": {
            "source_evidence_id": "CA_STUDY_FIN_EVD_01",
            "first_year_funds_evidence": True,
            "full_duration_funding_plan_if_over_one_year": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "proof_of_funds": {
            "source_evidence_id": "CA_STUDY_FIN_EVD_02",
            "example_documents": [
                "tuition_or_housing_payment_receipt",
                "student_or_education_loan",
                "scholarship_or_funded_program",
                "employment_income_documents",
                "financial_supporter_documents",
                "canadian_bank_account",
                "guaranteed_investment_certificate",
                "six_month_bank_statements_with_source",
                "pension_or_rental_income_documents",
            ],
            "all_examples_mandatory": False,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "quebec": {
            "source_evidence_id": "CA_STUDY_FIN_EVD_05",
            "use_federal_non_quebec_amounts": False,
            "quebec_amounts": None,
            "separate_provincial_source_required": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }

    result["financial_requirements_review"].update({
        "tuition": "separate_from_living_cost_amount",
        "living_expenses": "date_and_family_count_dependent",
        "return_transportation": "separate_from_living_cost_amount",
        "specific_amount": None,
        "applicable_reference_date": None,
        "living_cost_table_ids": [
            "CA_STUDY_LIVING_COST_2026_09",
            "CA_STUDY_LIVING_COST_2025_01",
        ],
    })
    
    # IRCC Study Permit financial support evidence.
    # Preserve both application-date-specific living cost tables.
    # Amounts are extracted from the captured official source.

    finance_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_financial_support_ircc_en.txt"
    )

    if not finance_path.is_file():
        raise FileNotFoundError(finance_path)

    finance_raw = finance_path.read_bytes()
    finance_text = finance_raw.decode("utf-8-sig")
    finance_lines = finance_text.splitlines()
    finance_hash = hashlib.sha256(finance_raw).hexdigest()

    required_finance_lines = {
        21: "Proof of financial support",
        30: "first year of your studies",
        35: "Common documents",
        77: "September 1, 2026",
        94: "January 1, 2025",
        110: "Quebec",
        119: "Date modified: 2026-08-28",
    }

    for number, marker in required_finance_lines.items():
        if (
            len(finance_lines) < number
            or marker not in finance_lines[number - 1]
        ):
            raise ValueError(
                f"Financial source mismatch at line {number}"
            )

    finance_ranges = [
        ("financial_capacity_general", 21, 33),
        ("accepted_proof_examples", 35, 70),
        ("living_costs_from_2026_09_01", 72, 92),
        ("living_costs_2025_to_2026_08_31", 94, 108),
        ("quebec_separate_requirements", 110, 111),
    ]

    financial_evidence = []

    for index, (topic, first, last) in enumerate(
        finance_ranges, 1
    ):
        quote = "\n".join(
            finance_lines[first - 1:last]
        ).strip()

        if len(quote) < 50:
            raise ValueError(
                f"Financial evidence unexpectedly short: {topic}"
            )

        financial_evidence.append({
            "evidence_id": f"CA_STUDY_FIN_EVD_{index:02d}",
            "topic": topic,
            "source_file": finance_path.relative_to(ROOT).as_posix(),
            "source_sha256": finance_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    def parse_living_cost_table(first, last):
        table_lines = finance_lines[first - 1:last]
        amounts = {}

        for line in table_lines:
            match = re.fullmatch(
                r"\s*([1-7])\s+\$([\d,]+)\s*",
                line,
            )

            if match:
                family_count = int(match.group(1))
                amount = int(
                    match.group(2).replace(",", "")
                )

                if family_count in amounts:
                    raise ValueError(
                        f"Duplicate family count: {family_count}"
                    )

                amounts[family_count] = amount

        additional = re.search(
            r"If more than 7 people, each additional "
            r"family member\s+\$([\d,]+)",
            "\n".join(table_lines),
            re.I,
        )

        if set(amounts) != set(range(1, 8)):
            raise ValueError(
                f"Incomplete financial table: {first}-{last}"
            )

        if not additional:
            raise ValueError(
                f"Additional family amount missing: {first}-{last}"
            )

        return {
            "amounts_by_total_family_members": {
                str(k): v
                for k, v in sorted(amounts.items())
            },
            "additional_amount_per_person_above_seven": int(
                additional.group(1).replace(",", "")
            ),
        }

    living_cost_2026 = parse_living_cost_table(80, 91)
    living_cost_previous = parse_living_cost_table(96, 107)

    result["financial_support_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/study-permit/get-documents/"
            "financial-support.html"
        ),
        "source_file": finance_path.relative_to(ROOT).as_posix(),
        "source_sha256": finance_hash,
        "source_last_modified": "2026-08-28",
        "char_count": len(finance_text),
        "line_count": len(finance_lines),
        "review_status": "needs_review",
    }

    result["financial_support_evidence"] = financial_evidence

    result["financial_living_cost_tables"] = [
        {
            "table_id": "CA_STUDY_LIVING_COST_2026_09",
            "applies_from": "2026-09-01",
            "applies_through": None,
            "geographic_scope": "canada_except_quebec",
            "currency": "CAD",
            "period": "first_year",
            "includes_tuition": False,
            "includes_transportation": False,
            "source_evidence_id": "CA_STUDY_FIN_EVD_03",
            **living_cost_2026,
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        },
        {
            "table_id": "CA_STUDY_LIVING_COST_2025_01",
            "applies_from": "2025-01-01",
            "applies_through": "2026-08-31",
            "geographic_scope": "canada_except_quebec",
            "currency": "CAD",
            "period": "first_year",
            "includes_tuition": False,
            "includes_transportation": False,
            "source_evidence_id": "CA_STUDY_FIN_EVD_04",
            **living_cost_previous,
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        },
    ]

    result["financial_support_conditions_review"] = {
        "general_financial_capacity": {
            "source_evidence_id": "CA_STUDY_FIN_EVD_01",
            "components": [
                "tuition_fees",
                "living_expenses",
                "transportation_to_and_from_canada",
            ],
            "employment_income_in_canada_not_assumed": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "multi_year_studies": {
            "source_evidence_id": "CA_STUDY_FIN_EVD_01",
            "first_year_funds_evidence": True,
            "full_duration_funding_plan_if_over_one_year": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "proof_of_funds": {
            "source_evidence_id": "CA_STUDY_FIN_EVD_02",
            "example_documents": [
                "tuition_or_housing_payment_receipt",
                "student_or_education_loan",
                "scholarship_or_funded_program",
                "employment_income_documents",
                "financial_supporter_documents",
                "canadian_bank_account",
                "guaranteed_investment_certificate",
                "six_month_bank_statements_with_source",
                "pension_or_rental_income_documents",
            ],
            "all_examples_mandatory": False,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "quebec": {
            "source_evidence_id": "CA_STUDY_FIN_EVD_05",
            "use_federal_non_quebec_amounts": False,
            "quebec_amounts": None,
            "separate_provincial_source_required": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }

    result["financial_requirements_review"].update({
        "tuition": "separate_from_living_cost_amount",
        "living_expenses": "date_and_family_count_dependent",
        "return_transportation": "separate_from_living_cost_amount",
        "specific_amount": None,
        "applicable_reference_date": None,
        "living_cost_table_ids": [
            "CA_STUDY_LIVING_COST_2026_09",
            "CA_STUDY_LIVING_COST_2025_01",
        ],
    })

    if not (
        len(financial_evidence) == 5
        and len(result["financial_living_cost_tables"]) == 2
        and len(result["financial_support_conditions_review"]) == 4
        and all(
            len(table["amounts_by_total_family_members"]) == 7
            and table["review_status"] == "needs_review"
            and table["eligibility_rule"] is None
            and table["legal_validation_approved"] is False
            and table["approved_for_eligibility_decision"] is False
            for table in result["financial_living_cost_tables"]
        )
    ):
        raise ValueError(
            "Financial support integration validation failed"
        )
    
    # IRCC Study Permit application process evidence.
    # Preserve previous eligibility, document, PAL/TAL,
    # and financial support evidence.

    application_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_application_ircc_en.txt"
    )

    if not application_path.is_file():
        raise FileNotFoundError(application_path)

    application_raw = application_path.read_bytes()
    application_text = application_raw.decode("utf-8-sig")
    application_lines = application_text.splitlines()
    application_hash = hashlib.sha256(
        application_raw
    ).hexdigest()

    required_application_lines = {
        20: "How to apply",
        21: "before you come to Canada",
        29: "Get your documents ready",
        38: "Apply online",
        39: "must apply online",
        41: "only eligible to apply on paper",
        45: "doctoral student",
        57: "Where are you applying from?",
        67: "Date modified: 2026-09-02",
    }

    for number, marker in required_application_lines.items():
        if (
            len(application_lines) < number
            or marker not in application_lines[number - 1]
        ):
            raise ValueError(
                f"Application source mismatch at line {number}"
            )

    application_ranges = [
        ("application_location", 20, 21),
        ("document_preparation", 29, 37),
        ("online_application_and_paper_exceptions", 38, 44),
        ("doctoral_processing_and_application_routes", 45, 60),
    ]

    application_evidence = []

    for index, (topic, first, last) in enumerate(
        application_ranges, 1
    ):
        quote = "\n".join(
            application_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Application evidence unexpectedly short: {topic}"
            )

        application_evidence.append({
            "evidence_id": f"CA_STUDY_APP_EVD_{index:02d}",
            "topic": topic,
            "source_file": application_path.relative_to(ROOT).as_posix(),
            "source_sha256": application_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["application_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/study-permit/apply.html"
        ),
        "source_language": "en",
        "source_file": (
            application_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": application_hash,
        "source_last_modified": "2026-09-02",
        "char_count": len(application_text),
        "line_count": len(application_lines),
        "review_status": "needs_review",
    }

    result["application_evidence"] = application_evidence

    result["application_process_review"] = {
        "application_location": {
            "source_evidence_id": "CA_STUDY_APP_EVD_01",
            "general_route": "before_entering_canada",
            "other_routes_to_verify": [
                "within_canada",
                "at_port_of_entry",
            ],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "document_submission": {
            "source_evidence_id": "CA_STUDY_APP_EVD_02",
            "documents_to_review": [
                "letter_of_acceptance",
                "pal_tal_or_exemption_evidence",
                "other_required_documents",
            ],
            "pal_tal_exemption_proof_required_if_applicable": True,
            "incomplete_application_may_delay_processing": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "application_method": {
            "source_evidence_id": "CA_STUDY_APP_EVD_03",
            "general_method": "online",
            "paper_application_exceptions_to_verify": [
                "disability_preventing_online_application",
                "specified_non_national_refugee_or_stateless_documents",
            ],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "doctoral_processing": {
            "source_evidence_id": "CA_STUDY_APP_EVD_04",
            "faster_processing_may_be_available": True,
            "eligible_family_members_may_be_included": True,
            "specific_eligibility_not_verified": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "fees_and_biometrics": {
            "application_fee_cad": None,
            "biometrics_fee_cad": None,
            "biometrics_deadline_days": None,
            "separate_official_source_required": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }

    if not (
        len(application_evidence) == 4
        and len(result["application_process_review"]) == 5
        and all(
            item["review_status"] == "needs_review"
            for item in application_evidence
        )
        and all(
            item["eligibility_rule"] is None
            and item["review_status"] == "needs_review"
            for item in result["application_process_review"].values()
        )
    ):
        raise ValueError(
            "Study Permit application integration failed"
        )
    
    # IRCC Study Permit — After you apply.
    # Add application processing, biometrics, approval and refusal
    # evidence without authorizing eligibility decisions.

    after_apply_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_after_apply_ircc_en.txt"
    )

    if not after_apply_path.is_file():
        raise FileNotFoundError(after_apply_path)

    after_apply_raw = after_apply_path.read_bytes()
    after_apply_text = after_apply_raw.decode("utf-8-sig")
    after_apply_lines = after_apply_text.splitlines()
    after_apply_hash = hashlib.sha256(
        after_apply_raw
    ).hexdigest()

    required_after_apply_lines = {
        20: "After you apply",
        27: "fingerprints and photo",
        30: "We process your study permit application",
        43: "missing documents",
        47: "Updating your application",
        55: "If we approve your application",
        61: "This letter is not your study permit",
        71: "within Canada",
        82: "If we refuse your application",
        103: "Date modified: 2026-08-28",
    }

    for number, marker in required_after_apply_lines.items():
        if (
            len(after_apply_lines) < number
            or marker not in after_apply_lines[number - 1]
        ):
            raise ValueError(
                f"After-apply source mismatch at line {number}"
            )

    after_apply_ranges = [
        ("biometrics", 27, 28),
        ("processing_and_missing_documents", 30, 45),
        ("application_updates_and_status", 47, 54),
        ("approval_and_study_permit_issuance", 55, 80),
        ("refusal_and_reasons", 82, 92),
    ]

    after_apply_evidence = []

    for index, (topic, first, last) in enumerate(
        after_apply_ranges, 1
    ):
        quote = "\n".join(
            after_apply_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"After-apply evidence too short: {topic}"
            )

        after_apply_evidence.append({
            "evidence_id": f"CA_STUDY_AFTER_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                after_apply_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": after_apply_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["after_apply_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/study-permit/after-apply.html"
        ),
        "source_language": "en",
        "source_file": (
            after_apply_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": after_apply_hash,
        "source_last_modified": "2026-08-28",
        "char_count": len(after_apply_text),
        "line_count": len(after_apply_lines),
        "review_status": "needs_review",
    }

    result["after_apply_evidence"] = after_apply_evidence

    result["after_apply_process_review"] = {
        "biometrics": {
            "source_evidence_id": "CA_STUDY_AFTER_EVD_01",
            "appointment_recommended_promptly": True,
            "biometrics_required_for_every_applicant": None,
            "biometrics_deadline_days": None,
            "separate_deadline_source_required": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "application_processing": {
            "source_evidence_id": "CA_STUDY_AFTER_EVD_02",
            "checks_document_completeness": True,
            "possible_additional_steps": [
                "interview",
                "additional_information",
                "medical_exam_if_required",
                "police_certificate_if_required",
            ],
            "missing_documents_may_delay_processing": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "application_updates": {
            "source_evidence_id": "CA_STUDY_AFTER_EVD_03",
            "contact_information_changes_must_be_reported": True,
            "status_tracking_identifiers": [
                "unique_client_identifier",
                "application_number",
            ],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "approval_outside_canada": {
            "source_evidence_id": "CA_STUDY_AFTER_EVD_04",
            "letter_of_introduction": "issued_if_approved",
            "letter_is_study_permit": False,
            "actual_permit_issued_at_port_of_entry": True,
            "entry_document_if_required": [
                "electronic_travel_authorization",
                "temporary_resident_visa",
            ],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "approval_inside_canada": {
            "source_evidence_id": "CA_STUDY_AFTER_EVD_04",
            "study_permit_sent_by_mail": True,
            "approval_letter_in_online_account": True,
            "study_start_after_approval_letter": (
                "subject_to_applicable_conditions"
            ),
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "refusal": {
            "source_evidence_id": "CA_STUDY_AFTER_EVD_05",
            "reason_letter_provided": True,
            "illustrative_reasons": [
                "invalid_letter_of_acceptance",
                "insufficient_financial_support",
                "required_medical_exam_not_passed",
                "study_purpose_not_established",
                "departure_intention_not_established",
            ],
            "reasons_are_not_exhaustive": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }

    if not (
        len(after_apply_evidence) == 5
        and len(result["after_apply_process_review"]) == 6
        and all(
            item["review_status"] == "needs_review"
            for item in after_apply_evidence
        )
        and all(
            item["eligibility_rule"] is None
            and item["review_status"] == "needs_review"
            for item in result["after_apply_process_review"].values()
        )
    ):
        raise ValueError(
            "Study Permit after-apply integration failed"
        )
    
    # IRCC Study Permit — Prepare for your arrival.
    # Preserve previous evidence and draft policy candidates.

    arrival_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_arrival_ircc_en.txt"
    )

    if not arrival_path.is_file():
        raise FileNotFoundError(arrival_path)

    arrival_raw = arrival_path.read_bytes()
    arrival_text = arrival_raw.decode("utf-8-sig")
    arrival_lines = arrival_text.splitlines()
    arrival_hash = hashlib.sha256(arrival_raw).hexdigest()

    required_arrival_lines = {
        20: "Prepare for your arrival",
        32: "How early can you arrive",
        35: "not allowed to work",
        37: "Changing your designated learning institution",
        38: "new study permit application",
        41: "When you arrive in Canada",
        45: "port of entry letter of introduction",
        51: "enough money for your stay",
        57: "valid immigration medical exam results",
        58: "valid for 12 months",
        63: "proof you entered Canada",
        66: "Inadmissibility",
        77: "Date modified: 2026-08-28",
    }

    for number, marker in required_arrival_lines.items():
        if (
            len(arrival_lines) < number
            or marker not in arrival_lines[number - 1]
        ):
            raise ValueError(
                f"Study arrival source mismatch at line {number}"
            )

    arrival_ranges = [
        ("early_arrival_and_work_restrictions", 32, 35),
        ("dli_change_after_approval", 37, 38),
        ("arrival_documents_and_financial_capacity", 41, 56),
        ("medical_exam_validity", 57, 62),
        ("entry_proof_and_inadmissibility", 63, 69),
    ]

    arrival_evidence = []

    for index, (topic, first, last) in enumerate(
        arrival_ranges, 1
    ):
        quote = "\n".join(
            arrival_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Arrival evidence unexpectedly short: {topic}"
            )

        arrival_evidence.append({
            "evidence_id": f"CA_STUDY_ARR_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                arrival_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": arrival_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["arrival_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "study-canada/study-permit/prepare-arrival.html"
        ),
        "source_language": "en",
        "source_file": (
            arrival_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": arrival_hash,
        "source_last_modified": "2026-08-28",
        "char_count": len(arrival_text),
        "line_count": len(arrival_lines),
        "review_status": "needs_review",
    }

    result["arrival_evidence"] = arrival_evidence

    result["arrival_process_review"] = {
        "arrival_timing": {
            "source_evidence_id": "CA_STUDY_ARR_EVD_01",
            "fixed_earliest_arrival_days": None,
            "reasonable_preparation_time_advised": True,
            "on_or_off_campus_work_before_studies": False,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "dli_change_after_outside_canada_approval": {
            "source_evidence_id": "CA_STUDY_ARR_EVD_02",
            "new_study_permit_application_required": True,
            "new_letter_of_acceptance_required": True,
            "new_application_fees_required": True,
            "scope": "approved_application_from_outside_canada",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "entry_documents": {
            "source_evidence_id": "CA_STUDY_ARR_EVD_03",
            "documents_to_review": [
                "valid_passport_or_travel_document",
                "port_of_entry_letter_of_introduction",
                "valid_letter_of_acceptance_copy",
                "visa_office_requested_documents",
                "applicable_entry_authorization",
                "proof_of_sufficient_funds",
            ],
            "possible_entry_authorizations": [
                "eta",
                "temporary_resident_visa",
                "other_applicable_status_or_travel_document",
            ],
            "all_authorizations_required_together": False,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "medical_exam_at_entry": {
            "source_evidence_id": "CA_STUDY_ARR_EVD_04",
            "conditional_on_medical_exam_requirement": True,
            "exam_validity_months": 12,
            "must_be_valid_on_entry_date": True,
            "new_exam_if_expired_before_entry": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "entry_inspection": {
            "source_evidence_ids": [
                "CA_STUDY_ARR_EVD_03",
                "CA_STUDY_ARR_EVD_05",
            ],
            "border_officer_checks_requirements": True,
            "admissibility_review_required": True,
            "entry_stamp_if_proof_requested": (
                "review_available_options"
            ),
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "enrolment_deferral": {
            "source_evidence_id": None,
            "details_in_captured_text": False,
            "separate_source_required": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }

    result["arrival_legal_review"] = {
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(arrival_evidence) == 5
        and len(result["arrival_process_review"]) == 6
        and all(
            item["review_status"] == "needs_review"
            for item in arrival_evidence
        )
        and all(
            item["eligibility_rule"] is None
            and item["review_status"] == "needs_review"
            for item in result["arrival_process_review"].values()
        )
    ):
        raise ValueError(
            "Study Permit arrival integration failed"
        )
    
    # IRCC Biometrics — official fees and collection process.
    # The source does not establish the 30-day deadline,
    # study permit fee, or individual exemption criteria.

    biometrics_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_biometrics_ircc_en.txt"
    )

    if not biometrics_path.is_file():
        raise FileNotFoundError(biometrics_path)

    biometrics_raw = biometrics_path.read_bytes()
    biometrics_text = biometrics_raw.decode("utf-8-sig")
    biometrics_lines = biometrics_text.splitlines()
    biometrics_hash = hashlib.sha256(
        biometrics_raw
    ).hexdigest()

    required_biometrics_lines = {
        18: "How to give your fingerprints and photo",
        25: "Step 1: Pay the biometrics fee",
        31: "Individual applicant: CAN$85",
        32: "maximum total fee of CAN$170",
        51: "Step 2: Get the biometric instruction letter",
        58: "your BIL",
        74: "current application",
        79: "Step 3: Go to an official biometric collection site",
        82: "in person",
        86: "Booking an appointment is free",
        113: "Date modified: 2026-03-30",
    }

    for number, marker in required_biometrics_lines.items():
        if (
            len(biometrics_lines) < number
            or marker not in biometrics_lines[number - 1]
        ):
            raise ValueError(
                f"Biometrics source mismatch at line {number}"
            )

    biometrics_ranges = [
        ("biometrics_fees", 25, 38),
        ("late_fee_payment", 40, 50),
        ("bil_and_identity_documents", 51, 73),
        ("current_bil_requirement", 74, 78),
        ("collection_and_booking", 79, 108),
    ]

    biometrics_evidence = []

    for index, (topic, first, last) in enumerate(
        biometrics_ranges, 1
    ):
        quote = "\n".join(
            biometrics_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Biometrics evidence too short: {topic}"
            )

        biometrics_evidence.append({
            "evidence_id": f"CA_STUDY_BIO_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                biometrics_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": biometrics_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    # Extract official fee values from source text.
    individual_match = re.search(
        r"Individual applicant:\s*CAN\$(\d+)",
        biometrics_text,
        re.I,
    )

    family_match = re.search(
        r"Families applying at the same time"
        r".*?maximum total fee of CAN\$(\d+)",
        biometrics_text,
        re.I,
    )

    if not individual_match or not family_match:
        raise ValueError(
            "Could not extract official biometrics fee amounts"
        )

    individual_fee = int(individual_match.group(1))
    family_fee_cap = int(family_match.group(1))

    if individual_fee != 85 or family_fee_cap != 170:
        raise ValueError(
            "Biometrics fees differ from reviewed source"
        )

    result["biometrics_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "biometrics/how-to-give.html"
        ),
        "source_language": "en",
        "source_file": (
            biometrics_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": biometrics_hash,
        "source_last_modified": "2026-03-30",
        "char_count": len(biometrics_text),
        "line_count": len(biometrics_lines),
        "review_status": "needs_review",
    }

    result["biometrics_evidence"] = biometrics_evidence

    result["biometrics_fees"] = {
        "currency": "CAD",
        "individual_applicant": individual_fee,
        "eligible_family_maximum_total": family_fee_cap,
        "family_scope": (
            "eligible_family_members_applying_at_same_time"
        ),
        "appointment_booking_fee": 0,
        "source_evidence_ids": [
            "CA_STUDY_BIO_EVD_01",
            "CA_STUDY_BIO_EVD_05",
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    result["biometrics_process_review"] = {
        "payment": {
            "source_evidence_ids": [
                "CA_STUDY_BIO_EVD_01",
                "CA_STUDY_BIO_EVD_02",
            ],
            "payment_with_application_advised": True,
            "late_payment_may_delay_processing": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "instruction_letter": {
            "source_evidence_ids": [
                "CA_STUDY_BIO_EVD_03",
                "CA_STUDY_BIO_EVD_04",
            ],
            "current_application_bil_required": True,
            "standard_appointment_documents": [
                "current_biometric_instruction_letter",
                "valid_passport",
            ],
            "identity_document_exceptions_need_review": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "collection": {
            "source_evidence_id": "CA_STUDY_BIO_EVD_05",
            "in_person_collection": True,
            "official_collection_location_required": True,
            "appointment_should_be_booked_promptly": True,
            "booking_is_free": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "deadline_and_exemptions": {
            "source_evidence_id": None,
            "biometrics_deadline_days": None,
            "who_must_submit_biometrics": None,
            "previous_biometrics_reuse_conditions": None,
            "separate_official_sources_required": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "quality_and_recollection": {
            "source_evidence_id": "CA_STUDY_BIO_EVD_05",
            "recollection_may_be_required": True,
            "reason": "insufficient_fingerprint_quality",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }

    # Update existing placeholders without assigning
    # the still-unverified study permit application fee.
    result["application_process_review"][
        "fees_and_biometrics"
    ].update({
        "application_fee_cad": None,
        "biometrics_fee_cad": individual_fee,
        "biometrics_family_fee_cap_cad": family_fee_cap,
        "biometrics_deadline_days": None,
        "source_evidence_id": "CA_STUDY_BIO_EVD_01",
        "separate_official_source_required": True,
    })

    result["after_apply_process_review"][
        "biometrics"
    ].update({
        "individual_fee_cad": individual_fee,
        "biometrics_deadline_days": None,
        "fee_source_evidence_id": "CA_STUDY_BIO_EVD_01",
    })

    if not (
        len(biometrics_evidence) == 5
        and len(result["biometrics_process_review"]) == 5
        and individual_fee == 85
        and family_fee_cap == 170
        and all(
            item["review_status"] == "needs_review"
            for item in biometrics_evidence
        )
        and all(
            item["eligibility_rule"] is None
            and item["review_status"] == "needs_review"
            for item in result[
                "biometrics_process_review"
            ].values()
        )
    ):
        raise ValueError(
            "Biometrics integration validation failed"
        )
    
    # IRCC biometrics deadline evidence.
    # Deadline starts when the applicant receives the BIL.
    # A web-form request does not guarantee an extension.

    deadline_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_biometrics_deadline_ircc_en.txt"
    )

    if not deadline_path.is_file():
        raise FileNotFoundError(deadline_path)

    deadline_raw = deadline_path.read_bytes()
    deadline_text = deadline_raw.decode("utf-8-sig")
    deadline_lines = deadline_text.splitlines()
    deadline_hash = hashlib.sha256(deadline_raw).hexdigest()

    required_deadline_lines = {
        18: "Where to give your fingerprints and photo",
        22: "biometric instruction letter",
        23: "30 days from the time you get your BIL",
        26: "use the web form",
        30: "appointment by the deadline",
        33: "screenshot of the appointment confirmation",
        42: "Date modified: 2026-08-24",
    }

    for number, marker in required_deadline_lines.items():
        if (
            len(deadline_lines) < number
            or marker not in deadline_lines[number - 1]
        ):
            raise ValueError(
                f"Biometrics deadline source mismatch: line {number}"
            )

    deadline_match = re.search(
        r"You have\s+(\d+)\s+days from the time "
        r"you get your BIL",
        deadline_text,
        re.I,
    )

    if not deadline_match:
        raise ValueError(
            "Unable to extract BIL-based deadline"
        )

    deadline_days = int(deadline_match.group(1))

    if deadline_days != 30:
        raise ValueError(
            "Biometrics deadline differs from reviewed source"
        )

    deadline_ranges = [
        ("bil_deadline_and_booking", 18, 24),
        ("deadline_extension_request", 25, 38),
    ]

    deadline_evidence = []

    for index, (topic, first, last) in enumerate(
        deadline_ranges, 1
    ):
        quote = "\n".join(
            deadline_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Deadline evidence too short: {topic}"
            )

        deadline_evidence.append({
            "evidence_id": f"CA_STUDY_BIO_DEAD_{index:02d}",
            "topic": topic,
            "source_file": (
                deadline_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": deadline_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["biometrics_deadline_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "biometrics/where-to-give.html"
        ),
        "source_language": "en",
        "source_file": (
            deadline_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": deadline_hash,
        "source_last_modified": "2026-08-24",
        "char_count": len(deadline_text),
        "line_count": len(deadline_lines),
        "review_status": "needs_review",
    }

    result["biometrics_deadline_evidence"] = deadline_evidence

    result["biometrics_deadline_requirements"] = {
        "deadline_days": deadline_days,
        "deadline_trigger": "bil_received",
        "applies_if_biometrics_required": True,
        "individual_bil_instructions_must_be_checked": True,
        "extension_request_channel": "ircc_web_form",
        "extension_request_requires_reason": True,
        "appointment_confirmation_may_be_provided": True,
        "extension_automatically_approved": False,
        "extension_approval_status": "not_determined",
        "source_evidence_ids": [
            "CA_STUDY_BIO_DEAD_01",
            "CA_STUDY_BIO_DEAD_02",
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    # Link the newly verified deadline to existing review groups.

    result["biometrics_process_review"][
        "deadline_and_exemptions"
    ].update({
        "source_evidence_ids": [
            "CA_STUDY_BIO_DEAD_01",
            "CA_STUDY_BIO_DEAD_02",
        ],
        "biometrics_deadline_days": deadline_days,
        "deadline_trigger": "bil_received",
        "extension_request_channel": "ircc_web_form",
        "separate_official_sources_required": True,
    })

    result["application_process_review"][
        "fees_and_biometrics"
    ].update({
        "biometrics_deadline_days": deadline_days,
        "deadline_trigger": "bil_received",
    })

    result["after_apply_process_review"][
        "biometrics"
    ].update({
        "biometrics_deadline_days": deadline_days,
        "deadline_trigger": "bil_received",
        "separate_deadline_source_required": False,
    })

    if not (
        len(deadline_evidence) == 2
        and deadline_days == 30
        and result["biometrics_deadline_requirements"][
            "eligibility_rule"
        ] is None
        and result["biometrics_deadline_requirements"][
            "legal_validation_approved"
        ] is False
        and result["biometrics_deadline_requirements"][
            "approved_for_eligibility_decision"
        ] is False
    ):
        raise ValueError(
            "Biometrics deadline integration failed"
        )
    
    # IRCC Study Permit official application fee evidence.
    # Keep ordinary study permit, status restoration,
    # and biometrics fees as separate fee components.

    fee_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_fees_ircc_en.txt"
    )

    if not fee_path.is_file():
        raise FileNotFoundError(fee_path)

    fee_raw = fee_path.read_bytes()
    fee_text = fee_raw.decode("utf-8-sig")
    fee_lines = fee_text.splitlines()
    fee_hash = hashlib.sha256(fee_raw).hexdigest()

    required_fee_lines = {
        35: "Study Permits (including extensions)",
        37: "Study permit (including extensions)",
        38: "Restore your status as a student",
        40: "Restore your status",
        42: "396.25",
        406: "Biometrics",
        415: "Biometrics",
        425: "170.00",
        462: "Date modified: 2026-09-21",
    }

    for number, marker in required_fee_lines.items():
        if (
            len(fee_lines) < number
            or marker not in fee_lines[number - 1]
        ):
            raise ValueError(
                f"Study Permit fee source mismatch at line {number}"
            )

    fee_ranges = [
        ("study_permit_application_and_extension", 35, 37),
        ("student_status_restoration", 38, 42),
        ("biometrics_individual_and_family", 405, 425),
    ]

    fee_evidence = []

    for index, (topic, first, last) in enumerate(
        fee_ranges, 1
    ):
        quote = "\n".join(
            fee_lines[first - 1:last]
        ).strip()

        if len(quote) < 30:
            raise ValueError(
                f"Fee evidence unexpectedly short: {topic}"
            )

        fee_evidence.append({
            "evidence_id": f"CA_STUDY_FEE_EVD_{index:02d}",
            "topic": topic,
            "source_file": fee_path.relative_to(ROOT).as_posix(),
            "source_sha256": fee_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    # Extract values from the official source, not assumptions.
    study_fee_match = re.search(
        r"Study permit \(including extensions\)"
        r"\s*[–-]\s*per person\s+([\d,]+(?:\.\d+)?)",
        fee_text,
        re.I,
    )

    restoration_match = re.search(
        r"Restore your status \(\$([\d,.]+)\)"
        r"\s+and a get a new study permit"
        r"\s+\(\$([\d,.]+)\)\s+([\d,.]+)",
        fee_text,
        re.I,
    )

    if not study_fee_match or not restoration_match:
        raise ValueError(
            "Study Permit or restoration fee not found"
        )

    def parse_cad(value):
        return float(value.replace(",", ""))

    study_fee = parse_cad(study_fee_match.group(1))
    restoration_fee = parse_cad(
        restoration_match.group(1)
    )
    restoration_new_permit_fee = parse_cad(
        restoration_match.group(2)
    )
    restoration_total = parse_cad(
        restoration_match.group(3)
    )

    if not (
        study_fee == 150.00
        and restoration_fee == 246.25
        and restoration_new_permit_fee == study_fee
        and restoration_total == 396.25
        and abs(
            restoration_fee
            + restoration_new_permit_fee
            - restoration_total
        ) < 0.001
    ):
        raise ValueError(
            "Official fee amounts failed consistency check"
        )

    result["study_permit_fee_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://ircc.canada.ca/english/"
            "information/fees/fees.asp"
        ),
        "source_language": "en",
        "source_file": fee_path.relative_to(ROOT).as_posix(),
        "source_sha256": fee_hash,
        "source_last_modified": "2026-09-21",
        "line_count": len(fee_lines),
        "char_count": len(fee_text),
        "review_status": "needs_review",
    }

    result["study_permit_fee_evidence"] = fee_evidence

    result["study_permit_fees"] = {
        "currency": "CAD",
        "application_or_extension_per_person": study_fee,
        "student_status_restoration_component": restoration_fee,
        "new_permit_component_for_restoration": (
            restoration_new_permit_fee
        ),
        "restoration_and_new_permit_total": (
            restoration_total
        ),
        "restoration_total_includes_new_permit_fee": True,
        "individual_biometrics_fee": (
            result["biometrics_fees"]["individual_applicant"]
        ),
        "biometrics_added_only_if_required": True,
        "individual_standard_total_if_biometrics_required": (
            study_fee
            + result["biometrics_fees"]["individual_applicant"]
        ),
        "fee_exemptions_verified": False,
        "fee_exemptions": None,
        "source_evidence_ids": [
            "CA_STUDY_FEE_EVD_01",
            "CA_STUDY_FEE_EVD_02",
            "CA_STUDY_FEE_EVD_03",
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    result["application_process_review"][
        "fees_and_biometrics"
    ].update({
        "application_fee_cad": study_fee,
        "biometrics_fee_cad": (
            result["biometrics_fees"]["individual_applicant"]
        ),
        "fee_source_evidence_id": "CA_STUDY_FEE_EVD_01",
        "fee_details_separate_source_required": False,
        "separate_official_source_required": True,
    })

    if not (
        len(fee_evidence) == 3
        and study_fee == 150
        and restoration_total == 396.25
        and result["study_permit_fees"][
            "individual_standard_total_if_biometrics_required"
        ] == 235
        and result["study_permit_fees"][
            "eligibility_rule"
        ] is None
        and result["study_permit_fees"][
            "legal_validation_approved"
        ] is False
        and result["study_permit_fees"][
            "approved_for_eligibility_decision"
        ] is False
    ):
        raise ValueError(
            "Study Permit fee integration validation failed"
        )
    
    # IRCC temporary-resident biometrics reuse evidence.
    # Reuse validity is separate from study permit validity.
    # Detailed age and status exemptions remain under review.

    reuse_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_biometrics_reuse_ircc_en.txt"
    )

    if not reuse_path.is_file():
        raise FileNotFoundError(reuse_path)

    reuse_raw = reuse_path.read_bytes()
    reuse_text = reuse_raw.decode("utf-8-sig")
    reuse_lines = reuse_text.splitlines()
    reuse_hash = hashlib.sha256(reuse_raw).hexdigest()

    required_reuse_lines = {
        20: "Temporary resident applicants",
        26: "unless you’re exempt",
        31: "valid for 10 years",
        33: "automatically attached",
        35: "beyond the expiry date",
        41: "choose to give them again",
        46: "this application",
        52: "Once your visa or permit has been issued",
        59: "refused because you didn’t give biometrics",
        67: "old BIL",
        72: "Date modified: 2026-03-30",
    }

    for number, marker in required_reuse_lines.items():
        if (
            len(reuse_lines) < number
            or marker not in reuse_lines[number - 1]
        ):
            raise ValueError(
                f"Biometrics reuse source mismatch at line {number}"
            )

    reuse_ranges = [
        ("first_time_submission", 25, 28),
        ("ten_year_validity_and_automatic_reuse", 30, 38),
        ("voluntary_resubmission", 40, 48),
        ("permit_already_issued", 49, 58),
        ("refusal_and_new_bil", 59, 67),
    ]

    reuse_evidence = []

    for index, (topic, first, last) in enumerate(
        reuse_ranges, 1
    ):
        quote = "\n".join(
            reuse_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Reuse evidence unexpectedly short: {topic}"
            )

        reuse_evidence.append({
            "evidence_id": f"CA_STUDY_BIO_REUSE_{index:02d}",
            "topic": topic,
            "source_file": reuse_path.relative_to(ROOT).as_posix(),
            "source_sha256": reuse_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    validity_match = re.search(
        r"Your biometrics are valid for (\d+) years",
        reuse_text,
        re.I,
    )

    if not validity_match:
        raise ValueError(
            "Biometrics validity was not found in source"
        )

    validity_years = int(validity_match.group(1))

    if validity_years != 10:
        raise ValueError(
            "Biometrics validity differs from reviewed source"
        )

    result["biometrics_reuse_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "biometrics/when-to-give-temporary-residence.html"
        ),
        "source_language": "en",
        "source_file": reuse_path.relative_to(ROOT).as_posix(),
        "source_sha256": reuse_hash,
        "source_last_modified": "2026-03-30",
        "char_count": len(reuse_text),
        "line_count": len(reuse_lines),
        "review_status": "needs_review",
    }

    result["biometrics_reuse_evidence"] = reuse_evidence

    result["biometrics_reuse_requirements"] = {
        "validity_years": validity_years,
        "scope": "temporary_residence_applications",
        "valid_previous_biometrics_auto_linked": True,
        "covered_application_types": [
            "visitor_visa",
            "study_permit",
            "work_permit",
            "applicable_extensions",
        ],
        "permit_cannot_exceed_biometrics_expiry": True,
        "voluntary_resubmission_when_applying": True,
        "new_bil_for_resubmission": True,
        "resubmission_alone_extends_issued_permit": False,
        "detailed_exemption_rules_verified": False,
        "age_exemptions": None,
        "other_status_exemptions": None,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in reuse_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    result["biometrics_process_review"][
        "deadline_and_exemptions"
    ].update({
        "previous_biometrics_reuse_conditions": (
            "valid_temporary_resident_biometrics_within_10_years"
        ),
        "reuse_source_evidence_id": "CA_STUDY_BIO_REUSE_02",
        "who_must_submit_biometrics": None,
        "separate_official_sources_required": True,
    })

    result["application_process_review"][
        "fees_and_biometrics"
    ].update({
        "biometrics_reuse_validity_years": validity_years,
        "biometrics_may_not_be_required_again": True,
        "biometrics_reuse_source_evidence_id": (
            "CA_STUDY_BIO_REUSE_02"
        ),
    })

    if not (
        len(reuse_evidence) == 5
        and validity_years == 10
        and result["biometrics_reuse_requirements"][
            "eligibility_rule"
        ] is None
        and result["biometrics_reuse_requirements"][
            "legal_validation_approved"
        ] is False
        and result["biometrics_reuse_requirements"][
            "approved_for_eligibility_decision"
        ] is False
        and all(
            item["review_status"] == "needs_review"
            for item in reuse_evidence
        )
    ):
        raise ValueError(
            "Biometrics reuse integration failed"
        )
    
    # IRCC biometrics exemptions and submission scope.
    # Exemptions are distinct from valid biometrics reuse.
    # Store reviewed conditions as unapproved draft data.

    exemption_path = (
        ROOT / "data/raw/canada/study"
        / "study_permit_biometrics_exemptions_ircc_en.txt"
    )

    if not exemption_path.is_file():
        raise FileNotFoundError(exemption_path)

    exemption_raw = exemption_path.read_bytes()
    exemption_text = exemption_raw.decode("utf-8-sig")
    exemption_lines = exemption_text.splitlines()
    exemption_hash = hashlib.sha256(
        exemption_raw
    ).hexdigest()

    required_exemption_lines = {
        18: "Who needs to give their fingerprints and photo",
        24: "Unless you’re exempt",
        27: "excluding US nationals",
        33: "Temporary resident applicants",
        42: "travel document that’s not a passport",
        49: "Who’s exempt from giving their biometrics",
        60: "permanent resident application",
        61: "under the age of 14",
        62: "over the age of 79",
        63: "no upper age exemption for asylum claimants",
        64: "How we assess the age",
        65: "when you submitted your application",
        76: "Date modified: 2026-07-09",
    }

    for number, marker in required_exemption_lines.items():
        if (
            len(exemption_lines) < number
            or marker not in exemption_lines[number - 1]
        ):
            raise ValueError(
                f"Biometrics exemption source mismatch: line {number}"
            )

    exemption_ranges = [
        ("general_submission_and_us_national_scope", 23, 32),
        ("previous_biometrics_and_validity", 33, 40),
        ("special_travel_documents", 42, 48),
        ("enumerated_exemptions", 49, 63),
        ("application_date_age_assessment", 64, 65),
    ]

    exemption_evidence = []

    for index, (topic, first, last) in enumerate(
        exemption_ranges, 1
    ):
        quote = "\n".join(
            exemption_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Exemption evidence unexpectedly short: {topic}"
            )

        exemption_evidence.append({
            "evidence_id": f"CA_STUDY_BIO_EXEMPT_{index:02d}",
            "topic": topic,
            "source_file": (
                exemption_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": exemption_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["biometrics_exemption_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "biometrics/who-needs-to-give.html"
        ),
        "source_language": "en",
        "source_file": (
            exemption_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": exemption_hash,
        "source_last_modified": "2026-07-09",
        "char_count": len(exemption_text),
        "line_count": len(exemption_lines),
        "review_status": "needs_review",
    }

    result["biometrics_exemption_evidence"] = exemption_evidence

    result["biometrics_exemption_requirements"] = {
        "general_scope": {
            "source_evidence_id": "CA_STUDY_BIO_EXEMPT_01",
            "application_types_to_review": [
                "initial_study_permit",
                "study_permit_extension",
            ],
            "us_national_general_exception": True,
            "special_travel_document_override_needs_review": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "previous_biometrics": {
            "source_evidence_id": "CA_STUDY_BIO_EXEMPT_02",
            "reuse_and_exemption_are_distinct": True,
            "validity_years": 10,
            "reuse_conditions_source": (
                "biometrics_reuse_requirements"
            ),
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "special_travel_documents": {
            "source_evidence_id": "CA_STUDY_BIO_EXEMPT_03",
            "documents_to_review": [
                "refugee_travel_document",
                "certificate_of_identity",
                "us_refugee_travel_document_with_required_status",
            ],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "age_based_exemptions": {
            "source_evidence_ids": [
                "CA_STUDY_BIO_EXEMPT_04",
                "CA_STUDY_BIO_EXEMPT_05",
            ],
            "age_reference": "application_submission_date",
            "under_age": 14,
            "over_age": 79,
            "asylum_claimant_upper_age_exception": True,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "status_based_exemptions": {
            "source_evidence_id": "CA_STUDY_BIO_EXEMPT_04",
            "categories_to_review": [
                "canadian_citizen_or_citizenship_applicant",
                "existing_permanent_resident_with_exceptions",
                "visa_exempt_visitor_only",
                "head_of_state_or_government",
                "diplomatic_or_official_visa",
                "us_visa_holder_transiting",
                "pending_pr_application_with_biometrics_submitted",
            ],
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    }

    # Update previously unresolved exemption placeholders.

    result["biometrics_reuse_requirements"].update({
        "detailed_exemption_rules_verified": True,
        "age_exemptions": {
            "under_age": 14,
            "over_age": 79,
            "assessed_at": "application_submission_date",
            "asylum_claimant_exception": True,
        },
        "other_status_exemptions": (
            "see_biometrics_exemption_requirements"
        ),
        "exemption_source_evidence_id": (
            "CA_STUDY_BIO_EXEMPT_04"
        ),
    })

    result["biometrics_process_review"][
        "deadline_and_exemptions"
    ].update({
        "who_must_submit_biometrics": (
            "conditional_on_exemption_and_reuse_review"
        ),
        "exemption_source_evidence_id": (
            "CA_STUDY_BIO_EXEMPT_04"
        ),
        "separate_official_sources_required": False,
    })

    result["biometrics_exemption_legal_review"] = {
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(exemption_evidence) == 5
        and len(result["biometrics_exemption_requirements"]) == 5
        and all(
            item["review_status"] == "needs_review"
            and item["eligibility_rule"] is None
            for item in result[
                "biometrics_exemption_requirements"
            ].values()
        )
        and result["biometrics_exemption_legal_review"][
            "approved_for_eligibility_decision"
        ] is False
    ):
        raise ValueError(
            "Biometrics exemption integration failed"
        )

    if not (
        len(financial_evidence) == 5
        and len(result["financial_living_cost_tables"]) == 2
        and len(result["financial_support_conditions_review"]) == 4
        and all(
            len(table["amounts_by_total_family_members"]) == 7
            and table["review_status"] == "needs_review"
            and table["eligibility_rule"] is None
            and table["legal_validation_approved"] is False
            and table["approved_for_eligibility_decision"] is False
            for table in result["financial_living_cost_tables"]
        )
    ):
        raise ValueError(
            "Financial support integration validation failed"
        )

    if not (
        len(evidence) == 3
        and len(candidates) == 4
        and len(checks) == 13
        and len(REVIEW_GROUPS) == 6
        and all(checks.values())
        and all(
            item["review_status"] == "needs_review"
            and item["eligibility_rule"] is None
            and item["legal_validation_approved"] is False
            and item["approved_for_eligibility_decision"] is False
            for item in candidates
        )
    ):
        raise ValueError("Study Permit consistency check failed")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        from .review_support import attach_official_review
    except ImportError:
        from review_support import attach_official_review
    attach_official_review(result)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("=== CANADA STUDY PERMIT EVIDENCE ===")
    print("SOURCE CHARS:", len(text))
    print("SOURCE LINES:", len(lines))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(candidates))
    print("SOURCE CHECKS:", len(checks))
    print("REVIEW GROUPS:", len(REVIEW_GROUPS))
    print("SOURCE MODIFIED: 2026-01-26")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

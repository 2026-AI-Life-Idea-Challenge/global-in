
"""
Canada IEC Working Holiday - Republic of Korea.

Extract source-linked evidence and draft policy candidates
from the official IRCC eligibility page.

No automatic eligibility rules are approved.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data/raw/canada/working_holiday"
    / "iec_working_holiday_ircc_en.txt"
)

OUTPUT = (
    ROOT / "data/processed/canada/working_holiday"
    / "iec_working_holiday_evidence_draft.json"
)

SOURCE_URL = (
    "https://www.canada.ca/en/immigration-refugees-citizenship/"
    "services/work-canada/iec/eligibility.html?selection=kr-wh"
)

REQUIRED_MARKERS = {
    "korean_citizenship": r"be a citizen of the Republic of Korea",
    "passport": r"valid Korean passport",
    "passport_validity": r"can['’]t be valid longer than your passport",
    "age": r"between the ages of 18 and 35",
    "funds": r"CAN\$2,500",
    "insurance": r"health insurance for the duration",
    "admissibility": r"not be inadmissible to Canada",
    "return_ticket": r"round-trip ticket",
    "dependants": r"not be accompanied by dependants",
    "fees": r"pay the fees",
    "twice": r"participate in IEC twice",
    "duration": r"24 months per participation",
    "young_professionals": r"Young Professionals category",
    "international_coop": r"International Co-op category once",
    "profile_and_ita": r"invitation to apply",
}

EVIDENCE_GROUPS = [
    {
        "topic": "youth_mobility_agreement",
        "first": 23,
        "last": 30,
    },
    {
        "topic": "korea_agreement_and_participation",
        "first": 35,
        "last": 42,
    },
    {
        "topic": "nationality_passport_and_age",
        "first": 44,
        "last": 49,
    },
    {
        "topic": "financial_and_insurance_requirements",
        "first": 50,
        "last": 52,
    },
    {
        "topic": "admissibility_travel_dependants_and_fees",
        "first": 53,
        "last": 57,
    },
    {
        "topic": "application_navigation_and_source_date",
        "first": 59,
        "last": 70,
    },
]

POLICY_DEFINITIONS = [
    {
        "policy_id": "CA_IEC_WH_POL_01",
        "topic": "citizenship_and_age",
        "evidence_topics": [
            "nationality_passport_and_age",
        ],
        "conditions_to_review": [
            "citizenship_republic_of_korea",
            "age_18_to_35_inclusive",
            "age_calculation_at_relevant_application_stage",
        ],
    },
    {
        "policy_id": "CA_IEC_WH_POL_02",
        "topic": "passport_and_participation",
        "evidence_topics": [
            "korea_agreement_and_participation",
            "nationality_passport_and_age",
        ],
        "conditions_to_review": [
            "passport_valid_for_intended_stay",
            "permit_not_longer_than_passport",
            "maximum_two_iec_participations",
            "maximum_24_months_per_participation",
            "prior_participation_under_old_agreement",
            "category_specific_participation_limits",
        ],
    },
    {
        "policy_id": "CA_IEC_WH_POL_03",
        "topic": "financial_and_travel_proof",
        "evidence_topics": [
            "financial_and_insurance_requirements",
            "admissibility_travel_dependants_and_fees",
        ],
        "conditions_to_review": [
            "minimum_cad_2500",
            "round_trip_ticket_or_departure_funds",
            "local_cost_of_living",
            "proof_at_applicable_application_or_entry_stage",
        ],
    },
    {
        "policy_id": "CA_IEC_WH_POL_04",
        "topic": "insurance_and_admissibility",
        "evidence_topics": [
            "financial_and_insurance_requirements",
            "admissibility_travel_dependants_and_fees",
        ],
        "conditions_to_review": [
            "insurance_for_entire_stay",
            "insurance_evidence_at_entry",
            "not_inadmissible_to_canada",
        ],
    },
    {
        "policy_id": "CA_IEC_WH_POL_05",
        "topic": "dependants_fees_and_application",
        "evidence_topics": [
            "admissibility_travel_dependants_and_fees",
            "application_navigation_and_source_date",
        ],
        "conditions_to_review": [
            "not_accompanied_by_dependants",
            "applicable_fees",
            "iec_profile",
            "invitation_to_apply",
            "work_permit_application",
        ],
    },
]

REVIEW_GROUPS = {
    "citizenship_and_age": [
        "Korean citizenship",
        "age 18 to 35 inclusive",
        "age assessment timing",
    ],
    "passport_and_validity": [
        "passport valid for stay",
        "permit validity limited by passport",
    ],
    "participation_history": [
        "maximum two IEC participations",
        "previous agreement participation",
        "Working Holiday and Young Professionals category choices",
        "International Co-op participation limitation",
    ],
    "financial_and_travel": [
        "CAD 2500 minimum",
        "departure ticket or sufficient funds",
        "financial proof timing",
    ],
    "insurance_and_admissibility": [
        "health insurance for full stay",
        "insurance evidence at border",
        "admissibility",
    ],
    "dependants_and_fees": [
        "not accompanied by dependants",
        "fees and applicable amounts",
    ],
    "application_process": [
        "profile creation",
        "invitation to apply",
        "work permit application",
        "availability and invitation not confirmed by eligibility",
    ],
}


def load_source():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()

    if len(text) < 3500:
        raise ValueError("IRCC source unexpectedly short")

    if re.search(r"<!DOCTYPE|<html|<script", text, re.I):
        raise ValueError("HTML detected instead of plain text")

    checks = {
        name: bool(re.search(pattern, text, re.I))
        for name, pattern in REQUIRED_MARKERS.items()
    }

    missing = [
        name for name, matched in checks.items()
        if not matched
    ]

    if missing:
        raise ValueError(f"Source markers missing: {missing}")

    expected_lines = {
        35: "Republic of Korea",
        44: "To be eligible for the Working Holiday category",
        49: "between the ages of 18 and 35",
        50: "CAN$2,500",
        70: "2026-08-07",
    }

    for number, marker in expected_lines.items():
        actual = lines[number - 1]
        if marker not in actual:
            raise ValueError(
                f"Source layout changed at line {number}: "
                f"{actual!r}"
            )

    return raw, text, lines, checks


def extract_evidence(lines, source_hash):
    evidence = []

    for number, group in enumerate(EVIDENCE_GROUPS, 1):
        first = group["first"]
        last = group["last"]

        quote = "\n".join(
            lines[first - 1:last]
        ).strip()

        if len(quote) < 50:
            raise ValueError(
                f"Evidence unexpectedly short: {group['topic']}"
            )

        evidence.append({
            "evidence_id": f"CA_IEC_WH_EVD_{number:02d}",
            "topic": group["topic"],
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "source_sha256": source_hash,
            "review_status": "needs_review",
        })

    return evidence


def build_candidates(evidence):
    evidence_by_topic = {
        item["topic"]: item["evidence_id"]
        for item in evidence
    }

    candidates = []

    for definition in POLICY_DEFINITIONS:
        source_ids = [
            evidence_by_topic[topic]
            for topic in definition["evidence_topics"]
        ]

        candidates.append({
            "policy_id": definition["policy_id"],
            "topic": definition["topic"],
            "source_evidence_ids": source_ids,
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

    evidence = extract_evidence(
        lines, source_hash
    )

    candidates = build_candidates(evidence)

    result = {
        "country": "Canada",
        "program": "iec_working_holiday",
        "program_category": "working_holiday",
        "target_citizenship": "Republic of Korea",
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
            "source_last_modified": "2026-08-07",
        },
        "evidence": evidence,
        "policy_candidates": candidates,
        "source_requirement_checks": checks,
        "conditional_requirements": {
            topic: {
                "review_points": points,
                "eligibility_rule": None,
                "review_status": "needs_review",
            }
            for topic, points in REVIEW_GROUPS.items()
        },
        "reference_values": {
            "age_min": 18,
            "age_max_inclusive": 35,
            "maximum_iec_participations": 2,
            "maximum_months_per_participation": 24,
            "minimum_initial_funds_cad": 2500,
            "source_evidence_id": "CA_IEC_WH_EVD_02",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "agreement_change_review": {
            "previous_participation_limit": 1,
            "previous_maximum_months": 12,
            "current_participation_limit": 2,
            "current_maximum_months": 24,
            "prior_participation_transition": "needs_review",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "related_programs_to_review": [
            "iec_young_professionals",
            "iec_international_coop",
        ],
        "application_process_review": [
            "create_iec_profile",
            "receive_invitation_to_apply",
            "submit_work_permit_application",
        ],
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }
    
    # Supplementary IRCC evidence: IEC profile, invitation and deadlines.
    process_path = (
        ROOT / "data/raw/canada/working_holiday"
        / "iec_profile_invitation_ircc_en.txt"
    )

    if not process_path.is_file():
        raise FileNotFoundError(process_path)

    process_raw = process_path.read_bytes()
    process_text = process_raw.decode("utf-8-sig")
    process_lines = process_text.splitlines()
    process_hash = hashlib.sha256(process_raw).hexdigest()

    expected_lines = {
        22: "Create your IEC profile and get your invitation to apply",
        29: "2026 IEC season is closed",
        42: "Step 1: Use the IRCC secure account",
        56: "Step 2: Complete your IEC profile",
        79: "Step 3: Submit your profile",
        94: "Step 4: Wait for an ITA",
        112: "Step 5: Respond to your ITA",
        136: "Date modified: 2026-10-19",
    }

    for number, marker in expected_lines.items():
        if (
            len(process_lines) < number
            or marker not in process_lines[number - 1]
        ):
            raise ValueError(
                f"IEC process source layout mismatch: line {number}"
            )

    process_source = {
        "authority": "Immigration, Refugees and Citizenship Canada",
        "source_url": (
            "https://www.canada.ca/en/immigration-refugees-citizenship/"
            "services/work-canada/iec/become-candidate.html"
        ),
        "source_file": process_path.relative_to(ROOT).as_posix(),
        "source_sha256": process_hash,
        "source_language": "en",
        "char_count": len(process_text),
        "line_count": len(process_lines),
        "source_last_modified": "2026-10-19",
        "review_status": "needs_review",
    }

    process_ranges = [
        ("profile_and_season_status", 22, 30),
        ("eligibility_questionnaire", 42, 53),
        ("profile_completion", 56, 77),
        ("submission_and_invitation_pool", 79, 109),
        ("invitation_response_and_application", 112, 127),
    ]

    process_evidence = []

    for index, (topic, first, last) in enumerate(
        process_ranges, 1
    ):
        quote = "\n".join(
            process_lines[first - 1:last]
        ).strip()

        if len(quote) < 50:
            raise ValueError(
                f"IEC process evidence too short: {topic}"
            )

        process_evidence.append({
            "evidence_id": f"CA_IEC_WH_PROCESS_EVD_{index:02d}",
            "topic": topic,
            "source_file": process_source["source_file"],
            "source_sha256": process_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["application_process_source"] = process_source
    result["application_process_evidence"] = process_evidence

    result["application_process_steps"] = [
        {
            "step": "eligibility_questionnaire",
            "source_evidence_id": "CA_IEC_WH_PROCESS_EVD_02",
        },
        {
            "step": "complete_profile",
            "source_evidence_id": "CA_IEC_WH_PROCESS_EVD_03",
        },
        {
            "step": "submit_profile",
            "source_evidence_id": "CA_IEC_WH_PROCESS_EVD_04",
        },
        {
            "step": "wait_for_invitation",
            "source_evidence_id": "CA_IEC_WH_PROCESS_EVD_04",
        },
        {
            "step": "respond_to_invitation",
            "source_evidence_id": "CA_IEC_WH_PROCESS_EVD_05",
        },
        {
            "step": "submit_work_permit_application",
            "source_evidence_id": "CA_IEC_WH_PROCESS_EVD_05",
        },
    ]

    result["application_deadline_review"] = {
        "profile_completion_days": 60,
        "ita_acceptance_days": 10,
        "work_permit_application_days_after_acceptance": 20,
        "ita_deadline_source": "deadline stated in individual invitation",
        "work_permit_deadline_start": (
            "day and time the applicant accepts the ITA"
        ),
        "source_evidence_ids": [
            "CA_IEC_WH_PROCESS_EVD_03",
            "CA_IEC_WH_PROCESS_EVD_05",
        ],
        "automatic_deadline_calculation_approved": False,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["application_availability"] = {
        "season_year": 2026,
        "source_status": "closed",
        "source_statement": "The pools for the 2026 season are closed.",
        "source_evidence_id": "CA_IEC_WH_PROCESS_EVD_01",
        "source_last_modified": "2026-10-19",
        "current_or_future_season_status": "additional_confirmation",
        "automatic_availability_decision_approved": False,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["application_process_review"] = {
        "profile_is_not_work_permit_application": True,
        "invitation_required_before_work_permit_application": True,
        "one_iec_profile_at_a_time": True,
        "multiple_eligible_category_pools_possible": True,
        "invitation_not_guaranteed": True,
        "one_iec_permit_per_season": True,
        "previous_participations_reviewed_by_officer": True,
        "individual_invitation_status": "unknown",
        "source_evidence_ids": [
            "CA_IEC_WH_PROCESS_EVD_04",
            "CA_IEC_WH_PROCESS_EVD_05",
        ],
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    if not (
        len(process_evidence) == 5
        and len(result["application_process_steps"]) == 6
        and result["application_availability"]["season_year"] == 2026
        and len(candidates) == 5
    ):
        raise ValueError("IEC process integration check failed")
    
    # IRCC work permit application evidence.
    # Preserve the existing eligibility and ITA evidence.

    permit_path = (
        ROOT / "data/raw/canada/working_holiday"
        / "iec_work_permit_application_ircc_en.txt"
    )

    if not permit_path.is_file():
        raise FileNotFoundError(permit_path)

    permit_raw = permit_path.read_bytes()
    permit_text = permit_raw.decode("utf-8-sig")
    permit_lines = permit_text.splitlines()
    permit_hash = hashlib.sha256(permit_raw).hexdigest()

    expected_permit_lines = {
        20: "Submit your work permit application",
        32: "Step 1: Make sure you know the date and time",
        40: "Step 2: Complete the online forms",
        62: "Step 3: Get all the documents you need",
        94: "Step 4: Pay your fees",
        111: "Step 5: Submit your complete application",
        130: "Step 6: Give your biometrics",
        153: "Date modified: 2026-05-28",
    }

    for number, marker in expected_permit_lines.items():
        if (
            len(permit_lines) < number
            or marker not in permit_lines[number - 1]
        ):
            raise ValueError(
                f"Work permit source changed at line {number}"
            )

    permit_ranges = [
        ("application_deadline_utc", 32, 38),
        ("online_application_form", 40, 61),
        ("personalised_document_checklist", 62, 93),
        ("application_fees", 94, 108),
        ("submission_and_biometrics", 111, 146),
    ]

    permit_evidence = []

    for index, (topic, first, last) in enumerate(
        permit_ranges, 1
    ):
        quote = "\n".join(
            permit_lines[first - 1:last]
        ).strip()

        if len(quote) < 80:
            raise ValueError(
                f"Work permit evidence too short: {topic}"
            )

        permit_evidence.append({
            "evidence_id": (
                f"CA_IEC_WH_PERMIT_EVD_{index:02d}"
            ),
            "topic": topic,
            "source_file": permit_path.relative_to(ROOT).as_posix(),
            "source_sha256": permit_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["work_permit_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/iec/apply-work-permit.html"
        ),
        "source_language": "en",
        "source_file": permit_path.relative_to(ROOT).as_posix(),
        "source_sha256": permit_hash,
        "char_count": len(permit_text),
        "line_count": len(permit_lines),
        "source_last_modified": "2026-05-28",
        "review_status": "needs_review",
    }

    result["work_permit_evidence"] = permit_evidence

    result["work_permit_application_steps"] = [
        "confirm_deadline_in_utc",
        "complete_online_forms",
        "prepare_personalised_document_checklist",
        "pay_applicable_fees",
        "submit_complete_application",
        "provide_biometrics_if_required",
    ]

    result["work_permit_document_review"] = {
        "source_evidence_id": "CA_IEC_WH_PERMIT_EVD_03",
        "documents_to_review": [
            "passport",
            "digital_photo",
            "curriculum_vitae",
            "police_certificates_if_required",
            "medical_exam_if_required",
            "family_information_if_required",
            "proof_of_residency_if_required",
            "other_personalised_documents",
        ],
        "personalised_checklist_required": True,
        "all_listed_documents_universally_required": False,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["work_permit_fee_review"] = {
        "reference_year": 2026,
        "currency": "CAD",
        "iec_participation_fee": 184.75,
        "working_holiday_open_work_permit_fee": 100.00,
        "working_holiday_base_total": 284.75,
        "biometrics_fee": "additional_if_applicable",
        "employer_compliance_fee_scope": (
            "Young Professionals and International Co-op; "
            "not included in Working Holiday base total"
        ),
        "source_evidence_id": "CA_IEC_WH_PERMIT_EVD_04",
        "current_fee_confirmation_required": True,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["work_permit_deadline_review"] = {
        "days_after_ita_acceptance": 20,
        "deadline_timezone": "UTC",
        "deadline_source": "individual_IRCC_account_message",
        "biometrics_days_if_required": 30,
        "biometrics_trigger": (
            "biometric_instruction_letter"
        ),
        "automatic_deadline_calculation_approved": False,
        "source_evidence_ids": [
            "CA_IEC_WH_PERMIT_EVD_01",
            "CA_IEC_WH_PERMIT_EVD_05",
        ],
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["work_permit_exceptions_review"] = {
        "missing_police_certificate": (
            "proof_of_request_may_be_submitted"
        ),
        "missing_medical_exam": (
            "proof_of_appointment_may_be_submitted"
        ),
        "processing_delay_possible": True,
        "application_approval_not_guaranteed": True,
        "source_evidence_id": "CA_IEC_WH_PERMIT_EVD_05",
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    if not (
        len(permit_evidence) == 5
        and len(result["work_permit_application_steps"]) == 6
        and len(
            result["work_permit_document_review"][
                "documents_to_review"
            ]
        ) == 8
        and result["work_permit_fee_review"][
            "working_holiday_base_total"
        ] == 284.75
    ):
        raise ValueError(
            "IEC work permit integration check failed"
        )
    
    # IRCC arrival and port-of-entry evidence.
    # Preserve all existing eligibility and application evidence.

    arrival_path = (
        ROOT / "data/raw/canada/working_holiday"
        / "iec_prepare_arrival_ircc_en.txt"
    )

    if not arrival_path.is_file():
        raise FileNotFoundError(arrival_path)

    arrival_raw = arrival_path.read_bytes()
    arrival_text = arrival_raw.decode("utf-8-sig")
    arrival_lines = arrival_text.splitlines()
    arrival_hash = hashlib.sha256(arrival_raw).hexdigest()

    expected_arrival_lines = {
        20: "Prepare for arrival",
        26: "Arriving in Canada",
        41: "Proof of health insurance",
        57: "Proof of funds",
        69: "Review your work permit",
        93: "Date modified: 2025-11-17",
    }

    for number, marker in expected_arrival_lines.items():
        if (
            len(arrival_lines) < number
            or marker not in arrival_lines[number - 1]
        ):
            raise ValueError(
                f"IEC arrival source layout mismatch: line {number}"
            )

    arrival_ranges = [
        ("port_of_entry_documents", 26, 39),
        ("health_insurance_requirements", 41, 55),
        ("financial_proof", 57, 62),
        ("currency_declaration", 64, 68),
        ("work_permit_review_and_validity", 69, 89),
    ]

    arrival_evidence = []

    for index, (topic, first, last) in enumerate(
        arrival_ranges, 1
    ):
        quote = "\n".join(
            arrival_lines[first - 1:last]
        ).strip()

        if len(quote) < 70:
            raise ValueError(
                f"IEC arrival evidence too short: {topic}"
            )

        arrival_evidence.append({
            "evidence_id": (
                f"CA_IEC_WH_ARRIVAL_EVD_{index:02d}"
            ),
            "topic": topic,
            "source_file": arrival_path.relative_to(ROOT).as_posix(),
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
            "work-canada/iec/prepare-arrival.html"
        ),
        "source_language": "en",
        "source_file": arrival_path.relative_to(ROOT).as_posix(),
        "source_sha256": arrival_hash,
        "char_count": len(arrival_text),
        "line_count": len(arrival_lines),
        "source_last_modified": "2025-11-17",
        "review_status": "needs_review",
    }

    result["arrival_evidence"] = arrival_evidence

    result["arrival_document_review"] = {
        "source_evidence_id": "CA_IEC_WH_ARRIVAL_EVD_01",
        "documents_to_review": [
            "valid_passport",
            "poe_letter_of_introduction",
            "health_insurance_proof",
            "proof_of_funds",
            "departure_ticket_or_sufficient_funds",
            "copies_of_work_permit_application_documents",
        ],
        "poe_letter_is_not_work_permit": True,
        "final_work_permit_issuance_at_border": True,
        "border_officer_admissibility_review_required": True,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["arrival_insurance_review"] = {
        "source_evidence_id": "CA_IEC_WH_ARRIVAL_EVD_02",
        "required_coverage_to_review": [
            "medical_care",
            "hospitalization",
            "repatriation",
        ],
        "insurance_valid_for_entire_stay": True,
        "provincial_health_card_alone_insufficient": True,
        "short_insurance_may_shorten_permit": True,
        "extension_after_insurance_based_shortening": (
            "not_permitted_under_source_guidance"
        ),
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["arrival_financial_review"] = {
        "source_evidence_id": "CA_IEC_WH_ARRIVAL_EVD_03",
        "currency": "CAD",
        "minimum_initial_funds": 2500,
        "covered_period_months": 3,
        "bank_statement_max_age_before_departure_days": 7,
        "departure_ticket_funds_review": True,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["arrival_currency_declaration_review"] = {
        "source_evidence_id": "CA_IEC_WH_ARRIVAL_EVD_04",
        "currency": "CAD",
        "declaration_threshold": 10000,
        "scope": (
            "Currency and monetary instruments carried "
            "into Canada, not ordinary bank account balance"
        ),
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["arrival_work_permit_review"] = {
        "source_evidence_id": "CA_IEC_WH_ARRIVAL_EVD_05",
        "validity_limiters_to_review": [
            "youth_mobility_agreement_duration",
            "passport_expiry",
            "biometrics_expiry",
            "health_insurance_expiry",
        ],
        "other_categories_only": [
            "employment_contract_end_date_for_young_professionals",
            "employment_contract_end_date_for_international_coop",
        ],
        "checks_at_port_of_entry": [
            "name_spelling",
            "permit_expiry",
            "medical_work_restrictions",
            "other_permit_conditions_if_applicable",
        ],
        "report_errors_before_leaving_port_of_entry": True,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    if not (
        len(arrival_evidence) == 5
        and len(
            result["arrival_document_review"]["documents_to_review"]
        ) == 6
        and len(
            result["arrival_insurance_review"]["required_coverage_to_review"]
        ) == 3
        and len(
            result["arrival_work_permit_review"]["validity_limiters_to_review"]
        ) == 4
    ):
        raise ValueError(
            "IEC arrival evidence integration check failed"
        )

    if not (
        len(evidence) == 6
        and len(candidates) == 5
        and len(checks) == 15
        and len(REVIEW_GROUPS) == 7
        and all(checks.values())
        and all(
            candidate["review_status"] == "needs_review"
            and candidate["eligibility_rule"] is None
            and candidate["legal_validation_approved"] is False
            and candidate["approved_for_eligibility_decision"] is False
            for candidate in candidates
        )
    ):
        raise ValueError("IEC Working Holiday consistency check failed")

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
        from .review_support import attach_official_review
    except ImportError:
        from review_support import attach_official_review
    attach_official_review(result)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("=== CANADA IEC WORKING HOLIDAY EVIDENCE ===")
    print("SOURCE CHARS:", len(text))
    print("SOURCE LINES:", len(lines))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(candidates))
    print("SOURCE CHECKS:", len(checks))
    print("REVIEW GROUPS:", len(REVIEW_GROUPS))
    print("SOURCE MODIFIED: 2026-08-07")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()

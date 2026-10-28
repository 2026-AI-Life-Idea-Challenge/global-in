
"""
Canada Employer-Specific Work Permit evidence extraction.

Source: IRCC Employer-specific work permits.
Policy candidates are unapproved review drafts.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data/raw/canada/employment"
    / "employer_specific_eligibility_ircc_en.txt"
)

OUTPUT = (
    ROOT / "data/processed/canada/employment"
    / "employer_specific_evidence_draft.json"
)

SOURCE_URL = (
    "https://www.canada.ca/en/"
    "immigration-refugees-citizenship/services/"
    "work-canada/employer-specific.html"
)

REQUIRED_LINES = {
    11: "Employer-specific work permits",
    12: "2 types of work permits",
    14: "employer needs to take steps",
    22: "What is an employer-specific work permit",
    23: "conditions of the permit",
    25: "employer, location and occupation",
    26: "Conditions",
    30: "comply with all the information",
    37: "What you need to apply",
    40: "non-compliant employers",
    41: "general requirements",
    49: "labour market impact assessment",
    50: "Most jobs need an LMIA",
    54: "LMIA-exempt",
    56: "LMIA letter and Annex A",
    66: "Apply for an employer-specific work permit",
    85: "Date modified: 2026-03-31",
}

EVIDENCE_RANGES = [
    ("permit_types_and_employer_preconditions", 11, 14),
    ("permit_conditions_and_restrictions", 22, 30),
    ("job_offer_and_general_requirements", 37, 47),
    ("lmia_and_employer_preparation", 49, 58),
    ("application_locations_and_extension", 60, 78),
]

POLICY_DEFINITIONS = [
    (
        "CA_ESWP_POL_01",
        "job_offer_and_employer_compliance",
        [
            "genuine_job_offer",
            "employer_not_on_non_compliant_list",
            "employer_identity",
            "employment_contract",
        ],
        ["job_offer_and_general_requirements"],
    ),
    (
        "CA_ESWP_POL_02",
        "general_work_permit_eligibility",
        [
            "general_work_permit_requirements",
            "admissibility",
            "applicant_documents",
            "work_permit_required_or_exempt",
        ],
        ["job_offer_and_general_requirements"],
    ),
    (
        "CA_ESWP_POL_03",
        "lmia_required_path",
        [
            "lmia_requirement_classification",
            "positive_lmia",
            "lmia_letter",
            "annex_a",
            "employer_pre_application_steps",
        ],
        ["lmia_and_employer_preparation"],
    ),
    (
        "CA_ESWP_POL_04",
        "lmia_exempt_path",
        [
            "lmia_exemption_category",
            "official_exemption_code",
            "employer_portal_submission_if_applicable",
            "offer_of_employment_number_if_applicable",
            "employer_compliance_fee_if_applicable",
        ],
        ["lmia_and_employer_preparation"],
    ),
    (
        "CA_ESWP_POL_05",
        "permit_conditions_and_application_route",
        [
            "named_employer",
            "occupation",
            "work_location",
            "permit_conditions",
            "application_location",
            "extension_or_change_of_conditions",
        ],
        [
            "permit_conditions_and_restrictions",
            "application_locations_and_extension",
        ],
    ),
]


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    source_raw = SOURCE.read_bytes()
    source_text = source_raw.decode("utf-8-sig")
    source_lines = source_text.splitlines()
    source_hash = hashlib.sha256(source_raw).hexdigest()

    if len(source_text) < 3000 or len(source_lines) != 122:
        raise ValueError(
            "Employer-specific source length differs "
            "from reviewed source"
        )

    if re.search(r"<!DOCTYPE|<html|<script", source_text, re.I):
        raise ValueError("Expected plain-text IRCC source")

    for number, marker in REQUIRED_LINES.items():
        if marker not in source_lines[number - 1]:
            raise ValueError(
                f"Source mismatch at line {number}: {marker}"
            )

    evidence = []

    for index, (topic, first, last) in enumerate(
        EVIDENCE_RANGES, 1
    ):
        quote = "\n".join(
            source_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Evidence unexpectedly short: {topic}"
            )

        evidence.append({
            "evidence_id": f"CA_ESWP_EVD_{index:02d}",
            "topic": topic,
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    evidence_by_topic = {
        item["topic"]: item["evidence_id"]
        for item in evidence
    }

    policy_candidates = []

    for policy_id, topic, conditions, evidence_topics in (
        POLICY_DEFINITIONS
    ):
        policy_candidates.append({
            "policy_id": policy_id,
            "topic": topic,
            "conditions_to_review": conditions,
            "source_evidence_ids": [
                evidence_by_topic[name]
                for name in evidence_topics
            ],
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result = {
        "country": "Canada",
        "program": "employer_specific_work_permit",
        "program_category": "employment",
        "official_source": {
            "authority": (
                "Immigration, Refugees and Citizenship Canada"
            ),
            "source_url": SOURCE_URL,
            "source_language": "en",
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "source_last_modified": "2026-03-31",
            "char_count": len(source_text),
            "line_count": len(source_lines),
        },
        "evidence": evidence,
        "policy_candidates": policy_candidates,
        "lmia_path_review": {
            "lmia_required": {
                "source_evidence_id": "CA_ESWP_EVD_04",
                "positive_lmia_and_annex_a": (
                    "conditional_source_requirement"
                ),
                "detailed_rules_verified": False,
                "eligibility_rule": None,
                "legal_validation_approved": False,
                "approved_for_eligibility_decision": False,
                "review_status": "needs_review",
            },
            "lmia_exempt": {
                "source_evidence_id": "CA_ESWP_EVD_04",
                "exemption_code": None,
                "employer_portal_requirement_verified": False,
                "employer_compliance_fee_verified": False,
                "detailed_rules_verified": False,
                "eligibility_rule": None,
                "legal_validation_approved": False,
                "approved_for_eligibility_decision": False,
                "review_status": "needs_review",
            },
        },
        "permit_condition_review": {
            "permit_fields": [
                "employer",
                "location",
                "occupation",
                "conditions",
                "remarks",
            ],
            "source_evidence_id": "CA_ESWP_EVD_02",
            "automatic_work_authorization": False,
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        },
        "application_route_review": {
            "routes": [
                "outside_canada",
                "inside_canada",
                "port_of_entry",
                "extension",
            ],
            "route_specific_rules_verified": False,
            "source_evidence_id": "CA_ESWP_EVD_05",
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        },
        "application_availability": {
            "status": "not_verified",
            "last_checked": None,
            "review_status": "needs_review",
        },
        "follow_up_sources_required": [
            "general_work_permit_eligibility",
            "lmia_required_employer_steps",
            "lmia_exempt_employer_steps",
            "application_documents",
            "application_inside_outside_canada",
            "port_of_entry_eligibility",
            "permit_fees_and_biometrics",
            "extension_and_employer_change",
        ],
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    def safe(item):
        return (
            item["review_status"] == "needs_review"
            and item["eligibility_rule"] is None
            and item["legal_validation_approved"] is False
            and item["approved_for_eligibility_decision"] is False
        )

    if not (
        len(evidence) == 5
        and len(policy_candidates) == 5
        and len(REQUIRED_LINES) == 17
        and len(evidence_by_topic) == 5
        and all(map(safe, policy_candidates))
        and all(map(safe, result["lmia_path_review"].values()))
        and safe(result["permit_condition_review"])
        and safe(result["application_route_review"])
        and safe(result)
    ):
        raise ValueError(
            "Employer-specific evidence consistency check failed"
        )
    
    # Official IRCC LMIA requirement and hiring-path evidence.
    # LMIA exemptions and work permit exemptions are distinct.
    # Do not activate eligibility decisions from these drafts.

    lmia_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_lmia_requirement_ircc_en.txt"
    )

    if not lmia_path.is_file():
        raise FileNotFoundError(lmia_path)

    lmia_raw = lmia_path.read_bytes()
    lmia_text = lmia_raw.decode("utf-8-sig")
    lmia_lines = lmia_text.splitlines()
    lmia_hash = hashlib.sha256(lmia_raw).hexdigest()

    required_lmia_lines = {
        13: "Find out if you need a labour market impact assessment",
        14: "positive or negative effect",
        16: "A positive LMIA confirms",
        20: "Most employers need an LMIA",
        23: "open work permit",
        31: "Determine if you need an LMIA",
        35: "worker needs a work permit",
        39: "LMIA exemption codes",
        40: "work permit exemptions",
        45: "How to hire if you need an LMIA",
        46: "Temporary Foreign Worker Program",
        48: "Employment and Social Development Canada",
        53: "positive LMIA decision letter",
        57: "Annex A",
        61: "How to hire if you don’t need an LMIA",
        62: "International Mobility Program",
        66: "Hiring in Quebec",
        72: "Global Skills Strategy",
        74: "with or without an LMIA",
        82: "Date modified: 2026-04-23",
    }

    for number, marker in required_lmia_lines.items():
        if (
            len(lmia_lines) < number
            or marker not in lmia_lines[number - 1]
        ):
            raise ValueError(
                f"LMIA source mismatch at line {number}: {marker}"
            )

    lmia_ranges = [
        ("lmia_meaning_and_open_permit", 13, 23),
        ("lmia_and_work_permit_exemption_checks", 31, 44),
        ("tfwp_positive_lmia_and_annex_a", 45, 59),
        ("imp_lmia_exempt_hiring", 61, 64),
        ("quebec_and_global_skills_strategy", 66, 76),
    ]

    lmia_evidence = []

    for index, (topic, first, last) in enumerate(
        lmia_ranges, 1
    ):
        quote = "\n".join(
            lmia_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"LMIA evidence unexpectedly short: {topic}"
            )

        lmia_evidence.append({
            "evidence_id": f"CA_ESWP_LMIA_EVD_{index:02d}",
            "topic": topic,
            "source_file": lmia_path.relative_to(ROOT).as_posix(),
            "source_sha256": lmia_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["lmia_requirement_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/hire-temporary-foreign/"
            "find-need-labour-market-impact-assessment.html"
        ),
        "source_language": "en",
        "source_file": lmia_path.relative_to(ROOT).as_posix(),
        "source_sha256": lmia_hash,
        "source_last_modified": "2026-04-23",
        "char_count": len(lmia_text),
        "line_count": len(lmia_lines),
        "review_status": "needs_review",
    }

    result["lmia_evidence"] = lmia_evidence

    lmia_requirements = {
        "lmia_meaning": {
            "positive_lmia_context_verified": True,
            "existing_open_work_permit_lmia_exemption": True,
            "source_evidence_id": "CA_ESWP_LMIA_EVD_01",
        },
        "requirement_classification": {
            "lmia_requirement_status": "additional_review",
            "work_permit_requirement_status": "additional_review",
            "employer_preparation_status": "additional_review",
            "lmia_and_work_permit_exemptions_separate": True,
            "official_exemption_codes_required": True,
            "source_evidence_id": "CA_ESWP_LMIA_EVD_02",
        },
        "lmia_required_tfwp": {
            "program": "Temporary Foreign Worker Program",
            "lmia_authority": (
                "Employment and Social Development Canada"
            ),
            "positive_lmia_decision_letter_required": True,
            "annex_a_employment_details_required": True,
            "employer_provides_documents_to_worker": True,
            "worker_work_permit_application_required": True,
            "source_evidence_id": "CA_ESWP_LMIA_EVD_03",
        },
        "lmia_exempt_imp": {
            "program": "International Mobility Program",
            "lmia_exemption_code": None,
            "employer_portal_rules_verified": False,
            "employer_compliance_fee_verified": False,
            "work_permit_exemption_assumed": False,
            "source_evidence_id": "CA_ESWP_LMIA_EVD_04",
        },
        "special_routes": {
            "quebec_separate_requirements": True,
            "gss_lmia_or_exempt_route_possible": True,
            "detailed_route_rules_verified": False,
            "source_evidence_id": "CA_ESWP_LMIA_EVD_05",
        },
    }

    for group in lmia_requirements.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["lmia_requirements_review"] = lmia_requirements

    # Update the existing LMIA branches without approving them.

    result["lmia_path_review"]["lmia_required"].update({
        "program": "Temporary Foreign Worker Program",
        "positive_lmia_decision_letter_required": True,
        "annex_a_employment_details_required": True,
        "source_evidence_id": "CA_ESWP_LMIA_EVD_03",
        "detailed_rules_verified": False,
    })

    result["lmia_path_review"]["lmia_exempt"].update({
        "program": "International Mobility Program",
        "source_evidence_id": "CA_ESWP_LMIA_EVD_04",
        "detailed_rules_verified": False,
    })

    result["lmia_requirement_legal_review"] = {
        "lmia_requirement_rule_approved": False,
        "work_permit_exemption_rule_approved": False,
        "tfwp_employer_process_complete": False,
        "imp_employer_process_complete": False,
        "quebec_rules_verified": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in lmia_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(lmia_evidence) == 5
        and len(lmia_requirements) == 5
        and len({
            item["evidence_id"]
            for item in lmia_evidence
        }) == 5
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in lmia_requirements.values()
        )
        and all(
            group["approved_for_eligibility_decision"] is False
            for group in result["lmia_path_review"].values()
        )
    ):
        raise ValueError("LMIA requirement integration failed")
    
    # IRCC International Mobility Program employer procedures.
    # Employer Portal, compliance fee, LMIA and work permit
    # exemptions must be evaluated independently.
    # This is review evidence, not an approved eligibility rule.

    imp_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_imp_how_to_hire_ircc_en.txt"
    )

    if not imp_path.is_file():
        raise FileNotFoundError(imp_path)

    imp_raw = imp_path.read_bytes()
    imp_text = imp_raw.decode("utf-8-sig")
    imp_lines = imp_text.splitlines()
    imp_hash = hashlib.sha256(imp_raw).hexdigest()

    required_imp_lines = {
        19: "How to hire a worker",
        25: "Submit an offer of employment",
        28: "March 13, 2026",
        32: "In most cases",
        34: "$230",
        35: "Employer Portal",
        38: "your business",
        41: "wage and benefits",
        45: "French-speaking or bilingual",
        48: "speaking and listening in French",
        49: "outside the province of Quebec",
        53: "overnight camp counsellor",
        57: "Innovation Stream",
        58: "Global Hypergrowth Project",
        60: "TEER",
        61: "wage assessment",
        64: "open work permit",
        69: "Employer Portal",
        75: "After you submit an offer of employment",
        76: "7-digit number",
        78: "work permit application",
        80: "Applying for a work permit",
        84: "port of entry letter",
        85: "border services officer",
        87: "mail them a work permit",
        92: "can no longer apply",
        96: "outside of Canada",
        98: "maintained status",
        103: "admissible to Canada",
        107: "visitor visa",
        108: "medical examination",
        110: "valid work permit",
        111: "rights as a worker",
        118: "Date modified: 2026-04-23",
    }

    for number, marker in required_imp_lines.items():
        if (
            len(imp_lines) < number
            or marker not in imp_lines[number - 1]
        ):
            raise ValueError(
                f"IMP source mismatch at line {number}: {marker}"
            )

    imp_ranges = [
        ("employer_portal_and_compliance_fee", 25, 41),
        ("special_lmia_exempt_hiring", 42, 61),
        ("open_permit_and_employer_exemptions", 62, 71),
        ("offer_number_and_worker_application", 75, 78),
        ("inside_outside_canada_decisions", 80, 87),
        ("port_of_entry_and_maintained_status", 89, 104),
        ("entry_documents_medical_and_rights", 106, 111),
    ]

    imp_evidence = []

    for index, (topic, first, last) in enumerate(
        imp_ranges, 1
    ):
        quote = "\n".join(
            imp_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"IMP evidence unexpectedly short: {topic}"
            )

        imp_evidence.append({
            "evidence_id": f"CA_ESWP_IMP_EVD_{index:02d}",
            "topic": topic,
            "source_file": imp_path.relative_to(ROOT).as_posix(),
            "source_sha256": imp_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["imp_employer_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/hire-temporary-foreign/"
            "international-mobility-program/how-to-hire.html"
        ),
        "source_language": "en",
        "source_file": imp_path.relative_to(ROOT).as_posix(),
        "source_sha256": imp_hash,
        "source_last_modified": "2026-04-23",
        "char_count": len(imp_text),
        "line_count": len(imp_lines),
        "review_status": "needs_review",
    }

    result["imp_evidence"] = imp_evidence

    imp_review = {
        "employer_portal_and_fee": {
            "usual_employer_portal_submission": True,
            "usual_employer_compliance_fee_cad": 230,
            "offer_information": [
                "business_information",
                "foreign_worker_information",
                "job_details",
                "wage_and_benefits",
            ],
            "all_employers_required": False,
            "exemption_details_verified": False,
            "source_evidence_id": "CA_ESWP_IMP_EVD_01",
        },
        "special_hiring_categories": {
            "quebec_extension_exception_date": "2026-03-13",
            "french_speaking_outside_quebec": (
                "conditional_lmia_exemption"
            ),
            "overnight_camp_counsellor": (
                "conditional_lmia_exemption"
            ),
            "innovation_stream": {
                "ghp_participating_employer": True,
                "eligible_teer_categories": [0, 1, 2, 3],
                "wage_assessment_required": True,
            },
            "individual_exemption_eligibility_verified": False,
            "source_evidence_id": "CA_ESWP_IMP_EVD_02",
        },
        "exemptions": {
            "open_work_permit_holder": {
                "offer_submission_required": False,
                "employer_compliance_fee_required": False,
            },
            "other_employer_portal_exemptions": (
                "additional_review"
            ),
            "other_compliance_fee_exemptions": (
                "additional_review"
            ),
            "portal_and_fee_exemptions_independent": True,
            "source_evidence_id": "CA_ESWP_IMP_EVD_03",
        },
        "offer_number": {
            "issued_after_portal_submission": True,
            "number_digits_stated_in_source": 7,
            "prefix_required": None,
            "employer_provides_to_worker": True,
            "worker_applies_after_receipt": True,
            "source_evidence_id": "CA_ESWP_IMP_EVD_04",
        },
        "application_decisions": {
            "outside_canada_online": (
                "letter_of_introduction_then_border_assessment"
            ),
            "inside_canada_approved": (
                "work_permit_sent_by_mail"
            ),
            "entry_approval_automatic": False,
            "source_evidence_id": "CA_ESWP_IMP_EVD_05",
        },
        "port_of_entry_and_maintained_status": {
            "most_inside_canada_poe_applications_unavailable": True,
            "some_outside_canada_poe_applications_possible": True,
            "poe_requires_category_eligibility": True,
            "poe_requires_admissibility": True,
            "leaving_on_maintained_status_can_end_work_ability": True,
            "automatic_poe_application_eligibility": False,
            "source_evidence_id": "CA_ESWP_IMP_EVD_06",
        },
        "travel_medical_and_worker_rights": {
            "entry_documents_may_include": [
                "visitor_visa",
                "electronic_travel_authorization",
            ],
            "medical_exam_conditional": True,
            "valid_work_permit_and_conditions_required": True,
            "worker_rights_information_required": True,
            "source_evidence_id": "CA_ESWP_IMP_EVD_07",
        },
    }

    for group in imp_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["imp_employer_review"] = imp_review

    result["lmia_path_review"]["lmia_exempt"].update({
        "employer_portal_rules_verified": True,
        "employer_compliance_fee_verified": True,
        "general_employer_compliance_fee_cad": 230,
        "offer_number_digits": 7,
        "employer_portal_exemptions_need_review": True,
        "compliance_fee_exemptions_need_review": True,
        "individual_lmia_exemption_codes_need_review": True,
        "automatic_employer_preparation_approval": False,
        "imp_source_evidence_ids": [
            item["evidence_id"] for item in imp_evidence
        ],
        "detailed_rules_verified": False,
    })

    result["application_route_review"].update({
        "inside_canada_poe_restrictions_collected": True,
        "outside_canada_poe_eligibility_needs_review": True,
        "maintained_status_reentry_warning_collected": True,
        "automatic_route_eligibility_decision": False,
    })

    result["imp_employer_legal_review"] = {
        "general_employer_steps_collected": True,
        "individual_lmia_exemption_rules_approved": False,
        "employer_portal_exceptions_approved": False,
        "compliance_fee_exceptions_approved": False,
        "offer_number_prefix_not_confirmed": True,
        "automatic_work_authorization": False,
        "source_evidence_ids": [
            item["evidence_id"] for item in imp_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(imp_evidence) == 7
        and len(imp_review) == 7
        and len({
            item["evidence_id"] for item in imp_evidence
        }) == 7
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in imp_review.values()
        )
    ):
        raise ValueError("IMP employer integration failed")
    
    # IRCC employer compliance exemptions.
    # Portal exemption and compliance-fee exemption are distinct.
    # All categories are unapproved evidence for manual review.

    compliance_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_compliance_exemptions_ircc_en.txt"
    )

    if not compliance_path.is_file():
        raise FileNotFoundError(compliance_path)

    compliance_raw = compliance_path.read_bytes()
    compliance_text = compliance_raw.decode("utf-8-sig")
    compliance_lines = compliance_text.splitlines()
    compliance_hash = hashlib.sha256(
        compliance_raw
    ).hexdigest()

    required_compliance_lines = {
        11: "Employer compliance exemptions",
        12: "don’t need to use the Employer Portal",
        14: "Employers that don’t need to use the Employer Portal",
        15: "international missions or consular posts",
        16: "Foreign Missions and International Organizations Act",
        18: "a foreign government",
        19: "international bridge or tunnel",
        22: "Employer compliance fee exemptions",
        23: "LMIA",
        25: "No, I am exempt",
        27: "Proof of fee exemption",
        30: "Work permit extension for workers in Quebec",
        31: "March 13, 2026",
        35: "extending their employer-specific work permit",
        37: "Demande de sélection permanente",
        38: "do not have to pay",
        42: "Non-trade international agreements",
        43: "R204(a)",
        45: "R299(h)",
        48: "Reciprocal employment",
        49: "R205(b)",
        53: "Work related to a research program",
        54: "R205(c)(i)",
        61: "research chair positions",
        65: "Unremunerated charitable or religious work",
        66: "R205(d)",
        68: "R299(f)",
        69: "cannot receive payment",
        70: "not sufficient",
        77: "Date modified: 2026-04-23",
    }

    for number, marker in required_compliance_lines.items():
        if (
            len(compliance_lines) < number
            or marker not in compliance_lines[number - 1]
        ):
            raise ValueError(
                "Employer compliance source mismatch "
                f"at line {number}: {marker}"
            )

    compliance_ranges = [
        ("employer_portal_exemptions", 11, 20),
        ("fee_exemption_claim_and_proof", 22, 27),
        ("quebec_extension_fee_exemption", 29, 40),
        ("international_and_reciprocal_agreements", 42, 52),
        ("research_program_fee_exemptions", 53, 64),
        ("unremunerated_charitable_religious_work", 65, 70),
    ]

    compliance_evidence = []

    for index, (topic, first, last) in enumerate(
        compliance_ranges, 1
    ):
        quote = "\n".join(
            compliance_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Compliance evidence too short: {topic}"
            )

        compliance_evidence.append({
            "evidence_id": f"CA_ESWP_COMP_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                compliance_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": compliance_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["compliance_exemptions_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/hire-temporary-foreign/"
            "find-need-labour-market-impact-assessment/"
            "employer-compliance-exemptions.html"
        ),
        "source_language": "en",
        "source_file": (
            compliance_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": compliance_hash,
        "source_last_modified": "2026-04-23",
        "char_count": len(compliance_text),
        "line_count": len(compliance_lines),
        "review_status": "needs_review",
    }

    result["compliance_exemptions_evidence"] = (
        compliance_evidence
    )

    compliance_review = {
        "employer_portal_exemptions": {
            "exemption_categories": [
                "international_missions_or_consular_posts",
                "recognized_international_organizations",
                "foreign_governments",
                "international_bridge_or_tunnel_operators",
            ],
            "individual_entity_qualification_verified": False,
            "automatic_portal_exemption": False,
            "source_evidence_id": "CA_ESWP_COMP_EVD_01",
        },
        "fee_exemption_claim_and_proof": {
            "portal_fee_exemption_option": (
                "No, I am exempt from paying fees "
                "for this Offer of Employment."
            ),
            "proof_of_exemption_required": True,
            "proof_may_include_explanation_letter": True,
            "portal_exemption_and_fee_exemption_separate": True,
            "automatic_fee_exemption": False,
            "source_evidence_id": "CA_ESWP_COMP_EVD_02",
        },
        "quebec_extension": {
            "special_policy_date": "2026-03-13",
            "work_in_quebec": True,
            "current_employer_relationship": (
                "conditional_requirement"
            ),
            "employer_specific_extension": (
                "conditional_requirement"
            ),
            "permanent_selection_application": (
                "conditional_requirement"
            ),
            "all_policy_conditions_verified": False,
            "automatic_fee_exemption": False,
            "source_evidence_id": "CA_ESWP_COMP_EVD_03",
        },
        "international_and_reciprocal_agreements": {
            "non_trade_lmia_reference": "R204(a)",
            "reciprocal_employment_lmia_reference": "R205(b)",
            "fee_exemption_references": [
                "R299(h)",
                "R299(g)",
                "R299(k)",
            ],
            "examples": [
                "Fulbright_Program_Canada_US",
                "Roosevelt_Campobello_International_Park",
                "US_government_personnel",
                "cultural_agreements",
                "Canada_China_cultural_exchange",
            ],
            "individual_agreement_eligibility_verified": False,
            "automatic_fee_exemption": False,
            "source_evidence_id": "CA_ESWP_COMP_EVD_04",
        },
        "research_programs": {
            "lmia_reference": "R205(c)(i)",
            "fee_exemption_reference": "R299(e)",
            "examples": [
                "Atomic_Energy_of_Canada_sponsored_researchers",
                "National_Research_Council_sponsored_scholars",
                "Natural_Resources_Canada_sponsored_scholars",
                "NSERC_sponsored_scholars",
                "Canada_Research_Chair",
                "Canada_Excellence_Research_Chair",
            ],
            "sponsorship_requirements_need_review": True,
            "automatic_fee_exemption": False,
            "source_evidence_id": "CA_ESWP_COMP_EVD_05",
        },
        "charitable_and_religious_work": {
            "lmia_reference": "R205(d)",
            "fee_reference": "R299(f)",
            "unremunerated_work_required": True,
            "living_expense_stipend_may_be_allowed": True,
            "stipend_below_prevailing_minimum_wage": True,
            "non_monetary_benefits_examples": [
                "housing",
                "health_care",
            ],
            "proof_must_describe_remuneration": True,
            "organization_type_alone_sufficient": False,
            "automatic_fee_exemption": False,
            "source_evidence_id": "CA_ESWP_COMP_EVD_06",
        },
    }

    for group in compliance_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["compliance_exemptions_review"] = (
        compliance_review
    )

    # Add details to previously created IMP review groups.
    # Never treat evidence collection as automatic approval.

    result["imp_employer_review"]["exemptions"].update({
        "portal_exemption_categories_collected": True,
        "fee_exemption_categories_collected": True,
        "individual_portal_exemption_approved": False,
        "individual_fee_exemption_approved": False,
        "compliance_source_evidence_ids": [
            item["evidence_id"]
            for item in compliance_evidence
        ],
    })

    result["lmia_path_review"]["lmia_exempt"].update({
        "employer_portal_exemptions_need_review": True,
        "compliance_fee_exemptions_need_review": True,
        "individual_fee_exemption_approved": False,
        "individual_portal_exemption_approved": False,
        "automatic_employer_preparation_approval": False,
    })

    result["compliance_exemptions_legal_review"] = {
        "portal_exemption_categories_collected": True,
        "fee_exemption_categories_collected": True,
        "portal_and_fee_exemptions_independent": True,
        "individual_lmia_exemption_approved": False,
        "individual_portal_exemption_approved": False,
        "individual_fee_exemption_approved": False,
        "automatic_exemption_decision": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in compliance_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(compliance_evidence) == 6
        and len(compliance_review) == 6
        and len({
            item["evidence_id"]
            for item in compliance_evidence
        }) == 6
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in compliance_review.values()
        )
    ):
        raise ValueError(
            "Employer compliance exemptions integration failed"
        )
    
    # IRCC work permit eligibility: applications from outside Canada.
    # Scope is limited to the outside-Canada application route.
    # This evidence must not authorize an eligibility decision.

    outside_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_general_eligibility_outside_ircc_en.txt"
    )

    if not outside_path.is_file():
        raise FileNotFoundError(outside_path)

    outside_raw = outside_path.read_bytes()
    outside_text = outside_raw.decode("utf-8-sig")
    outside_lines = outside_text.splitlines()
    outside_hash = hashlib.sha256(outside_raw).hexdigest()

    required_outside_lines = {
        11: "Work permit: Applying from outside Canada",
        18: "Check if you can apply",
        23: "general requirements",
        29: "Requirements to apply from outside Canada",
        32: "enough money",
        34: "family size",
        35: "community you plan to settle in",
        36: "work permit program",
        38: "2023 data",
        39: "required documents",
        41: "other documents",
        42: "leave Canada",
        43: "Reasons your application may be refused",
        44: "Additional requirements for your situation",
        47: "additional requirements",
        48: "special instructions",
        50: "Requirements based on types of work permits",
        53: "employer-specific (closed) work permits",
        55: "can’t choose",
        58: "A job offer is required",
        63: "Including family on your application",
        64: "spouse, common-law partner",
        68: "visa or eTA",
        69: "study permit",
        70: "open work permit",
        77: "Date modified: 2026-05-25",
    }

    for number, marker in required_outside_lines.items():
        if (
            len(outside_lines) < number
            or marker.casefold()
            not in outside_lines[number - 1].casefold()
        ):
            raise ValueError(
                "Outside-Canada eligibility source mismatch "
                f"at line {number}: {marker}"
            )

    outside_ranges = [
        (
            "general_eligibility_scope",
            18,
            28,
        ),
        (
            "financial_documents_and_departure",
            29,
            43,
        ),
        (
            "additional_program_requirements",
            44,
            49,
        ),
        (
            "work_permit_type_and_job_offer",
            50,
            61,
        ),
        (
            "family_members_and_separate_permissions",
            63,
            70,
        ),
    ]

    outside_evidence = []

    for index, (topic, first, last) in enumerate(
        outside_ranges, 1
    ):
        quote = "\n".join(
            outside_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Outside-Canada evidence too short: {topic}"
            )

        outside_evidence.append({
            "evidence_id": f"CA_ESWP_OUT_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                outside_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": outside_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["outside_canada_eligibility_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/permit-outside/eligibility.html"
        ),
        "source_language": "en",
        "source_file": (
            outside_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": outside_hash,
        "source_last_modified": "2026-05-25",
        "char_count": len(outside_text),
        "line_count": len(outside_lines),
        "review_status": "needs_review",
    }

    result["outside_canada_eligibility_evidence"] = (
        outside_evidence
    )

    outside_review = {
        "application_scope": {
            "application_location": "outside_canada",
            "general_requirements_apply": True,
            "permit_type_requirements_also_apply": True,
            "inside_canada_rules_verified": False,
            "port_of_entry_rules_fully_verified": False,
            "source_evidence_id": "CA_ESWP_OUT_EVD_01",
        },
        "financial_documents_and_departure": {
            "funds_for_applicant_and_family": True,
            "funds_for_return_home": True,
            "funds_depend_on": [
                "family_size",
                "settlement_community",
                "work_permit_program",
            ],
            "low_income_cutoffs_reference_year": 2023,
            "fixed_2026_minimum_funds_verified": False,
            "required_documents": True,
            "additional_ircc_documents_may_be_requested": True,
            "intention_to_leave_before_expiry": True,
            "refusal_reasons_listed_in_source": False,
            "source_evidence_id": "CA_ESWP_OUT_EVD_02",
        },
        "program_specific_requirements": {
            "additional_requirements_may_apply": True,
            "special_application_instructions_may_apply": True,
            "specific_requirements_fully_verified": False,
            "source_evidence_id": "CA_ESWP_OUT_EVD_03",
        },
        "work_permit_type": {
            "work_permit_types": [
                "employer_specific",
                "open",
            ],
            "employer_specific_job_offer_required": True,
            "permit_type_freely_chosen_by_applicant": False,
            "individual_job_offer_eligibility_verified": False,
            "source_evidence_id": "CA_ESWP_OUT_EVD_04",
        },
        "family_members": {
            "family_member_categories": [
                "spouse",
                "common_law_partner",
                "dependent_child",
            ],
            "separate_permissions_to_review": [
                "entry_visa_or_eta",
                "study_permit",
                "open_work_permit",
            ],
            "automatic_family_permission": False,
            "source_evidence_id": "CA_ESWP_OUT_EVD_05",
        },
    }

    for group in outside_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["outside_canada_eligibility_review"] = (
        outside_review
    )

    result["application_route_review"].update({
        "outside_canada_general_requirements_collected": True,
        "outside_canada_source_evidence_ids": [
            item["evidence_id"]
            for item in outside_evidence
        ],
        "outside_canada_individual_eligibility_approved": False,
        "automatic_route_eligibility_decision": False,
    })

    result["outside_canada_legal_review"] = {
        "general_outside_canada_requirements_collected": True,
        "criminal_history_details_verified_here": False,
        "ineligible_employer_details_verified_here": False,
        "2026_fixed_funds_threshold_approved": False,
        "inside_canada_rules_approved": False,
        "port_of_entry_rules_approved": False,
        "automatic_eligibility_decision": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in outside_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(outside_evidence) == 5
        and len(outside_review) == 5
        and len({
            item["evidence_id"]
            for item in outside_evidence
        }) == 5
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in outside_review.values()
        )
    ):
        raise ValueError(
            "Outside-Canada eligibility integration failed"
        )
    
    # IRCC outside-Canada work permit supporting documents.
    # Evidence is grounded in the saved plain-text source.
    # All document requirements remain unapproved for decisions.

    docs_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_outside_documents_ircc_en.txt"
    )

    if not docs_path.is_file():
        raise FileNotFoundError(docs_path)

    docs_raw = docs_path.read_bytes()
    docs_text = docs_raw.decode("utf-8-sig")
    docs_lines = docs_text.splitlines()
    docs_hash = hashlib.sha256(docs_raw).hexdigest()

    required_docs_lines = {
        11: "Work permit: Applying from outside Canada",
        18: "Forms and documents",
        21: "inside Canada or at a port of entry",
        30: "Forms and documents that all applicants",
        33: "IMM 1295",
        35: "valid (not expired) passport",
        36: "visa photo specifications",
        37: "personalized document checklist",
        41: "Documents required by your local visa office",
        42: "visa office requirements",
        46: "Supporting documents you might need",
        49: "medical exam",
        51: "certified translations",
        52: "IMM 5707",
        53: "IMM 5409",
        55: "IMM 5476",
        56: "IMM 5475",
        57: "present immigration status",
        58: "Documents for employer-specific work permits",
        63: "current employer",
        64: "past employers",
        65: "past work experience",
        66: "license or certification",
        67: "Not applicable",
        68: "résumé",
        71: "LMIA-required work permits",
        74: "positive LMIA and LMIA file number",
        75: "employment contract",
        76: "job offer letter",
        77: "Quebec Acceptance Certificate",
        80: "LMIA-exempt work permits",
        83: "employment contract",
        84: "offer of employment number",
        87: "Not applicable",
        95: "Date modified: 2026-07-17",
    }

    for number, marker in required_docs_lines.items():
        if (
            len(docs_lines) < number
            or marker.casefold()
            not in docs_lines[number - 1].casefold()
        ):
            raise ValueError(
                "Outside documents source mismatch "
                f"at line {number}: {marker}"
            )

    docs_ranges = [
        ("common_application_documents", 25, 39),
        ("local_visa_office_documents", 41, 45),
        ("conditional_supporting_documents", 46, 57),
        ("employer_specific_qualification_documents", 58, 69),
        ("lmia_required_documents", 71, 79),
        ("lmia_exempt_documents", 80, 85),
    ]

    docs_evidence = []

    for index, (topic, first, last) in enumerate(
        docs_ranges, 1
    ):
        quote = "\n".join(
            docs_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Outside documents evidence too short: {topic}"
            )

        docs_evidence.append({
            "evidence_id": f"CA_ESWP_DOC_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                docs_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": docs_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["outside_documents_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/permit-outside/forms-documents.html"
        ),
        "source_language": "en",
        "source_file": (
            docs_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": docs_hash,
        "source_last_modified": "2026-07-17",
        "char_count": len(docs_text),
        "line_count": len(docs_lines),
        "review_status": "needs_review",
    }

    result["outside_documents_evidence"] = docs_evidence

    docs_review = {
        "common_documents": {
            "application_location": "outside_canada",
            "forms": ["IMM 1295"],
            "valid_passport_or_travel_document_copy": True,
            "visa_specification_photo_count": 1,
            "online_personalized_checklist_required": True,
            "source_evidence_id": "CA_ESWP_DOC_EVD_01",
        },
        "local_visa_office": {
            "requirements_depend_on_application_country": True,
            "additional_documents_always_required": False,
            "individual_visa_office_requirements_verified": False,
            "source_evidence_id": "CA_ESWP_DOC_EVD_02",
        },
        "conditional_supporting_documents": {
            "possible_documents": [
                "medical_exam_proof",
                "marriage_certificate",
                "certified_translations",
                "IMM_5707",
                "IMM_5409",
                "employment_documents",
                "IMM_5476_if_represented",
                "IMM_5475_if_information_release_authorized",
                "immigration_status_in_application_country",
            ],
            "all_documents_unconditionally_required": False,
            "source_evidence_id": "CA_ESWP_DOC_EVD_03",
        },
        "employer_specific_qualifications": {
            "document_categories": [
                "current_employer_letter",
                "previous_employer_reference_letter",
                "past_work_experience_proof",
                "job_qualification_proof",
                "resume",
            ],
            "regulated_job_license_if_applicable": True,
            "not_applicable_upload_for_unneeded_license": True,
            "individual_applicant_documents_verified": False,
            "source_evidence_id": "CA_ESWP_DOC_EVD_04",
        },
        "lmia_required": {
            "positive_lmia_copy": True,
            "lmia_file_number": True,
            "employment_contract": True,
            "job_offer_letter": True,
            "quebec_caq_source_condition": (
                "paid_job_in_quebec_more_than_30_days"
            ),
            "quebec_caq_exceptions_verified": False,
            "source_evidence_id": "CA_ESWP_DOC_EVD_05",
        },
        "lmia_exempt": {
            "employment_contract": True,
            "offer_of_employment_number": (
                "normally_required_subject_to_exceptions"
            ),
            "number_prefix_confirmed_in_saved_txt": False,
            "employer_portal_exceptions_need_review": True,
            "individual_lmia_exemption_verified": False,
            "source_evidence_id": "CA_ESWP_DOC_EVD_06",
        },
    }

    for group in docs_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["outside_documents_review"] = docs_review

    result["outside_canada_eligibility_review"][
        "financial_documents_and_departure"
    ].update({
        "general_document_categories_collected": True,
        "individual_document_checklist_verified": False,
    })

    result["lmia_path_review"]["lmia_required"].update({
        "worker_document_source_collected": True,
        "job_offer_letter_required": True,
        "employment_contract_required": True,
        "quebec_caq_conditions_need_review": True,
    })

    result["lmia_path_review"]["lmia_exempt"].update({
        "worker_document_source_collected": True,
        "employment_contract_required": True,
        "offer_number_required_subject_to_exceptions": True,
        "offer_number_prefix_from_saved_txt_verified": False,
        "automatic_employer_preparation_approval": False,
    })

    result["outside_documents_legal_review"] = {
        "outside_canada_document_categories_collected": True,
        "individual_checklist_approved": False,
        "local_visa_office_documents_approved": False,
        "quebec_caq_exceptions_approved": False,
        "offer_number_format_from_txt_verified": False,
        "automatic_document_sufficiency_decision": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in docs_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(docs_evidence) == 6
        and len(docs_review) == 6
        and len({
            item["evidence_id"]
            for item in docs_evidence
        }) == 6
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in docs_review.values()
        )
    ):
        raise ValueError(
            "Outside documents integration failed"
        )
    
    # IRCC outside-Canada work permit application process.
    # Fee amounts, NOC priority guidance and biometrics
    # are evidence for review, not approved decisions.

    application_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_outside_application_ircc_en.txt"
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
        11: "Work permit: Applying from outside Canada",
        18: "Submit your application",
        21: "inside Canada or at a port of entry",
        32: "Step 1: Check if you need special instructions",
        39: "Priority processing for work permit applicants",
        43: "faster processing",
        45: "full-time and non-seasonal",
        46: "NOC 31100",
        47: "NOC 31101",
        48: "NOC 31102",
        49: "support letter",
        61: "National Occupational Classification",
        66: "only the number",
        67: "NOC 2021",
        70: "NOC 2021 codes",
        72: "Agriculture and agri-food occupations",
        86: "Health-care occupations",
        107: "NOC 44100",
        108: "NOC 44101",
        127: "Step 2: Sign in to your account",
        128: "IRCC secure account",
        132: "Step 3: Upload forms and documents",
        133: "personalized document checklist",
        139: "Step 4: Pay the fees",
        144: "exempt from paying",
        148: "$155",
        149: "$100",
        150: "$85",
        151: "$170",
        152: "Step 5: Submit a complete application",
        153: "missing documents",
        155: "November 27, 2026",
        161: "Step 6: Give your biometrics",
        162: "biometrics instruction letter",
        166: "biometrics again",
        170: "valid for longer than your biometrics",
        179: "Date modified: 2026-08-28",
    }

    if len(application_lines) != 216:
        raise ValueError(
            "Outside application source line count mismatch"
        )

    for number, marker in required_application_lines.items():
        if (
            marker.casefold()
            not in application_lines[number - 1].casefold()
        ):
            raise ValueError(
                "Outside application source mismatch "
                f"at line {number}: {marker}"
            )

    application_ranges = [
        ("application_steps_and_special_instructions", 25, 37),
        ("priority_processing_and_noc", 39, 118),
        ("secure_account_and_document_upload", 127, 137),
        ("application_and_biometrics_fees", 139, 151),
        ("complete_application_and_temporary_notice", 152, 159),
        ("biometrics_after_application", 161, 172),
        ("source_date_and_navigation", 173, 179),
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
                f"Outside application evidence too short: {topic}"
            )

        application_evidence.append({
            "evidence_id": f"CA_ESWP_APP_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                application_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": application_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["outside_application_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/permit-outside/apply.html"
        ),
        "source_language": "en",
        "source_file": (
            application_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": application_hash,
        "source_last_modified": "2026-08-28",
        "char_count": len(application_text),
        "line_count": len(application_lines),
        "review_status": "needs_review",
    }

    result["outside_application_evidence"] = (
        application_evidence
    )

    # Preserve the official NOC codes without inferring
    # automatic priority-processing eligibility.
    noc_source_lines = application_lines[71:108]
    noc_codes = sorted(set(
        re.findall(
            r"\bNOC\s+(\d{5})\b",
            "\n".join(noc_source_lines),
        )
    ))

    special_healthcare_nocs = [
        "31100",
        "31101",
        "31102",
    ]

    application_review = {
        "application_steps": {
            "application_location": "outside_canada",
            "special_instructions_check_required": True,
            "questionnaire_guidance_may_apply": True,
            "application_form_guidance_may_apply": True,
            "source_evidence_id": "CA_ESWP_APP_EVD_01",
        },
        "priority_processing": {
            "special_healthcare_noc_codes": (
                special_healthcare_nocs
            ),
            "healthcare_priority_conditions": [
                "full_time_non_seasonal_job_offer",
                "provincial_or_territorial_support_letter",
                "provincial_nominee_context",
                "general_work_permit_eligibility",
            ],
            "other_priority_noc_codes_from_source": noc_codes,
            "noc_version": "NOC_2021",
            "noc_2021_application_date_from": "2022-11-16",
            "source_noc_codes_manually_validated": False,
            "automatic_priority_processing_decision": False,
            "priority_processing_guaranteed": False,
            "source_evidence_id": "CA_ESWP_APP_EVD_02",
        },
        "account_and_upload": {
            "ircc_secure_account": True,
            "personalized_document_checklist": True,
            "electronic_document_copies": True,
            "online_accommodation_exceptions_need_review": True,
            "source_evidence_id": "CA_ESWP_APP_EVD_03",
        },
        "application_fees": {
            "currency": "CAD",
            "work_permit_processing_fee": 155,
            "open_work_permit_additional_fee": 100,
            "biometrics_individual_fee": 85,
            "biometrics_family_maximum_fee": 170,
            "open_work_permit_fee_applies_to_eswp": False,
            "imp_employer_compliance_fee_separate": True,
            "fee_exemptions_need_review": True,
            "biometrics_applicability_needs_review": True,
            "source_evidence_id": "CA_ESWP_APP_EVD_04",
        },
        "complete_application": {
            "complete_application_required": True,
            "missing_documents_may_cause_refusal": True,
            "ebola_temporary_measure_date": "2026-11-27",
            "ebola_notice_not_general_eligibility_rule": True,
            "source_evidence_id": "CA_ESWP_APP_EVD_05",
        },
        "biometrics_after_application": {
            "biometrics_instruction_letter_if_applicable": True,
            "appointment_after_instruction_letter": True,
            "repeat_biometrics_may_be_required": True,
            "repeat_reasons": [
                "biometrics_expiring_soon",
                "previous_permanent_residence_refusal",
                "only_partial_biometrics_collected",
            ],
            "permit_validity_may_depend_on_biometrics": True,
            "automatic_biometrics_exemption_decision": False,
            "source_evidence_id": "CA_ESWP_APP_EVD_06",
        },
        "source_metadata": {
            "source_last_modified": "2026-08-28",
            "application_process_scope": "outside_canada",
            "inside_canada_process_approved": False,
            "port_of_entry_process_approved": False,
            "source_evidence_id": "CA_ESWP_APP_EVD_07",
        },
    }

    for group in application_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["outside_application_review"] = (
        application_review
    )

    result["application_route_review"].update({
        "outside_canada_submission_process_collected": True,
        "outside_canada_fee_schedule_collected": True,
        "biometrics_process_collected": True,
        "priority_processing_conditions_collected": True,
        "automatic_route_eligibility_decision": False,
        "outside_application_source_evidence_ids": [
            item["evidence_id"]
            for item in application_evidence
        ],
    })

    result["outside_application_legal_review"] = {
        "general_outside_process_collected": True,
        "individual_fee_exemptions_approved": False,
        "biometrics_exemptions_approved": False,
        "priority_processing_eligibility_approved": False,
        "individual_document_sufficiency_approved": False,
        "automatic_work_permit_approval": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in application_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(application_evidence) == 7
        and len(application_review) == 7
        and len(noc_codes) > 20
        and len({
            item["evidence_id"]
            for item in application_evidence
        }) == 7
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in application_review.values()
        )
    ):
        raise ValueError(
            "Outside application integration failed"
        )
    
    # IRCC outside-Canada work permit decision evidence.
    # Application approval, LOI issuance, work permit issuance
    # and entry authorization are separate decisions.
    # Refusal grounds are review indicators, not automatic rules.

    decision_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_outside_decision_ircc_en.txt"
    )

    if not decision_path.is_file():
        raise FileNotFoundError(decision_path)

    decision_raw = decision_path.read_bytes()
    decision_text = decision_raw.decode("utf-8-sig")
    decision_lines = decision_text.splitlines()
    decision_hash = hashlib.sha256(
        decision_raw
    ).hexdigest()

    required_decision_lines = {
        11: "Work permit: Applying from outside Canada",
        18: "Wait for a decision",
        23: "how we process your application",
        29: "November 27, 2026",
        35: "Check the status of your application",
        38: "How we process your application",
        39: "including biometrics",
        43: "employers who failed to comply",
        44: "qualify for a work permit",
        47: "interview",
        48: "medical exam",
        51: "more information or documents",
        53: "If we approve your application",
        56: "letter of introduction",
        57: "application is approved",
        58: "present it at the POE",
        59: "not your work permit",
        60: "electronic travel authorization",
        62: "final decision",
        64: "If we refuse your application",
        67: "eligibility requirements",
        68: "weak ties to your home country",
        69: "inadmissible to Canada",
        70: "incomplete",
        71: "insufficient funds",
        72: "job offer was not genuine",
        73: "right skills or education",
        74: "no longer offered",
        75: "untruthfully",
        76: "apply again",
        84: "Date modified: 2026-10-19",
    }

    if len(decision_lines) != 121:
        raise ValueError(
            "Outside decision source line count mismatch"
        )

    for number, marker in required_decision_lines.items():
        if (
            marker.casefold()
            not in decision_lines[number - 1].casefold()
        ):
            raise ValueError(
                "Outside decision source mismatch "
                f"at line {number}: {marker}"
            )

    decision_ranges = [
        ("application_status_and_temporary_notice", 25, 36),
        ("application_processing_and_employer_checks", 38, 51),
        ("approval_loi_and_border_decision", 53, 62),
        ("application_refusal_reasons", 64, 75),
        ("reapplication_after_refusal", 75, 76),
    ]

    decision_evidence = []

    for index, (topic, first, last) in enumerate(
        decision_ranges, 1
    ):
        quote = "\n".join(
            decision_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Outside decision evidence too short: {topic}"
            )

        decision_evidence.append({
            "evidence_id": f"CA_ESWP_DEC_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                decision_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": decision_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["outside_decision_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/permit-outside/after-apply.html"
        ),
        "source_language": "en",
        "source_file": (
            decision_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": decision_hash,
        "source_last_modified": "2026-10-19",
        "char_count": len(decision_text),
        "line_count": len(decision_lines),
        "review_status": "needs_review",
    }

    result["outside_decision_evidence"] = decision_evidence

    refusal_reasons = [
        {
            "reason": "permit_type_eligibility",
            "source_line": 67,
        },
        {
            "reason": "temporary_resident_intent",
            "source_line": 68,
        },
        {
            "reason": "admissibility",
            "source_line": 69,
        },
        {
            "reason": "application_completeness",
            "source_line": 70,
        },
        {
            "reason": "financial_sufficiency",
            "source_line": 71,
        },
        {
            "reason": "job_offer_genuineness",
            "source_line": 72,
        },
        {
            "reason": "job_qualification_evidence",
            "source_line": 73,
        },
        {
            "reason": "program_availability",
            "source_line": 74,
        },
        {
            "reason": "truthfulness_and_misrepresentation",
            "source_line": 75,
        },
    ]

    decision_review = {
        "application_status_and_temporary_notice": {
            "application_status_check_available": True,
            "ebola_temporary_measure_date": "2026-11-27",
            "ebola_notice_not_general_eligibility_rule": True,
            "source_evidence_id": "CA_ESWP_DEC_EVD_01",
        },
        "application_processing": {
            "document_completeness_checked": True,
            "biometrics_completeness_checked": True,
            "incomplete_application_may_be_refused": True,
            "employer_non_compliance_list_checked": True,
            "individual_work_permit_eligibility_checked": True,
            "additional_interview_possible": True,
            "medical_exam_conditional_on": [
                "type_of_work",
                "country_of_residence",
            ],
            "additional_documents_may_be_requested": True,
            "automatic_processing_approval": False,
            "source_evidence_id": "CA_ESWP_DEC_EVD_02",
        },
        "approval_and_entry": {
            "application_approved": "not_verified",
            "letter_of_introduction_issued": "not_verified",
            "work_permit_issued": "not_verified",
            "entry_authorized": "not_verified",
            "loi_is_work_permit": False,
            "visitor_visa_or_eta_issued_if_applicable": True,
            "border_officer_decides_permit_and_entry": True,
            "application_approval_guarantees_entry": False,
            "source_evidence_id": "CA_ESWP_DEC_EVD_03",
        },
        "refusal_reasons": {
            "official_refusal_reasons": refusal_reasons,
            "reasons_are_non_exhaustive_examples": True,
            "automatic_refusal_decision": False,
            "source_evidence_id": "CA_ESWP_DEC_EVD_04",
        },
        "reapplication": {
            "decision_letter_may_restrict_reapplication": True,
            "additional_information_recommended": True,
            "reapplication_automatically_allowed": False,
            "reapplication_approval_guaranteed": False,
            "source_evidence_id": "CA_ESWP_DEC_EVD_05",
        },
    }

    for group in decision_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["outside_decision_review"] = decision_review

    # A stream being discontinued is not the same as an
    # individual applicant failing its eligibility conditions.
    result["application_availability"].update({
        "status": "not_verified",
        "stream_availability_requires_separate_check": True,
        "source_evidence_id": "CA_ESWP_DEC_EVD_04",
    })

    result["application_route_review"].update({
        "outside_canada_decision_process_collected": True,
        "loi_and_work_permit_issuance_separated": True,
        "border_entry_decision_separate": True,
        "automatic_route_eligibility_decision": False,
        "outside_decision_source_evidence_ids": [
            item["evidence_id"]
            for item in decision_evidence
        ],
    })

    result["outside_decision_legal_review"] = {
        "general_decision_process_collected": True,
        "refusal_reasons_collected": True,
        "application_approval_not_work_authorization": True,
        "loi_not_work_permit": True,
        "individual_refusal_reason_verified": False,
        "individual_reapplication_permission_verified": False,
        "border_entry_permission_approved": False,
        "automatic_decision_or_work_authorization": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in decision_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(decision_evidence) == 5
        and len(decision_review) == 5
        and len(refusal_reasons) == 9
        and len({
            item["evidence_id"]
            for item in decision_evidence
        }) == 5
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in decision_review.values()
        )
        and decision_review["approval_and_entry"][
            "loi_is_work_permit"
        ] is False
        and result["application_availability"][
            "status"
        ] == "not_verified"
    ):
        raise ValueError(
            "Outside decision integration failed"
        )
    
    # IRCC outside-Canada arrival and permit issuance evidence.
    # Application approval, entry and actual permit issuance
    # are separate. All individual statuses stay unverified.

    arrival_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_outside_arrival_ircc_en.txt"
    )

    if not arrival_path.is_file():
        raise FileNotFoundError(arrival_path)

    arrival_raw = arrival_path.read_bytes()
    arrival_text = arrival_raw.decode("utf-8-sig")
    arrival_lines = arrival_text.splitlines()
    arrival_hash = hashlib.sha256(arrival_raw).hexdigest()

    required_arrival_lines = {
        11: "Work permit: Applying from outside Canada",
        18: "Arrive in Canada",
        26: "Documents you need at the border",
        29: "November 27, 2026",
        35: "Documents you need at the border",
        36: "Required documents",
        37: "must bring these documents",
        39: "your passport",
        40: "valid for longer",
        41: "visitor visa",
        42: "immigration medical exam",
        43: "valid the day you enter Canada",
        44: "letter of introduction",
        45: "work permit application was approved",
        50: "electronic version",
        52: "Supporting documents",
        55: "work experience and education",
        56: "positive labour market impact assessment",
        57: "Quebec Acceptance Certificate",
        58: "offer of employment number",
        59: "Identity check at the border",
        64: "fingerprints",
        68: "secondary inspection",
        69: "Meet the border officer",
        70: "Canada Border Services Agency",
        76: "entry requirements",
        77: "leave Canada",
        78: "false or incomplete information",
        80: "final decision",
        82: "print your work permit",
        83: "actual work permit",
        85: "before you leave",
        90: "Date modified: 2026-08-28",
    }

    if len(arrival_lines) != 127:
        raise ValueError(
            "Outside arrival source line count mismatch"
        )

    for number, marker in required_arrival_lines.items():
        if (
            marker.casefold()
            not in arrival_lines[number - 1].casefold()
        ):
            raise ValueError(
                "Outside arrival source mismatch "
                f"at line {number}: {marker}"
            )

    arrival_ranges = [
        ("required_border_documents", 35, 51),
        ("supporting_border_documents", 52, 58),
        ("border_identity_checks", 59, 68),
        ("cbsa_admissibility_and_final_decision", 69, 80),
        ("actual_permit_issuance_and_verification", 82, 90),
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
                f"Outside arrival evidence too short: {topic}"
            )

        arrival_evidence.append({
            "evidence_id": f"CA_ESWP_ARR_EVD_{index:02d}",
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

    result["outside_arrival_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/permit-outside/arrival.html"
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

    result["outside_arrival_evidence"] = arrival_evidence

    arrival_review = {
        "required_border_documents": {
            "passport_required": True,
            "passport_valid_for_planned_stay": True,
            "visitor_visa_if_required": True,
            "valid_ime_if_required": True,
            "ime_valid_on_entry_date": True,
            "application_approval_proof_required": True,
            "loi_accepted_as_approval_proof": True,
            "printed_or_electronic_loi_accepted": True,
            "individual_documents_verified": False,
            "source_evidence_id": "CA_ESWP_ARR_EVD_01",
        },
        "supporting_border_documents": {
            "job_qualification_proof": True,
            "positive_lmia_copy_if_required": True,
            "quebec_caq_attestation_condition": (
                "if_working_in_quebec"
            ),
            "offer_number_for_lmia_exempt_portal_route": True,
            "all_supporting_documents_unconditional": False,
            "quebec_caq_exceptions_fully_verified": False,
            "source_evidence_id": "CA_ESWP_ARR_EVD_02",
        },
        "border_identity_check": {
            "identity_check_required": True,
            "some_airports_use_primary_kiosk": True,
            "fingerprints_compared_with_application": True,
            "secondary_inspection_may_check_fingerprints": True,
            "individual_identity_verified": False,
            "source_evidence_id": "CA_ESWP_ARR_EVD_03",
        },
        "cbsa_border_decision": {
            "border_authority": (
                "Canada Border Services Agency"
            ),
            "entry_requirements_checked": True,
            "departure_at_end_of_approved_stay_checked": True,
            "accurate_and_complete_information_required": True,
            "false_or_incomplete_information_risk": [
                "refusal_of_entry",
                "removal_from_canada",
            ],
            "border_officer_final_permit_decision": True,
            "border_officer_final_entry_decision": True,
            "automatic_entry_approval": False,
            "source_evidence_id": "CA_ESWP_ARR_EVD_04",
        },
        "actual_permit_issuance": {
            "work_permit_printed_at_border_if_approved": True,
            "permit_errors_should_be_raised_before_leaving": True,
            "loi_is_actual_work_permit": False,
            "individual_status": {
                "letter_of_introduction_issued": "not_verified",
                "entry_document_valid": "not_verified",
                "identity_check_completed": "not_verified",
                "border_admissibility_verified": "not_verified",
                "work_permit_issued": "not_verified",
                "work_permit_conditions_verified": "not_verified",
            },
            "automatic_work_authorization": False,
            "source_evidence_id": "CA_ESWP_ARR_EVD_05",
        },
    }

    for group in arrival_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["outside_arrival_review"] = arrival_review

    result["application_route_review"].update({
        "outside_canada_arrival_process_collected": True,
        "border_entry_and_permit_issuance_separate": True,
        "individual_entry_permission_approved": False,
        "individual_work_permit_issued": False,
        "automatic_route_eligibility_decision": False,
        "outside_arrival_source_evidence_ids": [
            item["evidence_id"]
            for item in arrival_evidence
        ],
    })

    result["outside_decision_review"][
        "approval_and_entry"
    ].update({
        "arrival_source_collected": True,
        "border_admissibility_individual_status": "not_verified",
        "actual_permit_issuance_individual_status": "not_verified",
        "application_approval_guarantees_entry": False,
    })

    result["outside_arrival_legal_review"] = {
        "official_arrival_process_collected": True,
        "individual_document_sufficiency_verified": False,
        "individual_border_admissibility_approved": False,
        "individual_permit_issuance_verified": False,
        "quebec_special_requirements_approved": False,
        "loi_not_actual_work_permit": True,
        "automatic_entry_or_work_authorization": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in arrival_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(arrival_evidence) == 5
        and len(arrival_review) == 5
        and len({
            item["evidence_id"]
            for item in arrival_evidence
        }) == 5
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in arrival_review.values()
        )
        and all(
            status == "not_verified"
            for status in arrival_review[
                "actual_permit_issuance"
            ]["individual_status"].values()
        )
    ):
        raise ValueError(
            "Outside arrival integration failed"
        )
    
    # IRCC after-work-permit-issuance evidence.
    # Work conditions, validity, SIN, health coverage,
    # and permit changes are stored for review only.

    after_permit_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_after_permit_ircc_en.txt"
    )

    if not after_permit_path.is_file():
        raise FileNotFoundError(after_permit_path)

    after_permit_raw = after_permit_path.read_bytes()
    after_permit_text = after_permit_raw.decode("utf-8-sig")
    after_permit_lines = after_permit_text.splitlines()
    after_permit_hash = hashlib.sha256(
        after_permit_raw
    ).hexdigest()

    required_after_permit_lines = {
        18: "After you get your work permit",
        26: "Conditions of your work permit",
        29: "Conditions of your work permit",
        32: "the type of work you can do",
        33: "the employer you can work for",
        34: "where you can work",
        35: "how long the work permit is valid",
        36: "how long you’re allowed to stay",
        37: "Employment location condition",
        38: "different location",
        40: "Medical conditions",
        41: "upfront medical exam",
        43: "remove the conditions",
        47: "Validity of your work permit",
        48: "passport or biometrics",
        50: "Steps to take after you get your work permit",
        53: "Social insurance number",
        54: "SIN as soon as you arrive",
        58: "Health insurance",
        61: "provincial or territorial health insurance",
        62: "enough money",
        64: "Extensions, studying and permanent residence",
        67: "extend or change your work permit",
        68: "study while you work",
        69: "apply for permanent residence",
        76: "Date modified: 2026-05-07",
    }

    if len(after_permit_lines) != 113:
        raise ValueError(
            "After-permit source line count mismatch"
        )

    for number, marker in required_after_permit_lines.items():
        if (
            marker.casefold()
            not in after_permit_lines[number - 1].casefold()
        ):
            raise ValueError(
                "After-permit source mismatch "
                f"at line {number}: {marker}"
            )

    after_permit_ranges = [
        ("permit_conditions", 29, 38),
        ("medical_conditions_and_removal", 40, 45),
        ("permit_validity_limits", 47, 48),
        ("sin_and_health_insurance", 50, 63),
        ("extension_study_and_permanent_residence", 64, 69),
    ]

    after_permit_evidence = []

    for index, (topic, first, last) in enumerate(
        after_permit_ranges, 1
    ):
        quote = "\n".join(
            after_permit_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"After-permit evidence too short: {topic}"
            )

        after_permit_evidence.append({
            "evidence_id": f"CA_ESWP_POST_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                after_permit_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": after_permit_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["after_permit_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/permit-outside/after-apply.html"
        ),
        "source_language": "en",
        "source_file": (
            after_permit_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": after_permit_hash,
        "source_last_modified": "2026-05-07",
        "char_count": len(after_permit_text),
        "line_count": len(after_permit_lines),
        "review_status": "needs_review",
    }

    result["after_permit_evidence"] = after_permit_evidence

    after_permit_review = {
        "permit_conditions": {
            "permit_fields": [
                "occupation",
                "employer",
                "work_location",
                "permit_validity",
                "authorized_stay_duration",
            ],
            "different_work_location_may_be_possible": True,
            "individual_location_exception_verified": False,
            "individual_permit_conditions_verified": False,
            "source_evidence_id": "CA_ESWP_POST_EVD_01",
        },
        "medical_conditions": {
            "upfront_medical_exam_may_apply": True,
            "medical_restrictions_may_be_removable": True,
            "individual_medical_requirements_verified": False,
            "automatic_medical_condition_removal": False,
            "source_evidence_id": "CA_ESWP_POST_EVD_02",
        },
        "permit_validity": {
            "general_duration_description": "often_1_to_2_years",
            "fixed_eswp_duration": None,
            "limited_by_passport_expiry": True,
            "limited_by_biometrics_expiry": True,
            "individual_expiry_date_verified": False,
            "automatic_duration_calculation": False,
            "source_evidence_id": "CA_ESWP_POST_EVD_03",
        },
        "post_arrival_steps": {
            "sin_application_needed": True,
            "provincial_or_territorial_health_insurance": (
                "one_possible_coverage_option"
            ),
            "medical_cost_funds": (
                "alternative_mentioned_in_source"
            ),
            "dependants_included_in_health_coverage_review": True,
            "individual_health_coverage_verified": False,
            "source_evidence_id": "CA_ESWP_POST_EVD_04",
        },
        "extension_and_other_pathways": {
            "extension_or_change_may_be_possible": True,
            "study_while_working_may_be_possible": True,
            "permanent_residence_separate_pathway": True,
            "employer_change_conditions_verified": False,
            "extension_eligibility_verified": False,
            "automatic_extension_approval": False,
            "automatic_new_employer_work_authorization": False,
            "source_evidence_id": "CA_ESWP_POST_EVD_05",
        },
    }

    for group in after_permit_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["after_permit_review"] = after_permit_review

    result["permit_condition_review"].update({
        "post_issuance_source_collected": True,
        "passport_and_biometrics_expiry_limits_collected": True,
        "medical_conditions_review_required": True,
        "individual_permit_conditions_verified": False,
        "automatic_work_authorization": False,
        "after_permit_source_evidence_ids": [
            item["evidence_id"]
            for item in after_permit_evidence
        ],
    })

    result["after_permit_legal_review"] = {
        "official_post_issuance_guidance_collected": True,
        "employer_change_rules_verified": False,
        "extension_rules_verified": False,
        "individual_permit_validity_verified": False,
        "automatic_permit_conditions_approval": False,
        "automatic_work_authorization": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in after_permit_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(after_permit_evidence) == 5
        and len(after_permit_review) == 5
        and len({
            item["evidence_id"]
            for item in after_permit_evidence
        }) == 5
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in after_permit_review.values()
        )
    ):
        raise ValueError(
            "After-permit integration failed"
        )
    
    # IRCC changing jobs or employers.
    # New permit application and interim work authorization
    # are separate processes.
    # Extension and maintained-status rules remain unapproved.

    change_path = (
        ROOT / "data/raw/canada/employment"
        / "employer_specific_change_employer_ircc_en.txt"
    )

    if not change_path.is_file():
        raise FileNotFoundError(change_path)

    change_raw = change_path.read_bytes()
    change_text = change_raw.decode("utf-8-sig")
    change_lines = change_text.splitlines()
    change_hash = hashlib.sha256(change_raw).hexdigest()

    required_change_lines = {
        12: "Extend or change the conditions",
        20: "Changing jobs or employers",
        21: "must apply for a new work permit",
        23: "request authorization to work",
        25: "Open work permit holders",
        27: "Who’s eligible",
        30: "applied for a new employer-specific work permit",
        32: "have an employer-specific work permit",
        33: "work without a work permit",
        34: "If you lose your job",
        35: "How to request authorization",
        38: "after you apply",
        40: "Step 1",
        41: "IRCC web form",
        49: "courier tracking number",
        54: "PPCHANGEWORK2020",
        57: "Temporary public policy",
        59: "new job offer",
        61: "paper application",
        67: "workers who have been exempt",
        68: "PPCHANGEWORK2020",
        78: "Step 2",
        79: "wait for us to email you",
        81: "10 to 15 days",
        83: "not your work permit",
        93: "Date modified: 2026-10-08",
    }

    if len(change_lines) != 130:
        raise ValueError(
            "Employer change source line count mismatch"
        )

    for number, marker in required_change_lines.items():
        if (
            marker.casefold()
            not in change_lines[number - 1].casefold()
        ):
            raise ValueError(
                "Employer change source mismatch "
                f"at line {number}: {marker}"
            )

    change_ranges = [
        ("new_employer_new_permit_requirement", 20, 25),
        ("interim_authorization_eligibility", 27, 36),
        ("webform_and_priority_code", 38, 54),
        ("temporary_public_policy_request", 56, 76),
        ("authorization_email_and_response", 78, 85),
    ]

    change_evidence = []

    for index, (topic, first, last) in enumerate(
        change_ranges, 1
    ):
        quote = "\n".join(
            change_lines[first - 1:last]
        ).strip()

        if len(quote) < 60:
            raise ValueError(
                f"Employer change evidence too short: {topic}"
            )

        change_evidence.append({
            "evidence_id": f"CA_ESWP_CHANGE_EVD_{index:02d}",
            "topic": topic,
            "source_file": (
                change_path.relative_to(ROOT).as_posix()
            ),
            "source_sha256": change_hash,
            "start_line": first,
            "end_line": last,
            "exact_quote": quote,
            "review_status": "needs_review",
        })

    result["employer_change_source"] = {
        "authority": (
            "Immigration, Refugees and Citizenship Canada"
        ),
        "source_url": (
            "https://www.canada.ca/en/"
            "immigration-refugees-citizenship/services/"
            "work-canada/extend/change-jobs-employers.html"
        ),
        "source_language": "en",
        "source_file": (
            change_path.relative_to(ROOT).as_posix()
        ),
        "source_sha256": change_hash,
        "source_last_modified": "2026-10-08",
        "char_count": len(change_text),
        "line_count": len(change_lines),
        "review_status": "needs_review",
    }

    result["employer_change_evidence"] = change_evidence

    change_review = {
        "new_employer_new_permit": {
            "new_employer_specific_permit_application": True,
            "open_permit_holder_can_change_employer": True,
            "new_employer_work_automatically_allowed": False,
            "individual_new_permit_eligibility_verified": False,
            "source_evidence_id": "CA_ESWP_CHANGE_EVD_01",
        },
        "interim_authorization_eligibility": {
            "inside_canada_application_required": True,
            "existing_employer_specific_permit_route": True,
            "some_work_permit_exempt_workers_eligible": True,
            "business_visitor_excluded": True,
            "gss_short_term_worker_excluded": True,
            "iec_separate_change_rules_required": True,
            "individual_interim_eligibility_verified": False,
            "source_evidence_id": "CA_ESWP_CHANGE_EVD_02",
        },
        "webform_request": {
            "ircc_webform_required_for_request": True,
            "priority_code": "PPCHANGEWORK2020",
            "application_identifiers_required": True,
            "employer_and_job_information_required": True,
            "paper_application_tracking_number_if_needed": True,
            "priority_processing_guaranteed": False,
            "source_evidence_id": "CA_ESWP_CHANGE_EVD_03",
        },
        "temporary_public_policy": {
            "public_policy_request_collected": True,
            "distinct_templates_for": [
                "employer_specific_permit_holders",
                "work_permit_exempt_workers",
            ],
            "previous_and_new_employment_details_required": True,
            "new_work_permit_application_information_required": True,
            "individual_public_policy_exemption_approved": False,
            "source_evidence_id": "CA_ESWP_CHANGE_EVD_04",
        },
        "authorization_email": {
            "wait_for_ircc_authorization_email": True,
            "stated_response_days_approximate": [10, 15],
            "paper_application_may_take_longer": True,
            "email_is_work_permit": False,
            "authorization_email_received": "not_verified",
            "new_employer_work_authorized": "not_verified",
            "automatic_interim_work_authorization": False,
            "source_evidence_id": "CA_ESWP_CHANGE_EVD_05",
        },
    }

    for group in change_review.values():
        group.update({
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    result["employer_change_review"] = change_review

    result["after_permit_review"][
        "extension_and_other_pathways"
    ].update({
        "employer_change_official_source_collected": True,
        "new_permit_required_for_employer_change": True,
        "interim_work_authorization_separate": True,
        "interim_authorization_received": "not_verified",
        "general_extension_rules_fully_verified": False,
        "maintained_status_rules_fully_verified": False,
        "automatic_new_employer_work_authorization": False,
    })

    result["employer_change_legal_review"] = {
        "employer_change_process_collected": True,
        "individual_interim_authorization_verified": False,
        "actual_new_work_permit_issued": "not_verified",
        "general_extension_rules_fully_verified": False,
        "maintained_status_rules_fully_verified": False,
        "job_loss_details_in_saved_txt_verified": False,
        "automatic_new_employer_work_authorization": False,
        "source_evidence_ids": [
            item["evidence_id"]
            for item in change_evidence
        ],
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "review_status": "needs_review",
    }

    if not (
        len(change_evidence) == 5
        and len(change_review) == 5
        and len({
            item["evidence_id"]
            for item in change_evidence
        }) == 5
        and all(
            group["review_status"] == "needs_review"
            and group["eligibility_rule"] is None
            and group["legal_validation_approved"] is False
            and group["approved_for_eligibility_decision"] is False
            for group in change_review.values()
        )
        and change_review["authorization_email"][
            "new_employer_work_authorized"
        ] == "not_verified"
    ):
        raise ValueError(
            "Employer change integration failed"
        )

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

    print("=== CANADA EMPLOYER-SPECIFIC EVIDENCE ===")
    print("SOURCE CHARS:", len(source_text))
    print("SOURCE LINES:", len(source_lines))
    print("EVIDENCE:", len(evidence))
    print("POLICY CANDIDATES:", len(policy_candidates))
    print("SOURCE CHECKS:", len(REQUIRED_LINES))
    print("LMIA REVIEW GROUPS:", len(result["lmia_path_review"]))
    print("SOURCE MODIFIED: 2026-03-31")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()


"""
Germany Opportunity Card (§20a) evidence draft.

Two pathways:
- Recognised skilled worker
- Points system

No candidate is approved for automated eligibility decisions.
"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SOURCE = (
    ROOT / "data/raw/germany/employment"
    / "opportunity_card_make_it_in_germany_en.txt"
)

OUTPUT = (
    ROOT / "data/processed/germany/employment"
    / "opportunity_card_evidence_draft.json"
)

SOURCE_URL = (
    "https://www.make-it-in-germany.com/en/"
    "visa-recognition/opportunity-card/job-search"
)

SECTION_HEADINGS = [
    (
        "requirements",
        "Requirements for the opportunity card: what you should know",
    ),
    (
        "points_system",
        "Option 2: Opportunity card via the points system",
    ),
    (
        "self_check",
        'Self-Check "opportunity card": do you meet the requirements?',
    ),
    (
        "prospects",
        "Prospects with the opportunity card after entry",
    ),
    (
        "online_application",
        "Apply for the opportunity card online",
    ),
]

CHECKS = {
    "legal_basis": r"Section 20a",
    "two_options": r"two options for applying",
    "recognised_qualification": r"fully recognised in Germany",
    "six_points": r"at least six points",
    "financial_proof": r"1,091",
    "vocational_training": r"at least two years of vocational training",
    "german_a1": r"level A1",
    "english_b2": r"level B2",
    "partial_recognition": r"four points",
    "shortage_occupation": r"shortage occupation",
    "professional_experience": r"professional experience",
    "german_language_points": r"three points at level B2",
    "english_bonus": r"English at level C1",
    "age_points": r"Age:",
    "previous_residence": r"continuous period of at least six months",
    "partner_points": r"Skilled worker potential of spouses",
    "maximum_one_year": r"maximum of one year",
    "weekly_20_hours": r"20 hours a week",
    "trial_work": r"maximum of two weeks per employer",
    "extension": r"extended for up to two years",
    "online_portal": r"Consular Services Portal",
}

POINT_CRITERIA = [
    (
        "partial_equivalence",
        "Equivalence of qualification:",
        {"partial_recognition": 4},
    ),
    (
        "shortage_occupation",
        "Qualification in a shortage occupation:",
        {"shortage_occupation": 1},
    ),
    (
        "professional_experience",
        "Professional experience:",
        {
            "two_years_within_five": 2,
            "five_years_within_seven": 3,
        },
    ),
    (
        "language_skills",
        "Language skills:",
        {
            "german_a2": 1,
            "german_b1": 2,
            "german_b2_or_higher": 3,
            "english_c1_or_native_bonus": 1,
        },
    ),
    (
        "age",
        "Age:",
        {
            "younger_age_band": 2,
            "next_age_band": 1,
        },
    ),
    (
        "previous_stay",
        "Previous stays in Germany:",
        {"qualifying_previous_stay": 1},
    ),
    (
        "partner",
        "Skilled worker potential of spouses or life partners:",
        {"eligible_partner": 1},
    ),
]


def read_source():
    raw = SOURCE.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()

    if len(text) < 10000:
        raise ValueError("Source unexpectedly short")

    if "Opportunity Card for Jobseekers in Germany" not in text:
        raise ValueError("Incorrect source document")

    if re.search(r"<!DOCTYPE|<html|<script", text, re.I):
        raise ValueError("HTML detected instead of copied text")

    checks = {
        key: bool(re.search(pattern, text, re.I))
        for key, pattern in CHECKS.items()
    }

    missing = [key for key, passed in checks.items() if not passed]

    if missing:
        raise ValueError(f"Missing source markers: {missing}")

    return raw, text, lines, checks


def locate(lines, marker, start=0):
    matches = [
        i for i in range(start, len(lines))
        if marker in lines[i]
    ]

    if not matches:
        raise ValueError(f"Source marker missing: {marker}")

    return matches[0]


def extract_sections(lines, source_hash):
    # Skip duplicated headings in the page navigation.
    main_start = locate(lines, "In this video:", 25)
    positions = []

    for topic, heading in SECTION_HEADINGS:
        index = locate(lines, heading, main_start)
        positions.append((topic, heading, index))

    indices = [index for _, _, index in positions]

    if indices != sorted(indices):
        raise ValueError("Main section order has changed")

    footer = locate(
        lines, "Information on the web", indices[-1] + 1
    )

    sections = []

    for i, (topic, heading, start) in enumerate(positions):
        end = (
            positions[i + 1][2]
            if i + 1 < len(positions)
            else footer
        )

        quote = "\n".join(lines[start:end]).strip()

        if len(quote) < 60:
            raise ValueError(f"Section too short: {topic}")

        sections.append({
            "section_id": f"DE_OPP_SEC_{i + 1:02d}",
            "topic": topic,
            "heading": heading,
            "start_line": start + 1,
            "end_line": end,
            "exact_quote": quote,
            "source_sha256": source_hash,
            "review_status": "needs_review",
        })

    return sections


def extract_points(lines, source_hash):
    start = locate(
        lines,
        "You can collect points for the following criteria:",
    )
    end = locate(
        lines,
        "Please note that all information you provide",
        start + 1,
    )

    criteria = []

    for i, (name, marker, scores) in enumerate(
        POINT_CRITERIA, 1
    ):
        first = locate(lines, marker, start + 1)

        if first >= end:
            raise ValueError(f"Point criterion outside section: {name}")

        if i < len(POINT_CRITERIA):
            next_marker = POINT_CRITERIA[i][1]
            last = locate(lines, next_marker, first + 1)
        else:
            last = end

        quote = "\n".join(lines[first:last]).strip()

        criteria.append({
            "criterion_id": f"DE_OPP_POINTS_{i:02d}",
            "criterion": name,
            "score_options_for_review": scores,
            "start_line": first + 1,
            "end_line": last,
            "exact_quote": quote,
            "source_sha256": source_hash,
            "stacking_rule_approved": False,
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "review_status": "needs_review",
        })

    return criteria


def build_pathways():
    pathways = [
        {
            "pathway_id": "recognised_skilled_worker",
            "name": "Opportunity Card - Recognised Qualification",
            "points_system_required": False,
            "language_certificate_required_by_this_pathway": False,
            "qualification_review": (
                "German qualification or fully recognised "
                "foreign vocational or academic qualification"
            ),
        },
        {
            "pathway_id": "points_system",
            "name": "Opportunity Card - Points System",
            "points_system_required": True,
            "minimum_points_reference": 6,
            "qualification_review": (
                "Recognised in country of qualification, "
                "with additional evidence and training-duration checks"
            ),
            "language_review": "German A1 or English B2",
        },
    ]

    candidates = []

    for i, pathway in enumerate(pathways, 1):
        candidate_id = f"DE_OPP_POL_{i:02d}"
        pathway["policy_candidate_id"] = candidate_id
        pathway["eligibility_rule"] = None
        pathway["review_status"] = "needs_review"

        candidates.append({
            "policy_id": candidate_id,
            "pathway_id": pathway["pathway_id"],
            "eligibility_rule": None,
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "review_status": "needs_review",
        })

    return pathways, candidates


def main():
    raw, text, lines, checks = read_source()
    source_hash = hashlib.sha256(raw).hexdigest()

    sections = extract_sections(lines, source_hash)
    points = extract_points(lines, source_hash)
    pathways, candidates = build_pathways()

    review_groups = {
        "qualification_and_recognition": [
            "German qualification",
            "full foreign qualification recognition",
            "foreign qualification evidence for points pathway",
            "vocational training duration",
            "anabin or comparability documents",
        ],
        "language_requirements": [
            "points pathway baseline German A1 or English B2",
            "higher German language points",
            "English C1 or native speaker bonus",
        ],
        "points_calculation": [
            "minimum six points",
            "mutual exclusivity of experience tiers",
            "mutual exclusivity of German language tiers",
            "age band boundaries",
            "evidence for each claimed point",
        ],
        "financial_resources": [
            "2026 monthly reference EUR 1091",
            "blocked account",
            "declaration of commitment",
            "duration of funding",
        ],
        "permitted_activities": [
            "initial maximum one year",
            "part-time employment total twenty hours weekly",
            "trial work up to two weeks per employer",
        ],
        "residence_transition": [
            "subsequent employment residence permit",
            "conditional opportunity card extension",
            "separate Section 20 post-graduation pathway",
        ],
        "application_procedure": [
            "Consular Services Portal",
            "German Embassy in Seoul document requirements",
        ],
    }

    result = {
        "country": "Germany",
        "program": "opportunity_card",
        "legal_basis": "AufenthG Section 20a",
        "official_source": {
            "authority": "German Federal Government - Make it in Germany",
            "source_url": SOURCE_URL,
            "source_file": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": source_hash,
            "source_language": "en",
            "char_count": len(text),
            "line_count": len(lines),
        },
        "evidence_sections": sections,
        "eligibility_pathways": pathways,
        "policy_candidates": candidates,
        "points_criteria": points,
        "source_requirement_checks": checks,
        "conditional_requirements": {
            name: {
                "review_points": values,
                "eligibility_rule": None,
                "review_status": "needs_review",
            }
            for name, values in review_groups.items()
        },
        "financial_reference": {
            "year": 2026,
            "currency": "EUR",
            "net_monthly_eur": 1091,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        "related_but_separate_program": {
            "legal_basis": "AufenthG Section 20",
            "description": "Job search after German studies or training",
            "review_status": "needs_review",
        },
        "review_status": "needs_review",
        "eligibility_rule": None,
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # Supplementary evidence from the German Embassy in Seoul.
    # Reuse the previously saved long-term visa source.
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

    # Verify that the source still has the expected section layout.
    boundaries = {
        113: "기회 카드 (Chancenkarte)",
        142: "연구원 및 학자를 위한 비자",
    }

    for line_number, heading in boundaries.items():
        actual = embassy_lines[line_number - 1].strip()
        if actual != heading:
            raise ValueError(
                f"Embassy section boundary mismatch "
                f"at line {line_number}: {actual!r}"
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
        "relevant_start_line": 113,
        "relevant_end_line": 140,
        "review_status": "needs_review",
    }

    embassy_ranges = [
        ("application_channels", 113, 118),
        ("application_documents", 120, 133),
        ("processing_fee_and_validity", 135, 140),
    ]

    embassy_evidence = []

    for index, (topic, first, last) in enumerate(
        embassy_ranges, 1
    ):
        quote = "\n".join(
            embassy_lines[first - 1:last]
        ).strip()

        if len(quote) < 40:
            raise ValueError(
                f"Embassy evidence unexpectedly short: {topic}"
            )

        embassy_evidence.append({
            "evidence_id": f"DE_OPP_EMBASSY_EVD_{index:02d}",
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
        "source_evidence_id": "DE_OPP_EMBASSY_EVD_02",
        "documents_to_review": [
            "completed_and_signed_application",
            "valid_passport_and_biographical_page_copy",
            "recent_passport_photo",
            "korean_foreign_registration_card_if_applicable",
            "qualification_certificate",
            "motivation_letter_and_job_search_plan",
            "curriculum_vitae",
            "financial_proof",
            "incoming_health_insurance",
            "additional_documents_if_requested",
        ],
        "financial_proof_examples": [
            "blocked_account",
            "binding_part_time_employment_offer",
            "declaration_of_commitment",
        ],
        "application_method_specific_requirements": True,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["embassy_application_review"] = {
        "source_evidence_ids": [
            "DE_OPP_EMBASSY_EVD_01",
            "DE_OPP_EMBASSY_EVD_03",
        ],
        "online_application_available": True,
        "in_person_application_option": True,
        "processing_time_guidance": "approximately 4 weeks",
        "embassy_fee_eur": 75,
        "fee_refundable": False,
        "initial_visa_max_months": 12,
        "eligibility_rule": None,
        "review_status": "needs_review",
    }

    result["embassy_scope_notes"] = [
        {
            "topic": "two_eligibility_pathways",
            "finding": (
                "The embassy page provides a shared application "
                "checklist. The federal source defines two distinct "
                "eligibility pathways."
            ),
            "review_status": "needs_review",
        },
        {
            "topic": "financial_proof",
            "finding": (
                "Embassy financial proof examples must be reviewed "
                "against the applicable 2026 federal amount and "
                "the applicant's funding arrangements."
            ),
            "review_status": "needs_review",
        },
        {
            "topic": "source_text_quality",
            "finding": (
                "The embassy text at source line 138 contains "
                "an apparent copy or page-rendering artefact. "
                "Verify the wording before legal approval."
            ),
            "review_status": "needs_review",
        },
        {
            "topic": "points_system",
            "finding": (
                "The embassy application checklist does not replace "
                "the federal rules for the six-point pathway."
            ),
            "review_status": "needs_review",
        },
    ]

    if not (
        len(sections) == 5
        and len(pathways) == 2
        and len(candidates) == 2
        and len(points) == 7
        and len(checks) == 21
        and len(review_groups) == 7
        and all(checks.values())
        and all(
            x["eligibility_rule"] is None
            and not x["approved_for_eligibility_decision"]
            for x in candidates
        )
    ):
        raise ValueError("Opportunity Card consistency check failed")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== GERMANY OPPORTUNITY CARD EVIDENCE ===")
    print("SOURCE CHARS:", len(text))
    print("SOURCE LINES:", len(lines))
    print("EVIDENCE SECTIONS:", len(sections))
    print("ELIGIBILITY PATHWAYS:", len(pathways))
    print("POLICY CANDIDATES:", len(candidates))
    print("POINTS CRITERIA:", len(points))
    print("SOURCE CHECKS:", len(checks))
    print("REVIEW GROUPS:", len(review_groups))
    print("FINANCIAL REFERENCE YEAR: 2026")
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
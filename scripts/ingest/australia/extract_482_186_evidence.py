
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

RAW = Path("data/raw/australia/employment")
OUT = Path(
    "data/processed/australia/employment/"
    "subclass_482_core_skills_evidence_draft.json"
)

SOURCE_URL = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/"
    "skills-in-demand-visa-subclass-482/"
    "core-skills-stream"
)

# (탭, Evidence ID, 분류, 원문 검색 문구)
TARGETS = [
    ("eligibility", "age", "eligibility",
     "There is no age requirement for this visa."),
    ("eligibility", "sponsor", "eligibility",
     "Be nominated by an approved sponsor"),
    ("eligibility", "occupation_list", "eligibility",
     "Core Skills Occupation List (CSOL)"),
    ("eligibility", "work_experience", "eligibility",
     "You must have at least 1 year relevant work experience"),
    ("eligibility", "skills_assessment", "eligibility",
     "Some primary SID visa applicants must undergo"),
    ("eligibility", "english", "eligibility",
     "minimum standards of English language proficiency"),
    ("eligibility", "health_insurance", "eligibility",
     "You must maintain adequate health cover"),
    ("step_by_step", "nomination_trn", "application",
     "Transaction Reference Number (TRN)"),
    ("step_by_step", "passport", "document",
     "You need a valid passport or other travel document"),
    ("step_by_step", "employment_references", "document",
     "Employment references that you provide should cover"),
    ("step_by_step", "translation", "document",
     "Have all non-English documents translated into English."),
    ("step_by_step", "online_application", "application",
     "You apply for this visa online."),
    ("step_by_step", "visa_outcome", "application",
     "We will let you know our decision about your visa application"),
    ("about_this_visa", "visa_cost", "cost",
     "AUD4,015.00"),
    ("about_this_visa", "length_of_stay", "duration",
     "How long you can stay"),
    ("about_this_visa", "family", "family",
     "Include family"),
    ("about_this_visa", "employment_start", "condition",
     "You must begin your employment within 90 days"),
    ("when_you_have_this_visa", "job_loss", "condition",
     "up to 180 days to find a new employer"),
    ("when_you_have_this_visa", "report_changes", "condition",
     "changes to your employer"),
    ("eligibility", "relevant_skills", "eligibility",
     "Have relevant skills, qualifications and employment background to perform occupation"),
    ("eligibility", "health_insurance_requirement", "eligibility",
     "Have health insurance"),
    ("eligibility", "character_requirement", "eligibility",
     "Meet our character requirement"),
    ("eligibility", "sponsorship_payment_restriction", "eligibility",
     "Have not contravened"),
    ("eligibility", "government_debt", "eligibility",
     "Have no debt to the Australian government"),
    ("eligibility", "australian_values_statement", "eligibility",
     "Sign the Australian values statement"),
    ("when_you_have_this_visa", "visa_extension", "duration",
     "You can’t stay longer by extending the visa."),
]

FILES = {
    tab: RAW / f"subclass_482_core_skills_{tab}.txt"
    for tab in (
        "eligibility",
        "step_by_step",
        "about_this_visa",
        "when_you_have_this_visa",
    )
}


def main():
    # 원본을 읽기만 하며, 기존 결과 파일은 덮어쓰지 않음
    if OUT.exists():
        print("UPDATING EXISTING DRAFT:", OUT)

    sources = {}
    for tab, path in FILES.items():
        content = path.read_bytes()
        text = content.decode("utf-8-sig")
        sources[tab] = {
            "path": path,
            "sha256": hashlib.sha256(content).hexdigest(),
            "lines": text.splitlines(),
        }

    evidence = []
    missing = []

    for tab, evidence_id, category, phrase in TARGETS:
        source = sources[tab]
        matches = [
            (number, line)
            for number, line in enumerate(
                source["lines"], start=1
            )
            if phrase in line
        ]

        if not matches:
            missing.append(f"{tab}/{evidence_id}")
            continue

        # 목차에 먼저 등장하는 항목은 마지막 일치 위치를 사용
        if evidence_id in {"length_of_stay", "family"}:
            line_number, quote = matches[-1]
        else:
            line_number, quote = matches[0]

        lines = source["lines"]

        # 긴 정책 항목은 실제 섹션 경계로 추출한다.
        # 끝 경계에 해당하는 다음 섹션 제목은 포함하지 않는다.
        SECTION_BOUNDS = {
            "sponsor": (
                "Be nominated by an approved sponsor",
                "Work for your nominating employer",
            ),
            "length_of_stay": (
                "How long you can stay",
                "Stay longer",
            ),
            "family": (
                "Include family",
                "Apply from",
            ),
            "report_changes": (
                "Tell us if things change",
                "See how long you can stay",
            ),
        }

        if evidence_id in SECTION_BOUNDS:
            start_heading, end_heading = SECTION_BOUNDS[evidence_id]

            start_matches = [
                i for i, line in enumerate(lines)
                if line.strip() == start_heading
            ]

            if not start_matches:
                raise ValueError(
                    f"Section start missing: {evidence_id}"
                )

            # 목차가 있을 수 있으므로 마지막 제목 사용
            start_idx = start_matches[-1]

            end_matches = [
                i for i in range(start_idx + 1, len(lines))
                if lines[i].strip() == end_heading
            ]

            if not end_matches:
                raise ValueError(
                    f"Section end missing: {evidence_id}"
                )

            end_idx = end_matches[0]

            start = start_idx + 1
            end = end_idx
        else:
            start = max(1, line_number - 2)
            end = min(len(lines), line_number + 10)

        source_excerpt = "\n".join(
            lines[start - 1:end]
        )

        evidence.append({
            "evidence_id": f"AU_482_CORE_{evidence_id}",
            "country": "australia",
            "program": "subclass_482_core_skills",
            "category": category,
            "source_tab": tab,
            "source_file": source["path"].as_posix(),
            "source_sha256": source["sha256"],
            "source_url": SOURCE_URL,
            "line_number": line_number,
            "exact_quote": quote,
            "source_excerpt": source_excerpt,
            "excerpt_start_line": start,
            "excerpt_end_line": end,
            "match_count": len(matches),
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    print("=== 482 CORE SKILLS EVIDENCE ===")
    print("TARGETS:", len(TARGETS))
    print("FOUND:", len(evidence))
    print("MISSING:", missing)

    if missing:
        raise ValueError(
            "Some evidence targets were not found. "
            "No output was written."
        )

    result = {
        "program": "subclass_482_core_skills",
        "dataset_type": "evidence_candidate_draft",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_url": SOURCE_URL,
        "evidence_count": len(evidence),
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
        "evidence": evidence,
    }

    # Eligibility 전체 16개 항목을 원문 경계 기준으로 분리
    ELIGIBILITY_HEADINGS = [
        "Be this age",
        "Be the holder of an appropriate visa",
        "Have complied with previous visa conditions",
        "Be nominated by an approved sponsor",
        "Work for your nominating employer",
        "Have relevant skills, qualifications and employment background to perform occupation",
        "Have worked in your nominated occupation or a related field for at least 1 year",
        "Have a positive skills assessment",
        "Have health insurance",
        "Meet our health requirement",
        "Meet our character requirement",
        "Have not contravened ‘paying for visa sponsorship’ legislative provisions",
        "Have this level of English language",
        "Not have had a visa cancelled or a previous application refused",
        "Have no debt to the Australian government",
        "Sign the Australian values statement",
    ]

    lines = sources["eligibility"]["lines"]
    positions = []

    for heading in ELIGIBILITY_HEADINGS:
        matches = [
            i for i, line in enumerate(lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one heading: {heading}, "
                f"found {len(matches)}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Eligibility heading order mismatch")

    end_markers = [
        i for i, line in enumerate(lines)
        if line.strip().startswith(
            "Meet all these criteria? Check how to apply"
        )
    ]

    if len(end_markers) != 1:
        raise ValueError("Eligibility end marker mismatch")

    section_end = end_markers[0]

    if positions[-1] >= section_end:
        raise ValueError("Invalid final section boundary")

    eligibility_sections = []

    for i, heading in enumerate(ELIGIBILITY_HEADINGS):
        start_idx = positions[i]

        if i + 1 < len(positions):
            end_idx = positions[i + 1]
        else:
            end_idx = section_end

        section_text = "\n".join(
            lines[start_idx:end_idx]
        ).strip()

        if not section_text.startswith(heading):
            raise ValueError(
                f"Section heading mismatch: {heading}"
            )

        if len(section_text) < len(heading) + 10:
            raise ValueError(
                f"Section too short: {heading}"
            )

        eligibility_sections.append({
            "section_id": f"AU_482_CORE_ELIG_{i + 1:02d}",
            "heading": heading,
            "source_tab": "eligibility",
            "source_file": sources["eligibility"]["path"].as_posix(),
            "source_sha256": sources["eligibility"]["sha256"],
            "source_url": SOURCE_URL,
            "start_line": start_idx + 1,
            "end_line": end_idx,
            "original_text": section_text,
            "section_sha256": hashlib.sha256(
                section_text.encode("utf-8")
            ).hexdigest(),
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    result["eligibility_sections"] = eligibility_sections
    result["eligibility_section_count"] = len(
        eligibility_sections
    )

    print(
        "ELIGIBILITY SECTIONS:",
        len(eligibility_sections)
    )


    # Eligibility 전체 16개 항목을 원문 경계 기준으로 분리
    ELIGIBILITY_HEADINGS = [
        "Be this age",
        "Be the holder of an appropriate visa",
        "Have complied with previous visa conditions",
        "Be nominated by an approved sponsor",
        "Work for your nominating employer",
        "Have relevant skills, qualifications and employment background to perform occupation",
        "Have worked in your nominated occupation or a related field for at least 1 year",
        "Have a positive skills assessment",
        "Have health insurance",
        "Meet our health requirement",
        "Meet our character requirement",
        "Have not contravened ‘paying for visa sponsorship’ legislative provisions",
        "Have this level of English language",
        "Not have had a visa cancelled or a previous application refused",
        "Have no debt to the Australian government",
        "Sign the Australian values statement",
    ]

    lines = sources["eligibility"]["lines"]
    positions = []

    for heading in ELIGIBILITY_HEADINGS:
        matches = [
            i for i, line in enumerate(lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one heading: {heading}, "
                f"found {len(matches)}"
            )

        positions.append(matches[0])

    if positions != sorted(positions):
        raise ValueError("Eligibility heading order mismatch")

    end_markers = [
        i for i, line in enumerate(lines)
        if line.strip().startswith(
            "Meet all these criteria? Check how to apply"
        )
    ]

    if len(end_markers) != 1:
        raise ValueError("Eligibility end marker mismatch")

    section_end = end_markers[0]

    if positions[-1] >= section_end:
        raise ValueError("Invalid final section boundary")

    eligibility_sections = []

    for i, heading in enumerate(ELIGIBILITY_HEADINGS):
        start_idx = positions[i]

        if i + 1 < len(positions):
            end_idx = positions[i + 1]
        else:
            end_idx = section_end

        section_text = "\n".join(
            lines[start_idx:end_idx]
        ).strip()

        if not section_text.startswith(heading):
            raise ValueError(
                f"Section heading mismatch: {heading}"
            )

        if len(section_text) < len(heading) + 10:
            raise ValueError(
                f"Section too short: {heading}"
            )

        eligibility_sections.append({
            "section_id": f"AU_482_CORE_ELIG_{i + 1:02d}",
            "heading": heading,
            "source_tab": "eligibility",
            "source_file": sources["eligibility"]["path"].as_posix(),
            "source_sha256": sources["eligibility"]["sha256"],
            "source_url": SOURCE_URL,
            "start_line": start_idx + 1,
            "end_line": end_idx,
            "original_text": section_text,
            "section_sha256": hashlib.sha256(
                section_text.encode("utf-8")
            ).hexdigest(),
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    result["eligibility_sections"] = eligibility_sections
    result["eligibility_section_count"] = len(
        eligibility_sections
    )

    print(
        "ELIGIBILITY SECTIONS:",
        len(eligibility_sections)
    )

    # Eligibility 원문 16개를 정책 검토 후보로 변환
    # 원문을 해석하거나 자격 충족을 자동 판정하지 않는다.
    POLICY_TOPICS = [
        "age",
        "visa_status_at_application",
        "previous_visa_compliance",
        "employer_sponsorship",
        "nominated_employment",
        "relevant_skills_and_qualifications",
        "relevant_work_experience",
        "skills_assessment",
        "health_insurance",
        "health_requirement",
        "character_requirement",
        "prohibited_sponsorship_payments",
        "english_language",
        "immigration_history",
        "government_debt",
        "australian_values_statement",
    ]

    if len(eligibility_sections) != len(POLICY_TOPICS):
        raise ValueError(
            "Eligibility section / policy topic count mismatch"
        )

    policy_candidates = []

    for section, topic in zip(
        eligibility_sections,
        POLICY_TOPICS,
    ):
        policy_candidates.append({
            "policy_id": section["section_id"].replace(
                "_ELIG_", "_POL_"
            ),
            "program": "subclass_482_core_skills",
            "topic": topic,
            "title": section["heading"],
            "source_section_id": section["section_id"],
            "source_file": section["source_file"],
            "source_sha256": section["source_sha256"],
            "source_url": section["source_url"],
            "source_start_line": section["start_line"],
            "source_end_line": section["end_line"],
            "source_text": section["original_text"],

            # 실제 정책 해석은 별도 검토
            "applicability": "needs_review",
            "requirement_type": "needs_review",
            "requirement_value": None,
            "exceptions": {
                "review_status": "needs_review",
                "items": [],
            },
            "required_documents": {
                "review_status": "needs_review",
                "items": [],
            },
            "eligibility_rule": None,
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    if len({
        item["policy_id"]
        for item in policy_candidates
    }) != 16:
        raise ValueError("Duplicate policy candidate IDs")

    result["policy_candidates"] = policy_candidates
    result["policy_candidate_count"] = len(
        policy_candidates
    )

    # 공식 원문에 근거한 잠정 정책 분류.
    # 실제 자격 충족 여부나 법적 승인 여부는 판정하지 않는다.
    CLASSIFICATION_DRAFT = {
        "age": (
            "no_age_requirement",
            "The source states that there is no age requirement."
        ),
        "visa_status_at_application": (
            "conditional",
            "Specific visa status is required when applying in Australia."
        ),
        "previous_visa_compliance": (
            "conditional",
            "Previous visa-condition compliance is relevant when in Australia."
        ),
        "employer_sponsorship": (
            "required",
            "Employer nomination and sponsor status must be reviewed."
        ),
        "nominated_employment": (
            "required_with_possible_exceptions",
            "Work restrictions depend on sponsor type and occupation."
        ),
        "relevant_skills_and_qualifications": (
            "required",
            "Relevant skills, qualifications and experience must be demonstrated."
        ),
        "relevant_work_experience": (
            "required_with_recognition_rules",
            "At least one year of relevant experience is stated, subject to recognition rules."
        ),
        "skills_assessment": (
            "occupation_dependent",
            "Mandatory assessment applies to certain applicants, with possible exemptions."
        ),
        "health_insurance": (
            "required",
            "Adequate health cover must be maintained during the relevant stay."
        ),
        "health_requirement": (
            "required",
            "Health requirements apply to primary and relevant secondary applicants."
        ),
        "character_requirement": (
            "required",
            "Character requirements apply; document exemptions require review."
        ),
        "prohibited_sponsorship_payments": (
            "prohibition_with_possible_exception",
            "Relevant sponsorship-payment conduct and ministerial discretion require review."
        ),
        "english_language": (
            "required_with_exemptions",
            "Minimum English proficiency standards apply unless exempt."
        ),
        "immigration_history": (
            "case_specific",
            "Prior visa cancellation or refusal may affect eligibility."
        ),
        "government_debt": (
            "conditional",
            "Outstanding Australian government debt requires repayment or an arrangement."
        ),
        "australian_values_statement": (
            "age_conditional",
            "Confirmation is required for applicants aged 18 or older."
        ),
    }

    for policy in policy_candidates:
        topic = policy["topic"]
        classification, note = CLASSIFICATION_DRAFT[topic]

        policy["provisional_classification"] = classification
        policy["interpretation_note_draft"] = note
        policy["interpretation_review_status"] = "needs_review"
        policy["rule_parameters_verified"] = False

        # 판정 엔진에서 사용할 실행 가능한 규칙은 아직 생성하지 않음
        policy["eligibility_rule"] = None
        policy["approved_for_eligibility_decision"] = False

    result["policy_candidates"] = policy_candidates

    print(
        "CLASSIFIED POLICY DRAFTS:",
        len(policy_candidates)
    )

    print(
        "POLICY CANDIDATES:",
        len(policy_candidates)
    )

    # 482 영어 능력 요건의 별도 공식 원문 연결
    # 점수, 면제 조건은 아직 자동 판정 규칙으로 변환하지 않음
    english_path = (
        RAW / "subclass_482_english_proficiency.txt"
    )

    english_bytes = english_path.read_bytes()
    english_text = english_bytes.decode("utf-8-sig")

    english_source = {
        "source_id": "AU_482_ENGLISH_OFFICIAL",
        "source_file": english_path.as_posix(),
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "skills-in-demand-visa-subclass-482/"
            "sufficient-english"
        ),
        "source_sha256": hashlib.sha256(
            english_bytes
        ).hexdigest(),
        "source_text": english_text,
        "last_updated": "2026-09-21",
        "applies_to_streams": [
            "core_skills",
            "specialist_skills",
            "labour_agreement",
        ],
        "review_status": "needs_review",
        "legal_validation_approved": False,
    }

    for policy in policy_candidates:
        if policy["topic"] == "english_language":
            policy["additional_source_ids"] = [
                english_source["source_id"]
            ]
            policy["english_requirements_review"] = {
                "exemptions": "needs_review",
                "test_scores": "needs_review",
                "test_date_rules": "needs_review",
                "online_test_restrictions": "needs_review",
                "labour_agreement_exception": "needs_review",
            }

    result["additional_official_sources"] = [
        english_source
    ]
    result["policy_candidates"] = policy_candidates

    print("ENGLISH SOURCE LINKED: True")

    # =========================================================
    # Supplementary salary policies + consolidated data audit
    # =========================================================

    salary_path = (
        RAW / "subclass_482_salary_requirements.txt"
    )
    salary_bytes = salary_path.read_bytes()
    salary_text = salary_bytes.decode("utf-8-sig")
    salary_sha256 = hashlib.sha256(salary_bytes).hexdigest()

    salary_url = (
        "https://immi.homeaffairs.gov.au/visas/"
        "getting-a-visa/visa-listing/"
        "temporary-skill-shortage-482/"
        "salary-requirements"
    )

    salary_markers = [
        "Core Skills Income Threshold",
        "Annual market salary rate",
        "Determining the AMSR",
        "How to determine the AMSR",
        "AUD79,423",
        "AUD76,515",
        "AUD73,150",
        "1 July 2026",
        "30 June 2027",
        "AUD250,000",
        "Last updated: 21 September 2026",
    ]

    missing_salary_markers = [
        marker for marker in salary_markers
        if marker not in salary_text
    ]

    if missing_salary_markers:
        raise ValueError(
            "Missing salary markers: "
            + repr(missing_salary_markers)
        )

    salary_source = {
        "source_id": "AU_482_SALARY_OFFICIAL",
        "source_file": salary_path.as_posix(),
        "source_url": salary_url,
        "source_sha256": salary_sha256,
        "source_text": salary_text,
        "last_updated": "2026-09-21",
        "review_status": "needs_review",
        "legal_validation_approved": False,
    }

    additional_sources = result.setdefault(
        "additional_official_sources", []
    )

    additional_sources = [
        source for source in additional_sources
        if source["source_id"] != salary_source["source_id"]
    ]
    additional_sources.append(salary_source)

    result["additional_official_sources"] = additional_sources

    # Separate supplemental policies so the existing
    # 16 Eligibility policy candidates remain unchanged.
    supplemental_policies = [
        {
            "policy_id": "AU_482_CORE_POL_CSIT",
            "program": "subclass_482_core_skills",
            "topic": "core_skills_income_threshold",
            "source_id": salary_source["source_id"],
            "source_sha256": salary_sha256,
            "threshold_history_draft": [
                {
                    "from": "2024-12-07",
                    "to": "2025-06-30",
                    "amount_aud": 73150,
                },
                {
                    "from": "2025-07-01",
                    "to": "2026-06-30",
                    "amount_aud": 76515,
                },
                {
                    "from": "2026-07-01",
                    "to": "2027-06-30",
                    "amount_aud": 79423,
                },
            ],
            "date_basis": "nomination_lodgement_date",
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "eligibility_rule": None,
        },
        {
            "policy_id": "AU_482_CORE_POL_AMSR",
            "program": "subclass_482_core_skills",
            "topic": "annual_market_salary_rate",
            "source_id": salary_source["source_id"],
            "source_sha256": salary_sha256,
            "salary_comparison_required_draft": True,
            "annual_salary_250k_condition_review": True,
            "determination_methods_review": True,
            "copied_table_layout_verified": False,
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
            "eligibility_rule": None,
        },
    ]

    result["supplemental_policy_candidates"] = (
        supplemental_policies
    )

    # ---------------- Combined audit ----------------

    evidence = result["evidence"]
    sections = result["eligibility_sections"]
    policies = result["policy_candidates"]
    sources_list = result["additional_official_sources"]

    all_policy_ids = [
        p["policy_id"]
        for p in policies + supplemental_policies
    ]

    if len(evidence) != 26:
        raise ValueError("Evidence count mismatch")

    if len({
        e["evidence_id"] for e in evidence
    }) != 26:
        raise ValueError("Duplicate evidence IDs")

    if len(sections) != 16 or len(policies) != 16:
        raise ValueError("Eligibility count mismatch")

    if len(set(all_policy_ids)) != 18:
        raise ValueError("Duplicate policy IDs")

    section_by_id = {
        s["section_id"]: s for s in sections
    }

    for policy in policies:
        section = section_by_id.get(
            policy["source_section_id"]
        )

        if section is None:
            raise ValueError(
                "Missing section: " + policy["policy_id"]
            )

        if policy["source_text"] != section["original_text"]:
            raise ValueError(
                "Policy source mismatch: " + policy["policy_id"]
            )

    for section in sections:
        source_path = Path(section["source_file"])
        source_bytes = source_path.read_bytes()
        source_lines = source_bytes.decode(
            "utf-8-sig"
        ).splitlines()

        actual_text = "\n".join(
            source_lines[
                section["start_line"] - 1:
                section["end_line"]
            ]
        ).strip()

        if (
            hashlib.sha256(source_bytes).hexdigest()
            != section["source_sha256"]
            or actual_text != section["original_text"]
        ):
            raise ValueError(
                "Section integrity failed: "
                + section["section_id"]
            )

    for current, following in zip(
        sections, sections[1:]
    ):
        if current["end_line"] + 1 != following["start_line"]:
            raise ValueError("Eligibility section gap")

    source_ids = [
        source["source_id"]
        for source in sources_list
    ]

    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Duplicate official source IDs")

    for source in sources_list:
        source_bytes = Path(
            source["source_file"]
        ).read_bytes()

        if (
            hashlib.sha256(source_bytes).hexdigest()
            != source["source_sha256"]
        ):
            raise ValueError(
                "Official source SHA mismatch: "
                + source["source_id"]
            )

    english_policies = [
        p for p in policies
        if p["topic"] == "english_language"
    ]

    if len(english_policies) != 1:
        raise ValueError("English policy missing")

    if "AU_482_ENGLISH_OFFICIAL" not in (
        english_policies[0].get(
            "additional_source_ids", []
        )
    ):
        raise ValueError("English source not linked")

    if not {
        "AU_482_ENGLISH_OFFICIAL",
        "AU_482_SALARY_OFFICIAL",
    }.issubset(set(source_ids)):
        raise ValueError("Official source missing")

    for policy in policies + supplemental_policies:
        if (
            policy["review_status"] != "needs_review"
            or policy["legal_validation_approved"] is not False
            or policy["approved_for_eligibility_decision"] is not False
            or policy["eligibility_rule"] is not None
        ):
            raise ValueError(
                "Unsafe policy approval: "
                + policy["policy_id"]
            )

    if result["review_status"] != "needs_review":
        raise ValueError("Unexpected overall review status")

    print("=== CONSOLIDATED 482 DATA AUDIT ===")
    print("EVIDENCE:", len(evidence))
    print("ELIGIBILITY SECTIONS:", len(sections))
    print("BASE POLICIES:", len(policies))
    print("SALARY POLICIES:", len(supplemental_policies))
    print("OFFICIAL DETAIL SOURCES:", len(sources_list))
    print("SALARY SHA256:", salary_sha256)
    print("AMSR TABLE LAYOUT: NEEDS_REVIEW")
    print("LEGAL STATUS: needs_review")
    print("CONSOLIDATED AUDIT: PASS")

    # ========================================================
    # 482 Specialist Skills: four-tab source + policy draft
    # ========================================================
    import json as ss_json
    import hashlib as ss_hashlib
    from pathlib import Path as SSPath

    ss_tabs = [
        "about_this_visa",
        "eligibility",
        "step_by_step",
        "when_you_have_this_visa",
    ]

    ss_sources = {}
    ss_texts = {}

    for tab in ss_tabs:
        path = RAW / (
            f"subclass_482_specialist_skills_{tab}.txt"
        )
        content = path.read_bytes()
        txt = content.decode("utf-8-sig")

        if not 1000 < len(txt) < 100000:
            raise ValueError(f"Unexpected source size: {tab}")

        if any(tag in txt.lower() for tag in (
            "<!doctype", "<html", "<script"
        )):
            raise ValueError(f"HTML source found: {tab}")

        ss_texts[tab] = txt
        ss_sources[tab] = {
            "source_file": path.as_posix(),
            "source_sha256": ss_hashlib.sha256(
                content
            ).hexdigest(),
            "char_count": len(txt),
            "source_url": (
                "https://immi.homeaffairs.gov.au/"
                "visas/getting-a-visa/visa-listing/"
                "skills-in-demand-visa-subclass-482/"
                "specialist-skills-stream"
            ),
            "review_status": "needs_review",
        }

    ss_headings = [
        ("age", "Be this age"),
        ("visa_status_at_application",
         "Be the holder of an appropriate visa"),
        ("previous_visa_compliance",
         "Have complied with previous visa conditions"),
        ("employer_sponsorship",
         "Be nominated by an approved sponsor"),
        ("nominated_employment",
         "Work for your nominating employer"),
        ("relevant_skills_and_qualifications",
         "Have relevant skills, qualifications and employment background to perform occupation"),
        ("relevant_work_experience",
         "Have worked in your nominated occupation or a related field for at least 1 year"),
        ("skills_assessment",
         "Have a positive skills assessment"),
        ("health_insurance", "Have health insurance"),
        ("health_requirement", "Meet our health requirement"),
        ("character_requirement", "Meet our character requirement"),
        ("prohibited_sponsorship_payments",
         "Have not contravened ‘paying for visa sponsorship’ legislative provisions"),
        ("immigration_history",
         "Not have had a visa cancelled or a previous application refused"),
        ("government_debt",
         "Have no debt to the Australian government"),
        ("australian_values_statement",
         "Sign the Australian values statement"),
    ]

    ss_lines = ss_texts["eligibility"].splitlines()
    ss_positions = []

    for topic, heading in ss_headings:
        matches = [
            i for i, line in enumerate(ss_lines)
            if line.strip() == heading
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Eligibility heading mismatch: {heading} "
                f"({len(matches)})"
            )
        ss_positions.append(matches[0])

    if ss_positions != sorted(ss_positions):
        raise ValueError("Eligibility heading order mismatch")

    # Exclude navigation/footer content after final section.
    ss_last = ss_positions[-1]
    ss_footer = [
        i for i in range(ss_last + 1, len(ss_lines))
        if (
            ss_lines[i].strip().startswith("Last updated:")
            or ss_lines[i].strip().startswith(
                "pop-up content starts"
            )
            or ss_lines[i].strip().startswith(
                "Tell us what you think"
            )
        )
    ]
    ss_end = min(ss_footer) if ss_footer else len(ss_lines)

    ss_sections = []
    ss_policies = []
    ss_evidence = []

    for index, (topic, heading) in enumerate(
        ss_headings, start=1
    ):
        begin = ss_positions[index - 1]
        end = (
            ss_positions[index]
            if index < len(ss_positions)
            else ss_end
        )

        body = "\n".join(ss_lines[begin:end]).strip()

        if not body.startswith(heading):
            raise ValueError(f"Section mismatch: {heading}")

        if len(body) <= len(heading):
            raise ValueError(f"Empty section: {heading}")

        section_id = f"AU_482_SPECIALIST_ELIG_{index:02d}"
        policy_id = f"AU_482_SPECIALIST_POL_{index:02d}"

        ss_sections.append({
            "section_id": section_id,
            "heading": heading,
            "start_line": begin + 1,
            "end_line": end,
            "original_text": body,
            "source_sha256": ss_sources[
                "eligibility"
            ]["source_sha256"],
            "review_status": "needs_review",
        })

        ss_evidence.append({
            "evidence_id": f"AU_482_SPECIALIST_EVD_{index:02d}",
            "source_section_id": section_id,
            "exact_quote": heading,
            "line_number": begin + 1,
            "source_tab": "eligibility",
            "review_status": "needs_review",
        })

        ss_policies.append({
            "policy_id": policy_id,
            "program": "subclass_482_specialist_skills",
            "topic": topic,
            "source_section_id": section_id,
            "source_text": body,
            "requirement_type": "needs_review",
            "applicability": "needs_review",
            "exceptions": [],
            "eligibility_rule": None,
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    # Reuse shared 482 rules without copying Core Skills rules.
    ss_shared = {}

    for source_id, filename in [
        (
            "AU_482_ENGLISH_OFFICIAL",
            "subclass_482_english_proficiency.txt",
        ),
        (
            "AU_482_SALARY_OFFICIAL",
            "subclass_482_salary_requirements.txt",
        ),
        (
            "AU_482_IMMI_18_039",
            "subclass_482_mandatory_skills_assessment_immi_18_039.txt",
        ),
    ]:
        path = RAW / filename
        content = path.read_bytes()
        ss_shared[source_id] = {
            "source_file": path.as_posix(),
            "source_sha256": ss_hashlib.sha256(
                content
            ).hexdigest(),
            "review_status": "needs_review",
        }

    salary_txt = (
        RAW / "subclass_482_salary_requirements.txt"
    ).read_text(encoding="utf-8-sig")

    if "AUD146,576" not in salary_txt:
        raise ValueError("Specialist income threshold missing")

    ss_supplemental = [
        {
            "topic": "specialist_skills_income_threshold",
            "source_id": "AU_482_SALARY_OFFICIAL",
            "amount_aud_draft": 146576,
            "nomination_lodgement_from": "2026-07-01",
            "nomination_lodgement_to": "2027-06-30",
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        {
            "topic": "specialist_occupation_requirements",
            "source_tab": "eligibility",
            "occupation_rules_structured": False,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
        {
            "topic": "english_language",
            "source_id": "AU_482_ENGLISH_OFFICIAL",
            "exemptions_structured": False,
            "test_scores_structured": False,
            "eligibility_rule": None,
            "review_status": "needs_review",
        },
    ]

    ss_result = {
        "program": "subclass_482_specialist_skills",
        "source_tabs": ss_sources,
        "shared_official_sources": ss_shared,
        "evidence": ss_evidence,
        "eligibility_sections": ss_sections,
        "policy_candidates": ss_policies,
        "supplemental_policy_candidates": ss_supplemental,
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # Consolidated integrity checks
    if len(ss_sections) != 15 or len(ss_policies) != 15:
        raise ValueError("Specialist policy count mismatch")

    if len({
        p["policy_id"] for p in ss_policies
    }) != 15:
        raise ValueError("Duplicate specialist policy ID")

    if any(
        a["end_line"] + 1 != b["start_line"]
        for a, b in zip(ss_sections, ss_sections[1:])
    ):
        raise ValueError("Specialist section boundary gap")

    ss_output = SSPath(
        "data/processed/australia/employment/"
        "subclass_482_specialist_skills_evidence_draft.json"
    )

    ss_output.parent.mkdir(parents=True, exist_ok=True)
    ss_output.write_text(
        ss_json.dumps(
            ss_result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== 482 SPECIALIST SKILLS ===")
    print("SOURCE TABS:", len(ss_sources))
    print("EVIDENCE:", len(ss_evidence))
    print("ELIGIBILITY SECTIONS:", len(ss_sections))
    print("BASE POLICY CANDIDATES:", len(ss_policies))
    print("SUPPLEMENTAL CANDIDATES:", len(ss_supplemental))
    print("SHARED SOURCES:", len(ss_shared))
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", ss_output)

    # =========================================================
    # 482 Labour Agreement - source and policy draft
    # =========================================================
    import json as la_json

    la_tabs = [
        "about_this_visa",
        "eligibility",
        "step_by_step",
        "when_you_have_this_visa",
    ]

    la_url = (
        "https://immi.homeaffairs.gov.au/visas/"
        "getting-a-visa/visa-listing/"
        "skills-in-demand-visa-subclass-482/"
        "labour-agreement-stream"
    )

    la_sources = {}
    la_lines = {}

    for tab in la_tabs:
        p = RAW / f"subclass_482_labour_agreement_{tab}.txt"
        raw = p.read_bytes()
        content = raw.decode("utf-8-sig")

        if not 1000 < len(content) < 100000:
            raise ValueError(f"Invalid Labour Agreement source: {tab}")

        if "<!doctype" in content.lower() or "<script" in content.lower():
            raise ValueError(f"HTML found in source: {tab}")

        la_lines[tab] = content.splitlines()
        la_sources[tab] = {
            "source_file": p.as_posix(),
            "source_url": la_url,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "char_count": len(content),
            "review_status": "needs_review",
        }

    la_headings = [
        ("labour_agreement_occupation",
         "Be working under a labour agreement"),
        ("relevant_work_experience",
         "Have at least 1 year of work experience"),
        ("employer_nomination", "Be nominated"),
        ("health_requirement", "Meet our health requirement"),
        ("character_requirement", "Meet our character requirement"),
        ("english_language",
         "Have a level of English language suitable for your occupation"),
        ("australian_values_statement",
         "Sign the Australian values statement"),
        ("health_insurance", "Have adequate health insurance"),
        ("government_debt",
         "Have paid back your debt to the Australian government"),
        ("immigration_history",
         "Not have had a visa cancelled or a previous application refused"),
    ]

    lines = la_lines["eligibility"]
    positions = []

    for topic, heading in la_headings:
        found = [
            i for i, line in enumerate(lines)
            if line.strip() == heading
        ]
        if len(found) != 1:
            raise ValueError(f"Heading mismatch: {heading}: {found}")
        positions.append(found[0])

    if positions != sorted(positions):
        raise ValueError("Eligibility heading order mismatch")

    ending = [
        i for i, line in enumerate(lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(ending) != 1 or ending[0] <= positions[-1]:
        raise ValueError("Eligibility end marker mismatch")

    la_sections = []
    la_evidence = []
    la_policies = []

    for index, (topic, heading) in enumerate(la_headings):
        start = positions[index]
        end = (
            positions[index + 1]
            if index + 1 < len(positions)
            else ending[0]
        )

        body = "\n".join(lines[start:end]).strip()
        if not body.startswith(heading) or len(body) <= len(heading):
            raise ValueError(f"Invalid eligibility section: {heading}")

        identifier = f"AU_482_LA_{index + 1:02d}"

        la_sections.append({
            "section_id": identifier,
            "topic": topic,
            "heading": heading,
            "source_tab": "eligibility",
            "start_line": start + 1,
            "end_line": end,
            "original_text": body,
            "source_sha256": la_sources["eligibility"]["source_sha256"],
            "review_status": "needs_review",
        })

        la_evidence.append({
            "evidence_id": identifier + "_EVD",
            "source_section_id": identifier,
            "source_tab": "eligibility",
            "exact_quote": heading,
            "line_number": start + 1,
            "review_status": "needs_review",
        })

        la_policies.append({
            "policy_id": identifier + "_POL",
            "program": "subclass_482_labour_agreement",
            "topic": topic,
            "source_section_id": identifier,
            "source_text": body,
            "requirement_type": "needs_review",
            "labour_agreement_variation": "needs_review",
            "exceptions": [],
            "eligibility_rule": None,
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    # Application step headings, retaining original document
    step_lines = la_lines["step_by_step"]
    la_steps = []

    for number in range(1, 5):
        heading = f"Step {number}"
        matches = [
            i for i, line in enumerate(step_lines)
            if line.strip() == heading
        ]
        if len(matches) != 1:
            raise ValueError(f"Application {heading} mismatch")

        la_steps.append({
            "step_number": number,
            "heading": heading,
            "source_tab": "step_by_step",
            "start_line": matches[0] + 1,
            "review_status": "needs_review",
        })

    # Reuse common official documents as evidence sources
    la_shared_files = {
        "english": "subclass_482_english_proficiency.txt",
        "salary": "subclass_482_salary_requirements.txt",
        "skills_assessment":
            "subclass_482_mandatory_skills_assessment_immi_18_039.txt",
    }

    la_shared = {}

    for key, filename in la_shared_files.items():
        p = RAW / filename
        la_shared[key] = {
            "source_file": p.as_posix(),
            "source_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "applicability": "needs_review",
        }

    la_result = {
        "program": "subclass_482_labour_agreement",
        "stream": "labour_agreement",
        "official_sources": la_sources,
        "shared_sources": la_shared,
        "eligibility_sections": la_sections,
        "evidence": la_evidence,
        "policy_candidates": la_policies,
        "application_steps": la_steps,
        "agreement_specific_terms": {
            "occupation": "needs_review",
            "work_experience": "needs_review",
            "english": "needs_review",
            "salary": "needs_review",
        },
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    if not (
        len(la_sources) == 4
        and len(la_sections) == 10
        and len(la_evidence) == 10
        and len(la_policies) == 10
        and len(la_steps) == 4
    ):
        raise ValueError("Labour Agreement data count mismatch")

    if any(
        a["end_line"] + 1 != b["start_line"]
        for a, b in zip(la_sections, la_sections[1:])
    ):
        raise ValueError("Labour Agreement section boundary gap")

    la_out = (
        RAW.parent.parent.parent
        / "processed/australia/employment/"
        "subclass_482_labour_agreement_evidence_draft.json"
    )

    # Explicit project-root output, independent of RAW layout
    la_out = Path(
        "data/processed/australia/employment/"
        "subclass_482_labour_agreement_evidence_draft.json"
    )

    la_out.parent.mkdir(parents=True, exist_ok=True)
    la_out.write_text(
        la_json.dumps(la_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== 482 LABOUR AGREEMENT ===")
    print("SOURCE TABS:", len(la_sources))
    print("ELIGIBILITY SECTIONS:", len(la_sections))
    print("EVIDENCE:", len(la_evidence))
    print("POLICY CANDIDATES:", len(la_policies))
    print("APPLICATION STEPS:", len(la_steps))
    print("SHARED SOURCES:", len(la_shared))
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", la_out)

    # =====================================================
    # Australia 186 Direct Entry: source and policy draft
    # =====================================================
    import json as de_json

    de_prefix = "subclass_186_direct_entry"
    de_url = (
        "https://immi.homeaffairs.gov.au/visas/"
        "getting-a-visa/visa-listing/"
        "employer-nomination-scheme-186/direct-entry-stream"
    )

    de_tabs = [
        "about_this_visa",
        "eligibility",
        "step_by_step",
        "when_you_have_this_visa",
    ]

    de_sources = {}
    de_lines = {}

    for tab in de_tabs:
        path = RAW / f"{de_prefix}_{tab}.txt"
        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")

        if not 1000 < len(content) < 100000:
            raise ValueError(f"186 invalid source size: {tab}")

        if any(x in content.lower() for x in (
            "<!doctype", "<html", "<script"
        )):
            raise ValueError(f"186 HTML source detected: {tab}")

        de_lines[tab] = content.splitlines()
        de_sources[tab] = {
            "source_file": path.as_posix(),
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "source_url": de_url,
            "char_count": len(content),
            "review_status": "needs_review",
        }

    de_headings = [
        ("eligible_occupation", "Have an eligible occupation"),
        ("work_experience", "Have relevant work experience"),
        ("licensing_registration",
         "Licensing, registration or membership"),
        ("skills_assessment", "Have a positive skills assessment"),
        ("employer_nomination", "Be nominated"),
        ("age", "Be this age"),
        ("health", "Meet our health requirement"),
        ("character", "Meet our character requirement"),
        ("values_statement", "Sign the Australian values statement"),
        ("english", "Have this level of English language"),
        ("government_debt",
         "Have paid back your debt to the Australian government"),
        ("immigration_history",
         "Not have had a visa cancelled or a previous application refused"),
    ]

    eligibility_lines = de_lines["eligibility"]
    de_positions = []

    for topic, heading in de_headings:
        matches = [
            i for i, line in enumerate(eligibility_lines)
            if line.strip() == heading
        ]
        if len(matches) != 1:
            raise ValueError(
                f"186 heading mismatch: {heading}: {matches}"
            )
        de_positions.append(matches[0])

    if de_positions != sorted(de_positions):
        raise ValueError("186 eligibility heading order mismatch")

    end_matches = [
        i for i, line in enumerate(eligibility_lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(end_matches) != 1:
        raise ValueError("186 eligibility end marker mismatch")

    de_end = end_matches[0]
    if de_end <= de_positions[-1]:
        raise ValueError("186 invalid eligibility end position")

    de_sections = []
    de_policies = []
    de_evidence = []

    for index, (topic, heading) in enumerate(de_headings):
        start = de_positions[index]
        end = (
            de_positions[index + 1]
            if index + 1 < len(de_positions)
            else de_end
        )

        body = "\n".join(
            eligibility_lines[start:end]
        ).strip()

        if not body.startswith(heading) or len(body) <= len(heading):
            raise ValueError(f"186 invalid section: {heading}")

        section_id = f"AU_186_DE_ELIG_{index + 1:02d}"

        de_sections.append({
            "section_id": section_id,
            "topic": topic,
            "heading": heading,
            "source_tab": "eligibility",
            "source_sha256": de_sources[
                "eligibility"
            ]["source_sha256"],
            "start_line": start + 1,
            "end_line": end,
            "original_text": body,
            "review_status": "needs_review",
        })

        de_evidence.append({
            "evidence_id": f"AU_186_DE_EVD_{index + 1:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "exact_quote": heading,
            "line_number": start + 1,
            "review_status": "needs_review",
        })

        de_policies.append({
            "policy_id": f"AU_186_DE_POL_{index + 1:02d}",
            "program": de_prefix,
            "topic": topic,
            "source_section_id": section_id,
            "source_text": body,
            "requirement_type": "needs_review",
            "exceptions_review_status": "needs_review",
            "eligibility_rule": None,
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    # Retain all five application steps with their source text
    step_lines = de_lines["step_by_step"]
    step_positions = []

    for number in range(1, 6):
        matches = [
            i for i, line in enumerate(step_lines)
            if line.strip() == f"Step {number}"
        ]
        if len(matches) != 1:
            raise ValueError(
                f"186 Step {number} mismatch: {matches}"
            )
        step_positions.append(matches[0])

    if step_positions != sorted(step_positions):
        raise ValueError("186 application step order mismatch")

    step_footer = next(
        (
            i for i in range(step_positions[-1] + 1, len(step_lines))
            if step_lines[i].strip().startswith(
                "pop-up content starts"
            )
            or step_lines[i].strip().startswith(
                "Tell us what you think of this page"
            )
            or step_lines[i].strip().startswith("Last updated:")
        ),
        len(step_lines),
    )

    de_steps = []

    for index, start in enumerate(step_positions):
        end = (
            step_positions[index + 1]
            if index + 1 < len(step_positions)
            else step_footer
        )
        de_steps.append({
            "step_number": index + 1,
            "start_line": start + 1,
            "end_line": end,
            "original_text": "\n".join(
                step_lines[start:end]
            ).strip(),
            "review_status": "needs_review",
        })

    # CSOL source is shared; do not reuse 482-specific
    # skills-assessment exemptions for subclass 186.
    csol_path = RAW / "core_skills_occupation_list_official.txt"

    de_result = {
        "program": de_prefix,
        "visa_subclass": "186",
        "stream": "direct_entry",
        "pathway_type": "permanent_employment",
        "official_sources": de_sources,
        "eligibility_sections": de_sections,
        "evidence": de_evidence,
        "policy_candidates": de_policies,
        "application_steps": de_steps,
        "shared_sources": {
            "csol": {
                "source_file": csol_path.as_posix(),
                "source_sha256": hashlib.sha256(
                    csol_path.read_bytes()
                ).hexdigest(),
                "review_status": "needs_review",
            },
        },
        "detailed_rules_pending": [
            "skills_assessment_exemptions",
            "age_exemptions",
            "competent_english",
            "dependent_functional_english",
            "nomination_validity",
            "salary_requirements",
        ],
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # One consolidated integrity check
    if not (
        len(de_sources) == 4
        and len(de_sections) == 12
        and len(de_evidence) == 12
        and len(de_policies) == 12
        and len(de_steps) == 5
    ):
        raise ValueError("186 Direct Entry count mismatch")

    if any(
        left["end_line"] + 1 != right["start_line"]
        for left, right in zip(de_sections, de_sections[1:])
    ):
        raise ValueError("186 Direct Entry section gap")

    if len({
        p["policy_id"] for p in de_policies
    }) != 12:
        raise ValueError("186 duplicate policy IDs")

    if any(
        p["eligibility_rule"] is not None
        or p["approved_for_eligibility_decision"] is not False
        for p in de_policies
    ):
        raise ValueError("186 unapproved executable rules")

    de_output = Path(
        "data/processed/australia/employment/"
        "subclass_186_direct_entry_evidence_draft.json"
    )

    de_output.parent.mkdir(parents=True, exist_ok=True)
    de_output.write_text(
        de_json.dumps(de_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== 186 DIRECT ENTRY ===")
    print("SOURCE TABS:", len(de_sources))
    print("ELIGIBILITY SECTIONS:", len(de_sections))
    print("EVIDENCE:", len(de_evidence))
    print("POLICY CANDIDATES:", len(de_policies))
    print("APPLICATION STEPS:", len(de_steps))
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", de_output)

    # =========================================================
    # 186 Temporary Residence Transition Stream
    # =========================================================
    import hashlib as trt_hashlib
    import json as trt_json
    from pathlib import Path as TRTPath

    trt_prefix = "subclass_186_trt"
    trt_raw_dir = TRTPath("data/raw/australia/employment")
    trt_output = TRTPath(
        "data/processed/australia/employment/"
        "subclass_186_trt_evidence_draft.json"
    )
    trt_url = (
        "https://immi.homeaffairs.gov.au/visas/"
        "getting-a-visa/visa-listing/"
        "employer-nomination-scheme-186/"
        "temporary-residence-transition-stream"
    )

    trt_tabs = [
        "about_this_visa",
        "eligibility",
        "step_by_step",
        "when_you_have_this_visa",
    ]

    trt_sources = {}
    trt_lines = {}
    trt_contents = {}

    # 1. 공식 원문 로드
    for tab in trt_tabs:
        path = trt_raw_dir / f"{trt_prefix}_{tab}.txt"
        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")

        if len(content) <= 1000:
            raise ValueError(f"186 TRT source too short: {tab}")

        if any(
            marker in content.lower()
            for marker in ("<!doctype", "<html", "<script")
        ):
            raise ValueError(f"186 TRT HTML source detected: {tab}")

        trt_contents[tab] = content
        trt_lines[tab] = content.splitlines()

        trt_sources[tab] = {
            "source_file": path.as_posix(),
            "source_url": trt_url,
            "source_sha256": trt_hashlib.sha256(raw).hexdigest(),
            "char_count": len(content),
            "review_status": "needs_review",
        }

    if len(set(trt_contents.values())) != 4:
        raise ValueError("186 TRT duplicate source tabs")

    # 2. Eligibility 원문에서 확인된 13개 제목
    trt_headings = [
        ("required_skills", "Have the required skills"),
        (
            "eligible_sponsored_employment",
            "Have 2 years eligible sponsored employment in the "
            "3 years prior to your application",
        ),
        (
            "licensing_registration",
            "Licensing, registration or membership",
        ),
        (
            "last_sponsoring_employer_nomination",
            "Be nominated by the employer who sponsored "
            "your temporary work visa",
        ),
        ("eligible_business", "Eligible business"),
        ("age", "Be this age"),
        ("english_language", "Have this level of English language"),
        ("qualifying_visa", "Have this visa"),
        ("health", "Meet our health requirement"),
        ("character", "Meet our character requirement"),
        (
            "australian_values_statement",
            "Sign the Australian values statement",
        ),
        (
            "government_debt",
            "Have paid back your debt to the Australian government",
        ),
        (
            "immigration_history",
            "Not have had a visa cancelled or a previous application refused",
        ),
    ]

    eligibility_lines = trt_lines["eligibility"]
    trt_positions = []

    for topic, heading in trt_headings:
        matches = [
            i for i, line in enumerate(eligibility_lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"186 TRT heading mismatch: {heading}: {matches}"
            )

        trt_positions.append(matches[0])

    if trt_positions != sorted(trt_positions):
        raise ValueError("186 TRT eligibility heading order mismatch")

    end_matches = [
        i for i, line in enumerate(eligibility_lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(end_matches) != 1:
        raise ValueError("186 TRT eligibility footer mismatch")

    eligibility_end = end_matches[0]

    if eligibility_end <= trt_positions[-1]:
        raise ValueError("186 TRT eligibility boundary error")

    # 3. Evidence 및 정책 후보 추출
    trt_sections = []
    trt_evidence = []
    trt_policies = []

    for index, (topic, heading) in enumerate(trt_headings):
        start = trt_positions[index]
        end = (
            trt_positions[index + 1]
            if index + 1 < len(trt_positions)
            else eligibility_end
        )

        source_text = "\n".join(
            eligibility_lines[start:end]
        ).strip()

        if (
            not source_text.startswith(heading)
            or len(source_text) <= len(heading)
        ):
            raise ValueError(f"186 TRT invalid section: {heading}")

        section_id = f"AU_186_TRT_ELIG_{index + 1:02d}"

        trt_sections.append({
            "section_id": section_id,
            "topic": topic,
            "heading": heading,
            "source_tab": "eligibility",
            "start_line": start + 1,
            "end_line": end,
            "original_text": source_text,
            "source_sha256": trt_sources[
                "eligibility"
            ]["source_sha256"],
            "review_status": "needs_review",
        })

        trt_evidence.append({
            "evidence_id": f"AU_186_TRT_EVD_{index + 1:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "exact_quote": source_text,
            "start_line": start + 1,
            "end_line": end,
            "review_status": "needs_review",
        })

        trt_policies.append({
            "policy_id": f"AU_186_TRT_POL_{index + 1:02d}",
            "program": trt_prefix,
            "topic": topic,
            "source_section_id": section_id,
            "source_text": source_text,
            "requirement_type": "needs_review",
            "exception_review_status": "needs_review",
            "eligibility_rule": None,
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    # 4. 신청 절차 Step 1~5
    step_lines = trt_lines["step_by_step"]
    step_positions = []

    for number in range(1, 6):
        matches = [
            i for i, line in enumerate(step_lines)
            if line.strip() == f"Step {number}"
        ]

        if len(matches) != 1:
            raise ValueError(
                f"186 TRT Step {number} mismatch: {matches}"
            )

        step_positions.append(matches[0])

    if step_positions != sorted(step_positions):
        raise ValueError("186 TRT application step order mismatch")

    footer_candidates = [
        i
        for i in range(step_positions[-1] + 1, len(step_lines))
        if step_lines[i].strip().startswith((
            "pop-up content starts",
            "Tell us what you think of this page",
            "Last updated:",
        ))
    ]

    step_end = (
        min(footer_candidates)
        if footer_candidates
        else len(step_lines)
    )

    trt_steps = []

    for index, start in enumerate(step_positions):
        end = (
            step_positions[index + 1]
            if index + 1 < len(step_positions)
            else step_end
        )

        trt_steps.append({
            "step_number": index + 1,
            "source_tab": "step_by_step",
            "start_line": start + 1,
            "end_line": end,
            "original_text": "\n".join(
                step_lines[start:end]
            ).strip(),
            "review_status": "needs_review",
        })

    # 5. 세부 조건 및 예외 검토 대상
    trt_conditional_requirements = {
        "employment_period": {
            "source_topic": "eligible_sponsored_employment",
            "review_points": [
                "two_years_within_three_years",
                "full_time_employment",
                "employment_in_australia",
                "qualifying_visa_during_employment",
                "approved_occupation",
                "multiple_457_or_482_visas",
                "employer_changes",
            ],
        },
        "age": {
            "source_topic": "age",
            "review_points": [
                "under_45_general_requirement",
                "academic_exemption",
                "scientist_exemption",
                "regional_medical_practitioner_exemption",
                "high_income_exemption",
                "subclass_457_transitional_arrangements",
            ],
        },
        "visa_status": {
            "source_topic": "qualifying_visa",
            "review_points": [
                "subclass_457",
                "subclass_482",
                "eligible_bridging_visa",
                "last_substantive_visa",
            ],
        },
        "employer_nomination": {
            "source_topic": "last_sponsoring_employer_nomination",
            "review_points": [
                "last_sponsoring_employer",
                "lawfully_operating_business",
                "six_month_nomination_window",
                "nomination_withdrawal",
                "position_availability",
            ],
        },
        "english": {
            "source_topic": "english_language",
            "review_points": [
                "competent_english",
                "no_english_exemption_since_2019_11_16",
            ],
        },
    }

    for group in trt_conditional_requirements.values():
        group["review_status"] = "needs_review"
        group["eligibility_rule"] = None

    # 6. 최종 JSON
    trt_result = {
        "program": trt_prefix,
        "visa_subclass": "186",
        "stream": "temporary_residence_transition",
        "pathway_type": "permanent_employment",
        "official_sources": trt_sources,
        "eligibility_sections": trt_sections,
        "evidence": trt_evidence,
        "policy_candidates": trt_policies,
        "application_steps": trt_steps,
        "conditional_requirements": trt_conditional_requirements,
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # 7. 저장 전 통합 검사
    if not (
        len(trt_sources) == 4
        and len(trt_sections) == 13
        and len(trt_evidence) == 13
        and len(trt_policies) == 13
        and len(trt_steps) == 5
    ):
        raise ValueError("186 TRT count mismatch")

    if any(
        left["end_line"] + 1 != right["start_line"]
        for left, right in zip(trt_sections, trt_sections[1:])
    ):
        raise ValueError("186 TRT eligibility section gap")

    if any(
        p["eligibility_rule"] is not None
        or p["approved_for_eligibility_decision"]
        for p in trt_policies
    ):
        raise ValueError("186 TRT unapproved executable policy")

    trt_output.parent.mkdir(parents=True, exist_ok=True)
    trt_output.write_text(
        trt_json.dumps(
            trt_result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== 186 TEMPORARY RESIDENCE TRANSITION ===")
    print("SOURCE TABS:", len(trt_sources))
    print("ELIGIBILITY SECTIONS:", len(trt_sections))
    print("EVIDENCE:", len(trt_evidence))
    print("POLICY CANDIDATES:", len(trt_policies))
    print("APPLICATION STEPS:", len(trt_steps))
    print(
        "CONDITIONAL GROUPS:",
        len(trt_conditional_requirements),
    )
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", trt_output)

    # =========================================================
    # 186 Labour Agreement Stream
    # =========================================================
    import hashlib as la186_hashlib
    import json as la186_json
    from pathlib import Path as LA186Path

    la186_prefix = "subclass_186_labour_agreement"
    la186_raw_dir = LA186Path("data/raw/australia/employment")
    la186_output = LA186Path(
        "data/processed/australia/employment/"
        "subclass_186_labour_agreement_evidence_draft.json"
    )

    la186_url = (
        "https://immi.homeaffairs.gov.au/visas/"
        "getting-a-visa/visa-listing/"
        "employer-nomination-scheme-186/"
        "labour-agreement-stream"
    )

    la186_tabs = [
        "about_this_visa",
        "eligibility",
        "step_by_step",
        "when_you_have_this_visa",
    ]

    la186_sources = {}
    la186_lines = {}
    la186_contents = {}

    # 1. Load and validate the four official source tabs
    for tab in la186_tabs:
        path = la186_raw_dir / f"{la186_prefix}_{tab}.txt"
        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")

        if len(content) <= 1000:
            raise ValueError(f"186 LA source too short: {tab}")

        if any(
            marker in content.lower()
            for marker in ("<!doctype", "<html", "<script")
        ):
            raise ValueError(f"186 LA HTML source detected: {tab}")

        if not any(
            line.strip().lower() == "labour agreement stream"
            for line in content.splitlines()
        ):
            raise ValueError(f"186 LA wrong visa stream: {tab}")

        la186_contents[tab] = content
        la186_lines[tab] = content.splitlines()

        la186_sources[tab] = {
            "source_file": path.as_posix(),
            "source_url": la186_url,
            "source_sha256": la186_hashlib.sha256(raw).hexdigest(),
            "char_count": len(content),
            "review_status": "needs_review",
        }

    if len(set(la186_contents.values())) != 4:
        raise ValueError("186 LA duplicate source tabs")

    # 2. Eligibility headings confirmed against the source
    la186_headings = [
        (
            "labour_agreement_employment",
            "Be working under a labour agreement",
        ),
        (
            "licensing_registration",
            "Licensing, registration or membership",
        ),
        ("employer_nomination", "Be nominated"),
        ("age", "Be this age"),
        ("qualifying_visa", "Have this visa"),
        ("health", "Meet our health requirement"),
        ("character", "Meet our character requirement"),
        (
            "australian_values_statement",
            "Sign the Australian values statement",
        ),
        (
            "government_debt",
            "Have paid back your debt to the Australian government",
        ),
        (
            "immigration_history",
            "Not have had a visa cancelled or a previous application refused",
        ),
    ]

    la186_elig_lines = la186_lines["eligibility"]
    la186_positions = []

    for topic, heading in la186_headings:
        matches = [
            i for i, line in enumerate(la186_elig_lines)
            if line.strip() == heading
        ]

        if len(matches) != 1:
            raise ValueError(
                f"186 LA eligibility heading mismatch: "
                f"{heading}: {matches}"
            )

        la186_positions.append(matches[0])

    if la186_positions != sorted(la186_positions):
        raise ValueError("186 LA eligibility heading order mismatch")

    la186_end_matches = [
        i for i, line in enumerate(la186_elig_lines)
        if line.strip().startswith("Meet all these criteria?")
    ]

    if len(la186_end_matches) != 1:
        raise ValueError("186 LA eligibility footer mismatch")

    la186_elig_end = la186_end_matches[0]

    if la186_elig_end <= la186_positions[-1]:
        raise ValueError("186 LA invalid eligibility boundary")

    # 3. Extract evidence and policy candidates
    la186_sections = []
    la186_evidence = []
    la186_policies = []

    for index, (topic, heading) in enumerate(la186_headings):
        start = la186_positions[index]
        end = (
            la186_positions[index + 1]
            if index + 1 < len(la186_positions)
            else la186_elig_end
        )

        original_text = "\n".join(
            la186_elig_lines[start:end]
        ).strip()

        if (
            not original_text.startswith(heading)
            or len(original_text) <= len(heading)
        ):
            raise ValueError(
                f"186 LA invalid eligibility section: {heading}"
            )

        section_id = f"AU_186_LA_ELIG_{index + 1:02d}"

        la186_sections.append({
            "section_id": section_id,
            "topic": topic,
            "heading": heading,
            "source_tab": "eligibility",
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "source_sha256": la186_sources[
                "eligibility"
            ]["source_sha256"],
            "review_status": "needs_review",
        })

        la186_evidence.append({
            "evidence_id": f"AU_186_LA_EVD_{index + 1:02d}",
            "source_section_id": section_id,
            "source_tab": "eligibility",
            "exact_quote": original_text,
            "start_line": start + 1,
            "end_line": end,
            "review_status": "needs_review",
        })

        la186_policies.append({
            "policy_id": f"AU_186_LA_POL_{index + 1:02d}",
            "program": la186_prefix,
            "topic": topic,
            "source_section_id": section_id,
            "source_text": original_text,
            "requirement_type": "needs_review",
            "agreement_variation": "needs_review",
            "exception_review_status": "needs_review",
            "eligibility_rule": None,
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        })

    # 4. Preserve application steps 1 through 5
    la186_step_lines = la186_lines["step_by_step"]
    la186_step_positions = []

    for number in range(1, 6):
        matches = [
            i for i, line in enumerate(la186_step_lines)
            if line.strip() == f"Step {number}"
        ]

        if len(matches) != 1:
            raise ValueError(
                f"186 LA Step {number} mismatch: {matches}"
            )

        la186_step_positions.append(matches[0])

    if la186_step_positions != sorted(la186_step_positions):
        raise ValueError("186 LA application step order mismatch")

    la186_footer_candidates = [
        i
        for i in range(
            la186_step_positions[-1] + 1,
            len(la186_step_lines),
        )
        if la186_step_lines[i].strip().startswith((
            "pop-up content starts",
            "Tell us what you think of this page",
            "Last updated:",
        ))
    ]

    la186_step_end = (
        min(la186_footer_candidates)
        if la186_footer_candidates
        else len(la186_step_lines)
    )

    la186_steps = []

    for index, start in enumerate(la186_step_positions):
        end = (
            la186_step_positions[index + 1]
            if index + 1 < len(la186_step_positions)
            else la186_step_end
        )

        original_text = "\n".join(
            la186_step_lines[start:end]
        ).strip()

        if not original_text.startswith(f"Step {index + 1}"):
            raise ValueError(
                f"186 LA empty application step: {index + 1}"
            )

        la186_steps.append({
            "step_number": index + 1,
            "source_tab": "step_by_step",
            "start_line": start + 1,
            "end_line": end,
            "original_text": original_text,
            "review_status": "needs_review",
        })

    # 5. Agreement-specific conditions requiring legal review
    la186_agreement_conditions = {
        "occupation_and_skills": {
            "source_topic": "labour_agreement_employment",
            "review_points": [
                "agreement_covered_position",
                "suitable_skills_and_qualifications",
                "skills_assessment_if_requested",
            ],
        },
        "work_experience": {
            "source_topic": "labour_agreement_employment",
            "review_points": [
                "experience_required_by_specific_agreement",
                "experience_concessions_if_applicable",
            ],
        },
        "english": {
            "source_topic": "labour_agreement_employment",
            "review_points": [
                "english_level_defined_by_agreement",
                "english_concessions_if_applicable",
            ],
        },
        "age": {
            "source_topic": "age",
            "review_points": [
                "general_under_45_rule",
                "agreement_specific_age_variation",
            ],
        },
        "employer_nomination": {
            "source_topic": "employer_nomination",
            "review_points": [
                "lawfully_operating_business",
                "employer_party_to_labour_agreement",
                "nomination_validity",
                "adverse_information",
                "position_availability",
            ],
        },
        "qualifying_visa": {
            "source_topic": "qualifying_visa",
            "review_points": [
                "in_australia_application",
                "substantive_457_or_482",
                "visa_issued_under_labour_agreement",
            ],
        },
        "salary_and_employment_terms": {
            "source_topic": "employer_nomination",
            "review_points": [
                "agreement_specific_salary_conditions",
                "applicable_income_thresholds",
                "employment_terms",
            ],
        },
    }

    for group in la186_agreement_conditions.values():
        group["review_status"] = "needs_review"
        group["eligibility_rule"] = None

    # 6. Consolidated output
    la186_result = {
        "program": la186_prefix,
        "visa_subclass": "186",
        "stream": "labour_agreement",
        "pathway_type": "permanent_employment",
        "official_sources": la186_sources,
        "eligibility_sections": la186_sections,
        "evidence": la186_evidence,
        "policy_candidates": la186_policies,
        "application_steps": la186_steps,
        "agreement_specific_requirements": la186_agreement_conditions,
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # 7. Integrity checks before saving
    if not (
        len(la186_sources) == 4
        and len(la186_sections) == 10
        and len(la186_evidence) == 10
        and len(la186_policies) == 10
        and len(la186_steps) == 5
        and len(la186_agreement_conditions) == 7
    ):
        raise ValueError("186 LA data count mismatch")

    if any(
        left["end_line"] + 1 != right["start_line"]
        for left, right in zip(la186_sections, la186_sections[1:])
    ):
        raise ValueError("186 LA eligibility section gap")

    if len({
        item["policy_id"] for item in la186_policies
    }) != 10:
        raise ValueError("186 LA duplicate policy IDs")

    if any(
        item["eligibility_rule"] is not None
        or item["approved_for_eligibility_decision"]
        for item in la186_policies
    ):
        raise ValueError("186 LA unapproved executable rule")

    # 8. Save draft JSON
    la186_output.parent.mkdir(parents=True, exist_ok=True)
    la186_output.write_text(
        la186_json.dumps(
            la186_result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== 186 LABOUR AGREEMENT ===")
    print("SOURCE TABS:", len(la186_sources))
    print("ELIGIBILITY SECTIONS:", len(la186_sections))
    print("EVIDENCE:", len(la186_evidence))
    print("POLICY CANDIDATES:", len(la186_policies))
    print("APPLICATION STEPS:", len(la186_steps))
    print(
        "AGREEMENT REVIEW GROUPS:",
        len(la186_agreement_conditions),
    )
    print("STATUS: CANDIDATES_NEED_REVIEW")
    print("SAVED:", la186_output)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # =========================================================
    # CSOL + Mandatory Skills Assessment source structuring
    # =========================================================
    import re

    csol_path = RAW / "core_skills_occupation_list_official.txt"
    skills_path = (
        RAW
        / "subclass_482_mandatory_skills_assessment_immi_18_039.txt"
    )

    csol_bytes = csol_path.read_bytes()
    skills_bytes = skills_path.read_bytes()

    csol_text = csol_bytes.decode("utf-8-sig")
    skills_text = skills_bytes.decode("utf-8-sig")

    # CSOL: row number + six-digit ANZSCO + occupation
    csol_matches = re.findall(
        r"(?m)^\s*(\d{1,3})\s+(\d{6})\s+([^\r\n]+)",
        csol_text,
    )

    occupations = [
        {
            "list_number": int(number),
            "anzsco_code": code,
            "occupation_title": title.strip(),
            "source_id": "AU_CSOL_OFFICIAL",
            "review_status": "needs_review",
        }
        for number, code, title in csol_matches
    ]

    numbers = [x["list_number"] for x in occupations]
    codes = [x["anzsco_code"] for x in occupations]

    if len(occupations) != 456:
        raise ValueError(
            f"CSOL occupation count mismatch: {len(occupations)}"
        )

    if numbers != list(range(1, 457)):
        raise ValueError("CSOL row numbering mismatch")

    if len(set(codes)) != 456:
        raise ValueError("Duplicate CSOL ANZSCO code")

    # IMMI 18/039: Section 5 occupation / assessing authority
    # Extract candidates, but do not infer mandatory assessment.
    section5_matches = re.findall(
        r"(?m)^\s*(\d{1,2})\s+(.+?)\s+"
        r"(\d{6})\s+(TRA|VETASSESS)\b",
        skills_text,
        re.IGNORECASE,
    )

    # PDF의 줄바꿈으로 잘린 직업명을 원문에 맞춰 복원
    ASSESSMENT_TITLE_CORRECTIONS = {
        16: "metal fitters and machinists (nec)",
        17: "metal machinist (first class)",
        21: "program or project administrator",
    }

    assessment_occupations = [
        {
            "item_number": int(number),
            "occupation_title": ASSESSMENT_TITLE_CORRECTIONS.get(
                    int(number), title.strip()
                ),
            "anzsco_code": code,
            "assessing_authority": authority.upper(),
            "source_id": "AU_482_IMMI_18_039",
            "mandatory_for_all_applicants": False,
            "applicability_review_status": "needs_review",
        }
        for number, title, code, authority in section5_matches
    ]

    skills_lines = skills_text.splitlines()

    def extract_legal_section(start_heading, end_heading=None):
        starts = [
            i for i, line in enumerate(skills_lines)
            if line.strip() == start_heading
        ]

        if len(starts) != 1:
            raise ValueError(
                f"Section heading mismatch: {start_heading}: "
                f"{len(starts)}"
            )

        start = starts[0]

        if end_heading is None:
            end = len(skills_lines)
        else:
            ends = [
                i for i in range(start + 1, len(skills_lines))
                if skills_lines[i].strip() == end_heading
            ]

            if len(ends) != 1:
                raise ValueError(
                    f"Section end mismatch: {end_heading}"
                )
            end = ends[0]

        return {
            "heading": start_heading,
            "start_line": start + 1,
            "end_line": end,
            "original_text": "\n".join(
                skills_lines[start:end]
            ).strip(),
            "review_status": "needs_review",
        }

    section6 = extract_legal_section(
        "6 Specification of classes of persons",
        "7 Exempt applicant for an occupation",
    )

    section7 = extract_legal_section(
        "7 Exempt applicant for an occupation"
    )

    result["occupation_list"] = {
        "source_id": "AU_CSOL_OFFICIAL",
        "source_file": csol_path.as_posix(),
        "source_sha256": hashlib.sha256(
            csol_bytes
        ).hexdigest(),
        "source_pdf": (
            RAW / "core_skills_occupation_list_official.pdf"
        ).as_posix(),
        "occupation_count": len(occupations),
        "occupations": occupations,
        "review_status": "needs_review",
    }

    result["mandatory_skills_assessment"] = {
        "source_id": "AU_482_IMMI_18_039",
        "source_file": skills_path.as_posix(),
        "source_sha256": hashlib.sha256(
            skills_bytes
        ).hexdigest(),
        "source_pdf": (
            RAW
            / "subclass_482_mandatory_skills_assessment_immi_18_039.pdf"
        ).as_posix(),
        "legal_instrument": "IMMI 18/039",
        "compilation_date": "2024-12-14",
        "assessment_occupation_candidates": assessment_occupations,
        "section6_applicant_classes": section6,
        "section7_exemptions": section7,
        "nationality_conditions_structured": False,
        "exemption_rules_structured": False,
        "review_status": "needs_review",
        "legal_validation_approved": False,
        "approved_for_eligibility_decision": False,
    }

    # Combined structural checks before overwriting the draft
    if not assessment_occupations:
        raise ValueError("No skills assessment occupations parsed")

    assessment_numbers = [
        x["item_number"] for x in assessment_occupations
    ]

    if len(assessment_numbers) != len(set(assessment_numbers)):
        raise ValueError("Duplicate assessment item numbers")

    # 확보한 공식 PDF에는 22번 다음에 24번이 등장한다.
    # 23번을 임의로 생성하지 않고 별도 검토 대상으로 기록한다.
    expected_assessment_numbers = [
        *range(1, 23),
        24,
        25,
    ]

    if sorted(assessment_numbers) != expected_assessment_numbers:
        raise ValueError(
            "Assessment item numbering mismatch: "
            f"{sorted(assessment_numbers)}"
        )

    # Item 23 was repealed by LIN 24/094,
    # Schedule 1, items 6 and 8, effective 2024-12-07.
    result["mandatory_skills_assessment"][
        "unresolved_source_item_numbers"
    ] = []

    result["mandatory_skills_assessment"][
        "repealed_source_items"
    ] = [{
        "item_number": 23,
        "status": "repealed",
        "effective_date": "2024-12-07",
        "amending_instrument": "LIN 24/094",
        "amendment_reference": "Schedule 1, items 6 and 8",
        "official_url": (
            "https://www.legislation.gov.au/F2024L01621/latest"
        ),
        "verification_status": "official_source_confirmed",
    }]

    result["mandatory_skills_assessment"][
        "source_item_gap_review_status"
    ] = "resolved_by_amendment"

    print("ASSESSMENT ITEMS: 24 ACTIVE ENTRIES")
    print("REPEALED SOURCE ITEM: 23")

    if not section6["original_text"] or not section7["original_text"]:
        raise ValueError("Empty legal section")

    print("=== CSOL AND SKILLS ASSESSMENT ===")
    print("CSOL OCCUPATIONS:", len(occupations))
    print("UNIQUE ANZSCO:", len(set(codes)))
    print(
        "ASSESSMENT OCCUPATION CANDIDATES:",
        len(assessment_occupations),
    )
    print("ASSESSMENT ITEMS:", assessment_numbers)
    print(
        "SECTION 6 LENGTH:",
        len(section6["original_text"]),
    )
    print(
        "SECTION 7 LENGTH:",
        len(section7["original_text"]),
    )
    print("POLICY STATUS: needs_review")

    print("SAVED:", OUT)
    print("STATUS: CANDIDATES_NEED_REVIEW")


if __name__ == "__main__":
    main()
    try:
        from .review_support import refresh_reviews
    except ImportError:
        from review_support import refresh_reviews
    refresh_reviews(programs=["subclass_482_core_skills","subclass_482_specialist_skills","subclass_482_labour_agreement","subclass_186_direct_entry","subclass_186_labour_agreement","subclass_186_trt"])

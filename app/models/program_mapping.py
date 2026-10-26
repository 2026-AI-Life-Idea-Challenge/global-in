
from typing import Any

from app.models.program import Country


PROGRAM_ALIASES = {
    "japan": {
        "jp_working_holiday": "JP-WH-01",
    },
    "usa": {
        "US-EM-01": "US-WK-01",
        "US-EM-04": "US-WK-02",
    },
}

COUNTRY_PREFIXES = {
    "australia": "AU",
    "germany": "DE",
    "canada": "CA",
}


def get_source_program_id(
    country: Country,
    data: dict[str, Any],
) -> str | None:
    """원본 JSON에서 프로그램 식별자를 추출한다."""

    if country in ("japan", "usa"):
        value = (
            data.get("program_id")
            or data.get("team_reference_program_id")
        )
    else:
        value = data.get("program")

    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None


def normalize_program_id(
    country: Country,
    source_program_id: str,
) -> str:
    """국가별 원본 프로그램 ID를 공통 ID로 정규화한다."""

    source_program_id = source_program_id.strip()

    if not source_program_id:
        raise ValueError("source_program_id cannot be empty")

    aliases = PROGRAM_ALIASES.get(country, {})

    if source_program_id in aliases:
        return aliases[source_program_id]

    if country in ("japan", "usa"):
        return source_program_id

    prefix = COUNTRY_PREFIXES[country]

    if source_program_id.startswith(f"{prefix}:"):
        return source_program_id

    return f"{prefix}:{source_program_id}"



def classify_artifact_roles(
    data: dict[str, Any],
) -> list[str]:
    """원본 JSON의 자료 역할을 보수적으로 분류한다.

    역할 분류는 데이터 사용 승인 또는 법적 검증을 의미하지 않는다.
    """

    roles: list[str] = []
    dataset_type = str(data.get("dataset_type") or "").lower()

    def add(role: str) -> None:
        if role not in roles:
            roles.append(role)

    # 1. 검토·감사 전용 산출물
    # 명시적인 자료 유형을 우선한다.
    if dataset_type and (
        "audit" in dataset_type
        or "review_report" in dataset_type
        or "validation_report" in dataset_type
        or "review_summary" in dataset_type
        or "triage_summary" in dataset_type
    ):
        return ["review_artifact"]

    # 2. 검색 인덱스 및 검색 품질 자료
    if dataset_type == "usa_retrieval_dataset_index":
        return ["retrieval_artifact"]

    # 3. 서류 및 서류별 근거
    if isinstance(data.get("documents"), (list, dict)):
        add("document_requirement")

    if (
        data.get("parent_document_id")
        and data.get("source_row_number") is not None
    ):
        add("document_evidence")

    # 4. 명시적 Evidence 컬렉션
    evidence_keys = {
        "evidence",
        "evidence_records",
        "embassy_evidence",
        "shared_requirement_evidence",
        "country_specific_evidence",
    }

    if any(
        isinstance(data.get(key), (list, dict))
        for key in evidence_keys
    ):
        add("source_evidence")

    # 5. 미국 공식 Evidence의 sections 구조
    sections = data.get("sections")
    if isinstance(sections, list) and any(
        isinstance(item, dict)
        and "evidence_id" in item
        for item in sections
    ):
        add("source_evidence")
    elif isinstance(sections, list):
        add("source_content")

    # 6. 공식 원문 및 출처 묶음
    sources = data.get("sources")
    if isinstance(sources, list) and any(
        isinstance(item, dict)
        and (
            "evidence_blocks" in item
            or "body_text" in item
        )
        for item in sources
    ):
        add("source_evidence")

    if isinstance(data.get("source"), dict) and isinstance(
        sections, list
    ):
        add("source_content")

    if dataset_type in {
        "official_pdf_text",
        "australia_official_visa_text_draft",
    }:
        add("source_archive")

    # 7. 정책 후보와 검토 중인 정책 레코드
    if (
        "policy_candidates" in data
        or "candidate_records" in data
    ):
        add("policy_candidate")

    if "policy_records" in data:
        add("policy_review")

    # 8. 자격 요건 초안
    if "requirements" in data:
        add("eligibility_draft")

    # 9. 프로그램 상세 정보
    detail_keys = {
        "application_dates",
        "application_method",
        "application_location",
        "programme_overview",
        "visa_validity",
        "post_entry",
        "work_conditions",
        "eligibility",
        "application",
        "fee_records",
        "agencies",
        "useful_information",
    }

    if any(key in data for key in detail_keys):
        add("program_detail")

    if dataset_type in {
        "program_information_draft",
        "west_full_reviewed_information",
    }:
        add("program_detail")

    # 10. 별도 근거·검토 산출물
    if "legal_reference_records" in data:
        add("legal_reference")

    if "review_items" in data or "review_queue" in data:
        add("review_artifact")

    if "validation" in data or "checks" in data:
        add("review_artifact")

    if not roles:
        add("unclassified")

    return roles


def deduplicate_documents(
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Document ID를 기준으로 동일 서류의 중복을 방지한다.

    같은 ID에 내용이 다른 레코드가 존재하면 자동 병합하지 않는다.
    """

    unique_documents: dict[str, dict[str, Any]] = {}

    for document in documents:
        document_id = document.get("document_id")

        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("Document ID is missing or invalid")

        document_id = document_id.strip()

        if document_id not in unique_documents:
            unique_documents[document_id] = document
            continue

        existing = unique_documents[document_id]

        if existing != document:
            raise ValueError(
                f"Conflicting document records: {document_id}"
            )

    return list(unique_documents.values())

def extract_program_display_name(
    country: Country,
    data: dict[str, Any],
) -> str | None:
    """원본에서 명시적으로 제공된 프로그램 표시명만 추출한다.

    프로그램 식별자, 경로 유형, 카테고리를
    공식 표시명으로 자동 변환하지 않는다.
    """

    name_fields = ["program_name", "programme_name", "visa_or_residence_title"]

    if country == "japan":
        name_fields.append("status_of_residence")

    for field in name_fields:
        value = data.get(field)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return None

def create_program_from_json(
    country: Country,
    data: dict[str, Any],
    source_file: str,
    display_name: str | None = None,
):
    """원본 JSON을 공통 Program 모델로 변환한다.

    표시명과 프로그램 ID가 확인되지 않으면 생성하지 않는다.
    정책 검토 및 서비스 사용 승인 상태는 변경하지 않는다.
    """
    from app.models.program import Program

    source_program_id = get_source_program_id(country, data)

    if source_program_id is None:
        raise ValueError(
            f"Missing source program ID: {source_file}"
        )

    program_id = normalize_program_id(
        country,
        source_program_id,
    )

    name = display_name

    if name is None:
        name = extract_program_display_name(country, data)

    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            f"Missing verified display name: {program_id}"
        )

    if not isinstance(source_file, str) or not source_file.strip():
        raise ValueError("source_file is required")

    def optional_string(field: str) -> str | None:
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    return Program(
        program_id=program_id,
        country=country,
        name=name.strip(),
        category=None,
        route_id=optional_string("route_id"),
        visa_subclass=optional_string("visa_subclass"),
        stream=optional_string("stream"),
        source_program_id=source_program_id,
        source_file=source_file.strip(),
        review_status="needs_review",
        metadata={},
    )

def collect_program_name_candidates(
    country: Country,
    sources: list[tuple[str, dict[str, Any]]],
) -> dict[str, dict[str, list[str]]]:
    """원본 파일별 프로그램 표시명 후보를 수집한다.

    동일 프로그램의 서로 다른 표시명을 자동 병합하거나
    대표 이름으로 확정하지 않는다.
    """

    result: dict[str, dict[str, list[str]]] = {}

    for source_file, data in sources:
        source_program_id = get_source_program_id(country, data)

        if source_program_id is None:
            continue

        program_id = normalize_program_id(
            country,
            source_program_id,
        )

        name = extract_program_display_name(country, data)

        if name is None:
            continue

        program_names = result.setdefault(program_id, {})
        source_files = program_names.setdefault(name, [])

        if source_file not in source_files:
            source_files.append(source_file)

    return result

def resolve_program_display_name(
    program_id: str,
    name_candidates: dict[str, dict[str, list[str]]],
) -> str | None:
    """원본에서 추출된 프로그램명 후보를 안전하게 판정한다.

    후보가 없으면 None을 반환한다.
    후보가 하나면 해당 이름을 반환한다.
    서로 다른 이름이 여러 개면 자동 선택하지 않는다.
    """

    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id is required")

    variants = name_candidates.get(program_id, {})

    names = sorted(
        name.strip()
        for name in variants
        if isinstance(name, str) and name.strip()
    )

    if not names:
        return None

    if len(names) > 1:
        raise ValueError(
            f"Conflicting program display names: "
            f"{program_id} -> {names}"
        )

    return names[0]

# 원본 JSON에서 직접 추출할 수 없는 프로그램명을
# 별도 검증 후 등록하기 위한 매핑.
#
# key: 정규화된 프로그램 ID
# value: 출처를 확인한 표시명
#
# 확인되지 않은 이름은 등록하지 않는다.
VERIFIED_PROGRAM_DISPLAY_NAMES: dict[str, str] = {
    "AU:subclass_186_direct_entry": (
        "Employer Nomination Scheme visa (subclass 186)"
        " — Direct Entry stream"
    ),
    "AU:subclass_186_labour_agreement": (
        "Employer Nomination Scheme visa (subclass 186)"
        " — Labour Agreement stream"
    ),
    "AU:subclass_186_trt": (
        "Employer Nomination Scheme visa (subclass 186)"
        " — Temporary Residence Transition stream"
    ),
    "AU:subclass_189_points_tested": (
        "Skilled Independent visa (subclass 189)"
        " — Points-tested stream"
    ),
    "AU:subclass_190": (
        "Skilled Nominated visa (subclass 190)"
    ),
    "AU:subclass_491": (
        "Skilled Work Regional (Provisional) visa (subclass 491)"
    ),
        "AU:subclass_191_regional_provisional": (
        "Permanent Residence (Skilled Regional) visa (subclass 191)"
        " — Regional Provisional stream"
    ),
        "AU:subclass_494_employer_sponsored": (
        "Skilled Employer Sponsored Regional (Provisional)"
        " visa (subclass 494) — Employer Sponsored stream"
    ),
    "AU:subclass_494_labour_agreement": (
        "Skilled Employer Sponsored Regional (Provisional)"
        " visa (subclass 494) — Labour Agreement stream"
    ),
        "AU:subclass_407": "Training visa (subclass 407)",
    "AU:subclass_482_core_skills": (
        "Skills in Demand visa (subclass 482) — Core Skills stream"
    ),
    "AU:subclass_482_specialist_skills": (
        "Skills in Demand visa (subclass 482) — Specialist Skills stream"
    ),
    "AU:subclass_482_labour_agreement": (
        "Skills in Demand visa (subclass 482) — Labour Agreement stream"
    ),
    "AU:subclass_500": "Student visa (subclass 500)",
    "AU:subclass_417_first": (
        "Working Holiday visa (subclass 417) — First Working Holiday visa"
    ),
    "AU:subclass_417_second": (
        "Working Holiday visa (subclass 417) — Second Working Holiday visa"
    ),
    "AU:subclass_417_third": (
        "Working Holiday visa (subclass 417) — Third Working Holiday visa"
    ),
    "AU:subclass_462_first": (
        "Work and Holiday visa (subclass 462) — First Work and Holiday visa"
    ),
    "AU:subclass_462_second": (
        "Work and Holiday visa (subclass 462) — Second Work and Holiday visa"
    ),
    "AU:subclass_462_third": (
        "Work and Holiday visa (subclass 462) — Third Work and Holiday visa"
    ),
    # Germany — Employment
    "DE:eu_blue_card": "EU Blue Card",
    "DE:opportunity_card": "Opportunity Card (Chancenkarte)",
    "DE:skilled_worker": "Visa for Qualified Professionals",

    # Germany — Study
    "DE:study_visa": "Visa for Studying",
    "DE:seeking_higher_education_place": "Visa for Seeking a Place in Higher Education",

    # Germany — Working Holiday
    "DE:working_holiday": "Working Holiday Visa",
    # Canada — Employment
    "CA:employer_specific_work_permit": "Employer-specific Work Permit",
    "CA:post_graduation_work_permit": "Post-Graduation Work Permit (PGWP)",

    # Canada — Study
    "CA:study_permit": "Study Permit",

    # Canada — Working Holiday
    "CA:iec_working_holiday": "International Experience Canada (IEC) — Working Holiday",
        # Japan
    "JP:JP-EM-01": "Engineer / Specialist in Humanities / International Services",
    "JP:JP-ST-01": "Student (留学)",
    "JP:JP-WH-01": "Japan Working Holiday",

    # United States
    "US:US-EM-01": "H-1B Specialty Occupations",
    "US:US-EM-02": "BridgeUSA J-1 Intern",
    "US:US-EM-03": "BridgeUSA J-1 Trainee",
    "US:US-WEST-01": "WEST Program",
    "US:US-ST-01": "F-1 Academic Student",
    "US:US-ST-03": "BridgeUSA J-1 College and University Student",
    "US:US-WH-01": "BridgeUSA J-1 Summer Work Travel",
}


def get_verified_program_display_name(
    program_id: str,
) -> str | None:
    """별도로 확인된 프로그램 표시명을 반환한다."""

    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id is required")

    return VERIFIED_PROGRAM_DISPLAY_NAMES.get(program_id.strip())

# 표시명의 공식 출처를 추적하기 위한 별도 매핑.
# VERIFIED_PROGRAM_DISPLAY_NAMES와 같은 program_id를 사용한다.
#
# 예시:
# "프로그램 ID": {
#     "source_url": "확인한 공식 URL",
#     "source_title": "공식 페이지 제목",
# }
#
# 출처를 실제 확인하기 전에는 등록하지 않는다.
PROGRAM_DISPLAY_NAME_SOURCES: dict[str, dict[str, str]] = {
    "AU:subclass_186_direct_entry": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "employer-nomination-scheme-186/direct-entry-stream"
        ),
        "source_title": (
            "Employer Nomination Scheme visa (subclass 186)"
            " Direct Entry stream"
        ),
    },
    "AU:subclass_186_labour_agreement": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "employer-nomination-scheme-186/labour-agreement-stream"
        ),
        "source_title": (
            "Employer Nomination Scheme (subclass 186)"
            " Labour Agreement stream"
        ),
    },
    "AU:subclass_186_trt": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "employer-nomination-scheme-186/"
            "temporary-residence-transition-stream"
        ),
        "source_title": (
            "Employer Nomination Scheme (subclass 186)"
            " Temporary Residence Transition stream"
        ),
    },
        "AU:subclass_189_points_tested": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "skilled-independent-189/points-tested"
        ),
        "source_title": (
            "Skilled Independent visa (subclass 189)"
            " Points-tested stream"
        ),
    },
        "AU:subclass_190": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "skilled-nominated-190"
        ),
        "source_title": (
            "Skilled Nominated visa (subclass 190)"
        ),
    },
        "AU:subclass_491": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "skilled-work-regional-provisional-491"
        ),
        "source_title": (
            "Skilled Work Regional (Provisional)"
            " visa (subclass 491)"
        ),
    },
        "AU:subclass_191_regional_provisional": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "skilled-regional-191/regional-provisional"
        ),
        "source_title": (
            "Permanent Residence (Skilled Regional)"
            " visa (subclass 191)"
            " Regional Provisional stream"
        ),
    },
        "AU:subclass_494_employer_sponsored": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "skilled-employer-sponsored-regional-494/"
            "employer-sponsored-stream"
        ),
        "source_title": (
            "Skilled Employer Sponsored Regional (Provisional)"
            " visa (subclass 494) Employer Sponsored stream"
        ),
    },
    "AU:subclass_494_labour_agreement": {
        "source_url": (
            "https://immi.homeaffairs.gov.au/visas/"
            "getting-a-visa/visa-listing/"
            "skilled-employer-sponsored-regional-494/"
            "labour-agreement-stream"
        ),
        "source_title": (
            "Skilled Employer Sponsored Regional (Provisional)"
            " visa (subclass 494) Labour Agreement stream"
        ),
    },
        "AU:subclass_407": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/training-407",
        "source_title": "Training visa (subclass 407)",
    },
    "AU:subclass_482_core_skills": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skills-in-demand-visa-subclass-482/core-skills-stream",
        "source_title": "Skills in Demand visa (subclass 482) Core Skills stream",
    },
    "AU:subclass_482_specialist_skills": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skills-in-demand-visa-subclass-482/specialist-skills-stream",
        "source_title": "Skills in Demand visa (subclass 482) Specialist Skills stream",
    },
    "AU:subclass_482_labour_agreement": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skills-in-demand-visa-subclass-482/labour-agreement-stream",
        "source_title": "Skills in Demand visa (subclass 482) Labour Agreement stream",
    },
    "AU:subclass_500": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500",
        "source_title": "Student visa (subclass 500)",
    },
    "AU:subclass_417_first": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417/first-working-holiday-417",
        "source_title": "Working Holiday visa (subclass 417) First Working Holiday visa",
    },
    "AU:subclass_417_second": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417/second-working-holiday-417",
        "source_title": "Working Holiday visa (subclass 417) Second Working Holiday visa",
    },
    "AU:subclass_417_third": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-417/third-working-holiday-417",
        "source_title": "Working Holiday visa (subclass 417) Third Working Holiday visa",
    },
    "AU:subclass_462_first": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462/first-work-holiday-462",
        "source_title": "Work and Holiday visa (subclass 462) First Work and Holiday visa",
    },
    "AU:subclass_462_second": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462/second-work-holiday-462",
        "source_title": "Work and Holiday visa (subclass 462) Second Work and Holiday visa",
    },
    "AU:subclass_462_third": {
        "source_url": "https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/work-holiday-462/third-work-and-holiday-462",
        "source_title": "Work and Holiday visa (subclass 462) Third Work and Holiday visa",
    },
        # Germany — Employment
    "DE:eu_blue_card": {
        "source_url": "https://www.make-it-in-germany.com/en/visa-residence/types/eu-blue-card",
        "source_title": "EU Blue Card",
    },
    "DE:opportunity_card": {
        "source_url": "https://www.make-it-in-germany.com/en/visa-recognition/opportunity-card/job-search",
        "source_title": "Opportunity Card",
    },
    "DE:skilled_worker": {
        "source_url": "https://www.make-it-in-germany.com/en/visa-residence/types/work-qualified-professionals",
        "source_title": "Visa for Qualified Professionals",
    },

    # Germany — Study
    "DE:study_visa": {
        "source_url": "https://www.make-it-in-germany.com/en/visa-residence/types/studying",
        "source_title": "Visa for Studying",
    },
    "DE:seeking_higher_education_place": {
        "source_url": "https://www.make-it-in-germany.com/en/visa-residence/types/studying",
        "source_title": "Visa for Seeking a Place in Higher Education",
    },

    # Germany — Working Holiday
    "DE:working_holiday": {
        "source_url": "https://seoul.diplo.de/kr-ko/service/1694216-1694216",
        "source_title": "Working Holiday Visa",
    },
        # Canada — Employment
    "CA:employer_specific_work_permit": {
        "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/employer-specific.html",
        "source_title": "Employer-specific Work Permit",
    },
    "CA:post_graduation_work_permit": {
        "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html",
        "source_title": "Post-Graduation Work Permit — Eligibility",
    },

    # Canada — Study
    "CA:study_permit": {
        "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/eligibility.html",
        "source_title": "Study Permit — Eligibility",
    },

    # Canada — Working Holiday
    "CA:iec_working_holiday": {
        "source_url": "https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility.html?selection=kr-wh",
        "source_title": "International Experience Canada — Working Holiday",
    },
        # Japan
    "JP:JP-EM-01": {
        "source_url": "https://www.moj.go.jp/isa/content/001437255.pdf",
        "source_title": "Engineer / Specialist in Humanities / International Services — Change of Status Documents",
    },
    "JP:JP-ST-01": {
        "source_url": "https://www.moj.go.jp/isa/content/001463585.pdf",
        "source_title": "Student — Certificate of Eligibility Documents",
    },
    "JP:JP-WH-01": {
        "source_url": "https://www.kr.emb-japan.go.jp/itpr_ko/visa_working.html",
        "source_title": "Japan Working Holiday — Embassy of Japan in Korea",
    },

    # United States
    "US:US-EM-01": {
        "source_url": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
        "source_title": "H-1B Specialty Occupations — USCIS",
    },
    "US:US-EM-02": {
        "source_url": "https://j1visa.state.gov/programs/intern/",
        "source_title": "BridgeUSA — Intern",
    },
    "US:US-EM-03": {
        "source_url": "https://j1visa.state.gov/programs/trainee/",
        "source_title": "BridgeUSA — Trainee",
    },
    "US:US-WEST-01": {
        "source_url": "https://www.niied.go.kr/web/main/nid/niied_board/5570",
        "source_title": "WEST Program — National Institute for International Education",
    },
    "US:US-ST-01": {
        "source_url": "https://studyinthestates.dhs.gov/school-search",
        "source_title": "Study in the States — School Search",
    },
    "US:US-ST-03": {
        "source_url": "https://j1visa.state.gov/programs/college-and-university-student/",
        "source_title": "BridgeUSA — College and University Student",
    },
    "US:US-WH-01": {
        "source_url": "https://j1visa.state.gov/programs/summer-work-travel/",
        "source_title": "BridgeUSA — Summer Work Travel",
    },
}


def validate_program_display_name_registry() -> list[str]:
    """표시명과 출처 매핑 사이의 구조적 오류를 검사한다."""

    errors: list[str] = []

    for program_id, name in VERIFIED_PROGRAM_DISPLAY_NAMES.items():
        if not isinstance(name, str) or not name.strip():
            errors.append(f"Invalid display name: {program_id}")
            continue

        source = PROGRAM_DISPLAY_NAME_SOURCES.get(program_id)

        if not isinstance(source, dict):
            errors.append(f"Missing name source: {program_id}")
            continue

        source_url = source.get("source_url")
        source_title = source.get("source_title")

        if not isinstance(source_url, str) or not source_url.strip():
            errors.append(f"Missing source URL: {program_id}")

        if not isinstance(source_title, str) or not source_title.strip():
            errors.append(f"Missing source title: {program_id}")

    for program_id in PROGRAM_DISPLAY_NAME_SOURCES:
        if program_id not in VERIFIED_PROGRAM_DISPLAY_NAMES:
            errors.append(f"Orphan name source: {program_id}")

    return errors

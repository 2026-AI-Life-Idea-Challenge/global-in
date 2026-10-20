# 신청 절차 5개 섹션의 공식 원문, 프로그램 ID, 출처 메타데이터 저장


import json, re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag


# 프로젝트 루트 기준 입출력 경로
INPUT_PATH = Path("data/raw/japan/working_holiday/japan_working_holiday_embassy.html")
OUTPUT_PATH = Path("data/raw/japan/working_holiday/japan_working_holiday_application.json")

SOURCE_URL = (
    "https://www.kr.emb-japan.go.jp/"
    "itpr_ko/visa_working.html"
)

# 공식 페이지에 표시된 문서 날짜
PAGE_DISPLAY_DATE = "2026-09-30"

SECTION_FIELDS = {
    "(1)": "application_method",
    "(2)": "required_documents_guidance",
    "(3)": "application_period",
    "(4)": "application_location",
    "(5)": "result_notification",
}


def extract_section_text(heading: Tag) -> str:
    """다음 제목이 나오기 전까지 해당 섹션의 원문만 추출한다."""
    parts = []

    for element in heading.next_elements:
        # 다음 섹션 또는 상위 제목에서 중단
        if isinstance(element, Tag) and element.name in (
            "h1", "h2", "h3"
        ):
            break

        if not isinstance(element, NavigableString):
            continue

        # 제목, CSS, JavaScript 등의 텍스트 제외
        if element.find_parent(
            ["h1", "h2", "h3", "script", "style"]
        ):
            continue

        text = str(element).strip()

        if text:
            parts.append(text)

    return " ".join(parts)


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"HTML 파일 없음: {INPUT_PATH}")

    soup = BeautifulSoup(
        INPUT_PATH.read_text(encoding="utf-8"),
        "html.parser",
    )

    sections = []

    for heading in soup.find_all("h3"):
        title = heading.get_text(" ", strip=True)

        for prefix, field in SECTION_FIELDS.items():
            if not title.startswith(prefix):
                continue

            original_text = extract_section_text(heading)

            if not original_text:
                raise ValueError(f"원문 추출 실패: {title}")

            sections.append({
                "field": field,
                "heading": title,
                "original_text": original_text,
                "validation_status": "needs_review",
            })
            break

    # 예상한 다섯 섹션을 모두 추출했는지 확인
    extracted_fields = [s["field"] for s in sections]

    if len(sections) != 5 or set(extracted_fields) != set(
        SECTION_FIELDS.values()
    ):
        raise ValueError(
            f"신청수속 섹션 누락 또는 중복: {extracted_fields}"
        )

    structured_dates = structure_application_dates(sections)
    structured_method = structure_application_method(sections)
    structured_location = structure_application_location(sections)
    structured_notification = structure_result_notification(sections)
    structured_document_guidance = structure_document_guidance(sections)

    result = {
        "route_id": "JP-WH",
        "program_id": "JP-WH-01",
        "target_nationality": "KR",
        "data_type": "application",
        "source": {
            "official_agency": "Embassy of Japan in Korea",
            "source_url": SOURCE_URL,
            "page_display_date": PAGE_DISPLAY_DATE,
            "collection_mode": "manual",
            "extracted_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "verified_at": None,
            "source_license": None,
            "needs_verification": True,
        },
        "sections": sections,
        "structured_dates": structured_dates,
        "structured_method": structured_method,
        "structured_location": structured_location,
        "structured_notification": structured_notification,
        "structured_document_guidance": structured_document_guidance,
        "validation_status": "needs_review",
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 52-1 저장 결과 =====")
    print("파일:", OUTPUT_PATH)
    print("섹션 수:", len(sections))
    print("검증 상태:", result["validation_status"])
    print("JSON 저장: 성공")


# 날짜 구조화 함수
def structure_application_dates(sections: list[dict]) -> dict:
    """신청기간과 심사결과 발표일을 공식 원문에서 추출한다."""

    # 섹션 이름을 키로 변환하여 필요한 원문에 접근
    section_by_field = {
        section["field"]: section["original_text"]
        for section in sections
    }

    period_text = section_by_field["application_period"]
    result_text = section_by_field["result_notification"]

    # 신청기간: 2026년 / 제4사분기 / 10월 12~16일
    year_match = re.search(r"(\d{4})년의 신청기간", period_text)
    period_match = re.search(
        r"제\s*(\d+)사분기\s*(\d+)월\s*(\d+)일\([^)]+\)부터\s*(\d+)일\([^)]+\)까지",
        period_text,
    )

    # 심사결과: 제4사분기 / 11월 24일
    result_match = re.search(
        r"제\s*(\d+)사분기\s*(\d+)월\s*(\d+)일\([^)]+\)",
        result_text,
    )

    # 원문 형식이 바뀌면 잘못된 날짜를 저장하지 않고 중단
    if not all([year_match, period_match, result_match]):
        raise ValueError("공식 원문에서 신청기간 또는 발표일을 찾지 못했습니다.")

    year = int(year_match.group(1))
    quarter = int(period_match.group(1))
    month = int(period_match.group(2))
    start_day = int(period_match.group(3))
    end_day = int(period_match.group(4))

    result_quarter = int(result_match.group(1))
    result_month = int(result_match.group(2))
    result_day = int(result_match.group(3))

    if quarter != result_quarter or not 1 <= quarter <= 4:
        raise ValueError("신청기간과 결과 발표일의 분기 정보가 일치하지 않습니다.")

    # 실제 달력에 존재하는 날짜인지 검증
    from datetime import date

    start_date = date(year, month, start_day)
    end_date = date(year, month, end_day)
    announcement_date = date(year, result_month, result_day)

    if start_date > end_date or end_date > announcement_date:
        raise ValueError("신청기간과 결과 발표일의 시간 순서가 올바르지 않습니다.")

    return {
        "application_period": {
            "year": year,
            "quarter": quarter,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "original_text": period_text,
            "validation_status": "needs_review",
        },
        "result_announcement": {
            "year": year,
            "quarter": result_quarter,
            "announcement_date": announcement_date.isoformat(),
            "original_text": result_text,
            "validation_status": "needs_review",
        },
    }


# 지정 여행업자를 통한 신청, 개인·우편 신청 제한, 중복 신청 무효를 데이터로 저장하는 함수
def structure_application_method(sections: list[dict]) -> dict:
    """대사관 공식 원문에서 신청 방법과 제한 사항을 구조화한다."""

    # 저장된 섹션 중 신청방법 원문 찾기
    section_by_field = {
        section["field"]: section["original_text"]
        for section in sections
    }

    original_text = section_by_field["application_method"]

    # 원문 표현이 변경되었을 때 잘못된 규칙을 저장하지 않도록 검사
    required_phrases = [
        "지정 여행업자",
        "개인 신청이나 우편에 의한 신청은 접수하지 않으므로",
        "복수 신청은 모두 무효처리",
    ]

    missing = [
        phrase for phrase in required_phrases
        if phrase not in original_text
    ]

    if missing:
        raise ValueError(
            f"신청방법 공식 원문 변경 또는 누락: {missing}"
        )

    return {
        "submission_channel": "designated_travel_agency",
        "individual_embassy_submission_allowed": False,
        "postal_submission_allowed": False,
        "multiple_applications_allowed": False,

        # 지정 여행업자의 구체적인 목록은 아직 수집하지 않음
        "designated_agencies": None,

        # 현재 저장된 대사관 페이지 기준의 규칙
        "original_text": original_text,
        "validation_status": "needs_review",
    }

# 서울·부산·제주 관할 공관 구조화(주민등록상 주소에 따른 관할 공관 구조화) 함수

def structure_application_location(sections: list[dict]) -> dict:
    """주민등록상 주소에 따른 관할 일본 공관을 구조화한다."""

    section_by_field = {
        section["field"]: section["original_text"]
        for section in sections
    }

    original_text = section_by_field["application_location"]

    # 공식 원문이 변경되면 잘못된 관할 규칙을 저장하지 않도록 검사
    required_phrases = [
        "주민등록상 주소",
        "주대한민국일본국대사관 영사부",
        "주부산일본국총영사관",
        "주제주일본국총영사관",
        "부산광역시",
        "대구광역시",
        "울산광역시",
        "제주특별자치도",
    ]

    missing = [
        phrase for phrase in required_phrases
        if phrase not in original_text
    ]

    if missing:
        raise ValueError(f"관할 공관 공식 원문 확인 실패: {missing}")

    # 경상남도·경상북도는 공식 문서에서 축약하거나 개별 표기할 수 있음
    gyeongsang_valid = (
        "경상남ㆍ북도" in original_text
        or (
            "경상남도" in original_text
            and "경상북도" in original_text
        )
    )

    if not gyeongsang_valid:
        raise ValueError("경상남도·경상북도 관할 표기 확인 실패")

    return {
        "address_basis": "resident_registration_address",
        "jurisdictions": [
            {
                "office_id": "JP_EMBASSY_KR",
                "office_name": "주대한민국일본국대사관 영사부",
                "regions": [],
                "region_match": "all_except_other_jurisdictions",
            },
            {
                "office_id": "JP_CONSULATE_BUSAN",
                "office_name": "주부산일본국총영사관",
                "regions": [
                    "부산광역시",
                    "대구광역시",
                    "울산광역시",
                    "경상남도",
                    "경상북도",
                ],
                "region_match": "in_list",
            },
            {
                "office_id": "JP_CONSULATE_JEJU",
                "office_name": "주제주일본국총영사관",
                "regions": ["제주특별자치도"],
                "region_match": "in_list",
            },
        ],
        "original_text": original_text,
        "validation_status": "needs_review",
    }

# 심사결과 알림 구조화 함수
def structure_result_notification(sections: list[dict]) -> dict:
    """심사결과 통지 방식과 최종 발급 유의사항을 구조화한다."""

    section_by_field = {
        section["field"]: section["original_text"]
        for section in sections
    }

    original_text = section_by_field["result_notification"]

    # 공식 원문에 필요한 문구가 실제 존재하는지 확인
    required_phrases = [
        "심사결과는 홈페이지에 게시",
        "전화로의 문의에는 답하지 않습니다",
        "최종심사",
        "사증이 발급되지 않습니다",
    ]

    missing = [
        phrase for phrase in required_phrases
        if phrase not in original_text
    ]

    if missing:
        raise ValueError(
            f"심사결과 알림 원문 확인 실패: {missing}"
        )

    return {
        "notification_channel": "official_website",
        "telephone_inquiry_supported": False,

        # 홈페이지 발표 이후에도 최종 발급 심사가 남아 있음
        "announcement_guarantees_visa_issuance": False,
        "final_review_required": True,

        # 발표일은 structured_dates에서 별도로 관리
        "announcement_date_field": (
            "structured_dates.result_announcement.announcement_date"
        ),

        "original_text": original_text,
        "validation_status": "needs_review",
    }

# 제출서류 주의사항 구조화 함수

def structure_document_guidance(sections: list[dict]) -> dict:
    """공식 원문에 기재된 제출서류 공통 주의사항을 구조화한다."""

    section_by_field = {
        section["field"]: section["original_text"]
        for section in sections
    }

    original_text = section_by_field["required_documents_guidance"]

    # 원문에 주요 제출 주의사항이 존재하는지 확인
    required_phrases = [
        "각 자료가 누락되지 않게",
        "스테이플러로 서류를 묶지 마시고",
        "여권 원본과 같도록 사본의 크기를 변경하지 마시고",
        "여권 인적 사항 내용이 명확하게 보이도록",
    ]

    missing = [
        phrase for phrase in required_phrases
        if phrase not in original_text
    ]

    if missing:
        raise ValueError(
            f"제출서류 주의사항 원문 확인 실패: {missing}"
        )

    return {
        "check_missing_documents_before_submission": True,
        "stapled_documents_allowed": False,
        "submit_documents_as_separate_sheets": True,
        "passport_copy": {
            "resize_allowed": False,
            "personal_information_must_be_legible": True,
            "related_document_id": "JP_WH_DOC_010",
        },
        "related_documents_dataset": (
            "japan_working_holiday_documents_structured.json"
        ),
        "original_text": original_text,
        "validation_status": "needs_review",
    }


if __name__ == "__main__":
    main()
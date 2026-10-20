
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup


# 기존에 저장한 일본 대사관 공식 HTML
INPUT_PATH = Path(
    "data/raw/japan/working_holiday/japan_working_holiday_embassy.html"
)

# 사증 유효기간 구조화 결과
OUTPUT_PATH = Path(
    "data/processed/japan/working_holiday/japan_working_holiday_visa_validity_structured.json"
)

SOURCE_URL = (
    "https://www.kr.emb-japan.go.jp/itpr_ko/visa_working.html"
)


def extract_official_text(soup: BeautifulSoup) -> str:
    """사증 유효기간을 설명하는 공식 문단을 추출한다."""

    candidates = [
        text
        for text in soup.stripped_strings
        if "사증 발급일로부터 1년간 유효한 단수 입국사증" in text
    ]

    if len(candidates) != 1:
        raise ValueError(
            f"사증 유효기간 원문 확인 필요: {len(candidates)}건"
        )

    return candidates[0]


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"HTML 파일 없음: {INPUT_PATH}")

    soup = BeautifulSoup(
        INPUT_PATH.read_text(encoding="utf-8"),
        "html.parser",
    )

    original_text = extract_official_text(soup)

    # 원문의 각 정책 요소를 저장 전에 확인
    required_phrases = [
        "사증 발급일로부터 1년간 유효한 단수 입국사증",
        "1회당 1년간의 체류",
        "최대 2회",
        "체류 기간 연장은 허용되지 않습니다",
    ]

    for phrase in required_phrases:
        if phrase not in original_text:
            raise ValueError(f"공식 원문 확인 필요: {phrase}")

    result = {
        "route_id": "JP-WH",
        "program_id": "JP-WH-01",
        "target_nationality": "KR",
        "data_type": "visa_validity",

        "source": {
            "official_agency": "Embassy of Japan in Korea",
            "source_url": SOURCE_URL,
            "collection_mode": "manual",
            "extracted_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "verified_at": None,
            "source_license": None,
            "needs_verification": True,
        },

        "visa_validity": {
            # 사증 발급일 기준 유효기간
            "validity_years": 1,
            "validity_start_event": "visa_issuance_date",

            # 단수 입국사증
            "entry_type": "single_entry",

            # 일본 입국 후 1회당 체류기간
            "stay_duration_years": 1,

            # 기존 JP_WH_004에도 저장된 참여 횟수
            "maximum_participations": 2,
            "related_eligibility_rule_id": "JP_WH_004",

            # 일본 내 체류기간 연장 불가
            "stay_extension_allowed": False,

            # 모든 구조화 값에 대한 공식 원문
            "evidence_text": original_text,
            "validation_status": "needs_review",
        },

        "original_text": original_text,
        "validation_status": "needs_review",
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 58-5 사증 유효기간 구조화 =====")
    print("파일:", OUTPUT_PATH)
    print("원문 길이:", len(original_text))
    print("사증 유효기간: 발급일로부터 1년")
    print("입국 형태: 단수")
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()

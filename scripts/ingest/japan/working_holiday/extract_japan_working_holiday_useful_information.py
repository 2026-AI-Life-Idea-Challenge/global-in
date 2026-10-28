
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag


INPUT_PATH = Path("data/raw/japan/working_holiday/japan_working_holiday.html")

OUTPUT_PATH = Path(
    "data/raw/japan/working_holiday/japan_working_holiday_useful_information.json"
)

SOURCE_URL = "https://www.mofa.go.jp/j_info/visit/w_holiday/"
PAGE_DISPLAY_DATE = "2026-04-01"

SECTION_TITLE = "Other useful information"

# 공식 본문의 마지막 문장.
# HTML의 마지막 섹션이어서 푸터가 따라오는 문제를 방지하는 안전장치.
END_MARKER = "We would appreciate your cooperation in this regard."


def extract_section(soup: BeautifulSoup) -> str:
    """공식 섹션의 본문을 추출하고 사이트 푸터를 제외한다."""

    heading = next(
        (
            h for h in soup.find_all(["h1", "h2", "h3"])
            if SECTION_TITLE in h.get_text(" ", strip=True)
        ),
        None,
    )

    if heading is None:
        raise ValueError("Other useful information 섹션을 찾지 못했습니다.")

    parts = []

    for element in heading.next_elements:
        # 다음 제목이나 푸터 영역을 만나면 추출 중단
        if isinstance(element, Tag):
            if element.name in ("h1", "h2", "h3", "footer"):
                break

            if element.get("id") in (
                "footer",
                "footer-sitemaps",
            ):
                break

        if not isinstance(element, NavigableString):
            continue

        # 제목, 스크립트, 푸터 내부 텍스트 제외
        if element.find_parent(
            ["h1", "h2", "h3", "script", "style", "footer"]
        ):
            continue

        text = str(element).strip()

        if text:
            parts.append(text)

    extracted_text = " ".join(parts)

    # 정제 단계에서 검증한 공식 본문 종료 문구 확인
    if extracted_text.count(END_MARKER) != 1:
        raise ValueError("본문 종료 문구가 변경되었거나 누락되었습니다.")

    # 현재 저장된 HTML에서 검증된 본문 범위까지만 보존
    original_text = (
        extracted_text.split(END_MARKER, 1)[0] + END_MARKER
    )

    return original_text


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"HTML 파일 없음: {INPUT_PATH}")

    soup = BeautifulSoup(
        INPUT_PATH.read_text(encoding="utf-8"),
        "html.parser",
    )

    original_text = extract_section(soup)

    # 참고 정보 3가지의 핵심 근거 검사
    required_phrases = [
        "fraudulent entities",
        "Employment Service Centre for Foreigners",
        "Hello Work",
        "questionnaire",
    ]

    missing = [
        phrase
        for phrase in required_phrases
        if phrase.lower() not in original_text.lower()
    ]

    if missing:
        raise ValueError(f"공식 원문 누락: {missing}")

    # 푸터가 다시 포함되지 않았는지 검증
    if "Page Top" in original_text or "Copyright" in original_text:
        raise ValueError("불필요한 푸터가 포함되었습니다.")

    result = {
        "route_id": "JP-WH",
        "program_id": "JP-WH-01",
        "target_nationality": "KR",
        "data_type": "useful_information",
        "source": {
            "official_agency": "Ministry of Foreign Affairs of Japan",
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
        "original_text": original_text,
        "validation_status": "needs_review",
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 56-4 Raw JSON 저장 =====")
    print("파일:", OUTPUT_PATH)
    print("원문 길이:", len(original_text))
    print("검토 상태:", result["validation_status"])
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()

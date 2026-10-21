
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag


# 수동 저장한 일본 외무성 공식 HTML
INPUT_PATH = Path("data/raw/japan/working_holiday/japan_working_holiday.html")

# 추출된 원문을 저장할 파일
OUTPUT_PATH = Path(
    "data/raw/japan/working_holiday/japan_working_holiday_post_entry.json"
)

SOURCE_URL = "https://www.mofa.go.jp/j_info/visit/w_holiday/"
PAGE_DISPLAY_DATE = "2026-04-01"


def extract_official_section(soup: BeautifulSoup, heading_phrase: str) -> str:
    """Return the same heading-bounded source text as the original extractors.

    This helper neither rewrites original text nor infers policy meaning.
    """
    heading = next(
        (h for h in soup.find_all(["h1", "h2", "h3"])
         if heading_phrase in h.get_text(" ", strip=True)),
        None,
    )
    if heading is None:
        raise ValueError(f"공식 원문 섹션을 찾지 못했습니다: {heading_phrase}")

    parts = []
    for element in heading.next_elements:
        if isinstance(element, Tag) and element.name in ("h1", "h2", "h3"):
            break
        if not isinstance(element, NavigableString):
            continue
        if element.find_parent(["h1", "h2", "h3", "script", "style"]):
            continue
        text = str(element).strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def extract_post_entry(soup: BeautifulSoup) -> str:
    """Preserved public interface for historical reproducibility."""
    return extract_official_section(soup, "Procedure at a municipal office")


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"HTML 파일 없음: {INPUT_PATH}")

    soup = BeautifulSoup(
        INPUT_PATH.read_text(encoding="utf-8"),
        "html.parser",
    )

    original_text = extract_post_entry(soup)

    # 정책 핵심 문구가 없으면 저장하지 않음
    required_phrases = [
        "municipal office where they live",
        "notify the Ministry of Justice",
        "within 14 days",
        "finding a place to settle down",
    ]

    missing = [
        phrase for phrase in required_phrases
        if phrase.lower() not in original_text.lower()
    ]

    if missing:
        raise ValueError(f"공식 원문 변경 또는 누락: {missing}")

    result = {
        "route_id": "JP-WH",
        "program_id": "JP-WH-01",
        "target_nationality": "KR",
        "data_type": "post_entry",
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

    # 최종 1회 저장
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 55-2 Raw JSON 저장 =====")
    print("파일:", OUTPUT_PATH)
    print("원문 길이:", len(original_text))
    print("검토 상태:", result["validation_status"])
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()

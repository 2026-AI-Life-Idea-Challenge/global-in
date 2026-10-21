
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag


# 수동 저장한 일본 외무성 공식 HTML
INPUT_PATH = Path("data/raw/japan/working_holiday/japan_working_holiday.html")

# 취업 제한 원문을 저장할 Raw JSON
OUTPUT_PATH = Path(
    "data/raw/japan/working_holiday/japan_working_holiday_work_conditions.json"
)

SOURCE_URL = "https://www.mofa.go.jp/j_info/visit/w_holiday/"
PAGE_DISPLAY_DATE = "2026-04-01"


# Reuse the original post-entry extractor module: no additional helper file.
from extract_japan_working_holiday_post_entry import extract_official_section


def extract_work_conditions(soup: BeautifulSoup) -> str:
    """Preserved public interface for historical reproducibility."""
    return extract_official_section(soup, "Work Conditions")


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"HTML 파일 없음: {INPUT_PATH}")

    soup = BeautifulSoup(
        INPUT_PATH.read_text(encoding="utf-8"),
        "html.parser",
    )

    original_text = extract_work_conditions(soup)

    # 핵심 문구가 없으면 잘못된 데이터를 저장하지 않도록 중단
    required_phrases = [
        "incidental activity",
        "supplementing their travel funds",
        "bars, cabarets, nightclubs",
        "gambling establishments",
        "deportation",
        "victim of human trafficking",
        "criminal charges",
    ]

    missing = [
        phrase for phrase in required_phrases
        if phrase.lower() not in original_text.lower()
    ]

    if missing:
        raise ValueError(f"공식 원문 누락 또는 변경: {missing}")

    result = {
        "route_id": "JP-WH",
        "program_id": "JP-WH-01",
        "target_nationality": "KR",
        "data_type": "work_conditions",
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

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 54-2 저장 결과 =====")
    print("파일:", OUTPUT_PATH)
    print("원문 길이:", len(original_text))
    print("검토 상태:", result["validation_status"])
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()

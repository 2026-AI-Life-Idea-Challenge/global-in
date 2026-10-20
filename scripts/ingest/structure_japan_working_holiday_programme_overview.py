
import json
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup


# 기존에 저장한 일본 외무성 공식 HTML
INPUT_PATH = Path("data/raw/japan_working_holiday.html")

# Global-In에서 사용할 프로그램 개요 데이터
OUTPUT_PATH = Path(
    "data/processed/"
    "japan_working_holiday_programme_overview_structured.json"
)

SOURCE_URL = "https://www.mofa.go.jp/j_info/visit/w_holiday/"
PAGE_DISPLAY_DATE = "2026-04-01"


def extract_korea_row(soup: BeautifulSoup) -> dict:
    """공식 국가별 표에서 South Korea 행을 정확하게 추출한다."""

    matches = []

    for row in soup.find_all("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all(["th", "td"], recursive=False)
        ]

        if "South Korea" in cells:
            matches.append((row, cells))

    # 국가명이 다른 위치에서 중복될 경우 잘못된 행 선택 방지
    if len(matches) != 1:
        raise ValueError(
            f"South Korea 행이 정확히 1개여야 합니다: {len(matches)}"
        )

    row, cells = matches[0]

    table = row.find_parent("table")
    if table is None:
        raise ValueError("국가별 공식 표를 찾지 못했습니다.")

    # HTML의 실제 표 헤더를 확인
    headers = [
        header.get_text(" ", strip=True)
        for header in table.find_all("th")
    ]

    expected_headers = [
        "",
        "Countries/regions",
        "Year of initiation",
        "Maximum number of visas issued per year",
    ]

    if headers != expected_headers:
        raise ValueError(f"표 헤더 변경 확인 필요: {headers}")

    if len(cells) != 4:
        raise ValueError(f"한국 행의 열 개수 확인 필요: {cells}")

    row_number, country, initiation_year, annual_cap = cells

    if not (
        row_number.isdigit()
        and country == "South Korea"
        and initiation_year.isdigit()
        and annual_cap.replace(",", "").isdigit()
    ):
        raise ValueError(f"한국 행 값 확인 필요: {cells}")

    return {
        "partner_country": country,
        "year_of_initiation": int(initiation_year),
        "annual_visa_cap": int(annual_cap.replace(",", "")),
        "annual_visa_cap_type": "maximum_issued_per_year",
        "source_row": cells,
        "source_headers": headers,
    }


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"HTML 파일 없음: {INPUT_PATH}")

    soup = BeautifulSoup(
        INPUT_PATH.read_text(encoding="utf-8"),
        "html.parser",
    )

    korea = extract_korea_row(soup)

    result = {
        "route_id": "JP-WH",
        "program_id": "JP-WH-01",
        "target_nationality": "KR",
        "data_type": "programme_overview",
        "source": {
            "official_agency": "Ministry of Foreign Affairs of Japan",
            "source_url": SOURCE_URL,
            "page_display_date": PAGE_DISPLAY_DATE,
            "collection_mode": "manual",
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "verified_at": None,
            "source_license": None,
            "needs_verification": True,
        },
        "programme_overview": {
            "partner_country": korea["partner_country"],
            "year_of_initiation": korea["year_of_initiation"],
            "annual_visa_cap": korea["annual_visa_cap"],
            "annual_visa_cap_type": korea["annual_visa_cap_type"],
            "as_of_date": PAGE_DISPLAY_DATE,

            # 표의 실제 원문을 보존하여 근거 추적
            "source_headers": korea["source_headers"],
            "source_row": korea["source_row"],

            # 발급 상한을 개인의 자격 판정 규칙으로 사용하지 않음
            "is_individual_eligibility_rule": False,
            "validation_status": "needs_review",
        },
        "validation_status": "needs_review",
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 57-3 프로그램 개요 구조화 =====")
    print("파일:", OUTPUT_PATH)
    print("국가:", korea["partner_country"])
    print("협정 개시 연도:", korea["year_of_initiation"])
    print("연간 발급 상한:", korea["annual_visa_cap"])
    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()


import json, pymupdf
import re
from datetime import datetime, timezone
from pathlib import Path


INPUT_PATH = Path(
    "data/raw/japan/working_holiday/japan_working_holiday_accredited_agencies.pdf"
)

OUTPUT_PATH = Path(
    "data/processed/japan/working_holiday/"
    "japan_working_holiday_accredited_agencies_structured.json"
)

SOURCE_URL = "https://www.kr.emb-japan.go.jp/files/100927276.pdf"
DOCUMENT_DATE = "2026-01-05"


def extract_lines(page):
    """PDF에서 텍스트와 실제 좌표를 함께 추출한다."""
    lines = []

    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = " ".join(
                span["text"] for span in line["spans"]
            ).strip()

            if text:
                lines.append({
                    "x": round(line["bbox"][0], 1),
                    "y": round(line["bbox"][1], 1),
                    "text": text,
                })

    return sorted(lines, key=lambda x: (x["y"], x["x"]))



def get_column(x, text):
    """좌표와 텍스트 형식을 함께 사용하여 표의 열을 구분한다."""

    # 전화번호는 일부 기관에서 주소 열에 가까운 위치에 배치됨.
    # 좌표만으로 분류하지 않고 전화번호 형태를 우선 확인한다.
    phone_pattern = (
        r"^(?:0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}"
        r"|1\d{3}[-\s]?\d{4})"
        r"(?:\([^)]*\)|~\d+)?$"
    )

    if re.match(phone_pattern, text):
        return "phone"

    # 나머지 항목은 PDF의 열 시작 위치를 기준으로 구분
    if 80 <= x < 160:
        return "name"

    if 160 <= x < 370:
        return "address"

    if 370 <= x < 430:
        return "phone"

    if 430 <= x < 595:
        return "language"

    return None


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(INPUT_PATH)

    with pymupdf.open(INPUT_PATH) as document:
        if len(document) != 1:
            raise ValueError("PDF 페이지 수 변경 확인 필요")

        lines = extract_lines(document[0])

    # 주소 열은 기관마다 한 개씩 존재하는 것을 확인했음
    address_lines = [
        line for line in lines
        if 160 <= line["x"] <= 175
        and 100 <= line["y"] < 775
    ]

    if len(address_lines) != 33:
        raise ValueError(
            f"주소 행 개수 변경 확인 필요: {len(address_lines)}"
        )

    # 각 기관의 주소 Y 좌표를 기준으로 행 경계 계산
    address_positions = [line["y"] for line in address_lines]

    boundaries = [97.0]

    for current, next_position in zip(
        address_positions,
        address_positions[1:],
    ):
        boundaries.append((current + next_position) / 2)

    # 마지막 기관 아래에는 대사관 면책 문구가 있음
    boundaries.append(775.0)

    agencies = []

    for index, address_line in enumerate(address_lines):
        start_y = boundaries[index]
        end_y = boundaries[index + 1]

        # 동일한 표 행에 속하는 텍스트만 수집
        row_lines = [
            line for line in lines
            if start_y <= line["y"] < end_y
        ]

        columns = {
            "name": [],
            "address": [],
            "phone": [],
            "language": [],
        }

        for line in row_lines:
            column = get_column(line["x"], line["text"])

            if column:
                columns[column].append(line)

        # 열 내부의 텍스트는 위에서 아래 순서로 정렬
        for key in columns:
            columns[key].sort(key=lambda x: x["y"])

        name_lines = [x["text"] for x in columns["name"]]
        address_texts = [x["text"] for x in columns["address"]]
        phones = [x["text"] for x in columns["phone"]]
        languages = [x["text"] for x in columns["language"]]

        # 한글이 포함된 이름과 그 외 이름을 구분한다.
        # JEC처럼 한글명이 없는 기관은 None으로 저장한다.
        korean_names = [
            name for name in name_lines
            if re.search(r"[가-힣]", name)
        ]

        other_names = [
            name for name in name_lines
            if not re.search(r"[가-힣]", name)
        ]

        if not name_lines:
            raise ValueError(f"{index + 1}번 기관명 누락")

        if len(address_texts) != 1:
            raise ValueError(
                f"{index + 1}번 주소 확인 필요: {address_texts}"
            )

        if not phones:
            raise ValueError(f"{index + 1}번 전화번호 누락")

        # 여러 영문명 줄을 원문 순서대로 보존
        agency = {
            "agency_id": f"JP_WH_AGENCY_{index + 1:03d}",
            "name_ko": " ".join(korean_names) if korean_names else None,
            "name_other": " ".join(other_names) if other_names else None,
            "address": address_texts[0],
            "phone_numbers": phones,
            "supported_languages_original": languages,
            "row_index": index + 1,
            "validation_status": "needs_review",
        }

        agencies.append(agency)

    result = {
        "route_id": "JP-WH",
        "program_id": "JP-WH-01",
        "target_nationality": "KR",
        "data_type": "accredited_agencies",
        "source": {
            "official_agency": "Embassy of Japan in Korea",
            "source_url": SOURCE_URL,
            "document_date": DOCUMENT_DATE,
            "collection_mode": "manual",
            "extracted_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "verified_at": None,
            "source_license": None,
            "needs_verification": True,
        },
        "agency_count": len(agencies),
        "agencies": agencies,
        "notes": {
            "language_field": (
                "PDF에 언어가 명시된 경우에만 기록. "
                "빈 배열은 지원 언어가 없다는 뜻이 아님."
            ),
            "agency_scope": (
                "주한일본대사관 지정 여행사 PDF 기준. "
                "모든 일본 공관의 신청 가능 기관을 뜻하지 않음."
            ),
            "disclaimer_ko": (
                "주한일본대사관은 비자 대리신청업체와 "
                "신청인 사이 계약상 분쟁에 법적 책임을 지지 않음."
            ),
        },
        "validation_status": "needs_review",
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("===== STEP 59-7 기관 데이터 구조화 =====")
    print("파일:", OUTPUT_PATH)
    print("기관 수:", result["agency_count"])

    # 다중 이름과 단일 이름을 갖는 기관 확인
    for agency in agencies:
        if agency["row_index"] in (16, 24, 25, 33):
            print(
                agency["agency_id"],
                agency["name_ko"],
                "/",
                agency["name_other"],
            )

    print("JSON 저장: 성공")


if __name__ == "__main__":
    main()

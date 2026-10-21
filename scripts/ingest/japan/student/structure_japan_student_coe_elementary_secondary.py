
import hashlib
import json
import re
from pathlib import Path

import pymupdf

from structure_japan_student_coe_documents import save_structured_json


PROJECT_ROOT = Path(__file__).resolve().parents[4]

PDF_PATH = (
    PROJECT_ROOT
    / "data/raw/japan/student/japan_student_coe_pdfs/001463593.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/japan/student/"
    "japan_student_coe_elementary_secondary_structured.json"
)

SOURCE_URL = "https://www.moj.go.jp/isa/content/001463593.pdf"

STATUS_MAP = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
}

EXPECTED_SYMBOLS = [
    "○", "△", "○", "○", "△",
    "△", "△", "○", "○", "△",
    "△", "△", "△", "△", "△",
    "△", "△", "△", "△", "△", "△",
]

# 비고 열이 여러 서류에 걸쳐 병합된 영역
MERGED_CONDITIONS = {
    (10, 11, 12, 13): (
        "高校に入学する場合であって、"
        "学生交換計画又はこれに準ずる"
        "国際交流計画を策定していない場合"
    ),
    (15, 16, 17): (
        "中学校又は小学校に入学する場合"
    ),
}

# 서류명 열에 조건이 함께 들어 있는 항목
INLINE_CONDITIONS = {
    5: "高校に入学する場合",
    18: "高校に特待生として入学する場合",
}


def get_boundaries(page):
    return sorted({
        round(item[1].y, 1)
        for drawing in page.get_drawings()
        for item in drawing["items"]
        if (
            item[0] == "l"
            and abs(item[1].y - item[2].y) < 1
            and abs(item[1].x - item[2].x) > 300
        )
    })


def get_row_bounds(boundaries, y):
    matches = [
        (low, high)
        for low, high in zip(
            boundaries,
            boundaries[1:],
        )
        if low <= y < high
    ]

    if len(matches) != 1:
        raise ValueError(
            f"행 경계 확인 실패: Y={y}"
        )

    return matches[0]


def extract_column_text(
    blocks,
    low,
    high,
    min_x,
    max_x,
):
    selected = sorted(
        [
            block
            for block in blocks
            if (
                min_x < block[0] < max_x
                and low <= block[1] < high
            )
        ],
        key=lambda block: block[1],
    )

    return "".join(
        block[4].strip().replace("\n", "")
        for block in selected
    )


def extract_documents(page):
    blocks = page.get_text("blocks")
    boundaries = get_boundaries(page)

    markers = []

    for block in blocks:
        match = re.match(
            r"^(\d+)\s*\n\s*([○△－])",
            block[4].strip(),
        )

        if 195 < block[0] < 215 and match:
            markers.append({
                "number": int(match.group(1)),
                "symbol": match.group(2),
                "y": block[1],
            })

    markers.sort(key=lambda item: item["number"])

    numbers = [
        marker["number"]
        for marker in markers
    ]

    if numbers != list(range(1, 22)):
        raise ValueError(
            "서류 번호 1~21 검증 실패"
        )

    symbols = [
        marker["symbol"]
        for marker in markers
    ]

    if symbols != EXPECTED_SYMBOLS:
        raise ValueError(
            "제출 기호 검증 실패"
        )

    # 실제 병합 영역의 위·아래 구분선 확인
    expected_boundaries = [
        590.1, 640.1, 690.2, 740.3,
        790.4, 840.4, 890.5, 940.6, 990.7,
    ]

    for y in expected_boundaries:
        if not any(
            abs(boundary - y) < 0.2
            for boundary in boundaries
        ):
            raise ValueError(
                f"병합 영역 경계 누락: {y}"
            )

    # 병합 영역의 비고 원문 직접 추출
    merged_text = {
        (10, 11, 12, 13): extract_column_text(
            blocks, 590.1, 790.4, 670, 900
        ),
        (15, 16, 17): extract_column_text(
            blocks, 840.4, 990.7, 670, 900
        ),
    }

    for group, expected in MERGED_CONDITIONS.items():
        if merged_text[group] != expected:
            raise ValueError(
                f"{group}번 병합 비고 원문 불일치: "
                f"{merged_text[group]}"
            )

    documents = []

    for marker in markers:
        number = marker["number"]
        symbol = marker["symbol"]

        low, high = get_row_bounds(
            boundaries,
            marker["y"],
        )

        name = extract_column_text(
            blocks, low, high, 218, 510
        )

        condition = extract_column_text(
            blocks, low, high, 670, 900
        )

        condition_scope = (
            "individual_row"
            if condition
            else None
        )

        # 서류명 끝에 붙은 조건 분리
        if number in INLINE_CONDITIONS:
            inline = INLINE_CONDITIONS[number]

            if not name.endswith(inline):
                raise ValueError(
                    f"{number}번 조건 분리 실패"
                )

            name = name[:-len(inline)]

            if condition:
                raise ValueError(
                    f"{number}번 비고 중복 확인 필요"
                )

            condition = inline
            condition_scope = "inline_text"

        # 병합 셀 적용
        for group, merged_condition in (
            merged_text.items()
        ):
            if number in group:
                condition = merged_condition
                condition_scope = "merged_cell"
                break

        if not name:
            raise ValueError(
                f"{number}번 서류명 누락"
            )

        documents.append({
            "document_id": (
                f"JP_ST_COE_SCHOOL_{number:03d}"
            ),
            "row_number": number,
            "name_ja": name,
            "requirement_symbol": symbol,
            "requirement_status": STATUS_MAP[symbol],
            "condition_original_ja": (
                condition or None
            ),
            "condition_scope": condition_scope,
            "source": {
                "document_id": "001463593",
                "page": 1,
                "url": SOURCE_URL,
            },
            "validation_status": "needs_review",
        })

    return documents


def main():
    if not PDF_PATH.is_file():
        raise FileNotFoundError(PDF_PATH)

    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"기존 JSON 덮어쓰기 금지: {OUTPUT_PATH}"
        )

    with pymupdf.open(PDF_PATH) as pdf:
        if len(pdf) != 2:
            raise ValueError(
                "PDF 페이지 수 불일치"
            )

        documents = extract_documents(pdf[0])

    by_number = {
        d["row_number"]: d
        for d in documents
    }

    # 개별 서류명 및 조건 검증
    assert by_number[5]["name_ja"] == (
        "最終学校の卒業証明書"
    )

    assert by_number[5]["condition_original_ja"] == (
        "高校に入学する場合"
    )

    assert by_number[18]["name_ja"].startswith(
        "特待生受入れに関する資料"
    )

    assert by_number[18]["condition_original_ja"] == (
        "高校に特待生として入学する場合"
    )

    # 병합 조건 검증
    for number in (10, 11, 12, 13):
        assert (
            by_number[number]["condition_original_ja"]
            == MERGED_CONDITIONS[(10, 11, 12, 13)]
        )

        assert (
            by_number[number]["condition_scope"]
            == "merged_cell"
        )

    for number in (15, 16, 17):
        assert (
            by_number[number]["condition_original_ja"]
            == MERGED_CONDITIONS[(15, 16, 17)]
        )

    # 기타 중요 조건 확인
    assert "提出は不要" in (
        by_number[2]["condition_original_ja"] or ""
    )

    assert "１年以上" in (
        by_number[6]["condition_original_ja"] or ""
    )

    assert "未成年" in (
        by_number[19]["condition_original_ja"] or ""
    )

    assert "18歳未満" in (
        by_number[20]["condition_original_ja"] or ""
    )

    assert "不許可処分" in (
        by_number[21]["condition_original_ja"] or ""
    )

    result = {
        "program_id": "JP-ST-01",
        "route_id": "JP-ST",
        "application_type": (
            "certificate_of_eligibility"
        ),
        "school_category": (
            "elementary_secondary_school"
        ),
        "school_classification": (
            "elementary_junior_high_high_school"
        ),
        "target_nationality": "KR",
        "source_language": "ja",
        "source_url": SOURCE_URL,
        "source_sha256": hashlib.sha256(
            PDF_PATH.read_bytes()
        ).hexdigest(),
        "validation_status": "needs_review",
        "documents": documents,
    }

    save_structured_json(OUTPUT_PATH, result)

    saved = json.loads(
        OUTPUT_PATH.read_text(encoding="utf-8")
    )

    assert saved == result, (
        "JSON 저장 검증 실패"
    )

    symbols = [
        d["requirement_symbol"]
        for d in documents
    ]

    print(
        "===== STEP 62-125 초·중등학교 COE 구조화 ====="
    )
    print("저장 파일:", OUTPUT_PATH)
    print("전체 서류:", len(documents))
    print("필수:", symbols.count("○"))
    print("조건부:", symbols.count("△"))
    print("병합 조건 10~13번: 정상")
    print("병합 조건 15~17번: 정상")
    print("서류명 내부 조건 5·18번: 정상")
    print("JSON 저장 및 검증: 성공")


if __name__ == "__main__":
    main()
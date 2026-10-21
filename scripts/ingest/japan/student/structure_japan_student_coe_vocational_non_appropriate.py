
import hashlib
import json
import re
from pathlib import Path

import pymupdf

from structure_japan_student_coe_documents import save_structured_json


PROJECT_ROOT = Path(__file__).resolve().parents[4]

PDF_PATH = (
    PROJECT_ROOT
    / "data/raw/japan/student/japan_student_coe_pdfs/001463589.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/japan/student/"
    "japan_student_coe_vocational_non_appropriate_structured.json"
)

SOURCE_URL = "https://www.moj.go.jp/isa/content/001463589.pdf"

STATUS_MAP = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
}


def extract_documents(page):
    blocks = page.get_text("blocks")

    # PDF 표의 실제 가로 구분선 추출
    boundaries = sorted({
        round(item[1].y, 1)
        for drawing in page.get_drawings()
        for item in drawing["items"]
        if (
            item[0] == "l"
            and abs(item[1].y - item[2].y) < 1
            and abs(item[1].x - item[2].x) > 300
        )
    })

    # 서류 번호 및 제출 기호 추출
    markers = []

    for block in blocks:
        match = re.match(
            r"^(\d+)\s*\n\s*([○△－])",
            block[4].strip(),
        )

        if 130 < block[0] < 145 and match:
            markers.append({
                "number": int(match.group(1)),
                "symbol": match.group(2),
                "y": block[1],
            })

    markers.sort(key=lambda x: x["number"])

    if [m["number"] for m in markers] != list(range(1, 15)):
        raise ValueError("서류 번호 1~14 추출 실패")

    documents = []

    for marker in markers:
        number = marker["number"]
        symbol = marker["symbol"]

        matches = [
            (low, high)
            for low, high in zip(boundaries, boundaries[1:])
            if low <= marker["y"] < high
        ]

        if len(matches) != 1:
            raise ValueError(
                f"{number}번 행 경계 확인 실패"
            )

        low, high = matches[0]

        # 서류명 열
        name_blocks = sorted(
            [
                b for b in blocks
                if 150 < b[0] < 450
                and low <= b[1] < high
            ],
            key=lambda b: b[1],
        )

        # 비고 열
        note_blocks = sorted(
            [
                b for b in blocks
                if 610 < b[0] < 850
                and low <= b[1] < high
            ],
            key=lambda b: b[1],
        )

        name = "".join(
            b[4].strip().replace("\n", "")
            for b in name_blocks
        )

        condition = "".join(
            b[4].strip().replace("\n", "")
            for b in note_blocks
        )

        if not name or "備考欄参照" in name:
            raise ValueError(
                f"{number}번 서류명 추출 오류"
            )

        documents.append({
            "document_id": (
                f"JP_ST_COE_VOC_NONAPP_{number:03d}"
            ),
            "row_number": number,
            "name_ja": name,
            "requirement_symbol": symbol,
            "requirement_status": STATUS_MAP[symbol],
            "condition_original_ja": condition or None,
            "source": {
                "document_id": "001463589",
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
            raise ValueError("PDF 페이지 수 불일치")

        documents = extract_documents(pdf[0])

    symbols = [
        d["requirement_symbol"]
        for d in documents
    ]

    assert len(documents) == 14
    assert symbols == [
        "○", "△", "○", "△", "○", "○", "○",
        "○", "○", "○", "○", "△", "△", "△",
    ], "제출 기호 불일치"

    by_number = {
        d["row_number"]: d
        for d in documents
    }

    # 주요 서류명 검증
    assert by_number[4]["name_ja"] == "最終学校の卒業証明書"
    assert by_number[6]["name_ja"] == "経費支弁書"
    assert "預金残高証明書" in by_number[8]["name_ja"]
    assert "教育機関が確認" in by_number[13]["name_ja"]
    assert "説明及び資料" in by_number[14]["name_ja"]

    # 비고 원문 검증
    assert "提出は不要" in (
        by_number[2]["condition_original_ja"] or ""
    )
    assert "所属機関が大学" in (
        by_number[4]["condition_original_ja"] or ""
    )
    assert "18歳未満" in (
        by_number[13]["condition_original_ja"] or ""
    )
    assert "不許可処分" in (
        by_number[14]["condition_original_ja"] or ""
    )

    result = {
        "program_id": "JP-ST-01",
        "route_id": "JP-ST",
        "application_type": "certificate_of_eligibility",
        "school_category": "vocational_school",
        "school_classification": (
            "not_notified_as_appropriate_school"
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

    assert saved == result, "JSON 저장 검증 실패"

    print("===== STEP 62-99 전문학교 미통지 구조화 =====")
    print("저장 파일:", OUTPUT_PATH)
    print("전체 서류:", len(documents))
    print("필수:", symbols.count("○"))
    print("조건부:", symbols.count("△"))
    print("PDF 근거 연결: 성공")
    print("JSON 저장 및 검증: 성공")


if __name__ == "__main__":
    main()
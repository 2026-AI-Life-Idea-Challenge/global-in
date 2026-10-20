
import hashlib
import json
import re
from pathlib import Path

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parents[4]

PDF_PATH = (
    PROJECT_ROOT
    / "data/raw/japan/student/japan_student_coe_pdfs/001463587.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/japan/student/japan_student_coe_vocational_class1_structured.json"
)

SOURCE_URL = "https://www.moj.go.jp/isa/content/001463587.pdf"

STATUS_MAP = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
}


def extract_rows(page):
    blocks = page.get_text("blocks")

    # PDF 표의 실제 가로 구분선
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

    # 서류 번호와 제출 기호
    markers = []

    for block in blocks:
        match = re.match(
            r"^(\d+)\s*\n\s*([○△－])",
            block[4].strip(),
        )

        if 165 < block[0] < 175 and match:
            markers.append({
                "number": int(match.group(1)),
                "symbol": match.group(2),
                "y": block[1],
            })

    markers.sort(key=lambda x: x["number"])

    if [m["number"] for m in markers] != list(range(1, 7)):
        raise ValueError("서류 번호 1~6 추출 실패")

    documents = []

    for marker in markers:
        matches = [
            (low, high)
            for low, high in zip(boundaries, boundaries[1:])
            if low <= marker["y"] < high
        ]

        if len(matches) != 1:
            raise ValueError(
                f"{marker['number']}번 행 경계 확인 실패"
            )

        low, high = matches[0]

        # 서류명: X 185~400
        name_blocks = sorted(
            [
                b for b in blocks
                if 185 < b[0] < 400 and low <= b[1] < high
            ],
            key=lambda b: b[1],
        )

        # 비고: X 575~850
        note_blocks = sorted(
            [
                b for b in blocks
                if 575 < b[0] < 850 and low <= b[1] < high
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

        if not name:
            raise ValueError(
                f"{marker['number']}번 서류명 누락"
            )

        documents.append({
            "document_id": (
                f"JP_ST_COE_VOC_C1_{marker['number']:03d}"
            ),
            "row_number": marker["number"],
            "name_ja": name,
            "requirement_symbol": marker["symbol"],
            "requirement_status": STATUS_MAP[
                marker["symbol"]
            ],
            "condition_original_ja": condition or None,
            "source": {
                "document_id": "001463587",
                "page": 1,
                "url": SOURCE_URL,
            },
            "validation_status": "needs_review",
        })

    return documents


def main():
    if not PDF_PATH.is_file():
        raise FileNotFoundError(PDF_PATH)

    # 기존 JSON 보호
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"기존 파일 덮어쓰기 금지: {OUTPUT_PATH}"
        )

    with pymupdf.open(PDF_PATH) as pdf:
        if len(pdf) != 2:
            raise ValueError("PDF 페이지 수 불일치")

        documents = extract_rows(pdf[0])

    required = sum(
        x["requirement_status"] == "required"
        for x in documents
    )

    conditional = sum(
        x["requirement_status"] == "conditional"
        for x in documents
    )

    assert len(documents) == 6
    assert required == 3
    assert conditional == 3

    by_number = {
        x["row_number"]: x
        for x in documents
    }

    # 서류명 검증
    assert by_number[1]["name_ja"] == (
        "在留資格認定証明書交付申請書"
    )
    assert by_number[4]["name_ja"] == (
        "日本語能力に係る資料"
    )
    assert "教育機関が確認" in by_number[5]["name_ja"]
    assert "説明及び資料" in by_number[6]["name_ja"]

    # 조건 원문 검증
    assert "提出は不要" in (
        by_number[2]["condition_original_ja"] or ""
    )
    assert by_number[3]["condition_original_ja"] is None
    assert "18歳未満" in (
        by_number[5]["condition_original_ja"] or ""
    )
    assert "不許可処分" in (
        by_number[6]["condition_original_ja"] or ""
    )

    result = {
        "program_id": "JP-ST-01",
        "route_id": "JP-ST",
        "application_type": "certificate_of_eligibility",
        "school_category": "vocational_school",
        "school_classification": "appropriate_school_class_1",
        "target_nationality": "KR",
        "source_language": "ja",
        "source_url": SOURCE_URL,
        "source_sha256": hashlib.sha256(
            PDF_PATH.read_bytes()
        ).hexdigest(),
        "validation_status": "needs_review",
        "documents": documents,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    saved = json.loads(
        OUTPUT_PATH.read_text(encoding="utf-8")
    )

    assert saved["documents"] == documents

    print("===== STEP 62-52 전문학교 Class I 구조화 =====")
    print("저장 파일:", OUTPUT_PATH)
    print("제출서류:", len(documents))
    print("필수:", required)
    print("조건부:", conditional)
    print("JSON 저장 및 검증: 성공")


if __name__ == "__main__":
    main()
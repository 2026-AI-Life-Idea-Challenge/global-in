
import hashlib
import json
import re
from pathlib import Path

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parents[4]

PDF_PATH = (
    PROJECT_ROOT
    / "data/raw/japan/student/japan_student_coe_pdfs/001463588.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/japan/student/"
    "japan_student_coe_vocational_class2_structured.json"
)

SOURCE_URL = "https://www.moj.go.jp/isa/content/001463588.pdf"

STATUS_MAP = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
}


def extract_documents(page):
    blocks = page.get_text("blocks")
    words = page.get_text("words")

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

    # 제출서류 번호
    markers = []

    for block in blocks:
        match = re.match(
            r"^(\d+)(?:\s|$)",
            block[4].strip(),
        )

        if 125 < block[0] < 140 and match:
            number = int(match.group(1))

            if 1 <= number <= 9:
                markers.append((number, block[1]))

    markers.sort()

    assert [n for n, _ in markers] == list(range(1, 10)), (
        "서류 번호 1~9 추출 실패"
    )

    documents = []

    for number, y in markers:
        matches = [
            (low, high)
            for low, high in zip(boundaries, boundaries[1:])
            if low <= y < high
        ]

        assert len(matches) == 1, (
            f"{number}번 행 경계 확인 실패"
        )

        low, high = matches[0]

        # 서류명 열
        name_blocks = sorted(
            [
                b for b in blocks
                if 145 < b[0] < 390
                and low <= b[1] < high
            ],
            key=lambda b: b[1],
        )

        # 비고 열
        note_blocks = sorted(
            [
                b for b in blocks
                if 615 < b[0] < 850
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

        # 별표 기재 국가·지역 열 (한국 포함)
        listed_symbols = [
            w[4]
            for w in words
            if (
                425 < w[0] < 445
                and low <= w[1] < high
                and w[4] in STATUS_MAP
            )
        ]

        # 별표 외 국가·지역 열
        other_symbols = [
            w[4]
            for w in words
            if (
                500 < w[0] < 520
                and low <= w[1] < high
                and w[4] in STATUS_MAP
            )
        ]

        assert len(listed_symbols) == 1, (
            f"{number}번 한국 적용 기호 오류"
        )
        assert len(other_symbols) == 1, (
            f"{number}번 기타 국가 기호 오류"
        )
        assert name and "備考欄参照" not in name, (
            f"{number}번 서류명 오류"
        )

        kr_symbol = listed_symbols[0]
        other_symbol = other_symbols[0]

        documents.append({
            "document_id": f"JP_ST_COE_VOC_C2_{number:03d}",
            "row_number": number,
            "name_ja": name,
            "requirement_symbol": kr_symbol,
            "requirement_status": STATUS_MAP[kr_symbol],
            "nationality_columns": {
                "listed_countries": {
                    "symbol": kr_symbol,
                    "status": STATUS_MAP[kr_symbol],
                },
                "other_countries": {
                    "symbol": other_symbol,
                    "status": STATUS_MAP[other_symbol],
                },
            },
            "condition_original_ja": condition or None,
            "source": {
                "document_id": "001463588",
                "page": 1,
                "url": SOURCE_URL,
            },
            "validation_status": "needs_review",
        })

    return documents


def main():
    assert PDF_PATH.is_file(), "공식 PDF 파일 없음"

    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"기존 JSON 덮어쓰기 금지: {OUTPUT_PATH}"
        )

    with pymupdf.open(PDF_PATH) as pdf:
        assert len(pdf) == 2, "PDF 페이지 수 불일치"
        documents = extract_documents(pdf[0])

    symbols = [
        d["requirement_symbol"]
        for d in documents
    ]

    expected = [
        "○", "△", "○", "○", "－",
        "－", "－", "△", "△",
    ]

    assert symbols == expected, "한국 제출 요건 검증 실패"

    by_number = {
        d["row_number"]: d
        for d in documents
    }

    assert by_number[5]["name_ja"] == "経費支弁書"
    assert "預金残高証明書" in by_number[6]["name_ja"]
    assert "奨学金" in by_number[7]["name_ja"]
    assert "教育機関が確認" in by_number[8]["name_ja"]
    assert "説明及び資料" in by_number[9]["name_ja"]

    assert "提出は不要" in (
        by_number[2]["condition_original_ja"] or ""
    )
    assert "18歳未満" in (
        by_number[8]["condition_original_ja"] or ""
    )

    result = {
        "program_id": "JP-ST-01",
        "route_id": "JP-ST",
        "application_type": "certificate_of_eligibility",
        "school_category": "vocational_school",
        "school_classification": "appropriate_school_class_2",
        "target_nationality": "KR",
        "nationality_category": "listed_countries",
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

    assert saved == result, "JSON 저장 검증 실패"

    print("===== STEP 62-87 전문학교 Class II 구조화 =====")
    print("저장 파일:", OUTPUT_PATH)
    print("전체 서류:", len(documents))
    print("한국 국적 필수:", symbols.count("○"))
    print("한국 국적 조건부:", symbols.count("△"))
    print("한국 국적 해당 없음:", symbols.count("－"))
    print("두 국적 열 보존: 성공")
    print("JSON 저장 및 검증: 성공")


if __name__ == "__main__":
    main()

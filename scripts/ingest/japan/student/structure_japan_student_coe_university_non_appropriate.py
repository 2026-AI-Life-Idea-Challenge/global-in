
import hashlib
import json
import re
from pathlib import Path

import pymupdf


# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parents[4]

# 적정교 통지를 받지 않은 대학·대학원 COE 제출서류
PDF_PATH = (
    PROJECT_ROOT
    / "data/raw/japan/student/japan_student_coe_pdfs/001463586.pdf"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/japan/student/japan_student_coe_university_non_appropriate_structured.json"
)

SOURCE_URL = "https://www.moj.go.jp/isa/content/001463586.pdf"

STATUS_MAP = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
}


def extract_rows(page):
    """실제 표 가로선으로 16개 서류의 이름과 비고를 연결한다."""
    blocks = page.get_text("blocks")

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

    markers = []

    for block in blocks:
        x, y = block[0], block[1]
        match = re.match(
            r"^(\d+)\s*\n\s*([○△－])",
            block[4].strip(),
        )

        if 190 < x < 210 and match:
            markers.append({
                "number": int(match.group(1)),
                "symbol": match.group(2),
                "y": y,
            })

    markers.sort(key=lambda item: item["number"])

    if len(markers) != 16:
        raise ValueError(
            f"제출서류 16개가 아닙니다: {len(markers)}"
        )

    if [m["number"] for m in markers] != list(range(1, 17)):
        raise ValueError("서류 번호가 연속되지 않습니다.")

    rows = []

    for marker in markers:
        y = marker["y"]

        matches = [
            (low, high)
            for low, high in zip(boundaries, boundaries[1:])
            if low <= y < high
        ]

        if len(matches) != 1:
            raise ValueError(
                f"{marker['number']}번 행 경계 확인 실패"
            )

        low, high = matches[0]

        # 서류명 열: X좌표 210~530
        name_blocks = sorted(
            [
                b for b in blocks
                if 210 < b[0] < 530 and low <= b[1] < high
            ],
            key=lambda b: b[1],
        )

        # 비고 열: X좌표 665~900
        note_blocks = sorted(
            [
                b for b in blocks
                if 665 < b[0] < 900 and low <= b[1] < high
            ],
            key=lambda b: b[1],
        )

        raw_name = "".join(
            b[4].strip().replace("\n", "")
            for b in name_blocks
        )

        document_name = raw_name.replace(
            "（備考欄参照）有無", ""
        )

        condition_text = "".join(
            b[4].strip().replace("\n", "")
            for b in note_blocks
        )

        if not document_name:
            raise ValueError(
                f"{marker['number']}번 서류명 누락"
            )

        if "備考欄参照" in document_name:
            raise ValueError(
                f"{marker['number']}번 서류명 정제 실패"
            )

        rows.append({
            "document_id": (
                f"JP_ST_COE_UNI_NONAPP_{marker['number']:03d}"
            ),
            "row_number": marker["number"],
            "name_ja": document_name,
            "requirement_symbol": marker["symbol"],
            "requirement_status": STATUS_MAP[marker["symbol"]],
            "condition_original_ja": condition_text or None,
            "source": {
                "document_id": "001463586",
                "page": 1,
                "url": SOURCE_URL,
            },
            "validation_status": "needs_review",
        })

    return rows


def main():
    if not PDF_PATH.is_file():
        raise FileNotFoundError(PDF_PATH)

    # 기존 JSON 덮어쓰기 방지
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"기존 JSON을 덮어쓰지 않습니다: {OUTPUT_PATH}"
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

    if required != 8 or conditional != 8:
        raise ValueError("제출 상태 개수 불일치")

    by_number = {
        x["row_number"]: x
        for x in documents
    }

    # 핵심 서류 및 긴 서류명 확인
    assert by_number[8]["name_ja"] == "経費支弁書"
    assert "預金残高証明書" in by_number[10]["name_ja"]
    assert "教育機関が確認" in by_number[15]["name_ja"]
    assert "する説明及び資料" in by_number[16]["name_ja"]

    # 비고 연결 검증
    assert "は不要" in (
        by_number[2]["condition_original_ja"] or ""
    )
    assert by_number[3]["condition_original_ja"] is None
    assert "場合は不要" in (
        by_number[4]["condition_original_ja"] or ""
    )

    result = {
        "program_id": "JP-ST-01",
        "route_id": "JP-ST",
        "application_type": "certificate_of_eligibility",
        "school_category": "university",
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

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

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
    assert len(saved["documents"]) == 16

    print("===== 대학 COE 제출서류 구조화 =====")
    print("저장 파일:", OUTPUT_PATH)
    print("제출서류:", len(documents))
    print("필수:", required)
    print("조건부:", conditional)
    print("JSON 저장 및 검증: 성공")


if __name__ == "__main__":
    main()

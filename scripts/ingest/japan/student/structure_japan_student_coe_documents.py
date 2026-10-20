
import hashlib
import json
import re
from pathlib import Path

import pymupdf


# 프로젝트 경로
PROJECT_ROOT = Path(__file__).resolve().parents[4]

# 첫 번째 대학·대학원 COE 제출서류 PDF
PDF_PATH = (
    PROJECT_ROOT
    / "data/raw/japan/student/japan_student_coe_pdfs/001463585.pdf"
)

# 구조화 결과 저장 경로
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data/processed/japan/student/japan_student_coe_university_class12_structured.json"
)

SOURCE_URL = (
    "https://www.moj.go.jp/isa/content/001463585.pdf"
)

STATUS_MAP = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
}


def extract_rows(page):
    """PDF 표의 실제 가로 구분선을 기준으로 행을 추출한다."""

    blocks = page.get_text("blocks")

    # 표의 가로 구분선 추출
    boundaries = sorted({
        round(item[1].y, 1)
        for drawing in page.get_drawings()
        for item in drawing["items"]
        if (
            item[0] == "l"
            and abs(item[1].y - item[2].y) < 1
            and abs(item[1].x - item[2].x) > 300
            and 130 < item[1].y < 730
        )
    })

    # 번호와 제출 기호가 들어 있는 블록
    markers = []

    for block in blocks:
        x, y = block[0], block[1]
        text = block[4].strip()

        match = re.match(
            r"^([1-9])\s*\n\s*([○△－])",
            text,
        )

        if 175 < x < 195 and match:
            markers.append({
                "number": int(match.group(1)),
                "symbol": match.group(2),
                "y": y,
            })

    markers.sort(key=lambda item: item["number"])

    if len(markers) != 9:
        raise ValueError(
            f"제출서류 9개가 아닙니다: {len(markers)}개"
        )

    rows = []

    for marker in markers:
        y = marker["y"]

        # 번호가 포함된 실제 표 행 경계 찾기
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
                f"{marker['number']}번 표 경계 확인 실패"
            )

        low, high = matches[0]

        # 서류명 열
        names = sorted(
            [
                block
                for block in blocks
                if (
                    195 < block[0] < 510
                    and low <= block[1] < high
                )
            ],
            key=lambda block: block[1],
        )

        # 비고 열
        notes = sorted(
            [
                block
                for block in blocks
                if (
                    650 < block[0] < 850
                    and low <= block[1] < high
                )
            ],
            key=lambda block: block[1],
        )

        document_name = "".join(
            block[4].strip().replace("\n", "")
            for block in names
        )

        condition_text = "".join(
            block[4].strip().replace("\n", "")
            for block in notes
        )

        if not document_name:
            raise ValueError(
                f"{marker['number']}번 서류명 누락"
            )

        rows.append({
            "document_id": (
                f"JP_ST_COE_UNI_{marker['number']:03d}"
            ),
            "row_number": marker["number"],
            "name_ja": document_name,
            "requirement_symbol": marker["symbol"],
            "requirement_status": STATUS_MAP[
                marker["symbol"]
            ],
            "condition_original_ja": (
                condition_text or None
            ),
            "source": {
                "document_id": "001463585",
                "page": 1,
                "url": SOURCE_URL,
            },
            "validation_status": "needs_review",
        })

    return rows


def main():
    if not PDF_PATH.is_file():
        raise FileNotFoundError(PDF_PATH)

    # 기존 구조화 결과 보호
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"기존 JSON을 덮어쓰지 않습니다: {OUTPUT_PATH}"
        )

    with pymupdf.open(PDF_PATH) as pdf:
        if len(pdf) != 2:
            raise ValueError("PDF 페이지 수 확인 필요")

        documents = extract_rows(pdf[0])

    # 필수·조건부 개수 검증
    required = sum(
        item["requirement_status"] == "required"
        for item in documents
    )

    conditional = sum(
        item["requirement_status"] == "conditional"
        for item in documents
    )

    if required != 2 or conditional != 7:
        raise ValueError("제출서류 상태 개수 불일치")

    # 이미 확인한 여러 줄 서류명 검증
    by_number = {
        item["row_number"]: item
        for item in documents
    }

    assert "追記欄ページ" in by_number[3]["name_ja"]
    assert "教育機関が確認" in by_number[8]["name_ja"]
    assert "説明及び資料" in by_number[9]["name_ja"]

    # 비고가 다른 행에 섞이지 않았는지 확인
    assert "は不要" in (
        by_number[2]["condition_original_ja"] or ""
    )
    assert by_number[3]["condition_original_ja"] is None
    assert "合を除く。" in (
        by_number[4]["condition_original_ja"] or ""
    )

    result = {
        "program_id": "JP-ST-01",
        "route_id": "JP-ST",
        "application_type": "certificate_of_eligibility",
        "school_category": "university",
        "school_classification": (
            "appropriate_school_class_1_or_2"
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

    # 저장된 내용 검증
    saved = json.loads(
        OUTPUT_PATH.read_text(encoding="utf-8")
    )

    assert saved["documents"] == documents

    print("===== STEP 62-36 COE 제출서류 구조화 =====")
    print("저장 파일:", OUTPUT_PATH)
    print("제출서류:", len(documents))
    print("필수:", required)
    print("조건부:", conditional)
    print("JSON 저장 및 검증: 성공")


if __name__ == "__main__":
    main()
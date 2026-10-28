
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_renewal_pdfs/001367009.pdf"
HASH_PATH = RAW / "japan_employment_renewal_pdf_hashes.json"

OUTPUT = PROCESSED / "japan_employment_renewal_structured.json"

EXPECTED_SHA = (
    "472a27d772b1649e61fb99a2ec569e8eb48ee8cc6811789160cf1160a17fa622"
)

# STEP 63-73~74에서 검증한 실제 PDF 표 경계
ROW_BOUNDARIES = {
    1: {
        "numbers": list(range(1, 8)),
        "y": [
            126.58, 158.62, 238.30, 270.34,
            521.38, 666.82, 728.02, 818.86,
        ],
    },
    2: {
        "numbers": list(range(8, 14)),
        "y": [
            70.66, 208.78, 299.62, 390.46,
            481.30, 575.74, 716.62,
        ],
    },
}

CATEGORY_X = {
    "1": 294.9,
    "2": 360.5,
    "3": 426.0,
    "4": 491.5,
}

EXPECTED_SYMBOLS = {
    1: ("○", "○", "○", "○"),
    2: ("○", "○", "○", "○"),
    3: ("○", "○", "○", "○"),
    4: (None, None, None, None),
    5: ("△", "△", "△", "△"),
    6: (None, None, "○", "○"),
    7: (None, None, "○", "○"),
    8: (None, None, "○", "○"),
    9: (None, None, "○", "○"),
    10: (None, None, "○", "○"),
    11: (None, None, "○", "○"),
    12: (None, None, "△", "△"),
    13: (None, None, None, "○"),
}

STATUS = {
    "○": "required",
    "△": "conditional",
    "－": "not_applicable",
    None: "not_explicitly_marked",
}

KEYWORDS = {
    1: ["在留期間更新許可申請書"],
    2: ["写真", "６か月以内"],
    3: ["パスポート", "在留カード"],
    4: ["所属機関", "カテゴリー", "証明する文書"],
    5: ["派遣契約", "派遣先"],
    6: ["所属機関の代表者", "申告書"],
    7: ["住民税", "納税証明書"],
    8: ["活動内容", "労働契約", "役員報酬"],
    9: ["登記事項証明書"],
    10: ["事業内容", "案内書"],
    11: ["決算文書", "事業計画書"],
    12: ["言語能力", "ＣＥＦＲ", "Ｂ２"],
    13: ["法定調書合計表", "源泉徴収"],
}


def compact(text):
    return "".join(text.split())


def sha256(data):
    return hashlib.sha256(data).hexdigest()


print("===== STEP 63-75 갱신 신청 기본 JSON 구조화 =====")

# 1. 입력 무결성 및 기존 데이터 보호
assert PDF_PATH.is_file(), "PDF 원본 누락"
assert HASH_PATH.is_file(), "해시 기록 누락"
assert not OUTPUT.exists(), "출력 JSON이 이미 존재합니다."

pdf_bytes = PDF_PATH.read_bytes()
pdf_sha = sha256(pdf_bytes)

assert pdf_sha == EXPECTED_SHA, "공식 PDF SHA-256 불일치"

hash_data = json.loads(
    HASH_PATH.read_text(encoding="utf-8")
)

assert hash_data["route_id"] == "JP-EM"
assert hash_data["application_type"] == "renewal"

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

assert record["sha256"] == pdf_sha

# 2. PDF 행별 원문 및 제출 기호 추출
documents = []

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 2

    # 페이지 2의 범위·추가 제출 조건을 원문 그대로 저장
    scope_note = pdf[1].get_text(
        "text",
        clip=pymupdf.Rect(0, 0, 595, 70.5),
        sort=True,
    ).strip()

    normalized_note = compact(scope_note)

    assert "転職後の初回の更新許可申請" in normalized_note
    assert "提出資料１３は不要" in normalized_note
    assert "提出書類１２" in normalized_note

    for page_number, config in ROW_BOUNDARIES.items():
        page = pdf[page_number - 1]
        words = page.get_text("words", sort=False)

        numbers = config["numbers"]
        boundaries = config["y"]

        assert len(boundaries) == len(numbers) + 1

        for index, number in enumerate(numbers):
            upper = boundaries[index] + 0.6
            lower = boundaries[index + 1] - 0.6

            assert upper < lower

            # STEP 63-74와 동일한 범위 사용
            row_clip = pymupdf.Rect(
                55, upper, 535, lower
            )

            row_text = page.get_text(
                "text",
                clip=row_clip,
                sort=True,
            ).strip()

            assert row_text, f"No.{number} 원문 누락"

            normalized = compact(row_text)

            for keyword in KEYWORDS[number]:
                assert keyword in normalized, (
                    f"No.{number} 핵심 문구 누락: {keyword}"
                )

            number_words = [
                w for w in words
                if re.fullmatch(r"\d{1,2}", w[4].strip())
                and int(w[4]) == number
                and 35 <= w[0] <= 55
                and upper <= (w[1] + w[3]) / 2 <= lower
            ]

            assert len(number_words) == 1, (
                f"No.{number} 서류 번호 좌표 이상"
            )

            requirements = {}
            actual_symbols = []

            for category, center_x in CATEGORY_X.items():
                candidates = [
                    w[4].strip()
                    for w in words
                    if w[4].strip() in {"○", "△", "－"}
                    and abs(w[0] - center_x) <= 8
                    and upper <= (w[1] + w[3]) / 2 <= lower
                ]

                # No.4는 각 열에 증빙 문구가 있어
                # 일반 제출 기호로 해석하지 않는다.
                if number == 4:
                    symbol = None
                    status = "category_specific_evidence_text"
                else:
                    assert len(candidates) <= 1, (
                        f"No.{number} Category {category} 기호 중복"
                    )

                    symbol = (
                        candidates[0]
                        if candidates else None
                    )
                    status = STATUS[symbol]

                requirements[category] = {
                    "symbol": symbol,
                    "status": status,
                }

                actual_symbols.append(symbol)

            assert tuple(actual_symbols) == EXPECTED_SYMBOLS[number], (
                f"No.{number} 제출 표시 불일치"
            )

            documents.append({
                "document_id": f"JP_EM_RENEWAL_DOC_{number:03d}",
                "row_number": number,
                "page": page_number,
                "raw_row_text_ja": row_text,
                "category_requirements": requirements,
                "applicability_scope": (
                    "additional_documents_after_job_change"
                    if number >= 8
                    else "general_renewal_table"
                ),
                "text_extraction_method": "pdf_table_boundaries_full_row",
                "validation_status": "needs_review",
            })

            print(
                f"No.{number:02d}",
                f"Page {page_number}",
                dict(zip(CATEGORY_X, actual_symbols)),
                f"{len(row_text)}자",
            )

# 3. 기본 구조화 데이터
dataset = {
    "route_id": "JP-EM",
    "program_id": "JP-EM-01",
    "application_type": "renewal",
    "status_of_residence": "技術・人文知識・国際業務",
    "source": {
        "official_agency": "Immigration Services Agency of Japan",
        "pdf_filename": PDF_PATH.name,
        "source_url": record["source_url"],
        "source_sha256": pdf_sha,
    },
    "category_columns": ["1", "2", "3", "4"],
    "additional_submission_note_ja": scope_note,
    "additional_submission_note_interpretation_status": "needs_review",
    "automatic_eligibility_rules_enabled": False,
    "document_count": len(documents),
    "validation_status": "needs_review",
    "documents": documents,
}

# 4. 최종 검증
assert len(documents) == 13

assert [d["row_number"] for d in documents] == list(
    range(1, 14)
)

assert len({
    d["document_id"] for d in documents
}) == 13

assert all(
    d["validation_status"] == "needs_review"
    for d in documents
)

# 5. 신규 파일 저장 — 덮어쓰기 금지
PROCESSED.mkdir(parents=True, exist_ok=True)

# OS에 따른 줄바꿈 차이를 피하기 위해
# LF 방식의 UTF-8 바이트로 저장
output_bytes = json.dumps(
    dataset,
    ensure_ascii=False,
    indent=2,
).encode("utf-8")

with OUTPUT.open("xb") as f:
    f.write(output_bytes)

assert OUTPUT.read_bytes() == output_bytes

print("\n===== STEP 63-75 최종 결과 =====")
print("신청 유형:", dataset["application_type"])
print("구조화 서류:", len(documents))
print("추가 제출 조건 원문: 보존")
print("No.4 카테고리별 증빙: 별도 처리 표시")
print("자동 자격 판정: 비활성화")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("출력 SHA-256:", sha256(output_bytes))
print("기존 COE·변경 신청 JSON: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")
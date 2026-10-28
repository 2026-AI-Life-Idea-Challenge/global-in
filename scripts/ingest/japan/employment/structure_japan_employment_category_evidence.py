
from pathlib import Path
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"
REVIEW = ROOT / "_local_backup/japan_employment_category_evidence_review"

PDF_PATH = RAW / "japan_employment_coe_pdfs/001404131.pdf"
HASH_PATH = RAW / "japan_employment_coe_pdf_hashes.json"

SOURCE_PATH = (
    PROCESSED / "japan_employment_coe_common_structured.json"
)
OUTPUT_PATH = (
    REVIEW / "japan_employment_coe_common_structured.json"
)

# STEP 63-17에서 확인한 실제 표 좌표
COLUMNS = {
    "1": (216.5, 291.4),
    "2": (291.4, 366.3),
    "3": (366.3, 441.2),
    "4": (441.2, 516.1),
}

ROW_TOP = 330.96
ROW_BOTTOM = 572.04

print("===== STEP 63-18 카테고리 증빙 JSON 구조화 =====")

assert PDF_PATH.is_file(), "PDF 원본 누락"
assert HASH_PATH.is_file(), "해시 기록 누락"
assert SOURCE_PATH.is_file(), "기존 JSON 누락"
assert not OUTPUT_PATH.exists(), "수정 후보가 이미 존재함"

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

pdf_bytes = PDF_PATH.read_bytes()
sha256 = hashlib.sha256(pdf_bytes).hexdigest()

assert sha256 == record["sha256"], "PDF SHA-256 불일치"

dataset = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

assert dataset["document_count"] == 6
assert dataset["route_id"] == "JP-EM"

rows = [
    row for row in dataset["documents"]
    if row["document_id"] == "JP_EM_COE_DOC_004"
]

assert len(rows) == 1
row = rows[0]

assert "category_evidence" not in row, (
    "이미 category_evidence 필드가 존재합니다."
)

category_evidence = {}

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 1
    page = pdf[0]

    for category, (left, right) in COLUMNS.items():
        clip = pymupdf.Rect(
            left,
            ROW_TOP + 0.5,
            right,
            ROW_BOTTOM - 0.5,
        )

        text = page.get_text(
            "text",
            clip=clip,
            sort=True,
        ).strip()

        category_evidence[category] = {
            "original_text_ja": text,
            "source_cell_status": (
                "text_present" if text else "empty"
            ),
            "validation_status": "needs_review",
        }

# 추출 결과가 STEP 63-17 분석과 일치하는지 확인
assert "四季報" in category_evidence["1"]["original_text_ja"]
assert "在留申請オンライン" in (
    category_evidence["2"]["original_text_ja"]
)
# PDF 줄바꿈과 공백을 제거한 뒤 핵심 문구 검사
category_3_normalized = "".join(
    category_evidence["3"]["original_text_ja"].split()
)

assert "法定調書合計表" in category_3_normalized, (
    "카테고리 3 법정조서합계표 원문 확인 실패"
)
assert category_evidence["4"]["original_text_ja"] == ""

row["category_evidence"] = category_evidence
row["category_evidence_source"] = {
    "pdf_filename": PDF_PATH.name,
    "page": 1,
    "extraction_method": "pdf_column_coordinates",
    "source_sha256": sha256,
}
row["category_evidence_notes"] = (
    "카테고리 4의 원문 공란은 제출서류 면제를 뜻하지 않음. "
    "카테고리 분류 및 제출 조건은 별도 검토 필요."
)

REVIEW.mkdir(parents=True, exist_ok=True)

with OUTPUT_PATH.open("x", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

saved = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
assert saved == dataset, "후보 JSON 저장 검증 실패"

print("\n서류 ID:", row["document_id"])

for category, evidence in category_evidence.items():
    print(
        f"Category {category}:",
        evidence["source_cell_status"],
        "/ 문자 수:",
        len(evidence["original_text_ja"]),
    )

print("\n수정 후보:", OUTPUT_PATH.relative_to(ROOT))
print("원본 PDF SHA-256: 일치")
print("기존 processed JSON: 변경 없음")
print("정책 검증: needs_review")
print("STEP 63-18 완료")
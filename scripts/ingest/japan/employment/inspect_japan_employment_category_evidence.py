
from pathlib import Path
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW_DIR = ROOT / "data/raw/japan/employment"
PDF_PATH = (
    RAW_DIR
    / "japan_employment_coe_pdfs"
    / "001404131.pdf"
)
HASH_PATH = RAW_DIR / "japan_employment_coe_pdf_hashes.json"
JSON_PATH = (
    ROOT
    / "data/processed/japan/employment"
    / "japan_employment_coe_common_structured.json"
)

print("===== STEP 63-17 소속기관 카테고리 증빙 분석 =====")

# 1. 기존 파일과 SHA-256 확인
assert PDF_PATH.is_file(), "PDF 원본 누락"
assert HASH_PATH.is_file(), "해시 기록 누락"
assert JSON_PATH.is_file(), "구조화 JSON 누락"

hash_data = json.loads(
    HASH_PATH.read_text(encoding="utf-8")
)

record = next(
    item
    for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

pdf_bytes = PDF_PATH.read_bytes()
actual_hash = hashlib.sha256(pdf_bytes).hexdigest()

assert actual_hash == record["sha256"], (
    "PDF SHA-256 불일치"
)

dataset = json.loads(
    JSON_PATH.read_text(encoding="utf-8")
)

row = next(
    item
    for item in dataset["documents"]
    if item["row_number"] == 4
)

assert row["document_id"] == "JP_EM_COE_DOC_004"

print("PDF SHA-256: 일치")
print("서류 ID:", row["document_id"])

# 2. STEP 63-13에서 확인한 4번 행의 실제 경계
ROW_TOP = 330.96
ROW_BOTTOM = 572.04

# 표의 실제 열 배치를 기준으로 영역 분리
COLUMNS = {
    "document_description": (58.0, 216.5),
    "category_1": (216.5, 291.4),
    "category_2": (291.4, 366.3),
    "category_3": (366.3, 441.2),
    "category_4": (441.2, 516.1),
}

with pymupdf.open(
    stream=pdf_bytes,
    filetype="pdf",
) as pdf:
    page = pdf[0]

    for name, (left, right) in COLUMNS.items():
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

        print("\n" + "=" * 55)
        print("영역:", name)
        print("X 좌표:", left, "~", right)
        print("문자 수:", len(text))
        print("\n[일본어 원문]")
        print(text if text else "(추출된 텍스트 없음)")

print("\n===== 분석 결과 =====")
print("PDF 및 JSON 수정: 없음")
print("카테고리별 증빙 조건: 해석 전")
print("정책 검증 상태: needs_review")
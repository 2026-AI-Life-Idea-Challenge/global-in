
from pathlib import Path
import hashlib
import json

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_coe_pdfs/001437254.pdf"
HASH_PATH = RAW / "japan_employment_coe_pdf_hashes.json"
JSON_PATH = (
    PROCESSED / "japan_employment_coe_category34_structured.json"
)

print("===== STEP 63-22 학력·경력 증빙 원문 분석 =====")

assert PDF_PATH.is_file(), "원본 PDF 누락"
assert HASH_PATH.is_file(), "PDF 해시 기록 누락"
assert JSON_PATH.is_file(), "구조화 JSON 누락"

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

pdf_bytes = PDF_PATH.read_bytes()
sha256 = hashlib.sha256(pdf_bytes).hexdigest()

assert sha256 == record["sha256"], "PDF SHA-256 불일치"

dataset = json.loads(JSON_PATH.read_text(encoding="utf-8"))
assert dataset["route_id"] == "JP-EM"

row = next(
    item for item in dataset["documents"]
    if item["document_id"] == "JP_EM_COE_DOC_008"
)

# STEP 63-13에서 검증한 8번 행의 실제 경계
TOP = 271.46
BOTTOM = 459.31

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    assert len(pdf) == 1
    page = pdf[0]

    clip = pymupdf.Rect(
        100.0, TOP + 0.5,
        370.0, BOTTOM - 0.5
    )

    original_text = page.get_text(
        "text", clip=clip, sort=True
    ).strip()

normalized = "".join(original_text.split())

keywords = {
    "경력 이력서": "履歴書",
    "대학 졸업 증명": "卒業証明書",
    "재직·경력 증명": "在職証明書",
    "IT 자격 증명": "情報処理",
    "5번 서류 제출 예외": "５の資料",
    "국제업무 경력": "３年以上",
    "대학 졸업자 예외": "翻訳・通訳",
}

print("서류 ID:", row["document_id"])
print("원본 PDF:", PDF_PATH.name)
print("SHA-256:", sha256)
print("\n[8번 제출서류 일본어 원문]")
print(original_text)

print("\n[세부 조건 문구 확인]")
missing = []

for label, keyword in keywords.items():
    found = keyword in normalized
    print(f"{label}: {'확인' if found else '미확인'}")

    if not found:
        missing.append(label)

print("\n[기존 JSON 원문 비교]")
saved_text = row["raw_row_text_ja"]

for keyword in keywords.values():
    assert keyword in "".join(saved_text.split()), (
        f"기존 JSON 원문 누락: {keyword}"
    )

assert not missing, f"PDF 문구 누락: {missing}"

print("기존 JSON 핵심 문구: 일치")
print("PDF 원문 핵심 문구: 모두 확인")
print("원본 PDF·JSON 수정: 없음")
print("정책 검증 상태: needs_review")
print("STEP 63-22 완료")
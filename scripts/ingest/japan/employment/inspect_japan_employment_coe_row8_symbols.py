
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"

PDF_PATH = RAW / "japan_employment_coe_pdfs/001437254.pdf"
HASH_PATH = RAW / "japan_employment_coe_pdf_hashes.json"
JSON_PATH = (
    PROCESSED / "japan_employment_coe_category34_structured.json"
)

print("===== STEP 63-26 COE 8번 서류 기호 좌표 분석 =====")

for path in [PDF_PATH, HASH_PATH, JSON_PATH]:
    assert path.is_file(), f"파일 누락: {path}"

hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

pdf_bytes = PDF_PATH.read_bytes()
pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

assert pdf_hash == record["sha256"], "PDF SHA-256 불일치"

dataset = json.loads(JSON_PATH.read_text(encoding="utf-8"))

row8 = next(
    item for item in dataset["documents"]
    if item["document_id"] == "JP_EM_COE_DOC_008"
)

# 앞 단계에서 확인한 PDF 8번 행 경계
TOP = 271.1
BOTTOM = 459.31

with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
    page = pdf[0]

    words = page.get_text("words", sort=True)

    row_words = [
        word for word in words
        if TOP <= (word[1] + word[3]) / 2 <= BOTTOM
    ]

    print("PDF:", PDF_PATH.name)
    print("8번 행 내 전체 단어:", len(row_words))

    print("\n[기호 포함 단어 및 좌표]")
    symbol_words = []

    for word in row_words:
        x0, y0, x1, y1, text, *_ = word

        if re.search(r"[○●△□]", text):
            symbol_words.append(word)

            print(
                f"텍스트={text!r} "
                f"x={x0:.1f}~{x1:.1f} "
                f"y={y0:.1f}~{y1:.1f}"
            )

    if not symbol_words:
        print("개별 단어에서 기호를 찾지 못했습니다.")

    print("\n[본문 영역 추출: X=100~370]")
    body_clip = pymupdf.Rect(
        100, TOP, 370, BOTTOM
    )
    body_text = page.get_text(
        "text", clip=body_clip, sort=True
    )
    print(body_text)

    print("\n[카테고리 표시 영역 추출: X=370~470]")
    category_clip = pymupdf.Rect(
        370, TOP, 470, BOTTOM
    )
    category_text = page.get_text(
        "text", clip=category_clip, sort=True
    )
    print(category_text)

print("\n[현재 JSON의 8번 서류 원문에서 기호 확인]")
original = row8["raw_row_text_ja"]

for line in original.splitlines():
    if re.search(r"[○●△□]", line):
        print(repr(line))

print("\n[구조화된 경력 증빙에서 기호 확인]")
education = row8["education_evidence"]
options = education["alternative_group"]["options"]

work_option = next(
    item for item in options
    if item["clause"] == "イ"
)

for line in work_option["original_text_ja"].splitlines():
    if re.search(r"[○●△□]", line):
        print(repr(line))

print("\n===== STEP 63-26 분석 종료 =====")
print("PDF SHA-256: 일치")
print("PDF 및 JSON 수정: 없음")
print("기호 제거 여부: 미결정")
print("정책 검증 상태: needs_review")
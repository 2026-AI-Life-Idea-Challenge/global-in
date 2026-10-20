
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[4]

RAW = ROOT / "data/raw/japan/employment"
PROCESSED = ROOT / "data/processed/japan/employment"
REVIEW = ROOT / "_local_backup/japan_employment_row8_clean_review"

SOURCE = PROCESSED / "japan_employment_coe_category34_structured.json"
OUTPUT = REVIEW / "japan_employment_coe_category34_structured.json"
PDF = RAW / "japan_employment_coe_pdfs/001437254.pdf"
HASHES = RAW / "japan_employment_coe_pdf_hashes.json"

EXPECTED_JSON_SHA = (
    "a4ae01bce67bfaca7d8ff3d9ce309003d932597811556f71c3eee968f969b9c6"
)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def normalize(text):
    return "".join(text.split())

print("===== STEP 63-27 경력 증빙 본문 정제 =====")

for path in [SOURCE, PDF, HASHES]:
    assert path.is_file(), f"파일 누락: {path}"

assert not OUTPUT.exists(), "수정 후보가 이미 존재합니다"
assert sha256(SOURCE) == EXPECTED_JSON_SHA, (
    "최종 JSON이 예상 버전과 다릅니다"
)

hash_data = json.loads(HASHES.read_text(encoding="utf-8"))
record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF.name
)
assert sha256(PDF) == record["sha256"], "PDF 해시 불일치"

dataset = json.loads(SOURCE.read_text(encoding="utf-8"))

row8 = next(
    row for row in dataset["documents"]
    if row["document_id"] == "JP_EM_COE_DOC_008"
)

options = row8["education_evidence"]["alternative_group"]["options"]
work = next(item for item in options if item["clause"] == "イ")

assert "clean_text_ja" not in work

# PDF의 실제 본문 열만 추출한다.
with pymupdf.open(PDF) as pdf:
    page = pdf[0]
    body = page.get_text(
        "text",
        clip=pymupdf.Rect(100, 271.1, 370, 459.31),
        sort=True,
    )

# 조항 イ 시작부터 다음 조항 ウ 직전까지만 사용
start = re.search(
    r"(?m)^[ \t\u3000]*イ[ \t\u3000]+",
    body,
)
end = re.search(
    r"(?m)^[ \t\u3000]*ウ[ \t\u3000]+",
    body,
)

assert start is not None, "イ 조항 시작 위치 미확인"
assert end is not None, "ウ 조항 시작 위치 미확인"
assert start.start() < end.start(), "조항 순서 오류"

clean_text = body[start.start():end.start()].strip()

# 본문 핵심 내용 확인
normalized = normalize(clean_text)

for keyword in [
    "在職証明書",
    "関連する業務",
    "高等専門学校",
    "専修学校",
    "当該技術",
    "又は知識",
]:
    assert keyword in normalized, (
        f"정제 본문에서 누락된 문구: {keyword}"
    )

# 표 기호가 본문에 섞이지 않았는지 검사
assert not re.search(r"[○●△□]", clean_text), (
    "본문에 표 기호가 남아 있습니다"
)

# 원문 이력 추적: 기존 구조화 텍스트는 보존
original_work = work["original_text_ja"]

assert "○" in original_work and "□" in original_work, (
    "예상한 원문 혼입 상태와 다릅니다"
)

work["clean_text_ja"] = clean_text
work["clean_text_source"] = {
    "pdf_filename": PDF.name,
    "page": 1,
    "extraction_method": "body_column_clip",
    "clip_rect": [100, 271.1, 370, 459.31],
    "source_sha256": sha256(PDF),
}
work["text_cleaning_status"] = "needs_review"

# 저장 전 예상한 필드만 추가되었는지 확인
original_dataset = json.loads(SOURCE.read_text(encoding="utf-8"))
original_work = next(
    item
    for item in next(
        row for row in original_dataset["documents"]
        if row["document_id"] == "JP_EM_COE_DOC_008"
    )["education_evidence"]["alternative_group"]["options"]
    if item["clause"] == "イ"
)

assert {
    k: v for k, v in work.items()
    if k not in {
        "clean_text_ja",
        "clean_text_source",
        "text_cleaning_status",
    }
} == original_work, "기존 증빙 필드가 변경되었습니다"

REVIEW.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("x", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

assert json.loads(OUTPUT.read_text(encoding="utf-8")) == dataset

print("\n[정제된 경력 증빙 일본어 본문]")
print(clean_text)

print("\n===== STEP 63-27 결과 =====")
print("서류 ID: JP_EM_COE_DOC_008")
print("대상 조항: イ")
print("정제 후 본문 문자 수:", len(clean_text))
print("표 기호 혼입: 없음")
print("기존 원문: 보존")
print("PDF SHA-256: 일치")
print("후보 JSON:", OUTPUT.relative_to(ROOT))
print("후보 SHA-256:", sha256(OUTPUT))
print("기존 processed JSON: 변경 없음")
print("검증 상태: needs_review")
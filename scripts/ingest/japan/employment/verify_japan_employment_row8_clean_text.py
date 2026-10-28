
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]

FILENAME = "japan_employment_coe_category34_structured.json"

CURRENT = (
    ROOT / "data/processed/japan/employment" / FILENAME
)

CANDIDATE = (
    ROOT
    / "_local_backup/japan_employment_row8_clean_review"
    / FILENAME
)

PDF = (
    ROOT
    / "data/raw/japan/employment"
    / "japan_employment_coe_pdfs/001437254.pdf"
)

HASHES = (
    ROOT
    / "data/raw/japan/employment"
    / "japan_employment_coe_pdf_hashes.json"
)

EXPECTED_CURRENT = (
    "a4ae01bce67bfaca7d8ff3d9ce309003d932597811556f71c3eee968f969b9c6"
)

EXPECTED_CANDIDATE = (
    "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce"
)

ADDED_FIELDS = {
    "clean_text_ja",
    "clean_text_source",
    "text_cleaning_status",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text):
    return "".join(text.split())


def find_work_option(dataset):
    row = next(
        item for item in dataset["documents"]
        if item["document_id"] == "JP_EM_COE_DOC_008"
    )

    return next(
        item
        for item in row["education_evidence"][
            "alternative_group"
        ]["options"]
        if item["clause"] == "イ"
    )


print("===== STEP 63-28 경력 증빙 정제 후보 검증 =====")

# 1. 입력 파일 및 SHA-256 확인
for path in [CURRENT, CANDIDATE, PDF, HASHES]:
    assert path.is_file(), f"파일 누락: {path}"

assert sha256(CURRENT) == EXPECTED_CURRENT, (
    "기존 JSON SHA-256 불일치"
)

assert sha256(CANDIDATE) == EXPECTED_CANDIDATE, (
    "후보 JSON SHA-256 불일치"
)

current = json.loads(CURRENT.read_text(encoding="utf-8"))
candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))

# 2. 기존 메타데이터 및 서류 목록 보존 검사
assert {
    key: value for key, value in current.items()
    if key != "documents"
} == {
    key: value for key, value in candidate.items()
    if key != "documents"
}, "상위 메타데이터 변경"

assert len(current["documents"]) == 8
assert len(candidate["documents"]) == 8

for old, new in zip(
    current["documents"],
    candidate["documents"],
):
    assert old["document_id"] == new["document_id"]
    assert old["row_number"] == new["row_number"]

    if old["row_number"] != 8:
        assert old == new, (
            f"8번 이외 서류 변경: {old['document_id']}"
        )

# 3. 경력 증빙 이외의 옵션은 불변
old_row8 = next(
    row for row in current["documents"]
    if row["document_id"] == "JP_EM_COE_DOC_008"
)

new_row8 = next(
    row for row in candidate["documents"]
    if row["document_id"] == "JP_EM_COE_DOC_008"
)

old_group = old_row8["education_evidence"]["alternative_group"]
new_group = new_row8["education_evidence"]["alternative_group"]

for old_option, new_option in zip(
    old_group["options"],
    new_group["options"],
):
    assert old_option["clause"] == new_option["clause"]

    if old_option["clause"] != "イ":
        assert old_option == new_option

# 4. 기존 옵션과 추가된 세 필드 비교
old_work = find_work_option(current)
new_work = find_work_option(candidate)

assert set(new_work) - set(old_work) == ADDED_FIELDS

assert {
    key: value for key, value in new_work.items()
    if key not in ADDED_FIELDS
} == old_work, "기존 경력 증빙 필드 변경"

# 새 필드를 제거하면 데이터셋 전체가 같아야 함
restored = json.loads(
    json.dumps(candidate, ensure_ascii=False)
)

restored_work = find_work_option(restored)

for field in ADDED_FIELDS:
    restored_work.pop(field)

assert restored == current, (
    "추가 필드 외 다른 데이터 변경 발견"
)

# 5. 원문과 정제 본문 비교
original = normalize(old_work["original_text_ja"])
clean = normalize(new_work["clean_text_ja"])

# PDF 추출 과정에서 혼입된 행 번호와 표 기호 확인
print("\n[원문 비교 진단]")
print("기존 조항 원문:", repr(original))
print("정제된 본문:", repr(clean))

print(
    "高等8専門学校 출현 횟수:",
    original.count("高等8専門学校")
)
print(
    "○○□ 출현 횟수:",
    original.count("○○□")
)

# 원문은 변경하지 않고 비교용 문자열만 생성
cleaned_original = original

# 행 번호 혼입이 존재하는 경우에만 제거
if "高等8専門学校" in cleaned_original:
    cleaned_original = cleaned_original.replace(
        "高等8専門学校",
        "高等専門学校",
        1,
    )

# 표의 제출 표시 기호는 본문에서 제외
if "○○□" in cleaned_original:
    cleaned_original = cleaned_original.replace(
        "○○□",
        "",
        1,
    )

print(
    "불필요한 문자 제거 후 일치:",
    cleaned_original == clean
)

assert cleaned_original == clean, (
    "정제 본문과 기존 원문의 내용이 다릅니다. "
    "원문을 임의 수정하지 말고 출력 결과를 확인하세요."
)

assert cleaned_original == clean, (
    "정제 본문과 기존 원문의 내용이 다릅니다"
)

assert not re.search(r"[○●△□]", clean)

# 6. PDF 출처 확인
hash_data = json.loads(HASHES.read_text(encoding="utf-8"))

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF.name
)

pdf_hash = sha256(PDF)

assert pdf_hash == record["sha256"]

source = new_work["clean_text_source"]

assert source["source_sha256"] == pdf_hash
assert source["pdf_filename"] == PDF.name
assert source["page"] == 1
assert source["extraction_method"] == "body_column_clip"
assert source["clip_rect"] == [100, 271.1, 370, 459.31]

assert new_work["text_cleaning_status"] == "needs_review"

print("기존 제출서류: 8개 유지")
print("8번 외 변경된 서류: 없음")
print("기존 메타데이터 및 제출 기호: 동일")
print("변경 대상: JP_EM_COE_DOC_008 / イ")
print("추가된 필드:", sorted(ADDED_FIELDS))
print("기존 원문: 보존")
print("행 번호 및 표 기호 제거 후 원문 비교: 일치")
print("정제 본문 내 표 기호: 없음")
print("PDF SHA-256: 일치")

print("\n[JSON SHA-256]")
print("현재 JSON:", sha256(CURRENT))
print("후보 JSON:", sha256(CANDIDATE))

print("\n===== STEP 63-28 최종 결과 =====")
print("수정 후보 검증: 성공")
print("기존 파일 수정: 없음")
print("정책 검증 상태: needs_review")
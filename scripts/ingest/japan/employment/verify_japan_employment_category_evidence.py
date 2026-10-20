
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

PROCESSED = ROOT / "data/processed/japan/employment"
REVIEW = ROOT / "_local_backup/japan_employment_category_evidence_review"
RAW = ROOT / "data/raw/japan/employment"

BASE_PATH = PROCESSED / "japan_employment_coe_common_structured.json"
TEXT_PATH = REVIEW / "japan_employment_coe_common_structured.json"
SPLIT_PATH = REVIEW / "japan_employment_coe_common_evidence_split.json"

PDF_PATH = RAW / "japan_employment_coe_pdfs/001404131.pdf"
HASH_PATH = RAW / "japan_employment_coe_pdf_hashes.json"

print("===== STEP 63-20 카테고리 증빙 최종 후보 검증 =====")

for path in [BASE_PATH, TEXT_PATH, SPLIT_PATH, PDF_PATH, HASH_PATH]:
    assert path.is_file(), f"파일 누락: {path}"

base = json.loads(BASE_PATH.read_text(encoding="utf-8"))
text_candidate = json.loads(TEXT_PATH.read_text(encoding="utf-8"))
split_candidate = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))

# 1. 기존 데이터셋의 상위 구조 불변 검사
for candidate in [text_candidate, split_candidate]:
    assert {
        k: v for k, v in base.items() if k != "documents"
    } == {
        k: v for k, v in candidate.items() if k != "documents"
    }, "상위 메타데이터 변경 발견"

    assert len(candidate["documents"]) == 6

# 2. 4번 서류 외에는 모든 필드 동일
for i, (original, intermediate, final) in enumerate(
    zip(
        base["documents"],
        text_candidate["documents"],
        split_candidate["documents"],
    ),
    start=1,
):
    assert original["row_number"] == i
    assert intermediate["row_number"] == i
    assert final["row_number"] == i

    assert original["document_id"] == f"JP_EM_COE_DOC_{i:03d}"

    if i != 4:
        assert original == intermediate == final, (
            f"No.{i:02d} 데이터가 변경되었습니다."
        )

# 3. 4번 서류의 추가 필드만 허용
original = base["documents"][3]
intermediate = text_candidate["documents"][3]
final = split_candidate["documents"][3]

text_added_fields = {
    "category_evidence",
    "category_evidence_source",
    "category_evidence_notes",
}

split_added_fields = {
    "category_evidence_options",
    "category_evidence_interpretation_status",
}

assert set(intermediate) - set(original) == text_added_fields
assert set(final) - set(intermediate) == split_added_fields

assert {
    k: v for k, v in intermediate.items()
    if k not in text_added_fields
} == original, "기존 4번 서류 데이터가 변경되었습니다."

assert {
    k: v for k, v in final.items()
    if k not in split_added_fields
} == intermediate, "중간 후보 데이터가 변경되었습니다."

# 4. 증빙 원문과 개수 검사
evidence = final["category_evidence"]
options = final["category_evidence_options"]

expected_counts = {"1": 4, "2": 2, "3": 1, "4": 0}

assert set(evidence) == set(expected_counts)
assert set(options) == set(expected_counts)

all_ids = []

for category, expected_count in expected_counts.items():
    items = options[category]["evidence_options"]

    assert options[category]["evidence_count"] == expected_count
    assert len(items) == expected_count

    for item in items:
        assert item["validation_status"] == "needs_review"
        assert item["source_pdf"] == "001404131.pdf"

        normalized_text = "".join(
            evidence[category]["original_text_ja"].split()
        )

        for keyword in item["source_keywords_ja"]:
            assert keyword in normalized_text, (
                f"Category {category} 근거 누락: {keyword}"
            )

        all_ids.append(item["evidence_id"])

assert len(all_ids) == 7
assert len(set(all_ids)) == 7

assert evidence["4"]["original_text_ja"] == ""
assert evidence["4"]["source_cell_status"] == "empty"
assert options["4"]["evidence_count"] == 0

# 5. 원본 PDF SHA-256 검사
hash_data = json.loads(HASH_PATH.read_text(encoding="utf-8"))

record = next(
    item for item in hash_data["files"]
    if item["filename"] == PDF_PATH.name
)

pdf_hash = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()

assert pdf_hash == record["sha256"]
assert pdf_hash == final["category_evidence_source"]["source_sha256"]
assert pdf_hash == split_candidate["source"]["source_sha256"]

# 6. 검증 결과
print("기존 제출서류:", len(base["documents"]))
print("4번 외 변경된 서류: 없음")
print("기존 상위 메타데이터: 동일")
print("기존 제출 기호: 변경 없음")
print("추가된 증빙 선택지:", len(all_ids))
print("증빙 ID 중복: 없음")
print("Category 4 원문 공란: 유지")
print("원본 PDF SHA-256: 일치")

print("\n[파일별 SHA-256]")
for label, path in [
    ("현재 JSON", BASE_PATH),
    ("중간 후보", TEXT_PATH),
    ("최종 후보", SPLIT_PATH),
]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{label}: {digest}")

print("\n최종 후보 검증: 성공")
print("기존 파일 수정: 없음")
print("정책 검증 상태: needs_review")
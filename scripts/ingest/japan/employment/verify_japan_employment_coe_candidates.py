
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

PROCESSED_DIR = ROOT / "data/processed/japan/employment"
REVIEW_DIR = ROOT / "_local_backup/japan_employment_review"

FILES = [
    "japan_employment_coe_common_structured.json",
    "japan_employment_coe_category34_structured.json",
]

EXPECTED_COUNTS = [6, 8]

print("===== STEP 63-15 수정 후보 JSON 비교 검증 =====")

total_rows = 0
changed_text_rows = []
all_ids = []

for filename, expected_count in zip(FILES, EXPECTED_COUNTS):
    original_path = PROCESSED_DIR / filename
    candidate_path = REVIEW_DIR / filename

    assert original_path.is_file(), f"기존 JSON 누락: {filename}"
    assert candidate_path.is_file(), f"후보 JSON 누락: {filename}"

    original_bytes = original_path.read_bytes()
    candidate_bytes = candidate_path.read_bytes()

    original = json.loads(original_bytes.decode("utf-8"))
    candidate = json.loads(candidate_bytes.decode("utf-8"))

    # 데이터셋 상위 메타데이터는 동일해야 함
    original_meta = {
        k: v for k, v in original.items()
        if k != "documents"
    }
    candidate_meta = {
        k: v for k, v in candidate.items()
        if k != "documents"
    }

    assert original_meta == candidate_meta, (
        f"상위 메타데이터 변경 발견: {filename}"
    )

    old_rows = original["documents"]
    new_rows = candidate["documents"]

    assert len(old_rows) == len(new_rows) == expected_count

    file_changes = 0

    for old, new in zip(old_rows, new_rows):
        assert old["document_id"] == new["document_id"]
        assert old["row_number"] == new["row_number"]

        # 수정 허용: 원문 텍스트와 추출 방식 표시만
        old_fixed = {
            k: v for k, v in old.items()
            if k not in {
                "raw_row_text_ja",
                "text_extraction_method",
            }
        }
        new_fixed = {
            k: v for k, v in new.items()
            if k not in {
                "raw_row_text_ja",
                "text_extraction_method",
            }
        }

        assert old_fixed == new_fixed, (
            f"No.{old['row_number']:02d} "
            "원문 외의 데이터가 변경되었습니다."
        )

        assert new["raw_row_text_ja"].strip()
        assert new["text_extraction_method"] == (
            "pdf_table_horizontal_boundaries"
        )

        if old["raw_row_text_ja"] != new["raw_row_text_ja"]:
            file_changes += 1
            changed_text_rows.append(old["row_number"])

        all_ids.append(new["document_id"])

    total_rows += len(new_rows)

    print("\n파일:", filename)
    print("서류 수:", len(new_rows))
    print("원문이 변경된 서류:", file_changes)
    print("서류 ID·제출 기호·메타데이터: 일치")
    print(
        "기존 JSON SHA-256:",
        hashlib.sha256(original_bytes).hexdigest(),
    )
    print(
        "후보 JSON SHA-256:",
        hashlib.sha256(candidate_bytes).hexdigest(),
    )

assert total_rows == 14
assert len(set(all_ids)) == 14

print("\n===== 최종 검증 =====")
print("전체 서류:", total_rows)
print("고유 서류 ID:", len(set(all_ids)))
print("원문 변경 서류 번호:", changed_text_rows)
print("원문 외 필드 변경: 없음")
print("기존 JSON 수정: 없음")
print("정책 검증 상태: needs_review")
print("수정 후보 비교 검증: 성공")
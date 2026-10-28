
from pathlib import Path
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[4]

PROCESSED = ROOT / "data/processed/japan/employment"
REVIEW = ROOT / "_local_backup/japan_employment_category_evidence_review"
BACKUP = ROOT / "_local_backup/japan_employment_before_category_evidence"

FILENAME = "japan_employment_coe_common_structured.json"

CURRENT_PATH = PROCESSED / FILENAME
CANDIDATE_PATH = REVIEW / "japan_employment_coe_common_evidence_split.json"
BACKUP_PATH = BACKUP / FILENAME
TEMP_PATH = PROCESSED / (FILENAME + ".pending")

# STEP 63-20에서 확인된 SHA-256
EXPECTED_CURRENT = (
    "fc7e47d8d3a4d14203ab98300548a5a0fbc6ee7e552a52ac1cbda90de8ebbcd6"
)

EXPECTED_CANDIDATE = (
    "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


print("===== STEP 63-21 카테고리 증빙 최종 반영 =====")

# 1. 파일 존재 여부 및 기존 파일 보호
assert CURRENT_PATH.is_file(), "기존 JSON 누락"
assert CANDIDATE_PATH.is_file(), "최종 후보 JSON 누락"
assert not BACKUP_PATH.exists(), "백업 파일이 이미 존재합니다"
assert not TEMP_PATH.exists(), "임시 파일이 이미 존재합니다"

# 2. STEP 63-20에서 확인한 해시와 비교
assert sha256(CURRENT_PATH) == EXPECTED_CURRENT, (
    "현재 JSON SHA-256 불일치"
)
assert sha256(CANDIDATE_PATH) == EXPECTED_CANDIDATE, (
    "후보 JSON SHA-256 불일치"
)

current = json.loads(CURRENT_PATH.read_text(encoding="utf-8"))
candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))

assert current["route_id"] == candidate["route_id"] == "JP-EM"
assert current["document_count"] == candidate["document_count"] == 6
assert current["validation_status"] == candidate["validation_status"] == "needs_review"

# 3. 4번 이외 모든 데이터가 동일한지 검사
assert {
    k: v for k, v in current.items() if k != "documents"
} == {
    k: v for k, v in candidate.items() if k != "documents"
}

for old_row, new_row in zip(
    current["documents"],
    candidate["documents"],
):
    assert old_row["document_id"] == new_row["document_id"]

    if old_row["row_number"] != 4:
        assert old_row == new_row
    else:
        assert {
            k: v for k, v in new_row.items()
            if k not in {
                "category_evidence",
                "category_evidence_source",
                "category_evidence_notes",
                "category_evidence_options",
                "category_evidence_interpretation_status",
            }
        } == old_row

        counts = {
            cat: data["evidence_count"]
            for cat, data in new_row["category_evidence_options"].items()
        }

        assert counts == {"1": 4, "2": 2, "3": 1, "4": 0}

print("사전 SHA-256 및 데이터 정합성 검증: 성공")

# 4. 기존 파일 백업
BACKUP.mkdir(parents=True, exist_ok=True)

with BACKUP_PATH.open("xb") as f:
    f.write(CURRENT_PATH.read_bytes())

assert sha256(BACKUP_PATH) == EXPECTED_CURRENT, (
    "백업 SHA-256 검증 실패"
)

print("기존 파일 백업:", BACKUP_PATH.relative_to(ROOT))
print("백업 SHA-256 검증: 성공")

# 5. 후보를 임시 파일에 복사하여 검증
with TEMP_PATH.open("xb") as f:
    f.write(CANDIDATE_PATH.read_bytes())

assert sha256(TEMP_PATH) == EXPECTED_CANDIDATE, (
    "임시 파일 SHA-256 불일치"
)

# 6. 백업과 현재 파일을 다시 확인한 후 교체
assert sha256(BACKUP_PATH) == EXPECTED_CURRENT
assert sha256(CURRENT_PATH) == EXPECTED_CURRENT

os.replace(TEMP_PATH, CURRENT_PATH)

# 7. 최종 파일 검증
assert sha256(CURRENT_PATH) == EXPECTED_CANDIDATE, (
    "교체 후 SHA-256 불일치"
)

final = json.loads(CURRENT_PATH.read_text(encoding="utf-8"))
assert len(final["documents"]) == 6

row4 = next(
    row for row in final["documents"]
    if row["document_id"] == "JP_EM_COE_DOC_004"
)

assert "category_evidence" in row4
assert "category_evidence_options" in row4

print("\n===== STEP 63-21 최종 결과 =====")
print("수정 반영:", CURRENT_PATH.relative_to(ROOT))
print("기존 JSON 백업: 성공")
print("최종 SHA-256:", sha256(CURRENT_PATH))
print("전체 제출서류:", len(final["documents"]))
print("카테고리별 증빙 선택지: 7개")
print("서류 ID 및 제출 기호: 변경 없음")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")
print("최종 반영: 성공")
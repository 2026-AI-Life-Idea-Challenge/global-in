
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[4]

FILENAME = "japan_employment_coe_category34_structured.json"

CURRENT = ROOT / "data/processed/japan/employment" / FILENAME

CANDIDATE = (
    ROOT
    / "_local_backup/japan_employment_row8_clean_review"
    / FILENAME
)

BACKUP = (
    ROOT
    / "_local_backup/japan_employment_before_row8_clean"
    / FILENAME
)

TEMP = CURRENT.with_name(CURRENT.name + ".pending")

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


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def get_work_option(dataset):
    row8 = next(
        row for row in dataset["documents"]
        if row["document_id"] == "JP_EM_COE_DOC_008"
    )

    return next(
        option
        for option in row8["education_evidence"][
            "alternative_group"
        ]["options"]
        if option["clause"] == "イ"
    )


print("===== STEP 63-29 정제된 경력 증빙 최종 반영 =====")

# 1. 입력 파일 검사
assert CURRENT.is_file(), "기존 JSON 누락"
assert CANDIDATE.is_file(), "수정 후보 JSON 누락"
assert not BACKUP.exists(), "백업이 이미 존재합니다"
assert not TEMP.exists(), "임시 파일이 이미 존재합니다"

assert sha256(CURRENT) == EXPECTED_CURRENT, (
    "기존 JSON SHA-256 불일치"
)

assert sha256(CANDIDATE) == EXPECTED_CANDIDATE, (
    "수정 후보 SHA-256 불일치"
)

current = load_json(CURRENT)
candidate = load_json(CANDIDATE)

# 2. 변경 범위 검증
assert current["route_id"] == candidate["route_id"] == "JP-EM"
assert len(current["documents"]) == len(candidate["documents"]) == 8

# 후보에서 새 필드 3개만 제거하면 기존 JSON과 완전히 같아야 함
restored = json.loads(
    json.dumps(candidate, ensure_ascii=False)
)

restored_work = get_work_option(restored)
candidate_work = get_work_option(candidate)
current_work = get_work_option(current)

assert set(candidate_work) - set(current_work) == ADDED_FIELDS

for field in ADDED_FIELDS:
    assert field in restored_work
    restored_work.pop(field)

assert restored == current, (
    "정제 필드 외 다른 데이터 변경 발견"
)

# 3. 경력 증빙 원문 검증
original = "".join(current_work["original_text_ja"].split())
clean = "".join(candidate_work["clean_text_ja"].split())

assert original.count("○○□") == 1
assert original.replace("○○□", "", 1) == clean

assert "○" not in clean
assert "□" not in clean

assert candidate_work["text_cleaning_status"] == "needs_review"
assert (
    candidate_work["clean_text_source"]["extraction_method"]
    == "body_column_clip"
)

print("사전 SHA-256 및 데이터 정합성 검사: 성공")

# 4. 기존 JSON 백업
BACKUP.parent.mkdir(parents=True, exist_ok=True)

with BACKUP.open("xb") as f:
    f.write(CURRENT.read_bytes())

assert sha256(BACKUP) == EXPECTED_CURRENT, (
    "백업 SHA-256 불일치"
)

print("백업 검증:", BACKUP.relative_to(ROOT))

# 5. 수정 후보를 임시 파일에 복사
with TEMP.open("xb") as f:
    f.write(CANDIDATE.read_bytes())

assert sha256(TEMP) == EXPECTED_CANDIDATE, (
    "임시 파일 SHA-256 불일치"
)

# 최종 교체 전 재검증
assert sha256(CURRENT) == EXPECTED_CURRENT
assert sha256(BACKUP) == EXPECTED_CURRENT

# 6. 최종 반영
os.replace(TEMP, CURRENT)

assert sha256(CURRENT) == EXPECTED_CANDIDATE, (
    "최종 JSON SHA-256 불일치"
)

final = load_json(CURRENT)
final_work = get_work_option(final)

assert final_work["clean_text_ja"] == (
    candidate_work["clean_text_ja"]
)

print("수정 반영:", CURRENT.relative_to(ROOT))

print("\n===== STEP 63-29 최종 결과 =====")
print("기존 JSON 백업: 성공")
print("최종 SHA-256:", sha256(CURRENT))
print("전체 제출서류:", len(final["documents"]))
print("정제 대상: JP_EM_COE_DOC_008 / イ")
print("정제 본문 문자 수:", len(final_work["clean_text_ja"]))
print("표 기호 혼입: 없음")
print("기존 일본어 원문: 보존")
print("다른 서류 및 제출 기호: 변경 없음")
print("수정 후보 JSON: 보존")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")
print("최종 반영: 성공")
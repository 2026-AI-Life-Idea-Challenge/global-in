
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[4]

FILENAME = "japan_employment_coe_category34_structured.json"

CURRENT = (
    ROOT / "data/processed/japan/employment" / FILENAME
)

CANDIDATE = (
    ROOT
    / "_local_backup/japan_employment_education_review"
    / FILENAME
)

BACKUP = (
    ROOT
    / "_local_backup/japan_employment_before_education_evidence"
    / FILENAME
)

TEMP = CURRENT.with_name(CURRENT.name + ".pending")

EXPECTED_CURRENT = (
    "e8d699ddb82a0c45846ccfa2700d0228ffac7a0a230e3cc6c1d92ee712f6555f"
)

EXPECTED_CANDIDATE = (
    "a4ae01bce67bfaca7d8ff3d9ce309003d932597811556f71c3eee968f969b9c6"
)

ADDED_FIELD = "education_evidence"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


print("===== STEP 63-25 학력·경력 증빙 최종 반영 =====")

# 1. 사전 검사
assert CURRENT.is_file(), "기존 JSON이 없습니다."
assert CANDIDATE.is_file(), "수정 후보 JSON이 없습니다."
assert not BACKUP.exists(), "기존 백업이 이미 존재합니다."
assert not TEMP.exists(), "이전 임시 파일이 존재합니다."

assert sha256(CURRENT) == EXPECTED_CURRENT, (
    "기존 JSON SHA-256 불일치"
)
assert sha256(CANDIDATE) == EXPECTED_CANDIDATE, (
    "수정 후보 JSON SHA-256 불일치"
)

current = load_json(CURRENT)
candidate = load_json(CANDIDATE)

# 2. 기존 데이터 보존 확인
assert current["route_id"] == candidate["route_id"] == "JP-EM"
assert current["document_count"] == candidate["document_count"] == 8
assert len(current["documents"]) == len(candidate["documents"]) == 8

assert {
    k: v for k, v in current.items() if k != "documents"
} == {
    k: v for k, v in candidate.items() if k != "documents"
}, "상위 메타데이터가 변경되었습니다."

for old, new in zip(
    current["documents"],
    candidate["documents"],
):
    assert old["row_number"] == new["row_number"]
    assert old["document_id"] == new["document_id"]

    if old["row_number"] != 8:
        assert old == new, (
            f"8번 이외 서류 변경: {old['document_id']}"
        )
    else:
        assert ADDED_FIELD not in old
        assert set(new) - set(old) == {ADDED_FIELD}

        without_added = {
            k: v for k, v in new.items()
            if k != ADDED_FIELD
        }
        assert without_added == old

        evidence = new[ADDED_FIELD]
        assert evidence["validation_status"] == "needs_review"

        group = evidence["alternative_group"]
        assert group["source_relation"] == "いずれか"

        options = group["options"]
        assert len(options) == 4

        assert [x["clause"] for x in options] == [
            "ア", "イ", "ウ", "エ"
        ]

        assert {
            x["clause"]
            for x in options
            if "exception_original_ja" in x
        } == {"ウ", "エ"}

        ids = [
            evidence["resume"]["evidence_id"]
        ] + [
            x["evidence_id"] for x in options
        ]

        assert len(ids) == len(set(ids)) == 5

print("사전 SHA-256 및 데이터 정합성 검사: 성공")

# 3. 백업 - 기존 파일은 덮어쓰지 않음
BACKUP.parent.mkdir(parents=True, exist_ok=True)

with BACKUP.open("xb") as f:
    f.write(CURRENT.read_bytes())

assert sha256(BACKUP) == EXPECTED_CURRENT, (
    "백업 SHA-256 검증 실패"
)

print("백업 검증:", BACKUP.relative_to(ROOT))

# 4. 임시 파일 생성 및 검증
with TEMP.open("xb") as f:
    f.write(CANDIDATE.read_bytes())

assert sha256(TEMP) == EXPECTED_CANDIDATE, (
    "임시 파일 SHA-256 불일치"
)

# 반영 직전 기존 파일 재확인
assert sha256(CURRENT) == EXPECTED_CURRENT
assert sha256(BACKUP) == EXPECTED_CURRENT

# 5. 최종 JSON 교체
os.replace(TEMP, CURRENT)

assert sha256(CURRENT) == EXPECTED_CANDIDATE, (
    "최종 JSON SHA-256 검증 실패"
)

final = load_json(CURRENT)

row8 = next(
    row for row in final["documents"]
    if row["document_id"] == "JP_EM_COE_DOC_008"
)

assert ADDED_FIELD in row8

print("수정 반영:", CURRENT.relative_to(ROOT))

print("\n===== STEP 63-25 최종 결과 =====")
print("기존 JSON 백업: 성공")
print("최종 SHA-256:", sha256(CURRENT))
print("전체 제출서류:", len(final["documents"]))
print("이력서 증빙:", 1)
print(
    "대체 증빙:",
    len(row8[ADDED_FIELD]["alternative_group"]["options"])
)
print("명시적 예외: 2")
print("서류 ID 및 제출 기호: 변경 없음")
print("기존 버전 복구용 백업: 보존")
print("수정 후보 JSON: 보존")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")
print("최종 반영: 성공")
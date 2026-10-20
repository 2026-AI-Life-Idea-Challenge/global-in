
from pathlib import Path
import hashlib
import json
import os
import shutil

ROOT = Path(__file__).resolve().parents[4]

PROCESSED = ROOT / "data/processed/japan/employment"
REVIEW = ROOT / "_local_backup/japan_employment_review"
BACKUP = ROOT / "_local_backup/japan_employment_before_row_fix"

# STEP 63-15에서 검증한 정확한 해시
EXPECTED = {
    "japan_employment_coe_common_structured.json": {
        "old": "22d4b2319d0c7215115e69e0eb39c76e28c2d76bf5e61d14bc57761830441e1b",
        "new": "fc7e47d8d3a4d14203ab98300548a5a0fbc6ee7e552a52ac1cbda90de8ebbcd6",
        "count": 6,
    },
    "japan_employment_coe_category34_structured.json": {
        "old": "1744c27775c08422586cc9b4f668b9e37a3c6288f6c9074e78f3dac2d6b8573d",
        "new": "e8d699ddb82a0c45846ccfa2700d0228ffac7a0a230e3cc6c1d92ee712f6555f",
        "count": 8,
    },
}

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

print("===== STEP 63-16 COE JSON 백업 및 수정 반영 =====")

# 모든 파일을 먼저 검증
for name, spec in EXPECTED.items():
    old = PROCESSED / name
    new = REVIEW / name
    backup = BACKUP / name

    assert old.is_file(), f"기존 파일 누락: {name}"
    assert new.is_file(), f"수정 후보 누락: {name}"
    assert not backup.exists(), f"백업 목적지에 이미 파일 존재: {backup}"

    assert sha256(old) == spec["old"], f"기존 JSON 해시 불일치: {name}"
    assert sha256(new) == spec["new"], f"후보 JSON 해시 불일치: {name}"

    old_data = json.loads(old.read_text(encoding="utf-8"))
    new_data = json.loads(new.read_text(encoding="utf-8"))

    assert len(old_data["documents"]) == spec["count"]
    assert len(new_data["documents"]) == spec["count"]

    # STEP 63-15와 동일한 불변 필드 검사
    assert {
        k: v for k, v in old_data.items() if k != "documents"
    } == {
        k: v for k, v in new_data.items() if k != "documents"
    }

    for a, b in zip(old_data["documents"], new_data["documents"]):
        assert {
            k: v for k, v in a.items()
            if k not in ("raw_row_text_ja", "text_extraction_method")
        } == {
            k: v for k, v in b.items()
            if k not in ("raw_row_text_ja", "text_extraction_method")
        }

print("사전 SHA-256 및 데이터 정합성 검사: 성공")

BACKUP.mkdir(parents=True, exist_ok=True)

# 기존 파일을 백업하고 해시 재확인
for name, spec in EXPECTED.items():
    old = PROCESSED / name
    backup = BACKUP / name

    with backup.open("xb") as f:
        f.write(old.read_bytes())

    assert sha256(backup) == spec["old"], f"백업 검증 실패: {name}"
    print("백업 검증:", backup.relative_to(ROOT))

# 모든 백업이 검증된 후 수정 후보 적용
for name, spec in EXPECTED.items():
    destination = PROCESSED / name
    source = REVIEW / name
    temporary = PROCESSED / (name + ".pending")

    assert not temporary.exists(), f"임시 파일 이미 존재: {temporary}"
    assert sha256(destination) == spec["old"], "교체 직전 기존 해시 변경"

    with temporary.open("xb") as f:
        f.write(source.read_bytes())

    assert sha256(temporary) == spec["new"], "임시 파일 해시 불일치"

    os.replace(temporary, destination)

    assert sha256(destination) == spec["new"], "교체 후 해시 불일치"
    print("수정 반영:", destination.relative_to(ROOT))

print("\n===== STEP 63-16 최종 결과 =====")
print("기존 JSON 백업:", len(EXPECTED), "개")
print("수정 JSON 반영:", len(EXPECTED), "개")
print("전체 제출서류: 14개")
print("서류 ID 및 제출 기호: 변경 없음")
print("기존 버전 복구용 백업: 보존")
print("수정 후보 JSON: 보존")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")

from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"
SCRIPT = (
    ROOT / "scripts/ingest/japan/employment/"
    "integrate_japan_employment_renewal.py"
)

INPUTS = {
    "japan_employment_renewal_structured.json":
        "ed24d73198981d6885cfa5fdb98a92cc2ca3acc06e5dfd4c8e73553e4f3e62ef",
    "japan_employment_renewal_category_evidence.json":
        "27db1ad63a15ba5b2c4a0e9946983ffd6656fef7e21b58d5b5152e3240317b7a",
    "japan_employment_renewal_dispatch_evidence.json":
        "3f735ab9b7c7c9581c38e83e0a176c321cebe6e413575a1b661e75e9c7691df5",
    "japan_employment_renewal_activity_evidence.json":
        "67421741ccb63c4a3b5dd105588cba5479353ef9c9c0037d8fedadd981d153db",
    "japan_employment_renewal_tax_evidence.json":
        "f48361c0db679f78c276e4a3cf7da0d48ddf8f87d6d83c204ff83ed551036447",
}

OUTPUT_NAME = "japan_employment_renewal_integrated.json"

EXPECTED_OUTPUT_SHA = (
    "b6ddc5500f9f5c51f62ea329bd0dfa04"
    "cb7e7a6c5710eb6fa98fd1bd92a94ffc"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


print("===== STEP 63-85 Renewal 재현성 검증 =====")

# 1. 기존 파일의 해시 기준 확보
original_output = BASE / OUTPUT_NAME

assert SCRIPT.is_file(), "통합 스크립트 누락"
assert original_output.is_file(), "통합 JSON 누락"

original_paths = [
    SCRIPT,
    original_output,
    *[BASE / name for name in INPUTS],
]

baseline = {}

for path in original_paths:
    assert path.is_file(), f"파일 누락: {path}"
    baseline[path] = sha256(path)

assert baseline[original_output] == EXPECTED_OUTPUT_SHA

for name, expected_hash in INPUTS.items():
    assert baseline[BASE / name] == expected_hash, (
        f"입력 SHA-256 불일치: {name}"
    )

print("[PASS] 기존 입력 5개 및 통합 결과 SHA-256")

# 2. 임시 프로젝트 환경 생성
with tempfile.TemporaryDirectory() as tmp:
    temp_root = Path(tmp) / "global-in"

    temp_base = (
        temp_root / "data/processed/japan/employment"
    )
    temp_scripts = (
        temp_root / "scripts/ingest/japan/employment"
    )

    temp_base.mkdir(parents=True)
    temp_scripts.mkdir(parents=True)

    for name in INPUTS:
        shutil.copy2(BASE / name, temp_base / name)

    temp_script = temp_scripts / SCRIPT.name
    shutil.copy2(SCRIPT, temp_script)

    # 임시 환경에 기존 통합 출력은 복사하지 않음
    temp_output = temp_base / OUTPUT_NAME

    assert not temp_output.exists()

    print("[PASS] 독립 임시 환경 구성")

    # 3. 통합 스크립트 재실행
    result = subprocess.run(
        [sys.executable, str(temp_script)],
        cwd=temp_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(
            "임시 환경에서 통합 스크립트 실행 실패"
        )

    assert temp_output.is_file()

    print("[PASS] 임시 환경에서 통합 JSON 재생성")

    # 4. SHA-256 및 JSON 데이터 비교
    reproduced_hash = sha256(temp_output)

    assert reproduced_hash == EXPECTED_OUTPUT_SHA, (
        "재생성 SHA-256 불일치"
    )

    assert temp_output.read_bytes() == (
        original_output.read_bytes()
    ), "재생성 파일 바이트 불일치"

    original_data = json.loads(
        original_output.read_text(encoding="utf-8")
    )

    reproduced_data = json.loads(
        temp_output.read_text(encoding="utf-8")
    )

    assert original_data == reproduced_data

    print("[PASS] 재생성 JSON SHA-256 일치")
    print("[PASS] 재생성 파일 바이트 완전 일치")
    print("[PASS] JSON 데이터 내용 일치")

# 5. 기존 파일 불변성 확인
for path, expected_hash in baseline.items():
    assert sha256(path) == expected_hash, (
        f"기존 파일 변경 감지: {path}"
    )

print("[PASS] 기존 JSON·통합 스크립트 불변")

print("\n===== STEP 63-85 최종 결과 =====")
print("신청 유형: renewal")
print("입력 JSON: 5개")
print("독립 임시 환경 재실행: 성공")
print("재생성 SHA-256:", reproduced_hash)
print("기존 통합 JSON과 바이트 일치: PASS")
print("기존 입력·출력·스크립트 변경: 없음")
print("자동 자격 판정: 비활성화")
print("정책 검증 상태: needs_review")
print("Git 커밋·푸시: 미실행")
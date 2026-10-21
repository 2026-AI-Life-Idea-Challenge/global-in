
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
    "build_japan_employment_retrieval_records.py"
)

OUTPUT_NAME = "japan_employment_retrieval_records.jsonl"
OUTPUT = BASE / OUTPUT_NAME

EXPECTED_SHA = (
    "d782f3618d46c951f21a305f40ef72e9"
    "825ee14d77084cad59fb22689c8d8be8"
)

INPUTS = {
    "japan_employment_coe_common_structured.json":
        "9c504f14fd5ce7a2551d9f85f727cf9721c1db17e46da48dfa1a8a96966a4a68",
    "japan_employment_coe_category34_structured.json":
        "4a54617aab5e41f3d32ab70595c9d82bc2ae11ebc4e0aff03bc324e0fac8a6ce",
    "japan_employment_change_integrated.json":
        "6e3fbddc14dc408ee73064211b0eef9c36d08f8652095c0bd5811bd86b1f0cc7",
    "japan_employment_renewal_integrated.json":
        "b6ddc5500f9f5c51f62ea329bd0dfa04cb7e7a6c5710eb6fa98fd1bd92a94ffc",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


print("===== STEP 63-96 JSONL 재현성 검증 =====")

# 1. 기존 파일 확인 및 해시 기록
assert SCRIPT.is_file(), "생성 스크립트 누락"
assert OUTPUT.is_file(), "기존 JSONL 누락"

original_paths = [SCRIPT, OUTPUT]

for filename in INPUTS:
    original_paths.append(BASE / filename)

baseline = {}

for path in original_paths:
    assert path.is_file(), f"파일 누락: {path}"
    baseline[path] = sha256(path)

assert baseline[OUTPUT] == EXPECTED_SHA
print("[PASS] 기존 JSONL SHA-256")

for filename, expected in INPUTS.items():
    path = BASE / filename
    assert baseline[path] == expected, (
        f"입력 JSON SHA-256 불일치: {filename}"
    )

print("[PASS] 입력 JSON 4개 SHA-256")

# 2. 독립 임시 프로젝트 환경 구성
with tempfile.TemporaryDirectory() as temp_dir:
    temp_root = Path(temp_dir) / "global-in"

    temp_base = (
        temp_root / "data/processed/japan/employment"
    )
    temp_scripts = (
        temp_root / "scripts/ingest/japan/employment"
    )

    temp_base.mkdir(parents=True)
    temp_scripts.mkdir(parents=True)

    for filename in INPUTS:
        shutil.copy2(
            BASE / filename,
            temp_base / filename
        )

    temp_script = temp_scripts / SCRIPT.name
    shutil.copy2(SCRIPT, temp_script)

    temp_output = temp_base / OUTPUT_NAME
    assert not temp_output.exists()

    print("[PASS] 독립 임시 환경 구성")

    # 3. 실제 생성 스크립트 재실행
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
            "임시 환경에서 JSONL 재생성 실패"
        )

    assert temp_output.is_file()
    print("[PASS] 임시 환경에서 JSONL 재생성")

    # 4. 바이트 및 해시 비교
    reproduced_sha = sha256(temp_output)

    assert reproduced_sha == EXPECTED_SHA, (
        "재생성 JSONL SHA-256 불일치"
    )

    original_bytes = OUTPUT.read_bytes()
    reproduced_bytes = temp_output.read_bytes()

    assert reproduced_bytes == original_bytes, (
        "기존 JSONL과 바이트 단위 불일치"
    )

    assert reproduced_bytes.count(b"\n") == 35
    assert b"\r\n" not in reproduced_bytes
    assert reproduced_bytes.endswith(b"\n")

    print("[PASS] JSONL SHA-256 완전 일치")
    print("[PASS] 바이트 단위 완전 일치")
    print("[PASS] UTF-8 / LF 및 35줄 확인")

    # 5. JSONL 레코드 내용 검증
    records = [
        json.loads(line)
        for line in reproduced_bytes.decode(
            "utf-8"
        ).splitlines()
    ]

    assert len(records) == 35

    ids = [record["record_id"] for record in records]
    assert len(set(ids)) == 35

    assert all(
        record["record_id"] == record["document_id"]
        and record["route_id"] == "JP-EM"
        and record["validation_status"] == "needs_review"
        and record["automatic_eligibility_rules_enabled"] is False
        for record in records
    )

    assert sum(
        bool(record["evidence"])
        for record in records
    ) == 9

    print("[PASS] 레코드 35개 및 상세 증빙 9개")

# 6. 실제 프로젝트 파일 변경 여부 확인
for path, expected_sha in baseline.items():
    assert sha256(path) == expected_sha, (
        f"기존 파일 변경 감지: {path}"
    )

print("[PASS] 기존 입력·출력·스크립트 불변")

print("\n===== STEP 63-96 최종 결과 =====")
print("검색 레코드: 35개")
print("고유 문서 ID: 35개")
print("상세 증빙 연결: 9개")
print("독립 임시 환경 재실행: PASS")
print("재생성 SHA-256:", reproduced_sha)
print("기존 JSONL과 바이트 일치: PASS")
print("기존 파일 변경: 없음")
print("정책 검증 상태: needs_review")
print("자동 자격 판정: 비활성화")
print("임베딩 생성·DB 적재: 미실행")
print("Git 커밋·푸시: 미실행")
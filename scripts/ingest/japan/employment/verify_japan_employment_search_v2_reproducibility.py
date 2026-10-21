
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
    ROOT / "scripts/ingest/japan/employment"
    / "build_japan_employment_search_text_v2.py"
)

INPUT = BASE / "japan_employment_retrieval_records.jsonl"

OUTPUT = BASE / "japan_employment_search_ready_v2.jsonl"

V1 = BASE / "japan_employment_search_ready.jsonl"

INPUT_SHA = (
    "d782f3618d46c951f21a305f40ef72e9"
    "825ee14d77084cad59fb22689c8d8be8"
)

OUTPUT_SHA = (
    "030ec57531c9c852d2d436388743c2e0"
    "5b6e6d84ec7ad78091e7dfeead304c87"
)

V1_SHA = (
    "6549dce07b8e751dcbee42028b0af7f"
    "c25701a7e7424d85874530c3f41f1ce43"
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path):
    raw = path.read_bytes()

    assert raw.endswith(b"\n"), f"마지막 LF 누락: {path}"
    assert b"\r\n" not in raw, f"CRLF 발견: {path}"

    return [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
    ]


print("===== STEP 63-101 v2 검색 본문 재현성 검증 =====")

# 1. 기존 파일 무결성 검증
original_files = {
    "script": SCRIPT,
    "input": INPUT,
    "v1": V1,
    "v2": OUTPUT,
}

baseline = {}

for name, path in original_files.items():
    assert path.is_file(), f"파일 누락: {name} / {path}"
    baseline[name] = sha256(path)

assert baseline["input"] == INPUT_SHA
assert baseline["v1"] == V1_SHA
assert baseline["v2"] == OUTPUT_SHA

print("[PASS] 기존 Source / v1 / v2 SHA-256")

# 2. 독립 임시 환경 구성
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

    temp_input = temp_base / INPUT.name
    temp_output = temp_base / OUTPUT.name
    temp_script = temp_scripts / SCRIPT.name

    shutil.copy2(INPUT, temp_input)
    shutil.copy2(SCRIPT, temp_script)
    # v2 shares its pure extraction function with the original v1 module.
    shutil.copy2(SCRIPT.with_name("build_japan_employment_search_text.py"), temp_scripts / "build_japan_employment_search_text.py")

    assert sha256(temp_input) == INPUT_SHA
    assert not temp_output.exists()

    print("[PASS] 독립 임시 환경 구성")

    # 3. v2 생성 스크립트 실제 재실행
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
            "독립 환경에서 v2 JSONL 재생성 실패"
        )

    assert temp_output.is_file()

    print("[PASS] 독립 환경에서 v2 JSONL 재생성")

    # 4. 출력 SHA 및 바이트 비교
    reproduced_sha = sha256(temp_output)

    assert reproduced_sha == OUTPUT_SHA, (
        "v2 재생성 SHA-256 불일치"
    )

    assert temp_output.read_bytes() == OUTPUT.read_bytes(), (
        "v2 JSONL 바이트 단위 불일치"
    )

    print("[PASS] 재생성 SHA-256 완전 일치")
    print("[PASS] 재생성 파일 바이트 완전 일치")

    # 5. 검색 레코드 구조 확인
    records = load_jsonl(temp_output)

    assert len(records) == 35
    assert len({r["document_id"] for r in records}) == 35

    assert sum(
        bool(r["evidence"]) for r in records
    ) == 9

    segment_count = sum(
        len(r["evidence_search_segments"])
        for r in records
    )

    assert segment_count == 66

    assert all(
        r["search_text_ja"] == r["raw_text_ja"]
        and r["validation_status"] == "needs_review"
        and r["automatic_eligibility_rules_enabled"] is False
        and r["embedding_generated"] is False
        for r in records
    )

    print("[PASS] 검색 레코드 35개")
    print("[PASS] 증빙 연결 9개 및 세그먼트 66개")
    print("[PASS] 자동 판정·임베딩 생성 비활성화")

# 6. 기존 프로젝트 파일 불변성 확인
for name, path in original_files.items():
    assert sha256(path) == baseline[name], (
        f"기존 파일 변경 감지: {name}"
    )

print("[PASS] 기존 입력·출력·스크립트 불변")

print("\n===== STEP 63-101 최종 결과 =====")
print("신청 유형: COE / Change / Renewal")
print("검색 레코드: 35개")
print("상세 증빙 연결: 9개")
print("증빙 원문 세그먼트: 66개")
print("독립 임시 환경 재실행: PASS")
print("재생성 SHA-256:", reproduced_sha)
print("기존 v2 JSONL과 바이트 일치: PASS")
print("기존 프로젝트 파일 변경: 없음")
print("정책 검증 상태: needs_review")
print("자동 자격 판정: 비활성화")
print("임베딩 생성·DB 적재: 미실행")
print("Git 커밋·푸시: 미실행")
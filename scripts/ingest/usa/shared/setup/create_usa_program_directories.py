
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]

RAW_BASE = ROOT / "data/raw/usa"
PROCESSED_BASE = ROOT / "data/processed/usa"
CRAWL_BASE = ROOT / "scripts/crawl/usa"
INGEST_BASE = ROOT / "scripts/ingest/usa"

MANIFEST = RAW_BASE / "usa_program_source_manifest.json"
SNAPSHOT_INDEX = (
    RAW_BASE / "source_snapshots/snapshot_index.json"
)

EXPECTED_MANIFEST_SHA = (
    "52489441fd37a75b07045d9a252a478"
    "9a144fc65d19275da8a9ca05620adaf31"
)

EXPECTED_INDEX_SHA = (
    "7db1f2c5b0b1b4a63c4db1355791880"
    "fec1ef851e253b61f756a899395c97831"
)

# program_id -> 프로그램별 상대 경로
PROGRAM_PATHS = {
    "US-WH-01": "working_holiday/summer_work_travel",
    "US-ST-01": "student/f1_academic_student",
    "US-ST-03": "student/j1_college_university_student",
    "US-EM-01": "employment/h1b_specialty_occupations",
    "US-EM-02": "employment/j1_intern",
    "US-EM-03": "employment/j1_trainee",
    "US-WEST-01": "employment/west",
}

SHARED_PATHS = {
    "raw": [
        "shared/source_manifest",
        "shared/visa_procedures",
    ],
    "processed": [
        "shared",
    ],
    "crawl": [
        "shared",
    ],
    "ingest": [
        "shared",
    ],
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_snapshot_hashes(index):
    hashes = {}

    for snapshot in index["snapshots"]:
        path = (
            RAW_BASE
            / "source_snapshots"
            / snapshot["filename"]
        )

        assert path.is_file(), f"원본 스냅샷 누락: {path}"
        assert path.resolve().parent == (
            RAW_BASE / "source_snapshots"
        ).resolve()

        actual_sha = sha256(path)

        assert actual_sha == snapshot["sha256"], (
            f"원본 스냅샷 SHA 불일치: {path}"
        )

        hashes[path] = actual_sha

    return hashes


print("===== STEP 64-04A 미국 프로그램 디렉터리 생성 =====")

# 1. 기존 데이터 무결성 확인
assert MANIFEST.is_file()
assert SNAPSHOT_INDEX.is_file()

assert sha256(MANIFEST) == EXPECTED_MANIFEST_SHA
assert sha256(SNAPSHOT_INDEX) == EXPECTED_INDEX_SHA

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
index = json.loads(
    SNAPSHOT_INDEX.read_text(encoding="utf-8")
)

assert manifest["program_count"] == 7
assert set(PROGRAM_PATHS) == {
    p["program_id"] for p in manifest["programs"]
}
assert index["snapshot_count"] == 5

existing_hashes = {
    MANIFEST: sha256(MANIFEST),
    SNAPSHOT_INDEX: sha256(SNAPSHOT_INDEX),
}

existing_hashes.update(
    collect_snapshot_hashes(index)
)

print("[PASS] Manifest / Snapshot Index SHA-256")
print("[PASS] 기존 HTML 5개 SHA-256")

# 2. 생성할 디렉터리 목록
directories = []

BASES = {
    "raw": RAW_BASE,
    "processed": PROCESSED_BASE,
    "crawl": CRAWL_BASE,
    "ingest": INGEST_BASE,
}

for kind, base in BASES.items():
    for relative in PROGRAM_PATHS.values():
        directories.append(base / relative)

    for relative in SHARED_PATHS[kind]:
        directories.append(base / relative)

# 중복 경로 제거
directories = list(dict.fromkeys(directories))

# 프로젝트 루트 밖의 경로를 생성하지 않도록 확인
for path in directories:
    assert path.resolve().is_relative_to(
        ROOT.resolve()
    ), f"허용되지 않은 경로: {path}"

# 3. 디렉터리 생성
created = []
already_exists = []

for path in directories:
    if path.is_dir():
        already_exists.append(path)
    else:
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)

# 4. 생성 결과 확인
assert all(path.is_dir() for path in directories)

print("[PASS] 프로그램별 디렉터리 생성")
print("[PASS] 공통 출처 디렉터리 생성")

print("\n[생성 결과]")
print("관리 대상 디렉터리:", len(directories))
print("새로 생성:", len(created))
print("기존 디렉터리:", len(already_exists))

print("\n[프로그램별 경로]")
for program_id, relative in PROGRAM_PATHS.items():
    print(f"{program_id}: {relative}")

# 5. 기존 파일 변경 여부 확인
for path, original_sha in existing_hashes.items():
    assert path.is_file()
    assert sha256(path) == original_sha, (
        f"기존 파일 변경 감지: {path}"
    )

print("\n[PASS] 기존 Manifest 불변")
print("[PASS] 기존 Snapshot Index 불변")
print("[PASS] 기존 HTML 5개 불변")

# 6. 최종 결과
print("\n===== STEP 64-04A 최종 결과 =====")
print("대상 프로그램:", len(PROGRAM_PATHS))
print("관리 대상 디렉터리:", len(directories))
print("새로 생성된 디렉터리:", len(created))
print("기존 원본 파일 변경: 없음")
print("기존 파일 이동·삭제: 없음")
print("새 JSON 생성: 없음")
print("자동 자격 판정: 비활성화 유지")
print("Git 커밋·푸시: 미실행")

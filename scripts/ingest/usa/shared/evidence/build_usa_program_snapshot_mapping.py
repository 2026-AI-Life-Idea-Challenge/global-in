
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]

RAW_BASE = ROOT / "data/raw/usa"

MANIFEST = RAW_BASE / "usa_program_source_manifest.json"

SNAPSHOT_DIR = RAW_BASE / "source_snapshots"
INDEX = SNAPSHOT_DIR / "snapshot_index.json"

OUTPUT = (
    RAW_BASE
    / "shared/source_manifest"
    / "usa_program_snapshot_mapping.json"
)

EXPECTED_MANIFEST_SHA = (
    "52489441fd37a75b07045d9a252a478"
    "9a144fc65d19275da8a9ca05620adaf31"
)

EXPECTED_INDEX_SHA = (
    "7db1f2c5b0b1b4a63c4db1355791880"
    "fec1ef851e253b61f756a899395c97831"
)

PROGRAM_PATHS = {
    "US-WH-01": "working_holiday/summer_work_travel",
    "US-ST-01": "student/f1_academic_student",
    "US-ST-03": "student/j1_college_university_student",
    "US-EM-01": "employment/h1b_specialty_occupations",
    "US-EM-02": "employment/j1_intern",
    "US-EM-03": "employment/j1_trainee",
    "US-WEST-01": "employment/west",
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_verified_json(path, expected_hash):
    assert path.is_file(), f"파일 없음: {path}"

    raw = path.read_bytes()
    assert sha256(raw) == expected_hash, (
        f"SHA-256 불일치: {path}"
    )

    return json.loads(raw.decode("utf-8")), raw


print("===== STEP 64-04B 프로그램별 HTML 연결 =====")

# 1. 기존 원본 검증
manifest, manifest_raw = read_verified_json(
    MANIFEST, EXPECTED_MANIFEST_SHA
)

index, index_raw = read_verified_json(
    INDEX, EXPECTED_INDEX_SHA
)

assert manifest["program_count"] == 7
assert index["snapshot_count"] == 5
assert len(index["snapshots"]) == 5

programs = {
    item["program_id"]: item
    for item in manifest["programs"]
}

assert set(programs) == set(PROGRAM_PATHS)

print("[PASS] Manifest 및 Snapshot Index SHA-256")
print("[PASS] 프로그램 ID 7개")

# 2. 프로그램별 공식 출처 URL 연결
source_to_programs = {}

for program in manifest["programs"]:
    program_id = program["program_id"]

    for source in program["sources"]:
        url = source["url"]
        source_to_programs.setdefault(url, []).append(
            program_id
        )

# 3. HTML 스냅샷 및 SHA-256 검증
snapshot_by_url = {}
original_hashes = {}

for item in index["snapshots"]:
    url = item["source_url"]
    filename = item["filename"]

    assert url not in snapshot_by_url, (
        f"중복 스냅샷 URL: {url}"
    )
    assert Path(filename).name == filename, (
        f"잘못된 스냅샷 파일명: {filename}"
    )

    assert url in source_to_programs, (
        f"Manifest에 없는 출처: {url}"
    )

    path = SNAPSHOT_DIR / filename
    assert path.is_file(), f"HTML 누락: {path}"

    digest = sha256(path.read_bytes())
    assert digest == item["sha256"], (
        f"HTML SHA-256 불일치: {path}"
    )

    snapshot_by_url[url] = item
    original_hashes[path] = digest

assert len(snapshot_by_url) == 5

print("[PASS] 공식 HTML 5개 SHA-256")

# 4. 프로그램별 매핑 작성
mapping_programs = []
linked_snapshots = 0

for program_id, relative_dir in PROGRAM_PATHS.items():
    program = programs[program_id]

    raw_program_dir = RAW_BASE / relative_dir
    processed_program_dir = (
        ROOT / "data/processed/usa" / relative_dir
    )

    assert raw_program_dir.is_dir(), (
        f"Raw 프로그램 폴더 없음: {raw_program_dir}"
    )
    assert processed_program_dir.is_dir(), (
        f"Processed 프로그램 폴더 없음: "
        f"{processed_program_dir}"
    )

    references = []

    for source in program["sources"]:
        url = source["url"]
        snapshot = snapshot_by_url.get(url)

        if snapshot is None:
            references.append({
                "source_url": url,
                "snapshot_status": "not_collected",
                "snapshot_path": None,
                "snapshot_sha256": None,
            })
            continue

        snapshot_path = (
            SNAPSHOT_DIR / snapshot["filename"]
        )

        references.append({
            "source_url": url,
            "snapshot_status": "collected_needs_review",
            "snapshot_path": snapshot_path.relative_to(
                ROOT
            ).as_posix(),
            "snapshot_sha256": snapshot["sha256"],
        })

        linked_snapshots += 1

    mapping_programs.append({
        "program_id": program_id,
        "route_id": program["route_id"],
        "official_program_name": (
            program["official_program_name"]
        ),
        "visa_classification": (
            program["visa_classification"]
        ),
        "raw_program_dir": raw_program_dir.relative_to(
            ROOT
        ).as_posix(),
        "processed_program_dir": (
            processed_program_dir.relative_to(ROOT).as_posix()
        ),
        "sources": references,
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
    })

# Manifest에서 프로그램별 출처 12개가 모두 연결되어야 함
assert sum(
    len(item["sources"])
    for item in mapping_programs
) == 12

# HTML 5개는 각기 다른 프로그램에 연결됨
assert linked_snapshots == 5

print("[PASS] 출처 12개 매핑")
print("[PASS] 수집된 HTML 5개 프로그램 연결")

# 5. 결과 JSON 생성
output_data = {
    "dataset_id": "USA_PROGRAM_SNAPSHOT_MAPPING_V1",
    "country": "US",
    "source_manifest_sha256": EXPECTED_MANIFEST_SHA,
    "snapshot_index_sha256": EXPECTED_INDEX_SHA,
    "program_count": 7,
    "source_link_count": 12,
    "linked_snapshot_count": 5,
    "validation_status": "needs_review",
    "automatic_eligibility_rules_enabled": False,
    "programs": mapping_programs,
}

payload = (
    json.dumps(
        output_data,
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
).encode("utf-8")

assert OUTPUT.parent.is_dir(), (
    "공통 Manifest 디렉터리가 없습니다."
)

# 기존 파일 덮어쓰기 방지
with OUTPUT.open("xb") as f:
    f.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == output_data

print("[PASS] 프로그램 매핑 JSON 저장")

# 6. 기존 파일 불변 검증
assert MANIFEST.read_bytes() == manifest_raw
assert INDEX.read_bytes() == index_raw

for path, original_sha in original_hashes.items():
    assert sha256(path.read_bytes()) == original_sha

print("[PASS] 기존 Manifest / Index 불변")
print("[PASS] 기존 공식 HTML 5개 불변")

print("\n[프로그램별 스냅샷 연결]")

for item in mapping_programs:
    count = sum(
        source["snapshot_status"]
        == "collected_needs_review"
        for source in item["sources"]
    )

    print(
        item["program_id"],
        "->",
        item["raw_program_dir"],
        f"({count}개 HTML)"
    )

print("\n===== STEP 64-04B 최종 결과 =====")
print("프로그램:", len(mapping_programs))
print("출처 연결:", 12)
print("기존 HTML 연결:", linked_snapshots)
print("매핑 파일:", OUTPUT.relative_to(ROOT))
print("매핑 SHA-256:", sha256(payload))
print("기존 파일 변경: 없음")
print("파일 이동·복사·삭제: 없음")
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
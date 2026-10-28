
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa"
PROCESSED = ROOT / "data/processed/usa"

MANIFEST = RAW / "usa_program_source_manifest.json"
INDEX = RAW / "source_snapshots/snapshot_index.json"
MAPPING = (
    RAW / "shared/source_manifest"
    / "usa_program_snapshot_mapping.json"
)

EXPECTED_HASHES = {
    MANIFEST: (
        "52489441fd37a75b07045d9a252a478"
        "9a144fc65d19275da8a9ca05620adaf31"
    ),
    INDEX: (
        "7db1f2c5b0b1b4a63c4db1355791880"
        "fec1ef851e253b61f756a899395c97831"
    ),
    MAPPING: (
        "3f62fad51e20449940bb02cd0f6b0e"
        "bd84e83944586973f00600a35cbae34e4d"
    ),
}

PROGRAM_PATHS = {
    "US-WH-01": "working_holiday/summer_work_travel",
    "US-ST-01": "student/f1_academic_student",
    "US-ST-03": "student/j1_college_university_student",
    "US-EM-01": "employment/h1b_specialty_occupations",
    "US-EM-02": "employment/j1_intern",
    "US-EM-03": "employment/j1_trainee",
    "US-WEST-01": "employment/west",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_verified(path):
    assert path.is_file(), f"파일 없음: {path}"
    assert digest(path) == EXPECTED_HASHES[path], (
        f"SHA-256 불일치: {path}"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def safe_project_path(value):
    path = ROOT / value
    assert path.resolve().is_relative_to(ROOT.resolve())
    return path


print("===== STEP 64-04C 스냅샷 매핑 독립 검증 =====")

manifest = read_verified(MANIFEST)
index = read_verified(INDEX)
mapping = read_verified(MAPPING)

print("[PASS] Manifest / Index / Mapping SHA-256")

assert manifest["program_count"] == 7
assert manifest["source_link_count"] == 12
assert index["snapshot_count"] == 5

assert mapping["program_count"] == 7
assert mapping["source_link_count"] == 12
assert mapping["linked_snapshot_count"] == 5

assert mapping["source_manifest_sha256"] == EXPECTED_HASHES[MANIFEST]
assert mapping["snapshot_index_sha256"] == EXPECTED_HASHES[INDEX]

assert mapping["validation_status"] == "needs_review"
assert mapping["automatic_eligibility_rules_enabled"] is False

print("[PASS] 상위 메타데이터 일치")

original_programs = {
    p["program_id"]: p
    for p in manifest["programs"]
}

mapped_programs = {
    p["program_id"]: p
    for p in mapping["programs"]
}

assert len(original_programs) == 7
assert len(mapped_programs) == 7
assert set(original_programs) == set(mapped_programs)
assert set(mapped_programs) == set(PROGRAM_PATHS)

snapshots = {
    s["source_url"]: s
    for s in index["snapshots"]
}

assert len(snapshots) == 5

tracked_files = {
    path: digest(path)
    for path in EXPECTED_HASHES
}

snapshot_paths = set()

for snapshot in snapshots.values():
    path = (
        RAW / "source_snapshots"
        / snapshot["filename"]
    )

    assert path.is_file()
    assert path.resolve().parent == (
        RAW / "source_snapshots"
    ).resolve()
    assert digest(path) == snapshot["sha256"]

    snapshot_paths.add(path)
    tracked_files[path] = digest(path)

print("[PASS] 원본 HTML 5개 SHA-256")

linked = 0
not_collected = 0
linked_by_program = Counter()
seen_snapshots = set()

for program_id, mapped in mapped_programs.items():
    original = original_programs[program_id]
    relative = PROGRAM_PATHS[program_id]

    assert mapped["route_id"] == original["route_id"]
    assert mapped["official_program_name"] == (
        original["official_program_name"]
    )
    assert mapped["visa_classification"] == (
        original["visa_classification"]
    )
    assert mapped["validation_status"] == "needs_review"
    assert mapped["automatic_eligibility_rules_enabled"] is False

    expected_raw = (
        RAW / relative
    ).relative_to(ROOT).as_posix()

    expected_processed = (
        PROCESSED / relative
    ).relative_to(ROOT).as_posix()

    assert mapped["raw_program_dir"] == expected_raw
    assert mapped["processed_program_dir"] == expected_processed

    assert safe_project_path(expected_raw).is_dir()
    assert safe_project_path(expected_processed).is_dir()

    original_sources = original["sources"]
    mapped_sources = mapped["sources"]

    assert len(original_sources) == len(mapped_sources)

    for src, ref in zip(original_sources, mapped_sources):
        url = src["url"]
        assert ref["source_url"] == url

        if url in snapshots:
            snapshot = snapshots[url]
            expected_path = (
                RAW / "source_snapshots"
                / snapshot["filename"]
            ).relative_to(ROOT).as_posix()

            assert ref["snapshot_status"] == (
                "collected_needs_review"
            )
            assert ref["snapshot_path"] == expected_path
            assert ref["snapshot_sha256"] == snapshot["sha256"]

            actual_path = safe_project_path(ref["snapshot_path"])
            assert actual_path.is_file()
            assert digest(actual_path) == ref["snapshot_sha256"]

            linked += 1
            linked_by_program[program_id] += 1
            seen_snapshots.add(url)

        else:
            assert ref["snapshot_status"] == "not_collected"
            assert ref["snapshot_path"] is None
            assert ref["snapshot_sha256"] is None
            not_collected += 1

assert linked == 5
assert not_collected == 7
assert seen_snapshots == set(snapshots)

assert dict(linked_by_program) == {
    "US-WH-01": 1,
    "US-ST-03": 1,
    "US-EM-02": 1,
    "US-EM-03": 1,
    "US-WEST-01": 1,
}

print("[PASS] 7개 프로그램 경로 일치")
print("[PASS] 공식 출처 12개 연결 일치")
print("[PASS] HTML 5개 연결 및 파일 해시 일치")
print("[PASS] 미수집 출처 연결 7개 유지")

for path, original_hash in tracked_files.items():
    assert digest(path) == original_hash, (
        f"파일 변경 감지: {path}"
    )

print("[PASS] 기존 Manifest / Index / Mapping / HTML 불변")

print("\n===== STEP 64-04C 최종 결과 =====")
print("프로그램:", len(mapped_programs))
print("공식 출처 연결:", linked + not_collected)
print("연결된 HTML:", linked)
print("미수집 출처 연결:", not_collected)
print("검증된 원본 HTML:", len(snapshot_paths))
print("기존 파일 변경: 없음")
print("신규 데이터 저장: 없음")
print("정책 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")

from pathlib import Path
from collections import Counter
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa"

MANIFEST = RAW / "usa_program_source_manifest.json"
INDEX = RAW / "source_snapshots/snapshot_index.json"
MAPPING = (
    RAW / "shared/source_manifest"
    / "usa_program_snapshot_mapping.json"
)

EXPECTED = {
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

SHARED = RAW / "shared/source_manifest"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_file(path, expected):
    assert path.is_file(), f"파일 없음: {path}"
    actual = sha256(path.read_bytes())
    assert actual == expected, (
        f"SHA-256 불일치: {path}\n"
        f"Expected: {expected}\nActual: {actual}"
    )


def serialize(data):
    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")


def safe_path(relative):
    path = ROOT / relative
    assert path.resolve().is_relative_to(
        ROOT.resolve()
    ), f"프로젝트 외부 경로: {relative}"
    return path


print("===== STEP 64-12 미국 원본 파일 배치 =====")

# 1. 기존 핵심 데이터 검증
original_hashes = dict(EXPECTED)

for path, expected_hash in EXPECTED.items():
    verify_file(path, expected_hash)

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
index = json.loads(INDEX.read_text(encoding="utf-8"))
mapping = json.loads(MAPPING.read_text(encoding="utf-8"))

assert manifest["program_count"] == 7
assert index["snapshot_count"] == 5
assert mapping["program_count"] == 7
assert mapping["source_link_count"] == 12
assert mapping["linked_snapshot_count"] == 5
assert (
    mapping["source_manifest_sha256"]
    == EXPECTED[MANIFEST]
)
assert (
    mapping["snapshot_index_sha256"]
    == EXPECTED[INDEX]
)

programs = {
    p["program_id"]: p
    for p in mapping["programs"]
}

assert len(programs) == 7
assert set(programs) == set(PROGRAM_PATHS)

snapshots = {
    s["source_url"]: s
    for s in index["snapshots"]
}

assert len(snapshots) == 5

for snapshot in snapshots.values():
    filename = snapshot["filename"]

    assert Path(filename).name == filename
    path = RAW / "source_snapshots" / filename

    assert path.resolve().parent == (
        RAW / "source_snapshots"
    ).resolve()

    verify_file(path, snapshot["sha256"])
    original_hashes[path] = snapshot["sha256"]

print("[PASS] Manifest / Index / Mapping 무결성")
print("[PASS] 원본 HTML 5개 SHA-256")

# 2. 파일 배치 계획 수립
# 저장 전에 전부 검사하고 계획을 메모리에 준비
planned = []
program_copy_count = Counter()

for program_id, relative in PROGRAM_PATHS.items():
    program = programs[program_id]
    target_dir = RAW / relative

    assert target_dir.is_dir(), (
        f"프로그램 폴더 없음: {target_dir}"
    )

    assert program["raw_program_dir"] == (
        target_dir.relative_to(ROOT).as_posix()
    )

    source_records = []

    for source in program["sources"]:
        url = source["source_url"]
        status = source["snapshot_status"]

        if status == "not_collected":
            assert source["snapshot_path"] is None
            assert source["snapshot_sha256"] is None

            source_records.append({
                "source_url": url,
                "collection_status": "not_collected",
                "local_file": None,
                "sha256": None,
            })
            continue

        assert status == "collected_needs_review"
        assert url in snapshots

        snapshot = snapshots[url]
        original_path = safe_path(
            source["snapshot_path"]
        )

        verify_file(
            original_path,
            source["snapshot_sha256"]
        )

        assert source["snapshot_sha256"] == (
            snapshot["sha256"]
        )

        # 각 프로그램 폴더에서 직접 확인할 HTML
        destination = target_dir / "official_source.html"

        planned.append((
            destination,
            original_path.read_bytes(),
        ))

        program_copy_count[program_id] += 1

        source_records.append({
            "source_url": url,
            "collection_status": (
                "collected_needs_review"
            ),
            "local_file": (
                destination.relative_to(ROOT).as_posix()
            ),
            "sha256": snapshot["sha256"],
            "original_snapshot": (
                original_path.relative_to(ROOT).as_posix()
            ),
        })

    # 프로그램별 출처 정보
    registry = {
        "dataset_type": "program_official_sources",
        "country": "US",
        "program_id": program_id,
        "route_id": program["route_id"],
        "official_program_name": (
            program["official_program_name"]
        ),
        "visa_classification": (
            program["visa_classification"]
        ),
        "source_manifest_sha256": EXPECTED[MANIFEST],
        "snapshot_mapping_sha256": EXPECTED[MAPPING],
        "sources": source_records,
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
    }

    planned.append((
        target_dir / "official_sources.json",
        serialize(registry),
    ))

# 3. 공통 출처 문서도 shared에 배치
assert SHARED.is_dir()

planned.append((
    SHARED / "usa_program_source_manifest.json",
    MANIFEST.read_bytes(),
))

planned.append((
    SHARED / "snapshot_index.json",
    INDEX.read_bytes(),
))

# 4. 계획 검증
assert sum(program_copy_count.values()) == 5
assert len(planned) == 14, (
    f"예상 배치 파일 14개, 실제 {len(planned)}개"
)

paths = [path for path, _ in planned]
assert len(paths) == len(set(paths))

# 기존 출력이 있을 때 내용이 다르면 중단
# 정상적인 재실행이라면 일치 여부만 확인
for path, content in planned:
    assert path.resolve().is_relative_to(
        RAW.resolve()
    )

    assert path.parent.is_dir()

    if path.exists():
        assert path.is_file(), (
            f"파일이 아닌 경로 존재: {path}"
        )
        assert path.read_bytes() == content, (
            f"기존 파일 내용 다름: {path}"
        )

print("[PASS] 14개 파일 배치 계획 검증")
print("[PASS] 기존 파일 충돌 사전 검사")

# 5. 파일 배치
created = []
already_exists = []

for path, content in planned:
    if path.exists():
        already_exists.append(path)
        continue

    with path.open("xb") as f:
        f.write(content)

    created.append(path)

# 6. 전체 배치 결과 검증
for path, expected_content in planned:
    assert path.is_file()
    assert sha256(path.read_bytes()) == sha256(
        expected_content
    )

for path, expected_hash in original_hashes.items():
    verify_file(path, expected_hash)

print("[PASS] 프로그램별 원본 파일 배치")
print("[PASS] 배치 파일 SHA-256 대조")
print("[PASS] 기존 원본 불변")

# 7. 프로그램별 결과 출력
print("\n[프로그램별 배치 현황]")

for program_id, relative in PROGRAM_PATHS.items():
    folder = RAW / relative
    html = folder / "official_source.html"
    registry = folder / "official_sources.json"

    assert registry.is_file()

    print(
        f"{program_id}",
        f"| HTML: {'있음' if html.is_file() else '미수집'}",
        "|",
        folder.relative_to(ROOT),
    )

print("\n===== STEP 64-12 최종 결과 =====")
print("프로그램 폴더:", len(PROGRAM_PATHS))
print("HTML 배치:", sum(program_copy_count.values()))
print("프로그램 출처 JSON:", 7)
print("공통 출처 파일 배치:", 2)
print("전체 배치 파일:", len(planned))
print("신규 생성:", len(created))
print("이미 존재:", len(already_exists))
print("SHA-256 검증: PASS")
print("기존 Manifest / Index / Mapping 불변: PASS")
print("기존 HTML 스냅샷 불변: PASS")
print("원본 삭제·이동: 없음")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
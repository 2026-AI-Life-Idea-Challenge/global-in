
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa"
PROCESSED = ROOT / "data/processed/usa"

MAPPING = RAW / (
    "shared/source_manifest/"
    "usa_program_snapshot_mapping.json"
)

REPORT = (
    PROCESSED / "shared/"
    "usa_seven_programs_audit.json"
)

H1B_V2 = (
    PROCESSED / "employment/"
    "h1b_specialty_occupations/"
    "official_evidence_v2.json"
)

EXPECTED_MAPPING_SHA = (
    "3f62fad51e20449940bb02cd0f6b0e"
    "bd84e83944586973f00600a35cbae34e4d"
)

PROGRAMS = {
    "US-WH-01": {
        "folder": "working_holiday/summer_work_travel",
        "evidence": "official_evidence.json",
        "sha": "7f509a5e67dfde3afa3a247fb4c533520b69c1c165ba9eb1d19e1a3524d39171",
        "expected_sections": 19,
    },
    "US-ST-01": {
        "folder": "student/f1_academic_student",
        "evidence": "official_evidence.json",
        "sha": "4e2cbbb4b99d17a378e4bac1701bd57b1d1a340d536fd9e92c1d9899f2f26fa4",
        "expected_sources": 2,
    },
    "US-ST-03": {
        "folder": "student/j1_college_university_student",
        "evidence": "official_evidence.json",
        "sha": "c2881ea19ce10dce1d4450758f803193614aadac0fc9b724c1be52f40a82b01e",
        "expected_sections": 10,
    },
    "US-EM-01": {
        "folder": "employment/h1b_specialty_occupations",
        "evidence": "official_evidence.json",
        "sha": "5055c6fafb9907b8fa621e50cf9ff5a2943b3587924eab38b86016b1e08e87d2",
        "expected_sources": 2,
    },
    "US-EM-02": {
        "folder": "employment/j1_intern",
        "evidence": "official_evidence.json",
        "sha": "6133401913510314b9847f4ba315bff1da32d03943b565bb1c50a898c7419124",
        "expected_sections": 13,
    },
    "US-EM-03": {
        "folder": "employment/j1_trainee",
        "evidence": "official_evidence.json",
        "sha": "d34f1b698bc2a7e50cd0387967166df4cc86bf89dff5f91d30b797cc1b8ccf95",
        "expected_sections": 13,
    },
    "US-WEST-01": {
        "folder": "employment/west",
        "evidence": "west_2026_first_half_full_review_data.json",
        "sha": "b3e781e89880996cc88a93a3618cc164794fdba9914ade9499111390bc108bc2",
    },
}

WEST_REVIEWED = (
    PROCESSED / "employment/west/"
    "west_2026_first_half_reviewed_data.json"
)

WEST_REVIEWED_SHA = (
    "c26e6d1b8295709062fd2b1df142764"
    "375569ad5d9784145d3f12bf9b126c67d"
)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def serialize(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def read_verified(path, expected_sha):
    assert path.is_file(), f"파일 없음: {path}"

    raw = path.read_bytes()

    assert sha256(raw) == expected_sha, (
        f"SHA-256 불일치: {path}"
    )

    return json.loads(raw.decode("utf-8")), raw


print("===== STEP 64-20 미국 7개 프로그램 통합 검증 =====")

# 1. 저장 경로 사전 확인
assert REPORT.parent.is_dir()
assert H1B_V2.parent.is_dir()

if REPORT.exists():
    raise FileExistsError("기존 통합 리포트 존재")
if H1B_V2.exists():
    raise FileExistsError("기존 H-1B v2 파일 존재")

mapping, mapping_raw = read_verified(
    MAPPING, EXPECTED_MAPPING_SHA
)

mapped = {
    p["program_id"]: p
    for p in mapping["programs"]
}

assert len(mapped) == 7
assert set(mapped) == set(PROGRAMS)

print("[PASS] 프로그램 매핑 7개")

# 2. 프로그램별 원본 연결 및 JSON 검증
records = []
original_files = {MAPPING: sha256(mapping_raw)}
h1b_original = None

for program_id, config in PROGRAMS.items():
    raw_folder = RAW / config["folder"]
    processed_folder = PROCESSED / config["folder"]

    assert raw_folder.is_dir()
    assert processed_folder.is_dir()

    registry_path = raw_folder / "official_sources.json"
    assert registry_path.is_file()

    registry_raw = registry_path.read_bytes()
    registry = json.loads(registry_raw.decode("utf-8"))

    assert registry["program_id"] == program_id
    assert (
        registry["automatic_eligibility_rules_enabled"]
        is False
    )

    original_files[registry_path] = sha256(registry_raw)

    evidence_path = (
        processed_folder / config["evidence"]
    )

    evidence, evidence_raw = read_verified(
        evidence_path, config["sha"]
    )

    assert evidence["program_id"] == program_id
    assert (
        evidence["automatic_eligibility_rules_enabled"]
        is False
    )

    original_files[evidence_path] = config["sha"]

    assert mapped[program_id]["raw_program_dir"] == (
        raw_folder.relative_to(ROOT).as_posix()
    )
    assert mapped[program_id]["processed_program_dir"] == (
        processed_folder.relative_to(ROOT).as_posix()
    )

    program_result = {
        "program_id": program_id,
        "raw_dir": raw_folder.relative_to(ROOT).as_posix(),
        "processed_dir": (
            processed_folder.relative_to(ROOT).as_posix()
        ),
        "evidence_file": (
            evidence_path.relative_to(ROOT).as_posix()
        ),
        "evidence_sha256": config["sha"],
        "file_integrity": "pass",
        "semantic_validation": "needs_review",
    }

    if "expected_sections" in config:
        sections = evidence["sections"]
        assert len(sections) == config["expected_sections"]

        # 원문 섹션 해시 재검증
        for section in sections:
            assert sha256(
                section["source_text"].encode("utf-8")
            ) == section["source_text_sha256"]

        program_result["section_count"] = len(sections)

        source_html = raw_folder / "official_source.html"
        assert source_html.is_file()

        assert sha256(
            source_html.read_bytes()
        ) == evidence["source_html_sha256"]

        original_files[source_html] = sha256(
            source_html.read_bytes()
        )

    elif "expected_sources" in config:
        sources = evidence["sources"]
        assert len(sources) == config["expected_sources"]

        total_blocks = 0

        for source in sources:
            html_path = ROOT / source["source_file"]

            assert html_path.is_file()
            assert html_path.resolve().parent == (
                raw_folder.resolve()
            )

            assert sha256(
                html_path.read_bytes()
            ) == source["source_sha256"]

            original_files[html_path] = (
                source["source_sha256"]
            )

            assert sha256(
                source["body_text"].encode("utf-8")
            ) == source["body_text_sha256"]

            for block in source["evidence_blocks"]:
                assert sha256(
                    block["source_text"].encode("utf-8")
                ) == block["source_text_sha256"]

            total_blocks += len(source["evidence_blocks"])

        program_result["source_count"] = len(sources)
        program_result["evidence_block_count"] = total_blocks

        if program_id == "US-EM-01":
            h1b_original = evidence

    else:
        # WEST: 기존 부분 검수 데이터와 PDF를 함께 검증
        west_reviewed, _ = read_verified(
            WEST_REVIEWED, WEST_REVIEWED_SHA
        )

        original_files[WEST_REVIEWED] = (
            WEST_REVIEWED_SHA
        )

        assert west_reviewed["program_id"] == program_id

        pdf_path = ROOT / evidence["source_pdf_path"]
        assert pdf_path.is_file()
        assert sha256(
            pdf_path.read_bytes()
        ) == evidence["source_pdf_sha256"]

        original_files[pdf_path] = (
            evidence["source_pdf_sha256"]
        )

        program_result["review_status"] = (
            evidence["validation_status"]
        )

    records.append(program_result)

    print(f"[PASS] {program_id}: 파일·해시·출처 연결")

assert len(records) == 7

# 3. H-1B Cap Season 분류 오류 수정본 생성
assert h1b_original is not None

h1b_v2 = json.loads(
    json.dumps(h1b_original, ensure_ascii=False)
)

fixed_count = 0

for source in h1b_v2["sources"]:
    url = source["source_url"].rstrip("/")

    if url.endswith("/h-1b-cap-season"):
        source["source_type"] = "h1b_cap_season_guidance"
        fixed_count += 1

    elif url.endswith("/h-1b-specialty-occupations"):
        source["source_type"] = (
            "h1b_specialty_occupations_guidance"
        )

    else:
        raise AssertionError(
            f"예상하지 못한 H-1B URL: {url}"
        )

assert fixed_count == 1

h1b_v2["dataset_version"] = 2
h1b_v2["derived_from_sha256"] = PROGRAMS[
    "US-EM-01"
]["sha"]

h1b_v2["source_type_validation"] = (
    "url_path_checked"
)

h1b_v2["validation_status"] = "needs_review"
h1b_v2["automatic_eligibility_rules_enabled"] = False

h1b_v2_payload = serialize(h1b_v2)

assert json.loads(
    h1b_v2_payload.decode("utf-8")
) == h1b_v2

print("[PASS] H-1B Cap Season 출처 유형 수정")

# 4. 통합 감사 리포트
audit = {
    "dataset_type": "usa_seven_programs_audit",
    "country": "US",
    "program_count": 7,
    "source_mapping_sha256": EXPECTED_MAPPING_SHA,
    "programs": records,
    "h1b_source_type_correction": {
        "old_file_sha256": PROGRAMS[
            "US-EM-01"
        ]["sha"],
        "new_file_path": (
            H1B_V2.relative_to(ROOT).as_posix()
        ),
        "new_file_sha256": sha256(h1b_v2_payload),
        "corrected_count": fixed_count,
    },
    "structural_validation": "pass",
    "semantic_validation": "needs_review",
    "automatic_eligibility_rules_enabled": False,
    "embedding_generated": False,
    "database_loaded": False,
}

audit_payload = serialize(audit)

# 5. 저장 및 즉시 재검증
with H1B_V2.open("xb") as f:
    f.write(h1b_v2_payload)

with REPORT.open("xb") as f:
    f.write(audit_payload)

assert H1B_V2.read_bytes() == h1b_v2_payload
assert REPORT.read_bytes() == audit_payload

assert json.loads(
    H1B_V2.read_text(encoding="utf-8")
) == h1b_v2

assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == audit

# 6. 기존 파일 불변 확인
for path, previous_hash in original_files.items():
    assert sha256(path.read_bytes()) == previous_hash, (
        f"기존 파일 변경 감지: {path}"
    )

print("[PASS] 전체 JSON 저장·재읽기")
print("[PASS] 기존 원본 파일 불변")

print("\n===== STEP 64-20 최종 결과 =====")
print("검증 프로그램:", len(records))
print("H-1B 분류 수정:", fixed_count, "개")
print("H-1B v2:", H1B_V2.relative_to(ROOT))
print("H-1B v2 SHA-256:", sha256(h1b_v2_payload))
print("통합 리포트:", REPORT.relative_to(ROOT))
print("리포트 SHA-256:", sha256(audit_payload))
print("프로그램 구조 검증: PASS")
print("프로그램별 출처 연결: PASS")
print("기존 데이터 변경: 없음")
print("정책·의미 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
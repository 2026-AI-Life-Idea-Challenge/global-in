
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
RAW = ROOT / "data/raw/usa"
PROCESSED = ROOT / "data/processed/usa"

MAPPING = (
    RAW / "shared/source_manifest/"
    "usa_program_snapshot_mapping.json"
)

MAPPING_SHA = (
    "3f62fad51e20449940bb02cd0f6b0e"
    "bd84e83944586973f00600a35cbae34e4d"
)

PROGRAMS = {
    "US-WH-01": {
        "folder": "working_holiday/summer_work_travel",
        "heading": "Summer Work Travel",
        "source_json_sha": (
            "e3900b9d8ebc3df9296747aeaad87a248"
            "5372aed6c4d81c59af6d169ed2b4d56"
        ),
    },
    "US-ST-03": {
        "folder": "student/j1_college_university_student",
        "heading": "College and University Student",
        "source_json_sha": (
            "f8805cb64a85e3d5c772475b93272b5c4"
            "a874cfd1fcd0d6d34981844f0c4f914"
        ),
    },
    "US-EM-02": {
        "folder": "employment/j1_intern",
        "heading": "Intern",
        "source_json_sha": (
            "225bc8427ad550813a86eb63c6eca381e"
            "9d10ad9978f1b3bb3ba47827ee91976"
        ),
    },
    "US-EM-03": {
        "folder": "employment/j1_trainee",
        "heading": "Trainee",
        "source_json_sha": (
            "0fe21ab727dbc460a6bb484810cebc997e"
            "db227a969b68e2542728d925a71c48"
        ),
    },
}

CATEGORY_PATTERNS = {
    "participants_and_eligibility": [
        r"participants?",
        r"\bstudents? must\b",
        r"\binterns? must\b",
        r"\btrainees? must\b",
    ],
    "benefits": [
        r"\bbenefits?\b",
    ],
    "restrictions": [
        r"limitations?",
        r"exceptions?",
        r"exclusions?",
        r"restrictions?",
        r"program length",
        r"readmittance",
    ],
    "program_sponsors": [
        r"sponsors?",
    ],
    "hosts_and_employers": [
        r"\bhosts?\b",
        r"\bemployers?\b",
    ],
    "occupational_categories": [
        r"occupational categories",
        r"occupational fields",
    ],
    "related_information": [
        r"more information",
        r"resources?",
        r"initiatives?",
        r"community support",
        r"map of",
        r"report abuse",
    ],
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def serialize(obj):
    return (
        json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def normalize(text):
    return " ".join(text.split())


def classify_heading(heading):
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, heading, re.IGNORECASE):
                return category

    return "program_description_or_other"


def build_evidence(program_id, config, source):
    sections = []

    for index, section in enumerate(source["sections"]):
        heading = normalize(section["heading"])
        original = section["raw_text"]

        assert isinstance(original, str)
        assert isinstance(heading, str)
        assert heading

        sections.append({
            "evidence_id": (
                f"{program_id}-SECTION-{index + 1:03d}"
            ),
            "section_index": index,
            "heading": heading,
            "heading_tag": section["heading_tag"],
            "category_candidate": classify_heading(heading),
            "source_text": original,
            "source_text_sha256": sha256(
                original.encode("utf-8")
            ),
            "source_text_length": len(original),
            "source_url": source["source"]["source_url"],
            "source_html_sha256": (
                source["source"]["snapshot_sha256"]
            ),
            "semantic_review_status": "needs_review",
            "legal_interpretation_status": "not_reviewed",
        })

    assert sections
    assert sections[0]["heading"] == config["heading"]

    category_counts = dict(sorted(Counter(
        section["category_candidate"]
        for section in sections
    ).items()))

    return {
        "dataset_type": "bridgeusa_official_evidence",
        "country": "US",
        "program_id": program_id,
        "official_program_name": source[
            "official_program_name"
        ],
        "route_id": source["route_id"],
        "visa_classification": source[
            "visa_classification"
        ],
        "source_url": source["source"]["source_url"],
        "source_html_sha256": (
            source["source"]["snapshot_sha256"]
        ),
        "source_content_sha256": (
            config["source_json_sha"]
        ),
        "source_section_count": len(sections),
        "category_counts": category_counts,
        "sections": sections,
        "category_assignment_method": (
            "heading_keyword_classification"
        ),
        "content_scope": (
            "extracted_sections_require_review"
        ),
        "section_boundaries_verified": False,
        "eligibility_rules_verified": False,
        "validation_status": "needs_review",
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }


print("===== STEP 64-16 BridgeUSA 공식 근거 일괄 구축 =====")

# 1. 매핑 무결성
mapping_raw = MAPPING.read_bytes()
assert sha256(mapping_raw) == MAPPING_SHA

mapping = json.loads(mapping_raw.decode("utf-8"))
mapped = {
    item["program_id"]: item
    for item in mapping["programs"]
}

assert len(mapped) == 7

print("[PASS] 미국 프로그램 매핑 무결성")

# 2. 네 프로그램의 전체 결과를 저장 전에 준비
prepared = []
originals = {MAPPING: mapping_raw}

for program_id, config in PROGRAMS.items():
    folder = config["folder"]

    source_path = (
        PROCESSED / folder / "source_content.json"
    )
    html_path = RAW / folder / "official_source.html"
    registry_path = RAW / folder / "official_sources.json"

    output_path = (
        PROCESSED / folder / "official_evidence.json"
    )

    assert source_path.is_file()
    assert html_path.is_file()
    assert registry_path.is_file()
    if output_path.exists():
        raise FileExistsError(f"기존 결과 파일 존재: {output_path}")

    source_raw = source_path.read_bytes()
    html_raw = html_path.read_bytes()
    registry_raw = registry_path.read_bytes()

    assert sha256(source_raw) == config["source_json_sha"]

    source = json.loads(source_raw.decode("utf-8"))
    registry = json.loads(registry_raw.decode("utf-8"))

    assert source["program_id"] == program_id
    assert registry["program_id"] == program_id
    assert source["validation_status"] == "needs_review"
    assert source[
        "automatic_eligibility_rules_enabled"
    ] is False

    assert sha256(html_raw) == (
        source["source"]["snapshot_sha256"]
    )

    registered = [
        item for item in registry["sources"]
        if item["collection_status"]
        == "collected_needs_review"
    ]

    assert len(registered) == 1
    assert registered[0]["sha256"] == sha256(html_raw)
    assert registered[0]["source_url"] == (
        source["source"]["source_url"]
    )

    program_mapping = mapped[program_id]

    assert program_mapping["raw_program_dir"] == (
        RAW / folder
    ).relative_to(ROOT).as_posix()

    evidence = build_evidence(
        program_id, config, source
    )

    payload = serialize(evidence)

    # 동일 입력으로 재생성
    assert payload == serialize(
        build_evidence(program_id, config, source)
    )

    # 섹션 원문·해시 대조
    assert len(evidence["sections"]) == len(
        source["sections"]
    )

    for record, original in zip(
        evidence["sections"], source["sections"]
    ):
        assert record["source_text"] == (
            original["raw_text"]
        )

        assert record["source_text_sha256"] == sha256(
            original["raw_text"].encode("utf-8")
        )

    assert output_path.parent.is_dir()

    originals[source_path] = source_raw
    originals[html_path] = html_raw
    originals[registry_path] = registry_raw

    prepared.append({
        "program_id": program_id,
        "output_path": output_path,
        "payload": payload,
        "data": evidence,
    })

    print(
        f"[PASS] {program_id}: "
        f"{len(evidence['sections'])}개 섹션 준비"
    )

assert len(prepared) == 4
print("[PASS] 4개 프로그램 원문·출처·재현성 검증")

# 3. 결과 파일 저장
for item in prepared:
    with item["output_path"].open("xb") as file:
        file.write(item["payload"])

    assert (
        item["output_path"].read_bytes()
        == item["payload"]
    )

    saved = json.loads(
        item["output_path"].read_text(
            encoding="utf-8"
        )
    )

    assert saved == item["data"]

print("[PASS] 공식 근거 JSON 4개 저장 및 재읽기")

# 4. 기존 파일 불변 확인
for path, original_raw in originals.items():
    assert path.read_bytes() == original_raw

print("[PASS] 기존 원본·매핑·구조화 JSON 불변")

# 5. 프로그램별 결과
print("\n[프로그램별 구축 결과]")

total_sections = 0

for item in prepared:
    data = item["data"]
    total_sections += data["source_section_count"]

    print("\n프로그램:", item["program_id"])
    print("원문 섹션:", data["source_section_count"])
    print("분류별:", data["category_counts"])
    print(
        "저장 경로:",
        item["output_path"].relative_to(ROOT)
    )
    print("SHA-256:", sha256(item["payload"]))

print("\n===== STEP 64-16 최종 결과 =====")
print("처리 프로그램:", len(prepared))
print("공식 근거 섹션:", total_sections)
print("신규 JSON:", len(prepared))
print("원본 SHA-256: PASS")
print("재현성: PASS")
print("저장 후 검증: PASS")
print("기존 파일 변경: 없음")
print("조건 의미 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
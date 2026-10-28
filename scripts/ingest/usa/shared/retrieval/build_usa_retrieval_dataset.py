
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa"

OUTPUT_INDEX = BASE / "shared/usa_retrieval_index.json"

MAX_CHARS = 1400
OVERLAP = 150

PROGRAMS = {
    "US-WH-01": (
        "working_holiday/summer_work_travel",
        "official_evidence.json",
        "7f509a5e67dfde3afa3a247fb4c533520b69c1c165ba9eb1d19e1a3524d39171",
        "bridgeusa",
    ),
    "US-ST-01": (
        "student/f1_academic_student",
        "official_evidence.json",
        "4e2cbbb4b99d17a378e4bac1701bd57b1d1a340d536fd9e92c1d9899f2f26fa4",
        "government_html",
    ),
    "US-ST-03": (
        "student/j1_college_university_student",
        "official_evidence.json",
        "c2881ea19ce10dce1d4450758f803193614aadac0fc9b724c1be52f40a82b01e",
        "bridgeusa",
    ),
    "US-EM-01": (
        "employment/h1b_specialty_occupations",
        "official_evidence_v2.json",
        "7fbba6a99d31234e18eb1a76828910128c04f52658db038781e0fc9a83071ab5",
        "government_html",
    ),
    "US-EM-02": (
        "employment/j1_intern",
        "official_evidence.json",
        "6133401913510314b9847f4ba315bff1da32d03943b565bb1c50a898c7419124",
        "bridgeusa",
    ),
    "US-EM-03": (
        "employment/j1_trainee",
        "official_evidence.json",
        "d34f1b698bc2a7e50cd0387967166df4cc86bf89dff5f91d30b797cc1b8ccf95",
        "bridgeusa",
    ),
    "US-WEST-01": (
        "employment/west",
        "west_2026_first_half_column_candidate.json",
        "31865507945b9a46c7485518364597ccf44978622c50242913dde822a481b8e3",
        "west_pdf",
    ),
}

WEST_PDF_SHA = (
    "6f11ae189a6ec58bde63eb52c2e7eba"
    "80b6ec4ffde1f0620f1dca95200542c31"
)

WEST_FULL_REVIEW = (
    BASE / "employment/west/"
    "west_2026_first_half_full_review_data.json"
)

WEST_FULL_REVIEW_SHA = (
    "b3e781e89880996cc88a93a3618cc164"
    "794fdba9914ade9499111390bc108bc2"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def serialize_json(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def serialize_jsonl(records):
    return "".join(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
        ) + "\n"
        for record in records
    ).encode("utf-8")


def verified_json(path, expected_sha):
    raw = path.read_bytes()

    assert sha256(raw) == expected_sha, (
        f"SHA-256 불일치: {path}"
    )

    return json.loads(raw.decode("utf-8")), raw


def split_text(text):
    """
    원문을 문자 위치 기준으로 나누며,
    원문 자체의 문자열은 변경하지 않는다.
    """
    if not text or not text.strip():
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + MAX_CHARS, len(text))

        chunks.append({
            "start": start,
            "end": end,
            "text": text[start:end],
        })

        if end == len(text):
            break

        start = end - OVERLAP

    assert chunks

    for part in chunks:
        assert (
            text[part["start"]:part["end"]]
            == part["text"]
        )

    return chunks


def collect_units(program_id, data, kind):
    units = []

    if kind == "bridgeusa":
        for section in data["sections"]:
            text = section["source_text"]

            assert sha256(
                text.encode("utf-8")
            ) == section["source_text_sha256"]

            units.append({
                "unit_id": section["evidence_id"],
                "text": text,
                "source_url": section["source_url"],
                "source_sha256": (
                    section["source_html_sha256"]
                ),
                "heading": section["heading"],
                "category": section["category_candidate"],
                "source_kind": "official_html",
                "physical_pdf_page": None,
                "printed_page_candidate": None,
                "side": None,
            })

    elif kind == "government_html":
        for source_index, source in enumerate(
            data["sources"], 1
        ):
            for block_index, block in enumerate(
                source["evidence_blocks"], 1
            ):
                text = block["source_text"]

                assert sha256(
                    text.encode("utf-8")
                ) == block["source_text_sha256"]

                units.append({
                    "unit_id": (
                        f"{program_id}-S{source_index:02d}"
                        f"-B{block_index:04d}"
                    ),
                    "text": text,
                    "source_url": source["source_url"],
                    "source_sha256": source["source_sha256"],
                    "heading": source["page_title"],
                    "category": source["source_type"],
                    "source_kind": "official_html",
                    "physical_pdf_page": None,
                    "printed_page_candidate": None,
                    "side": None,
                })

    elif kind == "west_pdf":
        assert len(data["pages"]) == 11

        for page in data["pages"]:
            physical = page["page"]

            for side, suffix in (
                ("left", "L"),
                ("right", "R"),
            ):
                text = page[f"{side}_text"]

                units.append({
                    "unit_id": (
                        f"{program_id}-P{physical:02d}-{suffix}"
                    ),
                    "text": text,
                    "source_url": (
                        "https://www.niied.go.kr/"
                        "web/main/nid/niied_board/5570"
                    ),
                    "source_sha256": WEST_PDF_SHA,
                    "heading": (
                        "2026년 상반기 WEST 모집 공고"
                    ),
                    "category": "official_notice_pdf",
                    "source_kind": "official_pdf",
                    "physical_pdf_page": physical,
                    "printed_page_candidate": (
                        (physical - 1) * 2
                        + (1 if side == "left" else 2)
                    ),
                    "side": side,
                })

    else:
        raise ValueError(f"알 수 없는 타입: {kind}")

    assert units, f"근거 단위 없음: {program_id}"

    return units


def build_records(program_id, data, kind, input_sha):
    units = collect_units(program_id, data, kind)
    records = []
    unit_ids = set()

    for unit in units:
        assert unit["unit_id"] not in unit_ids
        unit_ids.add(unit["unit_id"])

        parts = split_text(unit["text"])

        for part_index, part in enumerate(parts, 1):
            chunk_id = (
                f"{unit['unit_id']}-C{part_index:03d}"
            )

            record = {
                "chunk_id": chunk_id,
                "country": "US",
                "program_id": program_id,
                "source_kind": unit["source_kind"],
                "source_url": unit["source_url"],
                "source_sha256": unit["source_sha256"],
                "source_data_sha256": input_sha,
                "evidence_unit_id": unit["unit_id"],
                "heading": unit["heading"],
                "category_candidate": unit["category"],
                "text": part["text"],
                "text_sha256": sha256(
                    part["text"].encode("utf-8")
                ),
                "unit_text_sha256": sha256(
                    unit["text"].encode("utf-8")
                ),
                "char_start": part["start"],
                "char_end": part["end"],
                "physical_pdf_page": (
                    unit["physical_pdf_page"]
                ),
                "printed_page_candidate": (
                    unit["printed_page_candidate"]
                ),
                "side": unit["side"],
                "semantic_review_status": "needs_review",
                "eligibility_rule_verified": False,
                "automatic_eligibility_rules_enabled": False,
            }

            assert part["text"] == (
                unit["text"][
                    record["char_start"]:record["char_end"]
                ]
            )

            records.append(record)

    assert records
    assert len({
        record["chunk_id"] for record in records
    }) == len(records)

    return records


print("===== STEP 64-21 미국 7개 프로그램 RAG 데이터 구축 =====")

# WEST 확장 검수 데이터의 원본 연결 확인
west_review, west_review_raw = verified_json(
    WEST_FULL_REVIEW,
    WEST_FULL_REVIEW_SHA,
)

assert west_review["program_id"] == "US-WEST-01"
assert (
    west_review["automatic_eligibility_rules_enabled"]
    is False
)

print("[PASS] WEST 확장 검수 자료 무결성")

prepared = []
index_records = []
originals = {
    WEST_FULL_REVIEW: WEST_FULL_REVIEW_SHA
}

# 1. 전체 프로그램 JSONL 생성 준비
for program_id, (
    folder, filename, expected_sha, kind
) in PROGRAMS.items():

    source_path = BASE / folder / filename
    output_path = (
        BASE / folder / "retrieval_chunks.jsonl"
    )

    assert source_path.is_file()
    assert output_path.parent.is_dir()
    assert not output_path.exists(), (
        f"기존 결과 존재: {output_path}"
    )

    data, original_raw = verified_json(
        source_path, expected_sha
    )

    assert data["program_id"] == program_id
    assert data[
        "automatic_eligibility_rules_enabled"
    ] is False

    originals[source_path] = sha256(original_raw)

    records = build_records(
        program_id, data, kind, expected_sha
    )

    # 동일 입력에서 JSONL 재생성 결과 비교
    payload = serialize_jsonl(records)
    replay = serialize_jsonl(
        build_records(
            program_id, data, kind, expected_sha
        )
    )

    assert payload == replay

    # JSONL 각 행이 원래 레코드와 일치하는지 확인
    loaded = [
        json.loads(line)
        for line in payload.decode("utf-8").splitlines()
    ]

    assert loaded == records

    for record in records:
        assert record["program_id"] == program_id
        assert sha256(
            record["text"].encode("utf-8")
        ) == record["text_sha256"]

        assert record["eligibility_rule_verified"] is False

    prepared.append((output_path, payload, records))

    index_records.append({
        "program_id": program_id,
        "source_data_path": (
            source_path.relative_to(ROOT).as_posix()
        ),
        "source_data_sha256": expected_sha,
        "retrieval_path": (
            output_path.relative_to(ROOT).as_posix()
        ),
        "retrieval_sha256": sha256(payload),
        "chunk_count": len(records),
        "unique_evidence_units": len({
            record["evidence_unit_id"]
            for record in records
        }),
        "validation_status": "needs_review",
    })

    print(
        f"[PASS] {program_id}: "
        f"{len(records)}개 검색 청크 준비"
    )

assert len(prepared) == 7

print("[PASS] 7개 프로그램 JSONL 재현성·원문 대조")

# 2. 검색 데이터 Index 구성
index_data = {
    "dataset_type": "usa_retrieval_dataset_index",
    "country": "US",
    "program_count": 7,
    "chunking_method": "character_window_with_overlap",
    "max_chunk_characters": MAX_CHARS,
    "overlap_characters": OVERLAP,
    "west_full_review_sha256": WEST_FULL_REVIEW_SHA,
    "total_chunks": sum(
        item["chunk_count"]
        for item in index_records
    ),
    "programs": index_records,
    "validation_status": "needs_review",
    "automatic_eligibility_rules_enabled": False,
    "embedding_generated": False,
    "database_loaded": False,
}

index_payload = serialize_json(index_data)

assert OUTPUT_INDEX.parent.is_dir()
assert not OUTPUT_INDEX.exists()

# 3. 한 번의 실행으로 저장·검증
for output_path, payload, records in prepared:
    with output_path.open("xb") as file:
        file.write(payload)

    assert output_path.read_bytes() == payload

    saved_records = [
        json.loads(line)
        for line in output_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]

    assert saved_records == records

with OUTPUT_INDEX.open("xb") as file:
    file.write(index_payload)

assert OUTPUT_INDEX.read_bytes() == index_payload
assert json.loads(
    OUTPUT_INDEX.read_text(encoding="utf-8")
) == index_data

print("[PASS] 검색 JSONL 7개·통합 Index 저장")

# 4. 전체 입력 원본 불변 확인
for path, original_hash in originals.items():
    assert sha256(path.read_bytes()) == original_hash

print("[PASS] 기존 구조화 원본 전부 불변")

# 5. 결과
print("\n[프로그램별 검색 데이터]")

for entry in index_records:
    print(
        entry["program_id"],
        "| 청크:", entry["chunk_count"],
        "| 근거 단위:",
        entry["unique_evidence_units"],
    )
    print("  SHA-256:", entry["retrieval_sha256"])

print("\n===== STEP 64-21 최종 결과 =====")
print("프로그램:", index_data["program_count"])
print("전체 검색 청크:", index_data["total_chunks"])
print("생성 JSONL:", len(prepared))
print("검색 Index:", OUTPUT_INDEX.relative_to(ROOT))
print("Index SHA-256:", sha256(index_payload))
print("원문·청크 해시 검증: PASS")
print("JSONL 재현성: PASS")
print("기존 데이터 불변: PASS")
print("의미·법적 조건 검증: needs_review")
print("자동 자격 판정: 비활성화")
print("임베딩 생성: 미실행")
print("DB 적재: 미실행")
print("Git 커밋·푸시: 미실행")

from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa"
SHARED = BASE / "shared"

INDEX = SHARED / "usa_retrieval_index.json"
AUDIT = SHARED / "usa_retrieval_quality_audit.json"

INDEX_SHA = (
    "a5b801fd23d914861f04b51916e035"
    "f82e9c854fe3ad1353542bb80933d01c7a"
)

AUDIT_SHA = (
    "967800dc1d0a8bf24c67f761b4f212"
    "525b59d7f25381a636ffad80a899c7f0c0"
)

REVIEW_OUTPUT = SHARED / "usa_review_queue.jsonl"
CANDIDATE_OUTPUT = SHARED / "usa_unflagged_candidates.jsonl"
MANIFEST_OUTPUT = SHARED / "usa_retrieval_review_manifest.json"

EXPECTED_PROGRAMS = {
    "US-WH-01",
    "US-ST-01",
    "US-ST-03",
    "US-EM-01",
    "US-EM-02",
    "US-EM-03",
    "US-WEST-01",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_verified(path, expected_sha):
    assert path.is_file(), f"파일 없음: {path}"
    raw = path.read_bytes()
    assert sha256(raw) == expected_sha, (
        f"SHA-256 불일치: {path}"
    )
    return json.loads(raw.decode("utf-8")), raw


def jsonl_bytes(records):
    return "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
        for r in records
    ).encode("utf-8")


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


print("===== STEP 64-23 미국 검색 데이터 검토 대기열 =====")

# 1. 원본 인덱스·감사 결과 검증
index, index_raw = read_verified(INDEX, INDEX_SHA)
audit, audit_raw = read_verified(AUDIT, AUDIT_SHA)

assert index["program_count"] == 7
assert index["total_chunks"] == 334
assert audit["total_chunks"] == 334
assert audit["total_flagged_chunks"] == 201
assert audit["exact_duplicate_text_groups"] == 7
assert audit["retrieval_index_sha256"] == INDEX_SHA

assert index["automatic_eligibility_rules_enabled"] is False
assert audit["automatic_eligibility_rules_enabled"] is False

original_hashes = {
    INDEX: INDEX_SHA,
    AUDIT: AUDIT_SHA,
}

print("[PASS] 검색 인덱스·품질 감사 무결성")

# 2. 7개 프로그램의 모든 검색 청크 로드
all_chunks = []

for entry in index["programs"]:
    path = ROOT / entry["retrieval_path"]

    assert path.is_file()
    assert path.resolve().is_relative_to(BASE.resolve())

    raw = path.read_bytes()
    assert sha256(raw) == entry["retrieval_sha256"]

    chunks = [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]

    assert len(chunks) == entry["chunk_count"]

    for chunk in chunks:
        assert chunk["program_id"] == entry["program_id"]
        assert chunk["automatic_eligibility_rules_enabled"] is False
        assert chunk["eligibility_rule_verified"] is False
        assert sha256(
            chunk["text"].encode("utf-8")
        ) == chunk["text_sha256"]

    original_hashes[path] = entry["retrieval_sha256"]
    all_chunks.extend(chunks)

assert len(all_chunks) == 334
assert {c["program_id"] for c in all_chunks} == EXPECTED_PROGRAMS

chunk_by_id = {c["chunk_id"]: c for c in all_chunks}
assert len(chunk_by_id) == 334

print("[PASS] 334개 원본 청크 로드·검증")

# 3. 플래그와 중복 그룹 대조
flags_by_id = {}

for item in audit["flags"]:
    cid = item["chunk_id"]
    assert cid in chunk_by_id
    assert cid not in flags_by_id
    assert item["program_id"] == chunk_by_id[cid]["program_id"]
    flags_by_id[cid] = item["reasons"]

assert len(flags_by_id) == 201

duplicates_by_id = {}

for group_number, group in enumerate(
    audit["duplicate_groups"], 1
):
    chunk_ids = group["chunk_ids"]

    assert len(chunk_ids) >= 2

    for cid in chunk_ids:
        assert cid in chunk_by_id
        assert chunk_by_id[cid]["text_sha256"] == (
            group["text_sha256"]
        )
        assert cid not in duplicates_by_id

        duplicates_by_id[cid] = {
            "group_id": f"DUP-{group_number:03d}",
            "other_chunk_ids": [
                other for other in chunk_ids
                if other != cid
            ],
        }

assert len(audit["duplicate_groups"]) == 7

print("[PASS] 검토 표시 201개·중복 그룹 7개 대조")

# 4. 우선순위 분류
review_queue = []
unflagged_candidates = []

for chunk in all_chunks:
    cid = chunk["chunk_id"]
    reasons = flags_by_id.get(cid, [])

    if "pdf_table_layout_manual_review" in reasons:
        priority = "P0_table_layout"
    elif "potential_eligibility_or_legal_claim" in reasons:
        priority = "P1_policy_or_legal"
    elif "short_chunk" in reasons:
        priority = "P2_short_text"
    elif reasons:
        priority = "P3_other_flag"
    else:
        priority = "P4_unflagged"

    record = {
        **chunk,
        "audit_flags": reasons,
        "review_priority": priority,
        "duplicate_info": duplicates_by_id.get(cid),
        "human_semantic_review": "pending",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
    }

    if reasons:
        review_queue.append(record)
    else:
        unflagged_candidates.append(record)

assert len(review_queue) == 201
assert len(unflagged_candidates) == 133

assert {
    r["chunk_id"] for r in review_queue
}.isdisjoint({
    r["chunk_id"] for r in unflagged_candidates
})

assert {
    r["chunk_id"]
    for r in review_queue + unflagged_candidates
} == set(chunk_by_id)

# 우선 검토 순서 정렬
priority_order = {
    "P0_table_layout": 0,
    "P1_policy_or_legal": 1,
    "P2_short_text": 2,
    "P3_other_flag": 3,
    "P4_unflagged": 4,
}

review_queue.sort(
    key=lambda r: (
        priority_order[r["review_priority"]],
        r["program_id"],
        r["chunk_id"],
    )
)

# 5. 저장할 파일 일괄 준비
queue_raw = jsonl_bytes(review_queue)
candidate_raw = jsonl_bytes(unflagged_candidates)

priority_counts = dict(sorted(Counter(
    r["review_priority"] for r in review_queue
).items()))

manifest = {
    "dataset_type": "usa_retrieval_review_queue",
    "country": "US",
    "program_count": 7,
    "total_original_chunks": 334,
    "flagged_review_count": len(review_queue),
    "unflagged_candidate_count": len(unflagged_candidates),
    "duplicate_group_count": 7,
    "priority_counts": priority_counts,
    "source_index_sha256": INDEX_SHA,
    "source_quality_audit_sha256": AUDIT_SHA,
    "review_queue": {
        "path": REVIEW_OUTPUT.relative_to(ROOT).as_posix(),
        "sha256": sha256(queue_raw),
    },
    "unflagged_candidates": {
        "path": CANDIDATE_OUTPUT.relative_to(ROOT).as_posix(),
        "sha256": sha256(candidate_raw),
    },
    "note": (
        "Unflagged does not mean verified or approved. "
        "Duplicate groups are annotated, not removed."
    ),
    "validation_status": "needs_review",
    "human_review_completed": False,
    "approved_for_embedding": False,
    "approved_for_user_answers": False,
    "automatic_eligibility_rules_enabled": False,
    "database_loaded": False,
}

manifest_raw = json_bytes(manifest)

planned = [
    (REVIEW_OUTPUT, queue_raw),
    (CANDIDATE_OUTPUT, candidate_raw),
    (MANIFEST_OUTPUT, manifest_raw),
]

# 6. 저장 전 충돌 검사
for path, _ in planned:
    assert path.parent.is_dir()
    assert not path.exists(), (
        f"기존 결과가 존재합니다: {path}"
    )

assert queue_raw == jsonl_bytes(review_queue)
assert candidate_raw == jsonl_bytes(unflagged_candidates)
assert manifest_raw == json_bytes(manifest)

print("[PASS] 대기열 분리·재현성·저장 경로 검증")

# 7. 저장 및 재검증
for path, raw in planned:
    with path.open("xb") as file:
        file.write(raw)

    assert path.read_bytes() == raw

    print(
        "[PASS] 저장:",
        path.relative_to(ROOT),
        sha256(raw),
    )

saved_queue = [
    json.loads(line)
    for line in REVIEW_OUTPUT.read_text(
        encoding="utf-8"
    ).splitlines()
]

saved_candidates = [
    json.loads(line)
    for line in CANDIDATE_OUTPUT.read_text(
        encoding="utf-8"
    ).splitlines()
]

assert saved_queue == review_queue
assert saved_candidates == unflagged_candidates

for path, expected in original_hashes.items():
    assert sha256(path.read_bytes()) == expected, (
        f"원본 변경: {path}"
    )

print("[PASS] JSONL 재읽기·원본 불변성")

# 8. 결과
print("\n===== STEP 64-23 최종 결과 =====")
print("전체 청크:", 334)
print("우선 검토 대기열:", len(review_queue))
print("일반 검토 후보:", len(unflagged_candidates))
print("중복 그룹:", len(audit["duplicate_groups"]))
print("우선순위별:", priority_counts)
print("원본 청크 누락: 0")
print("원본 청크 삭제·변경: 없음")
print("데이터 의미 검수: pending")
print("답변용 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
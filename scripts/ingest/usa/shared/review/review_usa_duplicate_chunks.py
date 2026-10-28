
from pathlib import Path
from collections import defaultdict
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
SHARED = ROOT / "data/processed/usa/shared"
CLEANED = SHARED / "review/cleaned"

SOURCE = CLEANED / "usa_p1_ui_cleaned_final.jsonl"
INDEX = SHARED / "usa_retrieval_index.json"
AUDIT = SHARED / "usa_retrieval_quality_audit.json"

OUTPUT = CLEANED / "usa_duplicate_review.json"

EXPECTED = {
    SOURCE: (
        "1cf77cfa6b0c14e6da3c08eb5501bc"
        "751c50d6dbd9b19b79a37f674da0817275"
    ),
    INDEX: (
        "a5b801fd23d914861f04b51916e035"
        "f82e9c854fe3ad1353542bb80933d01c7a"
    ),
    AUDIT: (
        "967800dc1d0a8bf24c67f761b4f212"
        "525b59d7f25381a636ffad80a899c7f0c0"
    ),
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def verified_read(path, expected):
    assert path.is_file(), f"파일 없음: {path}"

    raw = path.read_bytes()
    assert sha256(raw) == expected, (
        f"SHA-256 불일치: {path}"
    )
    return raw


def parse_jsonl(raw):
    return [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]


def json_bytes(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


print("===== STEP 64-30 미국 중복 청크 검토 =====")

# 1. 기존 데이터 검증
source_raw = verified_read(
    SOURCE, EXPECTED[SOURCE]
)
index_raw = verified_read(
    INDEX, EXPECTED[INDEX]
)
audit_raw = verified_read(
    AUDIT, EXPECTED[AUDIT]
)

records = parse_jsonl(source_raw)
index = json.loads(index_raw)
audit = json.loads(audit_raw)

assert len(records) == 103
assert index["total_chunks"] == 334
assert len(audit["duplicate_groups"]) == 7

print("[PASS] 기존 정제 데이터·인덱스·감사 파일 검증")

# 2. 전체 원본 검색 청크 334개 확인
all_chunks = {}
original_file_hashes = dict(EXPECTED)

for entry in index["programs"]:
    path = ROOT / entry["retrieval_path"]

    assert path.resolve().is_relative_to(
        (ROOT / "data/processed/usa").resolve()
    )

    raw = verified_read(
        path,
        entry["retrieval_sha256"],
    )
    original_file_hashes[path] = entry["retrieval_sha256"]

    rows = parse_jsonl(raw)

    assert len(rows) == entry["chunk_count"]

    for row in rows:
        cid = row["chunk_id"]

        assert cid not in all_chunks
        assert row["program_id"] == entry["program_id"]
        assert sha256(
            row["text"].encode("utf-8")
        ) == row["text_sha256"]

        all_chunks[cid] = row

assert len(all_chunks) == 334

print("[PASS] 전체 334개 청크 원문 확인")

# 3. P1 중복 후보 추출
duplicate_candidates = [
    r for r in records
    if "duplicate_candidate"
    in r["review_issues"]
]

assert len(duplicate_candidates) == 6

candidate_ids = {
    r["chunk_id"] for r in duplicate_candidates
}

assert len(candidate_ids) == 6

for item in duplicate_candidates:
    cid = item["chunk_id"]
    original = all_chunks[cid]

    assert item["original_text"] == original["text"]
    assert item["original_text_sha256"] == (
        original["text_sha256"]
    )

print("[PASS] P1 중복 후보 6개 원문 확인")

# 4. 전체 감사 중복 그룹과 연결
groups = []
covered_ids = set()

for group_number, group in enumerate(
    audit["duplicate_groups"], 1
):
    ids = group["chunk_ids"]

    assert len(ids) >= 2
    assert len(set(ids)) == len(ids)

    for cid in ids:
        assert cid in all_chunks
        assert all_chunks[cid]["text_sha256"] == (
            group["text_sha256"]
        )

    matched_p1_ids = sorted(
        candidate_ids.intersection(ids)
    )

    covered_ids.update(matched_p1_ids)

    group_rows = [
        all_chunks[cid] for cid in ids
    ]

    program_ids = sorted({
        r["program_id"] for r in group_rows
    })
    source_urls = sorted({
        r["source_url"] for r in group_rows
    })

    if len(program_ids) > 1:
        candidate_action = (
            "preserve_cross_program_sources"
        )
    elif len(source_urls) > 1:
        candidate_action = (
            "preserve_distinct_official_sources"
        )
    else:
        candidate_action = (
            "inspect_same_source_repetition"
        )

    groups.append({
        "group_id": f"DUP-{group_number:03d}",
        "text_sha256": group["text_sha256"],
        "chunk_count": len(ids),
        "chunk_ids": ids,
        "matched_p1_candidate_ids": matched_p1_ids,
        "program_ids": program_ids,
        "source_urls": source_urls,
        "candidate_action": candidate_action,
        "members": [
            {
                "chunk_id": r["chunk_id"],
                "program_id": r["program_id"],
                "source_url": r["source_url"],
                "heading": r["heading"],
                "text_sha256": r["text_sha256"],
            }
            for r in group_rows
        ],
        "duplicate_review_status": "needs_review",
        "delete_original": False,
        "approved_for_user_answers": False,
    })

assert covered_ids == candidate_ids
assert len(groups) == 7

print("[PASS] 감사 중복 그룹 7개·P1 후보 6개 연결")

# 5. 정책 정제 결과 보존 여부 확인
for item in records:
    assert item["approved_for_user_answers"] is False
    assert item["approved_for_embedding"] is False
    assert (
        item["automatic_eligibility_rules_enabled"]
        is False
    )

report = {
    "dataset_type": "usa_duplicate_review",
    "country": "US",
    "total_original_chunks": 334,
    "p1_total_chunks": 103,
    "p1_duplicate_candidate_chunks": 6,
    "exact_text_duplicate_groups": 7,
    "groups": groups,
    "decision_policy": {
        "auto_delete_duplicates": False,
        "cross_program_sources": "preserve",
        "distinct_official_sources": "preserve",
        "same_source_repetition": "manual_review",
        "source_metadata_preserved": True,
    },
    "source_ui_cleaned_sha256": EXPECTED[SOURCE],
    "source_quality_audit_sha256": EXPECTED[AUDIT],
    "review_status": "needs_review",
    "human_semantic_review_completed": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "database_loaded": False,
}

payload = json_bytes(report)

# 6. 저장 전 충돌 검사
assert OUTPUT.parent.is_dir()

if OUTPUT.exists():
    assert OUTPUT.read_bytes() == payload, (
        f"기존 보고서와 내용이 다릅니다: {OUTPUT}"
    )
    state = "EXISTS_VERIFIED"
else:
    with OUTPUT.open("xb") as file:
        file.write(payload)
    state = "CREATED"

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == report

print(f"[PASS] {state}: {OUTPUT.relative_to(ROOT)}")

# 7. 기존 원본 불변
for path, expected in original_file_hashes.items():
    assert sha256(path.read_bytes()) == expected, (
        f"기존 파일 변경 감지: {path}"
    )

print("[PASS] 전체 원본 파일 불변")

# 8. 결과 출력
print("\n[중복 그룹별 후보 조치]")

for group in groups:
    print(
        group["group_id"],
        "| 청크:", group["chunk_count"],
        "| P1:", len(group["matched_p1_candidate_ids"]),
        "| 프로그램:", ",".join(group["program_ids"]),
        "| 조치:", group["candidate_action"],
    )

print("\n===== STEP 64-30 최종 결과 =====")
print("전체 원본 청크:", 334)
print("P1 청크:", 103)
print("P1 중복 후보:", 6)
print("전체 동일 텍스트 중복 그룹:", 7)
print("보고서:", OUTPUT.relative_to(ROOT))
print("SHA-256:", sha256(payload))
print("중복 자동 삭제: 없음")
print("원본 파일 변경: 없음")
print("정책 의미 검증: 미완료")
print("답변용 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
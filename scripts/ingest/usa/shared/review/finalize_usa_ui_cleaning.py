
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
CLEANED = ROOT / "data/processed/usa/shared/review/cleaned"

SOURCE = CLEANED / "usa_p1_cleaned_candidates.jsonl"
PREVIOUS_REPORT = CLEANED / "usa_p1_cleaning_report.json"

OUTPUT = CLEANED / "usa_p1_ui_cleaned_final.jsonl"
REPORT = CLEANED / "usa_p1_ui_final_report.json"

EXPECTED_SOURCE_SHA = (
    "28e48ffd4ec0a292514801a5a3c3f474"
    "c7a699f85aad3f39d50de75d2aad534d"
)
EXPECTED_REPORT_SHA = (
    "b94d8819e2332f4ace306f8fb2a17217"
    "e867ea096fb408c556859cf153109ac4"
)

MANUAL_IDS = {
    "US-EM-03-SECTION-013-C001",
    "US-WH-01-SECTION-019-C001",
}

UI_MARKER = " Program Resources "

EXPECTED_UI_IDS = {
    "US-EM-02-SECTION-011-C001",
    "US-EM-03-SECTION-011-C001",
    "US-EM-03-SECTION-013-C001",
    "US-ST-03-SECTION-009-C001",
    "US-WH-01-SECTION-019-C001",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verified_read(path, expected):
    assert path.is_file(), f"파일 없음: {path}"
    data = path.read_bytes()
    assert sha256(data) == expected, (
        f"SHA-256 불일치: {path}"
    )
    return data


def parse_jsonl(data):
    return [
        json.loads(line)
        for line in data.decode("utf-8").splitlines()
        if line.strip()
    ]


def jsonl_bytes(records):
    return "".join(
        json.dumps(
            r, ensure_ascii=False, sort_keys=True
        ) + "\n"
        for r in records
    ).encode("utf-8")


def json_bytes(obj):
    return (
        json.dumps(
            obj, ensure_ascii=False, indent=2
        ) + "\n"
    ).encode("utf-8")


def save_or_verify(path, data):
    if path.exists():
        assert path.read_bytes() == data, (
            f"기존 파일과 충돌: {path}"
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as f:
        f.write(data)

    assert path.read_bytes() == data
    return "CREATED"


print("===== STEP 64-29 UI 정제 후보 확정 =====")

# 1. STEP 64-28 결과 검증
source_raw = verified_read(
    SOURCE, EXPECTED_SOURCE_SHA
)
report_raw = verified_read(
    PREVIOUS_REPORT, EXPECTED_REPORT_SHA
)

records = parse_jsonl(source_raw)
previous_report = json.loads(
    report_raw.decode("utf-8")
)

assert len(records) == 103
assert previous_report["total_chunks"] == 103
assert previous_report["ui_flagged_chunks"] == 5

by_id = {r["chunk_id"]: r for r in records}
assert len(by_id) == 103
assert MANUAL_IDS <= set(by_id)

assert {
    r["chunk_id"]
    for r in records
    if "possible_site_ui_contamination"
    in r["review_issues"]
} == EXPECTED_UI_IDS

print("[PASS] STEP 64-28 입력·103개 청크 검증")

# 2. 수동 확인된 정확한 두 경계만 정제
results = []
manual_count = 0

for old in records:
    record = dict(old)
    chunk_id = record["chunk_id"]

    original_text = record["original_text"]
    previous_text = record["cleaned_candidate_text"]
    status = record["cleaning_status"]

    assert sha256(
        original_text.encode("utf-8")
    ) == record["original_text_sha256"]

    if chunk_id in MANUAL_IDS:
        assert status == "manual_review_required"
        assert previous_text == original_text

        # 해당 두 청크에서만 정확한 경계 사용
        assert original_text.count(UI_MARKER) == 1

        body, ui = original_text.split(
            UI_MARKER, 1
        )

        body = body.rstrip()
        removed = original_text[len(body):]

        assert body.endswith(".")
        assert removed.startswith(UI_MARKER)
        assert "Find a Program Sponsor" in removed
        assert len(body) > 100

        # 원본과 정제 후보가 손실 없이 대응
        assert body + removed == original_text

        record["cleaned_candidate_text"] = body
        record["cleaned_candidate_sha256"] = sha256(
            body.encode("utf-8")
        )
        record["cleaning_status"] = (
            "reviewed_ui_boundary_candidate"
        )
        record["cleaning_patterns"] = [
            "program_resources_boundary"
        ]
        record["removed_text"] = removed

        manual_count += 1

    else:
        # STEP 64-28의 결과를 그대로 사용
        assert status in {
            "unchanged",
            "safe_suffix_removed",
        }

        if status == "unchanged":
            assert previous_text == original_text

        if status == "safe_suffix_removed":
            assert original_text.startswith(previous_text)
            assert original_text == (
                previous_text + record["removed_text"]
            )

    assert sha256(
        record["cleaned_candidate_text"].encode("utf-8")
    ) == record["cleaned_candidate_sha256"]

    # UI 분리 확인은 법률 검증이 아님
    record["ui_cleaning_review_status"] = (
        "boundary_checked"
        if chunk_id in MANUAL_IDS
        else (
            "deterministic_suffix_checked"
            if status == "safe_suffix_removed"
            else "not_modified"
        )
    )

    record["human_review_status"] = "pending"
    record["official_live_rule_verified"] = False
    record["approved_for_user_answers"] = False
    record["approved_for_embedding"] = False
    record["automatic_eligibility_rules_enabled"] = False

    results.append(record)

assert manual_count == 2
assert len(results) == 103

# 3. 정제 상태 확인
counts = Counter(
    r["cleaning_status"] for r in results
)

assert counts == {
    "unchanged": 98,
    "safe_suffix_removed": 3,
    "reviewed_ui_boundary_candidate": 2,
}

changed_ids = {
    r["chunk_id"]
    for r in results
    if r["cleaned_candidate_text"]
    != r["original_text"]
}

assert changed_ids == EXPECTED_UI_IDS

# 모든 수정에서 삭제된 부분을 보존
for r in results:
    if r["chunk_id"] in changed_ids:
        assert (
            r["cleaned_candidate_text"]
            + r["removed_text"]
        ) == r["original_text"]

print("[PASS] UI 혼입 5개 후보 정제·역추적 검증")

# 4. 보고서 생성
output_raw = jsonl_bytes(results)

report = {
    "dataset_type": "usa_p1_ui_cleaning_final",
    "country": "US",
    "total_chunks": 103,
    "changed_candidate_count": len(changed_ids),
    "unchanged_count": counts["unchanged"],
    "step_64_28_safe_suffix_count": 3,
    "step_64_29_boundary_count": 2,
    "status_counts": dict(sorted(counts.items())),
    "changed_chunk_ids": sorted(changed_ids),
    "original_cleaning_file_sha256": (
        EXPECTED_SOURCE_SHA
    ),
    "previous_report_sha256": (
        EXPECTED_REPORT_SHA
    ),
    "output_sha256": sha256(output_raw),
    "originals_preserved": True,
    "removed_ui_text_preserved": True,
    "policy_meaning_verified": False,
    "current_policy_verified": False,
    "human_review_completed": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

report_raw = json_bytes(report)

# 5. 저장 전 충돌 검사
planned = [
    (OUTPUT, output_raw),
    (REPORT, report_raw),
]

for path, data in planned:
    assert path.parent.is_dir()
    if path.exists():
        assert path.read_bytes() == data, (
            f"기존 결과 파일과 충돌: {path}"
        )

# 6. 저장 및 재읽기
for path, data in planned:
    state = save_or_verify(path, data)
    print(f"[PASS] {state}: {path.relative_to(ROOT)}")
    print("SHA-256:", sha256(data))

assert parse_jsonl(OUTPUT.read_bytes()) == results
assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == report

# 7. 원본 불변
assert sha256(SOURCE.read_bytes()) == EXPECTED_SOURCE_SHA
assert sha256(
    PREVIOUS_REPORT.read_bytes()
) == EXPECTED_REPORT_SHA

print("[PASS] 저장·재읽기·기존 파일 불변")

print("\n===== STEP 64-29 최종 결과 =====")
print("전체 청크:", len(results))
print("UI 정제 후보:", len(changed_ids))
print("원문 유지:", counts["unchanged"])
print("이전 단계 안전 꼬리 정제:", 3)
print("이번 단계 경계 검토 정제:", manual_count)
print("정제 상태:", dict(sorted(counts.items())))
print("원본 및 제거 텍스트 보존: PASS")
print("정책 현행성 검증: 미완료")
print("법률·자격 의미 승인: False")
print("답변용 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
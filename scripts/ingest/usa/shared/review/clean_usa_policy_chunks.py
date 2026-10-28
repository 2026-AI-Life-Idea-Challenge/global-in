
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]

SHARED = ROOT / "data/processed/usa/shared"
POLICY = SHARED / "review/policy"
CLEANED = SHARED / "review/cleaned"

SOURCE = POLICY / "usa_p1_content_triage_103.jsonl"
ORIGINAL = SHARED / "usa_policy_review_queue.jsonl"

OUTPUT = CLEANED / "usa_p1_cleaned_candidates.jsonl"
REPORT = CLEANED / "usa_p1_cleaning_report.json"

EXPECTED_SOURCE_SHA = (
    "9bf2724b46d43f7bacdc2752dd11c26"
    "e22382ab20584c11509e9b49f9ad66ce8"
)

EXPECTED_ORIGINAL_SHA = (
    "d755e3f6d7f6506b999ccbd31f20cc2a"
    "89c787eaf7b5a617ecbf9c8d8be464b4"
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verified_read(path, expected_sha):
    assert path.is_file(), f"파일 없음: {path}"
    raw = path.read_bytes()
    assert sha256(raw) == expected_sha, (
        f"SHA-256 불일치: {path}"
    )
    return raw


def parse_jsonl(raw):
    return [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
        if line.strip()
    ]


def jsonl_bytes(records):
    return "".join(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
        ) + "\n"
        for record in records
    ).encode("utf-8")


def json_bytes(obj):
    return (
        json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def write_or_verify(path, content):
    if path.exists():
        assert path.read_bytes() == content, (
            f"기존 파일 내용 충돌: {path}"
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as f:
        f.write(content)

    assert path.read_bytes() == content
    return "CREATED"


# 정책 원문 뒤에 붙은 것으로 명확히 식별되는
# 사이트 메뉴 문자열만 제거한다.
#
# 검색 대상: 원문 끝부분에 정확히 일치하는 문구
# 원문 중간의 단어는 제거하지 않는다.
SAFE_TRAILING_PATTERNS = [
    (
        "bridgeusa_common_footer",
        re.compile(
            r"\s+Program Resources\s+"
            r"Common Questions\s+"
            r"SEVIS Information\s+"
            r"end tab 2 tab 3\s*$",
            flags=re.IGNORECASE,
        ),
    ),
]

UI_HINT = re.compile(
    r"Program Resources|"
    r"Common Questions|"
    r"SEVIS Information|"
    r"end tab|"
    r"<a\s|"
    r'class="button',
    flags=re.IGNORECASE,
)


def clean_candidate(text, flagged):
    """
    반환 상태:
    - safe_suffix_removed:
      정해진 UI 꼬리 문구만 제거한 정제 후보
    - manual_review_required:
      UI 혼입 의심이지만 자동 제거 불가
    - unchanged:
      UI 검토 플래그 없음

    모든 반환 결과는 여전히 답변·임베딩 미승인.
    """
    if not flagged:
        return text, "unchanged", [], ""

    for pattern_name, pattern in SAFE_TRAILING_PATTERNS:
        match = pattern.search(text)

        if match:
            candidate = text[:match.start()].rstrip()
            removed = text[match.start():]

            assert candidate.strip()
            assert len(candidate) < len(text)
            assert candidate + removed.lstrip() != ""

            # 제거 후에도 UI 의심 문자열이 있으면
            # 자동 정제를 확정하지 않는다.
            if UI_HINT.search(candidate):
                return (
                    text,
                    "manual_review_required",
                    [],
                    "",
                )

            return (
                candidate,
                "safe_suffix_removed",
                [pattern_name],
                removed,
            )

    return text, "manual_review_required", [], ""


print("===== STEP 64-28 미국 정책 청크 정제 =====")

# 1. 입력 무결성 확인
source_raw = verified_read(
    SOURCE, EXPECTED_SOURCE_SHA
)
original_raw = verified_read(
    ORIGINAL, EXPECTED_ORIGINAL_SHA
)

source_records = parse_jsonl(source_raw)
original_records = parse_jsonl(original_raw)

assert len(source_records) == 103
assert len(original_records) == 103

source_by_id = {
    r["chunk_id"]: r
    for r in source_records
}

original_by_id = {
    r["chunk_id"]: r
    for r in original_records
}

assert len(source_by_id) == 103
assert len(original_by_id) == 103
assert set(source_by_id) == set(original_by_id)

for cid, record in source_by_id.items():
    original = original_by_id[cid]

    assert record["program_id"] == original["program_id"]
    assert record["source_url"] == original["source_url"]
    assert record["source_text"] == original["text"]
    assert record["source_text_sha256"] == original["text_sha256"]

    assert sha256(
        record["source_text"].encode("utf-8")
    ) == record["source_text_sha256"]

print("[PASS] STEP 64-25·27 원본 103개 대조")

# 2. UI 의심 청크 검토 및 정제 후보 생성
results = []
ui_flag_count = 0

for cid in sorted(source_by_id):
    record = source_by_id[cid]
    original = original_by_id[cid]

    text = record["source_text"]

    flagged = (
        "possible_site_ui_contamination"
        in record["review_issues"]
    )

    if flagged:
        ui_flag_count += 1

    candidate, status, patterns, removed = (
        clean_candidate(text, flagged)
    )

    assert candidate
    assert status in {
        "unchanged",
        "safe_suffix_removed",
        "manual_review_required",
    }

    # 비변경 또는 UI 꼬리 제거만 허용
    if status == "safe_suffix_removed":
        assert text.startswith(candidate)
        assert text[len(candidate):] == removed
    else:
        assert candidate == text

    result = {
        "chunk_id": cid,
        "program_id": record["program_id"],
        "source_url": record["source_url"],
        "source_kind": record["source_kind"],
        "heading": record["heading"],
        "classification_candidate": (
            record["classification_candidate"]
        ),
        "review_issues": record["review_issues"],
        "original_text": text,
        "original_text_sha256": (
            record["source_text_sha256"]
        ),
        "cleaned_candidate_text": candidate,
        "cleaned_candidate_sha256": sha256(
            candidate.encode("utf-8")
        ),
        "cleaning_status": status,
        "cleaning_patterns": patterns,
        "removed_text": removed,
        "duplicate_info": record.get("duplicate_info"),
        "context_before": original["context_before"],
        "context_after": original["context_after"],
        "human_review_status": "pending",
        "official_live_rule_verified": False,
        "approved_for_embedding": False,
        "approved_for_user_answers": False,
        "automatic_eligibility_rules_enabled": False,
    }

    results.append(result)

assert len(results) == 103
assert ui_flag_count == 5

print("[PASS] UI 혼입 의심 5개 정제 후보 분석")

# 3. 중복 후보는 삭제하지 않고 관계만 기록
duplicate_candidates = [
    r for r in results
    if "duplicate_candidate" in r["review_issues"]
]

assert len(duplicate_candidates) == 6

for record in duplicate_candidates:
    assert record["duplicate_info"] is not None

print("[PASS] 중복 후보 6개 원본 유지·표시")

# 4. 결과 통계
status_counts = Counter(
    r["cleaning_status"]
    for r in results
)

ui_records = [
    {
        "chunk_id": r["chunk_id"],
        "program_id": r["program_id"],
        "cleaning_status": r["cleaning_status"],
        "cleaning_patterns": r["cleaning_patterns"],
        "removed_text": r["removed_text"],
    }
    for r in results
    if "possible_site_ui_contamination"
    in r["review_issues"]
]

assert len(ui_records) == 5

output_raw = jsonl_bytes(results)

report = {
    "dataset_type": "usa_policy_cleaning_report",
    "country": "US",
    "source_triage_sha256": EXPECTED_SOURCE_SHA,
    "source_policy_review_sha256": (
        EXPECTED_ORIGINAL_SHA
    ),
    "total_chunks": len(results),
    "ui_flagged_chunks": ui_flag_count,
    "cleaning_status_counts": dict(
        sorted(status_counts.items())
    ),
    "ui_review_records": ui_records,
    "duplicate_candidate_chunks": len(
        duplicate_candidates
    ),
    "duplicate_candidate_ids": [
        r["chunk_id"]
        for r in duplicate_candidates
    ],
    "policy_text_deleted": False,
    "source_files_modified": False,
    "human_review_completed": False,
    "approved_for_embedding": False,
    "approved_for_user_answers": False,
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
    "note": (
        "Only exact trailing UI strings may be removed "
        "from cleaned candidates. Source originals are "
        "preserved. No semantic or legal approval."
    ),
}

report["cleaned_jsonl_sha256"] = sha256(output_raw)
report_raw = json_bytes(report)

# 5. 저장
CLEANED.mkdir(parents=True, exist_ok=True)

planned = [
    (OUTPUT, output_raw),
    (REPORT, report_raw),
]

# 파일 충돌 검사 먼저 진행
for path, raw in planned:
    if path.exists():
        assert path.read_bytes() == raw, (
            f"기존 파일과 충돌: {path}"
        )

for path, raw in planned:
    status = write_or_verify(path, raw)
    print(
        f"[PASS] {status}:",
        path.relative_to(ROOT),
    )
    print("SHA-256:", sha256(raw))

# 6. 저장 후 검증
assert parse_jsonl(OUTPUT.read_bytes()) == results
assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == report

assert sha256(SOURCE.read_bytes()) == EXPECTED_SOURCE_SHA
assert sha256(ORIGINAL.read_bytes()) == EXPECTED_ORIGINAL_SHA

print("[PASS] 저장·재읽기·기존 파일 불변")

# 7. 콘솔 요약
print("\n[UI 혼입 의심 5개 처리 결과]")

for r in ui_records:
    print(
        r["chunk_id"],
        "=>",
        r["cleaning_status"],
    )

print("\n===== STEP 64-28 최종 결과 =====")
print("전체 정책 청크:", len(results))
print("UI 의심 청크:", ui_flag_count)
print("정제 상태별:", dict(sorted(status_counts.items())))
print("중복 후보:", len(duplicate_candidates))
print("원본 누락:", 0)
print("원본 파일 변경: 없음")
print("정제 후보 답변 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
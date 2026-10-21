
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

SOURCE = BASE / "japan_employment_retrieval_records.jsonl"
TARGET = BASE / "japan_employment_search_ready.jsonl"

SOURCE_SHA = (
    "d782f3618d46c951f21a305f40ef72e9"
    "825ee14d77084cad59fb22689c8d8be8"
)

TARGET_SHA = (
    "6549dce07b8e751dcbee42028b0af7f"
    "c25701a7e7424d85874530c3f41f1ce43"
)

TEXT_FIELDS = {
    "raw_text_ja",
    "original_text_ja",
    "intro_original_ja",
    "condition_text_ja",
    "evidence_text_ja",
    "source_text_ja",
    "source_intro_ja",
    "source_note_ja",
    "applicability_condition_ja",
}

ADDED_FIELDS = {
    "search_text_ja",
    "evidence_search_segments",
    "search_text_strategy",
    "embedding_generated",
}

EXPECTED_COUNTS = {
    "coe_common": 6,
    "coe_category34": 8,
    "change": 8,
    "renewal": 13,
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def extract_segments(value, path="evidence"):
    """원본 중첩 구조를 독립적으로 순회하여 텍스트를 확인."""
    result = []
    candidates = []

    def visit(obj, current):
        if isinstance(obj, dict):
            for key, child in obj.items():
                child_path = f"{current}.{key}"

                if isinstance(child, str) and child.strip():
                    if key in TEXT_FIELDS:
                        result.append({
                            "source_path": child_path,
                            "text_ja": child,
                        })
                    elif key.endswith("_ja"):
                        candidates.append({
                            "source_path": child_path,
                            "field": key,
                        })

                elif isinstance(child, (dict, list)):
                    visit(child, child_path)

        elif isinstance(obj, list):
            for i, child in enumerate(obj):
                visit(child, f"{current}[{i}]")

    visit(value, path)
    return result, candidates


def load_jsonl(raw):
    assert raw.endswith(b"\n"), "마지막 LF 누락"
    assert b"\r\n" not in raw, "CRLF 발견"

    lines = raw.decode("utf-8").splitlines()
    assert len(lines) == 35

    return [json.loads(line) for line in lines]


print("===== STEP 63-100 검색 본문 보존 검증 =====")

assert SOURCE.is_file(), "원본 JSONL 누락"
assert TARGET.is_file(), "검색 본문 JSONL 누락"

source_bytes = SOURCE.read_bytes()
target_bytes = TARGET.read_bytes()

assert sha256(source_bytes) == SOURCE_SHA
assert sha256(target_bytes) == TARGET_SHA

print("[PASS] 입력·출력 SHA-256 및 LF 형식")

source_records = load_jsonl(source_bytes)
target_records = load_jsonl(target_bytes)

assert len(source_records) == len(target_records) == 35

total_segments = 0
evidence_count = 0
group_counts = Counter()
unextracted_candidates = []

for index, (original, target) in enumerate(
    zip(source_records, target_records), start=1
):
    doc_id = original["document_id"]

    assert target["document_id"] == doc_id, (
        f"{index}번째 문서 ID 불일치"
    )

    assert target["record_id"] == original["record_id"]

    # 기존 레코드의 필드와 값이 전부 유지되었는지 확인
    assert set(target) == set(original) | ADDED_FIELDS, (
        f"{doc_id}: 필드 구성 불일치"
    )

    for key, value in original.items():
        assert target[key] == value, (
            f"{doc_id}: 기존 필드 변경 - {key}"
        )

    # 검색 본문은 일본어 원문 그대로 유지
    assert target["search_text_ja"] == original["raw_text_ja"]

    assert target["search_text_strategy"] == (
        "original_document_text_with_separate_evidence_segments"
    )

    assert target["embedding_generated"] is False
    assert target["automatic_eligibility_rules_enabled"] is False
    assert target["validation_status"] == "needs_review"

    # 증빙의 텍스트와 원본 경로를 다시 추출하여 비교
    expected_segments, candidates = extract_segments(
        original["evidence"]
    )

    assert target["evidence_search_segments"] == (
        expected_segments
    ), f"{doc_id}: 증빙 경로·텍스트·순서 불일치"

    for candidate in candidates:
        unextracted_candidates.append({
            "document_id": doc_id,
            **candidate,
        })

    total_segments += len(expected_segments)

    if original["evidence"]:
        evidence_count += 1

    group_counts[original["dataset_group"]] += 1

assert dict(group_counts) == EXPECTED_COUNTS
assert evidence_count == 9
assert total_segments == 63

print("[PASS] 검색 레코드 35개 및 기존 필드 완전 보존")
print("[PASS] 일본어 검색 본문 35개 원문 일치")
print("[PASS] 증빙 세그먼트 63개 경로·텍스트·순서 일치")
print("[PASS] 상세 증빙 구조 9개 보존")

# 추출 대상에서 빠진 일본어 필드 후보 출력
print("\n[추출되지 않은 일본어 텍스트 필드 후보]")

if unextracted_candidates:
    for candidate in unextracted_candidates:
        print(
            candidate["document_id"],
            "->",
            candidate["source_path"],
        )
else:
    print("없음")

# 기존 파일의 불변성 확인
assert sha256(SOURCE.read_bytes()) == SOURCE_SHA
assert sha256(TARGET.read_bytes()) == TARGET_SHA

print("\n[PASS] 기존 JSONL 2개 불변")

print("\n===== STEP 63-100 최종 결과 =====")
print("검색 레코드:", len(target_records))
print("상세 증빙 레코드:", evidence_count)
print("검증된 증빙 세그먼트:", total_segments)
print(
    "추가 검토할 일본어 필드 후보:",
    len(unextracted_candidates),
)
print("원본·출처·Category·증빙 구조: 보존")
print("자동 자격 판정: 비활성화")
print("정책 검증 상태: needs_review")
print("기존 파일 변경: 없음")
print("임베딩·DB 적재: 미실행")
print("Git 커밋·푸시: 미실행")
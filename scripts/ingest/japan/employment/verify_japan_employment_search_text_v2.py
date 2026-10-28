
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "data/processed/japan/employment"

FILES = {
    "source": (
        "japan_employment_retrieval_records.jsonl",
        "d782f3618d46c951f21a305f40ef72e9825ee14d77084cad59fb22689c8d8be8",
    ),
    "v1": (
        "japan_employment_search_ready.jsonl",
        "6549dce07b8e751dcbee42028b0af7fc25701a7e7424d85874530c3f41f1ce43",
    ),
    "v2": (
        "japan_employment_search_ready_v2.jsonl",
        "030ec57531c9c852d2d436388743c2e05b6e6d84ec7ad78091e7dfeead304c87",
    ),
}

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
    "clean_text_ja",
    "exception_original_ja",
}

EXPECTED_EXTRA_PATHS = {
    "evidence.education_evidence.alternative_group.options[1].clean_text_ja",
    "evidence.education_evidence.alternative_group.options[2].exception_original_ja",
    "evidence.education_evidence.alternative_group.options[3].exception_original_ja",
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def collect_texts(value, path="evidence"):
    segments = []
    unrecognized = []

    def walk(obj, current):
        if isinstance(obj, dict):
            for key, child in obj.items():
                child_path = f"{current}.{key}"

                if isinstance(child, str) and child.strip():
                    if key in TEXT_FIELDS:
                        segments.append({
                            "source_path": child_path,
                            "text_ja": child,
                        })
                    elif key.endswith("_ja"):
                        unrecognized.append(child_path)

                elif isinstance(child, (dict, list)):
                    walk(child, child_path)

        elif isinstance(obj, list):
            for index, child in enumerate(obj):
                walk(child, f"{current}[{index}]")

    walk(value, path)
    return segments, unrecognized


def load_file(name):
    filename, expected_sha = FILES[name]
    path = BASE / filename

    assert path.is_file(), f"파일 누락: {filename}"

    raw = path.read_bytes()

    assert sha256(raw) == expected_sha, (
        f"SHA-256 불일치: {filename}"
    )
    assert raw.endswith(b"\n")
    assert b"\r\n" not in raw

    records = [
        json.loads(line)
        for line in raw.decode("utf-8").splitlines()
    ]

    assert len(records) == 35

    return path, raw, records


print("===== STEP 63-100B v2 검색 본문 검증 =====")

loaded = {
    key: load_file(key)
    for key in FILES
}

print("[PASS] Source / v1 / v2 SHA-256")

source = loaded["source"][2]
v1 = loaded["v1"][2]
v2 = loaded["v2"][2]

groups = Counter()
added_segments = []
all_texts = []
total_v1 = 0
total_v2 = 0
evidence_count = 0

for original, old, new in zip(source, v1, v2):
    doc_id = original["document_id"]

    assert old["document_id"] == doc_id
    assert new["document_id"] == doc_id
    assert original["record_id"] == doc_id

    # 원래 검색 레코드의 모든 필드가 그대로 유지되어야 함
    for key, value in original.items():
        assert old[key] == value, f"v1 원본 변경: {doc_id}/{key}"
        assert new[key] == value, f"v2 원본 변경: {doc_id}/{key}"

    assert new["search_text_ja"] == original["raw_text_ja"]
    assert old["search_text_ja"] == new["search_text_ja"]

    assert new["validation_status"] == "needs_review"
    assert new["automatic_eligibility_rules_enabled"] is False
    assert new["embedding_generated"] is False

    # v1 대비 허용된 변화는 검색 세그먼트뿐
    assert set(old) == set(new)
    for key in old:
        if key != "evidence_search_segments":
            assert old[key] == new[key], (
                f"예상하지 못한 필드 변경: {doc_id}/{key}"
            )

    segments, unrecognized = collect_texts(
        original["evidence"]
    )

    assert not unrecognized, (
        f"{doc_id}: 미추출 일본어 후보 {unrecognized}"
    )

    assert new["evidence_search_segments"] == segments, (
        f"{doc_id}: 경로·텍스트·순서 불일치"
    )

    old_segments = old["evidence_search_segments"]
    old_paths = {
        item["source_path"]
        for item in old_segments
    }

    # v1에 있던 모든 세그먼트는 v2에도 그대로 존재
    assert all(
        item in segments
        for item in old_segments
    ), f"{doc_id}: v1 세그먼트 누락"

    assert len(old_paths) == len(old_segments)
    assert len({
        item["source_path"] for item in segments
    }) == len(segments)

    for item in segments:
        if item["source_path"] not in old_paths:
            added_segments.append({
                "document_id": doc_id,
                **item,
            })

        all_texts.append((doc_id, item["text_ja"]))

    total_v1 += len(old_segments)
    total_v2 += len(segments)
    evidence_count += bool(original["evidence"])
    groups[original["dataset_group"]] += 1

assert dict(groups) == {
    "coe_common": 6,
    "coe_category34": 8,
    "change": 8,
    "renewal": 13,
}

assert len({r["document_id"] for r in v2}) == 35
assert evidence_count == 9
assert total_v1 == 63
assert total_v2 == 66
assert len(added_segments) == 3

assert all(
    item["document_id"] == "JP_EM_COE_DOC_008"
    for item in added_segments
)

assert {
    item["source_path"] for item in added_segments
} == EXPECTED_EXTRA_PATHS

print("[PASS] 기존 레코드 35개 완전 보존")
print("[PASS] 상세 증빙 구조 9개 보존")
print("[PASS] 증빙 세그먼트 63개 -> 66개")
print("[PASS] 추가 일본어 필드 3개 경로 일치")
print("[PASS] 미추출 *_ja 문자열 후보 없음")

print("\n[추가 세그먼트]")
for item in added_segments:
    print(
        item["document_id"],
        "->",
        item["source_path"],
    )

# 문자열이 완전히 동일한 증빙 문구가 있는지 진단
text_counts = Counter(text for _, text in all_texts)
duplicates = {
    text: count
    for text, count in text_counts.items()
    if count > 1
}

print("\n[동일 증빙 원문 중복 진단]")
print("중복되는 서로 다른 텍스트 값:", len(duplicates))
print("중복으로 인한 추가 등장 횟수:",
      sum(count - 1 for count in duplicates.values()))

# 중복은 원문 특성일 수 있으므로 임의로 제거하지 않음
print("자동 중복 제거: 미실행")

# 검사 전후 모든 파일 해시 불변성 검증
for key, (path, original_bytes, _) in loaded.items():
    assert path.read_bytes() == original_bytes
    assert sha256(path.read_bytes()) == FILES[key][1]

print("\n[PASS] 기존 JSONL 3개 불변")

print("\n===== STEP 63-100B 최종 결과 =====")
print("검색 레코드: 35개")
print("상세 증빙 레코드: 9개")
print("v1 세그먼트: 63개")
print("v2 세그먼트: 66개")
print("신규 추가: 3개")
print("원본 및 Category·출처 구조: 유지")
print("v2 출력 SHA-256:", FILES["v2"][1])
print("기존 파일 변경: 없음")
print("정책 검증 상태: needs_review")
print("자동 자격 판정: 비활성화")
print("임베딩·DB 적재: 미실행")
print("Git 커밋·푸시: 미실행")
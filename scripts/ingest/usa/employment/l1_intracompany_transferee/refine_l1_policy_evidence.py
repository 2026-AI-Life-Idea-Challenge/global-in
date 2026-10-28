
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts.ingest.usa.shared.evidence.build_e2_policy_evidence import (
    extract_text,
)


ROOT = Path(
    "data/processed/usa/employment/l1_intracompany_transferee"
)

POLICY_PATH = ROOT / "l1_policy_review_2026_draft.json"
EVIDENCE_PATH = ROOT / "l1_policy_evidence_2026_draft.json"

EXPECTED_SOURCE_COUNT = 8
EXPECTED_POLICY_COUNT = 26
EXPECTED_EVIDENCE_COUNT = 30

REFINED_POLICY_IDS = [
    "L1-16",
    "L1-17",
    "L1-19",
    "L1-23",
    "L1-24",
    "L1-25",
    "L1-26",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(text: str) -> str:
    return " ".join(text.split())


def extract_between(
    text: str,
    start_phrase: str,
    end_phrase: str,
) -> str:
    start = text.find(start_phrase)

    if start < 0:
        raise ValueError(
            f"Start phrase not found: {start_phrase}"
        )

    end = text.find(
        end_phrase,
        start + len(start_phrase),
    )

    if end < 0:
        raise ValueError(
            f"End phrase not found: {end_phrase}"
        )

    return text[start:end + len(end_phrase)].strip()


def load_source_text(source: dict) -> str:
    path = Path(source["local_path"])

    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()

    if sha256(raw) != source["sha256"]:
        raise ValueError(
            f"Source SHA-256 mismatch: {source['source_id']}"
        )

    return normalize(extract_text(raw))


def main():
    # 1. 기존 정책 및 Evidence 읽기
    policy = json.loads(
        POLICY_PATH.read_text(encoding="utf-8")
    )

    original = json.loads(
        EVIDENCE_PATH.read_text(encoding="utf-8")
    )

    sources = {
        s["source_id"]: s
        for s in policy["official_sources"]
    }

    policies = {
        r["policy_id"]: r
        for r in policy["policy_records"]
    }

    records = original["evidence_records"]

    assert len(sources) == EXPECTED_SOURCE_COUNT
    assert len(policies) == EXPECTED_POLICY_COUNT
    assert len(records) == EXPECTED_EVIDENCE_COUNT

    assert original["source_count"] == 8
    assert original["policy_count"] == 26
    assert original["evidence_count"] == 30
    assert original["covered_policy_count"] == 26
    assert original["missing_search_count"] == 0

    original_evidence_ids = [
        r["evidence_id"] for r in records
    ]

    assert len(original_evidence_ids) == len(
        set(original_evidence_ids)
    )

    # 2. 필요한 공식 자료 로드 및 해시 확인
    needed_sources = [
        "DOS-TEMP-WORKER",
        "DOS-KR-RECIPROCITY",
        "USCIS-L1-POLICY-MANUAL",
        "DOS-NIV-INTERVIEW-LOCATION-20260715",
        "DOS-DS160-INSTRUCTIONS",
    ]

    source_texts = {}

    for source_id in needed_sources:
        assert source_id in sources

        source_texts[source_id] = load_source_text(
            sources[source_id]
        )

    dos = source_texts["DOS-TEMP-WORKER"]
    korea = source_texts["DOS-KR-RECIPROCITY"]
    manual = source_texts["USCIS-L1-POLICY-MANUAL"]
    interview = source_texts[
        "DOS-NIV-INTERVIEW-LOCATION-20260715"
    ]
    ds160 = source_texts["DOS-DS160-INSTRUCTIONS"]

    # 3. 정책별 정제 발췌문
    # L1-17은 서로 다른 공식 Evidence 2건을 정제
    replacements = {
        (
            "L1-16",
            "Form I-129",
        ): extract_between(
            dos,
            "Before an applicant can apply for a temporary worker visa",
            "Form I-797.",
        ),

        (
            "L1-17",
            "$205",
        ): extract_between(
            dos,
            "Fees - Pay the non-refundable visa application fee",
            "$205",
        ),

        (
            "L1-17",
            "Print and keep the DS-160 barcode page.",
        ): extract_between(
            ds160,
            "Print and keep the DS-160 barcode page.",
            "Review country-specific instructions on the U.S. Embassy or Consulate website.",
        ),

        (
            "L1-19",
            "L-1 None Multiple 60 Months",
        ): extract_between(
            korea,
            "L-1 None Multiple 60 Months",
            "L-2 None Multiple 60 Months",
        ),

        (
            "L1-23",
            "L-1 Blanket Petitions",
        ): extract_between(
            manual,
            "L-1 Blanket Petitions",
            "for which it seeks blanket preapproval.",
        ),

        (
            "L1-24",
            "Special Consideration: L-1A New Office Petitions",
        ): extract_between(
            manual,
            "Special Consideration: L-1A New Office Petitions",
            "sufficient physical premises to house the new office have been secured.",
        ),

        (
            "L1-25",
            "Extension of L-1 New Office Petitions",
        ): extract_between(
            manual,
            "Extension of L-1 New Office Petitions",
            "any future extension filing is treated as a regular individual L extension.",
        ),

        (
            "L1-26",
            "Applicants for U.S. nonimmigrant visas (NIV) should schedule",
        ): extract_between(
            interview,
            "Applicants for U.S. nonimmigrant visas (NIV) should schedule",
            "operating status and services.",
        ),
    }

    # 4. 기존 Evidence를 복사한 후 정제
    refined = copy.deepcopy(original)

    modified = []
    matched_keys = set()

    for record in refined["evidence_records"]:
        key = (
            record["policy_id"],
            record["search_phrase"],
        )

        if key not in replacements:
            continue

        assert key not in matched_keys

        policy_id = record["policy_id"]
        source_id = record["source_id"]
        replacement = replacements[key]

        assert policy_id in policies
        assert source_id in source_texts
        assert source_id in policies[policy_id]["source_ids"]

        assert (
            record["source_sha256"]
            == sources[source_id]["sha256"]
        )

        assert (
            record["source_path"]
            == sources[source_id]["local_path"]
        )

        assert replacement in source_texts[source_id]

        record["evidence_excerpt"] = replacement
        record["excerpt_sha256"] = sha256(
            replacement.encode("utf-8")
        )

        record["evidence_type"] = (
            "refined_candidate_excerpt"
        )
        record["semantic_support_verified"] = False
        record["review_status"] = "needs_review"

        modified.append(policy_id)
        matched_keys.add(key)

    # 5. 정제 대상 검증
    assert matched_keys == set(replacements)
    assert len(modified) == 8
    assert sorted(set(modified)) == REFINED_POLICY_IDS

    counts = Counter(modified)
    assert counts["L1-17"] == 2
    assert all(
        counts[policy_id] == 1
        for policy_id in REFINED_POLICY_IDS
        if policy_id != "L1-17"
    )

    # 신규 DS-160 Evidence에 메뉴가 포함되지 않았는지 검증
    ds160_evidence = next(
        r for r in refined["evidence_records"]
        if (
            r["policy_id"] == "L1-17"
            and r["source_id"] == "DOS-DS160-INSTRUCTIONS"
        )
    )

    ds160_excerpt = ds160_evidence["evidence_excerpt"]

    assert ds160_excerpt.startswith(
        "Print and keep the DS-160 barcode page."
    )
    assert ds160_excerpt.endswith(
        "Review country-specific instructions on the U.S. Embassy or Consulate website."
    )
    assert "More Information A-Z Index" not in ds160_excerpt

    # 6. 메타데이터 갱신
    refined["source_count"] = len(sources)
    refined["policy_count"] = len(policies)
    refined["evidence_count"] = len(
        refined["evidence_records"]
    )

    covered_ids = {
        r["policy_id"]
        for r in refined["evidence_records"]
    }

    refined["covered_policy_count"] = len(covered_ids)
    refined["missing_search_count"] = 0

    refined["refined_policy_ids"] = REFINED_POLICY_IDS
    refined["refinement_status"] = (
        "partial_refinement_needs_review"
    )
    refined["validation_status"] = "needs_review"

    refined["approved_for_user_answers"] = False
    refined["approved_for_embedding"] = False
    refined["embedding_generated"] = False

    # 7. 최종 무결성 및 안전 설정 확인
    assert len(refined["evidence_records"]) == 30
    assert covered_ids == set(policies)

    assert [
        r["evidence_id"]
        for r in refined["evidence_records"]
    ] == original_evidence_ids

    for record in refined["evidence_records"]:
        excerpt = record["evidence_excerpt"]

        assert sha256(
            excerpt.encode("utf-8")
        ) == record["excerpt_sha256"]

        assert record["policy_id"] in policies
        assert record["source_id"] in sources

        assert (
            record["source_id"]
            in policies[record["policy_id"]]["source_ids"]
        )

        assert record["semantic_support_verified"] is False
        assert record["review_status"] == "needs_review"

    assert refined["source_count"] == 8
    assert refined["policy_count"] == 26
    assert refined["evidence_count"] == 30
    assert refined["covered_policy_count"] == 26
    assert refined["missing_search_count"] == 0

    assert all(
        refined[k] is False
        for k in [
            "approved_for_user_answers",
            "approved_for_embedding",
            "embedding_generated",
        ]
    )

    # 8. 모든 검증을 통과한 뒤 동일 파일에 덮어쓰기
    EVIDENCE_PATH.write_text(
        json.dumps(
            refined,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("=== L-1 REFINED EVIDENCE ===")
    print("Official sources:", refined["source_count"])
    print("Policies:", refined["policy_count"])
    print("Evidence records:", refined["evidence_count"])
    print("Covered policies:", refined["covered_policy_count"])
    print("Refined policy IDs:", ", ".join(REFINED_POLICY_IDS))
    print("Refined evidence records:", len(modified))
    print("Missing searches:", refined["missing_search_count"])
    print("Saved:", EVIDENCE_PATH)
    print("[PASS] 8 sources, 26 policies, 30 evidence records")
    print("[PASS] 8 targeted evidence refinements")
    print("[PASS] DS-160 navigation text excluded")
    print("[PASS] Existing evidence JSON updated")
    print("[INFO] Semantic and legal review still required")


if __name__ == "__main__":
    main()
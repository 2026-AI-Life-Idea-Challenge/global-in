
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_structured_policies_2026_reviewed_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_draft.json"

# Source ID suffixes are abbreviated only in this mapping.
DUPLICATE_GROUPS = {
    "0023": ["0042", "0044"],
    "0064": ["0065", "0067"],
    "0061": ["0085"],
    "0004": ["0106", "0108"],
}

LEGAL_REVIEW_SUFFIXES = {
    "0007", "0008", "0022", "0053",
    "0057", "0072", "0100", "0103",
}

MISSING_POLICY_TOPICS = [
    {
        "topic": "standard_h1b_period_of_stay",
        "description_ko": (
            "H-1B 일반 최초 체류 최대 3년 및 "
            "추가 연장·일반적인 총 6년 규정"
        ),
        "preferred_source_id": "USCIS-H1B-OVERVIEW",
        "evidence_status": "not_in_review_packet",
        "review_status": "needs_review",
    },
]


def suffix_id(short_id):
    return "US-WK-01-POL-" + short_id


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"기존 파일 덮어쓰기 금지: {OUTPUT}"
        )

    data = json.loads(
        INPUT.read_text(encoding="utf-8-sig")
    )
    records = data["policy_records"]

    if len(records) != 111:
        raise ValueError("정책 레코드 수 불일치")

    by_id = {r["policy_id"]: r for r in records}

    if len(by_id) != 111:
        raise ValueError("중복 정책 ID 발견")

    # Check all review decisions and evidence hashes.
    for record in records:
        actual_hash = hashlib.sha256(
            record["evidence_excerpt"].encode("utf-8")
        ).hexdigest()

        if actual_hash != record["excerpt_sha256"]:
            raise ValueError(
                f"Evidence 해시 불일치: {record['policy_id']}"
            )

        if (
            record["review_status"] != "needs_review"
            or record["legal_status"] != "unverified"
            or record["semantic_support_verified"]
            or record["legal_effect_verified"]
        ):
            raise ValueError(
                f"검토 상태 오류: {record['policy_id']}"
            )

    links = []
    linked_ids = set()

    for primary_short, duplicate_shorts in DUPLICATE_GROUPS.items():
        primary_id = suffix_id(primary_short)
        primary = by_id[primary_id]

        for short in duplicate_shorts:
            duplicate_id = suffix_id(short)
            duplicate = by_id[duplicate_id]

            if duplicate["human_review_decision"] != "duplicate_support":
                raise ValueError(
                    f"중복 판정 불일치: {duplicate_id}"
                )

            links.append({
                "primary_policy_id": primary_id,
                "supporting_policy_id": duplicate_id,
                "primary_source_id": primary["source_id"],
                "supporting_source_id": duplicate["source_id"],
                "supporting_excerpt_sha256": duplicate["excerpt_sha256"],
                "link_status": "proposed",
                "review_status": "needs_review",
            })
            linked_ids.add(duplicate_id)

    all_duplicates = {
        r["policy_id"] for r in records
        if r["human_review_decision"] == "duplicate_support"
    }

    if linked_ids != all_duplicates:
        raise ValueError("중복 근거 연결 누락")

    legal_records = [
        r["policy_id"] for r in records
        if r["human_review_decision"] == "legal_effect_review"
    ]

    if {
        x[-4:] for x in legal_records
    } != LEGAL_REVIEW_SUFFIXES:
        raise ValueError("법적 효력 검토 대상 불일치")

    decisions = Counter(
        r["human_review_decision"] for r in records
    )

    result = {
        "program_id": "US-WK-01",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "input_file": INPUT.as_posix(),
        "input_record_count": len(records),
        "review_decision_counts": dict(decisions),
        "duplicate_evidence_links": links,
        "legal_effect_review_policy_ids": legal_records,
        "missing_policy_topics": MISSING_POLICY_TOPICS,
        "policy_records": records,
        "review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    saved = json.loads(OUTPUT.read_text(encoding="utf-8"))

    if (
        len(saved["policy_records"]) != 111
        or len(saved["duplicate_evidence_links"]) != 7
        or len(saved["legal_effect_review_policy_ids"]) != 8
        or saved["approved_for_user_answers"] is not False
        or saved["approved_for_embedding"] is not False
        or saved["automatic_eligibility_rules_enabled"] is not False
    ):
        raise ValueError("저장 결과 검증 실패")

    print("\n=== H-1B CONSOLIDATION VALIDATION ===")
    print("PRESERVED RECORDS:", len(saved["policy_records"]))
    print("DUPLICATE LINKS:", len(saved["duplicate_evidence_links"]))
    print(
        "LEGAL REVIEW ITEMS:",
        len(saved["legal_effect_review_policy_ids"])
    )
    print(
        "MISSING POLICY TOPICS:",
        len(saved["missing_policy_topics"])
    )
    print("EVIDENCE HASHES: PASS")
    print("REVIEW STATUS:", saved["review_status"])
    print("APPROVED FOR ANSWERS:", saved["approved_for_user_answers"])
    print("APPROVED FOR EMBEDDING:", saved["approved_for_embedding"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
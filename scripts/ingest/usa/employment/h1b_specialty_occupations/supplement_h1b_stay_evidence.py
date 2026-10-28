
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_consolidation_2026_draft.json"
V2 = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_supplemented_draft.json"

SOURCE_ID = "USCIS-H1B-OVERVIEW"

PATTERN = re.compile(
    r"period of stay|three years|six years|"
    r"3 years|6 years|3-year|sixth year|"
    r"three-year|six-year",
    re.IGNORECASE,
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"기존 파일 덮어쓰기 금지: {OUTPUT}"
        )

    consolidated = load(INPUT)
    v2 = load(V2)

    originals = consolidated["policy_records"]
    candidates = v2["candidate_records"]

    if len(originals) != 111 or len(candidates) != 1537:
        raise ValueError("입력 레코드 수 불일치")

    source_references = {
        (p["source_sha256"], p["source_url"])
        for p in originals
        if p["source_id"] == SOURCE_ID
    }

    if len(source_references) != 1:
        raise ValueError("USCIS Overview 출처가 불명확함")

    expected_source_hash, source_url = next(
        iter(source_references)
    )

    existing_ids = {
        p["source_candidate_id"] for p in originals
    }

    matched = []

    for c in candidates:
        if c["source_id"] != SOURCE_ID:
            continue

        text = c["evidence_excerpt"]

        if not PATTERN.search(text):
            continue

        if c["source_sha256"] != expected_source_hash:
            raise ValueError("원본 출처 해시 불일치")

        if sha256(text) != c["excerpt_sha256"]:
            raise ValueError("인용문 해시 불일치")

        matched.append(c)

    matched.sort(
        key=lambda c: c["source_paragraph_index"]
    )

    if not matched:
        raise ValueError(
            "체류 기간 관련 문단을 찾지 못했습니다"
        )

    supplements = []

    for candidate in matched:
        cid = candidate["candidate_id"]

        # Already included excerpts stay in the existing 111 records.
        if cid in existing_ids:
            continue

        supplements.append({
            "supplement_id": (
                f"US-WK-01-STAY-EV-{len(supplements) + 1:03d}"
            ),
            "source_candidate_id": cid,
            "source_id": SOURCE_ID,
            "source_url": source_url,
            "source_sha256": expected_source_hash,
            "source_paragraph_index": (
                candidate["source_paragraph_index"]
            ),
            "evidence_excerpt": (
                candidate["evidence_excerpt"]
            ),
            "excerpt_sha256": (
                candidate["excerpt_sha256"]
            ),
            "proposed_topic": "stay_extension",
            "policy_statement_ko": None,
            "human_review_decision": None,
            "legal_effect_verified": False,
            "semantic_support_verified": False,
            "review_status": "needs_review",
        })

    if not supplements:
        raise ValueError(
            "새로 연결할 체류 기간 Evidence가 없습니다"
        )

    result = {
        **consolidated,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "supplemental_evidence_count": len(supplements),
        "supplemental_stay_evidence": supplements,
        "missing_policy_topics": [
            {
                **item,
                "evidence_status": (
                    "supplemental_evidence_collected_"
                    "semantic_review_pending"
                ),
            }
            for item in consolidated["missing_policy_topics"]
        ],
        "review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            result, f, ensure_ascii=False, indent=2
        )

    saved = load(OUTPUT)

    if len(saved["policy_records"]) != 111:
        raise ValueError("기존 정책 레코드 손실")

    if len(saved["duplicate_evidence_links"]) != 7:
        raise ValueError("중복 근거 연결 손실")

    if len(saved["legal_effect_review_policy_ids"]) != 8:
        raise ValueError("법적 검토 대상 손실")

    for old, new in zip(
        consolidated["policy_records"],
        saved["policy_records"],
    ):
        if old != new:
            raise ValueError("기존 정책 내용 변경 발견")

    for item in saved["supplemental_stay_evidence"]:
        if sha256(item["evidence_excerpt"]) != item["excerpt_sha256"]:
            raise ValueError("추가 Evidence 해시 불일치")

    safety_fields = [
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    ]

    if any(saved[field] is not False for field in safety_fields):
        raise ValueError("승인 상태 오류")

    print("\n=== H-1B STAY EVIDENCE SUPPLEMENT ===")
    print("ORIGINAL RECORDS:", len(saved["policy_records"]))
    print("MATCHED SOURCE PARAGRAPHS:", len(matched))
    print("NEW SUPPLEMENTAL EVIDENCE:", len(supplements))
    print("DUPLICATE LINKS:", len(saved["duplicate_evidence_links"]))
    print(
        "LEGAL REVIEW ITEMS:",
        len(saved["legal_effect_review_policy_ids"])
    )
    print("EXISTING RECORDS UNCHANGED: PASS")
    print("EVIDENCE HASHES: PASS")

    print("\n=== EVIDENCE PREVIEW ===")
    for item in supplements:
        print(
            item["supplement_id"],
            "| PARAGRAPH:",
            item["source_paragraph_index"],
            "|",
            item["evidence_excerpt"][:400],
        )

    print("\n=== SAFETY ===")
    print("REVIEW STATUS:", saved["review_status"])
    print("APPROVED FOR ANSWERS:", saved["approved_for_user_answers"])
    print("APPROVED FOR EMBEDDING:", saved["approved_for_embedding"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
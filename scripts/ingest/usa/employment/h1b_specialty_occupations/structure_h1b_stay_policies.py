
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_consolidation_2026_supplemented_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_stay_structured_draft.json"

POLICY_DEFINITIONS = {
    "US-WK-01-STAY-EV-001": {
        "policy_id": "US-WK-01-POL-STAY-001",
        "policy_statement_ko": (
            "H-1B 전문직 근로자는 일반적으로 최초 최대 3년간 "
            "체류할 수 있으며, 일반적으로 추가 최대 3년을 "
            "연장하여 총 6년까지 체류할 수 있다."
        ),
        "applicability": (
            "H-1B 전문직 근로자의 일반 체류기간. "
            "지배지분 보유자 등 별도 규정 적용 여부 확인 필요."
        ),
        "requirements": [],
        "exceptions": [],
        "unresolved_questions": [
            "청원 기업 지배지분 보유자에 대한 별도 체류기간 제한",
            "6년 총 체류기간의 예외와 적용 조건",
        ],
    },
    "US-WK-01-STAY-EV-002": {
        "policy_id": "US-WK-01-POL-STAY-002",
        "policy_statement_ko": (
            "일정한 요건을 충족하는 H-1B 근로자는 노동허가 "
            "신청서 또는 이민청원서가 접수된 후 최소 365일이 "
            "경과한 경우 일반적인 6년 체류기간을 초과하는 "
            "연장 대상이 될 수 있다."
        ),
        "applicability": (
            "일반적인 H-1B 6년 체류한도를 초과하는 "
            "연장을 신청하는 근로자 중 관련 조건 충족자."
        ),
        "requirements": [
            "관련 노동허가 신청서 또는 이민청원서 접수 후 "
            "최소 365일 경과 여부 확인"
        ],
        "exceptions": [],
        "unresolved_questions": [
            "접수된 신청서의 종류 및 유효성",
            "연장 단위, 추가 자격요건 및 제한 사유",
            "전체 원문과 8 CFR 214.2(h)(13)(iii)(D) 대조",
        ],
    },
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"기존 결과 덮어쓰기 금지: {OUTPUT}"
        )

    data = load(INPUT)
    records = data["policy_records"]
    evidence = data["supplemental_stay_evidence"]

    if len(records) != 111 or len(evidence) != 2:
        raise ValueError("예상한 입력 레코드 수와 다릅니다")

    evidence_map = {
        e["supplement_id"]: e for e in evidence
    }

    if set(evidence_map) != set(POLICY_DEFINITIONS):
        raise ValueError("체류 Evidence ID 불일치")

    new_policies = []

    for evidence_id, definition in POLICY_DEFINITIONS.items():
        item = evidence_map[evidence_id]
        excerpt = item["evidence_excerpt"]

        if sha256(excerpt) != item["excerpt_sha256"]:
            raise ValueError(
                f"Evidence 해시 불일치: {evidence_id}"
            )

        if item["source_id"] != "USCIS-H1B-OVERVIEW":
            raise ValueError("예상하지 않은 출처")

        if evidence_id.endswith("001"):
            if not all(
                term in excerpt.lower()
                for term in (
                    "up to 3 years",
                    "6 years",
                    "controlling interest",
                )
            ):
                raise ValueError("기본 체류기간 근거 부족")

        if evidence_id.endswith("002"):
            if not all(
                term in excerpt.lower()
                for term in (
                    "365 days",
                    "beyond the sixth year",
                )
            ):
                raise ValueError("6년 초과 연장 근거 부족")

        new_policies.append({
            **definition,
            "program_id": "US-WK-01",
            "topic": "stay_extension",
            "supplement_id": evidence_id,
            "source_id": item["source_id"],
            "source_url": item["source_url"],
            "source_sha256": item["source_sha256"],
            "source_paragraph_index": (
                item["source_paragraph_index"]
            ),
            "evidence_excerpt": excerpt,
            "excerpt_sha256": item["excerpt_sha256"],
            "human_review_decision": "policy_draft_candidate",
            "legal_status": "unverified",
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        })

    result = {
        **data,
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "structured_stay_policy_count": len(new_policies),
        "supplemental_stay_policy_drafts": new_policies,
        "missing_policy_topics": [
            {
                **topic,
                "evidence_status": (
                    "structured_draft_created_review_pending"
                ),
            }
            for topic in data["missing_policy_topics"]
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

    if saved["policy_records"] != records:
        raise ValueError("기존 111개 정책 변경")

    if saved["supplemental_stay_evidence"] != evidence:
        raise ValueError("추가 Evidence 변경")

    if len(saved["supplemental_stay_policy_drafts"]) != 2:
        raise ValueError("정책 초안 수 불일치")

    if (
        len(saved["duplicate_evidence_links"]) != 7
        or len(saved["legal_effect_review_policy_ids"]) != 8
    ):
        raise ValueError("기존 검토 정보 손실")

    for policy in saved["supplemental_stay_policy_drafts"]:
        if sha256(policy["evidence_excerpt"]) != policy["excerpt_sha256"]:
            raise ValueError("저장된 Evidence 해시 불일치")

        if (
            policy["review_status"] != "needs_review"
            or policy["legal_status"] != "unverified"
            or policy["semantic_support_verified"]
            or policy["legal_effect_verified"]
        ):
            raise ValueError("정책 승인 상태 오류")

    for key in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    ):
        if saved[key] is not False:
            raise ValueError(f"안전 상태 오류: {key}")

    print("\n=== H-1B STAY POLICY VALIDATION ===")
    print("ORIGINAL RECORDS:", len(saved["policy_records"]))
    print(
        "SUPPLEMENTAL EVIDENCE:",
        len(saved["supplemental_stay_evidence"])
    )
    print(
        "NEW STAY POLICY DRAFTS:",
        len(saved["supplemental_stay_policy_drafts"])
    )
    print(
        "DUPLICATE LINKS:",
        len(saved["duplicate_evidence_links"])
    )
    print(
        "LEGAL REVIEW ITEMS:",
        len(saved["legal_effect_review_policy_ids"])
    )
    print("ORIGINAL RECORDS UNCHANGED: PASS")
    print("EVIDENCE HASHES: PASS")

    print("\n=== NEW POLICY DRAFTS ===")
    for policy in saved["supplemental_stay_policy_drafts"]:
        print(policy["policy_id"])
        print(" ", policy["policy_statement_ko"])
        print(
            "  UNRESOLVED QUESTIONS:",
            len(policy["unresolved_questions"])
        )

    print("\n=== SAFETY ===")
    print("REVIEW STATUS:", saved["review_status"])
    print("VERIFIED POLICIES: 0")
    print("APPROVED FOR ANSWERS:", saved["approved_for_user_answers"])
    print("APPROVED FOR EMBEDDING:", saved["approved_for_embedding"])
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
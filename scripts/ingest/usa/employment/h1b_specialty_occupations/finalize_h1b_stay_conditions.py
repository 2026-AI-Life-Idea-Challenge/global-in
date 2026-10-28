
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_consolidation_2026_stay_structured_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_conditions_draft.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"덮어쓰기 금지: {OUTPUT}")

    original = load(INPUT)
    result = deepcopy(original)

    policies = result["supplemental_stay_policy_drafts"]
    by_id = {p["policy_id"]: p for p in policies}

    expected_ids = {
        "US-WK-01-POL-STAY-001",
        "US-WK-01-POL-STAY-002",
    }

    if len(policies) != 2 or set(by_id) != expected_ids:
        raise ValueError("체류 정책 ID 불일치")

    first = by_id["US-WK-01-POL-STAY-001"]
    second = by_id["US-WK-01-POL-STAY-002"]

    for policy in policies:
        if policy["source_id"] != "USCIS-H1B-OVERVIEW":
            raise ValueError("출처 불일치")

        if sha256(policy["evidence_excerpt"]) != policy["excerpt_sha256"]:
            raise ValueError("원문 해시 불일치")

    first_text = first["evidence_excerpt"].lower()
    second_text = second["evidence_excerpt"].lower()

    required_first = (
        "up to 3 years",
        "6 years",
        "more than 50%",
        "majority voting rights",
        "18 months",
    )
    required_second = (
        "365 days",
        "labor certification",
        "immigrant visa petition",
        "beyond the sixth year",
    )

    if not all(x in first_text for x in required_first):
        raise ValueError("STAY-001 원문 조건 불충분")

    if not all(x in second_text for x in required_second):
        raise ValueError("STAY-002 원문 조건 불충분")

    first["policy_statement_ko"] = (
        "H-1B 전문직 근로자는 일반적으로 최초 최대 3년간 "
        "체류할 수 있고, 추가 최대 3년을 연장하여 총 6년까지 "
        "체류할 수 있다. 다만 청원 기업의 지분을 50% 초과 "
        "보유하거나 과반수 의결권을 가진 근로자는 최초 청원과 "
        "첫 연장 청원의 승인 유효기간이 각각 최대 18개월로 제한된다."
    )
    first["applicability"] = (
        "H-1B 전문직 근로자. 지배지분 또는 과반수 의결권 "
        "보유자는 별도 승인 유효기간 제한 적용."
    )
    first["special_conditions"] = [
        {
            "condition": "controlling_interest",
            "ownership_threshold": "more_than_50_percent",
            "alternative_condition": "majority_voting_rights",
            "initial_petition_max_months": 18,
            "first_extension_max_months": 18,
        }
    ]
    first["unresolved_questions"] = [
        "6년 일반 체류한도의 예외 및 추가 연장 사유",
        "개별 청원의 실제 승인 가능 기간과 기타 제한",
    ]

    second["policy_statement_ko"] = (
        "H-1B 근로자는 필요한 경우 노동부에 노동허가 신청서가 "
        "접수되었거나 USCIS에 이민청원서가 접수된 뒤 "
        "최소 365일이 경과했다면, 관련 추가 요건에 따라 "
        "일반적인 6년 체류기간을 초과하여 연장할 수 있다."
    )
    second["applicability"] = (
        "6년 체류한도를 초과하는 H-1B 연장 신청 중 "
        "8 CFR 214.2(h)(13)(iii)(D) 관련 요건을 충족하는 경우."
    )
    second["requirements"] = [
        "필요한 경우 노동부 노동허가 신청서 접수 또는 "
        "USCIS 이민청원서 접수",
        "해당 접수 이후 최소 365일 경과",
        "그 밖의 적용 요건은 별도 검토 필요",
    ]
    second["unresolved_questions"] = [
        "접수된 신청서의 상태 및 추가 법적 요건",
        "연장 가능 기간 및 제한 사유",
        "8 CFR 214.2(h)(13)(iii)(D) 전체 조항 대조",
    ]

    for policy in policies:
        policy["legal_status"] = "unverified"
        policy["semantic_support_verified"] = False
        policy["legal_effect_verified"] = False
        policy["review_status"] = "needs_review"

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    if result["policy_records"] != original["policy_records"]:
        raise ValueError("기존 111건 변경됨")

    if result["supplemental_stay_evidence"] != original["supplemental_stay_evidence"]:
        raise ValueError("추가 원문 변경됨")

    if (
        len(result["duplicate_evidence_links"]) != 7
        or len(result["legal_effect_review_policy_ids"]) != 8
    ):
        raise ValueError("기존 검토 관계 손실")

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    saved = load(OUTPUT)

    assert len(saved["policy_records"]) == 111
    assert len(saved["supplemental_stay_policy_drafts"]) == 2
    assert saved["approved_for_user_answers"] is False
    assert saved["approved_for_embedding"] is False
    assert saved["automatic_eligibility_rules_enabled"] is False
    assert saved["review_status"] == "needs_review"

    print("\n=== H-1B STAY CONDITIONS VALIDATION ===")
    print("ORIGINAL POLICY RECORDS: 111")
    print("STAY POLICY DRAFTS: 2")
    print("CONTROLLING INTEREST LIMIT: 18 MONTHS")
    print("BEYOND SIX YEARS: 365-DAY CONDITION")
    print("DUPLICATE LINKS:", len(saved["duplicate_evidence_links"]))
    print("LEGAL REVIEW ITEMS:", len(saved["legal_effect_review_policy_ids"]))
    print("ORIGINAL EVIDENCE PRESERVED: PASS")
    print("SAFETY: needs_review / approvals disabled")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
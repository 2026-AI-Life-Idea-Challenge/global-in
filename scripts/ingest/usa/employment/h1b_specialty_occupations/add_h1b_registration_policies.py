
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_consolidation_2026_core_supplemented_draft.json"
CANDIDATES = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_registration_draft.json"

NEW_POLICIES = {
    67: (
        "H-1B Cap 전자등록의 최초 등록기간은 "
        "매 회계연도 최소 14일이다. 선정 통지를 받은 "
        "등록자는 해당 수혜자에 대한 Cap 대상 청원을 "
        "제출할 수 있다."
    ),
    75: (
        "H-1B 등록자는 해당 SOC 코드와 예정 근무지역에 "
        "대해 등록 시 선택한 OEWS 임금수준 이상의 "
        "임금을 제시한다는 사실을 진술해야 한다."
    ),
    76: (
        "H-1B 등록자는 수혜자의 선정 가능성을 부당하게 "
        "높이기 위해 다른 등록자·청원인·대리인 등과 "
        "공모하지 않았다는 사실을 진술해야 한다."
    ),
    77: (
        "H-1B 등록 과정의 허위 진술이 확인되면 "
        "해당 등록은 부적법하게 제출된 것으로 판단될 수 "
        "있으며, 이를 근거로 청원이 거절되거나 "
        "기존 승인이 취소될 수 있다."
    ),
    86: (
        "동일한 H-1B 청원 예정자는 같은 회계연도에 "
        "동일 수혜자를 한 번만 등록할 수 있다. "
        "최초 등록기간 종료 후 해당 등록자의 중복 등록이 "
        "확인되면 그 등록자가 제출한 해당 수혜자의 "
        "등록 전부가 선정 절차에서 무효화될 수 있다."
    ),
}

SUPPORT = {
    31: "US-WK-01-POL-0004",
    91: "H1B-CAND-V2-00076",
    92: "H1B-CAND-V2-00077",
}

OPERATIONS = {
    81: "organizational_account",
    85: "organization_company_account",
    93: "fy2027_registration_fee",
    97: "registration_submitted_status",
    98: "registration_denied_status",
    99: "registration_failed_payment_status",
}

CONTEXT_HOLD = {48}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def candidate_id(n):
    return f"H1B-CAND-V2-{n:05d}"


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"덮어쓰기 금지: {OUTPUT}")

    original = load(INPUT)
    source = load(CANDIDATES)

    records = original["policy_records"]
    candidates = source["candidate_records"]

    if len(records) != 111 or len(candidates) != 1537:
        raise ValueError("기존 데이터 수 불일치")

    expected = (
        set(NEW_POLICIES)
        | set(SUPPORT)
        | set(OPERATIONS)
        | CONTEXT_HOLD
    )

    if len(expected) != 15:
        raise ValueError("대상 문단 수 불일치")

    index = {c["candidate_id"]: c for c in candidates}

    used_groups = [
        "policy_records",
        "supplemental_stay_evidence",
        "additional_core_policy_drafts",
        "additional_supporting_evidence",
        "additional_legal_review_evidence",
    ]

    previously_used = {
        r["source_candidate_id"]
        for group in used_groups
        for r in original[group]
    }

    # Match the source URL using both source ID and hash.
    source_urls = {
        (r["source_id"], r["source_sha256"]): r["source_url"]
        for r in records
    }

    added = []
    supporting = []
    operations = []
    held = []

    for number in sorted(expected):
        cid = candidate_id(number)

        if cid in previously_used:
            raise ValueError(f"이미 검토한 후보: {cid}")

        candidate = index[cid]
        excerpt = candidate["evidence_excerpt"]

        if sha256(excerpt) != candidate["excerpt_sha256"]:
            raise ValueError(f"Evidence 해시 불일치: {cid}")

        key = (
            candidate["source_id"],
            candidate["source_sha256"],
        )

        if key not in source_urls:
            raise ValueError(f"원본 출처 연결 실패: {cid}")

        if number == 31:
            required_source = "USCIS-H1B-OVERVIEW"
        elif number == 48:
            required_source = "USCIS-H1B-OVERVIEW"
        else:
            required_source = "USCIS-H1B-REGISTRATION"

        if candidate["source_id"] != required_source:
            raise ValueError(f"예상 출처 불일치: {cid}")

        base = {
            "source_candidate_id": cid,
            "source_id": candidate["source_id"],
            "source_url": source_urls[key],
            "source_sha256": candidate["source_sha256"],
            "source_paragraph_index": (
                candidate["source_paragraph_index"]
            ),
            "evidence_excerpt": excerpt,
            "excerpt_sha256": candidate["excerpt_sha256"],
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        if number in NEW_POLICIES:
            added.append({
                **base,
                "policy_id": (
                    f"US-WK-01-POL-REG-{len(added)+1:03d}"
                ),
                "program_id": "US-WK-01",
                "policy_statement_ko": NEW_POLICIES[number],
                "applicability": (
                    "H-1B Cap 대상 전자등록 절차"
                ),
                "requirements": [],
                "exceptions": [],
                "effective_date": None,
                "expiration_date": None,
                "legal_status": "unverified",
                "human_review_decision": "policy_draft_candidate",
                "review_rationale_ko": (
                    "USCIS 원문 기반 신규 등록 규정 초안. "
                    "조건·현행성 최종 검증 필요."
                ),
            })

        elif number in SUPPORT:
            supporting.append({
                **base,
                "supports": SUPPORT[number],
                "link_status": "proposed",
                "human_review_decision": "duplicate_support",
            })

        elif number in OPERATIONS:
            operations.append({
                **base,
                "operation_type": OPERATIONS[number],
                "fiscal_year": (
                    2027 if number == 93 else None
                ),
                "human_review_decision": "operational_information",
            })

        else:
            held.append({
                **base,
                "human_review_decision": "context_required",
                "review_reason_ko": (
                    "1년 단위 체류 연장 규정의 "
                    "선행 조건과 후속 문맥 확인 필요"
                ),
            })

    result = deepcopy(original)

    result["additional_registration_policy_drafts"] = added
    result["registration_supporting_evidence"] = supporting
    result["registration_operational_information"] = operations
    result["registration_context_review"] = held

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    saved = load(OUTPUT)

    if any(
        saved[group] != original[group]
        for group in used_groups
    ):
        raise ValueError("기존 데이터 손실 또는 변경")

    groups = [
        "additional_registration_policy_drafts",
        "registration_supporting_evidence",
        "registration_operational_information",
        "registration_context_review",
    ]

    sizes = [len(saved[group]) for group in groups]

    if sizes != [5, 3, 6, 1]:
        raise ValueError(f"분류 건수 오류: {sizes}")

    all_new = [
        record
        for group in groups
        for record in saved[group]
    ]

    if len({r["source_candidate_id"] for r in all_new}) != 15:
        raise ValueError("추가 후보 ID 중복")

    for record in all_new:
        if (
            sha256(record["evidence_excerpt"])
            != record["excerpt_sha256"]
        ):
            raise ValueError("저장된 Evidence 무결성 오류")

        if (
            record["semantic_support_verified"]
            or record["legal_effect_verified"]
            or record["review_status"] != "needs_review"
        ):
            raise ValueError("검토 상태 오류")

    for field in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    ):
        if saved[field] is not False:
            raise ValueError(f"안전 상태 오류: {field}")

    print("\n=== H-1B REGISTRATION SUPPLEMENT ===")
    print("ORIGINAL RECORDS:", len(records))
    print("EXISTING STAY DRAFTS:",
          len(saved["supplemental_stay_policy_drafts"]))
    print("EXISTING CORE ADDITIONS:",
          len(saved["additional_core_policy_drafts"]))
    print("NEW REGISTRATION POLICIES:", sizes[0])
    print("NEW SUPPORTING EVIDENCE:", sizes[1])
    print("OPERATIONAL ITEMS:", sizes[2])
    print("CONTEXT REVIEW ITEMS:", sizes[3])
    print("NEWLY CLASSIFIED:", len(all_new))
    print("TOTAL CLASSIFIED CANDIDATES:", 131 + len(all_new))
    print("REMAINING CANDIDATES:", 1537 - 131 - len(all_new))
    print("EXISTING DATA UNCHANGED: PASS")
    print("EVIDENCE HASHES: PASS")
    print("REVIEW STATUS: needs_review")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()

import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path("data/processed/usa/employment/h1b_specialty_occupation")
INPUT = BASE / "h1b_policy_consolidation_2026_registration_draft.json"
SOURCE = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_employer_obligations_draft.json"

POLICIES = {
    125: (
        "H-1B 청원서에 정규직으로 기재된 근로자가 고용을 시작한 후 "
        "고용주의 업무 부족 등 결정이나 근로자의 허가·면허 부족으로 "
        "비생산 상태에 놓인 경우, 고용주는 해당 기간에도 "
        "법에서 요구하는 정규직 임금을 지급해야 한다."
    ),
    126: (
        "H-1B 청원서에 시간제로 기재된 근로자가 고용을 시작한 후 "
        "관련 규정상 비생산 상태에 놓인 경우, 고용주는 청원서에 "
        "명시된 근무시간과 임금률에 따른 임금을 지급해야 한다."
    ),
    127: (
        "승인된 H-1B 청원이 있지만 근로자가 아직 고용을 시작하지 "
        "않은 경우, 관련 비생산 기간 임금 지급 의무는 청원에 따라 "
        "미국에 처음 입국한 날부터 30일이 지난 시점 또는 청원 "
        "승인 당시 미국에 체류하던 근로자가 해당 고용주를 위해 "
        "취업할 자격을 얻은 날부터 60일이 지난 시점에 적용될 수 "
        "있다. 실제 적용 조건과 예외는 별도 검토가 필요하다."
    ),
    128: (
        "H-1B 고용주는 승인된 고용기간 동안 건강·생명·장애보험, "
        "퇴직·저축제도, 상여금, 스톡옵션 등을 포함한 복리후생과 "
        "그 이용 자격을 미국인 근로자에게 적용하는 것과 동일한 "
        "기준으로 제공해야 한다."
    ),
    129: (
        "노동부 장관이 통지 및 심리 기회를 제공한 후 H-1B "
        "고용주의 법정 임금 미지급을 인정하는 경우, 관련 법률에 "
        "따라 필요한 체불임금 지급을 명령해야 한다."
    ),
}

LEGAL_HOLD = {
    123: "수수료 전가 금지의 적용 대상인 법정 수수료 범위 확인 필요",
}

CONTEXT_HOLD = {
    130: "제3자 고용 관련 조항의 앞뒤 문맥 확인 필요",
}

PREVIOUS_GROUPS = [
    "policy_records",
    "supplemental_stay_evidence",
    "additional_core_policy_drafts",
    "additional_supporting_evidence",
    "additional_legal_review_evidence",
    "additional_registration_policy_drafts",
    "registration_supporting_evidence",
    "registration_operational_information",
    "registration_context_review",
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"출력 파일이 이미 존재합니다: {OUTPUT}")

    original = load(INPUT)
    candidates = load(SOURCE)["candidate_records"]

    if len(candidates) != 1537:
        raise ValueError("원문 후보 수 불일치")

    for group in PREVIOUS_GROUPS:
        if group not in original:
            raise ValueError(f"기존 검토 그룹 누락: {group}")

    used = {
        record["source_candidate_id"]
        for group in PREVIOUS_GROUPS
        for record in original[group]
    }

    if len(used) != 146:
        raise ValueError(f"기존 검토 수 불일치: {len(used)}")

    index = {c["candidate_id"]: c for c in candidates}

    if len(index) != len(candidates):
        raise ValueError("원문 ID 중복")

    source_urls = {
        (r["source_id"], r["source_sha256"]): r["source_url"]
        for r in original["policy_records"]
    }

    new_policies = []
    legal_review = []
    context_review = []

    targets = set(POLICIES) | set(LEGAL_HOLD) | set(CONTEXT_HOLD)

    if len(targets) != 7:
        raise ValueError("대상 문단 수 불일치")

    for number in sorted(targets):
        cid = f"H1B-CAND-V2-{number:05d}"

        if cid in used:
            raise ValueError(f"기존 검토와 중복: {cid}")

        candidate = index[cid]

        if candidate["source_id"] != "DOL-H1B-LCA-LAW":
            raise ValueError(f"출처 불일치: {cid}")

        excerpt = candidate["evidence_excerpt"]

        if digest(excerpt) != candidate["excerpt_sha256"]:
            raise ValueError(f"Evidence 해시 불일치: {cid}")

        source_key = (
            candidate["source_id"],
            candidate["source_sha256"],
        )

        base = {
            "source_candidate_id": cid,
            "source_id": candidate["source_id"],
            "source_url": source_urls.get(source_key),
            "source_sha256": candidate["source_sha256"],
            "source_paragraph_index": candidate["source_paragraph_index"],
            "evidence_excerpt": excerpt,
            "excerpt_sha256": candidate["excerpt_sha256"],
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        if number in POLICIES:
            new_policies.append({
                **base,
                "policy_id": f"US-WK-01-POL-EMP-{len(new_policies)+1:03d}",
                "program_id": "US-WK-01",
                "policy_statement_ko": POLICIES[number],
                "applicability": "H-1B 고용주 및 근로자",
                "requirements": [],
                "exceptions": [],
                "effective_date": None,
                "expiration_date": None,
                "legal_status": "unverified",
                "human_review_decision": "policy_draft_candidate",
                "review_rationale_ko": (
                    "DOL 법률 원문 기반 정책 초안. 적용 예외와 "
                    "현행 법적 효력에 대한 추가 검증 필요."
                ),
            })

        elif number in LEGAL_HOLD:
            legal_review.append({
                **base,
                "human_review_decision": "legal_scope_review",
                "review_reason_ko": LEGAL_HOLD[number],
            })

        else:
            context_review.append({
                **base,
                "human_review_decision": "context_required",
                "review_reason_ko": CONTEXT_HOLD[number],
            })

    result = deepcopy(original)
    result["additional_employer_policy_drafts"] = new_policies
    result["employer_legal_scope_review"] = legal_review
    result["employer_context_review"] = context_review

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    saved = load(OUTPUT)

    if any(saved[g] != original[g] for g in PREVIOUS_GROUPS):
        raise ValueError("기존 검토 기록 변경")

    if len(saved["additional_employer_policy_drafts"]) != 5:
        raise ValueError("신규 정책 건수 오류")

    if len(saved["employer_legal_scope_review"]) != 1:
        raise ValueError("법적 범위 검토 건수 오류")

    if len(saved["employer_context_review"]) != 1:
        raise ValueError("문맥 검토 건수 오류")

    all_new = (
        saved["additional_employer_policy_drafts"]
        + saved["employer_legal_scope_review"]
        + saved["employer_context_review"]
    )

    if len({r["source_candidate_id"] for r in all_new}) != 8:
        raise ValueError("추가 후보 중복")

    for record in all_new:
        if digest(record["evidence_excerpt"]) != record["excerpt_sha256"]:
            raise ValueError("저장 후 해시 검증 실패")
        if (
            record["review_status"] != "needs_review"
            or record["semantic_support_verified"]
            or record["legal_effect_verified"]
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

    print("\n=== H-1B EMPLOYER OBLIGATIONS VALIDATION ===")
    print("PREVIOUSLY CLASSIFIED:", len(used))
    print("NEW POLICY DRAFTS:", len(new_policies))
    print("LEGAL SCOPE REVIEW:", len(legal_review))
    print("CONTEXT REVIEW:", len(context_review))
    print("TOTAL CLASSIFIED:", len(used) + len(all_new))
    print("REMAINING:", 1537 - len(used) - len(all_new))
    print("ORIGINAL DATA PRESERVED: PASS")
    print("EVIDENCE HASHES: PASS")
    print("REVIEW STATUS: needs_review")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
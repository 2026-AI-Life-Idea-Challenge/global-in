
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_consolidation_2026_conditions_draft.json"
CANDIDATES = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_core_supplemented_draft.json"

# Key: original V2 candidate suffix
# Value: Korean draft policy statement
NEW_POLICIES = {
    19: "H-1B 전문직 업무에 필요한 미국 학사 이상의 학위를 인가된 대학에서 취득한 경우, 근로자 자격요건 충족의 한 경로가 될 수 있다.",
    21: "해당 주에서 전문직 업무를 전면적으로 수행할 수 있는 제한 없는 면허·등록·자격증을 보유한 경우, 근로자 자격요건 충족의 한 경로가 될 수 있다.",
    22: "관련 분야의 교육·전문훈련·점진적으로 책임이 증가하는 경력이 미국 학사 이상 학위와 동등하고, 해당 분야의 전문성이 인정되는 경우 자격요건 충족의 한 경로가 될 수 있다.",
    23: "H-1B 전문직 청원을 제출할 때에는 노동부가 인증한 노동조건신청서(LCA)의 증빙을 Form I-129와 함께 제출해야 한다.",
    40: "H-1B 고용주는 유사 업무에 종사하는 다른 근로자에게 불리한 영향을 미치지 않는 근무조건을 제공해야 한다.",
    41: "H-1B 노동조건신청서 제출 시 해당 근무지에 파업 또는 직장폐쇄가 없어야 한다.",
    42: "H-1B 고용주는 노동조건신청서 제출 사실을 노동조합 대표에게 통지하거나 근무지에 게시해야 한다.",
    51: "H-1B 고용주가 승인된 체류기간 종료 전에 근로자를 해고하는 경우 합리적인 귀국 교통비를 부담해야 할 수 있으며, 자발적 퇴사의 경우에는 해당 의무가 적용되지 않는다.",
    53: "H-1B 이직 자격요건을 충족하는 근로자는 새 고용주가 적법하고 명백히 근거 없는 청원이 아닌 Form I-129를 제출한 시점과 청원서상 요청 시작일 중 늦은 시점부터 근무할 수 있다. 무허가 취업 이력, 청원 제출 기한, 승인·거절 결과에 따른 제한을 별도로 확인해야 한다.",
    58: "H-1B 근로자가 해고·퇴사 등으로 고용을 종료한 경우, 일정한 요건에 따라 최대 연속 60일 또는 기존 승인 유효기간 종료일까지 중 짧은 기간에 새 고용, 신분 변경 또는 출국을 준비할 수 있다.",
    59: "Cap 면제 고용에서 Cap 대상 고용으로 전환하면 새 고용주의 청원이 H-1B 연간 상한 및 전자등록 절차의 적용을 받을 수 있다.",
    61: "Cap 면제 고용을 유지하는 H-1B 근로자는 일정한 조건에서 Cap 대상 고용주와 동시 취업할 수 있으며, 새 고용주의 적법한 청원 제출 및 요청 시작일 등에 따라 근무 개시 시점이 결정된다.",
}

SUPPORT_LINKS = {
    35: 23,
    54: 53,
    55: 53,
    56: 53,
    57: 53,
}

LEGAL_HOLD = {36}


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def cid(number):
    return f"H1B-CAND-V2-{number:05d}"


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"덮어쓰기 금지: {OUTPUT}")

    original = load(INPUT)
    source = load(CANDIDATES)
    all_candidates = source["candidate_records"]

    if len(all_candidates) != 1537:
        raise ValueError("원문 후보 수 불일치")

    existing = original["policy_records"]
    stay = original["supplemental_stay_policy_drafts"]

    if len(existing) != 111 or len(stay) != 2:
        raise ValueError("기존 정책 수 불일치")

    index = {r["candidate_id"]: r for r in all_candidates}

    requested = (
        set(NEW_POLICIES)
        | set(SUPPORT_LINKS)
        | LEGAL_HOLD
    )

    if len(requested) != 18:
        raise ValueError("검토 후보 수 불일치")

    already_used = {
        r["source_candidate_id"] for r in existing
    } | {
        r["source_candidate_id"]
        for r in original["supplemental_stay_evidence"]
    }

    new_records = []
    supporting = []
    held = []

    for number in sorted(requested):
        candidate_id = cid(number)

        if candidate_id not in index:
            raise ValueError(f"후보 ID 누락: {candidate_id}")

        if candidate_id in already_used:
            raise ValueError(f"기존 검토 중복: {candidate_id}")

        candidate = index[candidate_id]

        if candidate["source_id"] != "USCIS-H1B-OVERVIEW":
            raise ValueError(f"출처 오류: {candidate_id}")

        evidence = candidate["evidence_excerpt"]

        if digest(evidence) != candidate["excerpt_sha256"]:
            raise ValueError(f"Evidence 해시 오류: {candidate_id}")

        base = {
            "source_candidate_id": candidate_id,
            "source_id": candidate["source_id"],
            "source_url": next(
                r["source_url"]
                for r in existing
                if r["source_id"] == candidate["source_id"]
                and r["source_sha256"] == candidate["source_sha256"]
            ),
            "source_sha256": candidate["source_sha256"],
            "source_paragraph_index": (
                candidate["source_paragraph_index"]
            ),
            "evidence_excerpt": evidence,
            "excerpt_sha256": candidate["excerpt_sha256"],
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        if number in NEW_POLICIES:
            new_records.append({
                **base,
                "policy_id": (
                    f"US-WK-01-POL-ADD-{len(new_records)+1:03d}"
                ),
                "program_id": "US-WK-01",
                "policy_statement_ko": NEW_POLICIES[number],
                "applicability": None,
                "requirements": [],
                "exceptions": [],
                "effective_date": None,
                "expiration_date": None,
                "legal_status": "unverified",
                "human_review_decision": "policy_draft_candidate",
                "review_rationale_ko": (
                    "미검토 USCIS 원문에서 추가한 초안. "
                    "적용 조건·예외·현행성 검증 필요."
                ),
            })

        elif number in SUPPORT_LINKS:
            supporting.append({
                **base,
                "primary_candidate_id": cid(SUPPORT_LINKS[number]),
                "link_status": "proposed",
                "human_review_decision": "duplicate_support",
            })

        else:
            held.append({
                **base,
                "human_review_decision": "legal_effect_review",
                "review_reason_ko": (
                    "I-129 절차와 10만 달러 납부 지침이 "
                    "같은 문단에 혼합됨. 법적 효력 검토 전 "
                    "사용 금지."
                ),
                "legal_status": "unverified",
            })

    result = deepcopy(original)

    result["additional_core_policy_drafts"] = new_records
    result["additional_supporting_evidence"] = supporting
    result["additional_legal_review_evidence"] = held

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    saved = load(OUTPUT)

    if (
        saved["policy_records"] != existing
        or saved["supplemental_stay_policy_drafts"] != stay
        or saved["duplicate_evidence_links"]
        != original["duplicate_evidence_links"]
        or saved["legal_effect_review_policy_ids"]
        != original["legal_effect_review_policy_ids"]
    ):
        raise ValueError("기존 검토 데이터 변경")

    counts = [
        len(saved["additional_core_policy_drafts"]),
        len(saved["additional_supporting_evidence"]),
        len(saved["additional_legal_review_evidence"]),
    ]

    if counts != [12, 5, 1]:
        raise ValueError("추가 데이터 수 불일치")

    all_added = (
        saved["additional_core_policy_drafts"]
        + saved["additional_supporting_evidence"]
        + saved["additional_legal_review_evidence"]
    )

    if len({
        r["source_candidate_id"] for r in all_added
    }) != 18:
        raise ValueError("추가 Evidence 중복")

    if any(
        digest(r["evidence_excerpt"]) != r["excerpt_sha256"]
        or r["semantic_support_verified"]
        or r["legal_effect_verified"]
        or r["review_status"] != "needs_review"
        for r in all_added
    ):
        raise ValueError("무결성 또는 안전 상태 오류")

    for key in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    ):
        if saved[key] is not False:
            raise ValueError(f"승인 상태 오류: {key}")

    print("\n=== H-1B CORE POLICY SUPPLEMENT ===")
    print("ORIGINAL RECORDS:", len(existing))
    print("PREVIOUS STAY DRAFTS:", len(stay))
    print("NEW CORE POLICY DRAFTS:", counts[0])
    print("SUPPORTING EVIDENCE:", counts[1])
    print("ADDITIONAL LEGAL HOLD:", counts[2])
    print("TOTAL NEWLY REVIEWED:", sum(counts))
    print("PREVIOUS DUPLICATE LINKS:",
          len(saved["duplicate_evidence_links"]))
    print("PREVIOUS LEGAL REVIEW ITEMS:",
          len(saved["legal_effect_review_policy_ids"]))
    print("ORIGINAL DATA UNCHANGED: PASS")
    print("EVIDENCE HASHES: PASS")
    print("REVIEW STATUS: needs_review")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
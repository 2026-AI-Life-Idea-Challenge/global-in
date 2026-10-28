
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path("data/processed/usa/employment/h1b_specialty_occupation")

INPUT = BASE / "h1b_policy_consolidation_2026_agent_lca_draft.json"
SOURCE = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_cap_gap_draft.json"

POLICY_ID = "US-WK-01-POL-CAPGAP-001"
DIRECT_ID = "H1B-CAND-V2-01442"
CONTEXT_ID = "H1B-CAND-V2-01411"


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_records(document):
    for group, value in document.items():
        if isinstance(value, list):
            for record in value:
                if isinstance(record, dict):
                    yield group, record


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"출력 파일이 이미 존재합니다: {OUTPUT}")

    original = load(INPUT)
    candidates = load(SOURCE)["candidate_records"]

    if len(candidates) != 1537:
        raise ValueError("전체 원문 수 불일치")

    index = {r["candidate_id"]: r for r in candidates}

    if len(index) != len(candidates):
        raise ValueError("원문 후보 ID 중복")

    existing = list(iter_records(original))

    used = {
        r["source_candidate_id"]
        for _, r in existing
        if str(r.get("source_candidate_id", "")).startswith(
            "H1B-CAND-V2-"
        )
    }

    if len(used) != 185:
        raise ValueError(f"기존 분류 원문 수 불일치: {len(used)}")

    if DIRECT_ID not in used or CONTEXT_ID not in used:
        raise ValueError("기존 Cap-gap 근거 원문 누락")

    policy_ids = {
        r["policy_id"]
        for _, r in existing
        if r.get("policy_id")
    }

    if POLICY_ID in policy_ids:
        raise ValueError("정책 ID 중복")

    expected_links = {
        "US-WK-01-POL-0095": CONTEXT_ID,
        "US-WK-01-POL-0097": DIRECT_ID,
    }

    for policy_id, source_id in expected_links.items():
        matches = [
            r for _, r in existing
            if r.get("policy_id") == policy_id
            and r.get("source_candidate_id") == source_id
            and r.get("human_review_decision") == "context_required"
        ]
        if len(matches) != 1:
            raise ValueError(f"기존 연결 기록 확인 실패: {policy_id}")

    direct = index[DIRECT_ID]
    context = index[CONTEXT_ID]

    for r in (direct, context):
        if r["source_id"] != "DHS-H1B-MODERNIZATION-2024":
            raise ValueError("원문 출처 불일치")
        if sha256(r["evidence_excerpt"]) != r["excerpt_sha256"]:
            raise ValueError(f"원문 해시 불일치: {r['candidate_id']}")

    direct_text = direct["evidence_excerpt"]

    required_phrases = [
        "The duration of status",
        "automatically extended until April 1",
        "Has been timely filed",
        "Is nonfrivolous",
    ]

    for phrase in required_phrases:
        if phrase not in direct_text:
            raise ValueError(f"필수 Cap-gap 근거 누락: {phrase}")

    prior = next(
        r for _, r in existing
        if r.get("policy_id") == "US-WK-01-POL-0097"
        and r.get("source_candidate_id") == DIRECT_ID
    )

    if (
        prior.get("source_sha256") != direct["source_sha256"]
        or prior.get("excerpt_sha256") != direct["excerpt_sha256"]
        or not prior.get("source_url")
    ):
        raise ValueError("기존 직접 Evidence 연결 오류")

    new_policy = {
        "policy_id": POLICY_ID,
        "program_id": "US-WK-01",
        "policy_statement_ko": (
            "2024년 H-1B 현대화 최종 규정에 따르면, "
            "일정한 F-1 학생이 H-1B Cap 대상 청원을 통해 "
            "신분 변경을 요청하고 그 청원이 기한 내 적법하게 "
            "제출되었으며, 해당 회계연도 내 H-1B 고용 "
            "시작일을 요청하고 명백히 근거 없는 청원이 "
            "아닌 경우, F-1 체류기간 및 해당되는 기존 "
            "취업허가는 해당 회계연도 4월 1일 또는 "
            "승인된 H-1B 청원의 유효 시작일 중 "
            "이른 날까지 자동 연장된다."
        ),
        "applicability": (
            "규정상 요건을 충족하는 F-1 학생의 "
            "H-1B Cap 대상 신분 변경 청원"
        ),
        "regulatory_section": "8 CFR 214.2(f)(5)(vi)(A)",
        "requirements": [],
        "exceptions": [],
        "effective_date": None,
        "expiration_date": None,
        "legal_status": "unverified",
        "human_review_decision": "policy_draft_candidate",
        "review_status": "needs_review",
        "semantic_support_verified": False,
        "legal_effect_verified": False,
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "source_candidate_id": DIRECT_ID,
        "source_id": direct["source_id"],
        "source_url": prior["source_url"],
        "source_sha256": direct["source_sha256"],
        "source_paragraph_index": direct["source_paragraph_index"],
        "evidence_excerpt": direct_text,
        "excerpt_sha256": direct["excerpt_sha256"],
        "evidence_reuse": True,
        "existing_evidence_policy_id": "US-WK-01-POL-0097",
        "context_evidence_ids": [CONTEXT_ID],
        "related_existing_policy_ids": [
            "US-WK-01-POL-0092",
            "US-WK-01-POL-0095",
        ],
        "review_rationale_ko": (
            "기존 01442 규정 본문을 재사용한 Cap-gap 초안. "
            "2026년 현재 법적 효력, 청원 상태별 종료 조건, "
            "취업허가 적용 대상 및 관련 예외 검증 필요. "
            "실직 후 60일 체류 유예기간과 구분해야 한다."
        ),
    }

    result = deepcopy(original)
    group = "additional_cap_gap_policy_drafts"

    if group in result:
        raise ValueError("정책 그룹 중복")

    result[group] = [new_policy]

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    safety_keys = {
        "review_status",
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    }

    for key, value in original.items():
        if key not in safety_keys and result[key] != value:
            raise ValueError(f"기존 데이터 변경: {key}")

    for key in safety_keys - {"review_status"}:
        if result[key] is not False:
            raise ValueError(f"승인 차단 오류: {key}")

    new_used = {
        r["source_candidate_id"]
        for _, r in iter_records(result)
        if str(r.get("source_candidate_id", "")).startswith(
            "H1B-CAND-V2-"
        )
    }

    if new_used != used:
        raise ValueError("기존 분류 원문 집합 변경")

    if sha256(new_policy["evidence_excerpt"]) != (
        new_policy["excerpt_sha256"]
    ):
        raise ValueError("Evidence 무결성 오류")

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if load(OUTPUT) != result:
        raise ValueError("저장 후 데이터 불일치")

    print("=== H-1B CAP-GAP VALIDATION ===")
    print("NEW POLICY DRAFTS: 1")
    print("DIRECT EVIDENCE REUSED:", DIRECT_ID)
    print("CONTEXT EVIDENCE LINKED:", CONTEXT_ID)
    print("UNIQUE CLASSIFIED:", len(new_used))
    print("REMAINING:", len(candidates) - len(new_used))
    print("PREVIOUS DATA PRESERVED: PASS")
    print("EVIDENCE SHA-256: PASS")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
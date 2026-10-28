
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path("data/processed/usa/employment/h1b_specialty_occupation")

INPUT = BASE / "h1b_policy_consolidation_2026_weighted_details_draft.json"
SOURCE = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_deference_draft.json"

NEW_POLICY_ID = "US-WK-01-POL-DEF-001"

# 기존에 분류한 규정 본문: 다시 분류하지 않고 참조만 수행
EXISTING_DIRECT_EVIDENCE = "H1B-CAND-V2-01440"
EXISTING_DIRECT_POLICY = "US-WK-01-POL-0096"

SUPPORT = {
    1206: (
        "US-WK-01-POL-0097",
        "근무지 변경 시 수정·신규 청원이 필요한 기존 기준의 명문화",
    ),
    1221: (
        NEW_POLICY_ID,
        "근무지역 변경과 중요한 변경의 관계 및 일률적 적용 금지",
    ),
    1222: (
        NEW_POLICY_ID,
        "중요한 사실·법률 오류, 변경 및 새로운 정보의 구체적 사례",
    ),
    1224: (
        NEW_POLICY_ID,
        "동일 당사자 판단 및 기존 승인과 달리 결정할 때의 설명 절차",
    ),
    1279: (
        "US-WK-01-POL-MOD-001",
        "계약서 요청 권한과 일률적인 계약서 제출 의무의 구분",
    ),
}

CONTEXT = {
    1214: (
        "Deference에 관한 이해관계자 의견을 주로 포함하므로 "
        "DHS의 확정 규정과 구분하여 보존"
    ),
    1443: (
        "단기 근무, Agent 청원, LCA 및 현장실사 관련 "
        "여러 규정이 연결된 복합 Evidence. "
        "01442·01444와 문장 경계 및 적용 범위 검토 필요"
    ),
}

TARGETS = {1216} | set(SUPPORT) | set(CONTEXT)


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidate_id(number):
    return f"H1B-CAND-V2-{number:05d}"


def hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def records(document):
    for group, value in document.items():
        if isinstance(value, list):
            for record in value:
                if isinstance(record, dict):
                    yield group, record


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"출력 파일이 이미 존재합니다: {OUTPUT}")

    original = load(INPUT)
    source_data = load(SOURCE)
    candidates = source_data["candidate_records"]

    if len(candidates) != 1537:
        raise ValueError("전체 후보 수 불일치")

    index = {r["candidate_id"]: r for r in candidates}

    if len(index) != len(candidates):
        raise ValueError("후보 ID 중복")

    if len(TARGETS) != 8:
        raise ValueError("이번 분류 대상은 8건이어야 합니다")

    existing = list(records(original))

    used = {
        r["source_candidate_id"]
        for _, r in existing
        if str(r.get("source_candidate_id", "")).startswith(
            "H1B-CAND-V2-"
        )
    }

    if len(used) != 177:
        raise ValueError(f"기존 분류 수 불일치: {len(used)}")

    if any(candidate_id(n) in used for n in TARGETS):
        raise ValueError("신규 후보가 기존 분류와 중복됩니다")

    policy_ids = {
        r["policy_id"]
        for _, r in existing
        if r.get("policy_id")
    }

    if NEW_POLICY_ID in policy_ids:
        raise ValueError("Deference 정책 ID 중복")

    required_existing_policies = {
        EXISTING_DIRECT_POLICY,
        "US-WK-01-POL-0097",
        "US-WK-01-POL-MOD-001",
    }

    if not required_existing_policies.issubset(policy_ids):
        raise ValueError("기존 연결 대상 정책이 존재하지 않습니다")

    direct_records = [
        r for _, r in existing
        if r.get("source_candidate_id") == EXISTING_DIRECT_EVIDENCE
        and r.get("policy_id") == EXISTING_DIRECT_POLICY
    ]

    if len(direct_records) != 1:
        raise ValueError("기존 Deference 규정 원문 연결 확인 실패")

    direct_candidate = index[EXISTING_DIRECT_EVIDENCE]

    if (
        hash_text(direct_candidate["evidence_excerpt"])
        != direct_candidate["excerpt_sha256"]
    ):
        raise ValueError("기존 규정 본문 해시 불일치")

    if "(5) Deference to prior USCIS determinations" not in (
        direct_candidate["evidence_excerpt"]
    ):
        raise ValueError("기존 규정 본문에서 Deference 조항을 찾지 못함")

    source_urls = {
        (r["source_id"], r["source_sha256"]): r["source_url"]
        for _, r in existing
        if (
            r.get("source_id")
            and r.get("source_sha256")
            and r.get("source_url")
        )
    }

    policy_drafts = []
    support_records = []
    context_records = []

    for n in sorted(TARGETS):
        source = index[candidate_id(n)]
        excerpt = source["evidence_excerpt"]

        if source["source_id"] != "DHS-H1B-MODERNIZATION-2024":
            raise ValueError(f"출처 불일치: {candidate_id(n)}")

        if hash_text(excerpt) != source["excerpt_sha256"]:
            raise ValueError(f"원문 해시 불일치: {candidate_id(n)}")

        source_key = (
            source["source_id"],
            source["source_sha256"],
        )

        if source_key not in source_urls:
            raise ValueError(f"출처 URL 연결 실패: {candidate_id(n)}")

        evidence = {
            "source_candidate_id": candidate_id(n),
            "source_id": source["source_id"],
            "source_url": source_urls[source_key],
            "source_sha256": source["source_sha256"],
            "source_paragraph_index":
                source["source_paragraph_index"],
            "evidence_excerpt": excerpt,
            "excerpt_sha256": source["excerpt_sha256"],
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        if n == 1216:
            policy_drafts.append({
                **evidence,
                "policy_id": NEW_POLICY_ID,
                "program_id": "US-WK-01",
                "policy_statement_ko": (
                    "2024년 최종 규정의 8 CFR 214.1(c)(5)에 따르면, "
                    "USCIS는 동일 당사자와 동일한 기초 사실에 관한 "
                    "Form I-129 심사에서 원칙적으로 이전 자격 판단을 "
                    "존중한다. 다만 이전 승인에 중요한 오류가 있거나 "
                    "상황·자격요건에 중요한 변경이 있거나 "
                    "자격에 부정적인 영향을 주는 새로운 중대한 "
                    "정보가 있는 경우에는 그러하지 않을 수 있다. "
                    "청원인의 입증 책임은 계속 유지된다."
                ),
                "applicability": (
                    "동일 당사자·동일 기초 사실에 관한 "
                    "Form I-129 신청"
                ),
                "requirements": [],
                "exceptions": [],
                "effective_date": None,
                "expiration_date": None,
                "legal_status": "unverified",
                "human_review_decision": "policy_draft_candidate",
                "direct_regulatory_evidence_id":
                    EXISTING_DIRECT_EVIDENCE,
                "existing_evidence_policy_id":
                    EXISTING_DIRECT_POLICY,
                "direct_regulatory_reference":
                    "8 CFR 214.1(c)(5), 2024 final rule",
                "review_rationale_ko": (
                    "기존 01440의 직접 규정 조문과 01216의 "
                    "DHS 공식 설명을 연결한 초안. "
                    "2026년 이후 개정·제안 규칙의 법적 효력과 "
                    "현재 적용 상태에 대한 확인이 필요하다."
                ),
            })

        elif n in SUPPORT:
            target_policy, reason = SUPPORT[n]

            support_records.append({
                **evidence,
                "supports": target_policy,
                "support_reason_ko": reason,
                "link_status": "proposed",
                "human_review_decision": "supporting_evidence",
            })

        else:
            context_records.append({
                **evidence,
                "human_review_decision": "context_required",
                "review_reason_ko": CONTEXT[n],
            })

    if (
        len(policy_drafts) != 1
        or len(support_records) != 5
        or len(context_records) != 2
    ):
        raise ValueError("분류별 건수 불일치")

    if any(
        r["supports"] not in policy_ids | {NEW_POLICY_ID}
        for r in support_records
    ):
        raise ValueError("보조 근거 연결 정책 ID 오류")

    new_records = (
        policy_drafts + support_records + context_records
    )

    if len({
        r["source_candidate_id"]
        for r in new_records
    }) != 8:
        raise ValueError("신규 Evidence ID 중복")

    for record in new_records:
        if hash_text(record["evidence_excerpt"]) != (
            record["excerpt_sha256"]
        ):
            raise ValueError("신규 Evidence 해시 검증 실패")

        if (
            record["review_status"] != "needs_review"
            or record["semantic_support_verified"] is not False
            or record["legal_effect_verified"] is not False
        ):
            raise ValueError("미승인 상태 검증 실패")

    result = deepcopy(original)

    new_groups = {
        "additional_deference_policy_drafts": policy_drafts,
        "modernization_deference_supporting_evidence":
            support_records,
        "modernization_deference_context_review":
            context_records,
    }

    for key in new_groups:
        if key in result:
            raise ValueError(f"기존 필드와 중복: {key}")

    result.update(new_groups)

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    safety_fields = {
        "review_status",
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    }

    for key, value in original.items():
        if key not in safety_fields and result[key] != value:
            raise ValueError(f"기존 데이터 변경: {key}")

    for key in safety_fields - {"review_status"}:
        if result[key] is not False:
            raise ValueError(f"승인 차단 실패: {key}")

    if len(used | {
        r["source_candidate_id"] for r in new_records
    }) != 185:
        raise ValueError("누적 분류 건수 불일치")

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if load(OUTPUT) != result:
        raise ValueError("저장 후 데이터 검증 실패")

    print("=== H-1B MODERNIZATION DEFERENCE VALIDATION ===")
    print("PREVIOUSLY CLASSIFIED:", len(used))
    print("NEW POLICY DRAFTS:", len(policy_drafts))
    print("SUPPORTING EVIDENCE:", len(support_records))
    print("CONTEXT REVIEW:", len(context_records))
    print("EXISTING REGULATORY EVIDENCE REUSED: PASS")
    print("TOTAL CLASSIFIED:", len(used) + len(new_records))
    print("REMAINING:", len(candidates) - len(used) - len(new_records))
    print("PREVIOUS DATA PRESERVED: PASS")
    print("NEW EVIDENCE HASHES: PASS")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
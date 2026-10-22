
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_consolidation_2026_deference_draft.json"
SOURCE = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_agent_lca_draft.json"

EVIDENCE_ID = "H1B-CAND-V2-01443"

POLICIES = [
    {
        "policy_id": "US-WK-01-POL-AGL-001",
        "policy_statement_ko": (
            "미국 내 Agent는 법령에 규정된 특정 고용·대리 관계에서 "
            "H 비이민 청원을 제출할 수 있다. Agent는 고용조건을 "
            "설명하고 필요한 자료를 제출해야 하며, 실제 고용주 "
            "역할을 수행하는 경우 계약을 통해 임금과 기타 "
            "고용조건을 보장해야 한다. H-1B에 대한 구체적 "
            "적용 범위는 추가 검토가 필요하다."
        ),
        "applicability": (
            "H 비이민 청원의 Agent 규정; "
            "H-1B 적용 범위 검증 필요"
        ),
        "regulatory_section": "8 CFR 214.2(h)(2)(i)(F)",
        "required_excerpt": "(F) Agents as petitioners.",
        "review_note": (
            "일반 H 청원 Agent 규정과 H-1B 특유의 요건을 "
            "구분하고, 실제 고용주 역할 및 외국 고용주 "
            "관련 책임의 적용 범위를 검증해야 한다."
        ),
    },
    {
        "policy_id": "US-WK-01-POL-AGL-002",
        "policy_statement_ko": (
            "노동부 장관이 법률에 열거된 특정 LCA 의무 위반 "
            "또는 중요한 사실의 허위 진술을 USCIS에 통지하면, "
            "USCIS는 해당 통지를 받은 날부터 최소 1년 동안 "
            "해당 고용주와 관련하여 INA 204 또는 214(c)에 "
            "따라 제출된 청원을 승인하지 않는다는 규정이 있다. "
            "위반 유형 및 제재의 현행 적용 여부는 검증이 필요하다."
        ),
        "applicability": (
            "법률에 명시된 LCA 위반·허위 진술과 "
            "노동부 통지가 발생한 고용주"
        ),
        "regulatory_section": "8 CFR 214.2(h)(4)(i)(B)(1)(v)",
        "required_excerpt": (
            "USCIS will not approve petitions filed"
        ),
        "review_note": (
            "모든 LCA 위반에 자동 적용되는 제재로 일반화하지 "
            "않아야 한다. 위반 조항, 노동부의 통지, "
            "최소 1년 기산점 및 적용 청원 유형 검증 필요."
        ),
    },
    {
        "policy_id": "US-WK-01-POL-AGL-003",
        "policy_statement_ko": (
            "고용주의 LCA가 노동부에 의해 정지되거나 "
            "무효화된 경우에도, 고용주가 이미 고용 중인 "
            "근로자의 허가된 체류기간 동안 LCA 조건을 "
            "계속 준수하겠다고 노동부에 인증했다면, "
            "해당 규정은 기존 승인 청원을 정지하거나 "
            "취소하지 않도록 정하고 있다."
        ),
        "applicability": (
            "LCA 정지·무효화 이후 기존 승인 청원 및 "
            "고용주의 계속 준수 인증"
        ),
        "regulatory_section": "8 CFR 214.2(h)(4)(i)(B)(1)(vi)",
        "required_excerpt": (
            "USCIS will not suspend or revoke"
        ),
        "review_note": (
            "새 청원의 승인 가능성과 이미 승인된 청원의 "
            "정지·취소 여부를 구분해야 한다. "
            "고용주의 인증 조건 및 현행 효력 검증 필요."
        ),
    },
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_records(data):
    for group, value in data.items():
        if isinstance(value, list):
            for record in value:
                if isinstance(record, dict):
                    yield group, record


def main():
    if OUTPUT.exists():
        raise FileExistsError(
            f"기존 결과 파일 덮어쓰기 금지: {OUTPUT}"
        )

    original = load(INPUT)
    candidates = load(SOURCE)["candidate_records"]

    if len(candidates) != 1537:
        raise ValueError("전체 원문 후보 수 불일치")

    index = {
        record["candidate_id"]: record
        for record in candidates
    }

    if len(index) != len(candidates):
        raise ValueError("원문 후보 ID 중복")

    existing = list(iter_records(original))

    classified_ids = {
        record["source_candidate_id"]
        for _, record in existing
        if str(
            record.get("source_candidate_id", "")
        ).startswith("H1B-CAND-V2-")
    }

    if len(classified_ids) != 185:
        raise ValueError(
            f"기존 분류 원문 건수 불일치: {len(classified_ids)}"
        )

    if EVIDENCE_ID not in classified_ids:
        raise ValueError("기존 Evidence 분류를 찾을 수 없음")

    context_matches = [
        record
        for group, record in existing
        if group == "modernization_deference_context_review"
        and record.get("source_candidate_id") == EVIDENCE_ID
    ]

    if len(context_matches) != 1:
        raise ValueError(
            "기존 01443 문맥 검토 기록 확인 실패"
        )

    existing_policy_ids = {
        record["policy_id"]
        for _, record in existing
        if record.get("policy_id")
    }

    new_policy_ids = [
        item["policy_id"] for item in POLICIES
    ]

    if len(set(new_policy_ids)) != 3:
        raise ValueError("신규 정책 ID 중복")

    if set(new_policy_ids) & existing_policy_ids:
        raise ValueError("기존 정책 ID와 중복")

    source = index[EVIDENCE_ID]
    excerpt = source["evidence_excerpt"]

    if source["source_id"] != "DHS-H1B-MODERNIZATION-2024":
        raise ValueError("원문 출처 불일치")

    if sha256(excerpt) != source["excerpt_sha256"]:
        raise ValueError("원문 SHA-256 불일치")

    if any(
        item["required_excerpt"] not in excerpt
        for item in POLICIES
    ):
        raise ValueError("필수 규정 문구 확인 실패")

    prior = context_matches[0]

    if (
        prior["source_sha256"] != source["source_sha256"]
        or prior["excerpt_sha256"] != source["excerpt_sha256"]
        or prior["evidence_excerpt"] != excerpt
    ):
        raise ValueError(
            "기존 Evidence와 신규 원문 내용 불일치"
        )

    if (
        prior.get("review_status") != "needs_review"
        or not prior.get("source_url")
    ):
        raise ValueError("기존 Evidence 상태·URL 확인 실패")

    draft_records = []

    for item in POLICIES:
        draft_records.append({
            "policy_id": item["policy_id"],
            "program_id": "US-WK-01",
            "policy_statement_ko": item["policy_statement_ko"],
            "applicability": item["applicability"],
            "regulatory_section": item["regulatory_section"],
            "requirements": [],
            "exceptions": [],
            "effective_date": None,
            "expiration_date": None,
            "legal_status": "unverified",
            "source_candidate_id": EVIDENCE_ID,
            "source_id": source["source_id"],
            "source_url": prior["source_url"],
            "source_sha256": source["source_sha256"],
            "source_paragraph_index":
                source["source_paragraph_index"],
            "evidence_excerpt": excerpt,
            "excerpt_sha256": source["excerpt_sha256"],
            "existing_evidence_group":
                "modernization_deference_context_review",
            "evidence_reuse": True,
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "human_review_decision":
                "policy_draft_candidate",
            "review_status": "needs_review",
            "review_rationale_ko": item["review_note"],
            "approved_for_user_answers": False,
            "approved_for_embedding": False,
            "automatic_eligibility_rules_enabled": False,
        })

    result = deepcopy(original)

    group = "additional_agent_lca_policy_drafts"

    if group in result:
        raise ValueError("신규 정책 그룹이 이미 존재함")

    result[group] = draft_records

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
            raise ValueError(
                f"기존 데이터 변경 감지: {key}"
            )

    for key in safety_keys - {"review_status"}:
        if result[key] is not False:
            raise ValueError(
                f"승인 차단 상태 오류: {key}"
            )

    if len(draft_records) != 3:
        raise ValueError("신규 정책 건수 불일치")

    for record in draft_records:
        if (
            sha256(record["evidence_excerpt"])
            != record["excerpt_sha256"]
        ):
            raise ValueError("정책 Evidence 해시 오류")

        if (
            record["review_status"] != "needs_review"
            or record["semantic_support_verified"] is not False
            or record["legal_effect_verified"] is not False
        ):
            raise ValueError("검토 상태 오류")

    new_classified_ids = {
        record["source_candidate_id"]
        for _, record in iter_records(result)
        if str(
            record.get("source_candidate_id", "")
        ).startswith("H1B-CAND-V2-")
    }

    if new_classified_ids != classified_ids:
        raise ValueError(
            "기존 분류 원문 집합이 변경됨"
        )

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )

    if load(OUTPUT) != result:
        raise ValueError("저장 후 JSON 검증 실패")

    print("=== H-1B AGENT / LCA VALIDATION ===")
    print("NEW POLICY DRAFTS:", len(draft_records))
    print("EXISTING EVIDENCE REUSED:", EVIDENCE_ID)
    print("UNIQUE CLASSIFIED:", len(new_classified_ids))
    print("REMAINING:", len(candidates) - len(new_classified_ids))
    print("PREVIOUS DATA PRESERVED: PASS")
    print("EVIDENCE SHA-256: PASS")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()

import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path("data/processed/usa/employment/h1b_specialty_occupation")

INPUT = BASE / "h1b_policy_consolidation_2026_worker_protection_draft.json"
SOURCE = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_weighted_details_draft.json"

POLICIES = {
    1041: {
        "policy_id": "US-WK-01-POL-WGT-001",
        "statement": (
            "H-1B cap 대상 청원은 법령상 유효하게 선정된 등록에 "
            "근거하여 제출해야 한다. 등록 대상 수혜자나 청원인을 "
            "임의로 대체할 수 없으며, 청원에는 등록 및 LCA와 "
            "일치하는 신원·직무·SOC 정보와 임금수준 관련 증빙이 "
            "필요하다. 일정한 신원 또는 근무지 변경은 USCIS의 "
            "재량에 따라 허용될 수 있다."
        ),
        "applicability": "전자등록을 사용하는 H-1B cap 청원",
    },
    741: {
        "policy_id": "US-WK-01-POL-WGT-002",
        "statement": (
            "수혜자가 여러 근무지에서 근무하거나 대리 청원인이 "
            "여러 직무를 제안하는 경우, 각 근무지·직무별로 "
            "제안 임금이 충족하는 OEWS 임금수준을 판단하고 "
            "그중 가장 낮은 해당 수준을 선정에 사용해야 한다. "
            "관련 산정 근거의 제출이 요구된다."
        ),
        "applicability": "복수 근무지 또는 복수 직무의 가중 선정",
    },
    1042: {
        "policy_id": "US-WK-01-POL-WGT-003",
        "statement": (
            "USCIS가 특정 회계연도의 H-1B 전자등록 절차를 "
            "중단한 경우에는 등록 대신 접수된 청원을 바탕으로 "
            "cap 대상 선정 절차를 수행한다. 무작위 선정이 "
            "필요하면 해당 청원의 OEWS 임금수준에 따라 "
            "I부터 IV까지 각각 1회부터 4회까지 가중하여 "
            "선정하며, 임금수준 산정 근거를 청원 제출일 "
            "기준으로 제출해야 한다."
        ),
        "applicability": "전자등록이 중단된 회계연도에 한정",
    },
}

SUPPORT = {
    723: {
        "policy_id": "US-WK-01-POL-WGT-001",
        "reason": "전자등록 제출일 기준 OEWS 임금자료 적용",
    },
    739: {
        "policy_id": "US-WK-01-POL-WGT-001",
        "reason": "등록 당시 선택한 임금수준의 산정 근거 제출",
    },
    759: {
        "policy_id": "US-WK-01-POL-WGT-001",
        "reason": "실제 채용 제안과 청원 제출 의사에 관한 등록 확약",
    },
    766: {
        "policy_id": "US-WK-01-POL-WGT-001",
        "reason": "등록·LCA·청원 정보 일치와 임금수준 조작 방지",
    },
}

CONTEXT = {
    727: (
        "전자등록의 가중 선정에 사용하는 OEWS 임금수준과 "
        "DOL LCA의 통상임금 산정에 사용하는 임금수준을 "
        "구분해야 한다. 관련 요건과 적용 범위의 "
        "추가 법적 검토가 필요하다."
    )
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidate_id(n):
    return f"H1B-CAND-V2-{n:05d}"


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_records(document):
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
        raise ValueError("전체 후보 건수가 1537건이 아닙니다.")

    candidate_index = {
        record["candidate_id"]: record
        for record in candidates
    }

    if len(candidate_index) != len(candidates):
        raise ValueError("원문 후보 ID가 중복됩니다.")

    used = {
        record["source_candidate_id"]
        for _, record in collect_records(original)
        if str(record.get("source_candidate_id", "")).startswith(
            "H1B-CAND-V2-"
        )
    }

    if len(used) != 169:
        raise ValueError(f"기존 분류 건수 불일치: {len(used)}")

    targets = set(POLICIES) | set(SUPPORT) | set(CONTEXT)

    if len(targets) != 8:
        raise ValueError("신규 분류 대상은 8건이어야 합니다.")

    if any(candidate_id(n) in used for n in targets):
        raise ValueError("기존에 분류한 원문과 중복됩니다.")

    existing_policy_ids = {
        record["policy_id"]
        for _, record in collect_records(original)
        if record.get("policy_id")
    }

    new_policy_ids = {
        item["policy_id"]
        for item in POLICIES.values()
    }

    if existing_policy_ids & new_policy_ids:
        raise ValueError("기존 정책 ID와 중복됩니다.")

    if len(new_policy_ids) != len(POLICIES):
        raise ValueError("신규 정책 ID가 중복됩니다.")

    source_urls = {
        (record["source_id"], record["source_sha256"]):
            record["source_url"]
        for _, record in collect_records(original)
        if (
            record.get("source_id")
            and record.get("source_sha256")
            and record.get("source_url")
        )
    }

    policy_drafts = []
    supporting_evidence = []
    context_review = []

    for n in sorted(targets):
        source = candidate_index[candidate_id(n)]
        excerpt = source["evidence_excerpt"]

        if source["source_id"] != "DHS-H1B-WEIGHTED-2025":
            raise ValueError(f"잘못된 공식 출처: {candidate_id(n)}")

        if sha256(excerpt) != source["excerpt_sha256"]:
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
            "source_paragraph_index": source[
                "source_paragraph_index"
            ],
            "evidence_excerpt": excerpt,
            "excerpt_sha256": source["excerpt_sha256"],
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        if n in POLICIES:
            item = POLICIES[n]

            policy_drafts.append({
                **evidence,
                "policy_id": item["policy_id"],
                "program_id": "US-WK-01",
                "policy_statement_ko": item["statement"],
                "applicability": item["applicability"],
                "requirements": [],
                "exceptions": [],
                "effective_date": None,
                "expiration_date": None,
                "legal_status": "unverified",
                "human_review_decision": "policy_draft_candidate",
                "review_rationale_ko": (
                    "DHS 가중 선정 규정 원문에 근거한 초안. "
                    "규정 본문·현행 효력·다른 정책과의 "
                    "의미적 중복 여부에 대한 검증이 필요하다."
                ),
            })

        elif n in SUPPORT:
            item = SUPPORT[n]

            if item["policy_id"] not in new_policy_ids:
                raise ValueError("보조 근거의 연결 대상 오류")

            supporting_evidence.append({
                **evidence,
                "supports": item["policy_id"],
                "support_reason_ko": item["reason"],
                "link_status": "proposed",
                "human_review_decision": "supporting_evidence",
            })

        else:
            context_review.append({
                **evidence,
                "human_review_decision": "context_required",
                "review_reason_ko": CONTEXT[n],
            })

    result = deepcopy(original)

    new_keys = {
        "additional_weighted_selection_policy_drafts":
            policy_drafts,
        "weighted_selection_supporting_evidence":
            supporting_evidence,
        "weighted_selection_context_review":
            context_review,
    }

    for key in new_keys:
        if key in result:
            raise ValueError(f"기존 필드와 중복됩니다: {key}")

    result.update(new_keys)

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
            raise ValueError(f"기존 데이터가 변경됐습니다: {key}")

    new_records = (
        policy_drafts + supporting_evidence + context_review
    )

    if (
        len(policy_drafts) != 3
        or len(supporting_evidence) != 4
        or len(context_review) != 1
    ):
        raise ValueError("신규 분류별 건수가 일치하지 않습니다.")

    if len({
        record["source_candidate_id"]
        for record in new_records
    }) != 8:
        raise ValueError("신규 Evidence ID 중복")

    for record in new_records:
        if sha256(record["evidence_excerpt"]) != record["excerpt_sha256"]:
            raise ValueError("Evidence 무결성 검사 실패")

        if (
            record["review_status"] != "needs_review"
            or record["semantic_support_verified"] is not False
            or record["legal_effect_verified"] is not False
        ):
            raise ValueError("검토 상태 오류")

    for key in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    ):
        if result[key] is not False:
            raise ValueError(f"승인 차단 실패: {key}")

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    saved = load(OUTPUT)

    if saved != result:
        raise ValueError("저장 후 JSON 검증 실패")

    print("=== H-1B WEIGHTED DETAILS VALIDATION ===")
    print("PREVIOUSLY CLASSIFIED:", len(used))
    print("NEW POLICY DRAFTS:", len(policy_drafts))
    print("SUPPORTING EVIDENCE:", len(supporting_evidence))
    print("CONTEXT REVIEW:", len(context_review))
    print("TOTAL CLASSIFIED:", len(used) + len(new_records))
    print(
        "REMAINING:",
        len(candidates) - len(used) - len(new_records),
    )
    print("PREVIOUS DATA PRESERVED: PASS")
    print("NEW EVIDENCE HASHES: PASS")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
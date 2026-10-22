
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path("data/processed/usa/employment/h1b_specialty_occupation")

INPUT = BASE / "h1b_policy_consolidation_2026_enforcement_draft.json"
SOURCE = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_worker_protection_draft.json"

POLICIES = {
    112: (
        "법률상 해당 의무의 적용 대상인 H-1B 고용주는 "
        "LCA가 뒷받침하는 비자 청원 제출일 전 90일부터 "
        "제출일 후 90일까지의 기간에 미국인 근로자를 "
        "법에서 금지하는 방식으로 대체해서는 안 된다. "
        "고용주 유형과 예외에 대한 추가 검증이 필요하다."
    ),
    120: (
        "H-1B LCA를 제출한 고용주는 관련 법령 위반을 "
        "합리적으로 의심하여 정보를 공개하거나 조사·절차에 "
        "협조한 근로자에게 협박, 블랙리스트, 해고 등 "
        "보복성 차별을 해서는 안 된다. 보호 대상에는 "
        "전직 근로자와 구직자도 포함된다."
    ),
    136: (
        "노동부 장관은 법률상 특정 조사를 개시하기 전에 "
        "원칙적으로 고용주에게 조사 예정 사실과 혐의에 "
        "대응할 수 있을 만큼 구체적인 내용을 통지해야 한다. "
        "다만 법 준수 확보를 방해할 수 있다고 판단되는 "
        "경우에는 규정상 통지 예외가 적용될 수 있다."
    ),
    137: (
        "법률상 특정 H-1B 고용주 조사는 최대 60일간 "
        "진행될 수 있다. 조사 결과 정해진 위반에 관한 "
        "합리적 근거가 확인되면 관계자 통지와 심리 기회를 "
        "제공하는 절차가 적용되며, 관련 규정은 후속 "
        "절차에 별도의 기한을 정한다."
    ),
}

SUPPORT = {
    133: {
        "supports": "US-WK-01-POL-ENF-002",
        "reason": "합리적 근거에 따른 조사 개시 요건 보강",
    },
    148: {
        "supports": "US-WK-01-POL-0020",
        "reason": "법정 통상임금 지급 기준의 보조 근거",
    },
}

HOLDS = {
    138: {
        "category": "exception_review",
        "reason": (
            "산업 표준에 따른 통상임금 산정 시 "
            "제재 면제의 적용 요건 및 체불임금 의무와의 관계 확인"
        ),
    },
    146: {
        "category": "context_required",
        "reason": (
            "연구기관 통상임금 산정 조항의 선행 문맥과 "
            "정확한 적용 대상 확인"
        ),
    },
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def cid(n):
    return f"H1B-CAND-V2-{n:05d}"


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"기존 출력 파일 보존: {OUTPUT}")

    original = load(INPUT)
    source = load(SOURCE)
    candidates = source["candidate_records"]

    if len(candidates) != 1537:
        raise ValueError("원문 후보 건수 불일치")

    index = {r["candidate_id"]: r for r in candidates}
    if len(index) != 1537:
        raise ValueError("원문 후보 ID 중복")

    used = {
        r["source_candidate_id"]
        for value in original.values()
        if isinstance(value, list)
        for r in value
        if isinstance(r, dict)
        and str(r.get("source_candidate_id", "")).startswith(
            "H1B-CAND-V2-"
        )
    }

    if len(used) != 161:
        raise ValueError(f"기존 분류 건수 불일치: {len(used)}")

    targets = set(POLICIES) | set(SUPPORT) | set(HOLDS)

    if len(targets) != 8:
        raise ValueError("신규 후보 수 불일치")

    if any(cid(n) in used for n in targets):
        raise ValueError("이미 분류한 후보와 중복")

    source_urls = {
        (r["source_id"], r["source_sha256"]): r["source_url"]
        for r in original["policy_records"]
        if r.get("source_url")
    }

    policy_drafts = []
    support_records = []
    hold_records = []

    for n in sorted(targets):
        r = index[cid(n)]
        excerpt = r["evidence_excerpt"]

        if r["source_id"] != "DOL-H1B-LCA-LAW":
            raise ValueError(f"출처 불일치: {cid(n)}")

        if sha256(excerpt) != r["excerpt_sha256"]:
            raise ValueError(f"원문 해시 불일치: {cid(n)}")

        key = (r["source_id"], r["source_sha256"])
        if key not in source_urls:
            raise ValueError(f"공식 출처 URL 연결 실패: {cid(n)}")

        base = {
            "source_candidate_id": cid(n),
            "source_id": r["source_id"],
            "source_url": source_urls[key],
            "source_sha256": r["source_sha256"],
            "source_paragraph_index": r["source_paragraph_index"],
            "evidence_excerpt": excerpt,
            "excerpt_sha256": r["excerpt_sha256"],
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        if n in POLICIES:
            policy_drafts.append({
                **base,
                "policy_id": f"US-WK-01-POL-WPR-{len(policy_drafts)+1:03d}",
                "program_id": "US-WK-01",
                "policy_statement_ko": POLICIES[n],
                "applicability": "H-1B 관련 해당 법정 적용 대상",
                "requirements": [],
                "exceptions": [],
                "effective_date": None,
                "expiration_date": None,
                "legal_status": "unverified",
                "human_review_decision": "policy_draft_candidate",
                "review_rationale_ko": (
                    "DOL 법률 원문 기반 초안. "
                    "선행 조항·적용 대상·예외·현행성 검증 필요."
                ),
            })
        elif n in SUPPORT:
            support_records.append({
                **base,
                "supports": SUPPORT[n]["supports"],
                "support_reason_ko": SUPPORT[n]["reason"],
                "link_status": "proposed",
                "human_review_decision": "supporting_evidence",
            })
        else:
            hold_records.append({
                **base,
                "human_review_decision": HOLDS[n]["category"],
                "review_reason_ko": HOLDS[n]["reason"],
            })

    result = deepcopy(original)
    result["additional_worker_protection_policy_drafts"] = policy_drafts
    result["worker_protection_supporting_evidence"] = support_records
    result["worker_protection_context_review"] = hold_records

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    if any(result[k] != v for k, v in original.items()
           if k not in {
               "review_status",
               "approved_for_user_answers",
               "approved_for_embedding",
               "automatic_eligibility_rules_enabled",
               "embedding_generated",
           }):
        raise ValueError("기존 데이터 변경")

    new_records = policy_drafts + support_records + hold_records

    if [len(policy_drafts), len(support_records), len(hold_records)] != [4, 2, 2]:
        raise ValueError("분류 건수 불일치")

    if len({r["source_candidate_id"] for r in new_records}) != 8:
        raise ValueError("신규 후보 ID 중복")

    existing_policy_ids = {
        r["policy_id"]
        for value in original.values()
        if isinstance(value, list)
        for r in value
        if isinstance(r, dict) and r.get("policy_id")
    }

    if any(r["policy_id"] in existing_policy_ids for r in policy_drafts):
        raise ValueError("신규 정책 ID 중복")

    if any(r["supports"] not in existing_policy_ids for r in support_records):
        raise ValueError("기존 정책 연결 대상 누락")

    for r in new_records:
        if sha256(r["evidence_excerpt"]) != r["excerpt_sha256"]:
            raise ValueError("신규 Evidence SHA-256 오류")
        if (
            r["semantic_support_verified"] is not False
            or r["legal_effect_verified"] is not False
            or r["review_status"] != "needs_review"
        ):
            raise ValueError("검토 상태 오류")

    for field in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    ):
        if result[field] is not False:
            raise ValueError(f"승인 차단 오류: {field}")

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    saved = load(OUTPUT)

    if any(saved[k] != v for k, v in original.items()
           if k not in {
               "review_status",
               "approved_for_user_answers",
               "approved_for_embedding",
               "automatic_eligibility_rules_enabled",
               "embedding_generated",
           }):
        raise ValueError("저장 후 기존 데이터 변경")

    print("\n=== H-1B WORKER PROTECTION VALIDATION ===")
    print("PREVIOUSLY CLASSIFIED:", len(used))
    print("NEW POLICY DRAFTS:", len(policy_drafts))
    print("SUPPORTING EVIDENCE:", len(support_records))
    print("CONTEXT / EXCEPTION REVIEW:", len(hold_records))
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
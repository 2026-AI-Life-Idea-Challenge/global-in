
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path("data/processed/usa/employment/h1b_specialty_occupation")

INPUT = BASE / "h1b_policy_consolidation_2026_modernization_draft.json"
SOURCE = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_enforcement_draft.json"

POLICIES = {
    132: (
        "노동부 장관은 일정한 LCA 조건을 고의로 위반하거나 "
        "신청서의 중요한 사실을 고의로 허위 진술한 것으로 "
        "판단된 고용주에 대해, 법에서 정한 조건에 따라 "
        "해당 판단일부터 최대 5년 동안 무작위 조사를 "
        "실시할 수 있다."
    ),
    134: (
        "노동부 장관은 고용주의 LCA 의무 위반에 관한 "
        "구체적이고 신뢰할 수 있는 정보를 접수하고 "
        "법에서 정한 위반 유형과 합리적 의심 요건 등이 "
        "충족되는 경우 조사를 실시할 수 있다. "
        "관련 규정은 정보 제공자의 신원 비공개도 허용한다."
    ),
}

CONTEXT_REVIEW = {
    142: (
        "미국인 근로자 대체·해고 판단에서 동등 이상의 "
        "보상과 복리후생을 갖춘 대체 일자리 제안의 "
        "예외 적용 범위 확인 필요"
    ),
    143: (
        "특정 채용 관련 의무 위반·허위 진술의 신고 "
        "자격 및 12개월 신고기한의 정확한 적용 범위 확인 필요"
    ),
}

HISTORICAL = {
    1473: (
        "2010년 특정 고용주에 대한 추가 수수료 도입과 "
        "2015년 9월 30일 종료에 관한 역사적 설명. "
        "현행 수수료 규정으로 사용 금지."
    ),
}

# 새로 분류할 원문 번호는 총 5개
TARGETS = set(POLICIES) | set(CONTEXT_REVIEW) | set(HISTORICAL)

# 과거 검토에서 이미 제외 처리된 원문
EXISTING_EXCLUDED = {
    141: "US-WK-01-POL-0021",
    144: "US-WK-01-POL-0047",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def cid(number):
    return f"H1B-CAND-V2-{number:05d}"


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"기존 출력 파일 덮어쓰기 금지: {OUTPUT}")

    original = load(INPUT)
    candidates = load(SOURCE)["candidate_records"]

    if len(candidates) != 1537:
        raise ValueError("전체 원문 후보 건수 불일치")

    index = {r["candidate_id"]: r for r in candidates}

    if len(index) != len(candidates):
        raise ValueError("전체 원문 후보 ID 중복")

    if len(TARGETS) != 5:
        raise ValueError("신규 검토 대상 건수 불일치")

    # 정책 초안처럼 후보 ID가 없는 레코드는 제외하고
    # 이미 분류된 원문 후보 ID만 집계한다.
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

    if len(used) != 156:
        raise ValueError(f"기존 분류 원문 수 불일치: {len(used)}")

    for number, policy_id in EXISTING_EXCLUDED.items():
        record = next(
            (
                r for r in original["policy_records"]
                if r["source_candidate_id"] == cid(number)
            ),
            None,
        )
        if (
            record is None
            or record["policy_id"] != policy_id
            or record["human_review_decision"]
            != "exclude_from_core_policy"
        ):
            raise ValueError(f"기존 제외 결정 확인 실패: {cid(number)}")

    if any(cid(n) in used for n in TARGETS):
        raise ValueError("신규 처리 대상 중 이미 검토한 원문 존재")

    # 기존 공식 출처 ID와 원본 문서 해시로 URL 연결
    source_urls = {
        (r["source_id"], r["source_sha256"]): r["source_url"]
        for r in original["policy_records"]
        if r.get("source_url")
    }

    policy_drafts = []
    context_records = []
    historical_records = []

    for number in sorted(TARGETS):
        candidate = index[cid(number)]
        excerpt = candidate["evidence_excerpt"]

        expected_source = (
            "DHS-H1B-BIOMETRIC-FEE-2026"
            if number == 1473
            else "DOL-H1B-LCA-LAW"
        )

        if candidate["source_id"] != expected_source:
            raise ValueError(f"출처 불일치: {cid(number)}")

        if sha256(excerpt) != candidate["excerpt_sha256"]:
            raise ValueError(f"원문 SHA-256 불일치: {cid(number)}")

        source_key = (
            candidate["source_id"],
            candidate["source_sha256"],
        )

        if source_key not in source_urls:
            raise ValueError(f"출처 URL 연결 실패: {cid(number)}")

        base = {
            "source_candidate_id": cid(number),
            "source_id": candidate["source_id"],
            "source_url": source_urls[source_key],
            "source_sha256": candidate["source_sha256"],
            "source_paragraph_index": candidate[
                "source_paragraph_index"
            ],
            "evidence_excerpt": excerpt,
            "excerpt_sha256": candidate["excerpt_sha256"],
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
        }

        if number in POLICIES:
            policy_drafts.append({
                **base,
                "policy_id": (
                    f"US-WK-01-POL-ENF-{len(policy_drafts)+1:03d}"
                ),
                "program_id": "US-WK-01",
                "policy_statement_ko": POLICIES[number],
                "applicability": "H-1B LCA 고용주 조사",
                "requirements": [],
                "exceptions": [],
                "effective_date": None,
                "expiration_date": None,
                "legal_status": "unverified",
                "human_review_decision": "policy_draft_candidate",
                "review_rationale_ko": (
                    "DOL 법률 원문을 근거로 작성한 초안. "
                    "위반 유형·조사 요건·현행성 검증 필요."
                ),
            })

        elif number in CONTEXT_REVIEW:
            context_records.append({
                **base,
                "human_review_decision": "context_required",
                "review_reason_ko": CONTEXT_REVIEW[number],
            })

        else:
            historical_records.append({
                **base,
                "human_review_decision": "historical_background",
                "historical_note_ko": HISTORICAL[number],
                "historical_end_date": "2015-09-30",
                "current_rule": False,
            })

    result = deepcopy(original)

    result["additional_enforcement_policy_drafts"] = policy_drafts
    result["enforcement_context_review"] = context_records
    result["historical_fee_evidence"] = historical_records

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    # 이전 통합 데이터의 모든 필드가 그대로 보존됐는지 검사
    for key, value in original.items():
        if key in {
            "review_status",
            "approved_for_user_answers",
            "approved_for_embedding",
            "automatic_eligibility_rules_enabled",
            "embedding_generated",
        }:
            continue
        if result[key] != value:
            raise ValueError(f"기존 데이터 변경: {key}")

    if (
        len(policy_drafts) != 2
        or len(context_records) != 2
        or len(historical_records) != 1
    ):
        raise ValueError("신규 분류 건수 불일치")

    all_new = policy_drafts + context_records + historical_records

    if len({r["source_candidate_id"] for r in all_new}) != 5:
        raise ValueError("신규 Evidence 중복")

    for record in all_new:
        if sha256(record["evidence_excerpt"]) != record["excerpt_sha256"]:
            raise ValueError("신규 Evidence 무결성 오류")
        if (
            record["semantic_support_verified"] is not False
            or record["legal_effect_verified"] is not False
            or record["review_status"] != "needs_review"
        ):
            raise ValueError("검토 상태 오류")

    for key in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    ):
        if result[key] is not False:
            raise ValueError(f"안전 상태 오류: {key}")

    with OUTPUT.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    saved = load(OUTPUT)

    if any(saved[key] != value for key, value in original.items()
           if key in saved and key not in {
               "review_status",
               "approved_for_user_answers",
               "approved_for_embedding",
               "automatic_eligibility_rules_enabled",
               "embedding_generated",
           }):
        raise ValueError("저장 후 기존 데이터 불일치")

    print("\n=== H-1B ENFORCEMENT VALIDATION ===")
    print("PREVIOUSLY CLASSIFIED:", len(used))
    print("NEW ENFORCEMENT POLICIES:", len(policy_drafts))
    print("CONTEXT REVIEW:", len(context_records))
    print("HISTORICAL FEE RECORDS:", len(historical_records))
    print("EXISTING EXCLUSIONS PRESERVED:", len(EXISTING_EXCLUDED))
    print("TOTAL CLASSIFIED:", len(used) + len(all_new))
    print("REMAINING:", 1537 - len(used) - len(all_new))
    print("PREVIOUS DATA PRESERVED: PASS")
    print("NEW EVIDENCE HASHES: PASS")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
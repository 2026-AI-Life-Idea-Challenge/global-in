
import hashlib
import json
from copy import deepcopy
from pathlib import Path

BASE = Path(
    "data/processed/usa/employment/h1b_specialty_occupation"
)

INPUT = BASE / "h1b_policy_consolidation_2026_employer_obligations_draft.json"
SOURCE = BASE / "h1b_policy_candidates_2026_v2_draft.json"
OUTPUT = BASE / "h1b_policy_consolidation_2026_modernization_draft.json"

# (정책 ID 접미번호, 근거 원문번호, 한국어 정책 초안, 원문 확인 키워드)
POLICY_SPECS = [
    (
        1, 1118,
        "H-1B 청원인은 요청한 청원 유효기간의 시작일을 기준으로 "
        "수혜자에게 제공할 실제 전문직 채용 자리가 존재함을 "
        "입증해야 한다.",
        "bona fide position",
    ),
    (
        2, 1118,
        "H-1B 청원에 제출하는 노동조건신청서(LCA)는 "
        "청원 내용과 적절하게 일치하고 이를 뒷받침해야 한다.",
        "properly corresponds",
    ),
    (
        3, 1118,
        "USCIS는 H-1B 현장실사를 수행할 수 있으며, "
        "현장실사에 대한 협조 거부는 청원 거절 또는 "
        "승인 취소의 근거가 될 수 있다.",
        "site visits",
    ),
    (
        4, 1444,
        "H-1B 청원인이 되는 미국 고용주는 미국 내 실제 채용 "
        "제의를 보유하고, 미국 내 법적 존재 및 송달 가능성을 "
        "갖추며, IRS 납세자 식별번호를 보유해야 한다. "
        "미국 내 원격근무나 사업장 외 근무도 채용 제의에 "
        "포함될 수 있다.",
        "Internal Revenue Service",
    ),
    (
        5, 1444,
        "H-1B 수혜자가 제3자 조직의 직무를 맡아 해당 조직의 "
        "체계에 편입되는 형태로 배치된다면, 수행 업무는 "
        "전문직이어야 하며 전문직 여부 판단에서는 "
        "청원인보다 해당 제3자의 직무 요건이 중요하다.",
        "Third party requirements",
    ),
    (
        6, 1444,
        "H-1B 수혜자가 청원 기업의 지분을 50% 초과 보유하거나 "
        "과반수 의결권을 갖는 경우, 근무시간의 대부분을 "
        "전문직 업무에 사용한다는 조건 아래 기업 소유 및 "
        "경영과 직접 관련된 업무를 수행할 수 있다.",
        "controlling interest",
    ),
    (
        7, 1444,
        "적격 고등교육기관·비영리 연구기관·정부 연구기관에 "
        "직접 고용되지 않은 H-1B 수혜자도, 근무시간의 "
        "절반 이상을 적격 기관의 핵심 목적이나 활동을 "
        "직접 지원·발전시키는 업무에 사용하는 등 "
        "해당 요건을 충족하면 Cap 면제 대상이 될 수 있다. "
        "적격 기관을 위한 미국 내 원격근무도 고려될 수 있다.",
        "at least half of their work time",
    ),
    (
        8, 1445,
        "H-1B 청원 승인은 청원인의 폐업, 서면 철회, "
        "해당 노동 인증의 취소 또는 청원인이 수혜자의 "
        "고용 종료를 통지하는 경우 등 규정에 명시된 "
        "사유에 따라 자동 취소될 수 있다.",
        "Immediate and automatic revocation",
    ),
    (
        9, 1445,
        "H-1B 청원 승인 심사가 최초 요청 유효기간 종료일 "
        "이후에 이루어지는 경우, USCIS는 필요한 상황에서 "
        "새 고용기간을 요청하는 증거요청(RFE)을 발급할 수 "
        "있다. 변경된 기간에 맞는 LCA 등 추가 요건이 "
        "적용될 수 있다.",
        "request for evidence",
    ),
]

NEW_CANDIDATE_NUMBERS = {1118, 1444, 1445}
EXISTING_CONTEXT_NUMBER = 1117

PREVIOUS_GROUPS = [
    "policy_records",
    "supplemental_stay_evidence",
    "supplemental_stay_policy_drafts",
    "additional_core_policy_drafts",
    "additional_supporting_evidence",
    "additional_legal_review_evidence",
    "additional_registration_policy_drafts",
    "registration_supporting_evidence",
    "registration_operational_information",
    "registration_context_review",
    "additional_employer_policy_drafts",
    "employer_legal_scope_review",
    "employer_context_review",
]


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cid(number):
    return f"H1B-CAND-V2-{number:05d}"


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"출력 파일이 이미 존재합니다: {OUTPUT}")

    original = load(INPUT)
    source = load(SOURCE)
    candidates = source["candidate_records"]

    if len(candidates) != 1537:
        raise ValueError("원문 후보 수 불일치")

    index = {r["candidate_id"]: r for r in candidates}

    if len(index) != len(candidates):
        raise ValueError("원문 후보 ID 중복")

    for group in PREVIOUS_GROUPS:
        if group not in original:
            raise ValueError(f"기존 그룹 누락: {group}")

    previous_records = [
        r
        for group in PREVIOUS_GROUPS
        for r in original[group]
    ]

    previous_ids = {
        r["source_candidate_id"]
        for r in previous_records
        if "source_candidate_id" in r
    }

    if len(previous_ids) != 153:
        raise ValueError(
            f"기존 검토 원문 수 불일치: {len(previous_ids)}"
        )

    context_id = cid(EXISTING_CONTEXT_NUMBER)

    if context_id not in previous_ids:
        raise ValueError("기존 연구기관 검토 기록 누락")

    for number in NEW_CANDIDATE_NUMBERS:
        if cid(number) in previous_ids:
            raise ValueError(f"신규 후보가 기존 기록에 존재: {cid(number)}")

    context_record = next(
        (
            r for r in original["policy_records"]
            if r["source_candidate_id"] == context_id
        ),
        None,
    )

    if (
        context_record is None
        or context_record["policy_id"] != "US-WK-01-POL-0092"
    ):
        raise ValueError("기존 연구기관 정책 연결 실패")

    source_urls = {
        (r["source_id"], r["source_sha256"]): r["source_url"]
        for r in original["policy_records"]
        if r.get("source_url")
    }

    evidence_records = []

    for number in sorted(NEW_CANDIDATE_NUMBERS):
        candidate = index[cid(number)]
        excerpt = candidate["evidence_excerpt"]

        if candidate["source_id"] != "DHS-H1B-MODERNIZATION-2024":
            raise ValueError(f"출처 불일치: {cid(number)}")

        if digest(excerpt) != candidate["excerpt_sha256"]:
            raise ValueError(f"원문 해시 불일치: {cid(number)}")

        source_key = (
            candidate["source_id"],
            candidate["source_sha256"],
        )

        if source_key not in source_urls:
            raise ValueError(f"출처 URL 연결 실패: {cid(number)}")

        evidence_records.append({
            "source_candidate_id": cid(number),
            "source_id": candidate["source_id"],
            "source_url": source_urls[source_key],
            "source_sha256": candidate["source_sha256"],
            "source_paragraph_index": candidate[
                "source_paragraph_index"
            ],
            "evidence_excerpt": excerpt,
            "excerpt_sha256": candidate["excerpt_sha256"],
            "review_status": "needs_review",
            "semantic_support_verified": False,
            "legal_effect_verified": False,
        })

    evidence_index = {
        r["source_candidate_id"]: r
        for r in evidence_records
    }

    policy_drafts = []

    for policy_number, candidate_number, statement, marker in POLICY_SPECS:
        evidence = evidence_index[cid(candidate_number)]

        if marker.lower() not in evidence["evidence_excerpt"].lower():
            raise ValueError(
                f"원문 확인 키워드 누락: {cid(candidate_number)} / {marker}"
            )

        policy_drafts.append({
            "policy_id": f"US-WK-01-POL-MOD-{policy_number:03d}",
            "program_id": "US-WK-01",
            "source_candidate_id": cid(candidate_number),
            "source_id": evidence["source_id"],
            "source_url": evidence["source_url"],
            "source_sha256": evidence["source_sha256"],
            "source_paragraph_index": evidence[
                "source_paragraph_index"
            ],
            "excerpt_sha256": evidence["excerpt_sha256"],
            "supporting_clause_keyword": marker,
            "policy_statement_ko": statement,
            "applicability": "H-1B 청원 및 해당 세부 규정",
            "requirements": [],
            "exceptions": [],
            "effective_date": None,
            "expiration_date": None,
            "legal_status": "unverified",
            "human_review_decision": "policy_draft_candidate",
            "semantic_support_verified": False,
            "legal_effect_verified": False,
            "review_status": "needs_review",
            "review_rationale_ko": (
                "2024년 DHS 현대화 규정 원문에 기반한 초안. "
                "조문별 의미·적용 예외·현행 효력 검증 필요."
            ),
        })

    result = deepcopy(original)

    result["modernization_evidence_records"] = evidence_records
    result["additional_modernization_policy_drafts"] = policy_drafts
    result["modernization_existing_evidence_links"] = [{
        "source_candidate_id": context_id,
        "existing_policy_id": "US-WK-01-POL-0092",
        "linked_new_policy_ids": [
            "US-WK-01-POL-MOD-007"
        ],
        "link_status": "proposed",
        "review_status": "needs_review",
    }]

    result["review_status"] = "needs_review"
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    # Validate before writing; preserve previous records unchanged.
    if any(result[g] != original[g] for g in PREVIOUS_GROUPS):
        raise ValueError("기존 검토 기록 변경")

    if len(evidence_records) != 3:
        raise ValueError("신규 원문 건수 오류")

    if len(policy_drafts) != 9:
        raise ValueError("정책 초안 건수 오류")

    if len({
        r["policy_id"] for r in policy_drafts
    }) != 9:
        raise ValueError("정책 ID 중복")

    if len({
        r["source_candidate_id"] for r in evidence_records
    }) != 3:
        raise ValueError("신규 Evidence ID 중복")

    for record in evidence_records:
        if digest(record["evidence_excerpt"]) != record["excerpt_sha256"]:
            raise ValueError("Evidence 해시 오류")

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

    if any(saved[g] != original[g] for g in PREVIOUS_GROUPS):
        raise ValueError("저장 후 기존 기록 불일치")

    if len(saved["additional_modernization_policy_drafts"]) != 9:
        raise ValueError("저장 후 정책 수 불일치")

    print("\n=== H-1B MODERNIZATION VALIDATION ===")
    print("PREVIOUSLY CLASSIFIED:", len(previous_ids))
    print("NEW UNIQUE SOURCE CANDIDATES:", len(evidence_records))
    print("NEW POLICY DRAFTS:", len(policy_drafts))
    print("EXISTING RESEARCH EVIDENCE LINK: 1")
    print("TOTAL CLASSIFIED CANDIDATES:",
          len(previous_ids) + len(evidence_records))
    print("REMAINING CANDIDATES:",
          1537 - len(previous_ids) - len(evidence_records))
    print("PREVIOUS DATA PRESERVED: PASS")
    print("EVIDENCE HASHES: PASS")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)


if __name__ == "__main__":
    main()
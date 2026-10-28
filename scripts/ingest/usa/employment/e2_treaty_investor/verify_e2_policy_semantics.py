
import copy
import hashlib
import json
from pathlib import Path

BASE = Path("data/processed/usa/employment/e2_treaty_investor")

INPUT = BASE / "e2_policy_review_2026_consolidated_draft.json"
EVIDENCE = BASE / "e2_policy_evidence_2026_refined_draft.json"

OUTPUT = BASE / "e2_policy_review_2026_semantic_refined_draft.json"
REPORT = BASE / "e2_semantic_review_report_2026_draft.json"

REVISIONS = {
    "E2-03": (
        "E-2 투자금의 상당성은 기존 사업 인수 또는 신규 사업 설립에 "
        "필요한 총비용과의 비율, 사업 성공에 대한 투자자의 재정적 "
        "확약 및 사업을 개발·지휘할 가능성을 뒷받침하는 규모 등을 "
        "고려하여 판단한다. 사업비용이 낮을수록 요구되는 투자금 "
        "비율은 일반적으로 높아진다."
    ),
    "E2-06": (
        "E-2의 적격 사업체는 상품이나 서비스를 제공하여 "
        "수익을 창출하는 실제적이고 활동 중인 상업적 또는 "
        "기업가적 사업이어야 한다."
    ),
    "E2-07": (
        "E-2 사업체는 투자자와 가족의 최소 생계유지에 필요한 "
        "소득을 초과하여 창출할 현재 또는 미래의 능력이 없는 "
        "한계적 사업에 해당해서는 안 된다."
    ),
    "E2-10": (
        "자격을 충족하는 E-2 투자자와 직원의 최초 미국 내 "
        "허가 체류기간은 최대 2년이다. 비자 유효기간과 "
        "실제 허가 체류기간은 구분해야 한다."
    ),
}

PENDING = [
    "Current legal effect and policy completeness",
    "Detailed substantial investment evaluation",
    "Employee nationality and enterprise ownership exceptions",
    "Seoul embassy application procedure",
    "DS-156E procedure and documentary exceptions",
    "Fee and reciprocity re-verification at application time",
    "Team master report US-WK-02 comparison",
    "Internal program ID registry confirmation",
    "Section-level evidence and semantic sign-off",
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def hash_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main():
    if OUTPUT.exists() or REPORT.exists():
        raise FileExistsError("출력 파일이 이미 존재합니다.")

    original = read(INPUT)
    evidence_doc = read(EVIDENCE)
    result = copy.deepcopy(original)

    policies = result["policy_records"]
    evidence = evidence_doc["evidence_records"]

    if len(policies) != 14 or len(evidence) != 14:
        raise ValueError("정책 또는 Evidence 수 불일치")

    policy_ids = [r["policy_id"] for r in policies]
    evidence_ids = [r["policy_id"] for r in evidence]

    if len(set(policy_ids)) != 14:
        raise ValueError("정책 ID 중복")

    if len(set(evidence_ids)) != 14:
        raise ValueError("Evidence ID 중복")

    if set(policy_ids) != set(evidence_ids):
        raise ValueError("정책/Evidence ID 불일치")

    evidence_by_id = {
        r["policy_id"]: r for r in evidence
    }

    sources = {
        r["source_id"]: r
        for r in result["official_sources"]
    }

    if len(sources) != 5:
        raise ValueError("공식 출처 개수 불일치")

    for policy in policies:
        pid = policy["policy_id"]
        ev = evidence_by_id[pid]

        if ev["source_id"] not in policy["source_ids"]:
            raise ValueError(f"출처 연결 실패: {pid}")

        if ev["source_id"] not in sources:
            raise ValueError(f"공식 출처 누락: {pid}")

        if ev["source_sha256"] != sources[
            ev["source_id"]
        ]["sha256"]:
            raise ValueError(f"출처 해시 연결 실패: {pid}")

        if hash_text(ev["excerpt_text"]) != ev[
            "excerpt_sha256"
        ]:
            raise ValueError(f"발췌문 해시 실패: {pid}")

        if pid in REVISIONS:
            policy["summary_ko"] = REVISIONS[pid]

        if not str(policy.get("summary_ko", "")).strip():
            raise ValueError(f"정책 요약 누락: {pid}")

        policy["review_status"] = "needs_review"

    result["validation_status"] = "needs_review"
    result["section_semantics_verified"] = False
    result["eligibility_rules_verified"] = False
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    # 원본 대비 정책 요약 외의 변경을 허용하지 않음
    expected = copy.deepcopy(original)

    for policy in expected["policy_records"]:
        if policy["policy_id"] in REVISIONS:
            policy["summary_ko"] = REVISIONS[
                policy["policy_id"]
            ]

    if result != expected:
        raise ValueError("허용되지 않은 데이터 변경")

    report = {
        "team_reference_program_id": result.get(
            "team_reference_program_id"
        ),
        "internal_program_id": result.get(
            "internal_program_id"
        ),
        "internal_id_status": result.get(
            "internal_id_status"
        ),
        "policy_count": len(policies),
        "evidence_count": len(evidence),
        "official_source_count": len(sources),
        "revised_policy_ids": sorted(REVISIONS),
        "summaries_complete": True,
        "evidence_sha256_verified": True,
        "evidence_source_hash_links_verified": True,
        "section_semantics_verified": False,
        "legal_effect_verified": False,
        "completeness_verified": False,
        "review_method": (
            "targeted_excerpt_alignment_and_integrity_check"
        ),
        "pending_review_items": PENDING,
        "review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if read(OUTPUT) != result or read(REPORT) != report:
        raise ValueError("저장 후 검증 실패")

    print("=== E-2 SEMANTIC REFINEMENT ===")
    print("POLICIES:", len(policies))
    print("EVIDENCE:", len(evidence))
    print("OFFICIAL SOURCES:", len(sources))
    print("REVISED:", ", ".join(sorted(REVISIONS)))
    print("ALL SUMMARIES PRESENT: PASS")
    print("EVIDENCE SHA-256: PASS")
    print("EVIDENCE SOURCE LINKS: PASS")
    print("PREVIOUS DATA PRESERVED: PASS")
    print("LEGAL EFFECT VERIFIED: False")
    print("COMPLETENESS VERIFIED: False")
    print("APPROVED FOR ANSWERS: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)
    print("REPORT:", REPORT)


if __name__ == "__main__":
    main()
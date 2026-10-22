
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

BASE = Path("data/processed/usa/employment/e2_treaty_investor")

POLICY_PATH = BASE / "e2_policy_review_2026_draft.json"
EVIDENCE_PATH = BASE / "e2_policy_evidence_2026_refined_draft.json"
OLD_REPORT_PATH = BASE / "e2_validation_report_2026_draft.json"

OUTPUT = BASE / "e2_policy_review_2026_consolidated_draft.json"
REPORT_OUTPUT = BASE / "e2_batch_validation_2026_draft.json"

UPDATES = {
    "E2-02": {
        "source_id": "DOS-TREATY",
        "summary": (
            "대한민국은 미국의 E-2 조약 투자자 비자 대상 국가이다. "
            "미국 국무부 조약국 목록에 따르면 대한민국의 E-2 "
            "조약 발효일은 1957년 11월 7일이다. "
            "다만 조약국 국적만으로 비자 자격이 자동 충족되지는 않는다."
        ),
    },
    "E2-11": {
        "source_id": "DOS-KR-RECIPROCITY",
        "summary": (
            "미국 국무부의 대한민국 국적자 상호주의 일정에 따르면 "
            "E-2 비자의 발급 수수료(reciprocity/issuance fee)는 "
            "없으며, 복수 입국이 가능하고 비자 유효기간은 "
            "60개월이다. 이는 미국 내 허가 체류기간과는 다르며, "
            "별도의 비자 신청 수수료가 적용될 수 있다."
        ),
    },
    "E2-12": {
        "source_id": "DOS-E-VISA",
        "summary": (
            "미국 국무부가 안내하는 E 계열 비이민비자의 "
            "일반 비자 신청 수수료는 미화 315달러이며, "
            "원칙적으로 환불되지 않는다. "
            "비자 발급 수수료는 국적별 상호주의 일정에 따라 "
            "별도로 확인해야 하며, 실제 신청 시점의 "
            "수수료와 해당 공관의 납부 절차를 재확인해야 한다."
        ),
    },
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    original = load(POLICY_PATH)
    evidence_doc = load(EVIDENCE_PATH)
    prior_report = load(OLD_REPORT_PATH)

    result = copy.deepcopy(original)
    policies = result["policy_records"]
    evidence = evidence_doc["evidence_records"]

    if len(policies) != 14 or len(evidence) != 14:
        raise ValueError("기존 정책 또는 Evidence 수가 14건이 아닙니다.")

    policy_index = {r["policy_id"]: r for r in policies}
    evidence_index = {r["policy_id"]: r for r in evidence}

    if len(policy_index) != 14 or len(evidence_index) != 14:
        raise ValueError("정책 또는 Evidence ID 중복")

    if set(policy_index) != set(evidence_index):
        raise ValueError("정책과 Evidence ID 연결 불일치")

    if prior_report.get("source_integrity_checked") is not True:
        raise ValueError("기존 출처 무결성 검증 미완료")

    if prior_report.get("policy_evidence_linkage_checked") is not True:
        raise ValueError("기존 Evidence 연결 검증 미완료")

    source_index = {
        r["source_id"]: r for r in result["official_sources"]
    }

    if len(source_index) != 5:
        raise ValueError("공식 출처 수 불일치")

    hash_errors = []

    for policy_id, ev in evidence_index.items():
        if ev["source_id"] not in source_index:
            raise ValueError(f"출처 누락: {policy_id}")

        if ev["source_id"] not in policy_index[policy_id]["source_ids"]:
            raise ValueError(f"정책 출처 연결 불일치: {policy_id}")

        if sha256(ev["excerpt_text"]) != ev["excerpt_sha256"]:
            hash_errors.append(policy_id)

    if hash_errors:
        raise ValueError(f"Evidence SHA-256 오류: {hash_errors}")

    for policy_id, update in UPDATES.items():
        policy = policy_index[policy_id]
        ev = evidence_index[policy_id]

        if str(policy.get("summary_ko", "")).strip():
            raise ValueError(f"기존 요약이 존재합니다: {policy_id}")

        if ev["source_id"] != update["source_id"]:
            raise ValueError(f"보완 대상 출처 불일치: {policy_id}")

        policy["summary_ko"] = update["summary"]

    missing_summaries = [
        r["policy_id"]
        for r in policies
        if not str(r.get("summary_ko", "")).strip()
    ]

    if missing_summaries:
        raise ValueError(f"정책 요약 누락: {missing_summaries}")

    for record in policies:
        record["review_status"] = "needs_review"

    result["validation_status"] = "needs_review"
    result["section_semantics_verified"] = False
    result["eligibility_rules_verified"] = False
    result["approved_for_user_answers"] = False
    result["approved_for_embedding"] = False
    result["automatic_eligibility_rules_enabled"] = False
    result["embedding_generated"] = False

    unchanged = copy.deepcopy(original)

    for record in unchanged["policy_records"]:
        if record["policy_id"] in UPDATES:
            record["summary_ko"] = UPDATES[record["policy_id"]]["summary"]

    for record in unchanged["policy_records"]:
        record["review_status"] = "needs_review"

    for key in (
        "validation_status",
        "section_semantics_verified",
        "eligibility_rules_verified",
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
        "embedding_generated",
    ):
        unchanged[key] = result[key]

    if result != unchanged:
        raise ValueError("허용되지 않은 기존 데이터 변경")

    report = {
        "program_id": result.get("team_reference_program_id"),
        "internal_program_id": result.get("internal_program_id"),
        "internal_id_status": result.get("internal_id_status"),
        "policy_count": len(policies),
        "evidence_count": len(evidence),
        "official_source_count": len(source_index),
        "summaries_completed": len(policies),
        "newly_completed_policy_ids": sorted(UPDATES),
        "applicant_type_counts": dict(
            Counter(r.get("applicant_type", "unknown") for r in policies)
        ),
        "evidence_sha256_checked": True,
        "policy_evidence_linkage_checked": True,
        "existing_source_integrity_previously_checked": True,
        "current_source_integrity_rechecked": False,
        "section_semantics_verified": False,
        "eligibility_rules_verified": False,
        "completeness_verified": False,
        "pending_review_topics": result.get("pending_review_topics", []),
        "pending_review_items": prior_report.get(
            "pending_review_items", []
        ),
        "review_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
        "embedding_generated": False,
        "notes": [
            "Three blank policy summaries populated from existing evidence.",
            "Korean E-2 reciprocity validity is not U.S. admission duration.",
            "MRV application fee and reciprocity issuance fee are distinct.",
            "Legal and semantic review remain pending.",
            "Team program ID is not proof of internal registry approval.",
        ],
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    REPORT_OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if load(OUTPUT) != result or load(REPORT_OUTPUT) != report:
        raise ValueError("저장 검증 실패")

    print("=== E-2 BATCH CONSOLIDATION ===")
    print("POLICIES:", len(policies))
    print("EVIDENCE:", len(evidence))
    print("OFFICIAL SOURCES:", len(source_index))
    print("NEWLY COMPLETED SUMMARIES:", len(UPDATES))
    print("TOTAL COMPLETED SUMMARIES:", len(policies))
    print("EVIDENCE SHA-256: PASS")
    print("POLICY-EVIDENCE LINKS: PASS")
    print("PREVIOUS DATA PRESERVED: PASS")
    print("LEGAL EFFECT VERIFIED: False")
    print("SEMANTIC REVIEW VERIFIED: False")
    print("APPROVED FOR ANSWERS: False")
    print("APPROVED FOR EMBEDDING: False")
    print("REVIEW STATUS: needs_review")
    print("SAVED:", OUTPUT)
    print("REPORT:", REPORT_OUTPUT)


if __name__ == "__main__":
    main()
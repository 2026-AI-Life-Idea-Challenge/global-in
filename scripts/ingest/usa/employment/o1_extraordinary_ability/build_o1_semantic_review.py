
import json
from pathlib import Path

ROOT = Path(
    "data/processed/usa/employment/o1_extraordinary_ability"
)

POLICY_PATH = ROOT / "o1_policy_review_2026_draft.json"
EVIDENCE_PATH = ROOT / "o1_policy_evidence_2026_refined_draft.json"
OUTPUT_PATH = ROOT / "o1_semantic_review_2026_draft.md"

HIGH_PRIORITY_IDS = {
    "O1-04", "O1-05", "O1-06",
    "O1-15", "O1-22", "O1-23",
    "O1-42", "O1-48", "O1-52", "O1-53",
    "O1-67", "O1-68", "O1-69", "O1-70",
    "O1-74", "O1-75", "O1-76", "O1-77",
}


def main():
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Refusing to overwrite: {OUTPUT_PATH}"
        )

    policy_data = json.loads(
        POLICY_PATH.read_text(encoding="utf-8")
    )
    evidence_data = json.loads(
        EVIDENCE_PATH.read_text(encoding="utf-8")
    )

    policies = policy_data["policy_records"]
    evidence_map = {
        item["policy_id"]: item
        for item in evidence_data["evidence_records"]
    }

    if len(policies) != 77 or len(evidence_map) != 77:
        raise ValueError("Expected 77 policies and 77 evidence records")

    lines = [
        "# O-1/O-2/O-3 정책–Evidence 의미 검토",
        "",
        "- 프로그램: US-WK-04",
        "- 전체 정책: 77",
        "- 공식 출처: 11",
        "- 구조 검증: 16/16 PASS",
        "- 의미적 검증: 미완료",
        "- 법적 검증: 미완료",
        "- 모든 레코드: needs_review",
        "",
        "> 주의: 원문에서 문장을 찾았다는 사실만으로 "
        "정책의 법적 정확성이 검증되는 것은 아닙니다.",
        "",
        "## 검토 기준",
        "",
        "각 정책에 대해 다음 내용을 확인합니다.",
        "",
        "1. 발췌문이 해당 정책의 핵심 주장을 직접 뒷받침하는가?",
        "2. 조건, 예외, 대상 분류, 숫자, 날짜가 일치하는가?",
        "3. 원문 일부를 잘라내면서 중요한 단서가 누락되지 않았는가?",
        "4. 수수료와 행정 절차는 최신 재확인이 필요한가?",
        "",
    ]

    for policy in policies:
        pid = policy["policy_id"]
        evidence = evidence_map[pid]

        priority = (
            "우선 검토"
            if pid in HIGH_PRIORITY_IDS
            else "일반 검토"
        )

        lines.extend([
            f"## {pid} — {policy['topic']}",
            "",
            f"- 검토 우선순위: **{priority}**",
            f"- 비자 분류: {', '.join(policy['visa_classifications'])}",
            f"- 공식 출처 ID: {evidence['source_id']}",
            f"- 검색어: `{evidence['search_phrase']}`",
            f"- 정책 상태: `{policy['review_status']}`",
            f"- 근거 검증: `{evidence['semantic_support_verified']}`",
            "",
            "### 정책 요약",
            "",
            policy["summary_ko"],
            "",
            "### 영어 원문 후보",
            "",
            "> " + evidence["evidence_excerpt"].replace("\n", " "),
            "",
            "### 검토 결과",
            "",
            "- [ ] 직접 근거 확인",
            "- [ ] 대상·조건·예외 일치 확인",
            "- [ ] 추가 원문 확인 필요 여부 판단",
            "",
            "**검토 메모:** 미작성",
            "",
            "---",
            "",
        ])

    OUTPUT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("=== O SEMANTIC REVIEW REPORT ===")
    print("Policies:", len(policies))
    print("Evidence:", len(evidence_map))
    print("High-priority policies:", len(HIGH_PRIORITY_IDS))
    print("Semantic approvals:", 0)
    print("Saved:", OUTPUT_PATH)
    print("[PASS] Review document generated")
    print("[INFO] No semantic or legal approvals were granted")


if __name__ == "__main__":
    main()
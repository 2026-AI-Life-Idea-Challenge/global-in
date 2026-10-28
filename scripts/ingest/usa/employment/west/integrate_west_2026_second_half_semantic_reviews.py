
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re

# ============================================================
# STEP 64-63
# WEST 2026 H2 검토 이슈 통합
#
# - 원본 검토 이슈 보존
# - 신규 검토 이슈 추적
# - 유사 주제 후보 표시
# - 정책 승인/자동 판정 수행하지 않음
# - 기존 파일 덮어쓰기 금지
# ============================================================

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT
    / "data/processed/usa/employment/west/2026_second_half"
)

INPUTS = {
    "register": (
        "west_2026_second_half_review_register.json",
        "49cd19ae12b204dea33db02767025552c2d717199ce038182dd6223b0582ca0b",
    ),
    "visa": (
        "west_2026_second_half_visa_internship_review.json",
        "9e796baff8fe1df5a3b2056d7b6cad94603624c18024dd836921c3dce3034678",
    ),
    "academic": (
        "west_2026_second_half_academic_finance_review.json",
        "c3cb750badb91b75e25746c6bf1ccb18e39a8302a3d5ccfed3b5a03577d48925",
    ),
    "documents": (
        "west_2026_second_half_documents_scores_review.json",
        "473fad7f914ed47eb0c570b82f36a39d250097923ef7318de1ec04a28699c6d7",
    ),
}

OUTPUT = (
    BASE / "west_2026_second_half_semantic_review_registry.json"
)

AUDIT = (
    BASE / "west_2026_second_half_semantic_review_audit.json"
)

TOPICS = {
    "visa_internship": [
        "비자", "J-1", "212(e)", "웨이버",
        "본국", "인턴십", "전공",
    ],
    "academic_graduation": [
        "학적", "졸업", "수료자", "학기",
        "재학생", "지원 자격",
    ],
    "financial_loan": [
        "지원금", "지원구간", "대출", "환율",
        "참가비", "환수", "재정",
    ],
    "documents": [
        "증빙", "서류", "제출",
        "발급", "등록번호", "성적표",
    ],
    "english_scores": [
        "TOEIC", "Speaking", "ACTFL",
        "어학", "환산표",
    ],
    "schedule": [
        "일정", "마감일", "선발", "시기",
    ],
    "faq": [
        "FAQ", "문답", "질문", "답변",
    ],
}

# 우선순위는 작업 순서 제안이며
# 위험도에 대한 법률적 판정이 아니다.
TOPIC_PRIORITY = {
    "visa_internship": "P0",
    "academic_graduation": "P1",
    "financial_loan": "P1",
    "documents": "P2",
    "english_scores": "P2",
    "schedule": "P2",
    "faq": "P2",
    "other": "P2",
}

PRIORITY_ORDER = {
    "P0": 0,
    "P1": 1,
    "P2": 2,
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def load_verified(name, filename, expected):
    path = BASE / filename

    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    actual = sha256(raw)

    if actual != expected:
        raise ValueError(
            f"{name}: SHA-256 불일치\n"
            f"예상: {expected}\n실제: {actual}"
        )

    data = json.loads(raw.decode("utf-8"))

    if data.get("program_id") != "US-WEST-01":
        raise ValueError(f"{name}: program_id 불일치")

    if data.get("notice_period") != "2026_second_half":
        raise ValueError(f"{name}: 모집 회차 불일치")

    for key in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
    ):
        if data.get(key) is not False:
            raise ValueError(
                f"{name}: 보호 상태 오류: {key}"
            )

    return data


def compact(text):
    return re.sub(
        r"\s+", "", str(text)
    ).casefold()


def classify(title, detail):
    combined = compact(
        f"{title} {detail}"
    )

    matches = []

    for topic, keywords in TOPICS.items():
        if any(
            compact(keyword) in combined
            for keyword in keywords
        ):
            matches.append(topic)

    return matches or ["other"]


def priority_for(topics):
    return min(
        (TOPIC_PRIORITY[t] for t in topics),
        key=lambda p: PRIORITY_ORDER[p],
    )


def make_issue(
    record_id,
    origin,
    title,
    detail,
    original,
):
    topics = classify(title, detail)

    return {
        "record_id": record_id,
        "origin": origin,
        "title": title,
        "detail": detail,
        "suggested_topics": topics,
        "suggested_priority": priority_for(topics),
        "original_record": original,
        "duplicate_decision": None,
        "resolved": False,
        "semantic_review_completed": False,
        "human_reviewer": None,
        "review_notes": None,
        "validation_status": "needs_review",
    }


def save_new_or_verify(path, data):
    raw = (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                "기존 파일의 내용이 다릅니다. "
                f"덮어쓰지 않음: {path}"
            )
        status = "EXISTS_VERIFIED"

    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"

    return status, sha256(raw)


print("===== STEP 64-63 WEST 의미 검토 이슈 통합 =====")

# 1. 입력 검증
data = {}

for name, (filename, expected_sha) in INPUTS.items():
    data[name] = load_verified(
        name,
        filename,
        expected_sha,
    )
    print(f"[PASS] 입력 SHA-256: {name}")

register = data["register"]
visa = data["visa"]
academic = data["academic"]
documents = data["documents"]

if len(register["original_issues"]) != 16:
    raise ValueError("기존 이슈 16건 불일치")

if len(register["additional_field_review_tasks"]) != 7:
    raise ValueError("추가 필드 작업 7건 불일치")

if len(visa["review_items"]) != 4:
    raise ValueError("비자·인턴십 항목 4개 불일치")

if len(academic["manual_review_issues"]) != 5:
    raise ValueError("학적·재정지원 이슈 5건 불일치")

if len(documents["manual_review_issues"]) != 4:
    raise ValueError("서류·성적 이슈 4건 불일치")

print("[PASS] 단계별 이슈 및 검토 항목 개수")


# 2. 기존 이슈 16건 보존
issues = []

for item in register["original_issues"]:
    issues.append(
        make_issue(
            record_id=item["record_id"],
            origin="step_64_58",
            title=item["title"],
            detail=item.get("detail", ""),
            original=item,
        )
    )


# 3. STEP 64-61 신규 이슈 5건
for index, item in enumerate(
    academic["manual_review_issues"], 1
):
    issues.append(
        make_issue(
            record_id=f"WEST-H2-ACADEMIC-{index:02d}",
            origin="step_64_61",
            title=item["issue"],
            detail=item.get("details", ""),
            original=item,
        )
    )


# 4. STEP 64-62 신규 이슈 4건
for index, item in enumerate(
    documents["manual_review_issues"], 1
):
    issues.append(
        make_issue(
            record_id=f"WEST-H2-DOCUMENTS-{index:02d}",
            origin="step_64_62",
            title=item["issue"],
            detail=item.get("details", ""),
            original=item,
        )
    )

if len(issues) != 25:
    raise ValueError(
        f"전체 이슈 수 오류: {len(issues)}"
    )

ids = [x["record_id"] for x in issues]

if len(ids) != len(set(ids)):
    raise ValueError("이슈 ID 중복")


# 5. STEP 64-60의 법률·인턴십 검토 항목은
# 신규 이슈로 중복 생성하지 않고 별도 연결
legal_review_tasks = []

for name, item in visa["review_items"].items():
    legal_review_tasks.append({
        "task_id": f"WEST-H2-VISA-{name}",
        "field": name,
        "related_faq": item.get("related_faq", []),
        "evidence": item.get("evidence", []),
        "review_status": "needs_review",
        "legal_review_completed": False,
    })


# 6. 동일 제목 후보 그룹 수집
# 정확히 같은 제목이라도 자동 병합하지 않음
title_groups = defaultdict(list)

for item in issues:
    title_groups[
        compact(item["title"])
    ].append(item["record_id"])

same_title_candidates = [
    members
    for members in title_groups.values()
    if len(members) > 1
]


# 7. 주제별 분류
topic_counts = Counter()
priority_counts = Counter()

for item in issues:
    priority_counts[
        item["suggested_priority"]
    ] += 1

    for topic in item["suggested_topics"]:
        topic_counts[topic] += 1

issues.sort(
    key=lambda item: (
        PRIORITY_ORDER[item["suggested_priority"]],
        item["record_id"],
    )
)


# 8. 기존 필드 작업 7개 유지
field_tasks = register["additional_field_review_tasks"]

# 결과 생성
result = {
    "dataset_type": "west_semantic_review_registry",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_input_sha256": {
        name: expected_sha
        for name, (_, expected_sha) in INPUTS.items()
    },
    "original_issue_count": 16,
    "new_academic_issue_count": 5,
    "new_documents_issue_count": 4,
    "total_issue_records": 25,
    "unique_issue_count_after_manual_deduplication": None,
    "issues": issues,
    "same_title_candidates": same_title_candidates,
    "suggested_priority_counts": dict(priority_counts),
    "suggested_topic_counts_nonexclusive": dict(topic_counts),
    "additional_field_tasks": field_tasks,
    "visa_internship_review_tasks": legal_review_tasks,
    "issues_automatically_resolved": 0,
    "issues_automatically_merged": 0,
    "semantic_review_completed": False,
    "legal_review_completed": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_semantic_review_registry_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "issue_records": len(issues),
    "original_issue_records": 16,
    "new_issue_records": 9,
    "visa_internship_review_tasks": len(
        legal_review_tasks
    ),
    "additional_field_tasks": len(field_tasks),
    "same_title_candidate_groups": len(
        same_title_candidates
    ),
    "priority_counts": dict(priority_counts),
    "issues_deleted": 0,
    "issues_automatically_resolved": 0,
    "input_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 9. 결과 저장
status, result_sha = save_new_or_verify(
    OUTPUT, result
)

audit["result_sha256"] = result_sha

audit_status, audit_sha = save_new_or_verify(
    AUDIT, audit
)


# 10. 입력 및 결과 무결성 재검증
for name, (filename, expected_sha) in INPUTS.items():
    current = sha256(
        (BASE / filename).read_bytes()
    )

    if current != expected_sha:
        raise ValueError(
            f"검사 중 입력 변경: {name}"
        )

if sha256(OUTPUT.read_bytes()) != result_sha:
    raise ValueError("결과 파일 무결성 오류")

if sha256(AUDIT.read_bytes()) != audit_sha:
    raise ValueError("감사 파일 무결성 오류")


print("\n===== STEP 64-63 최종 결과 =====")
print("기존 이슈:", 16)
print("신규 이슈:", 9)
print("이슈 기록 합계:", len(issues))
print(
    "동일 제목 후보 그룹:",
    len(same_title_candidates)
)
print(
    "비자·인턴십 별도 검토:",
    len(legal_review_tasks)
)
print("기존 필드 검토 작업:", len(field_tasks))

for priority in ("P0", "P1", "P2"):
    print(
        f"제안 우선순위 {priority}:",
        priority_counts[priority]
    )

print(f"[PASS] {status}: {OUTPUT.name}")
print("SHA-256:", result_sha)

print(f"[PASS] {audit_status}: {AUDIT.name}")
print("SHA-256:", audit_sha)

print("의미상 중복 수동 판정: 미완료")
print("정책 의미 최종 승인: 미완료")
print("원본 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")

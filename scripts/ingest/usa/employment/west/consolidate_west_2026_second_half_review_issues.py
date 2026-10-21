
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT / "data/processed/usa/employment/west/2026_second_half"
)

INPUTS = {
    "eligibility": (
        "west_2026_second_half_eligibility_source_verified.json",
        "b54407e89beebcd1218415d29e5a6c20263fecd41105b7c779ea8c98ca42b5ba",
        3,
    ),
    "application": (
        "west_2026_second_half_application_source_verified.json",
        "d2bbc9e8d254f70441de6ac1c2fdf0ed70a405ddd72ad378b3013fb9e258ee31",
        3,
    ),
    "financial": (
        "west_2026_second_half_financial_source_verified.json",
        "8d381edebe88569b087050cedcd8046f5adae0dd30c4b0e19ea30372f657ca3a",
        4,
    ),
    "selection": (
        "west_2026_second_half_selection_faq_review.json",
        "a2b8e320f65228e1650439f4663a23c0f6608db2c9edae52aee2f61dbce5c505",
        6,
    ),
    "remaining_fields": (
        "west_2026_second_half_remaining_fields_review.json",
        "8c13b18c8618a943d77ea4a25c1f07f997005effd42d2966414b35924a72aa50",
        None,
    ),
    "integrated_audit": (
        "west_2026_second_half_integrated_audit.json",
        "a1e29f60f5e73af7946d72f85418af5e0cdb5cb5ec8a03f0fee6977869893ec7",
        None,
    ),
}

OUTPUT = BASE / "west_2026_second_half_review_register.json"
AUDIT = BASE / "west_2026_second_half_review_register_audit.json"

# 이 분류는 검토 작업을 배분하기 위한 분류이며,
# 동일한 법적 조건이라는 판정이 아니다.
TOPIC_KEYWORDS = {
    "visa_and_internship": [
        "J-1", "비자", "본국거주", "웨이버", "인턴십",
    ],
    "academic_and_graduation": [
        "학적", "졸업", "수료", "지원 자격", "선발 회차",
    ],
    "finance_and_loans": [
        "지원구간", "지원금", "환율", "대출", "지급",
        "환수", "참가비",
    ],
    "documents_and_procedures": [
        "증빙", "서류", "마감일", "일정", "등록번호",
    ],
    "english_scores": [
        "TOEIC", "Speaking", "ACTFL", "어학성적",
    ],
    "faq_semantics": [
        "FAQ", "문답", "답변",
    ],
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_verified(name, filename, expected_sha):
    path = BASE / filename

    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    actual = sha256(raw)

    if actual != expected_sha:
        raise ValueError(
            f"{name}: SHA-256 불일치\n"
            f"예상: {expected_sha}\n실제: {actual}"
        )

    data = json.loads(raw.decode("utf-8"))

    if data.get("program_id") != "US-WEST-01":
        raise ValueError(f"{name}: 프로그램 ID 불일치")

    if data.get("notice_period") != "2026_second_half":
        raise ValueError(f"{name}: 모집 회차 불일치")

    for key in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
    ):
        if data.get(key) is not False:
            raise ValueError(f"{name}: 보호 설정 오류 - {key}")

    return data


def normalized(text):
    return re.sub(r"\s+", "", text).casefold()


def classify(text):
    matched = [
        topic
        for topic, words in TOPIC_KEYWORDS.items()
        if any(
            normalized(word) in normalized(text)
            for word in words
        )
    ]
    return matched or ["other"]


def write_new_or_verify(path, obj):
    raw = (
        json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 결과와 다름. 덮어쓰지 않음: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as handle:
            handle.write(raw)
        status = "CREATED"

    return status, sha256(raw)


print("===== STEP 64-58 WEST 검토 이슈 통합 =====")

data = {}

for name, (filename, expected_sha, _) in INPUTS.items():
    data[name] = read_verified(
        name, filename, expected_sha
    )
    print(f"[PASS] SHA-256 및 보호 설정: {name}")

# 1. 이전 단계의 이슈 16건 수집
records = []
issue_counts = {}

for name in ("eligibility", "application", "financial", "selection"):
    issues = data[name].get("manual_review_issues", [])
    expected_count = INPUTS[name][2]

    if len(issues) != expected_count:
        raise ValueError(
            f"{name}: 예상 이슈 {expected_count}, 실제 {len(issues)}"
        )

    issue_counts[name] = len(issues)

    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict) or not issue.get("issue"):
            raise ValueError(
                f"{name}: 이슈 형식 오류 #{index}"
            )

        title = issue["issue"]
        detail = (
            issue.get("details")
            or issue.get("note")
            or ""
        )

        records.append({
            "record_id": f"WEST-H2-{name.upper()}-{index:02d}",
            "origin_step": name,
            "origin_issue_index": index,
            "title": title,
            "detail": detail,
            "source_issue": issue,
            "suggested_topics": classify(title + " " + detail),
            "review_status": "needs_review",
            "resolved": False,
            "human_duplicate_decision": None,
            "approved_for_user_answers": False,
        })

if len(records) != 16:
    raise ValueError("원본 이슈 16건이 아님")

print("[PASS] 기존 수동 검토 이슈 16건 보존")

# 2. 동일 제목 후보만 표시
# 원본 이슈는 삭제·병합하지 않는다.
by_title = defaultdict(list)

for record in records:
    by_title[normalized(record["title"])].append(
        record["record_id"]
    )

exact_title_groups = [
    ids for ids in by_title.values()
    if len(ids) > 1
]

# 3. 잔여 필드 7개 검토 항목 추가
remaining = data["remaining_fields"]["fields"]

if len(remaining) != 7:
    raise ValueError("잔여 필드 7개 불일치")

field_tasks = []

for field_name, item in sorted(remaining.items()):
    if item.get("validation_status") != "needs_review":
        raise ValueError(
            f"{field_name}: 예상 밖의 검토 상태"
        )

    field_tasks.append({
        "task_id": f"WEST-H2-FIELD-{field_name}",
        "field": field_name,
        "description": item.get("remaining_review"),
        "source_summary": item.get("source_summary"),
        "evidence": item.get("evidence", []),
        "review_status": "needs_review",
        "source_presence_verified": (
            item.get("source_presence_verified") is True
        ),
        "semantic_review_completed": False,
    })

# 4. 27개 필드의 상태 보존
integrated = data["integrated_audit"]

if integrated["original_policy_field_count"] != 27:
    raise ValueError("원래 필드 수 불일치")

if len(integrated["field_tracking"]) != 27:
    raise ValueError("필드 추적 목록 불일치")

# 5. 주제별 작업 분류
topic_counts = Counter()

for record in records:
    for topic in record["suggested_topics"]:
        topic_counts[topic] += 1

register = {
    "dataset_type": "west_manual_review_register",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_sha256": integrated["source_pdf_sha256"],
    "input_sha256": {
        name: value[1]
        for name, value in INPUTS.items()
    },
    "original_policy_field_count": 27,
    "fields_with_related_review_data": 27,
    "original_issue_count": len(records),
    "original_issues": records,
    "same_title_duplicate_candidates": exact_title_groups,
    "duplicate_candidates_automatically_merged": 0,
    "topic_counts_nonexclusive": dict(topic_counts),
    "additional_field_review_tasks": field_tasks,
    "additional_field_task_count": len(field_tasks),
    "all_issues_resolved": False,
    "semantic_review_completed": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_manual_review_register_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "original_issue_counts": issue_counts,
    "original_issue_count": len(records),
    "same_title_duplicate_group_count": len(exact_title_groups),
    "issues_deleted_or_merged": 0,
    "additional_field_tasks": len(field_tasks),
    "human_semantic_review_completed": False,
    "input_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

state, result_sha = write_new_or_verify(
    OUTPUT, register
)

audit["register_sha256"] = result_sha

audit_state, audit_sha = write_new_or_verify(
    AUDIT, audit
)

# 최종 원본 보호 확인
for name, (filename, expected_sha, _) in INPUTS.items():
    if sha256((BASE / filename).read_bytes()) != expected_sha:
        raise ValueError(f"{name}: 검사 도중 입력 변경")

print("\n===== STEP 64-58 최종 결과 =====")
print("원래 정책 필드:", 27)
print("근거 연결 필드:", 27)
print("보존된 수동 검토 이슈:", len(records))
print("추가 필드 검토 작업:", len(field_tasks))
print("동일 제목 중복 후보 그룹:", len(exact_title_groups))
print("자동 병합·삭제:", 0)

print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)

print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)

print("정책 의미 최종 승인: 미완료")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
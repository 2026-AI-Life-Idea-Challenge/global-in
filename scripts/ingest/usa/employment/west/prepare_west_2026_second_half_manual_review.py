
from pathlib import Path
from itertools import combinations
from difflib import SequenceMatcher
import csv
import hashlib
import io
import json
import re


# =====================================================
# STEP 64-64
# WEST 2026 H2 수동 의미 검수용 작업표 생성
#
# - 기존 이슈 보존
# - 유사 이슈는 후보로만 표시
# - 자동 해결/병합/승인 없음
# - 기존 입력 파일 수정 없음
# =====================================================

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT
    / "data/processed/usa/employment/west/2026_second_half"
)

SOURCE = (
    BASE
    / "west_2026_second_half_semantic_review_registry.json"
)

EXPECTED_SHA = (
    "4bb986ba36156642c52d8aaa6a5b14a"
    "752fe4db6349977a09c070d9449c83fee"
)

ISSUES_CSV = BASE / "west_2026_second_half_issue_review_sheet.csv"
PAIRS_CSV = BASE / "west_2026_second_half_similarity_candidates.csv"
TASKS_CSV = BASE / "west_2026_second_half_field_task_sheet.csv"
AUDIT_JSON = BASE / "west_2026_second_half_manual_review_sheet_audit.json"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def normalize(value):
    text = str(value or "").casefold()
    return re.sub(r"\s+", "", text)


def similarity(a, b):
    a = normalize(a)
    b = normalize(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None, a, b, autojunk=False
    ).ratio()


def check_input():
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    raw = SOURCE.read_bytes()

    if sha256(raw) != EXPECTED_SHA:
        raise ValueError(
            "STEP 64-63 입력 SHA-256 불일치"
        )

    data = json.loads(raw.decode("utf-8"))

    if data["program_id"] != "US-WEST-01":
        raise ValueError("program_id 불일치")

    if data["notice_period"] != "2026_second_half":
        raise ValueError("모집 회차 불일치")

    for flag in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
    ):
        if data.get(flag) is not False:
            raise ValueError(
                f"보호 설정 오류: {flag}"
            )

    if len(data["issues"]) != 25:
        raise ValueError("이슈 25건 불일치")

    if len(data["visa_internship_review_tasks"]) != 4:
        raise ValueError("비자 검토 작업 4개 불일치")

    if len(data["additional_field_tasks"]) != 7:
        raise ValueError("필드 검토 작업 7개 불일치")

    return data


def csv_bytes(headers, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=headers,
        extrasaction="ignore",
        lineterminator="\n",
    )

    writer.writeheader()
    writer.writerows(rows)

    # Excel에서 한글이 깨지지 않도록 BOM 추가
    return buffer.getvalue().encode("utf-8-sig")


def json_bytes(data):
    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")


def write_without_overwrite(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 파일과 내용이 달라 덮어쓰지 않음: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"

    return status, sha256(raw)


print("===== STEP 64-64 수동 검토 작업표 생성 =====")

data = check_input()
print("[PASS] STEP 64-63 SHA-256 및 보호 상태")

issues = data["issues"]


# -----------------------------------------------------
# 1. 전체 이슈 검토표
# -----------------------------------------------------

issue_rows = []

for item in issues:
    issue_rows.append({
        "record_id": item["record_id"],
        "origin": item["origin"],
        "priority": item["suggested_priority"],
        "topics": ", ".join(
            item["suggested_topics"]
        ),
        "title": item["title"],
        "detail": item.get("detail", ""),
        "duplicate_decision": "미검토",
        "duplicate_of": "",
        "source_review": "미검토",
        "policy_semantic_review": "미검토",
        "external_verification_required": "미검토",
        "reviewer_notes": "",
        "final_status": "needs_review",
    })

issue_headers = [
    "record_id",
    "origin",
    "priority",
    "topics",
    "title",
    "detail",
    "duplicate_decision",
    "duplicate_of",
    "source_review",
    "policy_semantic_review",
    "external_verification_required",
    "reviewer_notes",
    "final_status",
]


# -----------------------------------------------------
# 2. 유사 이슈 후보
# -----------------------------------------------------

candidate_pairs = []

for a, b in combinations(issues, 2):
    title_score = similarity(
        a["title"], b["title"]
    )

    combined_a = (
        a["title"] + " " + a.get("detail", "")
    )
    combined_b = (
        b["title"] + " " + b.get("detail", "")
    )

    content_score = similarity(
        combined_a, combined_b
    )

    common_topics = (
        set(a["suggested_topics"])
        & set(b["suggested_topics"])
    )

    # 점수는 검토 후보 정렬용이다.
    score = round(
        title_score * 0.6
        + content_score * 0.4,
        4,
    )

    if score < 0.25 and not (
        score >= 0.15 and common_topics
    ):
        continue

    candidate_pairs.append({
        "issue_a": a["record_id"],
        "issue_b": b["record_id"],
        "title_a": a["title"],
        "title_b": b["title"],
        "score": score,
        "shared_topics": ", ".join(
            sorted(common_topics)
        ),
        "same_origin": (
            "예" if a["origin"] == b["origin"]
            else "아니오"
        ),
        "manual_decision": "미검토",
        "reviewer_notes": "",
    })

candidate_pairs.sort(
    key=lambda row: (
        -row["score"],
        row["issue_a"],
        row["issue_b"],
    )
)

# 유사한 상위 30쌍만 별도 검토 대상으로 표시
candidate_pairs = candidate_pairs[:30]

pair_headers = [
    "issue_a",
    "issue_b",
    "title_a",
    "title_b",
    "score",
    "shared_topics",
    "same_origin",
    "manual_decision",
    "reviewer_notes",
]


# -----------------------------------------------------
# 3. 비자 및 기타 필드 검토 작업표
# -----------------------------------------------------

task_rows = []

for task in data["visa_internship_review_tasks"]:
    task_rows.append({
        "task_id": task["task_id"],
        "category": "visa_internship",
        "field": task["field"],
        "related_faq": ", ".join(
            str(n)
            for n in task.get("related_faq", [])
        ),
        "evidence_pages": ", ".join(
            str(ref.get("printed_page", ""))
            for ref in task.get("evidence", [])
        ),
        "review_required": "예",
        "reviewer_notes": "",
        "final_status": "needs_review",
    })

for task in data["additional_field_tasks"]:
    task_rows.append({
        "task_id": task["task_id"],
        "category": "remaining_policy_field",
        "field": task["field"],
        "related_faq": "",
        "evidence_pages": ", ".join(
            str(ref.get("printed_page", ""))
            for ref in task.get("evidence", [])
        ),
        "review_required": "예",
        "reviewer_notes": "",
        "final_status": "needs_review",
    })

task_headers = [
    "task_id",
    "category",
    "field",
    "related_faq",
    "evidence_pages",
    "review_required",
    "reviewer_notes",
    "final_status",
]


# -----------------------------------------------------
# 4. 원본 검증과 저장
# -----------------------------------------------------

outputs = [
    (
        ISSUES_CSV,
        csv_bytes(issue_headers, issue_rows),
    ),
    (
        PAIRS_CSV,
        csv_bytes(pair_headers, candidate_pairs),
    ),
    (
        TASKS_CSV,
        csv_bytes(task_headers, task_rows),
    ),
]

audit = {
    "dataset_type": "west_manual_review_sheet_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "input_sha256": EXPECTED_SHA,
    "issue_count": len(issue_rows),
    "similarity_candidate_count": len(candidate_pairs),
    "separate_task_count": len(task_rows),
    "candidate_pairs_are_not_confirmed_duplicates": True,
    "human_review_completed": False,
    "issues_auto_resolved": 0,
    "issues_auto_merged": 0,
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 쓰기 전에 기존 결과 충돌을 전부 확인
planned = outputs + [
    (AUDIT_JSON, json_bytes(audit))
]

for path, raw in planned:
    if path.exists() and path.read_bytes() != raw:
        raise FileExistsError(
            f"기존 출력 파일과 충돌: {path}"
        )

for path, raw in planned:
    status, digest = write_without_overwrite(
        path, raw
    )
    print(f"[PASS] {status}: {path.name}")
    print("SHA-256:", digest)

if sha256(SOURCE.read_bytes()) != EXPECTED_SHA:
    raise ValueError("입력 파일이 실행 중 변경됨")

print("\n===== STEP 64-64 최종 결과 =====")
print("검토 이슈:", len(issue_rows))
print(
    "유사 이슈 후보:",
    len(candidate_pairs)
)
print("별도 검토 작업:", len(task_rows))
print("중복 자동 확정:", 0)
print("이슈 자동 해결:", 0)
print("원본 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
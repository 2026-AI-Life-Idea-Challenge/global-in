
from pathlib import Path
import hashlib
import json


# =====================================================
# STEP 64-68
# WEST 2026 H2 기관 간 교차 검토 결과 정리
#
# 기존 원본·검토 결과 수정 금지
# 자동 해결·자동 승인·임베딩 금지
# =====================================================

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT / "data/processed/usa/employment/west/2026_second_half"
)

INPUT = BASE / "west_2026_second_half_cross_agency_review.json"

OUTPUT = BASE / "west_2026_second_half_cross_agency_comparison.json"
AUDIT = BASE / "west_2026_second_half_cross_agency_comparison_audit.json"

INPUT_SHA = (
    "401086bfec485efb0beb788eade8489"
    "f6fa5c382210a8056bc329d26b95aa6e6"
)

# 공식 웹페이지에서 확인한 사실을 별도 메모로 기록한다.
# 이 스크립트는 네트워크에 접속하지 않으며
# HTML 원문 보관이나 원문 해시 검증을 수행하지 않는다.

COMPARISONS = {
    "WEST-H2-CROSS-01": {
        "comparison_status": "consistent",
        "finding": (
            "한국장학재단의 지원구간 확인용 대출신청과 "
            "실제 대출 실행은 서로 다른 절차임."
        ),
        "confirmed_details": {
            "bracket_application_required": True,
            "loan_execution_is_separate": True,
            "execution_automatically_approved": False,
        },
        "remaining_question": (
            "개별 신청자의 대출 실행 가능 여부는 "
            "재단 심사 조건에 따라 별도 확인."
        ),
    },

    "WEST-H2-CROSS-02": {
        "comparison_status": "different_procedures_confirmed",
        "finding": (
            "WEST 일반 지원, 한국장학재단 대출신청, "
            "대출 관련 서류제출은 서로 다른 마감일을 가짐."
        ),
        "confirmed_details": {
            "kosaf_application_start": "2026-07-06T09:00",
            "kosaf_application_deadline": "2026-08-05T17:00",
            "kosaf_document_deadline": "2026-08-05T18:00",
            "loan_execution_start": "2026-10-16",
            "loan_execution_end": "2026-10-27",
        },
        "remaining_question": (
            "일정 변경 공지 여부는 별도 확인 필요."
        ),
    },

    "WEST-H2-CROSS-03": {
        "comparison_status": "consistent",
        "finding": (
            "한국장학재단은 지원구간 산정 신청 대상으로 "
            "재학생·휴학생·초과학기자·수료자를 안내하며, "
            "졸업생은 해당 대출신청에서 제외함."
        ),
        "confirmed_details": {
            "bracket_application_statuses": [
                "enrolled",
                "leave_of_absence",
                "extra_semester",
                "course_completed",
            ],
            "graduates_excluded_from_kosaf_application": True,
        },
        "remaining_question": (
            "실제 대출 실행 가능 학적은 신청 가능 학적과 "
            "별도로 검토해야 함."
        ),
    },

    "WEST-H2-CROSS-04": {
        "comparison_status": "partially_confirmed",
        "finding": (
            "한국장학재단은 기존 지원구간 산정 이력이 있는 "
            "졸업생의 지원구간 통지서 별도 제출을 안내함."
        ),
        "confirmed_details": {
            "graduate_prior_bracket_notice": True,
            "all_alternative_documents_cross_verified": False,
        },
        "remaining_question": (
            "기존 산정 이력이 없는 졸업생의 대체 증빙과 "
            "지원액 산정 조건은 국립국제교육원 공고를 "
            "기준으로 별도 검토해야 함."
        ),
    },

    "WEST-H2-CROSS-05": {
        "comparison_status": "confirmed_by_kosaf",
        "finding": (
            "한국장학재단은 학자금 지원구간 산정을 위해 "
            "부모 또는 배우자의 가구원 정보제공 동의를 "
            "필수 절차로 안내함."
        ),
        "confirmed_details": {
            "family_consent_required": True,
            "document_submission_separate": True,
        },
        "remaining_question": (
            "특수한 가족관계 또는 정보제공 동의가 "
            "어려운 경우의 세부 처리는 재단 확인 필요."
        ),
    },

    "WEST-H2-CROSS-06": {
        "comparison_status": "separate_procedure_confirmed",
        "finding": (
            "재외국민전형 입학자는 국외 소득·재산 "
            "신고와 관련된 별도 절차가 있을 수 있음."
        ),
        "confirmed_details": {
            "special_admission_procedure_exists": True,
            "applies_to_all_overseas_residents": False,
        },
        "remaining_question": (
            "특별전형 해당 여부와 개인별 신고 의무는 "
            "한국장학재단 안내에 따라 확인."
        ),
    },

    "WEST-H2-CROSS-07": {
        "comparison_status": "confirmed_by_kosaf",
        "finding": (
            "한국장학재단은 합격자 발표 이전까지 "
            "확정된 지원구간을 기준으로 지원하며, "
            "WEST는 지원구간 최신화 신청기간에 "
            "제약이 있을 수 있다고 안내함."
        ),
        "confirmed_details": {
            "bracket_finalization_before_result": True,
            "personal_support_amount_verified": False,
        },
        "remaining_question": (
            "개별 지원금 액수와 변동 가능성은 "
            "운영기관 및 재단 안내로 별도 확인."
        ),
    },
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(data):
    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")


def write_once(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 파일과 내용 불일치: {path}"
            )
        state = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        state = "CREATED"

    return state, sha256(raw)


print("===== STEP 64-68 기관 간 교차 검토 결과 =====")

if not INPUT.is_file():
    raise FileNotFoundError(INPUT)

raw_input = INPUT.read_bytes()

if sha256(raw_input) != INPUT_SHA:
    raise ValueError("STEP 64-67 SHA-256 불일치")

source = json.loads(raw_input.decode("utf-8"))

assert source["program_id"] == "US-WEST-01"
assert source["notice_period"] == "2026_second_half"
assert source["task_count"] == 7
assert source["approved_for_user_answers"] is False
assert source["approved_for_embedding"] is False
assert source["automatic_eligibility_rules_enabled"] is False

print("[PASS] STEP 64-67 원본 검증")

tasks = source["cross_agency_review_tasks"]

source_task_ids = {task["id"] for task in tasks}

if source_task_ids != set(COMPARISONS):
    raise ValueError(
        "7개 교차 검토 항목의 ID 불일치"
    )

# 출처별 확인 사항을 URL 단위로 기록한다.
official_references = {
    "niied_notice": {
        "url": source["official_sources"]["niied_notice"]["url"],
        "source_type": "official_historical_notice",
        "content_sha256": None,
    },
    "kosaf_notice": {
        "url": source["official_sources"]["kosaf_notice"]["url"],
        "source_type": "official_dated_notice",
        "content_sha256": None,
    },
    "kosaf_loan_guide": {
        "url": source["official_sources"]["kosaf_loan_guide"]["url"],
        "source_type": "official_web_guide",
        "content_sha256": None,
    },
}

results = []

for task in tasks:
    task_id = task["id"]
    comparison = COMPARISONS[task_id]

    results.append({
        "task_id": task_id,
        "topic": task["topic"],
        "source_ids": task["source_ids"],
        "comparison_status": comparison["comparison_status"],
        "finding": comparison["finding"],
        "confirmed_details": comparison["confirmed_details"],
        "remaining_question": comparison["remaining_question"],
        "record_type": "official_source_review_note",
        "external_raw_content_archived": False,
        "review_status": "needs_review",
        "policy_semantics_approved": False,
        "individual_eligibility_determined": False,
    })

    print(
        f"[PASS] {task_id}: "
        f"{comparison['comparison_status']}"
    )

comparison_result = {
    "dataset_type": "west_cross_agency_comparison",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "input_sha256": INPUT_SHA,
    "reference_checked_date": "2026-10-21",
    "official_references": official_references,
    "results": results,
    "result_count": len(results),
    "external_source_snapshots_archived": False,
    "external_source_content_hashes_verified": False,
    "all_manual_issues_resolved": False,
    "final_semantic_review_completed": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_cross_agency_comparison_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "input_sha256": INPUT_SHA,
    "comparison_result_count": len(results),
    "automatically_resolved_issues": 0,
    "independent_source_hashes_verified": False,
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

result_raw = encode(comparison_result)
result_sha = sha256(result_raw)

audit["result_sha256"] = result_sha
audit_raw = encode(audit)

# 쓰기 전에 기존 파일 충돌 확인
for path, data in (
    (OUTPUT, result_raw),
    (AUDIT, audit_raw),
):
    if path.exists() and path.read_bytes() != data:
        raise FileExistsError(
            f"기존 결과가 달라 저장 중단: {path}"
        )

state, result_sha = write_once(
    OUTPUT, result_raw
)

audit_state, audit_sha = write_once(
    AUDIT, audit_raw
)

# 입력 무결성 재검사
if sha256(INPUT.read_bytes()) != INPUT_SHA:
    raise ValueError("실행 중 입력 파일 변경 감지")

print("\n===== STEP 64-68 최종 결과 =====")
print("교차 검토 작업:", len(results))
print("자동 해결 이슈:", 0)
print("외부 원문 해시 검증:", "미완료")

print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)

print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)

print("개인별 대출 판정: 비활성화")
print("답변·임베딩 승인: False")
print("Git commit·push: 미실행")
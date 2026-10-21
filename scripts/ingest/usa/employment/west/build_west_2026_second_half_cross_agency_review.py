
from pathlib import Path
import hashlib
import json

# STEP 64-67
# WEST 2026 H2 기관 간 정책 교차 검수 기록
# 기존 파일 수정·자동 승인·임베딩 없음

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa/employment/west/2026_second_half"

INPUTS = {
    "registry": (
        "west_2026_second_half_semantic_review_registry.json",
        "4bb986ba36156642c52d8aaa6a5b14a752fe4db6349977a09c070d9449c83fee",
    ),
    "pdf_findings": (
        "west_2026_second_half_pdf_findings.json",
        "76aff3a860078f75bc5cf5ac26865f481fdcf69a6f20183c71648994a9b41601",
    ),
    "academic_finance": (
        "west_2026_second_half_academic_finance_review.json",
        "c3cb750badb91b75e25746c6bf1ccb18e39a8302a3d5ccfed3b5a03577d48925",
    ),
}

OUTPUT = BASE / "west_2026_second_half_cross_agency_review.json"
AUDIT = BASE / "west_2026_second_half_cross_agency_audit.json"

OFFICIAL_SOURCES = {
    "niied_notice": {
        "agency": "국립국제교육원",
        "published_date": "2026-06-26",
        "url": "https://www.niied.go.kr/web/main/nid/niied_board/5749",
        "description": "2026년 하반기 WEST 참가자 모집 공고",
    },
    "kosaf_notice": {
        "agency": "한국장학재단",
        "published_date": "2026-06-30",
        "url": "https://www.kosaf.go.kr/ko/notice.do?mode=view&page=3&seqNo=21036",
        "description": "2026년 하반기 WEST 어학연수비 대출신청 안내",
    },
    "kosaf_loan_guide": {
        "agency": "한국장학재단",
        "published_date": None,
        "url": "https://www.kosaf.go.kr/ko/tuition.do?pg=PTHDWestAply_01M&ttab1=2",
        "description": "WEST 어학연수비 대출제도 안내",
    },
}

# 공식 웹페이지에서 확인한 내용의 검토 메모.
# 이 코드 자체가 웹페이지를 다시 읽거나 검증하지는 않는다.
TASKS = [
    {
        "id": "WEST-H2-CROSS-01",
        "topic": "support_bracket_application",
        "source_ids": ["niied_notice", "kosaf_notice"],
        "observed_official_guidance": (
            "WEST 지원구간 확인을 위한 한국장학재단 "
            "어학연수비 대출신청이 요구되며, "
            "실제 대출 실행은 추후 합격자 대상으로 안내됨."
        ),
        "review_question": (
            "지원구간 확인 신청과 실제 대출 실행이 "
            "서로 다른 절차로 보존되어 있는가?"
        ),
        "review_status": "manual_compare_pending",
    },
    {
        "id": "WEST-H2-CROSS-02",
        "topic": "loan_application_period",
        "source_ids": ["niied_notice", "kosaf_notice"],
        "observed_official_guidance": (
            "한국장학재단 신청기간은 2026-07-06 09:00부터 "
            "2026-08-05 17:00까지. 서류 제출은 "
            "2026-08-05 18:00까지로 별도 안내됨."
        ),
        "review_question": (
            "WEST 일반 지원기간과 재단 신청기간, "
            "서류 제출 마감시각을 구분했는가?"
        ),
        "review_status": "manual_compare_pending",
    },
    {
        "id": "WEST-H2-CROSS-03",
        "topic": "academic_status",
        "source_ids": ["niied_notice", "kosaf_notice", "kosaf_loan_guide"],
        "observed_official_guidance": (
            "재단은 지원구간 산정 가능 대상으로 재학생, "
            "휴학생, 초과학기자, 수료자를 안내하며 "
            "졸업생은 재단 신청에서 제외함."
        ),
        "review_question": (
            "지원구간 신청 가능 유형과 "
            "실제 대출 실행 가능 유형을 혼동하지 않았는가?"
        ),
        "review_status": "manual_compare_pending",
    },
    {
        "id": "WEST-H2-CROSS-04",
        "topic": "graduate_evidence",
        "source_ids": ["niied_notice", "kosaf_notice"],
        "observed_official_guidance": (
            "졸업생은 기존 학자금 지원구간 산정내역이 있으면 "
            "지원구간 통지서를 발급해 국립국제교육원에 "
            "별도로 제출하도록 안내됨."
        ),
        "review_question": (
            "기존 산정내역이 없는 졸업생의 증빙 분기는 "
            "국립국제교육원 공고와 일치하는가?"
        ),
        "review_status": "manual_compare_pending",
    },
    {
        "id": "WEST-H2-CROSS-05",
        "topic": "family_information_consent",
        "source_ids": ["kosaf_notice"],
        "observed_official_guidance": (
            "지원구간 산정을 위해 가구원 정보제공 동의가 "
            "필요하며, 신청자 상황별 제출 절차가 안내됨."
        ),
        "review_question": (
            "정보제공 동의 누락·서류 미제출의 영향을 "
            "지원구간 심사와 대출 실행으로 구분했는가?"
        ),
        "review_status": "manual_compare_pending",
    },
    {
        "id": "WEST-H2-CROSS-06",
        "topic": "overseas_income_reporting",
        "source_ids": ["niied_notice", "kosaf_notice"],
        "observed_official_guidance": (
            "재외국민전형 입학자의 국외 소득·재산 신고는 "
            "일반 지원구간 산정 절차와 다를 수 있음."
        ),
        "review_question": (
            "특별전형 관련 예외를 모든 해외 거주자에게 "
            "일률적으로 적용하지 않는가?"
        ),
        "review_status": "manual_compare_pending",
    },
    {
        "id": "WEST-H2-CROSS-07",
        "topic": "support_bracket_finalization",
        "source_ids": ["niied_notice", "kosaf_notice"],
        "observed_official_guidance": (
            "한국장학재단은 WEST 사업 특성상 "
            "지원구간 최신화 신청기간에 제약이 있을 수 있고 "
            "합격자 발표 전 확정된 구간으로 지원한다고 안내함."
        ),
        "review_question": (
            "지원구간 확정 시점과 개별 지원액 산정의 "
            "차이를 보존했는가?"
        ),
        "review_status": "manual_compare_pending",
    },
]


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def load_verified(name, filename, expected):
    path = BASE / filename
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    if sha256(raw) != expected:
        raise ValueError(f"{name}: SHA-256 불일치")

    data = json.loads(raw.decode("utf-8"))

    if data.get("program_id") != "US-WEST-01":
        raise ValueError(f"{name}: 프로그램 ID 불일치")

    if data.get("notice_period") != "2026_second_half":
        raise ValueError(f"{name}: 모집 회차 불일치")

    for flag in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
    ):
        if data.get(flag) is not False:
            raise ValueError(f"{name}: 보호 설정 오류: {flag}")

    return data


def encoded(obj):
    return (
        json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def save_once(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"출력 파일 충돌: {path}")
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"

    return status, sha256(raw)


print("===== STEP 64-67 WEST 기관 간 교차 검수 준비 =====")

data = {}

for name, (filename, expected) in INPUTS.items():
    data[name] = load_verified(name, filename, expected)
    print(f"[PASS] 입력 SHA-256 및 보호 상태: {name}")

if len(data["registry"]["issues"]) != 25:
    raise ValueError("원본 이슈 25건 불일치")

if len(data["pdf_findings"]["findings"]) != 3:
    raise ValueError("PDF 대조 결과 3건 불일치")

if len(TASKS) != 7:
    raise ValueError("교차 검토 작업 수 불일치")

if len({item["id"] for item in TASKS}) != len(TASKS):
    raise ValueError("교차 검토 작업 ID 중복")

for task in TASKS:
    if not set(task["source_ids"]).issubset(OFFICIAL_SOURCES):
        raise ValueError(f"{task['id']}: 알 수 없는 출처")

result = {
    "dataset_type": "west_cross_agency_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_inputs_sha256": {
        name: expected
        for name, (_, expected) in INPUTS.items()
    },
    "official_sources": OFFICIAL_SOURCES,
    "cross_agency_review_tasks": TASKS,
    "task_count": len(TASKS),
    "external_pages_downloaded_by_script": False,
    "external_page_hashes_verified": False,
    "manual_cross_agency_review_completed": False,
    "individual_loan_eligibility_determined": False,
    "current_policy_verified": False,
    "issues_automatically_resolved": 0,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_cross_agency_review_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "input_sha256": result["source_inputs_sha256"],
    "official_source_count": len(OFFICIAL_SOURCES),
    "cross_agency_task_count": len(TASKS),
    "cross_agency_tasks_completed": 0,
    "external_source_content_archived": False,
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

result_raw = encoded(result)
result_sha = sha256(result_raw)
audit["result_sha256"] = result_sha
audit_raw = encoded(audit)

# 기존 출력 충돌은 쓰기 전에 확인
for path, raw in (
    (OUTPUT, result_raw),
    (AUDIT, audit_raw),
):
    if path.exists() and path.read_bytes() != raw:
        raise FileExistsError(f"기존 출력과 충돌: {path}")

state, result_sha = save_once(OUTPUT, result_raw)
audit_state, audit_sha = save_once(AUDIT, audit_raw)

for name, (filename, expected) in INPUTS.items():
    if sha256((BASE / filename).read_bytes()) != expected:
        raise ValueError(f"입력 변경 감지: {name}")

print("\n===== STEP 64-67 최종 결과 =====")
print("공식 기관 출처:", len(OFFICIAL_SOURCES))
print("교차 검토 작업:", len(TASKS))
print("자동 해결 이슈:", 0)
print("외부 자료 원문 보관:", "미완료")
print("개인별 대출 판정:", "비활성화")
print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)
print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)
print("답변·임베딩 승인: False")
print("Git commit·push: 미실행")
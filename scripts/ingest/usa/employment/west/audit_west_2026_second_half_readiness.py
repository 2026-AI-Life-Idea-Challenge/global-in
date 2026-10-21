
from pathlib import Path
from collections import Counter
import hashlib
import json


# ============================================================
# STEP 64-69
# WEST 2026년 하반기 검수 상태 통합 감사
#
# 원본 및 기존 결과 변경 금지
# 서비스 답변·임베딩·자동 자격 판정 비활성화
# Git commit/push 수행하지 않음
# ============================================================

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT
    / "data/processed/usa/employment/west/2026_second_half"
)

PDF = (
    ROOT
    / "data/raw/usa/employment/west/2026_second_half"
    / "west_2026_second_half_notice.pdf"
)

INPUTS = {
    "registry": (
        "west_2026_second_half_semantic_review_registry.json",
        "4bb986ba36156642c52d8aaa6a5b14a752fe4db6349977a09c070d9449c83fee",
    ),
    "pdf_findings": (
        "west_2026_second_half_pdf_findings.json",
        "76aff3a860078f75bc5cf5ac26865f481fdcf69a6f20183c71648994a9b41601",
    ),
    "cross_agency": (
        "west_2026_second_half_cross_agency_comparison.json",
        "8ed7ff07eb016e8277d90a203f80b935c1fe201ea00c429d7571cea444c7b1f6",
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

PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

OUTPUT = BASE / "west_2026_second_half_readiness_audit.json"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_verified(path, expected):
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    actual = sha256(raw)

    if actual != expected:
        raise ValueError(
            f"SHA-256 불일치: {path}\n"
            f"예상: {expected}\n"
            f"실제: {actual}"
        )

    return json.loads(raw.decode("utf-8"))


def check_protection(name, data):
    if data.get("program_id") != "US-WEST-01":
        raise ValueError(f"{name}: program_id 오류")

    if data.get("notice_period") != "2026_second_half":
        raise ValueError(f"{name}: notice_period 오류")

    for key in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
    ):
        if data.get(key) is not False:
            raise ValueError(
                f"{name}: 차단 설정 오류 - {key}"
            )


def write_once(path, obj):
    raw = (
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 감사 파일과 내용 불일치: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"

    return status, sha256(raw)


print("===== STEP 64-69 WEST 전체 검수 상태 감사 =====")


# ------------------------------------------------------------
# 1. 원본 PDF 검사
# ------------------------------------------------------------

if not PDF.is_file():
    raise FileNotFoundError(PDF)

if sha256(PDF.read_bytes()) != PDF_SHA:
    raise ValueError("공식 원본 PDF SHA-256 불일치")

print("[PASS] 공식 PDF SHA-256")


# ------------------------------------------------------------
# 2. 단계별 결과 검사
# ------------------------------------------------------------

data = {}

for key, (filename, expected) in INPUTS.items():
    obj = read_verified(BASE / filename, expected)
    check_protection(key, obj)

    data[key] = obj

    print(
        f"[PASS] {key}: SHA-256 및 차단 설정"
    )


# ------------------------------------------------------------
# 3. 전체 이슈 추적
# ------------------------------------------------------------

registry = data["registry"]
findings = data["pdf_findings"]
cross = data["cross_agency"]
visa = data["visa"]
academic = data["academic"]
documents = data["documents"]

issues = registry["issues"]

if len(issues) != 25:
    raise ValueError("기존 이슈 25건 불일치")

issue_ids = [x["record_id"] for x in issues]

if len(issue_ids) != len(set(issue_ids)):
    raise ValueError("이슈 ID 중복")

if len(findings["findings"]) != 3:
    raise ValueError("PDF 대조 결과 3건 불일치")

if len(cross["results"]) != 7:
    raise ValueError("기관 간 교차 검토 7건 불일치")

if len(visa["review_items"]) != 4:
    raise ValueError("비자·인턴십 검토 4건 불일치")

if len(academic["review_items"]) != 7:
    raise ValueError("학적·재정 검토 7건 불일치")

if len(documents["review_items"]) != 5:
    raise ValueError("서류·성적 검토 5건 불일치")

if len(registry["additional_field_tasks"]) != 7:
    raise ValueError("잔여 필드 작업 7건 불일치")

print("[PASS] 단계별 검토 대상 개수")


# ------------------------------------------------------------
# 4. PDF 대조 결과와 이슈 연결
# ------------------------------------------------------------

finding_links = {}

for finding in findings["findings"]:
    fid = finding["finding_id"]

    for issue_id in finding["issue_ids"]:
        if issue_id not in issue_ids:
            raise ValueError(
                f"존재하지 않는 이슈 ID: {issue_id}"
            )

        finding_links.setdefault(
            issue_id, []
        ).append(fid)

# 연결만 되었을 뿐, 해결 완료로 판정하지 않음.
issue_tracking = []

for issue in issues:
    issue_id = issue["record_id"]
    linked = finding_links.get(issue_id, [])

    issue_tracking.append({
        "record_id": issue_id,
        "title": issue["title"],
        "origin": issue["origin"],
        "suggested_priority": (
            issue["suggested_priority"]
        ),
        "pdf_finding_ids": linked,
        "has_pdf_finding": bool(linked),
        "resolved": False,
        "review_status": "needs_review",
    })

linked_count = sum(
    bool(item["pdf_finding_ids"])
    for item in issue_tracking
)

unlinked_count = len(issues) - linked_count

if linked_count != 7:
    raise ValueError(
        f"PDF 연결 이슈 7건 예상, 실제 {linked_count}"
    )

print("[PASS] PDF 대조 결과 연결 이슈 7건")


# ------------------------------------------------------------
# 5. 기관 간 비교 상태 집계
# ------------------------------------------------------------

comparison_status_counts = Counter(
    item["comparison_status"]
    for item in cross["results"]
)

if sum(comparison_status_counts.values()) != 7:
    raise ValueError("기관 간 비교 상태 집계 오류")

if (
    cross.get("external_source_snapshots_archived")
    is not False
):
    raise ValueError(
        "외부 원문 보관 상태가 예상과 다름"
    )

if (
    cross.get("external_source_content_hashes_verified")
    is not False
):
    raise ValueError(
        "외부 원문 해시 검증 상태가 예상과 다름"
    )

print("[PASS] 기관별 검토 상태 및 원문 미보관 확인")


# ------------------------------------------------------------
# 6. 미완료 작업 관리
# ------------------------------------------------------------

pending_work = [
    {
        "task_id": "PENDING-01",
        "category": "external_source_provenance",
        "description": (
            "한국장학재단 등 외부 공식 웹페이지 "
            "원문 보관 및 SHA-256 검증"
        ),
        "status": "needs_review",
        "automatic_resolution_allowed": False,
    },
    {
        "task_id": "PENDING-02",
        "category": "financial_table_alignment",
        "description": (
            "단기·중기 재정지원 표 8개 행의 "
            "행·열 대응 독립 검증"
        ),
        "status": "needs_review",
        "automatic_resolution_allowed": False,
    },
    {
        "task_id": "PENDING-03",
        "category": "loan_eligibility",
        "description": (
            "학적별 실제 대출 실행 요건과 "
            "개인별 심사 조건 분리 검증"
        ),
        "status": "needs_review",
        "automatic_resolution_allowed": False,
    },
    {
        "task_id": "PENDING-04",
        "category": "historical_notice_corrections",
        "description": (
            "FAQ Q3 상반기 표기에 대한 "
            "국립국제교육원 정오표 또는 확인 여부"
        ),
        "status": "needs_review",
        "automatic_resolution_allowed": False,
    },
    {
        "task_id": "PENDING-05",
        "category": "visa_legal_review",
        "description": (
            "J-1 비자 본국거주의무 및 "
            "인턴십 제한의 실제 법률 적용 범위"
        ),
        "status": "needs_review",
        "automatic_resolution_allowed": False,
    },
    {
        "task_id": "PENDING-06",
        "category": "source_semantics",
        "description": (
            "기존 이슈 25건에 대한 "
            "독립적인 의미 검수 및 중복 판정"
        ),
        "status": "needs_review",
        "automatic_resolution_allowed": False,
    },
    {
        "task_id": "PENDING-07",
        "category": "current_policy",
        "description": (
            "2026년 하반기 역사적 공고와 "
            "새로운 모집 회차 정책 분리"
        ),
        "status": "needs_review",
        "automatic_resolution_allowed": False,
    },
]


# ------------------------------------------------------------
# 7. 최종 상태 판정
# ------------------------------------------------------------

audit = {
    "dataset_type": "west_readiness_integrated_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,

    "source_pdf_sha256": PDF_SHA,

    "input_sha256": {
        name: expected
        for name, (_, expected) in INPUTS.items()
    },

    "policy_field_count": 27,

    "issue_count": len(issues),
    "pdf_finding_count": len(findings["findings"]),
    "issues_linked_to_pdf_findings": linked_count,
    "issues_without_pdf_findings": unlinked_count,
    "issues_resolved": 0,

    "issue_tracking": issue_tracking,

    "visa_review_item_count": len(visa["review_items"]),
    "academic_review_item_count": len(
        academic["review_items"]
    ),
    "document_review_item_count": len(
        documents["review_items"]
    ),

    "cross_agency_item_count": len(cross["results"]),
    "cross_agency_status_counts": dict(
        comparison_status_counts
    ),

    "cross_agency_notes_recorded": True,
    "external_source_content_archived": False,
    "external_source_hashes_verified": False,

    "pending_work": pending_work,
    "pending_work_count": len(pending_work),

    "semantic_review_completed": False,
    "legal_review_completed": False,
    "financial_table_cells_independently_verified": False,
    "current_policy_verified": False,

    "ready_for_user_answers": False,
    "ready_for_embedding": False,
    "ready_for_automatic_eligibility": False,

    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,

    "original_files_modified": False,
}

status, output_sha = write_once(
    OUTPUT, audit
)


# ------------------------------------------------------------
# 8. 입력 무결성 재확인
# ------------------------------------------------------------

if sha256(PDF.read_bytes()) != PDF_SHA:
    raise ValueError("검사 도중 PDF 원본 변경")

for key, (filename, expected) in INPUTS.items():
    if sha256((BASE / filename).read_bytes()) != expected:
        raise ValueError(
            f"검사 도중 입력 변경: {key}"
        )


print("\n===== STEP 64-69 최종 결과 =====")
print("정책 필드:", 27)
print("검토 이슈:", len(issues))
print("PDF 근거 연결 이슈:", linked_count)
print("PDF 근거 미연결 이슈:", unlinked_count)
print("기관 간 비교 항목:", len(cross["results"]))
print("남은 검수 작업 범주:", len(pending_work))

print(f"[PASS] {status}: {OUTPUT.name}")
print("SHA-256:", output_sha)

print("정책 의미 최종 검수: 미완료")
print("외부 공식 원문 보관: 미완료")
print("서비스 답변 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
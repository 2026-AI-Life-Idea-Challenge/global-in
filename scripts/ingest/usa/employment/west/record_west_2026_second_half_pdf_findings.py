
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa/employment/west/2026_second_half"

PDF = (
    ROOT / "data/raw/usa/employment/west/2026_second_half"
    / "west_2026_second_half_notice.pdf"
)

REGISTRY = BASE / "west_2026_second_half_semantic_review_registry.json"

OUTPUT = BASE / "west_2026_second_half_pdf_findings.json"
AUDIT = BASE / "west_2026_second_half_pdf_findings_audit.json"

PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

REGISTRY_SHA = (
    "4bb986ba36156642c52d8aaa6a5b14a"
    "752fe4db6349977a09c070d9449c83fee"
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(path, expected):
    if not path.is_file() or digest(path) != expected:
        raise ValueError(f"입력 파일 무결성 오류: {path}")


def compact(text):
    return re.sub(r"\s+", "", text).casefold()


def require(text, phrases, label):
    source = compact(text)
    for phrase in phrases:
        if compact(phrase) not in source:
            raise ValueError(f"{label}: 문구 미확인 - {phrase}")


def printed_page(doc, number):
    page = doc[(number - 1) // 2]
    rect = page.rect
    mid = (rect.x0 + rect.x1) / 2

    clip = pymupdf.Rect(
        rect.x0 if number % 2 else mid,
        rect.y0,
        mid if number % 2 else rect.x1,
        rect.y1,
    )
    return page.get_text("text", clip=clip, sort=True)


def save_once(path, obj):
    raw = (
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(f"기존 파일 덮어쓰기 금지: {path}")
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"

    return status, hashlib.sha256(raw).hexdigest()


print("===== STEP 64-66 공식 PDF 대조 결과 기록 =====")

verify(PDF, PDF_SHA)
verify(REGISTRY, REGISTRY_SHA)

registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

assert registry["program_id"] == "US-WEST-01"
assert registry["notice_period"] == "2026_second_half"
assert len(registry["issues"]) == 25

for flag in (
    "approved_for_user_answers",
    "approved_for_embedding",
    "automatic_eligibility_rules_enabled",
):
    assert registry.get(flag) is False

issue_ids = {item["record_id"] for item in registry["issues"]}

with pymupdf.open(PDF) as doc:
    if len(doc) != 11:
        raise ValueError("PDF 물리 페이지 수 불일치")

    pages = {
        n: printed_page(doc, n)
        for n in (9, 11, 14, 19, 20)
    }

# PDF 텍스트로 검증할 수 있는 사항
checks = {
    9: [
        "취업취약계층 제출 서류",
        "졸업생 지원구간 제출 서류",
        "차상위계층",
        "학자금 지원구간 통지서",
        "신청 증명서",
    ],
    11: [
        "Q3.",
        "A3.",
        "2026년 상반기 선발",
        "어학연수 시작일",
    ],
    14: [
        "Q24.",
        "A24.",
        "학자금 지원구간 통지서",
    ],
    19: [
        "학자금대출",
        "신청증명서",
        "10구간",
    ],
    20: [
        "TOEIC Speaking",
        "ACTFL",
        "200점 만점",
    ],
}

for page, phrases in checks.items():
    require(pages[page], phrases, f"인쇄 {page}쪽")
    print(f"[PASS] 인쇄 {page}쪽: {len(phrases)}개 문구")

findings = [
    {
        "finding_id": "WEST-H2-FIND-Q3",
        "issue_ids": [
            "WEST-H2-ACADEMIC-01",
            "WEST-H2-ELIGIBILITY-01",
            "WEST-H2-SELECTION-04",
        ],
        "printed_pages": [11],
        "source_finding": (
            "2026년 하반기 공고 FAQ Q3의 예시에서 "
            "'2026년 상반기 선발'로 표기됨."
        ),
        "source_text_conflict_confirmed": True,
        "official_erratum_confirmed": False,
        "manual_followup": "국립국제교육원 또는 운영기관에 오기 여부 확인",
        "review_status": "source_discrepancy_verified",
    },
    {
        "finding_id": "WEST-H2-FIND-GRADUATE",
        "issue_ids": [
            "WEST-H2-ACADEMIC-04",
            "WEST-H2-APPLICATION-03",
            "WEST-H2-DOCUMENTS-02",
        ],
        "printed_pages": [9, 14, 19],
        "source_finding": (
            "졸업생은 기초·차상위 증명서, "
            "학자금 지원구간 통지서 또는 "
            "학자금대출·장학금 신청증명서 중 "
            "해당 조건에 맞는 증빙을 제출함."
        ),
        "special_cases": {
            "near_poverty_certificate": (
                "졸업생 지원구간 확인용 차상위계층 증명서 "
                "제출 시 1구간 금액 지원"
            ),
            "no_prior_scholarship_or_loan_application": (
                "신청증명서로 증빙을 대체하고 "
                "10구간에 준하는 정부지원금 지급"
            ),
        },
        "individual_document_decision_approved": False,
        "review_status": "source_branching_verified",
    },
    {
        "finding_id": "WEST-H2-FIND-SPEAKING",
        "issue_ids": [
            "WEST-H2-DOCUMENTS-04",
        ],
        "printed_pages": [20],
        "source_finding": (
            "TOEIC Speaking 점수의 ACTFL 등급 "
            "환산표 및 숫자 점수 입력 안내 확인."
        ),
        "score_rows_visually_reviewed": [
            {"actfl": "AH", "scores": [200]},
            {"actfl": "AM", "scores": [180, 190]},
            {"actfl": "AL", "scores": [160, 170]},
            {"actfl": "IH", "scores": [140, 150]},
            {"actfl": "IM3", "scores": [130]},
            {"actfl": "IM2", "scores": [120]},
            {"actfl": "IM1", "scores": [110]},
        ],
        "table_cells_verified_independently_by_code": False,
        "current_test_provider_rules_verified": False,
        "automatic_score_conversion_enabled": False,
        "review_status": "historical_table_visually_reviewed",
    },
]

for finding in findings:
    unknown = set(finding["issue_ids"]) - issue_ids
    if unknown:
        raise ValueError(f"등록되지 않은 이슈: {unknown}")

result = {
    "dataset_type": "west_pdf_source_findings",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_pdf_sha256": PDF_SHA,
    "input_registry_sha256": REGISTRY_SHA,
    "findings": findings,
    "findings_count": 3,
    "issues_resolved": 0,
    "issues_automatically_merged": 0,
    "semantic_review_completed": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_pdf_source_findings_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "input_pdf_sha256": PDF_SHA,
    "input_registry_sha256": REGISTRY_SHA,
    "printed_pages_checked": sorted(checks),
    "source_phrase_checks_passed": sum(map(len, checks.values())),
    "findings_recorded": len(findings),
    "manual_source_review_required": True,
    "original_files_modified": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

state, result_sha = save_once(OUTPUT, result)
audit["result_sha256"] = result_sha
audit_state, audit_sha = save_once(AUDIT, audit)

verify(PDF, PDF_SHA)
verify(REGISTRY, REGISTRY_SHA)

print("\n===== STEP 64-66 최종 결과 =====")
print("공식 PDF 대조 항목:", len(findings))
print("근거 문구 검사:", sum(map(len, checks.values())))
print("관련 이슈:", len(set(
    issue for item in findings for issue in item["issue_ids"]
)))
print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)
print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)
print("이슈 자동 해결: 0")
print("정책 의미 최종 승인: 미완료")
print("원본 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")

from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT / "data/processed/usa/employment/west/2026_second_half"
)
RAW = (
    ROOT / "data/raw/usa/employment/west/2026_second_half"
)

PDF = RAW / "west_2026_second_half_notice.pdf"
ELIGIBILITY = (
    BASE / "west_2026_second_half_eligibility_source_verified.json"
)

OUTPUT = (
    BASE / "west_2026_second_half_application_source_verified.json"
)
AUDIT = (
    BASE / "west_2026_second_half_application_source_audit.json"
)

PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)
ELIGIBILITY_SHA = (
    "b54407e89beebcd1218415d29e5a6c2"
    "0263fecd41105b7c779ea8c98ca42b5ba"
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_file(path, expected):
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = digest(path)
    if actual != expected:
        raise ValueError(
            f"SHA-256 불일치: {path}\n"
            f"예상: {expected}\n실제: {actual}"
        )


def normalized(text):
    return re.sub(r"\s+", "", text).lower()


def verify_phrases(page_text, phrases, label):
    text = normalized(page_text)
    for phrase in phrases:
        if normalized(phrase) not in text:
            raise ValueError(
                f"{label} 원문 확인 실패: {phrase}"
            )


def evidence(*pages):
    return [
        {
            "printed_page": p,
            "physical_pdf_page": (p + 1) // 2,
            "candidate_id": f"WEST-2026H2-LP{p:02d}",
            "pdf_sha256": PDF_SHA,
        }
        for p in pages
    ]


def reviewed(value, *pages, note=None):
    result = {
        "value": value,
        "evidence": evidence(*pages),
        "source_comparison_status": (
            "verified_against_uploaded_pdf"
        ),
        "validation_status": (
            "source_verified_policy_review_pending"
        ),
    }
    if note:
        result["note"] = note
    return result


def save_without_overwrite(path, data):
    raw = (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 파일과 충돌하여 덮어쓰지 않음: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"

    return status, hashlib.sha256(raw).hexdigest()


print("===== STEP 64-53 WEST 신청 절차 원문 검수 =====")

# 1. 기존 검수 결과·PDF 무결성 검사
verify_file(PDF, PDF_SHA)
verify_file(ELIGIBILITY, ELIGIBILITY_SHA)

previous = json.loads(
    ELIGIBILITY.read_text(encoding="utf-8")
)

assert previous["program_id"] == "US-WEST-01"
assert previous["approved_for_user_answers"] is False
assert previous["approved_for_embedding"] is False
assert previous["automatic_eligibility_rules_enabled"] is False

print("[PASS] 공식 PDF 및 STEP 64-52 결과 SHA-256")

# 2. 공식 PDF의 물리 페이지 검사
with pymupdf.open(PDF) as doc:
    assert len(doc) == 11

    application = doc[1].get_text()  # 인쇄 3~4쪽
    funding = doc[2].get_text()      # 인쇄 5~6쪽
    appendix = doc[4].get_text()     # 인쇄 9~10쪽
    faq = doc[6].get_text()          # 인쇄 13~14쪽

verify_phrases(
    application,
    [
        "2026",
        "7. 1.",
        "8. 5.",
        "17:00",
        "월드잡플러스",
        "자기소개서",
        "개인정보동의서",
        "재학",
        "졸업",
        "공인영어성적",
        "8.6.",
        "8.10.",
    ],
    "인쇄 3~4쪽",
)

verify_phrases(
    funding,
    [
        "한국장학재단",
        "어학연수비 대출",
        "학자금지원구간",
        "졸업생",
        "학자금 지원구간 통지서",
    ],
    "인쇄 5쪽",
)

verify_phrases(
    appendix,
    [
        "취업취약계층",
        "졸업생 지원구간",
        "참가신청서 접수",
        "대학 추천 공문",
    ],
    "인쇄 9~10쪽",
)

verify_phrases(
    faq,
    [
        "Q18.",
        "Q19.",
        "Q20.",
        "Q21.",
        "졸업생",
        "한국장학재단",
    ],
    "FAQ 13~14쪽",
)

print("[PASS] 신청 기간·절차·제출서류 원문 대조")

# 3. 확인된 모집 절차 구조화
fields = {
    "application_start": reviewed(
        "2026-07-01",
        3, 10
    ),
    "application_deadline": reviewed(
        "2026-08-05T17:00:00",
        3, 10,
        note="대한민국 현지시간. 해당 회차 접수는 종료됨."
    ),
    "university_recommendation": reviewed(
        {
            "required": True,
            "submission_start": "2026-08-06",
            "submission_end": "2026-08-10",
            "sender": "소속 또는 출신 대학",
            "recipient": "국립국제교육원",
            "university_internal_deadline": None,
        },
        3, 12, 13,
        note="대학 자체 서류 마감일은 각 대학에 확인 필요"
    ),
    "student_application_procedure": reviewed(
        {
            "applicable_statuses": [
                "재학생",
                "휴학생",
                "초과학기자",
                "수료자",
                "졸업유예자",
                "졸업예정자",
            ],
            "online_application": "월드잡플러스",
            "university_document_submission": True,
            "scholarship_support_bracket_check": (
                "한국장학재단 WEST 어학연수비 대출 신청"
            ),
            "support_bracket_check_required": True,
            "actual_loan_execution_required": False,
        },
        3, 4, 5, 14,
        note=(
            "지원구간 확인 목적의 신청은 필수이나 "
            "대출 실행과는 다름. 학적별 대출 실행 가능 여부는 "
            "별도 검수 대상."
        )
    ),
    "graduate_application_procedure": reviewed(
        {
            "online_application": "월드잡플러스",
            "university_document_submission": True,
            "scholarship_foundation_application_required": False,
            "support_bracket_evidence": [
                "기초생활수급자·차상위계층 증명서",
                "학자금 지원구간 통지서",
                "학자금대출·장학금 신청증명서",
            ],
            "support_bracket_document_selection": (
                "해당자의 발급 가능 서류 및 지원 이력에 따라 선택"
            ),
        },
        3, 4, 5, 9, 14,
        note=(
            "졸업생의 증빙서류는 무조건 세 종류를 "
            "모두 제출하는 것이 아님."
        )
    ),
}

# 4. 제출서류를 지원자 유형별로 정리
documents = {
    "online": reviewed(
        [
            "WEST 온라인 지원서",
            "자기소개서",
            "개인정보동의서",
        ],
        4
    ),
    "university_common": reviewed(
        [
            "WEST 온라인 지원서 및 자기소개서 출력물",
            "재학·휴학·졸업 등 학적증명서",
            "전 학년 성적증명서",
            "공인영어성적 증명서",
        ],
        4, 13
    ),
    "conditional": reviewed(
        {
            "vulnerable_group": (
                "취업취약계층 해당자 증빙자료"
            ),
            "graduate": (
                "학자금 지원구간 증빙자료"
            ),
            "transfer_student": (
                "편입 전·후 성적증명서"
            ),
        },
        3, 4, 9
    ),
    "issuance_date": reviewed(
        {
            "non_language_documents": (
                "2026-07-01 이후 발급분"
            ),
            "language_documents": (
                "2026-08-05 기준 2년 이내 유효한 성적"
            ),
        },
        4
    ),
}

# 5. 신청 절차 관련 미해결 검수 이슈
issues = [
    {
        "issue": "대학별 자체 서류 마감일",
        "status": "needs_review",
        "note": "모집 공고에 대학별 마감일은 명시되지 않음",
        "evidence": evidence(3, 4),
    },
    {
        "issue": "학적별 실제 대출 실행 가능 여부",
        "status": "needs_review",
        "note": (
            "재학생·휴학생·수료자·졸업유예자 등 "
            "세부 조건 분리 검증 필요"
        ),
        "evidence": evidence(5, 7, 14),
    },
    {
        "issue": "졸업생 지원구간 증빙서류 세부 분기",
        "status": "needs_review",
        "note": (
            "기초·차상위 여부와 한국장학재단 신청 이력에 "
            "따른 서류 분기 추가 검수 필요"
        ),
        "evidence": evidence(5, 9, 14, 19),
    },
]

# 6. 결과 데이터
result = {
    "dataset_type": "west_application_source_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_pdf_sha256": PDF_SHA,
    "eligibility_source_sha256": ELIGIBILITY_SHA,
    "fields": fields,
    "required_documents": documents,
    "manual_review_issues": issues,
    "validation_status": (
        "source_verified_policy_review_pending"
    ),
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "verified_input_pdf_sha256": PDF_SHA,
    "verified_eligibility_sha256": ELIGIBILITY_SHA,
    "application_fields_checked": len(fields),
    "document_categories_checked": len(documents),
    "manual_review_issues": len(issues),
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 7. 결과 저장 및 해시 출력
state, result_sha = save_without_overwrite(
    OUTPUT, result
)
audit["result_sha256"] = result_sha

audit_state, audit_sha = save_without_overwrite(
    AUDIT, audit
)

assert digest(OUTPUT) == result_sha
assert digest(AUDIT) == audit_sha
assert digest(PDF) == PDF_SHA
assert digest(ELIGIBILITY) == ELIGIBILITY_SHA

print("\n===== STEP 64-53 최종 결과 =====")
print("신청 관련 필드:", len(fields))
print("제출서류 분류:", len(documents))
print("수동 검토 이슈:", len(issues))
print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)
print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)
print("원본 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")

from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa/employment/west/2026_second_half"
RAW = ROOT / "data/raw/usa/employment/west/2026_second_half"

PDF = RAW / "west_2026_second_half_notice.pdf"
FINANCIAL = BASE / "west_2026_second_half_financial_source_verified.json"

OUTPUT = BASE / "west_2026_second_half_selection_faq_review.json"
AUDIT = BASE / "west_2026_second_half_selection_faq_audit.json"

PDF_SHA = "d04abdc458ad0a4a1f18196c9fdcb05f4ba39821183e0d77aaa5fa5f129a80e2"
FINANCIAL_SHA = "8d381edebe88569b087050cedcd8046f5adae0dd30c4b0e19ea30372f657ca3a"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(path, expected):
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path.read_bytes())
    if actual != expected:
        raise ValueError(
            f"SHA-256 불일치: {path}\n"
            f"예상: {expected}\n실제: {actual}"
        )


def norm(value):
    return re.sub(r"\s+", "", value).lower()


def require_phrases(text, phrases, label):
    value = norm(text)
    for phrase in phrases:
        if norm(phrase) not in value:
            raise ValueError(f"{label}: 근거 누락 - {phrase}")


def ref(*printed_pages):
    return [
        {
            "printed_page": p,
            "physical_pdf_page": (p + 1) // 2,
            "candidate_id": f"WEST-2026H2-LP{p:02d}",
            "source_pdf_sha256": PDF_SHA,
        }
        for p in printed_pages
    ]


def field(value, *pages, note=None):
    item = {
        "value": value,
        "evidence": ref(*pages),
        "source_comparison_status": "verified_against_pdf",
        "validation_status": "needs_review",
    }
    if note is not None:
        item["note"] = note
    return item


def save(path, obj):
    raw = (
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 결과와 다름. 덮어쓰지 않음: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"
    return status, sha256(raw)


print("===== STEP 64-55 WEST 선발 일정·대출·FAQ 검수 =====")

# 1. 기존 결과 무결성 확인
verify(PDF, PDF_SHA)
verify(FINANCIAL, FINANCIAL_SHA)

financial = json.loads(FINANCIAL.read_text(encoding="utf-8"))

assert financial["program_id"] == "US-WEST-01"
assert financial["approved_for_user_answers"] is False
assert financial["approved_for_embedding"] is False
assert financial["automatic_eligibility_rules_enabled"] is False

print("[PASS] 공식 PDF 및 STEP 64-54 결과 SHA-256")

# 2. PDF 페이지별 텍스트
with pymupdf.open(PDF) as doc:
    if len(doc) != 11:
        raise ValueError("예상 PDF 페이지 수와 다름")

    pages = [page.get_text() for page in doc]

# PDF 물리 5쪽 = 인쇄 9~10쪽
schedule_text = pages[4]

# PDF 물리 3쪽 = 인쇄 5~6쪽
loan_text = pages[2]

# PDF 물리 4쪽 = 인쇄 7~8쪽
loan_restriction_text = pages[3]

# PDF 물리 7쪽 = 인쇄 13~14쪽
loan_faq_text = pages[6]

require_phrases(
    schedule_text,
    [
        "선발 일정",
        "9.2.",
        "9.12.",
        "9.13.",
        "9.17.",
        "9.18.",
        "10.6.",
        "10.15.",
        "10.16.",
        "10.22.",
        "10.23",
        "10.27.",
        "11.14.",
        "27.1월",
    ],
    "선발 일정"
)

require_phrases(
    loan_text,
    [
        "한국장학재단",
        "어학연수비 대출",
        "졸업유예자는 불가",
        "수료자",
        "졸업생",
    ],
    "대출 신청·실행 조건"
)

require_phrases(
    loan_restriction_text,
    [
        "졸업생 및 졸업유예자는 불가",
        "재학생",
        "휴학생",
        "초과학기자",
        "수료자",
    ],
    "학적별 대출 제한"
)

require_phrases(
    loan_faq_text,
    [
        "Q20.",
        "Q21.",
        "졸업유예자",
        "불가능",
        "졸업생",
    ],
    "학자금 지원구간 FAQ"
)

print("[PASS] 선발 일정·학적별 대출 근거 확인")

# 3. FAQ Q1~Q49 존재 여부
faq_pages = pages[5:9]

faq_numbers = []
answer_numbers = []
faq_index = []

for physical_index, text in enumerate(faq_pages, start=6):
    questions = [
        int(x)
        for x in re.findall(r"\bQ(\d{1,2})\.", text)
    ]
    answers = [
        int(x)
        for x in re.findall(r"\bA(\d{1,2})\.", text)
    ]

    faq_numbers.extend(questions)
    answer_numbers.extend(answers)

    for number in questions:
        # 홀짝 인쇄 페이지의 정확한 소속은
        # 전체 페이지 텍스트만으로 단정하지 않음.
        faq_index.append({
            "question_number": number,
            "physical_pdf_page": physical_index,
            "printed_page_candidates": [
                physical_index * 2 - 1,
                physical_index * 2,
            ],
            "content_semantics_verified": False,
            "validation_status": "needs_review",
        })

expected = set(range(1, 50))

if (
    set(faq_numbers) != expected
    or set(answer_numbers) != expected
    or len(faq_numbers) != 49
    or len(answer_numbers) != 49
):
    raise ValueError(
        "FAQ Q1~Q49 또는 A1~A49 누락·중복 확인 필요"
    )

print("[PASS] FAQ 질문·답변 번호 Q1~Q49 / A1~A49")

# 4. 선발 일정 구조화
schedule = {
    "document_submission_deadline": field(
        "2026-08-05T17:00:00", 10
    ),
    "university_recommendation": field(
        {
            "start": "2026-08-06",
            "end": "2026-08-10",
        },
        10
    ),
    "scholarship_bracket_review": field(
        {
            "start": "2026-08-10",
            "end": "2026-10-05",
        },
        10
    ),
    "document_screening_result": field(
        "2026-09-02T16:00:00", 10
    ),
    "first_interview": field(
        {
            "short_term": "2026-09-12",
            "medium_term": "2026-09-13",
        },
        10
    ),
    "first_interview_result": field(
        "2026-09-17T16:00:00", 10
    ),
    "second_english_interview": field(
        {
            "start": "2026-09-18",
            "end": "2026-10-06",
        },
        10
    ),
    "final_result": field(
        "2026-10-15T16:00:00", 10
    ),
    "participation_fee_payment": field(
        {
            "start": "2026-10-16",
            "end": "2026-10-22",
        },
        10
    ),
    "additional_acceptance_and_payment": field(
        {
            "start": "2026-10-23",
            "end": "2026-10-27",
        },
        10
    ),
    "predeparture_orientation": field(
        "2026-11-14", 10
    ),
    "visa_interview": field(
        "2026년 11월 말 예정", 10
    ),
    "departure": field(
        "2026년 12월부터 예정", 10
    ),
    "language_training_start": field(
        "2027년 1월부터 예정", 10,
        note="현지중개기관·어학연수기관별 실제 시작일 상이"
    ),
}

# 5. 학적별 지원구간 신청과 실제 대출 실행 분리
loan = {
    "application_for_support_bracket": {
        "재학생": "required",
        "휴학생": "required",
        "초과학기자": "required",
        "수료자": "required",
        "졸업유예자": "required",
        "졸업생": "not_required_separate_documents",
    },
    "actual_loan_execution": {
        "재학생": "possible_subject_to_foundation_review",
        "휴학생": "possible_subject_to_foundation_review",
        "초과학기자": "possible_subject_to_foundation_review",
        "수료자": "conditional_2026_second_semester_registration",
        "졸업유예자": "not_allowed",
        "졸업생": "not_allowed",
    },
    "supporting_pages": ref(5, 7, 14),
    "individual_loan_eligibility_verified": False,
    "validation_status": "needs_review",
}

# 6. 검토 보류 이슈
issues = [
    {
        "issue": "선발 일정의 변경 가능성",
        "status": "needs_review",
        "evidence": ref(10),
    },
    {
        "issue": "학적 변경 시 대출 실행 제한",
        "status": "needs_review",
        "evidence": ref(5, 14),
    },
    {
        "issue": "수료자의 2026년 2학기 등록 조건",
        "status": "needs_review",
        "evidence": ref(5, 7, 14),
    },
    {
        "issue": "FAQ Q3 선발 시기 표기 불일치",
        "status": "needs_review",
        "evidence": ref(11),
    },
    {
        "issue": "FAQ Q43·Q48의 J-1 본국거주의무",
        "note": (
            "공고 내용만으로 모든 J-1 참가자에게 "
            "일률 적용하는 자동 법률 판단 금지. "
            "개별 비자 및 현행 법률 검증 별도 필요."
        ),
        "status": "needs_review",
        "evidence": ref(17, 18),
    },
    {
        "issue": "FAQ 49개 답변의 개별 의미 검수",
        "note": (
            "질문·답변 번호의 완전성만 확인. "
            "49개 답변 전체를 정책 승인한 것은 아님."
        ),
        "status": "needs_review",
        "evidence": ref(11, 12, 13, 14, 15, 16, 17, 18),
    },
]

# 7. 최종 결과
result = {
    "dataset_type": "west_selection_loan_faq_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_pdf_sha256": PDF_SHA,
    "financial_source_sha256": FINANCIAL_SHA,
    "selection_schedule": schedule,
    "scholarship_loan_by_academic_status": loan,
    "faq_index": sorted(
        faq_index,
        key=lambda item: item["question_number"]
    ),
    "faq_questions_verified": 49,
    "faq_answers_verified": 49,
    "faq_semantics_verified": False,
    "manual_review_issues": issues,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "input_pdf_sha256": PDF_SHA,
    "input_financial_sha256": FINANCIAL_SHA,
    "selection_schedule_fields": len(schedule),
    "faq_question_count": len(faq_numbers),
    "faq_answer_count": len(answer_numbers),
    "faq_meaning_approved": False,
    "loan_eligibility_approved": False,
    "manual_review_issues": len(issues),
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

state, result_sha = save(OUTPUT, result)
audit["result_sha256"] = result_sha
audit_state, audit_sha = save(AUDIT, audit)

verify(PDF, PDF_SHA)
verify(FINANCIAL, FINANCIAL_SHA)

print("\n===== STEP 64-55 최종 결과 =====")
print("선발 일정 항목:", len(schedule))
print("FAQ 질문:", len(faq_numbers))
print("FAQ 답변:", len(answer_numbers))
print("수동 검토 이슈:", len(issues))
print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)
print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)
print("FAQ 의미 검수: 미완료")
print("개인별 대출 판정: 비활성화")
print("원본 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
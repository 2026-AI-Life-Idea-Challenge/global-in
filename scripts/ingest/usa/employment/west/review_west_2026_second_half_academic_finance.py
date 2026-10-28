
from pathlib import Path
import hashlib
import json
import re

import pymupdf


# ============================================================
# STEP 64-61
# WEST 2026 H2 학적·졸업·재정지원 예외 의미 검토
# ============================================================

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT / "data/processed/usa/employment/west/2026_second_half"
)

PDF = (
    ROOT / "data/raw/usa/employment/west/2026_second_half"
    / "west_2026_second_half_notice.pdf"
)

PREVIOUS = BASE / "west_2026_second_half_visa_internship_review.json"

OUTPUT = BASE / "west_2026_second_half_academic_finance_review.json"
AUDIT = BASE / "west_2026_second_half_academic_finance_audit.json"

PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

PREVIOUS_SHA = (
    "9e796baff8fe1df5a3b2056d7b6cad9"
    "4603624c18024dd836921c3dce3034678"
)

FAQ_LOCATIONS = {
    3: 11,
    15: 13,
    20: 14,
    21: 14,
    24: 14,
    25: 15,
    26: 15,
}


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


def normalize(text):
    return re.sub(r"\s+", "", text).casefold()


def require(text, phrases, label):
    source = normalize(text)

    for phrase in phrases:
        if normalize(phrase) not in source:
            raise ValueError(
                f"{label}: 원문 문구를 찾지 못함 - {phrase}"
            )


def source_ref(printed_page):
    return {
        "printed_page": printed_page,
        "physical_pdf_page": (printed_page + 1) // 2,
        "candidate_id": f"WEST-2026H2-LP{printed_page:02d}",
        "source_pdf_sha256": PDF_SHA,
    }


def get_printed_page(doc, printed_page):
    """
    원본 PDF는 가로로 놓인 인쇄 페이지 2개가
    PDF 물리 페이지 1개를 구성한다.
    """
    physical_index = (printed_page - 1) // 2
    page = doc[physical_index]

    rect = page.rect
    middle = rect.x0 + rect.width / 2

    if printed_page % 2:
        clip = pymupdf.Rect(
            rect.x0, rect.y0, middle, rect.y1
        )
    else:
        clip = pymupdf.Rect(
            middle, rect.y0, rect.x1, rect.y1
        )

    return page.get_text(
        "text", clip=clip, sort=True
    )


def extract_faq(page_text, number, printed_page):
    question_match = re.search(
        rf"(?m)^\s*Q{number}\.\s*",
        page_text
    )
    answer_match = re.search(
        rf"(?m)^\s*A{number}\.\s*",
        page_text
    )

    if not question_match or not answer_match:
        raise ValueError(
            f"인쇄 {printed_page}쪽: "
            f"FAQ Q{number}/A{number} 누락"
        )

    if question_match.end() >= answer_match.start():
        raise ValueError(
            f"FAQ {number}: 질문·답변 위치 오류"
        )

    next_question = re.search(
        r"(?m)^\s*Q\d{1,2}\.\s*",
        page_text[answer_match.end():]
    )

    end = (
        answer_match.end() + next_question.start()
        if next_question
        else len(page_text)
    )

    question = page_text[
        question_match.end():answer_match.start()
    ].strip()

    answer = page_text[
        answer_match.end():end
    ].strip()

    if not question or not answer:
        raise ValueError(
            f"FAQ {number}: 빈 질문 또는 답변"
        )

    return {
        "question_number": number,
        "question": question,
        "answer": answer,
        "question_sha256": sha256(
            question.encode("utf-8")
        ),
        "answer_sha256": sha256(
            answer.encode("utf-8")
        ),
        "evidence": source_ref(printed_page),
        "extraction_status": "source_text_extracted",
        "semantic_review_completed": False,
    }


def save_new_or_verify(path, data):
    raw = (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"다른 내용의 파일이 이미 존재함: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as handle:
            handle.write(raw)
        status = "CREATED"

    return status, sha256(raw)


print("===== STEP 64-61 학적·졸업·재정지원 예외 검수 =====")

# 1. 입력 무결성
verify(PDF, PDF_SHA)
verify(PREVIOUS, PREVIOUS_SHA)

previous = json.loads(
    PREVIOUS.read_text(encoding="utf-8")
)

assert previous["program_id"] == "US-WEST-01"
assert previous["notice_period"] == "2026_second_half"
assert previous["approved_for_user_answers"] is False
assert previous["approved_for_embedding"] is False
assert previous["automatic_eligibility_rules_enabled"] is False

print("[PASS] PDF 및 STEP 64-60 결과 SHA-256")

# 2. 인쇄 페이지별 PDF 텍스트 추출
needed_pages = {
    2, 3, 4, 5, 7, 9, 11, 13, 14, 15, 19
}

with pymupdf.open(PDF) as doc:
    if len(doc) != 11:
        raise ValueError("PDF 물리 페이지 수 불일치")

    texts = {
        number: get_printed_page(doc, number)
        for number in needed_pages
    }

# 3. 핵심 조건의 원문 존재 검사
PAGE_CHECKS = {
    2: [
        "4학기",
        "2학기",
        "재·휴학생",
        "1년",
        "복수 국적자",
    ],
    3: [
        "추천 공문",
        "8.6.",
    ],
    5: [
        "한국장학재단",
        "어학연수비 대출",
        "졸업생",
        "수료자",
    ],
    7: [
        "졸업생 및 졸업유예자는 불가",
        "수료자",
    ],
    9: [
        "취업취약계층",
        "학자금 지원구간",
    ],
    11: ["Q3.", "A3.", "어학연수 시작일"],
    13: ["Q15.", "A15.", "재외국민"],
    14: ["Q20.", "Q21.", "Q24."],
    15: ["Q25.", "Q26."],
    19: ["학자금대출", "졸업생"],
}

for page, phrases in PAGE_CHECKS.items():
    require(texts[page], phrases, f"인쇄 {page}쪽")

print("[PASS] 주요 학적·졸업·지원구간 원문 확인")

# 4. FAQ 질문·답변 원문 추출
faq = {}

for number, page in FAQ_LOCATIONS.items():
    item = extract_faq(
        texts[page], number, page
    )

    faq[str(number)] = item

    print(
        f"[PASS] FAQ Q{number}/A{number} 추출"
    )

# 5. 각 답변의 의미를 확인할 단서 검사
ANSWER_CHECKS = {
    3: ["어학연수 시작일", "졸업"],
    15: ["10구간", "재외국민"],
    20: ["졸업생", "재학생"],
    21: ["실제 대출", "미신청"],
    24: ["학자금 지원구간", "증명서"],
    25: ["초과 학기자", "수료자", "졸업유예자"],
    26: ["합격자 발표일", "지원구간"],
}

for number, phrases in ANSWER_CHECKS.items():
    require(
        faq[str(number)]["answer"],
        phrases,
        f"FAQ A{number}"
    )

print("[PASS] FAQ 7개 답변의 핵심 문맥 확인")

# 6. 원문에 따른 조건 분리
review_items = {
    "enrollment_status": {
        "source_meaning": (
            "공고는 재학생·휴학생뿐 아니라 "
            "초과학기자·수료자·졸업유예자를 "
            "지원 절차상 구분하여 안내함."
        ),
        "evidence": [
            source_ref(2),
            source_ref(3),
            source_ref(15),
        ],
        "risk": (
            "학적 유형이 같아 보이더라도 "
            "지원구간 신청과 실제 대출 실행의 "
            "조건은 서로 다를 수 있음."
        ),
        "validation_status": "needs_review",
    },

    "recent_graduate": {
        "source_meaning": (
            "졸업생의 지원 자격은 실제 "
            "어학연수 시작일 기준 최근 1년 이내."
        ),
        "evidence": [
            source_ref(2),
            source_ref(11),
        ],
        "risk": (
            "지원서 제출일을 기준으로 "
            "졸업생 자격을 판정하지 않음. "
            "기관별 어학연수 시작일 확인 필요."
        ),
        "validation_status": "needs_review",
    },

    "support_bracket_application": {
        "source_meaning": (
            "재학생 계열은 한국장학재단 "
            "WEST 지원구간 확인 신청이 필요하며 "
            "졸업생은 대학에 별도 증빙을 제출."
        ),
        "evidence": [
            source_ref(5),
            source_ref(14),
        ],
        "risk": (
            "지원구간 확인을 위한 신청을 "
            "실제 대출 실행과 혼동하지 않음."
        ),
        "validation_status": "needs_review",
    },

    "loan_execution": {
        "source_meaning": (
            "재학생·휴학생·초과학기자는 "
            "공고상 대출 실행 가능 유형이며, "
            "수료자는 조건부, 졸업유예자·졸업생은 불가."
        ),
        "evidence": [
            source_ref(5),
            source_ref(7),
            source_ref(14),
        ],
        "risk": (
            "실제 대출 승인 여부는 "
            "한국장학재단 심사 및 개별 학적에 따름."
        ),
        "validation_status": "needs_review",
    },

    "graduate_support_evidence": {
        "source_meaning": (
            "졸업생은 기초·차상위 증명서, "
            "지원구간 통지서, 신청증명서 등을 "
            "발급 조건에 맞게 제출."
        ),
        "evidence": [
            source_ref(5),
            source_ref(9),
            source_ref(14),
            source_ref(19),
        ],
        "risk": (
            "모든 증빙서류가 동시에 필요한 것으로 "
            "안내하지 않음. 해당 유형의 "
            "증빙 분기를 추가 확인해야 함."
        ),
        "validation_status": "needs_review",
    },

    "overseas_admission_special_case": {
        "source_meaning": (
            "재외국민 특별전형 입학 여부 누락이 "
            "정부지원금 산정에 영향을 줄 수 있음."
        ),
        "evidence": [
            source_ref(4),
            source_ref(5),
            source_ref(13),
        ],
        "risk": (
            "지원구간과 관련된 예외를 "
            "모든 해외거주자에게 일괄 적용하지 않음."
        ),
        "validation_status": "needs_review",
    },

    "support_bracket_after_acceptance": {
        "source_meaning": (
            "공고 FAQ Q26은 합격자 발표일 기준 "
            "지원구간으로 활동 종료 시까지 "
            "지원한다고 안내함."
        ),
        "evidence": [source_ref(15)],
        "risk": (
            "개인별 지원액을 임의로 확정하지 않음."
        ),
        "validation_status": "needs_review",
    },
}

# 7. 명시적으로 보존할 검토 이슈
manual_issues = [
    {
        "issue": "FAQ Q3의 선발 회차 예시 불일치",
        "status": "needs_review",
        "details": (
            "하반기 공고의 FAQ 예시 문구에 "
            "상반기 선발 표현이 있어 확인 필요."
        ),
        "evidence": [source_ref(11)],
    },
    {
        "issue": "기관별 졸업생 기준일",
        "status": "needs_review",
        "details": (
            "기관별 실제 어학연수 시작일을 "
            "확인하기 전에는 개별 자격 판정 보류."
        ),
        "evidence": [
            source_ref(2),
            source_ref(11),
        ],
    },
    {
        "issue": "수료자 실제 대출 실행 조건",
        "status": "needs_review",
        "details": (
            "2026년 2학기 등록 여부 등 "
            "한국장학재단의 개별 심사 조건 확인."
        ),
        "evidence": [
            source_ref(5),
            source_ref(7),
            source_ref(14),
        ],
    },
    {
        "issue": "졸업생 지원구간 증빙 분기",
        "status": "needs_review",
        "details": (
            "발급 가능 서류·국가장학금 이력에 따른 "
            "증빙 구분 및 정부지원금 적용 확인."
        ),
        "evidence": [
            source_ref(9),
            source_ref(14),
            source_ref(19),
        ],
    },
    {
        "issue": "재외국민 특별전형 관련 지원금",
        "status": "needs_review",
        "details": (
            "입학 여부 기재 누락과 "
            "지원금 산정 간의 관계 추가 확인."
        ),
        "evidence": [
            source_ref(4),
            source_ref(5),
            source_ref(13),
        ],
    },
]

# 8. 결과 JSON
result = {
    "dataset_type": "west_academic_finance_semantic_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_pdf_sha256": PDF_SHA,
    "previous_review_sha256": PREVIOUS_SHA,
    "faq_original_text": faq,
    "review_items": review_items,
    "manual_review_issues": manual_issues,
    "faq_extracted_count": len(faq),
    "review_item_count": len(review_items),
    "issues_automatically_resolved": 0,
    "individual_eligibility_determined": False,
    "individual_loan_eligibility_determined": False,
    "semantic_review_completed": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_academic_finance_review_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_sha256": PDF_SHA,
    "input_previous_sha256": PREVIOUS_SHA,
    "faq_extracted_count": len(faq),
    "review_item_count": len(review_items),
    "manual_review_issues": len(manual_issues),
    "original_files_modified": False,
    "semantic_review_completed": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 9. 기존 파일을 덮어쓰지 않고 결과 저장
state, result_sha = save_new_or_verify(
    OUTPUT, result
)

audit["result_sha256"] = result_sha

audit_state, audit_sha = save_new_or_verify(
    AUDIT, audit
)

verify(PDF, PDF_SHA)
verify(PREVIOUS, PREVIOUS_SHA)
verify(OUTPUT, result_sha)
verify(AUDIT, audit_sha)

print("\n===== STEP 64-61 최종 결과 =====")
print("추출된 FAQ 문답:", len(faq))
print("의미 검토 항목:", len(review_items))
print("추가 검토 이슈:", len(manual_issues))
print("자동 해결 이슈:", 0)

print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)

print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)

print("원본 변경: 없음")
print("개인별 지원 자격 판정: 비활성화")
print("개인별 대출 판정: 비활성화")
print("답변·임베딩 승인: False")
print("Git commit·push: 미실행")
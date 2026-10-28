
from pathlib import Path
import hashlib
import json
import re

import pymupdf


# STEP 64-62
# WEST 2026 H2 제출서류·시험 성적표 검수

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT / "data/processed/usa/employment/west/2026_second_half"
)

PDF = (
    ROOT / "data/raw/usa/employment/west/2026_second_half"
    / "west_2026_second_half_notice.pdf"
)

PREVIOUS = (
    BASE / "west_2026_second_half_academic_finance_review.json"
)

OUTPUT = (
    BASE / "west_2026_second_half_documents_scores_review.json"
)

AUDIT = (
    BASE / "west_2026_second_half_documents_scores_audit.json"
)

PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

PREVIOUS_SHA = (
    "c3cb750badb91b75e25746c6bf1ccb18"
    "e39a8302a3d5ccfed3b5a03577d48925"
)


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
                f"{label}: PDF 원문 문구 누락: {phrase}"
            )


def printed_page(doc, number):
    physical = (number - 1) // 2
    page = doc[physical]
    rect = page.rect
    middle = rect.x0 + rect.width / 2

    if number % 2 == 1:
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


def evidence(page):
    return {
        "printed_page": page,
        "physical_pdf_page": (page + 1) // 2,
        "candidate_id": f"WEST-2026H2-LP{page:02d}",
        "source_pdf_sha256": PDF_SHA,
    }


def extract_faq(text, number, page):
    q = re.search(
        rf"(?m)^\s*Q{number}\.\s*", text
    )
    a = re.search(
        rf"(?m)^\s*A{number}\.\s*", text
    )

    if not q or not a or q.end() >= a.start():
        raise ValueError(
            f"FAQ Q{number}/A{number} 추출 실패"
        )

    next_q = re.search(
        r"(?m)^\s*Q\d{1,2}\.\s*",
        text[a.end():]
    )

    end = (
        a.end() + next_q.start()
        if next_q else len(text)
    )

    question = text[q.end():a.start()].strip()
    answer = text[a.end():end].strip()

    if not question or not answer:
        raise ValueError(
            f"FAQ {number}: 빈 질문 또는 답변"
        )

    return {
        "number": number,
        "question": question,
        "answer": answer,
        "question_sha256": sha256(
            question.encode("utf-8")
        ),
        "answer_sha256": sha256(
            answer.encode("utf-8")
        ),
        "evidence": evidence(page),
        "semantic_review_completed": False,
    }


def reviewed(summary, pages, caution):
    return {
        "source_summary": summary,
        "evidence": [
            evidence(page) for page in pages
        ],
        "caution": caution,
        "source_presence_verified": True,
        "semantic_review_completed": False,
        "validation_status": "needs_review",
    }


def write_new_or_verify(path, data):
    raw = (
        json.dumps(
            data, ensure_ascii=False, indent=2
        ) + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 파일과 내용이 다름: {path}"
            )
        state = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as file:
            file.write(raw)
        state = "CREATED"

    return state, sha256(raw)


print("===== STEP 64-62 제출서류·어학성적 증빙 검수 =====")

# 1. 원본 및 이전 결과 검증
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

print("[PASS] PDF 및 STEP 64-61 결과 SHA-256")


# 2. 인쇄 페이지 단위로 추출
needed_pages = {
    4, 9, 11, 12, 13, 14, 19, 20, 21, 22
}

with pymupdf.open(PDF) as doc:
    if len(doc) != 11:
        raise ValueError("물리 PDF 페이지 수 오류")

    texts = {
        n: printed_page(doc, n)
        for n in sorted(needed_pages)
    }

PAGE_CHECKS = {
    4: [
        "공인영어성적증명서",
    ],
    9: [
        "취업취약계층",
        "기초생활수급자",
        "차상위계층",
        "다문화가족",
        "졸업생 지원구간",
    ],
    11: ["Q1.", "A1."],
    12: [
        "Q12.", "A12.",
        "Registration Number", "Test ID",
    ],
    13: [
        "Q15.", "A15.",
        "Q19.", "A19.",
    ],
    14: ["Q24.", "A24."],
    19: [
        "학자금대출",
        "장학금 신청증명서",
        "10구간",
    ],
    20: [
        "TOEIC Speaking",
        "ACTFL",
        "200점 만점",
    ],
    21: [
        "OPIc", "Test ID", "12자리",
    ],
    22: [
        "G-TELP", "수험번호", "8자리",
    ],
}

phrase_check_count = 0

for number, phrases in PAGE_CHECKS.items():
    require(
        texts[number],
        phrases,
        f"인쇄 {number}쪽"
    )
    phrase_check_count += len(phrases)

print("[PASS] PDF 페이지별 증빙·식별번호 문구 검사")


# 3. FAQ 문답 추출
FAQ_LOCATIONS = {
    1: 11,
    12: 12,
    15: 13,
    19: 13,
    24: 14,
}

faq = {}

for number, page in FAQ_LOCATIONS.items():
    faq[str(number)] = extract_faq(
        texts[page], number, page
    )
    print(f"[PASS] FAQ Q{number}/A{number} 추출")

ANSWER_CHECKS = {
    1: ["접수 마감일", "명시된", "시험성적"],
    12: [
        "Registration Number",
        "Test ID",
        "수험번호",
    ],
    15: ["10구간", "재외국민"],
    19: [
        "공인영어성적",
        "재학",
        "지원구간",
    ],
    24: [
        "학자금 지원구간",
        "증명서",
    ],
}

for number, phrases in ANSWER_CHECKS.items():
    require(
        faq[str(number)]["answer"],
        phrases,
        f"FAQ A{number}"
    )

print("[PASS] FAQ 답변별 증빙 관련 문구 검사")


# 4. 증빙 내용과 주의사항 분리
review_items = {
    "vulnerable_group_documents": reviewed(
        "취업취약계층 유형별 증빙서류가 구분됨",
        [9],
        "각 자격 유형의 모든 세부 서류·발급처는 "
        "표 행·열별 최종 검수 필요",
    ),

    "graduate_support_bracket_documents": reviewed(
        "졸업생은 해당 조건에 따라 지원구간 "
        "통지서 또는 대체 증빙 등을 제출",
        [9, 14, 19],
        "모든 졸업생이 동일한 서류를 "
        "제출하거나 동일 지원구간에 "
        "해당한다고 판단하지 않음",
    ),

    "language_score_submission": reviewed(
        "마감일에 유효한 공고 지정 어학시험 "
        "성적만 인정하며 대학에도 증빙 제출",
        [4, 11, 13],
        "미기재 시험의 점수를 대체 인정하지 않음",
    ),

    "score_report_identifiers": reviewed(
        "시험별 등록번호 종류 및 자릿수 안내",
        [12, 20, 21, 22],
        "문자열 형식 검사와 성적표 진위 확인은 "
        "서로 다른 절차",
    ),

    "toeic_speaking_conversion": reviewed(
        "TOEIC Speaking ACTFL 등급표와 "
        "200점 만점 숫자 입력 안내",
        [20],
        "환산표 이미지의 전체 점수·등급 대응을 "
        "자동 전사하거나 자동 환산하지 않음",
    ),
}

# 5. 시험별 식별번호의 공고상 안내
score_identifiers = {
    "TOEIC": {
        "name": "Registration Number",
        "length": 6,
        "format_note": "숫자 6자리",
        "evidence": [
            evidence(12), evidence(20)
        ],
    },
    "TOEIC_Speaking": {
        "name": "Registration Number",
        "length": 6,
        "format_note": "숫자 6자리",
        "evidence": [
            evidence(12), evidence(20)
        ],
    },
    "OPIc": {
        "name": "Test ID",
        "length": 12,
        "format_note": (
            "숫자 1자리 + 영문 대문자 1자리 "
            "+ 숫자 10자리"
        ),
        "evidence": [
            evidence(12), evidence(21)
        ],
    },
    "G_TELP": {
        "name": "수험번호",
        "length": 11,
        "format_note": "숫자 11자리",
        "evidence": [
            evidence(12), evidence(22)
        ],
    },
    "G_TELP_Speaking": {
        "name": "수험번호",
        "length": 8,
        "format_note": (
            "알파벳 s + 숫자 7자리"
        ),
        "evidence": [
            evidence(12), evidence(22)
        ],
    },
}

# 위 형식은 문서의 안내 내용을 기록한 것이다.
# 성적 인증 API 또는 개인정보 유효성 검사로 사용하지 않는다.


# 6. 검토 이슈 보존
issues = [
    {
        "issue": "취업취약계층 증빙서류 표 상세 검수",
        "status": "needs_review",
        "evidence": [evidence(9)],
    },
    {
        "issue": "졸업생 지원구간 증빙 분기 검수",
        "status": "needs_review",
        "evidence": [
            evidence(9),
            evidence(14),
            evidence(19),
        ],
    },
    {
        "issue": "성적표 식별번호 형식과 진위 검증 구분",
        "status": "needs_review",
        "evidence": [
            evidence(12),
            evidence(20),
            evidence(21),
            evidence(22),
        ],
    },
    {
        "issue": "TOEIC Speaking 환산표 전체 값 검수",
        "status": "needs_review",
        "evidence": [evidence(20)],
    },
]

# 7. 결과 파일 구성
result = {
    "dataset_type": "west_documents_scores_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_pdf_sha256": PDF_SHA,
    "previous_review_sha256": PREVIOUS_SHA,
    "faq_original_text": faq,
    "review_items": review_items,
    "score_report_identifiers": score_identifiers,
    "manual_review_issues": issues,
    "toeic_speaking_conversion_table": None,
    "score_authenticity_verified": False,
    "document_eligibility_verified": False,
    "semantic_review_completed": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_documents_scores_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_sha256": PDF_SHA,
    "input_previous_sha256": PREVIOUS_SHA,
    "pdf_phrase_checks_passed": phrase_check_count,
    "faq_extracted_count": len(faq),
    "review_item_count": len(review_items),
    "score_identifier_types": len(score_identifiers),
    "manual_review_issues": len(issues),
    "toeic_speaking_table_values_verified": False,
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 8. 결과 저장
state, result_sha = write_new_or_verify(
    OUTPUT, result
)

audit["result_sha256"] = result_sha

audit_state, audit_sha = write_new_or_verify(
    AUDIT, audit
)

# 9. 최종 무결성 검사
verify(PDF, PDF_SHA)
verify(PREVIOUS, PREVIOUS_SHA)
verify(OUTPUT, result_sha)
verify(AUDIT, audit_sha)

print("\n===== STEP 64-62 최종 결과 =====")
print("PDF 근거 문구 검사:", phrase_check_count)
print("FAQ 원문 추출:", len(faq))
print("검토 항목:", len(review_items))
print("시험별 식별번호 유형:", len(score_identifiers))
print("추가 검토 이슈:", len(issues))

print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)
print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)

print("환산표 전체 수치 검수: 미완료")
print("원본 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
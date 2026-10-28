
from pathlib import Path
from datetime import date
import hashlib
import json
import re

import pymupdf


# ============================================================
# STEP 64-60
# WEST 2026년 하반기 J-1 비자·인턴십 의미 검수
#
# 입력 원본을 수정하지 않음
# 임베딩·자동 자격 판정·Git 작업 수행하지 않음
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

REGISTER = (
    BASE / "west_2026_second_half_review_register.json"
)

OUTPUT = (
    BASE / "west_2026_second_half_visa_internship_review.json"
)

AUDIT = (
    BASE / "west_2026_second_half_visa_internship_audit.json"
)

PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

REGISTER_SHA = (
    "49cd19ae12b204dea33db027670255"
    "52c2d717199ce038182dd6223b0582ca0b"
)

FAQ_NUMBERS = (39, 40, 43, 48)

# 2026-10-21 기준 검토에 사용한 미국 국무부 참고 자료.
# 프로그램 공고의 원본 근거와 별도로 보관한다.
US_OFFICIAL_SOURCES = {
    "dos_212e_eligibility": (
        "https://travel.state.gov/content/travel/en/"
        "us-visas/study/exchange/"
        "waiver-of-the-exchange-visitor/eligibility.html"
    ),
    "dos_2024_skills_list_update": (
        "https://travel.state.gov/content/travel/en/"
        "News/visas-news/"
        "exchange-visitor-skills-list-update-in-federal-register.html"
    ),
    "dos_advisory_opinion": (
        "https://travel.state.gov/content/travel/en/"
        "us-visas/visa-information-resources/"
        "advisory-opinions.html"
    ),
}


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_file(path, expected_sha):
    if not path.is_file():
        raise FileNotFoundError(path)

    actual_sha = sha256_bytes(path.read_bytes())

    if actual_sha != expected_sha:
        raise ValueError(
            f"SHA-256 불일치: {path}\n"
            f"예상: {expected_sha}\n"
            f"실제: {actual_sha}"
        )


def normalize(text):
    return re.sub(r"\s+", "", text).casefold()


def require_text(text, phrases, label):
    normalized = normalize(text)

    for phrase in phrases:
        if normalize(phrase) not in normalized:
            raise ValueError(
                f"{label}: PDF 원문 누락 - {phrase}"
            )


def extract_faq(text, number):
    """
    FAQ 번호를 기준으로 질문과 답변을 추출한다.

    본 PDF에서는 Q39/Q40/Q43/Q48이
    모두 PDF 물리 9쪽에 존재한다.
    """
    q_pattern = re.compile(
        rf"(?m)^\s*Q{number}\.\s*"
    )

    a_pattern = re.compile(
        rf"(?m)^\s*A{number}\.\s*"
    )

    q_match = q_pattern.search(text)
    a_match = a_pattern.search(text)

    if q_match is None or a_match is None:
        raise ValueError(
            f"FAQ Q{number}/A{number} 찾기 실패"
        )

    if q_match.end() > a_match.start():
        raise ValueError(
            f"FAQ {number}: 질문·답변 위치 오류"
        )

    question = text[
        q_match.end():a_match.start()
    ].strip()

    # 현재 답변 뒤의 다음 FAQ 질문을 찾는다.
    next_question = re.search(
        r"(?m)^\s*Q\d{1,2}\.\s*",
        text[a_match.end():],
    )

    if next_question:
        answer_end = (
            a_match.end() + next_question.start()
        )
    else:
        answer_end = len(text)

    answer = text[
        a_match.end():answer_end
    ].strip()

    if not question or not answer:
        raise ValueError(
            f"FAQ {number}: 질문 또는 답변이 비어 있음"
        )

    return {
        "number": number,
        "question": question,
        "answer": answer,
        "question_sha256": sha256_bytes(
            question.encode("utf-8")
        ),
        "answer_sha256": sha256_bytes(
            answer.encode("utf-8")
        ),
        "physical_pdf_page": 9,
        "printed_page": (
            18 if number == 48 else 17
        ),
        "source_pdf_sha256": PDF_SHA,
        "extraction_status": "source_text_extracted",
        "legal_meaning_approved": False,
    }


def evidence(printed_page):
    return {
        "printed_page": printed_page,
        "physical_pdf_page": 9,
        "candidate_id": (
            f"WEST-2026H2-LP{printed_page:02d}"
        ),
        "source_pdf_sha256": PDF_SHA,
    }


def save_new_or_verify(path, data):
    raw = (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                "기존 파일 내용과 다르므로 "
                f"덮어쓰지 않습니다: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        status = "CREATED"

    return status, sha256_bytes(raw)


print("===== STEP 64-60 WEST 비자·인턴십 의미 검수 =====")


# ============================================================
# 1. 입력 무결성 검사
# ============================================================

verify_file(PDF, PDF_SHA)
verify_file(REGISTER, REGISTER_SHA)

register = json.loads(
    REGISTER.read_text(encoding="utf-8")
)

assert register["program_id"] == "US-WEST-01"
assert register["notice_period"] == "2026_second_half"
assert register["original_issue_count"] == 16
assert register["additional_field_task_count"] == 7

assert register["approved_for_user_answers"] is False
assert register["approved_for_embedding"] is False
assert register["automatic_eligibility_rules_enabled"] is False

print("[PASS] 공식 PDF 및 STEP 64-58 결과 SHA-256")


# ============================================================
# 2. FAQ 원문 추출
# ============================================================

with pymupdf.open(PDF) as doc:
    if len(doc) != 11:
        raise ValueError("PDF 페이지 수가 11이 아닙니다.")

    faq_text = doc[8].get_text()

faq = {}

for number in FAQ_NUMBERS:
    item = extract_faq(faq_text, number)
    faq[str(number)] = item

    print(
        f"[PASS] FAQ Q{number}/A{number} 원문 추출"
    )

# 추출된 문답에 핵심 문구가 포함되는지 확인
require_text(
    faq["39"]["answer"],
    [
        "간호학/의학",
        "medical patient care or contact",
        "금지",
    ],
    "FAQ Q39"
)

require_text(
    faq["40"]["answer"],
    [
        "전공 관련 분야",
        "복수전공",
        "현지중개기관",
    ],
    "FAQ Q40"
)

require_text(
    faq["43"]["answer"],
    [
        "J-1",
        "2년간 본국",
        "귀국",
    ],
    "FAQ Q43"
)

require_text(
    faq["48"]["answer"],
    [
        "2년 본국거주의무",
        "웨이버",
        "H",
        "L",
        "K",
    ],
    "FAQ Q48"
)

print("[PASS] FAQ 4개 답변의 핵심 문맥 확인")


# ============================================================
# 3. 공고 원문과 법적 적용 범위 분리
# ============================================================

review_items = {
    "internship_patient_care": {
        "related_faq": [39],
        "evidence": [evidence(17)],
        "notice_meaning": (
            "공고는 간호학·의학 전공자의 "
            "환자 직접 접촉 인턴십을 제한한다고 설명함."
        ),
        "prohibited_inference": (
            "의료계열 전공자 전체가 WEST에 "
            "지원할 수 없다고 단정하지 않음."
        ),
        "further_verification": (
            "구체적인 인턴십 업무의 환자 접촉 여부와 "
            "적용되는 J-1 프로그램 규정 검토 필요."
        ),
        "validation_status": "needs_review",
    },

    "internship_field_matching": {
        "related_faq": [40],
        "evidence": [evidence(17)],
        "notice_meaning": (
            "전공 관련 분야 인턴십이 원칙이며, "
            "복수전공·기타 경험이 고려될 수 있음."
        ),
        "prohibited_inference": (
            "희망 기업이나 특정 인턴십 분야로 "
            "반드시 배정된다고 단정하지 않음."
        ),
        "further_verification": (
            "실제 현지중개기관의 배치 기준 "
            "및 참가자 개별 경력 확인 필요."
        ),
        "validation_status": "needs_review",
    },

    "j1_two_year_home_residency": {
        "related_faq": [43, 48],
        "evidence": [
            evidence(17),
            evidence(18),
        ],
        "notice_meaning": (
            "공고는 WEST 참가자의 귀국 및 "
            "2년 본국거주의무를 설명하고 있음."
        ),
        "external_legal_context": (
            "미국 국무부는 INA 212(e) 적용 근거로 "
            "정부재정지원, 해당 전문기술 목록, "
            "대학원 수준 의학교육·훈련 등을 제시함."
        ),
        "prohibited_inference": (
            "모든 J-1 비자 소지자가 무조건 "
            "212(e) 적용 대상이라고 판단하지 않음. "
            "WEST의 정부지원 사실만으로 "
            "개별 참가자의 법적 상태를 "
            "자동 확정하지 않음."
        ),
        "further_verification": (
            "실제 프로그램 재원, DS-2019, "
            "비자 관련 서류, 미국 국무부 안내 및 "
            "필요시 Advisory Opinion 확인."
        ),
        "official_reference_ids": [
            "dos_212e_eligibility",
            "dos_2024_skills_list_update",
            "dos_advisory_opinion",
        ],
        "validation_status": "needs_legal_review",
    },

    "j1_waiver": {
        "related_faq": [48],
        "evidence": [evidence(18)],
        "notice_meaning": (
            "공고는 특정 미국 비자 취득과 관련해 "
            "2년 본국거주의무 면제 신청을 안내함."
        ),
        "prohibited_inference": (
            "웨이버가 모든 신청자에게 허용되거나 "
            "신청만으로 승인된다고 판단하지 않음."
        ),
        "further_verification": (
            "개인의 212(e) 적용 여부, "
            "면제 사유·절차 및 미국 정부 결정 확인."
        ),
        "official_reference_ids": [
            "dos_212e_eligibility",
            "dos_advisory_opinion",
        ],
        "validation_status": "needs_legal_review",
    },
}


# ============================================================
# 4. 기존 이슈와 연결
# ============================================================

relevant_original_issues = []

for issue in register["original_issues"]:
    text = (
        str(issue.get("title", ""))
        + " "
        + str(issue.get("detail", ""))
    ).casefold()

    if any(
        keyword in text
        for keyword in (
            "j-1",
            "비자",
            "인턴십",
            "본국거주",
            "웨이버",
        )
    ):
        relevant_original_issues.append({
            "record_id": issue["record_id"],
            "title": issue["title"],
            "review_status": "needs_review",
        })

# 키워드 매칭은 관련 이슈의 후보 연결이며
# 원래 이슈를 삭제하거나 해결 처리하지 않는다.


# ============================================================
# 5. 검토 결과 생성
# ============================================================

result = {
    "dataset_type": "west_visa_internship_semantic_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_pdf_sha256": PDF_SHA,
    "review_register_sha256": REGISTER_SHA,
    "external_reference_checked_date": "2026-10-21",
    "external_reference_scope": (
        "미국 국무부의 일반적인 212(e) 안내. "
        "개별 WEST 참가자 법률 판단은 미수행."
    ),
    "us_official_reference_urls": US_OFFICIAL_SOURCES,
    "faq_original_text": faq,
    "review_items": review_items,
    "related_original_issue_candidates": (
        relevant_original_issues
    ),
    "source_meaning_notes_recorded": True,
    "individual_visa_applicability_determined": False,
    "legal_review_completed": False,
    "all_manual_issues_resolved": False,
    "current_policy_fully_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_visa_internship_review_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_sha256": PDF_SHA,
    "input_review_register_sha256": REGISTER_SHA,
    "faq_numbers_extracted": list(FAQ_NUMBERS),
    "faq_count": len(faq),
    "review_item_count": len(review_items),
    "related_original_issue_candidates": len(
        relevant_original_issues
    ),
    "issues_automatically_resolved": 0,
    "legal_decisions_automatically_made": 0,
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}


# ============================================================
# 6. 새 결과 저장
# ============================================================

state, result_sha = save_new_or_verify(
    OUTPUT, result
)

audit["result_sha256"] = result_sha

audit_state, audit_sha = save_new_or_verify(
    AUDIT, audit
)


# ============================================================
# 7. 최종 무결성 확인
# ============================================================

verify_file(PDF, PDF_SHA)
verify_file(REGISTER, REGISTER_SHA)
verify_file(OUTPUT, result_sha)
verify_file(AUDIT, audit_sha)

print("\n===== STEP 64-60 최종 결과 =====")
print("FAQ 원문 추출:", len(faq))
print("의미 검토 항목:", len(review_items))
print(
    "관련 기존 이슈 후보:",
    len(relevant_original_issues)
)
print("자동 해결한 이슈:", 0)
print("법적 자동 판정:", 0)

print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)

print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)

print("원본 변경: 없음")
print("법률 최종 검토: 미완료")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
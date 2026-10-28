
from pathlib import Path
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT / "data/processed/usa/employment/west/2026_second_half"
)

PDF = (
    ROOT
    / "data/raw/usa/employment/west/2026_second_half"
    / "west_2026_second_half_notice.pdf"
)

INTEGRATED = (
    BASE / "west_2026_second_half_integrated_audit.json"
)

OUTPUT = (
    BASE / "west_2026_second_half_remaining_fields_review.json"
)

AUDIT = (
    BASE / "west_2026_second_half_remaining_fields_audit.json"
)

PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

INTEGRATED_SHA = (
    "a1e29f60f5e73af7946d72f85418af5"
    "e0cdb5cb5ec8a03f0fee6977869893ec7"
)

# 각 필드의 검사 대상 물리 PDF 페이지.
# 물리 1쪽은 인쇄 1~2쪽에 해당한다.
REVIEW_ITEMS = {
    "vulnerable_group_evidence": {
        "pages": [5],
        "printed_pages": [9],
        "phrases": [
            "취업취약계층",
            "기초생활수급자",
            "차상위계층",
            "장애인",
            "다문화가족",
            "북향민",
        ],
        "summary": (
            "취업취약계층 범주 및 증빙서류 유형 확인"
        ),
        "remaining_review": (
            "지원자 유형별 세부 증빙 분기와 "
            "서류 유효성은 개별 검토 필요"
        ),
    },
    "eligibility_exceptions": {
        "pages": [1, 6],
        "printed_pages": [2, 11],
        "phrases": [
            "복수 국적자",
            "외국 소재 대학",
            "WEST 프로그램 기 참가자",
            "Q1.",
            "Q2.",
            "Q3.",
        ],
        "summary": (
            "지원 제한 및 FAQ 자격 관련 문구 확인"
        ),
        "remaining_review": (
            "FAQ Q3의 선발 회차 예시 불일치와 "
            "개인별 자격 적용은 별도 검토"
        ),
    },
    "internship_restrictions": {
        "pages": [9],
        "printed_pages": [17],
        "phrases": [
            "Q39.",
            "간호학/의학",
            "medical patient care or contact",
            "Q40.",
        ],
        "summary": (
            "의료 분야의 환자 직접 접촉 인턴십 "
            "제한 설명 확인"
        ),
        "remaining_review": (
            "모든 의료 관련 인턴십을 일괄 금지하는 "
            "규칙으로 변환하지 않음"
        ),
    },
    "j1_visa_conditions": {
        "pages": [9],
        "printed_pages": [17, 18],
        "phrases": [
            "Q43.",
            "Q48.",
            "2년",
            "웨이버",
        ],
        "summary": (
            "J-1 비자 및 본국거주의무 관련 "
            "공고 설명 확인"
        ),
        "remaining_review": (
            "현행 미국 법률, 비자 유형 및 "
            "개인별 적용 범위 별도 법률 검증 필요"
        ),
    },
    "graduation_evidence_examples": {
        "pages": [10],
        "printed_pages": [19],
        "phrases": [
            "붙임4",
            "학자금대출",
            "장학금 신청증명서",
            "졸업생",
        ],
        "summary": (
            "학자금 지원구간 통지서 발급이 "
            "불가능한 졸업생의 증빙 예시 확인"
        ),
        "remaining_review": (
            "졸업생의 실제 발급 가능 서류와 "
            "지원구간 적용 조건은 별도 검토"
        ),
    },
    "score_report_identifiers": {
        "pages": [6, 10, 11],
        "printed_pages": [12, 20, 21, 22],
        "phrases": [
            "Registration Number",
            "Test ID",
            "수험번호",
            "G-TELP Speaking",
        ],
        "summary": (
            "TOEIC·OPIc·G-TELP 등 "
            "시험별 등록번호 식별 안내 확인"
        ),
        "remaining_review": (
            "시험별 입력 형식은 확인 가능하나 "
            "개별 성적표의 진위 검증은 별도"
        ),
    },
    "toeic_speaking_conversion_reference": {
        "pages": [10],
        "printed_pages": [20],
        "phrases": [
            "TOEIC Speaking",
            "ACTFL",
            "200점 만점",
        ],
        "summary": (
            "TOEIC Speaking ACTFL 등급 "
            "환산표 및 숫자 점수 입력 안내 확인"
        ),
        "remaining_review": (
            "이미지 기반 환산표의 전체 점수-등급 "
            "대응은 독립 검증 전까지 사용 금지"
        ),
    },
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
    return re.sub(r"\s+", "", text).lower()


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
                f"기존 파일과 내용이 다릅니다: {path}"
            )
        status = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as handle:
            handle.write(raw)
        status = "CREATED"

    return status, sha256(raw)


def refs(item):
    return [
        {
            "printed_page": page,
            "physical_pdf_page": (page + 1) // 2,
            "candidate_id": (
                f"WEST-2026H2-LP{page:02d}"
            ),
            "source_pdf_sha256": PDF_SHA,
        }
        for page in item["printed_pages"]
    ]


print("===== STEP 64-57 WEST 잔여 7개 필드 검수 =====")

# 1. 기존 결과 및 공식 PDF 검증
verify(PDF, PDF_SHA)
verify(INTEGRATED, INTEGRATED_SHA)

previous = json.loads(
    INTEGRATED.read_text(encoding="utf-8")
)

assert previous["program_id"] == "US-WEST-01"
assert previous["original_policy_field_count"] == 27
assert previous["approved_for_user_answers"] is False
assert previous["approved_for_embedding"] is False
assert previous["automatic_eligibility_rules_enabled"] is False

remaining = set(
    previous["fields_without_separate_review_data"]
)

if remaining != set(REVIEW_ITEMS):
    raise ValueError(
        "STEP 64-56 잔여 필드 목록 불일치\n"
        f"기존: {sorted(remaining)}\n"
        f"현재: {sorted(REVIEW_ITEMS)}"
    )

print("[PASS] 공식 PDF 및 통합 감사 파일 SHA-256")
print("[PASS] 잔여 필드 7개 목록 일치")

# 2. PDF 원문 읽기
with pymupdf.open(PDF) as doc:
    if len(doc) != 11:
        raise ValueError("PDF 물리 페이지 수 불일치")

    page_texts = [page.get_text() for page in doc]

# 3. 각 필드의 근거 문구 검사
fields = {}
total_checks = 0

for field_name, item in REVIEW_ITEMS.items():
    source_text = "\n".join(
        page_texts[page - 1]
        for page in item["pages"]
    )

    normalized = normalize(source_text)
    evidence_checks = []

    for phrase in item["phrases"]:
        found = normalize(phrase) in normalized

        if not found:
            raise ValueError(
                f"{field_name}: 원문에서 "
                f"근거를 찾지 못함: {phrase}"
            )

        evidence_checks.append({
            "phrase": phrase,
            "found_in_pdf": True,
        })
        total_checks += 1

    fields[field_name] = {
        "field": field_name,
        "source_summary": item["summary"],
        "source_phrase_checks": evidence_checks,
        "evidence": refs(item),
        "source_presence_verified": True,
        "source_semantics_fully_verified": False,
        "remaining_review": item["remaining_review"],
        "validation_status": "needs_review",
        "approved_for_user_answers": False,
        "approved_for_embedding": False,
        "automatic_eligibility_rules_enabled": False,
    }

    print(
        f"[PASS] {field_name}: "
        f"{len(evidence_checks)}개 근거 문구"
    )

# 4. 결과 생성
result = {
    "dataset_type": "west_remaining_fields_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_pdf_sha256": PDF_SHA,
    "integrated_audit_sha256": INTEGRATED_SHA,
    "reviewed_field_count": len(fields),
    "fields": fields,
    "all_field_source_presence_verified": True,
    "semantic_review_completed": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_remaining_fields_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "input_pdf_sha256": PDF_SHA,
    "input_integrated_sha256": INTEGRATED_SHA,
    "remaining_fields_expected": 7,
    "remaining_fields_with_evidence": len(fields),
    "source_phrase_checks_passed": total_checks,
    "fields_semantically_approved": 0,
    "source_presence_verified": True,
    "semantic_review_completed": False,
    "current_policy_verified": False,
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 5. 원본을 변경하지 않고 새 파일만 저장
state, result_sha = save_new_or_verify(
    OUTPUT, result
)

audit["result_sha256"] = result_sha

audit_state, audit_sha = save_new_or_verify(
    AUDIT, audit
)

# 6. 저장 후 입력 파일 재검증
verify(PDF, PDF_SHA)
verify(INTEGRATED, INTEGRATED_SHA)

print("\n===== STEP 64-57 최종 결과 =====")
print("검수 대상 필드:", len(fields))
print("PDF 근거 문구 검사:", total_checks)
print("근거 문구 확인 실패:", 0)
print("정책 의미 최종 승인:", 0)

print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)

print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)

print("원본 변경: 없음")
print("현행 정책 검증: 미완료")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
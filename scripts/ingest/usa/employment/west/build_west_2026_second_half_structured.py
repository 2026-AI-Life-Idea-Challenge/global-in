
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]

BASE = (
    ROOT / "data/processed/usa/employment/west"
    / "2026_second_half"
)

SOURCE = (
    BASE / "west_2026_second_half_logical_candidates.jsonl"
)
SPLIT_REPORT = (
    BASE / "west_2026_second_half_logical_split_report.json"
)

OUTPUT = BASE / "west_2026_second_half_structured_draft.json"
REPORT = BASE / "west_2026_second_half_structure_audit.json"

EXPECTED_SOURCE_SHA = (
    "bf9dc2eda84f002e862fd3019569fa60"
    "c5f82f4e24992eeff4dd4bff8d6b1aa2"
)
EXPECTED_REPORT_SHA = (
    "cd6eb01b6c95a02f5b3353d0086548698"
    "f3dd25631156ef54064d418e5d8358d"
)
EXPECTED_PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)

# 시각 검수에서 확인한 페이지의 주제별 분류.
# 페이지 분류는 확정된 자격 판정 규칙이 아니다.
SECTIONS = {
    "program_overview": {
        "pages": [1, 2],
        "description": "모집 개요, 프로그램 구성, 기본 지원 자격",
    },
    "application": {
        "pages": [3, 4, 5],
        "description": "접수 기간, 신청 절차, 제출서류",
    },
    "financial_support": {
        "pages": [6, 7],
        "description": "단기·중기 참가비, 정부지원금, 대출",
    },
    "selection_and_documents": {
        "pages": [8, 9, 10],
        "description": "현지중개기관, 증빙서류, 선발 일정",
    },
    "faq": {
        "pages": list(range(11, 19)),
        "description": "지원·학적·비용·인턴십·비자 FAQ",
    },
    "appendices": {
        "pages": [19, 20, 21, 22],
        "description": "증빙서류 및 어학시험 성적표 예시",
    },
}

# 추출 후보와 별개로 사람이 검수해야 하는 필드
REVIEW_FIELDS = {
    "program_overview": [
        "short_term_capacity",
        "medium_term_capacity",
        "academic_status_eligibility",
        "language_score_requirements",
        "graduation_date_conditions",
    ],
    "application": [
        "application_start",
        "application_deadline",
        "university_recommendation",
        "student_application_procedure",
        "graduate_application_procedure",
    ],
    "financial_support": [
        "short_term_participation_fee_usd",
        "medium_term_participation_fee_usd",
        "support_by_income_bracket",
        "airfare_support_krw",
        "living_cost_support_krw",
        "loan_eligibility_by_academic_status",
    ],
    "selection_and_documents": [
        "selection_schedule",
        "required_documents_by_applicant_type",
        "vulnerable_group_evidence",
    ],
    "faq": [
        "faq_question_answer_boundaries",
        "eligibility_exceptions",
        "payment_rules",
        "internship_restrictions",
        "j1_visa_conditions",
    ],
    "appendices": [
        "graduation_evidence_examples",
        "toeic_speaking_conversion_reference",
        "score_report_identifiers",
    ],
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified_read(path, expected):
    assert path.is_file(), f"파일 없음: {path}"
    raw = path.read_bytes()
    assert digest(raw) == expected, (
        f"SHA-256 불일치: {path}"
    )
    return raw


def json_bytes(value):
    return (
        json.dumps(value, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def save_or_verify(path, raw):
    if path.exists():
        assert path.read_bytes() == raw, (
            f"기존 파일과 충돌: {path}"
        )
        return "EXISTS_VERIFIED"

    with path.open("xb") as f:
        f.write(raw)

    assert path.read_bytes() == raw
    return "CREATED"


print("===== STEP 64-50 WEST 하반기 구조화 초안 =====")

# 1. 이전 단계 파일 검증
source_raw = verified_read(
    SOURCE, EXPECTED_SOURCE_SHA
)

report_raw = verified_read(
    SPLIT_REPORT, EXPECTED_REPORT_SHA
)

pages = [
    json.loads(line)
    for line in source_raw.decode("utf-8").splitlines()
    if line.strip()
]

split_report = json.loads(
    report_raw.decode("utf-8")
)

assert len(pages) == 22
assert split_report["logical_page_candidates"] == 22
assert split_report["source_pdf_sha256"] == EXPECTED_PDF_SHA

by_number = {
    p["logical_page_number_candidate"]: p
    for p in pages
}

assert set(by_number) == set(range(1, 23))

all_ids = [
    block_id
    for page in pages
    for block_id in page["block_ids"]
]

assert len(all_ids) == 578
assert len(set(all_ids)) == 578

for page in pages:
    assert digest(
        page["text"].encode("utf-8")
    ) == page["text_sha256"]

    assert page["source_pdf_sha256"] == (
        EXPECTED_PDF_SHA
    )

print("[PASS] 22개 논리 페이지·578개 블록 검증")

# 2. 페이지 중복 및 누락 방지
assigned_pages = [
    n
    for section in SECTIONS.values()
    for n in section["pages"]
]

assert len(assigned_pages) == 22
assert len(set(assigned_pages)) == 22
assert set(assigned_pages) == set(range(1, 23))

print("[PASS] 주제별 페이지 분류 누락·중복 없음")

# 3. 근거 연결 구조 생성
sections = {}

for section_name, definition in SECTIONS.items():
    evidence_pages = []

    for number in definition["pages"]:
        page = by_number[number]

        evidence_pages.append({
            "logical_page_candidate": number,
            "physical_pdf_page": (
                page["physical_pdf_page"]
            ),
            "side": page["side"],
            "candidate_id": page["candidate_id"],
            "image_path": page["image_path"],
            "image_sha256": page["image_sha256"],
            "source_text": page["text"],
            "source_text_sha256": page["text_sha256"],
            "source_block_ids": page["block_ids"],
        })

    sections[section_name] = {
        "description": definition["description"],
        "logical_pages": definition["pages"],
        "evidence_pages": evidence_pages,
        "fields_pending_semantic_review": {
            field: {
                "value": None,
                "validation_status": "needs_review",
                "evidence_page_candidates": (
                    definition["pages"]
                ),
            }
            for field in REVIEW_FIELDS[section_name]
        },
        "semantic_review_status": "needs_review",
        "table_cell_alignment_verified": False,
    }

# 4. 구조화 초안
structured = {
    "dataset_type": "west_structured_draft",
    "country": "US",
    "program_id": "US-WEST-01",
    "program_name": "한미 대학생 연수(WEST)",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "official_notice_url": (
        "https://www.niied.go.kr/web/main/"
        "nid/niied_board/5749"
    ),
    "source_pdf_sha256": EXPECTED_PDF_SHA,
    "source_logical_candidates_sha256": (
        EXPECTED_SOURCE_SHA
    ),
    "physical_pdf_pages": 11,
    "logical_page_candidates": 22,
    "source_text_blocks": 578,
    "sections": sections,
    "review_status": "needs_review",
    "semantic_review_completed": False,
    "all_tables_verified": False,
    "current_application_open_verified": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 5. 감사 보고서
audit = {
    "dataset_type": "west_structure_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_sha256": EXPECTED_PDF_SHA,
    "input_sha256": EXPECTED_SOURCE_SHA,
    "section_count": len(sections),
    "section_page_counts": {
        name: len(value["logical_pages"])
        for name, value in sections.items()
    },
    "total_logical_pages": len(assigned_pages),
    "total_blocks": len(all_ids),
    "missing_pages": sorted(
        set(range(1, 23)) - set(assigned_pages)
    ),
    "duplicate_pages": (
        len(assigned_pages) - len(set(assigned_pages))
    ),
    "semantic_fields_pending_review": sum(
        len(fields)
        for fields in REVIEW_FIELDS.values()
    ),
    "semantic_values_auto_filled": 0,
    "original_files_modified": False,
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "validation_status": "needs_review",
}

structured_raw = json_bytes(structured)
audit["structured_file_sha256"] = digest(structured_raw)
audit_raw = json_bytes(audit)

# 6. 기존 결과 충돌 검사 및 저장
for path, data in (
    (OUTPUT, structured_raw),
    (REPORT, audit_raw),
):
    state = save_or_verify(path, data)
    print(
        f"[PASS] {state}: "
        f"{path.relative_to(ROOT)}"
    )
    print("SHA-256:", digest(data))

# 7. 저장 후 재검증
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == structured

assert json.loads(
    REPORT.read_text(encoding="utf-8")
) == audit

assert digest(SOURCE.read_bytes()) == (
    EXPECTED_SOURCE_SHA
)

assert digest(SPLIT_REPORT.read_bytes()) == (
    EXPECTED_REPORT_SHA
)

assert audit["missing_pages"] == []
assert audit["duplicate_pages"] == 0

print("[PASS] 결과 재읽기·원본 불변")

print("\n===== STEP 64-50 최종 결과 =====")
print("구조화 섹션:", len(sections))
print("논리 페이지:", len(assigned_pages))
print("원본 텍스트 블록:", len(all_ids))
print(
    "의미 검수 대기 필드:",
    audit["semantic_fields_pending_review"]
)
print("자동 입력된 정책 값:", 0)
print("원본 데이터 변경: 없음")
print("법률·정책 의미 검수: 미완료")
print("답변용 승인: False")
print("임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
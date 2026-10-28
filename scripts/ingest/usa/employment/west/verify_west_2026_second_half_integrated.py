
from pathlib import Path
import hashlib
import json
from collections import Counter

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

OUTPUT = BASE / "west_2026_second_half_integrated_audit.json"

EXPECTED_SHA = {
    "pdf": (
        "d04abdc458ad0a4a1f18196c9fdcb05"
        "f4ba39821183e0d77aaa5fa5f129a80e2"
    ),
    "draft": (
        "977cd6b2d0fc2ac9f88b3c75027ac0c"
        "e665b1a38a37cb92339b4b8870fffbe9e"
    ),
    "eligibility_candidates": (
        "7b33b3a374ee77734d64d63a10b6b5"
        "ed78ca7098d97711fb1e21ad0a1169e0b7"
    ),
    "eligibility": (
        "b54407e89beebcd1218415d29e5a6c2"
        "0263fecd41105b7c779ea8c98ca42b5ba"
    ),
    "application": (
        "d2bbc9e8d254f70441de6ac1c2fdf0ed"
        "70a405ddd72ad378b3013fb9e258ee31"
    ),
    "financial": (
        "8d381edebe88569b087050cedcd8046"
        "f5adae0dd30c4b0e19ea30372f657ca3a"
    ),
    "selection": (
        "a2b8e320f65228e1650439f4663a23c"
        "0f6608db2c9edae52aee2f61dbce5c505"
    ),
}

FILES = {
    "draft": "west_2026_second_half_structured_draft.json",
    "eligibility_candidates": (
        "west_2026_second_half_eligibility_review.json"
    ),
    "eligibility": (
        "west_2026_second_half_eligibility_source_verified.json"
    ),
    "application": (
        "west_2026_second_half_application_source_verified.json"
    ),
    "financial": (
        "west_2026_second_half_financial_source_verified.json"
    ),
    "selection": (
        "west_2026_second_half_selection_faq_review.json"
    ),
}

# STEP 64-50에서 정의한 원래 27개 필드.
# 각 필드가 어느 후속 결과에서 다뤄졌는지 추적한다.
FIELD_MAPPING = {
    "program_overview": {
        "short_term_capacity": "eligibility",
        "medium_term_capacity": "eligibility",
        "academic_status_eligibility": "eligibility",
        "language_score_requirements": "eligibility",
        "graduation_date_conditions": "eligibility",
    },
    "application": {
        "application_start": "application",
        "application_deadline": "application",
        "university_recommendation": "application",
        "student_application_procedure": "application",
        "graduate_application_procedure": "application",
    },
    "financial_support": {
        "short_term_participation_fee_usd": "financial",
        "medium_term_participation_fee_usd": "financial",
        "support_by_income_bracket": "financial",
        "airfare_support_krw": "financial",
        "living_cost_support_krw": "financial",
        "loan_eligibility_by_academic_status": "selection",
    },
    "selection_and_documents": {
        "selection_schedule": "selection",
        "required_documents_by_applicant_type": "application",
        "vulnerable_group_evidence": None,
    },
    "faq": {
        "faq_question_answer_boundaries": "selection",
        "eligibility_exceptions": None,
        "payment_rules": "financial",
        "internship_restrictions": None,
        "j1_visa_conditions": None,
    },
    "appendices": {
        "graduation_evidence_examples": None,
        "toeic_speaking_conversion_reference": None,
        "score_report_identifiers": None,
    },
}

# None은 관련 내용이 원문에 없다는 뜻이 아니라
# 별도의 필드 단위 의미 검수가 아직 진행되지 않았다는 뜻이다.

errors = []
warnings = []


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def check(condition, name):
    if condition:
        print("[PASS]", name)
    else:
        errors.append(name)
        print("[FAIL]", name)


def load_verified(path, expected, name):
    if not path.is_file():
        raise FileNotFoundError(f"{name}: {path}")

    raw = path.read_bytes()

    if digest(raw) != expected:
        raise ValueError(f"{name}: SHA-256 불일치")

    return json.loads(raw.decode("utf-8"))


def check_protection(data, label):
    check(
        data.get("approved_for_user_answers") is False,
        f"{label}: 답변 승인 비활성화"
    )
    check(
        data.get("approved_for_embedding") is False,
        f"{label}: 임베딩 승인 비활성화"
    )
    check(
        data.get("automatic_eligibility_rules_enabled") is False,
        f"{label}: 자동 자격 판정 비활성화"
    )


def save_without_overwrite(path, data):
    raw = (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 보고서와 내용이 달라 덮어쓰지 않음: {path}"
            )
        state = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as handle:
            handle.write(raw)
        state = "CREATED"

    return state, digest(raw)


print("===== STEP 64-56 WEST 정책 통합 검사 =====")

if not PDF.is_file():
    raise FileNotFoundError(PDF)

check(
    digest(PDF.read_bytes()) == EXPECTED_SHA["pdf"],
    "공식 원본 PDF SHA-256"
)

data = {}

for key, filename in FILES.items():
    data[key] = load_verified(
        BASE / filename,
        EXPECTED_SHA[key],
        key
    )
    print(f"[PASS] 입력 파일 SHA-256: {key}")

    check(
        data[key].get("program_id") == "US-WEST-01",
        f"{key}: 프로그램 ID"
    )
    check(
        data[key].get("notice_period") == "2026_second_half",
        f"{key}: 모집 회차"
    )
    check_protection(data[key], key)

draft = data["draft"]
elig = data["eligibility"]
app = data["application"]
fin = data["financial"]
sel = data["selection"]

# 1. 원래 27개 필드 존재 여부
print("\n[1] 정책 필드 추적")

field_rows = []
original_fields = set()
mapped_fields = set()

for section_name, section in draft["sections"].items():
    expected_fields = set(
        section["fields_pending_semantic_review"]
    )
    mapping = FIELD_MAPPING.get(section_name, {})

    check(
        expected_fields == set(mapping),
        f"{section_name}: 기존 필드 목록 일치"
    )

    for field_name in sorted(expected_fields):
        source = mapping.get(field_name)

        original_fields.add(field_name)

        if source:
            mapped_fields.add(field_name)

        field_rows.append({
            "section": section_name,
            "field": field_name,
            "review_output": source,
            "source_data_exists": source is not None,
            "semantic_review_completed": False,
            "validation_status": "needs_review",
        })

check(len(field_rows) == 27, "원래 정책 필드 27개")
check(
    len(original_fields) == 27,
    "27개 필드명 중복 없음"
)

# 2. 모집 인원·어학성적 정합성
print("\n[2] 지원 자격·어학성적")

short = elig["programs"]["short_term"]
medium = elig["programs"]["medium_term"]

check(
    short["capacity_approx_persons"]["value"] == 71,
    "단기 모집 인원 71명 내외"
)
check(
    medium["capacity_approx_persons"]["value"] == 31,
    "중기 모집 인원 31명 내외"
)

check(
    short["english_general_any_of"]["value"] == {
        "TOEIC_min": 800,
        "GTELP_Level2_min": 76,
    },
    "단기 일반 영어성적"
)

check(
    medium["english_general_any_of"]["value"] == {
        "TOEIC_min": 750,
        "GTELP_Level2_min": 70,
    },
    "중기 일반 영어성적"
)

check(
    short["english_speaking_any_of"]["value"] == {
        "OPIc_min": "IM2",
        "TOEIC_Speaking_ACTFL_min": "IM2",
        "GTELP_Speaking_level_min_qualification": "Level 6 이상",
    },
    "단기 말하기 성적"
)

check(
    medium["english_speaking_any_of"]["value"] == {
        "OPIc_min": "IM1",
        "TOEIC_Speaking_ACTFL_min": "IM1",
        "GTELP_Speaking_level_min_qualification": "Level 7 이상",
    },
    "중기 말하기 성적"
)

# 3. 신청 마감일 교차 검사
print("\n[3] 신청 절차·일정")

application_deadline = (
    app["fields"]["application_deadline"]["value"]
)
selection_deadline = (
    sel["selection_schedule"]
       ["document_submission_deadline"]["value"]
)

check(
    application_deadline == selection_deadline,
    "신청 마감일 교차 일치"
)

# 4. 참가비·재정지원 구조 검사
print("\n[4] 참가비·지원금")

expected_fees = {
    "short_term": 7045,
    "medium_term": 8912,
}

total_brackets = 0

for program, expected_fee in expected_fees.items():
    item = fin["programs"][program]
    rows = item["support_brackets"]

    check(
        item["participation_fee_usd"] == expected_fee,
        f"{program}: 참가비"
    )

    check(
        len(rows) == 4,
        f"{program}: 지원구간 4개"
    )

    total_brackets += len(rows)

    for row in rows:
        check(
            row["participation_fee_support_usd"]
            + row["participation_fee_self_payment_usd"]
            == expected_fee,
            f"{program}/{row['bracket_id']}: 참가비 합산"
        )

check(total_brackets == 8, "지원금 표 8개 행")

# 5. FAQ 번호·검토 상태
print("\n[5] FAQ")

faq_index = sel["faq_index"]
faq_numbers = [
    item["question_number"]
    for item in faq_index
]

check(
    len(faq_index) == 49,
    "FAQ 인덱스 49개"
)
check(
    sorted(faq_numbers) == list(range(1, 50)),
    "FAQ Q1~Q49 중복·누락 없음"
)
check(
    sel["faq_semantics_verified"] is False,
    "FAQ 의미 검수 미완료 상태 유지"
)
check(
    fin["table_cell_alignment_verified_by_code"] is False,
    "재정지원 표 행·열 자동검증 미완료 상태 유지"
)

# 6. 수동 검토 이슈 집계
issue_counts = {
    "eligibility": len(
        elig["manual_review_issues"]
    ),
    "application": len(
        app["manual_review_issues"]
    ),
    "financial": len(
        fin["manual_review_issues"]
    ),
    "selection": len(
        sel["manual_review_issues"]
    ),
}

unmapped_fields = [
    item["field"]
    for item in field_rows
    if not item["source_data_exists"]
]

# 7. 결과
print("\n===== STEP 64-56 최종 결과 =====")
print("검사 오류:", len(errors))
print("원래 정책 필드:", len(field_rows))
print("후속 검토 자료 연결 필드:", len(mapped_fields))
print("별도 필드 검수 대기:", len(unmapped_fields))
print("검토 이슈 건수(단계별 단순 합):", sum(issue_counts.values()))

print("\n별도 검수 대기 필드:")
for item in unmapped_fields:
    print(" -", item)

if errors:
    print("\n검사 결론: FAIL")
    for error in errors:
        print("[ERROR]", error)
    print("기존 파일 변경: 없음")
    raise SystemExit(1)

audit = {
    "dataset_type": "west_integrated_policy_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_pdf_sha256": EXPECTED_SHA["pdf"],
    "input_hashes": EXPECTED_SHA,
    "original_policy_field_count": len(field_rows),
    "field_tracking": field_rows,
    "fields_with_followup_review_data": len(mapped_fields),
    "fields_without_separate_review_data": unmapped_fields,
    "manual_issue_counts_by_step": issue_counts,
    "manual_issues_not_deduplicated": True,
    "cross_file_consistency_passed": True,
    "semantic_review_completed": False,
    "current_policy_verified": False,
    "financial_table_alignment_verified_by_code": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
    "original_files_modified": False,
}

state, output_sha = save_without_overwrite(OUTPUT, audit)

print(f"\n[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", output_sha)
print("검사 결론: PASS — 기존 결과 간 정합성 검사")
print("정책 의미 최종 승인: 미완료")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
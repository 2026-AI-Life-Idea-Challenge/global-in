
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
APPLICATION = (
    BASE / "west_2026_second_half_application_source_verified.json"
)

OUTPUT = (
    BASE / "west_2026_second_half_financial_source_verified.json"
)
AUDIT = (
    BASE / "west_2026_second_half_financial_source_audit.json"
)

PDF_SHA = (
    "d04abdc458ad0a4a1f18196c9fdcb05"
    "f4ba39821183e0d77aaa5fa5f129a80e2"
)
APPLICATION_SHA = (
    "d2bbc9e8d254f70441de6ac1c2fdf0ed"
    "70a405ddd72ad378b3013fb9e258ee31"
)

EXCHANGE_RATE = 1472
AIRFARE_KRW = 2_000_000

# 공식 PDF 인쇄 6~7쪽의 표를 시각적으로 대조하여 전사.
# 순서: 참가비 정부지원, 본인부담, 최대 생활비, 최대 총액(천원).
TABLES = {
    "short_term": {
        "printed_page": 6,
        "duration_months": 6,
        "participation_fee_usd": 7045,
        "living_support_months_max": 6,
        "rows": [
            ("basic_near_poverty_to_5", 7045, 0, 8400, 24735),
            ("6_to_7", 3523, 3522, 4200, 13368),
            ("8_to_9", 2466, 4579, 4200, 11812),
            ("10", 1761, 5284, 2100, 7684),
        ],
    },
    "medium_term": {
        "printed_page": 7,
        "duration_months": 12,
        "participation_fee_usd": 8912,
        "living_support_months_max": 9,
        "rows": [
            ("basic_near_poverty_to_5", 8912, 0, 12600, 33665),
            ("6_to_7", 4456, 4456, 6300, 17833),
            ("8_to_9", 3119, 5793, 6300, 15865),
            ("10", 2228, 6684, 3150, 9916),
        ],
    },
}

BRACKET_LABELS = {
    "basic_near_poverty_to_5": "기초·차상위~5구간",
    "6_to_7": "6~7구간",
    "8_to_9": "8~9구간",
    "10": "10구간",
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


def check_pdf_phrases(text, phrases, label):
    normalized = normalize(text)
    for phrase in phrases:
        if normalize(phrase) not in normalized:
            raise ValueError(
                f"{label} 원문 확인 실패: {phrase}"
            )


def evidence(printed_page):
    return {
        "printed_page": printed_page,
        "physical_pdf_page": (printed_page + 1) // 2,
        "candidate_id": (
            f"WEST-2026H2-LP{printed_page:02d}"
        ),
        "source_pdf_sha256": PDF_SHA,
    }


def save_new_or_verify(path, data):
    raw = (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"다른 내용의 결과가 이미 존재함: {path}"
            )
        state = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        state = "CREATED"

    assert sha256(path.read_bytes()) == sha256(raw)
    return state, sha256(raw)


print("===== STEP 64-54 WEST 재정지원 원문 검수 =====")

# 1. 입력 무결성
verify(PDF, PDF_SHA)
verify(APPLICATION, APPLICATION_SHA)

previous = json.loads(
    APPLICATION.read_text(encoding="utf-8")
)

assert previous["program_id"] == "US-WEST-01"
assert previous["approved_for_user_answers"] is False
assert previous["approved_for_embedding"] is False
assert previous["automatic_eligibility_rules_enabled"] is False

print("[PASS] 공식 PDF 및 STEP 64-53 SHA-256")

# 2. PDF의 참가비 및 지원금 표 확인
with pymupdf.open(PDF) as doc:
    assert len(doc) == 11

    # 물리 3쪽: 인쇄 5~6쪽
    text_5_6 = doc[2].get_text()

    # 물리 4쪽: 인쇄 7~8쪽
    text_7_8 = doc[3].get_text()

check_pdf_phrases(
    text_5_6,
    [
        "7,045",
        "8,912",
        "2,000,000",
        "1,472",
        "24,735",
        "13,368",
        "11,812",
        "7,684",
    ],
    "인쇄 5~6쪽",
)

check_pdf_phrases(
    text_7_8,
    [
        "8,912",
        "4,456",
        "3,119",
        "2,228",
        "33,665",
        "17,833",
        "15,865",
        "9,916",
    ],
    "인쇄 7~8쪽",
)

print("[PASS] PDF 참가비·정부지원금 핵심 수치 확인")

# 3. 지원금 표의 산술 검증
programs = {}
calculation_checks = []

for program_id, table in TABLES.items():
    fee = table["participation_fee_usd"]
    months = table["living_support_months_max"]
    page = table["printed_page"]

    rows = []

    for (
        bracket,
        fee_support,
        self_payment,
        living_total,
        published_total_1000,
    ) in table["rows"]:

        # 참가비 지원액 + 본인 부담금 = 참가비
        assert fee_support + self_payment == fee, (
            f"{program_id}/{bracket}: 참가비 합산 오류"
        )

        # 정부지원총액은 참가비 정부지원액,
        # 왕복항공료, 생활비의 합계이다.
        computed_krw = (
            (fee_support + living_total) * EXCHANGE_RATE
            + AIRFARE_KRW
        )

        published_krw = published_total_1000 * 1000

        # 공고상 총액은 천원 단위 반올림 표기.
        # 실제 지급액의 정확한 산술 결과라고 단정하지 않음.
        assert abs(computed_krw - published_krw) < 1000, (
            f"{program_id}/{bracket}: 총액 불일치"
        )

        rows.append({
            "bracket_id": bracket,
            "bracket_label": BRACKET_LABELS[bracket],
            "participation_fee_support_usd": fee_support,
            "participation_fee_self_payment_usd": self_payment,
            "airfare_support_krw": AIRFARE_KRW,
            "living_support_max_usd": living_total,
            "living_support_months_max": months,
            "published_max_total_1000_krw": (
                published_total_1000
            ),
            "source_evidence": evidence(page),
            "source_transcription_status": (
                "visually_transcribed_pending_final_review"
            ),
            "validation_status": "needs_review",
        })

        calculation_checks.append({
            "program": program_id,
            "bracket": bracket,
            "fee_reconciliation": True,
            "total_rounded_consistently": True,
        })

    programs[program_id] = {
        "duration_months_max": table["duration_months"],
        "participation_fee_usd": fee,
        "airfare_support_krw": AIRFARE_KRW,
        "living_support_months_max": months,
        "support_brackets": rows,
        "source_evidence": evidence(page),
    }

print("[PASS] 8개 지원구간 참가비·지원총액 산술 검증")

# 4. 금액에 대한 유의사항 및 추가 검토 이슈
manual_issues = [
    {
        "issue": "실제 지급 환율",
        "status": "needs_review",
        "note": (
            "공고 표는 2026년 기준환율 1,472원을 사용. "
            "실제 생활비 지급에는 연도별 기준환율이 적용됨."
        ),
        "evidence": evidence(6),
    },
    {
        "issue": "개인별 학자금 지원구간 확정",
        "status": "needs_review",
        "note": (
            "공고의 지원구간별 금액을 개인에게 직접 적용할 수 없음. "
            "졸업생 및 재외국민 특별전형 관련 예외 확인 필요."
        ),
        "evidence": evidence(5),
    },
    {
        "issue": "최대 지원금과 실제 지급금 차이",
        "status": "needs_review",
        "note": (
            "표는 최대 지원총액이며 실제 지급 대상 기간, "
            "지원구간, 지급 환율 등을 별도로 확인해야 함."
        ),
        "evidence": evidence(6),
    },
    {
        "issue": "지원금 반환 및 대출 자격",
        "status": "needs_review",
        "note": (
            "프로그램 중단에 따른 환수와 학적별 "
            "어학연수비 대출 실행 제한은 별도 검토."
        ),
        "evidence": evidence(7),
    },
]

# 5. 결과 JSON
result = {
    "dataset_type": "west_financial_source_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "source_pdf_sha256": PDF_SHA,
    "application_source_sha256": APPLICATION_SHA,
    "published_exchange_rate_krw_per_usd": EXCHANGE_RATE,
    "programs": programs,
    "payment_notes": {
        "participation_fee_currency": "USD",
        "participation_fee_payment": "일시납",
        "airfare_and_living_support_currency": "KRW",
        "airfare_is_included_in_published_max_total": True,
        "published_max_total_is_guaranteed": False,
        "exchange_rate_is_guaranteed": False,
    },
    "manual_review_issues": manual_issues,
    "table_cell_alignment_verified_by_code": False,
    "validation_status": (
        "source_transcribed_policy_review_pending"
    ),
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "input_pdf_sha256": PDF_SHA,
    "input_application_sha256": APPLICATION_SHA,
    "program_count": len(programs),
    "support_brackets_verified_arithmetically": (
        len(calculation_checks)
    ),
    "arithmetic_checks": calculation_checks,
    "manual_review_issues": len(manual_issues),
    "source_numbers_checked_in_pdf": True,
    "table_cell_alignment_verified_by_code": False,
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 6. 새 파일 생성, 기존 결과 덮어쓰기 금지
state, result_sha = save_new_or_verify(
    OUTPUT, result
)

audit["result_sha256"] = result_sha

audit_state, audit_sha = save_new_or_verify(
    AUDIT, audit
)

# 7. 최종 확인
verify(PDF, PDF_SHA)
verify(APPLICATION, APPLICATION_SHA)

print("\n===== STEP 64-54 최종 결과 =====")
print("프로그램:", len(programs))
print("지원구간별 금액 행:", len(calculation_checks))
print("수동 검토 이슈:", len(manual_issues))
print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)
print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)
print("원본 변경: 없음")
print("표 행·열의 코드 검증: 미완료")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")
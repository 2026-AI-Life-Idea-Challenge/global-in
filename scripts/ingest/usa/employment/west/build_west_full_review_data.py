
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re

import pymupdf

ROOT = Path(__file__).resolve().parents[5]

RAW = ROOT / "data/raw/usa/employment/west"
PROCESSED = ROOT / "data/processed/usa/employment/west"

PDF = RAW / "west_2026_first_half_notice.pdf"

PREVIOUS = (
    PROCESSED / "west_2026_first_half_reviewed_data.json"
)

OUTPUT = (
    PROCESSED / "west_2026_first_half_full_review_data.json"
)

PDF_SHA = (
    "6f11ae189a6ec58bde63eb52c2e7eba"
    "80b6ec4ffde1f0620f1dca95200542c31"
)

PREVIOUS_SHA = (
    "c26e6d1b8295709062fd2b1df142764"
    "375569ad5d9784145d3f12bf9b126c67d"
)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def compact(text):
    return re.sub(r"\s+", "", text).casefold()


def serialize(data):
    return (
        json.dumps(data, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")


def page_reference(physical_page, side, anchors, category):
    return {
        "physical_pdf_page": physical_page,
        "printed_page": (
            physical_page * 2 - 1
            if side == "left"
            else physical_page * 2
        ),
        "side": side,
        "category": category,
        "verification_anchors": anchors,
        "source_pdf_sha256": PDF_SHA,
    }


print("===== STEP 64-15 WEST 전체 검수 데이터 구축 =====")

# 1. 원본 무결성 검사
pdf_raw = PDF.read_bytes()
previous_raw = PREVIOUS.read_bytes()

assert sha256(pdf_raw) == PDF_SHA
assert sha256(previous_raw) == PREVIOUS_SHA
assert not OUTPUT.exists(), "기존 출력 파일이 존재합니다."

previous = json.loads(previous_raw.decode("utf-8"))

assert previous["program_id"] == "US-WEST-01"
assert previous["automatic_eligibility_rules_enabled"] is False

print("[PASS] 기존 PDF / 검수 JSON SHA-256")

# 2. 중기 WEST 지원금 표
mid_term = {
    "participation_fee_usd": 8912,
    "airfare_support_krw": 2000000,
    "notice_exchange_rate_krw_per_usd": 1472,
    "brackets": [
        {
            "label": "기초·차상위~5구간",
            "fee_government_usd": 8912,
            "fee_self_usd": 0,
            "living_support_usd": 12600,
            "maximum_total_support_1000krw": 33665,
        },
        {
            "label": "6~7구간",
            "fee_government_usd": 4456,
            "fee_self_usd": 4456,
            "living_support_usd": 6300,
            "maximum_total_support_1000krw": 17833,
        },
        {
            "label": "8~9구간",
            "fee_government_usd": 3119,
            "fee_self_usd": 5793,
            "living_support_usd": 6300,
            "maximum_total_support_1000krw": 15865,
        },
        {
            "label": "소득 10분위",
            "fee_government_usd": 2228,
            "fee_self_usd": 6684,
            "living_support_usd": 3150,
            "maximum_total_support_1000krw": 9916,
        },
    ],
    "source": page_reference(
        4, "left",
        [
            "8,912", "4,456", "3,119", "2,228",
            "33,665", "17,833", "15,865", "9,916",
        ],
        "mid_term_financial_support",
    ),
    "current_amounts_verified": False,
}

for row in mid_term["brackets"]:
    assert (
        row["fee_government_usd"]
        + row["fee_self_usd"]
        == mid_term["participation_fee_usd"]
    )

print("[PASS] 중기 참가비 분담 합계")

# 3. 해당 회차 선발 일정
schedule = {
    "application_open": "2026-02-11",
    "application_deadline": "2026-03-18T17:00:00",
    "university_recommendation": {
        "start": "2026-03-19",
        "end": "2026-03-23",
    },
    "financial_bracket_review": {
        "start": "2026-03-19",
        "end": "2026-05-14",
    },
    "document_result": "2026-04-09T16:00:00",
    "first_interview": {
        "short_term": "2026-04-18",
        "mid_term": "2026-04-19",
    },
    "first_interview_result": "2026-04-23T16:00:00",
    "second_interview": {
        "start": "2026-04-24",
        "end": "2026-05-12",
    },
    "final_result": "2026-05-21T16:00:00",
    "participation_fee_payment": {
        "start": "2026-05-22",
        "end": "2026-05-29",
    },
    "additional_selection": {
        "start": "2026-06-01",
        "end": "2026-06-04",
    },
    "pre_departure_orientation": "2026-06-25",
    "visa_interviews": {
        "start": "2026-07-06",
        "end": "2026-07-07",
    },
    "departure_period": "2026-07",
    "language_study_start_period": "2026-08",
    "dates_subject_to_change": True,
    "application_currently_open": False,
    "source": page_reference(
        5, "right",
        ["4.9.", "4.18.", "4.24.", "5.21.", "5.22.", "7.6."],
        "selection_schedule",
    ),
}

# 4. 조건별 추가 근거
supplementary_facts = [
    {
        "fact_id": "student_financial_bracket_application",
        "description": (
            "재학생·휴학생·초과학기자·수료자·졸업유예자는 "
            "한국장학재단 지원구간 확인 신청 대상. "
            "실제 대출 실행과는 별개."
        ),
        "source": page_reference(
            7, "right",
            ["Q21.", "A21."],
            "financial_bracket",
        ),
        "eligibility_rule_enabled": False,
    },
    {
        "fact_id": "graduate_financial_bracket_documents",
        "description": (
            "졸업생은 한국장학재단의 WEST 지원구간 확인 "
            "신청 대신 소속 대학에 해당 증빙서류 제출."
        ),
        "source": page_reference(
            7, "right",
            ["졸업생", "Q24."],
            "conditional_documents",
        ),
        "eligibility_rule_enabled": False,
    },
    {
        "fact_id": "minimum_completion_period",
        "description": (
            "단기: 어학연수 8주·인턴십 12주 이상. "
            "중기: 어학연수 12주·인턴십 24주 이상."
        ),
        "source": page_reference(
            8, "right",
            ["Q34.", "Q35."],
            "program_completion",
        ),
        "eligibility_rule_enabled": False,
    },
    {
        "fact_id": "internship_placement",
        "description": (
            "공고의 FAQ에 따르면 참가자의 독자적인 "
            "구직활동이 아닌 지정 스폰서의 인턴십 "
            "배치 절차를 따름."
        ),
        "source": page_reference(
            8, "right",
            ["Q37."],
            "internship_placement",
        ),
        "eligibility_rule_enabled": False,
    },
    {
        "fact_id": "patient_contact_restriction",
        "description": (
            "공고 FAQ는 간호·의학 전공자의 환자 직접 "
            "접촉 인턴십이 금지된다고 안내함."
        ),
        "source": page_reference(
            9, "left",
            ["Q39."],
            "internship_restrictions",
        ),
        "eligibility_rule_enabled": False,
    },
    {
        "fact_id": "two_year_home_residency_notice",
        "description": (
            "공고 FAQ에서 J-1의 2년 본국 거주의무와 "
            "면제 절차를 안내함. 개인별 실제 적용 여부는 "
            "미국 공식 비자 기준으로 별도 확인 필요."
        ),
        "source": page_reference(
            9, "right",
            ["Q48."],
            "visa_legal_notice",
        ),
        "eligibility_rule_enabled": False,
        "independent_legal_verification_required": True,
    },
]

# 5. PDF의 실제 인쇄 영역과 핵심 문자열 대조
sources = [mid_term["source"], schedule["source"]]
sources += [item["source"] for item in supplementary_facts]

with pymupdf.open(stream=pdf_raw, filetype="pdf") as doc:
    assert len(doc) == 11

    for source in sources:
        page = doc[source["physical_pdf_page"] - 1]
        mid = page.rect.width / 2

        if source["side"] == "left":
            clip = pymupdf.Rect(
                0, 0, mid, page.rect.height
            )
        else:
            clip = pymupdf.Rect(
                mid, 0, page.rect.width, page.rect.height
            )

        original_text = compact(
            page.get_text("text", clip=clip, sort=True)
        )

        for anchor in source["verification_anchors"]:
            assert compact(anchor) in original_text, (
                f"근거 확인 실패: "
                f"PDF {source['physical_pdf_page']} "
                f"{source['side']} / {anchor}"
            )

print("[PASS] 중기 지원금·일정·FAQ 원문 위치 대조")

# 6. 통합 결과
data = {
    "dataset_type": "west_full_reviewed_information",
    "country": "US",
    "program_id": "US-WEST-01",
    "notice_period": "2026_first_half",
    "historical_notice": True,
    "original_reviewed_data_path": (
        PREVIOUS.relative_to(ROOT).as_posix()
    ),
    "original_reviewed_data_sha256": PREVIOUS_SHA,
    "source_pdf_path": PDF.relative_to(ROOT).as_posix(),
    "source_pdf_sha256": PDF_SHA,
    "mid_term_financial_support": mid_term,
    "selection_schedule": schedule,
    "supplementary_facts": supplementary_facts,
    "reviewed_printed_pages": [
        2, 4, 6, 7, 10, 14, 16, 17, 18,
    ],
    "review_scope": (
        "selected_values_and_faq_items_verified"
    ),
    "all_pdf_statements_individually_verified": False,
    "current_rules_verified": False,
    "validation_status": "partially_reviewed",
    "automatic_eligibility_rules_enabled": False,
    "recommendation_rules_enabled": False,
    "embedding_generated": False,
}

payload = serialize(data)

assert payload == serialize(data)
assert data["automatic_eligibility_rules_enabled"] is False

# 7. 저장 및 재검증
with OUTPUT.open("xb") as file:
    file.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(
    OUTPUT.read_text(encoding="utf-8")
) == data

assert PDF.read_bytes() == pdf_raw
assert PREVIOUS.read_bytes() == previous_raw

print("[PASS] 확장 검수 JSON 저장 및 재읽기")
print("[PASS] 기존 PDF / 기존 검수 JSON 불변")

print("\n===== STEP 64-15 최종 결과 =====")
print("프로그램:", data["program_id"])
print("중기 WEST 지원금:", len(mid_term["brackets"]), "구간")
print("선발 일정: 구조화 완료")
print("추가 검토 근거:", len(supplementary_facts), "개")
print("PDF 근거 위치 대조: PASS")
print("원본 불변: PASS")
print("결과 파일:", OUTPUT.relative_to(ROOT))
print("결과 SHA-256:", sha256(payload))
print("검수 상태:", data["validation_status"])
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")

from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "data/processed/usa/employment/west"

CANDIDATE = BASE / "west_2026_first_half_column_candidate.json"
DRAFT = BASE / "west_2026_first_half_program_draft.json"
OUTPUT = BASE / "west_2026_first_half_reviewed_data.json"

EXPECTED = {
    CANDIDATE: "31865507945b9a46c7485518364597ccf44978622c50242913dde822a481b8e3",
    DRAFT: "167127ae0759cbd22fd785b03d81fd6d82b0e83f7add9e19674b36f5854a9709",
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def compact(text):
    return re.sub(r"\s+", "", text).casefold()


def evidence(page, side, subject):
    return {
        "source_pdf": (
            "data/raw/usa/employment/west/"
            "west_2026_first_half_notice.pdf"
        ),
        "physical_pdf_page": page,
        "side": side,
        "printed_page": page * 2 if side == "right" else page * 2 - 1,
        "subject": subject,
        "review_basis": "user_supplied_official_page_image",
    }


print("===== STEP 64-14 WEST 검수 데이터 구축 =====")

# 기존 데이터 검증
inputs = {}
for path, expected_hash in EXPECTED.items():
    raw = path.read_bytes()
    assert sha256(raw) == expected_hash, f"SHA 불일치: {path}"
    inputs[path] = raw

candidate = json.loads(inputs[CANDIDATE].decode("utf-8"))
draft = json.loads(inputs[DRAFT].decode("utf-8"))

assert candidate["program_id"] == "US-WEST-01"
assert draft["program_id"] == "US-WEST-01"
assert candidate["page_count"] == 11
assert draft["automatic_eligibility_rules_enabled"] is False

print("[PASS] 기존 후보·초안 SHA-256")

# 제공된 이미지 3장의 PDF 위치
P2 = evidence(1, "right", "programs_and_eligibility")
P4 = evidence(2, "right", "application_and_documents")
P6 = evidence(3, "right", "fees_and_financial_support")

# 표의 열 순서는 제공된 이미지에서 대조한 값.
# 자동 자격 판정용 규칙은 생성하지 않는다.
data = {
    "dataset_type": "reviewed_program_information",
    "country": "US",
    "program_id": "US-WEST-01",
    "program_name": "WEST (Work, English Study, Travel)",
    "notice": {
        "notice_number": "2026-15",
        "period": "2026_first_half",
        "historical_notice": True,
        "current_application_status": "not_verified",
    },
    "programs": {
        "short_term": {
            "label": "단기 WEST",
            "maximum_duration_months": 6,
            "language_study_months": 2,
            "internship_months": {"min": 3, "max": 4},
            "travel_months": 1,
            "planned_selection_approx": 71,
            "participation_fee_usd": 7045,
            "evidence": P2,
        },
        "mid_term": {
            "label": "중기 WEST",
            "maximum_duration_months": 12,
            "language_study_months": 3,
            "internship_months": {"min": 6, "max": 8},
            "travel_months": 1,
            "planned_selection_approx": 35,
            "participation_fee_usd": 8912,
            "evidence": P2,
        },
        "duplicate_application_prohibited": True,
    },
    "eligibility": {
        "nationality_text": "대한민국 국적 소지자",
        "visa_condition_text": "미국 비자 발급에 결격사유가 없는 자",
        "student_status_text": (
            "지원 시점 기준 4년제 대학 4학기 이상 "
            "또는 전문대학 2학기 이상 이수한 재·휴학생"
        ),
        "recent_graduate_text": (
            "어학연수 시작일 기준 최근 1년 이내 졸업생 "
            "(본 회차 2025년 8월·2026년 2월 졸업자)"
        ),
        "university_recommendation_text": (
            "소속 대학의 지원자 추천 공문"
        ),
        "english_scores": {
            "group_relationship_in_notice": (
                "① 그룹과 ② 그룹을 모두 충족. "
                "그룹 안에서는 제시된 시험 중 하나 충족."
            ),
            "short_term": {
                "group_1": {
                    "TOEIC_min": 800,
                    "GTELP_Level2_min": 76,
                },
                "group_2": {
                    "OPIc_min": "IM2",
                    "TOEIC_Speaking_min": "IM2",
                    "GTELP_Speaking_min_level": 6,
                },
            },
            "mid_term": {
                "group_1": {
                    "TOEIC_min": 750,
                    "GTELP_Level2_min": 70,
                },
                "group_2": {
                    "OPIc_min": "IM1",
                    "TOEIC_Speaking_min": "IM1",
                    "GTELP_Speaking_min_level": 7,
                },
            },
        },
        "restrictions_in_notice": [
            "복수 국적자",
            "외국 소재 대학(교) 학생",
            "WEST 프로그램 기 참가자",
            "WEST 기 지원자 중 참가비 납부 마감 이후 포기자",
        ],
        "evidence": P2,
        "rule_interpretation_status": "not_approved",
    },
    "application": {
        "opening_date": "2026-02-11",
        "deadline_local": "2026-03-18T17:00:00",
        "online_portal": "www.worldjob.or.kr",
        "university_submission_required_in_notice": True,
        "evidence": P4,
    },
    "documents": {
        "common_list_in_notice": [
            "WEST 온라인 지원서 및 자기소개서 출력물",
            "해당 학적 증명서",
            "전 학년 성적증명서",
            "공인영어성적증명서",
        ],
        "conditional_items": [
            {
                "item": "취업취약계층 증빙자료",
                "condition": "해당자",
            },
            {
                "item": "지원구간 증빙자료",
                "condition": "졸업생",
            },
        ],
        "other_submission_details_require_review": True,
        "evidence": P4,
    },
    "short_term_financial_support": {
        "base_participation_fee_usd": 7045,
        "round_trip_airfare_support_krw": 2000000,
        "notice_exchange_rate_krw_per_usd": 1472,
        "brackets": [
            {
                "label": "기초·차상위~5구간",
                "fee_government_usd": 7045,
                "fee_self_usd": 0,
                "living_support_usd": 8400,
                "maximum_total_support_1000krw": 24735,
            },
            {
                "label": "6~7구간",
                "fee_government_usd": 3523,
                "fee_self_usd": 3522,
                "living_support_usd": 4200,
                "maximum_total_support_1000krw": 13368,
            },
            {
                "label": "8~9구간",
                "fee_government_usd": 2466,
                "fee_self_usd": 4579,
                "living_support_usd": 4200,
                "maximum_total_support_1000krw": 11812,
            },
            {
                "label": "소득 10분위",
                "fee_government_usd": 1761,
                "fee_self_usd": 5284,
                "living_support_usd": 2100,
                "maximum_total_support_1000krw": 7684,
            },
        ],
        "amounts_are_historical_notice_values": True,
        "evidence": P6,
    },
    "mid_term_financial_support": {
        "participation_fee_usd": 8912,
        "bracket_table_status": "not_reviewed",
        "brackets": None,
    },
    "reviewed_printed_pages": [2, 4, 6],
    "remaining_pages_require_review": True,
    "table_review_status": "reviewed_for_listed_fields_only",
    "validation_status": "partially_reviewed",
    "automatic_eligibility_rules_enabled": False,
    "recommendation_rules_enabled": False,
    "embedding_generated": False,
}

# 기존 추출 텍스트에서 핵심 값이 존재하는지 교차 확인
page_text = {
    (page["page"], side): page[f"{side}_text"]
    for page in candidate["pages"]
    for side in ("left", "right")
}

checks = {
    (1, "right"): [
        "단기 WEST", "중기 WEST",
        "TOEIC 800", "TOEIC 750",
        "G-TELP Level2 76", "G-TELP Level2 70",
    ],
    (2, "right"): [
        "온라인 지원", "서류 제출",
        "자기소개서", "공인영어성적",
    ],
    (3, "right"): [
        "7,045", "8,912",
        "3,523", "3,522",
        "2,466", "4,579",
        "1,761", "5,284",
        "24,735", "13,368",
        "11,812", "7,684",
    ],
}

for key, tokens in checks.items():
    source = compact(page_text[key])
    for token in tokens:
        assert compact(token) in source, (
            f"원본에서 핵심 문자열 미발견: {key} / {token}"
        )

print("[PASS] 검수한 표의 핵심 문자열 원문 대조")

assert data["automatic_eligibility_rules_enabled"] is False
assert data["remaining_pages_require_review"] is True

for bracket in data["short_term_financial_support"]["brackets"]:
    assert (
        bracket["fee_government_usd"]
        + bracket["fee_self_usd"]
        == 7045
    )

print("[PASS] 단기 WEST 참가비 분담 합계 대조")

payload = (
    json.dumps(data, ensure_ascii=False, indent=2)
    + "\n"
).encode("utf-8")

replay = (
    json.dumps(data, ensure_ascii=False, indent=2)
    + "\n"
).encode("utf-8")

assert payload == replay
assert not OUTPUT.exists(), "기존 결과 파일이 존재합니다."

with OUTPUT.open("xb") as file:
    file.write(payload)

assert OUTPUT.read_bytes() == payload
assert json.loads(OUTPUT.read_text(encoding="utf-8")) == data

for path, raw in inputs.items():
    assert path.read_bytes() == raw

print("[PASS] 검수 데이터 JSON 저장 및 재읽기")
print("[PASS] 기존 입력 파일 불변")

print("\n===== STEP 64-14 최종 결과 =====")
print("프로그램:", data["program_id"])
print("검수한 인쇄 페이지:", data["reviewed_printed_pages"])
print("단기·중기 프로그램 구분: PASS")
print("영어성적 표 연결: PASS")
print("단기 지원금 표 연결: PASS")
print("중기 지원금 표: 미검수")
print("전체 조건 승인: 미완료")
print("출력 파일:", OUTPUT.relative_to(ROOT))
print("SHA-256:", sha256(payload))
print("자동 자격 판정: 비활성화")
print("Git 커밋·푸시: 미실행")
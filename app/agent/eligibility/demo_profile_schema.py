"""
app/agent/eligibility/demo_profile_schema.py

시연용 사용자 프로필 스키마 및 비교 규칙 정리
A 에이전트 ③번 작업: 자격 검토에 필요한 프로필 필드 명세

── 지원 범위 ────────────────────────────────────────────────────────────────
현재 knowledge release(20261028)에서 rule_based / conditional 자동 평가가
가능한 프로그램은 다음과 같습니다:

  CA:iec_working_holiday   (캐나다 IEC 워킹홀리데이)   ← 시연 1순위
  AU:subclass_186_direct_entry  (호주 ENS 186 DE)    ← 나이 조건만 자동
  JP:working_holiday_*         (일본 워홀)            ← matrix 기반
  DE:*                         (독일 일부)

나머지 대부분의 요건은 manual_check → overall: UNKNOWN.
시연에서는 CA IEC Working Holiday를 중심으로 사용합니다.

── evaluator operator별 필요 프로필 필드 ────────────────────────────────────

OPERATOR           | 필드명                          | 타입    | 설명
-------------------|---------------------------------|---------|------
age_range          | date_of_birth                   | str     | ISO 날짜 "YYYY-MM-DD"
                   | application_date                | str     | ISO 날짜 (기준일)
contains           | nationalities                   | list[str]| ISO 2자리 국가코드 리스트
equals             | korean_passport_valid_for_stay  | bool    | 한국 여권으로 체류 가능 여부
lt / gte           | iec_actual_work_permit_participations | int | IEC 실제 참여 횟수(0~)
gte / lte          | initial_settlement_funds_cad    | float   | 정착 자금(CAD)
equals (any)       | return_ticket_available         | bool    | 귀국 항공권 보유
                   | separate_return_ticket_funds_available | bool | 귀국 항공권 구매 자금 별도 보유
gte / lte          | bank_statement_age_days_at_departure | int | 은행 잔액증명서 발급 후 일수(출발일 기준)
equals             | bank_statement_in_own_name      | bool    | 본인 명의 잔액증명서
equals             | insurance_covers_entire_planned_stay | bool | 보험이 체류 전 기간 커버
                   | insurance_medical_care          | bool    | 의료 보험
                   | insurance_hospitalisation       | bool    | 입원 보험
                   | insurance_repatriation          | bool    | 본국 송환 보험

── AU subclass 186 Direct Entry 추가 필드 ────────────────────────────────────
age_range          | date_of_birth                   | str     | ISO 날짜
                   | application_date                | str     | ISO 날짜 (신청일, 기준 45세 미만)
"""

from __future__ import annotations

from typing import Any


# ── 시연용 프로필 템플릿 ───────────────────────────────────────────────────────

def demo_profile_ca_iec_wh_pass() -> dict[str, Any]:
    """
    CA IEC Working Holiday — 자격 충족 예시 프로필.
    자동 평가 가능한 POL_01~04가 모두 PASS를 반환해야 합니다.
    POL_05는 manual_check이므로 overall은 UNKNOWN.
    """
    return {
        # POL_01: 국적(한국) + 한국 여권 유효
        "nationalities": ["KR"],
        "korean_passport_valid_for_stay": True,

        # POL_02: IEC 참여 횟수 1회 미만 (신규 신청자)
        "iec_actual_work_permit_participations": 0,

        # POL_03: 정착 자금 CAD 2,500 이상 + 귀국 항공권 보유 + 은행증명서 요건
        "initial_settlement_funds_cad": 3000.0,
        "return_ticket_available": True,
        "separate_return_ticket_funds_available": False,  # any → 위 return_ticket_available로 충족
        "bank_statement_age_days_at_departure": 3,       # 0~7일 이내
        "bank_statement_in_own_name": True,

        # POL_04: 보험 요건 전부 충족
        "insurance_covers_entire_planned_stay": True,
        "insurance_medical_care": True,
        "insurance_hospitalisation": True,
        "insurance_repatriation": True,

        # 공통
        "date_of_birth": "1998-05-15",
        "application_date": "2026-10-28",
    }


def demo_profile_ca_iec_wh_fail_funds() -> dict[str, Any]:
    """
    CA IEC Working Holiday — POL_03 정착 자금 부족 예시.
    initial_settlement_funds_cad < 2500 → POL_03 FAIL → overall FAIL.
    """
    base = demo_profile_ca_iec_wh_pass()
    base["initial_settlement_funds_cad"] = 1500.0   # 2500 미만 → FAIL
    return base


def demo_profile_ca_iec_wh_unknown_insurance() -> dict[str, Any]:
    """
    CA IEC Working Holiday — 보험 정보 미제공 예시.
    insurance_* 필드 없음 → POL_04 UNKNOWN → overall UNKNOWN.
    """
    base = demo_profile_ca_iec_wh_pass()
    del base["insurance_covers_entire_planned_stay"]
    del base["insurance_medical_care"]
    del base["insurance_hospitalisation"]
    del base["insurance_repatriation"]
    return base


def demo_profile_au_186_de() -> dict[str, Any]:
    """
    AU subclass 186 Direct Entry — 연령 조건 평가 예시.
    POL_06: age_range(0~44) → 신청일 기준 45세 미만이면 PASS.
    나머지 11개 요건은 manual_check → overall UNKNOWN.
    """
    return {
        "date_of_birth": "1990-03-20",
        "application_date": "2026-10-28",
        # 나머지 수동 확인 필드들은 생략 (evaluator가 UNKNOWN 처리)
    }


# ── 비교 규칙 요약 ─────────────────────────────────────────────────────────────

COMPARISON_RULES: dict[str, list[dict[str, Any]]] = {
    "CA:iec_working_holiday": [
        {
            "requirement_id": "REVIEW:POLICY:CA_IEC_WH_POL_01",
            "description": "한국 국적 + 한국 여권 유효",
            "operator": "all",
            "auto_evaluable": True,
            "required_fields": ["nationalities", "korean_passport_valid_for_stay"],
            "rule": "nationalities contains 'KR' AND korean_passport_valid_for_stay == True",
            "manual_fallback": "나이 18~35 공개 범위 및 신청 단계별 생일 경계 확인",
        },
        {
            "requirement_id": "REVIEW:POLICY:CA_IEC_WH_POL_02",
            "description": "IEC 워킹홀리데이 참여 횟수 2회 미만",
            "operator": "all",
            "auto_evaluable": True,
            "required_fields": ["iec_actual_work_permit_participations"],
            "rule": "iec_actual_work_permit_participations < 2",
            "manual_fallback": "구 협정 참여 이력 및 카테고리별 참여 제한 확인",
        },
        {
            "requirement_id": "REVIEW:POLICY:CA_IEC_WH_POL_03",
            "description": "정착 자금 + 귀국 항공권 + 은행 증명서",
            "operator": "all",
            "auto_evaluable": True,
            "required_fields": [
                "initial_settlement_funds_cad",
                "return_ticket_available",
                "separate_return_ticket_funds_available",
                "bank_statement_age_days_at_departure",
                "bank_statement_in_own_name",
            ],
            "rule": (
                "initial_settlement_funds_cad >= 2500 "
                "AND (return_ticket_available == True OR separate_return_ticket_funds_available == True) "
                "AND bank_statement_age_days_at_departure in [0, 7] "
                "AND bank_statement_in_own_name == True"
            ),
            "manual_fallback": None,
        },
        {
            "requirement_id": "REVIEW:POLICY:CA_IEC_WH_POL_04",
            "description": "여행 보험 요건 전부 충족",
            "operator": "all",
            "auto_evaluable": True,
            "required_fields": [
                "insurance_covers_entire_planned_stay",
                "insurance_medical_care",
                "insurance_hospitalisation",
                "insurance_repatriation",
            ],
            "rule": "모든 insurance_* 필드 == True",
            "manual_fallback": "입국 적격성 심사(manual_check 병행)",
        },
        {
            "requirement_id": "REVIEW:POLICY:CA_IEC_WH_POL_05",
            "description": "기타 전체 요건 (구조화 미완료)",
            "operator": "manual_check",
            "auto_evaluable": False,
            "required_fields": [],
            "rule": None,
            "manual_fallback": "IEC WH POL_05 원문 조건·예외 대조 필요",
        },
    ],
    "AU:subclass_186_direct_entry": [
        {
            "requirement_id": "REVIEW:POLICY:AU_186_DE_POL_06",
            "description": "신청일 기준 연령 44세 이하 (면제 조항 있음)",
            "operator": "any",
            "auto_evaluable": True,
            "required_fields": ["date_of_birth", "application_date"],
            "rule": "age_at(application_date) <= 44",
            "manual_fallback": "법정 연령 면제·협약 양허·기간별 경과규정 심사",
        },
        {
            "requirement_id": "REVIEW:POLICY:AU_186_DE_POL_01~05,07~12",
            "description": "그 외 11개 요건 (스폰서, 직종, 영어, 건강 등)",
            "operator": "manual_check",
            "auto_evaluable": False,
            "required_fields": [],
            "rule": None,
            "manual_fallback": "전체 요건·예외를 사람이 확인하기 전 자동 충족 판정 금지",
        },
    ],
}


# ── 프로필 유효성 검사 헬퍼 ───────────────────────────────────────────────────

def missing_required_fields(
    program_key: str,
    profile: dict[str, Any],
) -> list[str]:
    """
    시연용: COMPARISON_RULES 기준으로 프로필에서 누락된 자동 평가 필드 목록 반환.
    missing_info 보완 요청 UI에 활용합니다.
    """
    if program_key not in COMPARISON_RULES:
        return []
    missing = []
    for rule in COMPARISON_RULES[program_key]:
        if not rule["auto_evaluable"]:
            continue
        for field in rule["required_fields"]:
            if field not in profile:
                missing.append(field)
    return list(dict.fromkeys(missing))  # 중복 제거, 순서 유지

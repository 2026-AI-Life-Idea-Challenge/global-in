"""
app/models/user_profile.py

공통 사용자 프로필 스키마.
A·B·C·D 에이전트 모두 이 클래스를 기준으로 사용합니다.

── 사용 방법 ─────────────────────────────────────────────────────────────────
  from app.models.user_profile import UserProfile

  profile = UserProfile(
      date_of_birth="1998-05-15",
      nationalities=["KR"],
      ...
  )
  profile_dict = profile.model_dump(exclude_none=True)  # A 에이전트에 전달 시
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """
    에이전트 간 공유 사용자 프로필.
    모든 필드는 Optional — 대화 중 점진적으로 채워집니다.
    """

    # ── 기본 신원 ────────────────────────────────────────────────────────────
    date_of_birth: str | None = Field(
        default=None,
        description="생년월일 (ISO 8601: YYYY-MM-DD). 나이 조건 자동 평가에 사용.",
    )
    nationalities: list[str] | None = Field(
        default=None,
        description="국적 목록 (ISO 3166-1 alpha-2 코드). 예: ['KR', 'US']",
    )

    # ── 신청 컨텍스트 ─────────────────────────────────────────────────────────
    application_date: str | None = Field(
        default=None,
        description=(
            "자격 검토 기준일 (ISO 8601: YYYY-MM-DD). "
            "미입력 시 A 에이전트가 오늘 날짜로 대체."
        ),
    )
    target_country: str | None = Field(
        default=None,
        description="목표 국가. B 에이전트 프로그램 검색에 사용. 예: 'canada'",
    )
    target_visa_type: str | None = Field(
        default=None,
        description="희망 비자 종류. 예: 'working_holiday', 'student', 'employment'",
    )
    purpose: str | None = Field(
        default=None,
        description="방문 목적 자유 텍스트. B 에이전트 검색 시 보조 컨텍스트.",
    )

    # ── CA IEC 워킹홀리데이 전용 ──────────────────────────────────────────────
    korean_passport_valid_for_stay: bool | None = Field(
        default=None,
        description="한국 여권으로 체류 가능 여부. CA IEC POL_01.",
    )
    iec_actual_work_permit_participations: int | None = Field(
        default=None,
        description="IEC 실제 참여 횟수 (0~). CA IEC POL_02: 2회 미만이어야 함.",
    )
    initial_settlement_funds_cad: float | None = Field(
        default=None,
        description="정착 자금 (CAD). CA IEC POL_03: 2,500 CAD 이상.",
    )
    return_ticket_available: bool | None = Field(
        default=None,
        description="귀국 항공권 보유 여부. CA IEC POL_03.",
    )
    separate_return_ticket_funds_available: bool | None = Field(
        default=None,
        description="귀국 항공권 구매 자금 별도 보유. CA IEC POL_03 (위와 OR 조건).",
    )
    bank_statement_age_days_at_departure: int | None = Field(
        default=None,
        description="출발일 기준 잔액증명서 발급 후 경과 일수. CA IEC POL_03: 0~7일.",
    )
    bank_statement_in_own_name: bool | None = Field(
        default=None,
        description="본인 명의 잔액증명서 여부. CA IEC POL_03.",
    )
    insurance_covers_entire_planned_stay: bool | None = Field(
        default=None,
        description="보험이 체류 전 기간 커버하는지 여부. CA IEC POL_04.",
    )
    insurance_medical_care: bool | None = Field(
        default=None,
        description="의료 보험 포함 여부. CA IEC POL_04.",
    )
    insurance_hospitalisation: bool | None = Field(
        default=None,
        description="입원 보험 포함 여부. CA IEC POL_04.",
    )
    insurance_repatriation: bool | None = Field(
        default=None,
        description="본국 송환 보험 포함 여부. CA IEC POL_04.",
    )

    # ── 확장 필드 (향후 프로그램 추가 시) ────────────────────────────────────
    extra: dict[str, Any] | None = Field(
        default=None,
        description=(
            "위 필드에 없는 프로그램별 추가 정보. "
            "새 프로그램 연동 시 여기 임시 저장 후 정식 필드로 승격."
        ),
    )

    def to_evaluator_dict(self) -> dict[str, Any]:
        """A 에이전트 evaluator에 전달할 dict. None 필드 제외."""
        data = self.model_dump(exclude_none=True)
        data.pop("target_country", None)
        data.pop("target_visa_type", None)
        data.pop("purpose", None)
        data.pop("extra", None)
        return data

    def to_search_context(self) -> dict[str, Any]:
        """B 에이전트 검색에 전달할 컨텍스트."""
        return {
            k: v for k, v in {
                "target_country": self.target_country,
                "target_visa_type": self.target_visa_type,
                "purpose": self.purpose,
                "nationalities": self.nationalities,
            }.items() if v is not None
        }

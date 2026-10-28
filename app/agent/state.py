"""상담 그래프의 공유 State."""

from typing import Literal, TypedDict

from app.models.consult import (
    EligibilityPayload,
    FollowUpQuestion,
    Intent,
    PrepItem,
    ProgramCandidate,
)
from app.models.user_profile import UserProfile


class ConsultState(TypedDict, total=False):
    # 이번 턴 입력
    user_message: str | None
    profile_updates: dict
    # 누적 상태 (checkpointer에 세션별로 저장)
    profile: UserProfile
    # 이번 턴 결과
    intent: Intent
    changed_fields: list[str]
    stage: Literal["asking", "result"]
    reply: str
    follow_up_questions: list[FollowUpQuestion]
    programs: list[ProgramCandidate]
    eligibility: list[EligibilityPayload]
    prep_items: list[PrepItem]

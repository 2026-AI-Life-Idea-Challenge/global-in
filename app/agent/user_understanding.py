"""사용자 이해 에이전트: 발화 → 프로필 변경분 추출, 프로필 병합, 부족한 정보 → 추가 질문."""

import os
from collections.abc import Callable

from pydantic import ValidationError

from app.models.consult import FollowUpQuestion, ProfileDelta, ProfileUpdateRequest
from app.models.user_profile import UserProfile

# (발화, 현재 프로필) → 변경분. 테스트에서는 LLM 없이 가짜 추출기를 넣는다.
Extractor = Callable[[str, UserProfile], ProfileDelta]

_SYSTEM_PROMPT = """너는 해외 진출(워킹홀리데이·유학·취업) 상담의 사용자 이해 담당이다.
사용자 발화에서 새로 언급되거나 바뀐 정보만 뽑아라. 언급되지 않은 필드는 반드시 null로 둔다.
- date_of_birth: 생년월일을 YYYY-MM-DD로. 나이만 말했으면 추측하지 말고 null
- nationalities: 국적 ISO 2자리 코드 목록 (예: 한국 → ["KR"])
- target_country: japan, australia, usa, germany, canada 중 하나
- target_visa_type: working_holiday(워홀), student(유학), employment(취업) 중 하나
- purpose: 방문 목적에 대한 자유 텍스트 (있을 때만)
- intent: recommend(프로그램 추천), check(자격 확인), prepare(준비 방법), update_info(정보 정정), other
현재 프로필: {profile}"""

# 추천·검토 전에 반드시 알아야 하는 기본 정보. 프로그램별 세부 조건은 A가 판단한다.
REQUIRED_FIELDS = ["target_country", "target_visa_type", "date_of_birth"]

FIELD_QUESTIONS: dict[str, FollowUpQuestion] = {
    "target_country": FollowUpQuestion(
        field="target_country", question="어느 나라로 가고 싶으세요?", input_type="select",
        options=["japan", "australia", "usa", "germany", "canada"],
    ),
    "target_visa_type": FollowUpQuestion(
        field="target_visa_type", question="워킹홀리데이, 유학, 취업 중 어떤 목적인가요?", input_type="select",
        options=["working_holiday", "student", "employment"],
    ),
    "date_of_birth": FollowUpQuestion(
        field="date_of_birth", question="생년월일을 알려주세요. (예: 1998-05-15)", input_type="date",
    ),
}

MAX_QUESTIONS_PER_TURN = 3


def llm_extractor() -> Extractor:
    """OpenAI structured output으로 ProfileDelta를 뽑는다. OPENAI_API_KEY 필요."""
    from openai import OpenAI

    client = OpenAI()
    model = os.environ.get("CONSULT_MODEL", "gpt-4o-mini")

    def extract(message: str, profile: UserProfile) -> ProfileDelta:
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": _SYSTEM_PROMPT.format(profile=profile.model_dump_json())},
                {"role": "user", "content": message},
            ],
            text_format=ProfileDelta,
        )
        return response.output_parsed or ProfileDelta()

    return extract


def merge_profile(profile: UserProfile, updates: dict) -> tuple[UserProfile, list[str]]:
    """None은 덮어쓰지 않고, ProfileUpdateRequest 검증에 실패하는 값(예: 생년월일 1800-01-01)은 버린다.
    (새 프로필, 바뀐 필드) 반환."""
    merged = profile.model_dump()
    changed = []
    for key, value in updates.items():
        if value is None:
            continue
        try:
            checked = ProfileUpdateRequest.model_validate({key: value}).model_dump(mode="json")[key]
        except ValidationError:
            continue
        if merged.get(key) == checked:
            continue
        merged[key] = checked
        changed.append(key)
    return UserProfile.model_validate(merged), changed


def missing_fields(profile: UserProfile) -> list[str]:
    return [f for f in REQUIRED_FIELDS if getattr(profile, f) is None]


def follow_up_questions(missing: list[str]) -> list[FollowUpQuestion]:
    return [FIELD_QUESTIONS[f] for f in missing[:MAX_QUESTIONS_PER_TURN]]

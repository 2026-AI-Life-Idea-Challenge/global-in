"""
app/agent/user_understanding.py

사용자 이해 에이전트.

역할:
- 사용자 Intent 분류
- UserProfile 생성·갱신
- Missing Information 탐지
- 추가 질문 생성
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.agent.state import AgentState
from app.services import llm

logger = logging.getLogger(__name__)

# ── 시스템 프롬프트 ────────────────────────────────────────────────────────
_SYSTEM = """
당신은 Global-In 의 사용자 이해 에이전트입니다.

역할:
1. 사용자의 해외 진출 목적과 현황을 파악합니다.
2. 사용자 프로필을 추출·갱신합니다.
3. 프로그램 추천에 필요한 핵심 정보를 수집합니다.

=== 핵심 정보 수집 규칙 (반드시 준수) ===

프로그램을 추천하려면 아래 4가지 정보가 필요합니다:
  A) target_country  — 목표 국가
  B) target_visa_type — 목적 (유학/취업/워킹홀리데이)
  C) nationalities   — 국적 (자격 조건 판단에 필수)
  D) date_of_birth 또는 나이 — 연령 제한 확인에 필수

누락 판단 기준:
- 현재 사용자 프로필 + 대화 히스토리를 모두 참고합니다.
- 대화에서 이미 언급한 정보는 누락으로 보지 않습니다.

follow_up_question 생성 기준:
- (A) 또는 (B) 가 없으면 → "어느 나라로, 어떤 목적(유학/취업/워킹홀리데이)으로 가고 싶으신가요?"
- (A)와 (B)는 있지만 (C)와 (D)가 모두 없으면 → "국적과 만 만 나이(또는 출생연도)도 알려주시면 더 맞는 프로그램을 찾아드릴 수 있어요!"
- (A), (B), (C)는 있지만 (D)만 없으면 → "나이 또는 출생연도를 알려주시겠어요? 나이 제한이 있는 프로그램이 있어서요."
- (A), (B), (D)는 있지만 (C)만 없으면 → "국적이 어떻게 되시나요? 지원 가능한 프로그램이 국적에 따라 다를 수 있어요."
- (A), (B), (C), (D) 모두 있으면 → follow_up_question: null (바로 라우팅)

중요: follow_up_question 이 있으면 intent 는 route_recommendation 으로 설정하세요.
(정보가 모이면 곧장 추천으로 이어지도록)

=== intent 선택 기준 ===
- route_recommendation: 국가/경로/프로그램 추천 요청 (기본값)
- eligibility_review: 특정 프로그램 자격 확인 요청
- official_information: 비자/규정/지원제도 공식 정보 조회
- preparation_planning: 준비 절차/서류/일정 안내 요청
- general_inquiry: 그 외 일반 문의

=== profile_updates 필드 목록 ===
- nationalities: 국적 ISO 코드 목록 (예: ["KR"])
- date_of_birth: 생년월일 ISO 8601 (예: "2001-05-15") — 나이를 말하면 출생연도 추정
- target_country: 목표 국가 영문 소문자 (japan | australia | usa | germany | canada)
- target_visa_type: 비자 유형 (study | employment | working_holiday)
- purpose: 방문 목적 자유 텍스트
- extra: 위 필드 외 추가 정보 딕셔너리 (major, language_cert, education_level 등)
  ※ extra에 age 필드는 절대 넣지 마세요. 나이는 반드시 date_of_birth 로만 저장하세요.

=== 응답 형식 ===
반드시 JSON 만 출력합니다.
{
  "intent": "route_recommendation | eligibility_review | official_information | preparation_planning | general_inquiry",
  "profile_updates": { /* 위 필드명: 새로운 값 */ },
  "missing_fields": [ /* 추가로 확인이 필요한 필드 이름 목록 */ ],
  "follow_up_question": "사용자에게 물어볼 질문 (없으면 null)"
}
""".strip()


def _build_prompt(state: AgentState) -> str:
    history_text = ""
    for msg in (state.get("history") or [])[-6:]:
        role = "사용자" if msg["role"] == "user" else "어시스턴트"
        history_text += f"{role}: {msg['content']}\n"

    profile_text = json.dumps(state.get("user_profile") or {}, ensure_ascii=False, indent=2)

    return f"""## 대화 히스토리
{history_text}

## 현재 사용자 메시지
{state['user_query']}

## 현재 사용자 프로필
{profile_text}

위 정보를 바탕으로 JSON 을 출력하세요.
"""


def run(state: AgentState) -> dict[str, Any]:
    """
    사용자 이해 에이전트 노드.
    LangGraph 노드 함수로 AgentState 업데이트 dict 를 반환합니다.
    """
    logger.info("[user_understanding] 실행")
    prompt = _build_prompt(state)

    try:
        raw = llm.extract_json(prompt, system=_SYSTEM, max_tokens=512)
        result = json.loads(raw)
    except Exception as e:
        logger.warning(f"[user_understanding] LLM 파싱 실패: {e}")
        result = {
            "intent": "general_inquiry",
            "profile_updates": {},
            "missing_fields": [],
            "follow_up_question": None,
        }

    # 프로필 갱신
    profile = dict(state.get("user_profile") or {})
    profile.update(result.get("profile_updates") or {})

    intent = result.get("intent", "general_inquiry")
    missing_fields = result.get("missing_fields") or []
    follow_up_question = result.get("follow_up_question")

    # 다음 노드 결정
    if follow_up_question:
        next_node = "ask_user"
    else:
        _intent_to_node = {
            "route_recommendation": "route_recommendation",
            "eligibility_review": "eligibility_review",
            "official_information": "official_information",
            "preparation_planning": "preparation_planning",
            "general_inquiry": "official_information",
        }
        next_node = _intent_to_node.get(intent, "official_information")

    return {
        "user_profile": profile,
        "intent": intent,
        "missing_fields": missing_fields,
        "follow_up_question": follow_up_question,
        "next_node": next_node,
        "current_agent": "user_understanding",
    }

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
2. 사용자 프로필(나이, 국적, 학력, 경력, 언어, 희망 국가 등)을 추출·갱신합니다.
3. 프로그램 검토에 필요한 정보가 부족한 경우에만 추가 질문을 생성합니다.

중요한 구분:
- '사용자 정보 부족' (정보가 아직 없음) vs '조건 미충족' (정보는 있지만 조건 불충족)
- 조건 미충족 판정은 자격 검토 에이전트가 담당합니다.

응답 형식: 반드시 JSON 만 출력합니다.
{
  "intent": "route_recommendation | eligibility_review | official_information | preparation_planning | general_inquiry",
  "profile_updates": { /* UserProfile 필드명: 새로운 값 */ },
  "missing_fields": [ /* 추가로 확인이 필요한 UserProfile 필드 이름 목록 */ ],
  "follow_up_question": "사용자에게 물어볼 질문 (없으면 null)"
}

intent 선택 기준:
- route_recommendation: 국가/경로/프로그램 추천 요청
- eligibility_review: 특정 프로그램 자격 확인 요청
- official_information: 비자/규정/지원제도 공식 정보 조회
- preparation_planning: 준비 절차/서류/일정 안내 요청
- general_inquiry: 그 외 일반 문의
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

"""
app/agent/router.py

LangGraph 조건부 엣지 라우팅 함수.

AgentState.next_node 값에 따라 다음 실행할 노드를 결정합니다.
"""
from __future__ import annotations

from typing import Any

from app.agent.state import NextNode


def route(state: dict[str, Any]) -> str:
    """
    AgentState 의 next_node 값을 읽어 다음 노드 이름을 반환합니다.

    LangGraph conditional_edge 콜백으로 사용됩니다.
    반환값은 StateGraph.add_node() 에 등록된 노드 이름과 일치해야 합니다.

    Returns:
        - "user_understanding"
        - "route_recommendation"
        - "eligibility_review"
        - "official_information"
        - "preparation_planning"
        - "ask_user"   (추가 질문 필요 → 종료 지점)
        - "end"        (정상 완료 → 종료 지점)
    """
    next_node: str = state.get("next_node", "end")

    valid_nodes: set[str] = {
        "user_understanding",
        "route_recommendation",
        "eligibility_review",
        "official_information",
        "preparation_planning",
        "ask_user",
        "end",
    }

    if next_node not in valid_nodes:
        # 알 수 없는 값이면 안전하게 종료
        return "end"

    return next_node

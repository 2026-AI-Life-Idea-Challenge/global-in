"""
app/agent/graph.py

LangGraph 워크플로우 그래프 정의.

5-에이전트 오케스트레이션:
  user_understanding
      ↓ (route)
  route_recommendation ← (intent: route_recommendation)
  eligibility_review   ← (intent: eligibility_review)
  official_information ← (intent: official_information)
  preparation_planning ← (intent: preparation_planning / 항상 거침)
      ↓
  end

조건부 라우팅:
  - 각 에이전트가 state.next_node 를 설정합니다.
  - router.route() 가 next_node 값을 읽어 다음 노드를 결정합니다.
  - "ask_user" 또는 "end" 는 종료 지점입니다.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.router import route
from app.agent import (
    user_understanding,
    route_recommendation,
    eligibility_review,
    official_information,
    preparation_planning,
)

logger = logging.getLogger(__name__)

# 종료 지점으로 매핑할 next_node 값 집합
_END_NODES = {"ask_user", "end"}


def _make_graph() -> StateGraph:
    """LangGraph StateGraph 를 구성하고 반환합니다."""
    graph = StateGraph(AgentState)

    # ── 노드 등록 ────────────────────────────────────────────────────────
    graph.add_node("user_understanding",    user_understanding.run)
    graph.add_node("route_recommendation",  route_recommendation.run)
    graph.add_node("eligibility_review",    eligibility_review.run)
    graph.add_node("official_information",  official_information.run)
    graph.add_node("preparation_planning",  preparation_planning.run)

    # ── 진입점 ───────────────────────────────────────────────────────────
    graph.set_entry_point("user_understanding")

    # ── 조건부 엣지 (user_understanding → 다음 에이전트) ────────────────
    graph.add_conditional_edges(
        "user_understanding",
        route,
        {
            "route_recommendation": "route_recommendation",
            "eligibility_review":   "eligibility_review",
            "official_information": "official_information",
            "preparation_planning": "preparation_planning",
            "ask_user": END,
            "end":      END,
        },
    )

    # ── route_recommendation → eligibility_review (항상) ─────────────────
    graph.add_conditional_edges(
        "route_recommendation",
        route,
        {
            "eligibility_review":   "eligibility_review",
            "official_information": "official_information",
            "ask_user": END,
            "end":      END,
        },
    )

    # ── eligibility_review → official_information or ask_user ───────────
    graph.add_conditional_edges(
        "eligibility_review",
        route,
        {
            "official_information": "official_information",
            "ask_user": END,
            "end":      END,
        },
    )

    # ── official_information → preparation_planning (항상) ───────────────
    graph.add_conditional_edges(
        "official_information",
        route,
        {
            "preparation_planning": "preparation_planning",
            "ask_user": END,
            "end":      END,
        },
    )

    # ── preparation_planning → END ────────────────────────────────────────
    graph.add_conditional_edges(
        "preparation_planning",
        route,
        {
            "ask_user": END,
            "end":      END,
        },
    )

    return graph


@lru_cache(maxsize=1)
def get_compiled_graph():
    """
    컴파일된 LangGraph 앱을 반환합니다.
    lru_cache 로 싱글턴 보장 (한 번만 컴파일).
    """
    logger.info("[graph] LangGraph 그래프 컴파일 시작")
    app = _make_graph().compile()
    logger.info("[graph] LangGraph 그래프 컴파일 완료")
    return app


async def run_graph(state: dict) -> dict:
    """
    LangGraph 그래프를 비동기로 실행합니다.

    Args:
        state: initial_state() 로 생성된 AgentState dict

    Returns:
        최종 AgentState dict
    """
    app = get_compiled_graph()
    result = await app.ainvoke(state)
    return result


def run_graph_sync(state: dict) -> dict:
    """
    LangGraph 그래프를 동기로 실행합니다.

    Args:
        state: initial_state() 로 생성된 AgentState dict

    Returns:
        최종 AgentState dict
    """
    app = get_compiled_graph()
    result = app.invoke(state)
    return result

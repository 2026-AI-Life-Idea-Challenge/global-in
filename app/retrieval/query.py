"""
app/retrieval/query.py

사용자 질문 + AgentState 정보를 조합하여 Retrieval 검색 Query 를 구성합니다.
"""
from __future__ import annotations

from typing import Any

from app.retrieval.filters import build_filters


def build_search_query(
    user_query: str,
    state: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    AgentState 에서 필요한 정보를 추출해
    (검색 텍스트, Metadata 필터) 쌍을 반환합니다.

    Args:
        user_query: 사용자의 현재 질문
        state: AgentState dict (또는 그 일부)

    Returns:
        (query_text, filters)
    """
    profile = state.get("user_profile", {})
    selected = state.get("selected_program") or {}

    destination_country = (
        selected.get("destination_country")
        or selected.get("country")
        or profile.get("target_country")
    )
    program_id = selected.get("program_id")
    support_program_ids: list[str] = [
        sp.get("support_program_id", "")
        for sp in state.get("candidate_support_programs", [])
        if sp.get("support_program_id")
    ]

    # 검색 텍스트: 질문 + 국가 + 프로그램 맥락 보강
    parts = [user_query]
    if destination_country:
        parts.append(destination_country)
    if program_id:
        parts.append(program_id)
    query_text = " ".join(parts)

    filters = build_filters(
        destination_country=destination_country or None,
        program_id=program_id or None,
        # support_program_id 는 여러 개일 수 있어 filters 에 직접 적용 어려움 — retriever 에서 처리
    )

    return query_text, filters


def build_official_info_query(
    user_query: str,
    state: dict[str, Any],
    information_topic: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    공식 정보 안내 에이전트 전용 Query 빌더.
    information_topic 을 추가로 지정할 수 있습니다.
    """
    query_text, filters = build_search_query(user_query, state)
    if information_topic:
        filters["information_topic"] = information_topic
    return query_text, filters


def build_support_program_query(
    user_query: str,
    state: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    국내외 지원제도 공식 근거 검색 전용 Query 빌더.
    """
    profile = state.get("user_profile", {})
    destination_country = profile.get("target_country")
    query_text = user_query
    if destination_country:
        query_text = f"{destination_country} {user_query}"

    filters = build_filters(
        destination_country=destination_country or None,
        target_nationality="Korean",
        information_topic="support",
    )
    return query_text, filters

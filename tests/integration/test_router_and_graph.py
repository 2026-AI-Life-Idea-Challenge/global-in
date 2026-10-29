"""
tests/integration/test_router_and_graph.py

Router 및 LangGraph 통합 테스트 (14개)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.router import route_after_understanding, route_after_eligibility
from app.agent.state import initial_state


# ── Router 테스트 ──────────────────────────────────────────────────────────

class TestRouteAfterUnderstanding:
    def _state(self, intent: str) -> dict:
        s = initial_state("ses", "query", [], {})
        s["intent"] = intent
        return s

    def test_visa_routes_to_recommendation(self):
        assert route_after_understanding(self._state("visa_inquiry")) == "route_recommendation"

    def test_employment_routes_to_recommendation(self):
        assert route_after_understanding(self._state("employment_inquiry")) == "route_recommendation"

    def test_study_routes_to_recommendation(self):
        assert route_after_understanding(self._state("study_inquiry")) == "route_recommendation"

    def test_working_holiday_routes_to_recommendation(self):
        assert route_after_understanding(self._state("working_holiday_inquiry")) == "route_recommendation"

    def test_general_routes_to_official_or_end(self):
        dest = route_after_understanding(self._state("general"))
        assert dest in ("official_information", "END", "__end__", "end")

    def test_unknown_intent_handled(self):
        dest = route_after_understanding(self._state("unknown_xyz"))
        assert isinstance(dest, str)


class TestRouteAfterEligibility:
    def _state(self, results: list) -> dict:
        s = initial_state("ses", "query", [], {})
        s["eligibility_results"] = results
        return s

    def test_eligible_routes_to_official(self):
        dest = route_after_eligibility(self._state([{"eligible": True}]))
        assert dest in ("official_information",)

    def test_ineligible_routes_to_planning_or_end(self):
        dest = route_after_eligibility(self._state([{"eligible": False}]))
        assert isinstance(dest, str)

    def test_empty_results_handled(self):
        dest = route_after_eligibility(self._state([]))
        assert isinstance(dest, str)


# ── run_graph 통합 테스트 ─────────────────────────────────────────────────

class TestRunGraph:
    @pytest.mark.asyncio
    async def test_graph_returns_final_answer(self):
        from app.agent.graph import run_graph
        state = initial_state("ses", "호주 비자 알려줘", [], {})

        with patch("app.agent.graph.get_compiled_graph") as mock_graph_fn:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={**state, "final_answer": "테스트 답변"})
            mock_graph_fn.return_value = mock_graph
            result = await run_graph(state)

        assert result["final_answer"] == "테스트 답변"

    @pytest.mark.asyncio
    async def test_graph_session_id_preserved(self):
        from app.agent.graph import run_graph
        state = initial_state("my-session-123", "query", [], {})

        with patch("app.agent.graph.get_compiled_graph") as mock_graph_fn:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(return_value={**state, "final_answer": "ok"})
            mock_graph_fn.return_value = mock_graph
            result = await run_graph(state)

        assert result["session_id"] == "my-session-123"

    @pytest.mark.asyncio
    async def test_graph_error_propagates(self):
        from app.agent.graph import run_graph
        state = initial_state("ses", "query", [], {})

        with patch("app.agent.graph.get_compiled_graph") as mock_graph_fn:
            mock_graph = MagicMock()
            mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("graph error"))
            mock_graph_fn.return_value = mock_graph

            with pytest.raises(RuntimeError):
                await run_graph(state)

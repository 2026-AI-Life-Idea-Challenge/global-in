"""
tests/integration/test_route_recommendation.py

RouteRecommendationAgent 통합 테스트 (8개)
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.agent.route_recommendation import RouteRecommendationAgent
from app.agent.state import initial_state


def _make_state(intent: str = "visa_inquiry", profile: dict | None = None) -> dict:
    s = initial_state("ses", "test query", [], {})
    s["intent"] = intent
    s["user_profile"] = profile or {"nationality": "korean", "age": 25}
    return s


def _patch_llm(answer: dict):
    return patch(
        "app.agent.route_recommendation.extract_json",
        return_value=json.dumps(answer),
    )


class TestRouteRecommendationAgent:
    def test_returns_candidate_programs(self):
        answer = {"recommended_programs": ["aus_skilled_visa", "aus_working_holiday"]}
        with _patch_llm(answer):
            agent = RouteRecommendationAgent()
            result = agent.run(_make_state())
        assert "recommended_programs" in result

    def test_returns_support_programs(self):
        answer = {"recommended_programs": [], "recommended_support_programs": ["kotra_aus"]}
        with _patch_llm(answer):
            result = RouteRecommendationAgent().run(_make_state())
        assert "recommended_support_programs" in result

    def test_employment_route(self):
        answer = {"recommended_programs": ["jp_engineer_visa"]}
        with _patch_llm(answer):
            result = RouteRecommendationAgent().run(_make_state("employment_inquiry"))
        assert result["recommended_programs"]

    def test_study_route(self):
        answer = {"recommended_programs": ["ca_study_permit"]}
        with _patch_llm(answer):
            result = RouteRecommendationAgent().run(_make_state("study_inquiry"))
        assert result["recommended_programs"]

    def test_working_holiday_route(self):
        answer = {"recommended_programs": ["aus_working_holiday"]}
        with _patch_llm(answer):
            result = RouteRecommendationAgent().run(_make_state("working_holiday_inquiry"))
        assert result

    def test_state_keys_forwarded(self):
        answer = {"recommended_programs": []}
        with _patch_llm(answer):
            result = RouteRecommendationAgent().run(_make_state())
        assert "session_id" in result
        assert "intent" in result

    def test_invalid_json_no_crash(self):
        with patch("app.agent.route_recommendation.extract_json", return_value="BAD"):
            result = RouteRecommendationAgent().run(_make_state())
        assert result is not None

    def test_empty_profile_handled(self):
        answer = {"recommended_programs": []}
        with _patch_llm(answer):
            result = RouteRecommendationAgent().run(_make_state(profile={}))
        assert result is not None

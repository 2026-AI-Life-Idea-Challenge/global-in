"""
tests/integration/test_eligibility_review.py

EligibilityReviewAgent 통합 테스트 (9개)
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.agent.eligibility_review import EligibilityReviewAgent
from app.agent.state import initial_state


def _make_state(programs: list | None = None) -> dict:
    s = initial_state("ses", "test", [], {})
    s["intent"] = "visa_inquiry"
    s["user_profile"] = {"nationality": "korean", "age": 25}
    s["recommended_programs"] = programs or ["aus_skilled_visa"]
    return s


def _patch_llm(answer: dict):
    return patch(
        "app.agent.eligibility_review.extract_json",
        return_value=json.dumps(answer),
    )


class TestEligibilityReviewAgent:
    def test_eligible_result(self):
        answer = {"eligibility_results": [{"program": "aus_skilled_visa", "eligible": True, "reason": "조건 충족"}]}
        with _patch_llm(answer):
            result = EligibilityReviewAgent().run(_make_state())
        assert result["eligibility_results"][0]["eligible"] is True

    def test_ineligible_result(self):
        answer = {"eligibility_results": [{"program": "aus_skilled_visa", "eligible": False, "reason": "나이 초과"}]}
        with _patch_llm(answer):
            result = EligibilityReviewAgent().run(_make_state())
        assert result["eligibility_results"][0]["eligible"] is False

    def test_multiple_programs(self):
        progs = ["aus_skilled_visa", "aus_working_holiday"]
        answer = {"eligibility_results": [
            {"program": "aus_skilled_visa", "eligible": True},
            {"program": "aus_working_holiday", "eligible": False},
        ]}
        with _patch_llm(answer):
            result = EligibilityReviewAgent().run(_make_state(progs))
        assert len(result["eligibility_results"]) == 2

    def test_empty_programs(self):
        answer = {"eligibility_results": []}
        with _patch_llm(answer):
            result = EligibilityReviewAgent().run(_make_state([]))
        assert result["eligibility_results"] == []

    def test_invalid_json_no_crash(self):
        with patch("app.agent.eligibility_review.extract_json", return_value="BAD"):
            result = EligibilityReviewAgent().run(_make_state())
        assert result is not None

    def test_state_preserved(self):
        answer = {"eligibility_results": []}
        with _patch_llm(answer):
            result = EligibilityReviewAgent().run(_make_state())
        assert "session_id" in result
        assert "user_profile" in result

    def test_reason_field_present(self):
        answer = {"eligibility_results": [{"program": "aus_skilled_visa", "eligible": True, "reason": "ok"}]}
        with _patch_llm(answer):
            result = EligibilityReviewAgent().run(_make_state())
        assert "reason" in result["eligibility_results"][0]

    def test_follow_up_question_set(self):
        answer = {
            "eligibility_results": [],
            "follow_up_question": "현재 학력이 어떻게 되세요?",
        }
        with _patch_llm(answer):
            result = EligibilityReviewAgent().run(_make_state())
        assert result.get("follow_up_question")

    def test_returns_dict(self):
        answer = {"eligibility_results": []}
        with _patch_llm(answer):
            result = EligibilityReviewAgent().run(_make_state())
        assert isinstance(result, dict)

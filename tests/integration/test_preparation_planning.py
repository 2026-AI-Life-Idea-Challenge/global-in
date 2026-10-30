"""
tests/integration/test_preparation_planning.py

PreparationPlanningAgent 통합 테스트 (13개)
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.agent.preparation_planning import PreparationPlanningAgent
from app.agent.state import initial_state


def _make_state(intent: str = "visa_inquiry") -> dict:
    s = initial_state("ses", "비자 준비 알려줘", [], {})
    s["intent"] = intent
    s["user_profile"] = {"nationality": "korean", "age": 25}
    s["recommended_programs"] = ["aus_skilled_visa"]
    s["eligibility_results"] = [{"program": "aus_skilled_visa", "eligible": True}]
    s["final_answer"] = "공식 정보 안내 완료"
    return s


def _patch_llm(answer: dict):
    return patch(
        "app.agent.preparation_planning.extract_json",
        return_value=json.dumps(answer),
    )


SAMPLE_CHECKLIST = [
    {"item": "여권 준비", "done": False},
    {"item": "영어 성적 취득", "done": False},
]
SAMPLE_ROADMAP = [
    {"step": 1, "title": "정보 수집", "duration": "1주"},
    {"step": 2, "title": "서류 준비", "duration": "4주"},
]


class TestPreparationPlanningAgent:
    def test_checklist_returned(self):
        with _patch_llm({"checklist": SAMPLE_CHECKLIST, "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state())
        assert result["checklist"] == SAMPLE_CHECKLIST

    def test_roadmap_returned(self):
        with _patch_llm({"checklist": [], "roadmap": SAMPLE_ROADMAP}):
            result = PreparationPlanningAgent().run(_make_state())
        assert result["roadmap"] == SAMPLE_ROADMAP

    def test_both_returned(self):
        with _patch_llm({"checklist": SAMPLE_CHECKLIST, "roadmap": SAMPLE_ROADMAP}):
            result = PreparationPlanningAgent().run(_make_state())
        assert result["checklist"] and result["roadmap"]

    def test_empty_checklist_allowed(self):
        with _patch_llm({"checklist": [], "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state())
        assert result["checklist"] == []

    def test_invalid_json_no_crash(self):
        with patch("app.agent.preparation_planning.extract_json", return_value="BAD"):
            result = PreparationPlanningAgent().run(_make_state())
        assert result is not None

    def test_state_preserved(self):
        with _patch_llm({"checklist": [], "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state())
        assert "session_id" in result
        assert "final_answer" in result

    def test_study_intent(self):
        with _patch_llm({"checklist": [{"item": "입학허가서"}], "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state("study_inquiry"))
        assert result["checklist"]

    def test_employment_intent(self):
        with _patch_llm({"checklist": [{"item": "경력증명서"}], "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state("employment_inquiry"))
        assert result["checklist"]

    def test_working_holiday_intent(self):
        with _patch_llm({"checklist": [{"item": "왕복 항공권"}], "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state("working_holiday_inquiry"))
        assert result["checklist"]

    def test_checklist_item_structure(self):
        with _patch_llm({"checklist": SAMPLE_CHECKLIST, "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state())
        assert "item" in result["checklist"][0]

    def test_roadmap_step_structure(self):
        with _patch_llm({"checklist": [], "roadmap": SAMPLE_ROADMAP}):
            result = PreparationPlanningAgent().run(_make_state())
        assert "step" in result["roadmap"][0]

    def test_returns_dict(self):
        with _patch_llm({"checklist": [], "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state())
        assert isinstance(result, dict)

    def test_multiple_checklist_items(self):
        items = [{"item": f"항목{i}"} for i in range(10)]
        with _patch_llm({"checklist": items, "roadmap": []}):
            result = PreparationPlanningAgent().run(_make_state())
        assert len(result["checklist"]) == 10

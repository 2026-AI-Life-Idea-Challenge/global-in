"""
tests/integration/test_user_understanding.py

UserUnderstandingAgent 단위·통합 테스트 (10개)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agent.user_understanding import UserUnderstandingAgent
from app.agent.state import initial_state


# ── 헬퍼 ──────────────────────────────────────────────────────────────────
def _make_state(query: str) -> dict:
    return initial_state(
        session_id="test-session",
        user_query=query,
        history=[],
        user_profile={},
    )


def _patch_extract_json(return_value: dict):
    """llm.extract_json 를 모킹합니다."""
    return patch(
        "app.agent.user_understanding.extract_json",
        return_value=json.dumps(return_value),
    )


# ── 테스트 ─────────────────────────────────────────────────────────────────

class TestUserUnderstandingAgent:
    def test_visa_intent_classification(self):
        with _patch_extract_json({"intent": "visa_inquiry", "profile": {}}):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state("호주 비자 신청 방법 알려줘"))
        assert result["intent"] == "visa_inquiry"

    def test_employment_intent_classification(self):
        with _patch_extract_json({"intent": "employment_inquiry", "profile": {}}):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state("일본에서 취업하고 싶어"))
        assert result["intent"] == "employment_inquiry"

    def test_study_intent_classification(self):
        with _patch_extract_json({"intent": "study_inquiry", "profile": {}}):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state("캐나다 유학 정보 주세요"))
        assert result["intent"] == "study_inquiry"

    def test_working_holiday_intent(self):
        with _patch_extract_json({"intent": "working_holiday_inquiry", "profile": {}}):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state("워킹홀리데이 신청하고 싶어"))
        assert result["intent"] == "working_holiday_inquiry"

    def test_general_intent_fallback(self):
        with _patch_extract_json({"intent": "general", "profile": {}}):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state("안녕하세요"))
        assert result["intent"] == "general"

    def test_profile_extraction_nationality(self):
        profile = {"nationality": "korean", "age": 25}
        with _patch_extract_json({"intent": "visa_inquiry", "profile": profile}):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state("한국인 25살, 호주 비자 알려줘"))
        assert result["user_profile"]["nationality"] == "korean"

    def test_profile_extraction_age(self):
        profile = {"age": 28}
        with _patch_extract_json({"intent": "working_holiday_inquiry", "profile": profile}):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state("28살 워킹홀리데이 되나요?"))
        assert result["user_profile"]["age"] == 28

    def test_invalid_json_falls_back_gracefully(self):
        with patch(
            "app.agent.user_understanding.extract_json",
            return_value="NOT_JSON",
        ):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state("이상한 입력"))
        # 오류 없이 완료되어야 함
        assert "intent" in result

    def test_state_keys_preserved(self):
        with _patch_extract_json({"intent": "visa_inquiry", "profile": {}}):
            agent = UserUnderstandingAgent()
            state = _make_state("비자 문의")
            result = agent.run(state)
        assert "session_id" in result
        assert "user_query" in result

    def test_empty_query_handled(self):
        with _patch_extract_json({"intent": "general", "profile": {}}):
            agent = UserUnderstandingAgent()
            result = agent.run(_make_state(""))
        assert result is not None

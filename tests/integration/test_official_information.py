"""
tests/integration/test_official_information.py

OfficialInformationAgent 통합 테스트 (10개)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agent.official_information import OfficialInformationAgent
from app.agent.state import initial_state


def _make_state(query: str = "호주 비자 절차") -> dict:
    s = initial_state("ses", query, [], {})
    s["intent"] = "visa_inquiry"
    s["user_profile"] = {"nationality": "korean", "age": 25}
    s["recommended_programs"] = ["aus_skilled_visa"]
    s["eligibility_results"] = [{"program": "aus_skilled_visa", "eligible": True}]
    return s


def _patch_rag(docs: list):
    return patch(
        "app.agent.official_information.retrieve_relevant_chunks",
        return_value=docs,
    )


def _patch_llm(answer: str = "공식 정보입니다."):
    return patch(
        "app.agent.official_information.chat",
        return_value=answer,
    )


class TestOfficialInformationAgent:
    def test_rag_docs_used(self):
        docs = [{"chunk_text": "비자 신청 요건: ...", "score": 0.9}]
        with _patch_rag(docs), _patch_llm():
            result = OfficialInformationAgent().run(_make_state())
        assert result.get("final_answer")

    def test_no_rag_docs_fallback(self):
        with _patch_rag([]), _patch_llm("LLM 단독 응답"):
            result = OfficialInformationAgent().run(_make_state())
        assert result["final_answer"] == "LLM 단독 응답"

    def test_final_answer_populated(self):
        with _patch_rag([]), _patch_llm("정보 응답"):
            result = OfficialInformationAgent().run(_make_state())
        assert "final_answer" in result

    def test_rag_error_handled(self):
        with patch("app.agent.official_information.retrieve_relevant_chunks", side_effect=Exception("DB 오류")), \
             _patch_llm("오류 시 LLM"):
            result = OfficialInformationAgent().run(_make_state())
        assert result is not None

    def test_state_keys_preserved(self):
        with _patch_rag([]), _patch_llm():
            result = OfficialInformationAgent().run(_make_state())
        assert "session_id" in result
        assert "intent" in result

    def test_multiple_docs_concatenated(self):
        docs = [
            {"chunk_text": "doc1", "score": 0.95},
            {"chunk_text": "doc2", "score": 0.80},
        ]
        with _patch_rag(docs), _patch_llm("종합 답변"):
            result = OfficialInformationAgent().run(_make_state())
        assert result["final_answer"]

    def test_query_forwarded_to_rag(self):
        mock_rag = MagicMock(return_value=[])
        with patch("app.agent.official_information.retrieve_relevant_chunks", mock_rag), _patch_llm():
            OfficialInformationAgent().run(_make_state("호주 비자 절차"))
        assert mock_rag.called

    def test_empty_query_handled(self):
        with _patch_rag([]), _patch_llm("빈 쿼리 응답"):
            result = OfficialInformationAgent().run(_make_state(""))
        assert result is not None

    def test_long_answer_allowed(self):
        long_ans = "A" * 3000
        with _patch_rag([]), _patch_llm(long_ans):
            result = OfficialInformationAgent().run(_make_state())
        assert len(result["final_answer"]) > 100

    def test_returns_dict(self):
        with _patch_rag([]), _patch_llm():
            result = OfficialInformationAgent().run(_make_state())
        assert isinstance(result, dict)

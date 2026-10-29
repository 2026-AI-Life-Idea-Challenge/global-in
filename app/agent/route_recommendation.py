"""
app/agent/route_recommendation.py

진출 경로 탐색·추천 에이전트.

역할:
- 사용자 조건에 맞는 국가·비자·프로그램 후보 탐색 (Program Resolver)
- 활용 가능한 국내외 지원제도 탐색
- 후보별 비교·추천 이유 생성
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.agent.state import AgentState
from app.services import llm, db

logger = logging.getLogger(__name__)

_SYSTEM = """
당신은 Global-In 의 진출 경로 탐색·추천 에이전트입니다.

역할:
1. 사용자 프로필과 의도에 맞는 국가와 비자/프로그램 후보를 선정합니다.
2. 함께 활용할 수 있는 국내외 지원제도를 탐색합니다.
3. 후보별 비교 결과와 추천 이유를 제공합니다.

중요:
- 자격 판정은 자격 검토 에이전트가 담당합니다. 여기서는 '후보' 를 선정만 합니다.
- Program 과 SupportProgram 을 구분하세요.
- 한국인에게 실제로 적용 가능한지 불분명한 지원제도는 '추가 확인 필요' 로 처리하세요.

응답 형식: 반드시 JSON 만 출력합니다.
{
  "candidate_countries": ["japan", "germany", ...],
  "candidate_programs": [
    {
      "program_id": "...",
      "country": "...",
      "name": "...",
      "category": "...",
      "recommendation_reason": "..."
    }
  ],
  "candidate_support_programs": [
    {
      "support_program_id": "...",
      "country": "...",
      "name": "...",
      "applicability_status": "확인됨 | 추가 확인 필요 | 해당 없음",
      "note": "..."
    }
  ],
  "summary": "추천 요약 (2-3문장)"
}
""".strip()


def _fetch_programs(
    country: str | None,
    category: str | None,
) -> list[dict[str, Any]]:
    """PostgreSQL 에서 Programs 를 조회합니다."""
    try:
        sql = """
            SELECT program_id, country, name, category, metadata
            FROM programs
            WHERE TRUE
        """
        params: list[Any] = []
        if country:
            sql += " AND country = %s"
            params.append(country)
        if category:
            sql += " AND category = %s"
            params.append(category)
        sql += " ORDER BY country, program_id LIMIT 20"
        return db.query(sql, params)
    except Exception as e:
        logger.warning(f"[route_recommendation] Programs 조회 실패: {e}")
        return []


def _fetch_support_programs(country: str | None) -> list[dict[str, Any]]:
    """PostgreSQL 에서 SupportPrograms 를 조회합니다."""
    try:
        sql = """
            SELECT support_program_id, country, name, provider, metadata
            FROM support_programs
            WHERE TRUE
        """
        params: list[Any] = []
        if country:
            sql += " AND country = %s"
            params.append(country)
        sql += " ORDER BY country, support_program_id LIMIT 20"
        return db.query(sql, params)
    except Exception as e:
        logger.warning(f"[route_recommendation] SupportPrograms 조회 실패: {e}")
        return []


def _build_prompt(state: AgentState, programs: list, support_programs: list) -> str:
    profile = json.dumps(state.get("user_profile") or {}, ensure_ascii=False, indent=2)
    prog_text = json.dumps(programs, ensure_ascii=False, indent=2)
    sp_text = json.dumps(support_programs, ensure_ascii=False, indent=2)
    return f"""## 사용자 질문
{state['user_query']}

## 사용자 프로필
{profile}

## 현재 의도
{state.get('intent', '')}

## DB 에서 조회된 Programs (후보 선정 참고)
{prog_text}

## DB 에서 조회된 SupportPrograms (후보 선정 참고)
{sp_text}

위 정보를 바탕으로 최적의 진출 경로 후보를 JSON 으로 출력하세요.
"""


def run(state: AgentState) -> dict[str, Any]:
    """진출 경로 탐색·추천 에이전트 노드."""
    logger.info("[route_recommendation] 실행")

    profile = state.get("user_profile") or {}
    target_country = profile.get("target_country")
    target_visa_type = profile.get("target_visa_type")

    programs = _fetch_programs(target_country, target_visa_type)
    support_programs = _fetch_support_programs(target_country)

    prompt = _build_prompt(state, programs, support_programs)

    try:
        raw = llm.extract_json(prompt, system=_SYSTEM, max_tokens=1024)
        result = json.loads(raw)
    except Exception as e:
        logger.warning(f"[route_recommendation] LLM 파싱 실패: {e}")
        result = {
            "candidate_countries": [],
            "candidate_programs": programs[:5],
            "candidate_support_programs": support_programs[:5],
            "summary": "진출 경로를 탐색했습니다.",
        }

    return {
        "candidate_countries": result.get("candidate_countries") or [],
        "candidate_programs": result.get("candidate_programs") or [],
        "candidate_support_programs": result.get("candidate_support_programs") or [],
        "next_node": "eligibility_review",
        "current_agent": "route_recommendation",
    }

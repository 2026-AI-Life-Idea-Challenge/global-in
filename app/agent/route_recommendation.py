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
- DB 에서 조회된 프로그램 중 사용자에게 적합한 것을 선택하세요.

응답 형식: 반드시 JSON 만 출력합니다.
{
  "candidate_countries": ["japan", "germany", ...],
  "candidate_programs": [
    {
      "program_id": "...",
      "country": "...",
      "name": "...",
      "category": "...",
      "recommendation_reason": "이 프로그램을 추천하는 구체적인 이유 (2-3문장)"
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


def _parse_metadata(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def _enrich_programs(
    llm_candidates: list[dict],
    db_programs: list[dict],
) -> list[dict]:
    """LLM이 선택한 후보에 DB 원본 데이터(description, url 등)를 병합합니다."""
    lookup = {p["program_id"]: p for p in db_programs}
    enriched = []
    for cp in llm_candidates:
        pid = cp.get("program_id", "")
        db_row = lookup.get(pid, {})
        meta = _parse_metadata(db_row.get("metadata"))
        enriched.append({
            "program_id":           pid,
            "country":              db_row.get("country") or cp.get("country", ""),
            "name":                 db_row.get("name") or cp.get("name", ""),
            "category":             db_row.get("category") or cp.get("category", ""),
            "recommendation_reason": cp.get("recommendation_reason", ""),
            "description":          meta.get("description") or meta.get("summary") or "",
            "url":                  meta.get("url") or meta.get("official_url") or meta.get("link") or "",
        })
    return enriched


def _enrich_support_programs(
    llm_candidates: list[dict],
    db_support: list[dict],
) -> list[dict]:
    """지원제도 후보에 DB 원본 데이터를 병합합니다."""
    lookup = {sp["support_program_id"]: sp for sp in db_support}
    enriched = []
    for sp in llm_candidates:
        spid = sp.get("support_program_id", "")
        db_row = lookup.get(spid, {})
        meta = _parse_metadata(db_row.get("metadata"))
        enriched.append({
            "support_program_id":   spid,
            "country":              db_row.get("country") or sp.get("country", ""),
            "name":                 db_row.get("name") or sp.get("name", ""),
            "applicability_status": sp.get("applicability_status", "추가 확인 필요"),
            "note":                 sp.get("note", ""),
            "description":          meta.get("description") or meta.get("summary") or "",
            "url":                  meta.get("url") or meta.get("official_url") or meta.get("link") or "",
        })
    return enriched


def _build_prompt(state: AgentState, programs: list, support_programs: list) -> str:
    profile = json.dumps(state.get("user_profile") or {}, ensure_ascii=False, indent=2)
    # metadata 는 LLM 에 보내지 않아도 됨 (토큰 절약)
    prog_summary = [
        {"program_id": p["program_id"], "country": p["country"],
         "name": p["name"], "category": p["category"]}
        for p in programs
    ]
    sp_summary = [
        {"support_program_id": sp["support_program_id"], "country": sp["country"],
         "name": sp["name"]}
        for sp in support_programs
    ]
    return f"""## 사용자 질문
{state['user_query']}

## 사용자 프로필
{profile}

## 현재 의도
{state.get('intent', '')}

## DB 에서 조회된 Programs (후보 선정 참고)
{json.dumps(prog_summary, ensure_ascii=False, indent=2)}

## DB 에서 조회된 SupportPrograms (후보 선정 참고)
{json.dumps(sp_summary, ensure_ascii=False, indent=2)}

위 정보를 바탕으로 최적의 진출 경로 후보를 JSON 으로 출력하세요.
프로그램이 없으면 candidate_programs 를 빈 배열로 두세요.
"""


def run(state: AgentState) -> dict[str, Any]:
    """진출 경로 탐색·추천 에이전트 노드."""
    logger.info("[route_recommendation] 실행")

    profile = state.get("user_profile") or {}
    target_country = profile.get("target_country")
    target_visa_type = profile.get("target_visa_type")

    programs = _fetch_programs(target_country, target_visa_type)
    support_programs = _fetch_support_programs(target_country)

    logger.info(f"[route_recommendation] DB 조회: programs={len(programs)}, support={len(support_programs)}")

    prompt = _build_prompt(state, programs, support_programs)

    try:
        raw = llm.extract_json(prompt, system=_SYSTEM, max_tokens=1024)
        result = json.loads(raw)
    except Exception as e:
        logger.warning(f"[route_recommendation] LLM 파싱 실패: {e}")
        # fallback: DB 데이터를 직접 사용
        fallback_programs = []
        for p in programs[:5]:
            meta = _parse_metadata(p.get("metadata"))
            fallback_programs.append({
                "program_id": p["program_id"],
                "country": p["country"],
                "name": p["name"],
                "category": p["category"],
                "recommendation_reason": "",
                "description": meta.get("description") or "",
                "url": meta.get("url") or meta.get("official_url") or "",
            })
        fallback_support = []
        for sp in support_programs[:3]:
            meta = _parse_metadata(sp.get("metadata"))
            fallback_support.append({
                "support_program_id": sp["support_program_id"],
                "country": sp["country"],
                "name": sp["name"],
                "applicability_status": "추가 확인 필요",
                "note": "",
                "description": meta.get("description") or "",
                "url": meta.get("url") or meta.get("official_url") or "",
            })
        return {
            "candidate_countries": [target_country] if target_country else [],
            "candidate_programs": fallback_programs,
            "candidate_support_programs": fallback_support,
            "next_node": "eligibility_review",
            "current_agent": "route_recommendation",
        }

    # LLM 선택 결과에 DB 원본 데이터 병합
    enriched_programs = _enrich_programs(
        result.get("candidate_programs") or [],
        programs,
    )
    enriched_support = _enrich_support_programs(
        result.get("candidate_support_programs") or [],
        support_programs,
    )

    logger.info(f"[route_recommendation] 후보: programs={len(enriched_programs)}, support={len(enriched_support)}")

    return {
        "candidate_countries": result.get("candidate_countries") or [],
        "candidate_programs": enriched_programs,
        "candidate_support_programs": enriched_support,
        "next_node": "eligibility_review",
        "current_agent": "route_recommendation",
    }

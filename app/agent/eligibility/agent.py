"""
app/agent/eligibility/agent.py

자격조건 검토 에이전트 (A 담당)
LangGraph 노드로 사용되는 함수들을 정의합니다.

State 흐름:
  profile + program_ids
      ↓
  [fetch_program_context_node]  programs, knowledge_documents, evidence 등 조회
      ↓
  [fetch_requirements_node]  DB에서 rule_set + requirements 조회
      ↓
  [check_eligibility_node]   evaluator로 각 요건 평가
      ↓
  EligibilityState (overall, per-program 결과, missing_info, program_contexts)
"""

from __future__ import annotations

import os
from typing import Any, TypedDict

from app.agent.eligibility.fetcher import (
    fetch_rule_set,
    fetch_requirements,
    RuleSet,
    RequirementRecord,
)
from app.agent.eligibility.checker import (
    check_eligibility,
    recheck_with_updated_profile,
    EligibilityResult,
)
from app.rules.reviews import VerifiedReviewDecision
from app.agent.eligibility.policy_fetcher import (
    fetch_program_context,
    ProgramContext,
)

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://global_in_app:outsiders4@localhost:5432/global_in",
)


# ── LangGraph State ────────────────────────────────────────────────────────────

class EligibilityState(TypedDict, total=False):
    # 입력
    profile: dict[str, Any]                      # 사용자 프로필
    program_ids: list[str]                        # 검토할 프로그램 ID 목록
    target_type: str                              # PROGRAM | SUPPORT_PROGRAM (기본 PROGRAM)
    as_of: str | None                             # 기준일 YYYY-MM-DD
    verified_reviews: list[VerifiedReviewDecision] # 인증된 심사 결과

    # 내부 캐시 (노드 간 전달)
    _fetched: dict[str, tuple[RuleSet | None, list[RequirementRecord]]]

    # 출력
    results: dict[str, EligibilityResult]         # program_id → 검토 결과
    missing_info: list[dict[str, Any]]            # UNKNOWN 요건의 pending_reviews 합산
    overall_summary: dict[str, str]               # program_id → overall 판정
    program_contexts: dict[str, ProgramContext]    # program_id → 프로그램 컨텍스트


# ── 노드 함수 ──────────────────────────────────────────────────────────────────

def fetch_program_context_node(state: EligibilityState) -> EligibilityState:
    """DB에서 각 프로그램의 기본 정보, 지식문서, 정책(approved), 근거, 준비사항을 조회합니다."""
    program_ids = state.get("program_ids", [])
    target_type = state.get("target_type", "PROGRAM")

    contexts: dict[str, ProgramContext] = {}
    for pid in program_ids:
        contexts[pid] = fetch_program_context(DB_URL, pid, target_type)

    return {**state, "program_contexts": contexts}


def fetch_requirements_node(state: EligibilityState) -> EligibilityState:
    """DB에서 각 프로그램의 rule_set과 requirements를 조회합니다."""
    program_ids = state.get("program_ids", [])
    target_type = state.get("target_type", "PROGRAM")

    fetched: dict[str, tuple[RuleSet | None, list[RequirementRecord]]] = {}

    for pid in program_ids:
        rule_set = fetch_rule_set(DB_URL, target_type, pid)
        requirements = fetch_requirements(DB_URL, target_type, pid)
        fetched[pid] = (rule_set, requirements)

    return {**state, "_fetched": fetched}


def check_eligibility_node(state: EligibilityState) -> EligibilityState:
    """각 프로그램에 대해 자격 검토를 수행합니다."""
    fetched = state.get("_fetched", {})
    profile = state.get("profile", {})
    as_of = state.get("as_of")
    verified_reviews = state.get("verified_reviews", [])

    results: dict[str, EligibilityResult] = {}

    for pid, (rule_set, requirements) in fetched.items():
        result = check_eligibility(
            rule_set=rule_set,
            requirements=requirements,
            profile=profile,
            as_of=as_of,
            verified_reviews=verified_reviews,
        )
        results[pid] = result

    missing_info = []
    for result in results.values():
        missing_info.extend(result.missing_info_reviews)

    overall_summary = {pid: r.overall for pid, r in results.items()}

    return {
        **state,
        "results": results,
        "missing_info": missing_info,
        "overall_summary": overall_summary,
    }


def recheck_node(state: EligibilityState) -> EligibilityState:
    """사용자 정보 변경 후 재검토합니다. (profile이 업데이트된 상태로 호출)"""
    # fetch는 이미 된 상태(_fetched 재사용), profile만 교체
    fetched = state.get("_fetched", {})
    profile = state.get("profile", {})
    as_of = state.get("as_of")
    verified_reviews = state.get("verified_reviews", [])

    results: dict[str, EligibilityResult] = {}

    for pid, (rule_set, requirements) in fetched.items():
        result = recheck_with_updated_profile(
            rule_set=rule_set,
            requirements=requirements,
            updated_profile=profile,
            as_of=as_of,
            verified_reviews=verified_reviews,
        )
        results[pid] = result

    missing_info = []
    for result in results.values():
        missing_info.extend(result.missing_info_reviews)

    overall_summary = {pid: r.overall for pid, r in results.items()}

    return {
        **state,
        "results": results,
        "missing_info": missing_info,
        "overall_summary": overall_summary,
    }


# ── LangGraph 그래프 빌드 ─────────────────────────────────────────────────────

def build_eligibility_graph():
    """
    자격조건 검토 에이전트 그래프를 빌드합니다.

    사용 예:
        graph = build_eligibility_graph()
        result = graph.invoke({
            "profile": {...},
            "program_ids": ["AU:subclass_186_direct_entry"],
            "target_type": "PROGRAM",
        })
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        raise ImportError("langgraph가 설치되어 있지 않습니다. pip install langgraph")

    builder = StateGraph(EligibilityState)

    builder.add_node("fetch_context", fetch_program_context_node)
    builder.add_node("fetch", fetch_requirements_node)
    builder.add_node("check", check_eligibility_node)

    builder.set_entry_point("fetch_context")
    builder.add_edge("fetch_context", "fetch")
    builder.add_edge("fetch", "check")
    builder.add_edge("check", END)

    return builder.compile()


# ── 직접 실행 (디버그용) ───────────────────────────────────────────────────────

def run_direct(
    profile: dict[str, Any],
    program_ids: list[str],
    target_type: str = "PROGRAM",
    as_of: str | None = None,
) -> dict[str, EligibilityResult]:
    """
    LangGraph 없이 직접 실행하는 함수 (시연·테스트용).

    사용 예:
        from app.agent.eligibility.agent import run_direct
        results = run_direct(
            profile={"age": 30, "nationality": "KR"},
            program_ids=["AU:subclass_186_direct_entry"],
        )
    """
    state: EligibilityState = {
        "profile": profile,
        "program_ids": program_ids,
        "target_type": target_type,
        "as_of": as_of,
        "verified_reviews": [],
    }
    state = fetch_program_context_node(state)
    state = fetch_requirements_node(state)
    state = check_eligibility_node(state)
    return state["results"]

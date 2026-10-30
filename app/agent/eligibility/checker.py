"""
app/agent/eligibility/checker.py

사용자 프로필과 요건 정의를 받아 자격 검토 결과를 반환합니다.
evaluator.evaluate()를 호출하고 결과를 집계합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.rules.evaluator import evaluate, PASS, FAIL, UNKNOWN
from app.rules.reviews import VerifiedReviewDecision
from app.agent.eligibility.fetcher import RequirementRecord, RuleSet


# ── 결과 타입 ──────────────────────────────────────────────────────────────────

@dataclass
class RequirementResult:
    requirement_id: str
    judgeability: str
    outcome: str          # PASS | FAIL | UNKNOWN
    pending_reviews: list[dict[str, Any]] = field(default_factory=list)
    # pending_reviews: official_assessment 노드 중 결과가 없는 것들


@dataclass
class EligibilityResult:
    target_type: str
    target_id: str
    overall: str          # PASS | FAIL | UNKNOWN
    coverage_complete: bool
    requirements: list[RequirementResult] = field(default_factory=list)

    @property
    def passed(self) -> list[RequirementResult]:
        return [r for r in self.requirements if r.outcome == PASS]

    @property
    def failed(self) -> list[RequirementResult]:
        return [r for r in self.requirements if r.outcome == FAIL]

    @property
    def unknown(self) -> list[RequirementResult]:
        return [r for r in self.requirements if r.outcome == UNKNOWN]

    @property
    def missing_info_reviews(self) -> list[dict[str, Any]]:
        """UNKNOWN 상태인 요건 중 official_assessment 대기 목록."""
        result = []
        for r in self.unknown:
            result.extend(r.pending_reviews)
        return result


# ── 메인 함수 ──────────────────────────────────────────────────────────────────

def check_eligibility(
    rule_set: RuleSet | None,
    requirements: list[RequirementRecord],
    profile: dict[str, Any],
    as_of: str | None = None,
    verified_reviews: list[VerifiedReviewDecision] | None = None,
) -> EligibilityResult:
    """
    사용자 프로필에 대해 모든 요건을 평가하고 결과를 반환합니다.

    Parameters
    ----------
    rule_set : RuleSet | None
        프로그램의 룰셋 (coverage_complete 확인용)
    requirements : list[RequirementRecord]
        평가할 요건 목록
    profile : dict
        사용자 프로필 (evaluator가 읽는 형식)
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 오늘 날짜 사용
    verified_reviews : list[VerifiedReviewDecision] | None
        인증된 백엔드 심사 결과 (없으면 official_assessment는 UNKNOWN)
    """
    target_type = rule_set.target_type if rule_set else (requirements[0].target_type if requirements else "PROGRAM")
    target_id   = rule_set.target_id   if rule_set else (requirements[0].target_id   if requirements else "")
    coverage_complete = rule_set.coverage_complete if rule_set else False
    _as_of = as_of or date.today().isoformat()

    req_results: list[RequirementResult] = []

    for req in requirements:
        expression = req.definition

        # trusted_context: [requirement_dict, as_of, records, original_profile, pending_list]
        pending: list[dict[str, Any]] = []
        trusted_context = [
            {
                "requirement_id": req.requirement_id,
                "target": {
                    "target_type": req.target_type,
                    "target_id": req.target_id,
                },
                "expression": expression,
            },
            _as_of,
            verified_reviews or [],
            profile,
            pending,
        ]

        outcome = evaluate(expression, profile, trusted_context)
        req_results.append(RequirementResult(
            requirement_id=req.requirement_id,
            judgeability=req.judgeability,
            outcome=outcome,
            pending_reviews=pending,
        ))

    overall = _aggregate(req_results)

    return EligibilityResult(
        target_type=target_type,
        target_id=target_id,
        overall=overall,
        coverage_complete=coverage_complete,
        requirements=req_results,
    )


def recheck_with_updated_profile(
    rule_set: RuleSet | None,
    requirements: list[RequirementRecord],
    updated_profile: dict[str, Any],
    as_of: str | None = None,
    verified_reviews: list[VerifiedReviewDecision] | None = None,
) -> EligibilityResult:
    """사용자 정보 변경 후 재검토 (check_eligibility의 래퍼)."""
    return check_eligibility(rule_set, requirements, updated_profile, as_of, verified_reviews)


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _aggregate(results: list[RequirementResult]) -> str:
    """
    전체 종합 판정:
    - FAIL이 하나라도 있으면 → FAIL
    - UNKNOWN이 있으면 → UNKNOWN
    - 모두 PASS → PASS
    - 요건 없음 → UNKNOWN (coverage 불완전)
    """
    if not results:
        return UNKNOWN
    outcomes = {r.outcome for r in results}
    if FAIL in outcomes:
        return FAIL
    if UNKNOWN in outcomes:
        return UNKNOWN
    return PASS

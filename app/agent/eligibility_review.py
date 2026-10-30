"""
app/agent/eligibility_review.py

자격 검토 에이전트.

역할:
- Rule Evaluator 를 호출하여 Program·SupportProgram 자격을 검토합니다.
- 자격 검토 결과를 정리하고 부족 조건·추가 확인 항목을 분류합니다.
- 판정 결과를 변경하지 않고 C·D에 전달합니다. 추가 LLM 호출은 하지 않습니다.

판정 상태: PASS='조건 충족', FAIL='조건 미충족', UNKNOWN='추가 확인 필요'
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.agent.state import AgentState, EligibilityResult
from app.rules.evaluator import PASS, FAIL, UNKNOWN, evaluate_target
from app.models.user_profile import UserProfile
from app.services import db

logger = logging.getLogger(__name__)

def _load_requirements(target_type: str, target_id: str) -> tuple[dict, list]:
    """
    Read canonical definitions from one read-only DB snapshot.

    C uses lower-case target names; the knowledge DB uses upper-case names.
    Connection/schema errors must propagate, rather than masquerade as absent
    rules and producing an empty UNKNOWN review.
    """
    canonical_type = target_type.upper()
    if canonical_type not in ('PROGRAM', 'SUPPORT_PROGRAM'):
        raise ValueError('Unsupported eligibility target type')
    with db.get_conn() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        rule_set_row = conn.execute(
            'SELECT definition, release_id FROM eligibility_rule_sets WHERE target_type = %s AND target_id = %s',
            (canonical_type, target_id),
        ).fetchone()
        if not rule_set_row:
            return {}, []

        req_rows = conn.execute(
            'SELECT definition FROM eligibility_requirements WHERE target_type = %s AND target_id = %s AND release_id = %s ORDER BY requirement_id',
            (canonical_type, target_id, rule_set_row['release_id']),
        ).fetchall()
        definition = rule_set_row['definition']
        if definition['target_type'] != canonical_type or definition['target_id'] != target_id:
            raise ValueError('Rule-set target does not match the requested target')
        return definition, [row['definition'] for row in req_rows]


def _run_rule_evaluator(
    target_type: str,
    target_id: str,
    profile_dict: dict[str, Any],
    as_of: str,
) -> EligibilityResult | None:
    """Rule Evaluator 를 실행하고 EligibilityResult 를 반환합니다."""
    rule_set, requirements = _load_requirements(target_type, target_id)
    if not rule_set:
        return None

    result = evaluate_target(rule_set, requirements, profile_dict, as_of)
    definitions = {r['requirement_id']: r for r in requirements}
    for condition in result.get('condition_results', []):
        definition = definitions.get(condition.get('requirement_id'), {})
        condition['description'] = definition.get('description', '')
        condition['judgeability'] = definition.get('judgeability', 'manual_check')

    missing: list[str] = []
    review_requests: list[dict] = []
    for cr in result.get("condition_results", []):
        if cr.get("status") == FAIL:
            missing.append(cr.get("requirement_id", ""))
        review_requests.extend(cr.get("review_requests", []))

    return EligibilityResult(
        target_type=target_type,
        target_id=target_id,
        status=result.get("overall_status", UNKNOWN),
        condition_results=result.get("condition_results", []),
        missing_conditions=missing,
        review_requests=review_requests,
    )


def run(state: AgentState) -> dict[str, Any]:
    """자격 검토 에이전트 노드."""
    logger.info("[eligibility_review] 실행")

    profile = state.get("user_profile") or {}
    as_of = profile.get("application_date") or date.today().isoformat()

    # UserProfile → evaluator dict 변환
    try:
        up = UserProfile(**{k: v for k, v in profile.items() if k in UserProfile.model_fields})
        profile_dict = up.to_evaluator_dict()
    except Exception:
        profile_dict = {k: v for k, v in profile.items() if v is not None}

    eligibility_results: list[EligibilityResult] = []

    # 후보 Programs 자격 검토
    for prog in (state.get("candidate_programs") or []):
        pid = prog.get("program_id")
        if not pid:
            continue
        result = _run_rule_evaluator("program", pid, profile_dict, as_of)
        if result:
            eligibility_results.append(result)
        else:
            # Rule 데이터가 없으면 UNKNOWN 으로 처리
            eligibility_results.append(EligibilityResult(
                target_type="program",
                target_id=pid,
                status=UNKNOWN,
                condition_results=[],
                missing_conditions=[],
                review_requests=[],
            ))

    # 후보 SupportPrograms 자격 검토
    for sp in (state.get("candidate_support_programs") or []):
        spid = sp.get("support_program_id")
        if not spid:
            continue
        result = _run_rule_evaluator("support_program", spid, profile_dict, as_of)
        if result:
            eligibility_results.append(result)
        else:
            eligibility_results.append(EligibilityResult(
                target_type="support_program",
                target_id=spid,
                status=UNKNOWN,
                condition_results=[],
                missing_conditions=[],
                review_requests=[],
            ))

    # Return the unchanged evaluator outcomes; C and D render them without
    # spending an extra model call that could invent questions or approvals.
    return {
        "eligibility_results": eligibility_results,
        "follow_up_question": None,
        "next_node": "official_information",
        "current_agent": "eligibility_review",
    }

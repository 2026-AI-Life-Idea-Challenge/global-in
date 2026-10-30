"""
app/agent/eligibility_review.py

자격 검토 에이전트.

역할:
- Rule Evaluator 를 호출하여 Program·SupportProgram 자격을 검토합니다.
- 자격 검토 결과를 정리하고 부족 조건·추가 확인 항목을 분류합니다.
- LLM 은 결과를 설명하는 역할만 담당합니다. Rule Evaluator 결과를 변경하지 않습니다.

판정 상태: PASS='조건 충족', FAIL='조건 미충족', UNKNOWN='추가 확인 필요'
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from app.agent.state import AgentState, EligibilityResult
from app.rules.evaluator import PASS, FAIL, UNKNOWN, evaluate_target
from app.models.user_profile import UserProfile
from app.services import llm, db

logger = logging.getLogger(__name__)

_SYSTEM = """
당신은 Global-In 의 자격 검토 에이전트입니다.

Rule Evaluator 가 계산한 자격 검토 결과를 사용자에게 한국어로 설명합니다.

중요 규칙:
- Rule Evaluator 의 판정(조건 충족/미충족/추가 확인 필요)을 절대 변경하지 마세요.
- '조건 충족' = 자격 요건 충족. 비자 발급 확정이 아닙니다.
- '지원제도 신청 자격' 과 '현재 신청 가능 여부' 를 구분하세요.
- 비자 자격과 지원제도 자격을 별도로 설명하세요.

응답 형식: 반드시 JSON 만 출력합니다.
{
  "summary": "전체 자격 검토 요약 (2-3문장)",
  "program_results": [
    {
      "target_id": "...",
      "status": "조건 충족 | 조건 미충족 | 추가 확인 필요",
      "explanation": "사용자 언어로 된 설명"
    }
  ],
  "support_program_results": [
    {
      "target_id": "...",
      "status": "조건 충족 | 조건 미충족 | 추가 확인 필요",
      "explanation": "..."
    }
  ],
  "additional_questions": ["확인이 필요한 사용자 정보 질문 (있는 경우)"]
}
""".strip()


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

    # LLM 으로 결과 설명 생성
    results_text = json.dumps(eligibility_results, ensure_ascii=False, indent=2)
    prompt = f"""## 사용자 질문
{state['user_query']}

## 자격 검토 결과 (Rule Evaluator 출력)
{results_text}

## 사용자 프로필
{json.dumps(profile, ensure_ascii=False, indent=2)}

위 결과를 변경하지 말고 사용자 언어로 설명하는 JSON 을 출력하세요.
"""
    try:
        raw = llm.extract_json(prompt, system=_SYSTEM, max_tokens=1024)
        llm_result = json.loads(raw)
    except Exception as e:
        logger.warning(f"[eligibility_review] LLM 설명 생성 실패: {e}")
        llm_result = {}

    # missing_fields 갱신 (추가 질문이 있는 경우)
    additional_q = llm_result.get("additional_questions") or []
    follow_up = ("\n".join(additional_q)) if additional_q else None

    return {
        "eligibility_results": eligibility_results,
        "follow_up_question": follow_up,
        "next_node": "ask_user" if follow_up else "official_information",
        "current_agent": "eligibility_review",
    }

"""
app/agent/preparation_planning.py

준비 계획 에이전트.

역할:
- 자격 검토 결과와 공식 정보를 바탕으로 구체적인 Checklist 와 Roadmap 을 생성합니다.
- Checklist: 비자·지원제도·공통 항목 분류
- Roadmap: 단계별 준비 일정 (사전준비 → 서류준비 → 신청 → 대기 → 입국/정착)
- 최종 종합 답변(final_answer)을 확정합니다.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from app.agent.state import AgentState, ChecklistItem, RoadmapStep
from app.services import llm

logger = logging.getLogger(__name__)

_SYSTEM = """
당신은 Global-In 의 준비 계획 에이전트입니다.

역할:
- 사용자 맞춤 Checklist 와 Roadmap 을 작성합니다.
- 자격 요건 검토 결과를 반영합니다.
  - '조건 미충족' 항목은 Checklist 에 명확히 표시합니다.
  - '추가 확인 필요' 항목은 확인 액션으로 Checklist 에 포함합니다.
- Roadmap 단계: 사전_준비, 서류_준비, 신청, 대기, 입국_정착
- 지원제도(비자 외)는 별도 카테고리로 분류하세요.
- 각 항목에는 구체적인 설명과 주의사항을 포함하세요.

=== final_answer 작성 규칙 (매우 중요) ===
final_answer 는 아래 구조로 작성하세요:
1. 사용자 상황 요약 (1-2문장)
2. 추천 프로그램/비자 목록 — 반드시 후보 비자/프로그램의 실제 이름을 언급하세요.
   예: "○○ 비자", "△△ 장학금", "□□ 제도" 등 구체적인 명칭 사용
3. 핵심 준비 사항 (2-3가지 구체적 항목)
4. 다음 단계 안내

generic 한 표현("비자를 알아보세요", "공식 채널을 확인하세요")은 사용하지 마세요.
실제 프로그램 이름을 포함한 구체적이고 친절한 안내를 작성하세요.

응답 형식: 반드시 JSON 만 출력합니다.
{
  "checklist": [
    {
      "category": "visa | support_program | common",
      "target_id": "관련 program_id 또는 support_program_id (없으면 null)",
      "title": "항목 제목",
      "description": "구체적인 설명 및 주의사항"
    }
  ],
  "roadmap": [
    {
      "stage": "사전_준비 | 서류_준비 | 신청 | 대기 | 입국_정착",
      "title": "단계 제목",
      "description": "단계 설명",
      "target_ids": ["관련 program_id 또는 support_program_id 목록"]
    }
  ],
  "final_answer": "사용자에게 전달할 종합 안내 메시지 (한국어, 친절하고 구체적으로, 실제 프로그램명 반드시 포함)"
}
""".strip()


def _build_context(state: AgentState) -> str:
    """LLM 프롬프트 컨텍스트를 구성합니다."""
    parts = []

    # 자격 검토 결과
    eligibility = state.get("eligibility_results") or []
    if eligibility:
        parts.append("## 자격 검토 결과")
        for er in eligibility:
            tid = er.get("target_id", "")
            status = er.get("status", "")
            missing = er.get("missing_conditions") or []
            parts.append(f"- {tid}: {status}")
            if missing:
                parts.append(f"  미충족 조건: {', '.join(missing)}")

    # 후보 프로그램
    programs = state.get("candidate_programs") or []
    if programs:
        parts.append("\n## 후보 비자/프로그램")
        for p in programs:
            pid = p.get("program_id", "")
            pname = p.get("program_name") or p.get("name", "")
            country = p.get("country") or p.get("destination_country", "")
            reason = p.get("recommendation_reason", "")
            line = f"- [{pid}] {pname} ({country})"
            if reason:
                line += f" — {reason}"
            parts.append(line)

    # 후보 지원제도
    support_programs = state.get("candidate_support_programs") or []
    if support_programs:
        parts.append("\n## 후보 지원제도")
        for sp in support_programs:
            spid = sp.get("support_program_id", "")
            spname = sp.get("program_name") or sp.get("name", "")
            parts.append(f"- [{spid}] {spname}")

    # 공식 정보 요약
    validated = state.get("validated_evidence") or []
    if validated:
        parts.append("\n## 검증된 공식 근거 요약")
        for ev in validated[:3]:
            agency = ev.get("official_agency") or "미상"
            title = ev.get("source_title") or ""
            content = ev.get("content", "")[:200]
            parts.append(f"- [{agency}] {title}\n  {content}")

    # 이전 final_answer (official_information 생성)
    prev_answer = state.get("final_answer", "")
    if prev_answer:
        parts.append(f"\n## 공식 정보 안내 (이전 단계)\n{prev_answer}")

    # 사용자 프로필
    profile = state.get("user_profile") or {}
    if profile:
        parts.append(f"\n## 사용자 프로필\n{json.dumps(profile, ensure_ascii=False)}")

    return "\n".join(parts)


def run(state: AgentState) -> dict[str, Any]:
    """준비 계획 에이전트 노드."""
    logger.info("[preparation_planning] 실행")

    context = _build_context(state)
    prompt = f"""## 사용자 질문
{state['user_query']}

{context}

위 정보를 바탕으로 사용자 맞춤 Checklist 와 Roadmap, 최종 안내 메시지를 JSON 으로 출력하세요.
final_answer 에는 반드시 위에 나온 실제 프로그램 이름을 언급하세요.
"""

    try:
        raw = llm.extract_json(prompt, system=_SYSTEM, max_tokens=2048)
        result = json.loads(raw)
    except Exception as e:
        logger.warning(f"[preparation_planning] LLM 결과 생성 실패: {e}")
        result = {
            "checklist": [],
            "roadmap": [],
            "final_answer": (
                "준비 계획 생성 중 오류가 발생했습니다. "
                "담당 대사관 또는 이민국에 직접 문의하시기 바랍니다."
            ),
        }

    # ChecklistItem 구성
    checklist: list[ChecklistItem] = []
    for item in result.get("checklist") or []:
        category = item.get("category", "common")
        if category not in ("visa", "support_program", "common"):
            category = "common"
        checklist.append(ChecklistItem(
            item_id=f"chk_{uuid.uuid4().hex[:8]}",
            category=category,
            target_id=item.get("target_id"),
            title=item.get("title", ""),
            description=item.get("description", ""),
        ))

    # RoadmapStep 구성
    valid_stages = {"사전_준비", "서류_준비", "신청", "대기", "입국_정착"}
    roadmap: list[RoadmapStep] = []
    for i, step in enumerate(result.get("roadmap") or []):
        stage = step.get("stage", "")
        if stage not in valid_stages:
            stage = "사전_준비"
        roadmap.append(RoadmapStep(
            step_id=f"step_{i+1:02d}",
            stage=stage,
            title=step.get("title", ""),
            description=step.get("description", ""),
            target_ids=step.get("target_ids") or [],
        ))

    final_answer = result.get("final_answer") or state.get("final_answer") or ""

    return {
        "checklist": checklist,
        "roadmap": roadmap,
        "final_answer": final_answer,
        "next_node": "end",
        "current_agent": "preparation_planning",
    }

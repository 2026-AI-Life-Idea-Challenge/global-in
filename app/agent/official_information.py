"""Call B's validated RAG and preserve its answers and citation provenance."""
from app.agent.state import AgentState
from app.services.consultation_b import answer, linked_evidence


def run(state: AgentState) -> dict:
    results = answer(state)
    evidence = linked_evidence(results)
    lines = [result['answer'] for result in results]
    supports = state.get('candidate_support_programs', [])
    if state.get('information_scope') in ('support', 'both') and supports:
        lines.append('연결 후보 지원제도 — 개인 자격이나 현재 접수 가능 여부를 확정한 목록은 아닙니다.')
        for support in supports:
            lines.append(f"- {support['name']} ({support['support_program_id']}): 저장된 모집 상태 {support.get('availability') or 'UNKNOWN'}, 확인일 {support.get('source_verified_at') or '미확인'}")
    if not lines:
        lines.append('현재 범위에서 안내할 프로그램 또는 공식 근거를 찾지 못했습니다. 국가·목적·제도명을 구체적으로 알려주세요.')
    return dict(rag_results=results, validated_evidence=evidence, retrieved_documents=[],
                final_answer='\n\n'.join(lines), next_node='preparation_planning', current_agent='official_information')

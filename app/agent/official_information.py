"""Call B's validated RAG and preserve its answers and citation provenance."""
import logging
from app.models.rag import RagResponseValidationError
from app.agent.state import AgentState
from app.services.consultation_b import answer, linked_evidence


def run(state: AgentState) -> dict:
    try:
        results = answer(state)
    except RagResponseValidationError:
        logging.getLogger(__name__).warning('RAG response validation failed', exc_info=True)
        return dict(rag_results=[], validated_evidence=[], retrieved_documents=[],
                    final_answer='요청하신 제도 정보는 근거를 확인하지 못해 안내할 수 없습니다. 공식 자료를 확인해 주세요.',
                    next_node='preparation_planning', current_agent='official_information')
    evidence = linked_evidence(results)
    lines = [result['answer'] for result in results]
    supports = state.get('candidate_support_programs', [])
    if state.get('information_scope') in ('support', 'both') and supports:
        lines.append('연결 후보 지원제도 — 개인 자격이나 현재 접수 가능 여부를 확정한 목록은 아닙니다.')
        for support in supports:
            label = {'OPEN': '접수 중으로 기록됨', 'CLOSED': '접수 종료로 기록됨', 'UPCOMING': '접수 예정으로 기록됨', 'UNKNOWN': '접수 여부 확인 필요'}.get(support.get('availability'), '확인 필요')
            lines.append(f"- {support['name']}: {label}, 확인일 {support.get('source_verified_at') or '미확인'}")
    if not lines:
        lines.append('현재 범위에서 안내할 프로그램 또는 공식 근거를 찾지 못했습니다. 국가·목적·제도명을 구체적으로 알려주세요.')
    return dict(rag_results=results, validated_evidence=evidence, retrieved_documents=[],
                final_answer='\n\n'.join(lines), next_node='preparation_planning', current_agent='official_information')

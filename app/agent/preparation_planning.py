"""Build source-linked confirmation actions without rewriting B's factual answer."""
import hashlib
from app.agent.state import AgentState


def run(state: AgentState) -> dict:
    checklist = []
    seen = set()
    for result in state.get('rag_results', []):
        target_id = result.get('program_id') or result.get('support_program_id')
        for claim in result.get('claims', []):
            target = claim.get('program_id') or target_id
            # Each task is explicitly a confirmation action, not an invented required document.
            sources = claim.get('citations', [])
            if not target or not sources:
                continue
            identity = target + ':' + claim['text']
            if identity in seen:
                continue
            seen.add(identity)
            checklist.append(dict(item_id='confirm_' + hashlib.sha256(identity.encode()).hexdigest()[:16],
                                  category='support_program' if result.get('support_program_id') else 'visa',
                                  target_id=target, title='공식 안내 확인', description=claim['text'],
                                  status='추가 확인', stage='preparation', required=False, citations=sources))
    for review in state.get('eligibility_results', []):
        for condition in review.get('condition_results', []):
            if condition.get('status') == '조건 충족':
                continue
            rid = condition.get('requirement_id', '')
            checklist.append(dict(item_id='review:' + review['target_id'] + ':' + rid,
                                  category='support_program' if review['target_type'] == 'support_program' else 'visa',
                                  target_id=review['target_id'], title='요건 추가 확인' if condition.get('status') == '추가 확인 필요' else '부족 조건 확인',
                                  description=' · '.join(value for value in (condition.get('reason'), condition.get('description')) if value) or rid,
                                  status='추가 확인', stage='preparation', required=False,
                                  source_document_ids=condition.get('source_document_ids', []), citations=[]))
    # No invented processing time, mandatory document, deadline or final approval.
    return dict(checklist=checklist, roadmap=[], final_answer=state.get('final_answer', ''),
                next_node='end', current_agent='preparation_planning')

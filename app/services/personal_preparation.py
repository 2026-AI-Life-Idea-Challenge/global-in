"""Read-only, rule-based personal preparation. No invented documents or deadlines."""
from app.services.consultation_catalog import load_catalog_detail
from app.agent.eligibility_review import run as review


def build_preparation(target_id, profile):
    detail = load_catalog_detail(target_id)
    if detail is None:
        return None
    kind = detail['kind']
    state = dict(user_profile=profile, candidate_programs=[], candidate_support_programs=[])
    state['candidate_programs' if kind == 'program' else 'candidate_support_programs'] = [
        {'program_id' if kind == 'program' else 'support_program_id': target_id}]
    reviews = review(state)['eligibility_results']
    sources = detail.get('sources', [])
    items = []
    for result in reviews:
        for condition in result.get('condition_results', []):
            outcome = condition.get('status')
            description = condition.get('description') or condition['requirement_id']
            prefix = {'조건 충족': '충족 조건 증빙 준비', '조건 미충족': '부족 조건 보완'}.get(outcome, '미확인 조건 확인')
            questions = [q for request in condition.get('review_requests', []) for q in request.get('questions', [])]
            items.append(dict(id='personal:' + target_id + ':' + condition['requirement_id'],
                program_id=target_id, title=prefix + ': ' + description,
                description='\n'.join(filter(None, [condition.get('reason'), *questions,
                    '필수 서류·기한은 공식 신청 안내에서 확인하세요. 이 항목은 최종 승인이나 필수 서류 확정이 아닙니다.'])),
                done=False, status='blocked' if outcome == '조건 미충족' else 'todo' if outcome == '조건 충족' else 'check_needed',
                citations=sources))
    if not items:
        # Retain actual dataset text, rather than inventing a generic personal checklist.
        for section in detail.get('sections', []):
            items.append(dict(id='dataset:' + section['id'], program_id=target_id,
                title='신청 준비 확인: ' + section['title'], description=section['body'],
                done=False, status='check_needed', citations=section.get('sources') or sources))
    return dict(target_id=target_id, items=items, profile_fields=sorted(k for k,v in profile.items() if v is not None),
        scope='profile_rule_comparison_not_final_approval')

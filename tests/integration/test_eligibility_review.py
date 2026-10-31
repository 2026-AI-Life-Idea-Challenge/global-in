"""A's graph adapter reads actual rule definitions and does not ask an LLM."""
from app.agent import eligibility_review as node


def test_evaluator_result_and_id_survive_stale_source(monkeypatch):
    target=dict(target_type='PROGRAM',target_id='P')
    req=dict(requirement_id='r',target=target,verified_at='2026-10-28',source_document_ids=['doc'],
             description='조건',judgeability='conditional',expression=dict(operator='equals',field='approved',value=True))
    rules=dict(**target,requirement_ids=['r'],coverage_complete=False,application_availability='UNKNOWN',blockers=[])
    monkeypatch.setattr(node,'_load_requirements',lambda *args:(rules,[req]))
    result=node.run(dict(user_query='질문',user_profile={'application_date':'2026-10-31'},candidate_programs=[dict(program_id='P')]))
    condition=result['eligibility_results'][0]['condition_results'][0]
    assert condition['status']=='추가 확인 필요'
    assert condition['requirement_id']=='r'
    assert condition['source_document_ids']==['doc']
    assert result['next_node']=='official_information'


def test_no_registered_rule_stays_unknown(monkeypatch):
    monkeypatch.setattr(node,'_load_requirements',lambda *args:({},[]))
    result=node.run(dict(user_query='질문',candidate_support_programs=[dict(support_program_id='S')]))
    assert result['eligibility_results'][0]['status']=='추가 확인 필요'

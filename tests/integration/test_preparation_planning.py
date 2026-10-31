"""Preparation actions retain source provenance and do not invent facts."""
from app.agent.preparation_planning import run


def test_confirmations_keep_b_answer_and_have_no_invented_deadline():
    state=dict(final_answer='원문 답변',rag_results=[dict(program_id='P',claims=[dict(text='조건 확인',citations=[dict(chunk_id='c')])])])
    result=run(state)
    assert result['final_answer']=='원문 답변'
    assert result['checklist'][0]['required'] is False
    assert result['checklist'][0]['citations']
    assert result['roadmap']==[]


def test_unsourced_claim_is_not_a_preparation_instruction():
    result=run(dict(rag_results=[dict(program_id='P',claims=[dict(text='확인되지 않은 마감일',citations=[])])]))
    assert result['checklist']==[]


def test_failed_condition_becomes_a_confirmation_action_not_approval():
    result=run(dict(eligibility_results=[dict(target_id='P',target_type='program',condition_results=[dict(requirement_id='r',status='조건 미충족',reason='요건 확인')])]))
    assert result['checklist'][0]['title']=='부족 조건 확인'
    assert result['checklist'][0]['status']=='추가 확인'

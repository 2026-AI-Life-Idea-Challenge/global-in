"""Current C graph + real B validation + A evaluator, with fake I/O only."""
from copy import deepcopy
from datetime import date
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent import user_understanding, eligibility_review, preparation_planning
from app.agent.graph import _make_graph
from app.api.consult import create_router
from app.models.rag import RagDraft, RagGeneration
from app.models.multi_program_rag import ProgramsDraft
from app.models.support_rag import SupportInfo
from app.services import consultation_b, program_rag, multi_program_rag, support_rag

PROGRAMS = [dict(program_id='CA:test', name='캐나다 테스트', country='canada', category='working_holiday'),
            dict(program_id='AU:test', name='호주 테스트', country='australia', category='working_holiday')]
SUPPORTS = [dict(support_program_id='S:test', name='테스트 지원', availability='CLOSED',
                 destination_countries=['CA'], source_verified_at='2026-10-28',
                 program_links=[dict(program_id='CA:test')])]


def row(pid='CA:test'):
    return dict(program_id=pid, document_id='doc:'+pid, revision_id='v1', chunk_id='c:'+pid, ordinal=0,
                title='테스트 공식 자료', body='A valid passport is required.', knowledge_kind='policy',
                source_urls=['https://example.org/passport'], source_references=[],
                document_active=True, chunk_active=True, document_embedding_approved=False,
                chunk_embedding_approved=False, answer_approved=False, content_review_status='checked_scope_limited',
                document_release_id='v1', chunk_release_id='v1',
                vector_rank=None, vector_similarity=None, keyword_rank=1, keyword_score=1.0, rrf_score=1/61)


@pytest.fixture
def setup(monkeypatch):
    calls = []
    def extract(prompt, **kwargs):
        data = json.loads(prompt)
        question = data['question']
        calls.append(('interpret', question))
        updates = {}
        if '1998-05-15' in question: updates['date_of_birth'] = '1998-05-15'
        if '1800-01-01' in question: updates['date_of_birth'] = '1800-01-01'
        if '나이만' in question: updates['date_of_birth'] = '1998-01-01'
        if '한국' in question: updates['nationalities'] = ['KR']
        return json.dumps(dict(intent='eligibility_review' if '자격' in question else 'official_information',
                               profile_updates=updates, program_ids=[] if '지원' in question or '미정' in question else ['CA:test'],
                               support_program_ids=['S:test'] if '지원' in question else [],
                               information_scope='support' if '지원' in question else 'program'))
    monkeypatch.setattr(user_understanding, 'load_catalog', lambda: (deepcopy(PROGRAMS), deepcopy(SUPPORTS)))
    monkeypatch.setattr(user_understanding.llm, 'extract_json', extract)
    monkeypatch.setattr(program_rag, 'search_program_evidence_hybrid', lambda pid, *_args, **_kwargs: [row(pid)])
    def generation(pid, question, evidence, **kwargs):
        calls.append(('generate', pid))
        return RagGeneration(RagDraft.model_validate(dict(items=[dict(question_part='여권 확인', answer='유효한 여권이 필요합니다.', citation_ids=['p1.s1'])])), 'fake', 'fake')
    monkeypatch.setattr(program_rag, 'generate_rag_draft', generation)
    monkeypatch.setattr(multi_program_rag, '_load_candidates', lambda *_: deepcopy(PROGRAMS))
    def multi_rows(*_args, **_kwargs):
        value = row(); value.pop('program_id')
        value.update(program_ids=['CA:test'], programs=[PROGRAMS[0]])
        return [value]
    monkeypatch.setattr(multi_program_rag, 'search_programs_evidence_hybrid', multi_rows)
    monkeypatch.setattr(multi_program_rag, 'generate_programs_draft', lambda *a, **k: RagGeneration(
        ProgramsDraft.model_validate(dict(items=[dict(program_id='CA:test', question_part='여권', answer='여권 확인이 필요합니다.', citation_ids=['p1.s1'])])), 'fake', 'fake'))
    def support_rows(_sid):
        value=row(); value.pop('program_id'); value['support_program_id']='S:test'; return [value]
    monkeypatch.setattr(support_rag, '_load_all_evidence', support_rows)
    monkeypatch.setattr(support_rag, '_load_support_info', lambda sid: SupportInfo(
        support_program_id=sid, name='테스트 지원', availability='CLOSED', source_verified_at=date(2026,10,28), profile={}, profile_release_id='v1'))
    monkeypatch.setattr(support_rag, 'generate_support_draft', generation)
    def requirements(kind, target):
        rid='r:'+target
        definition=dict(requirement_id=rid, target=dict(target_type=kind.upper(), target_id=target),
                        source_document_ids=['doc:'+target], description='국적 조건 확인',
                        judgeability='conditional', expression=dict(operator='contains', field='nationalities', value='KR'))
        return dict(target_type=kind.upper(), target_id=target, requirement_ids=[rid], coverage_complete=False,
                    application_availability='UNKNOWN', blockers=['partial coverage']), [definition]
    monkeypatch.setattr(eligibility_review, '_load_requirements', requirements)
    app=FastAPI(); app.include_router(create_router(_make_graph().compile()))
    client=TestClient(app)
    sid=client.post('/consult/sessions').json()['session_id']
    return client, sid, calls


def say(setup, message, profile=None):
    client,sid,_=setup
    body=dict(message=message)
    if profile is not None: body['profile']=profile
    response=client.post(f'/consult/sessions/{sid}/messages', json=body)
    assert response.status_code==200, response.text
    return response.json()


@pytest.mark.parametrize('mode', ['general', 'evidence', 'mixed'])
def test_merged_answer_modes_keep_team_routing_and_d_profile(setup, monkeypatch, mode):
    """Exercise the compiled graph/API, rather than checking merged text only."""
    original = user_understanding.llm.extract_json
    def extract(prompt, **kwargs):
        schema = kwargs['response_schema']['properties']
        assert schema['answer_mode']['enum'] == ['general', 'evidence', 'mixed']
        assert 'major' in schema['profile_updates']['items']['properties']['field']['enum']
        parsed = json.loads(original(prompt, **kwargs))
        parsed['answer_mode'] = mode
        parsed['profile_updates']['major'] = '컴퓨터공학'
        return json.dumps(parsed)
    monkeypatch.setattr(user_understanding.llm, 'extract_json', extract)
    guidance_calls = []
    def guidance(question, history, profile, **kwargs):
        guidance_calls.append((profile, kwargs))
        return '일반 준비 방향 안내'
    monkeypatch.setattr(preparation_planning, 'general_guidance', guidance)
    data = say(setup, '공식 안내와 준비 방향', dict(nationalities=['KR']))
    assert data['profile']['major'] == '컴퓨터공학'
    assert bool(guidance_calls) == (mode != 'evidence')
    assert any(kind == 'generate' for kind, _ in setup[2]) == (mode != 'general')
    if mode != 'general':
        assert data['citations']
        assert '유효한 여권이 필요합니다.' in data['reply']
    if mode != 'evidence':
        assert '일반 준비 방향 안내' in data['reply']
    # Reuse the same API session to ensure profile extensions survive another turn.
    again = say(setup, '다음 준비 방향')
    assert again['profile']['major'] == '컴퓨터공학'
    assert again['profile']['nationalities'] == ['KR']


def test_merged_mixed_clarification_keeps_missing_information_and_avoids_rag(setup, monkeypatch):
    original = user_understanding.llm.extract_json
    def extract(prompt, **kwargs):
        parsed = json.loads(original(prompt, **kwargs))
        parsed['answer_mode'] = 'mixed'
        return json.dumps(parsed)
    monkeypatch.setattr(user_understanding.llm, 'extract_json', extract)
    calls = []
    def guidance(question, history, profile, **kwargs):
        calls.append(kwargs)
        return '일반 준비 안내'
    monkeypatch.setattr(preparation_planning, 'general_guidance', guidance)
    data = say(setup, '자격과 준비 방향을 알려줘')
    assert '국적' in data['reply'] and '생년월일' in data['reply']
    assert '일반 준비 안내' in data['reply']
    assert calls == [{'ask_question': False}]
    assert not any(kind == 'generate' for kind, _ in setup[2])


def test_distinct_chat_sessions_keep_profile_history_and_scope_separate(setup, monkeypatch):
    client, australia_sid, _ = setup
    original = user_understanding.llm.extract_json
    contexts = []
    def extract(prompt, **kwargs):
        contexts.append(json.loads(prompt))
        return original(prompt, **kwargs)
    monkeypatch.setattr(user_understanding.llm, 'extract_json', extract)
    first = say(setup, '호주 워홀 알려줘')
    assert first['profile']['target_country'] == 'australia'
    second_sid = client.post('/consult/sessions').json()['session_id']
    assert second_sid != australia_sid
    response = client.post(f'/consult/sessions/{second_sid}/messages', json={'message':'국가 미정 프로그램 알려줘'})
    assert response.status_code == 200
    assert response.json()['profile']['target_country'] is None
    assert contexts[-1]['history'] == [] and contexts[-1]['profile'] == {}
    client.post(f'/consult/sessions/{second_sid}/messages', json={'message':'비교 계속'})
    assert any(message['content'] == '국가 미정 프로그램 알려줘' for message in contexts[-1]['history'])
    assert not any(message['content'] == '호주 워홀 알려줘' for message in contexts[-1]['history'])
    say(setup, '내 상담 이어서')
    assert contexts[-1]['profile']['target_country'] == 'australia'
    assert any(message['content'] == '호주 워홀 알려줘' for message in contexts[-1]['history'])
    assert not any(message['content'] == '비교 계속' for message in contexts[-1]['history'])


def test_first_profile_and_message_use_one_graph_with_real_b_citations(setup):
    data=say(setup, '공식 안내', dict(nationalities=['KR'], date_of_birth='1998-05-15'))
    assert sum(kind=='interpret' for kind,_ in setup[2])==1
    assert sum(kind=='generate' for kind,_ in setup[2])==1
    assert data['citations'][0]['source_url']=='https://example.org/passport'
    assert data['programs'][0]['citations']
    assert any(item['citations'] for item in data['prep_items'])
    assert data['rag_statuses'][0]['development_only'] is False
    assert data['eligibility'][0]['overall']=='추가 확인 필요'
    assert '유효한 여권이 필요합니다.' in data['reply']


def test_general_information_is_not_blocked_by_missing_personal_info(setup):
    data=say(setup, '일반 정보')
    assert data['stage']=='result'
    assert data['profile']['nationalities'] is None
    assert data['eligibility'][0]['unknown_requirement_ids']


def test_personal_check_asks_for_exact_missing_info(setup):
    data=say(setup, '자격 확인')
    assert data['stage']=='asking'
    assert '생년월일' in data['reply']
    assert not any(kind=='generate' for kind,_ in setup[2])


@pytest.mark.parametrize('message', ['나이만 28세 자격', '1800-01-01 자격'])
def test_age_only_or_invalid_birth_date_is_not_invented(setup, message):
    data=say(setup, message)
    assert data['profile']['date_of_birth'] is None
    assert data['stage']=='asking'


def test_explicit_full_birth_date_and_nationality_are_retained(setup):
    data=say(setup, '한국 국적, 1998-05-15 자격')
    assert data['profile']['date_of_birth']=='1998-05-15'
    assert data['profile']['nationalities']==['KR']
    assert data['stage']=='result'


def test_patch_rechecks_without_a_second_interpreter_call(setup):
    say(setup, '공식 안내', dict(nationalities=['KR']))
    before=sum(kind=='interpret' for kind,_ in setup[2])
    response=setup[0].patch(f'/consult/sessions/{setup[1]}/profile', json=dict(target_country='canada', target_visa_type='student'))
    assert response.status_code==200, response.text
    assert sum(kind=='interpret' for kind,_ in setup[2])==before
    assert response.json()['programs']==[]  # No stale working-holiday candidate.


def test_identity_only_patch_preserves_explicit_program_selection(setup):
    say(setup, '공식 안내')
    response=setup[0].patch(f'/consult/sessions/{setup[1]}/profile', json=dict(date_of_birth='1998-05-15'))
    assert response.status_code==200
    assert [p['program_id'] for p in response.json()['programs']]==['CA:test']


def test_support_result_is_separate_and_closed_is_not_open(setup):
    data=say(setup, '지원 제도 알려줘')
    assert data['programs']==[]
    assert data['support_programs'][0]['availability']=='CLOSED'
    assert data['support_eligibility'][0]['support_program_id']=='S:test'
    assert data['support_programs'][0]['citations']
    assert '접수 종료로 기록됨' in data['reply']
    assert data['prep_items'][0]['program_id']=='S:test'


def test_old_stored_status_cannot_answer_current_application_access(setup, monkeypatch):
    monkeypatch.setattr(support_rag, 'generate_support_draft', lambda *a, **k: RagGeneration(
        RagDraft.model_validate(dict(items=[dict(question_part='현재 접수 여부',answer='지금 신청 가능합니다.',citation_ids=['p1.s1'])])), 'fake', 'fake'))
    data=say(setup, '지원금 지금 신청할 수 있나요?')
    assert data['rag_statuses'][0]['status']=='insufficient_evidence'
    assert '지금 신청 가능합니다.' not in data['reply']
    assert data['support_programs'][0]['availability']=='CLOSED'


def test_b_search_failure_is_not_disguised_as_evidence_shortage(setup, monkeypatch):
    monkeypatch.setattr(program_rag, 'search_program_evidence_hybrid', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('offline')))
    response=setup[0].post(f'/consult/sessions/{setup[1]}/messages', json=dict(message='공식 안내'))
    assert response.status_code==503


def test_no_evidence_remains_explicit_and_not_a_generated_answer(setup, monkeypatch):
    monkeypatch.setattr(program_rag, 'search_program_evidence_hybrid', lambda *a, **k: [])
    data=say(setup, '공식 안내')
    assert data['rag_statuses'][0]['status']=='insufficient_evidence'
    assert data['citations']==[]
    assert not any(kind=='generate' for kind,_ in setup[2])


def test_multi_program_search_is_connected_without_country_assumption(setup):
    data=say(setup, '국가 미정 프로그램 알려줘')
    assert {p['program_id'] for p in data['programs']}=={'CA:test','AU:test'}
    assert data['profile']['target_country'] is None
    assert data['citations']


def test_preparation_does_not_overwrite_b_answer_or_invent_deadlines():
    state=dict(final_answer='B의 출처 기반 원문 답변', rag_results=[], eligibility_results=[])
    result=preparation_planning.run(state)
    assert result['final_answer']==state['final_answer']
    assert result['roadmap']==[]


def test_main_app_requires_internal_key(monkeypatch):
    from app.api import main
    monkeypatch.setattr(main,'INTERNAL_API_KEY','synthetic-test-key')
    client=TestClient(main.app)
    assert client.post('/consult/sessions').status_code==401
    assert client.post('/consult/sessions',headers={'x-internal-api-key':'synthetic-test-key'}).status_code==401
    assert client.post('/consult/sessions',headers={'x-internal-api-key':'synthetic-test-key','x-consult-owner':'a'*64}).status_code==200


def test_bad_profile_is_rejected_before_graph(setup):
    response=setup[0].post(f'/consult/sessions/{setup[1]}/messages',json=dict(message='질문',profile={'age':28}))
    assert response.status_code==422
    assert setup[2]==[]

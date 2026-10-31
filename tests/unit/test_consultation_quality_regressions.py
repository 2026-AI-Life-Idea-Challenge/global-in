"""Failure cases observed in real-model runs, replayed as deterministic tests."""
import pytest
import json
from app.agent.user_understanding import normalize_extraction
from app.agent import user_understanding
from app.agent.state import initial_state
from app.services.consultation_catalog import _sources
from app.services.support_rag import guard_duplicate_benefit_claims, guard_current_availability
from app.services.answer_quality import guard_unsupported_absolutes
from app.models.rag import RagDraft
from app.services.rag_llm import _bounded_citation_schema
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from app.api.consult import create_router
from app.api import main as api_main
from app.services import consultation_catalog


@pytest.mark.parametrize('intent', ['support_programs','support_discovery','support_question'])
def test_real_support_intent_alias_is_normalized(intent):
    parsed=normalize_extraction(dict(intent=intent,program_ids=None,support_program_ids=['S'],profile_updates=None))
    assert parsed.intent=='official_information'
    assert parsed.information_scope=='support'
    assert parsed.program_ids==[]
    assert parsed.profile_updates=={}


def test_catalog_sources_are_deduplicated_and_not_approval_claims():
    profile=dict(source_references=[dict(title='공식 안내',source_url='https://example.org',verified_at='2026-10-28'),
                                    dict(source_url='https://example.org'),dict(source_url='javascript:bad')])
    result=_sources(profile)
    assert len(result)==1
    assert result[0]['verified_at']=='2026-10-28'


def test_catalog_route_requires_internal_key_and_sanitizes_failure(monkeypatch):
    monkeypatch.setattr(api_main, 'INTERNAL_API_KEY', 'synthetic-key')
    monkeypatch.setattr(consultation_catalog, 'load_catalog', lambda: {'items': []})
    app=FastAPI()
    app.include_router(create_router(graph=object()), dependencies=[Depends(api_main.require_internal_api_key)])
    client=TestClient(app)
    assert client.get('/consult/catalog').status_code==401
    assert client.get('/consult/catalog',headers={'X-Internal-API-Key':'synthetic-key'}).json()=={'items':[]}
    def fail(): raise RuntimeError('private DB error')
    monkeypatch.setattr(consultation_catalog,'load_catalog',fail)
    result=client.get('/consult/catalog',headers={'X-Internal-API-Key':'synthetic-key'})
    assert result.status_code==503
    assert 'private DB error' not in result.text


def test_catalog_projection_keeps_ids_sources_and_unconfirmed_status(monkeypatch):
    class Connection:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def execute(self,query):
            self.query=query
            if query.startswith('SET'): assert 'READ ONLY' in query
            return self
        def fetchall(self):
            if 'FROM programs p' in self.query:
                return [dict(id='CA:test',name='Test',country='canada',category='study',profile=dict(source=dict(source_url='https://example.org')),release_id='release')]
            return [dict(id='S:test',name='Support',country='multi_country',profile={},availability='CLOSED',destination_countries=['CA'])]
    monkeypatch.setattr(consultation_catalog.db,'get_conn',Connection)
    data=consultation_catalog.load_catalog()
    assert data['counts']==dict(programs=1,supports=1)
    assert data['items'][0]['sources'][0]['source_url']=='https://example.org'
    assert data['items'][1]['availability']=='CLOSED'
    assert all(not item['final_eligibility'] for item in data['items'])


def test_answer_sections_keep_claim_scope_sources_and_per_source_date():
    class Graph:
        def invoke(self,state):
            return {**state,'final_answer':'안내','candidate_support_programs':[dict(support_program_id='S:test',name='지원금')],
                    'rag_results':[dict(support_program_id='S:test',question_parts=['지원 조건'],status='answered',claims=[
                        dict(text='조건을 확인하세요.',part_indexes=[0],citations=[dict(quote='2026년 취업 개시자 안내 기준',
                            title='공식 안내',source_urls=['https://example.org'],source_references=[dict(source_url='https://example.org',verified_at='2026-10-28')])])])]}
    app=FastAPI(); app.include_router(create_router(graph=Graph()))
    client=TestClient(app); sid=client.post('/consult/sessions').json()['session_id']
    result=client.post(f'/consult/sessions/{sid}/messages',json={'message':'지원 조건'}).json()
    section=result['answer_sections'][0]
    assert section['target_name']=='지원금'
    assert section['text']=='조건을 확인하세요.'
    assert section['scope_notes']==['2026년 취업 개시자 안내 기준']
    assert section['citations'][0]['verified_at']=='2026-10-28'


def test_unknown_intent_is_not_silently_changed_into_an_answer():
    with pytest.raises(ValueError): normalize_extraction(dict(intent='invented'))


def test_real_observed_duplicate_benefit_overclaim_is_withheld():
    draft=RagDraft.model_validate(dict(items=[dict(question_part='중복 지원',answer='중복 지원이 불가능하며 별도 심사가 필요합니다.',citation_ids=['p1.s1'])]))
    evidence=[dict(chunk_id='c',body='중복 지원·단계별 지급 요건은 별도 심사한다.')]
    assert guard_duplicate_benefit_claims(draft,evidence).items[0].answer is None


def test_explicit_prohibition_in_source_is_not_rewritten():
    draft=RagDraft.model_validate(dict(items=[dict(question_part='중복 지원',answer='해당 조건에서 중복 지원이 불가능합니다.',citation_ids=['p1.s1'])]))
    evidence=[dict(chunk_id='c',body='해당 조건에서는 중복 지원이 불가능하며 그 밖의 요건은 별도 심사한다.')]
    assert guard_duplicate_benefit_claims(draft,evidence).items[0].answer is not None


def test_source_does_not_support_added_no_exception_modifier():
    draft=RagDraft.model_validate(dict(items=[dict(question_part='건강',answer='건강 기준은 예외 없이 적용됩니다.',citation_ids=['p1.s1'])]))
    assert guard_unsupported_absolutes(draft,[dict(chunk_id='c',body='건강 요건의 충족 여부를 확인한다.')]).items[0].answer is None


def test_unknown_citation_id_is_left_for_regular_validator():
    draft=RagDraft.model_validate(dict(items=[dict(question_part='건강',answer='예외 없이 적용됩니다.',citation_ids=['invented'])]))
    assert guard_unsupported_absolutes(draft,[dict(chunk_id='c',body='조건')]).items[0].citation_ids==['invented']
    temporal=RagDraft.model_validate(dict(items=[dict(question_part='현재 접수 여부',answer='신청 가능합니다.',citation_ids=['invented'])]))
    assert guard_current_availability(temporal,None,'지금 신청할 수 있나요?',evidence=[]).items[0].citation_ids==['invented']


def test_canada_evidence_cannot_be_extended_to_australia():
    draft=RagDraft.model_validate(dict(items=[dict(question_part='체류 기간',answer='캐나다와 호주 모두 최대 24개월입니다.',citation_ids=['p1.s1'])]))
    evidence=[dict(chunk_id='c',body='한국인은 IEC 전체 최대 2회, 1회당 최대 24개월 참여 경로가 있다.')]
    assert guard_unsupported_absolutes(draft,evidence,program_id='CA:iec_working_holiday').items[0].answer is None


def test_model_schema_only_allows_supplied_citation_ids():
    wire=_bounded_citation_schema(RagDraft,('p1.s1','p2.s1'))
    good=dict(items=[dict(question_part='요건',answer='확인',citation_ids=['p1.s1'])])
    assert wire.model_validate(good).items[0].citation_ids==['p1.s1']
    good['items'][0]['citation_ids']=['invented']
    with pytest.raises(ValueError): wire.model_validate(good)


@pytest.mark.parametrize('question,expected', [('호주 417 첫 신청을 비교해줘',['AU:subclass_417_first']),('호주 417을 알려줘',None)])
def test_417_variants_are_not_mixed_or_assumed(monkeypatch,question,expected):
    programs=[dict(program_id='AU:subclass_417_'+stage,name=stage,country='australia',category='working_holiday') for stage in ('first','second','third')]
    monkeypatch.setattr(user_understanding,'load_catalog',lambda:(programs,[]))
    monkeypatch.setattr(user_understanding.llm,'extract_json',lambda *a,**k:json.dumps(dict(intent='official_information',program_ids=[p['program_id'] for p in programs])))
    result=user_understanding.run(initial_state('test',question))
    if expected:
        assert result['requested_program_ids']==expected
        assert result['next_node']!='ask_user'
    else:
        assert result['next_node']=='ask_user'
        assert '어떤 단계' in result['follow_up_question']


def test_latest_stage_in_history_wins_and_negated_first_is_not_selected(monkeypatch):
    programs=[dict(program_id='AU:subclass_417_'+stage,name=stage,country='australia',category='working_holiday') for stage in ('first','second','third')]
    monkeypatch.setattr(user_understanding,'load_catalog',lambda:(programs,[]))
    monkeypatch.setattr(user_understanding.llm,'extract_json',lambda *a,**k:json.dumps(dict(intent='official_information',program_ids=[p['program_id'] for p in programs])))
    history=[dict(role='user',content='호주 417 첫 신청'),dict(role='user',content='호주 417 2차로 바꿀게요')]
    result=user_understanding.run(initial_state('test','호주 417 준비사항',history=history))
    assert result['requested_program_ids']==['AU:subclass_417_second']
    result=user_understanding.run(initial_state('test','호주 417 첫 신청 말고 2차 신청'))
    assert result['requested_program_ids']==['AU:subclass_417_second']


def test_program_scope_is_not_dropped_by_support_classification(monkeypatch):
    programs=[dict(program_id='CA:iec',name='IEC',country='canada',category='working_holiday')]
    monkeypatch.setattr(user_understanding,'load_catalog',lambda:(programs,[]))
    monkeypatch.setattr(user_understanding.llm,'extract_json',lambda *a,**k:json.dumps(dict(intent='official_information',program_ids=['CA:iec'],information_scope='support')))
    result=user_understanding.run(initial_state('test','IEC 신청 조건'))
    assert result['information_scope']=='program'
    result=user_understanding.run(initial_state('test','IEC와 연결되는 지원금'))
    assert result['information_scope']=='support'

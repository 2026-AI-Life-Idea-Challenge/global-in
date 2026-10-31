import json
from app.services import personal_preparation, consultation_b
from app.agent import user_understanding, route_recommendation, official_information
from app.services.rag_llm import production_profile


def test_user_facing_mode_does_not_invent_or_override_nationality():
    assert 'nationalities' not in production_profile({})
    assert production_profile({'nationalities':['CA']})['nationalities']==['CA']


def test_personal_tasks_reflect_rule_outcomes_and_sources(monkeypatch):
    monkeypatch.setattr(personal_preparation, 'load_catalog_detail', lambda _: dict(kind='program', sources=[dict(title='공식',source_url='https://example.org')]))
    def evaluate(state):
        assert state['user_profile']['nationalities'] == ['KR']
        assert state['candidate_programs'] == [{'program_id':'AU:test'}]
        return {'eligibility_results':[{'condition_results':[
            dict(requirement_id='age',description='나이',status='조건 충족',reason='연령 조건 충족'),
            dict(requirement_id='work',description='경력',status='조건 미충족',reason='경력 부족'),
            dict(requirement_id='funds',description='재정',status='추가 확인 필요',reason='정보 부족')]}]}
    monkeypatch.setattr(personal_preparation,'review',evaluate)
    result=personal_preparation.build_preparation('AU:test',{'nationalities':['KR']})
    assert [item['status'] for item in result['items'][:3]] == ['todo','blocked','check_needed']
    assert all(item['citations'] and not item['done'] for item in result['items'])
    assert result['items'][0]['title']=='생년월일과 신청 예정일로 연령 조건 확인하기'
    assert all(len(item['title']) < 60 and item['task_version']==3 for item in result['items'])
    assert result['items'][0]['evidence'][0]['text']=='나이'


def test_wh_overview_is_scoped_even_if_interpreter_returns_empty(monkeypatch):
    programs=[dict(program_id='AU:subclass_417_first', name='AU417',country='australia',category='working_holiday'),
              dict(program_id='AU:482',name='AU482',country='australia',category='employment'),
              dict(program_id='US:H1B',name='H1B',country='usa',category='employment')]
    monkeypatch.setattr(user_understanding,'load_catalog',lambda:(programs,[]))
    monkeypatch.setattr(user_understanding.llm,'extract_json',lambda *a,**k:json.dumps(dict(intent='official_information',profile_updates={'target_country':None},program_ids=[],support_program_ids=[],information_scope='both')))
    state=user_understanding.run(dict(user_query='호주 워홀 전체적으로 알려줘',user_profile={},history=[]))
    assert state['overview'] and not state['follow_up_question']
    assert state['requested_program_ids']==['AU:subclass_417_first']
    routed=route_recommendation.run(state)
    assert routed['next_node']=='official_information'
    assert routed['candidate_support_programs']==[]
    assert [p['program_id'] for p in routed['candidate_programs']]==['AU:subclass_417_first']


def test_overview_followup_retains_previous_scope(monkeypatch):
    programs=[dict(program_id='AU:417',name='AU',country='australia',category='working_holiday')]
    monkeypatch.setattr(user_understanding,'load_catalog',lambda:(programs,[]))
    monkeypatch.setattr(user_understanding.llm,'extract_json',lambda *a,**k:json.dumps(dict(intent='official_information',profile_updates={'target_country':None},program_ids=[],support_program_ids=[],information_scope='program')))
    state=user_understanding.run(dict(user_query='전체적으로 알려줘',user_profile={'target_country':'australia','target_visa_type':'working_holiday'},requested_program_ids=['AU:417'],history=[]))
    assert state['user_profile']['target_country']=='australia'
    assert state['requested_program_ids']==['AU:417']


def test_user_answer_omits_internal_catalogue_dump_but_keeps_claims(monkeypatch):
    monkeypatch.setattr(official_information,'answer',lambda _: [dict(answer='development internal list US:H1B',claims=[dict(text='근거에 있는 조건',citations=[])])])
    output=official_information.run({'candidate_programs':[]})
    assert output['final_answer']=='근거에 있는 조건'
    assert 'US:H1B' not in output['final_answer']


def test_long_rule_is_an_action_with_original_kept_as_evidence(monkeypatch):
    original='Licensing, registration or membership You must be licensed, registered or a member of a professional body if mandatory. 적용 범위·예외: 노동협약 당하는 실제 해당 협약이 허용하는 요건에만 적용한다.'
    monkeypatch.setattr(personal_preparation,'load_catalog_detail',lambda _:dict(kind='program',sources=[]))
    monkeypatch.setattr(personal_preparation,'review',lambda _:{'eligibility_results':[{'condition_results':[dict(requirement_id='license',description=original,status='추가 확인 필요')]}]})
    item=personal_preparation.build_preparation('AU:test',{})['items'][0]
    assert item['title']=='근무 지역의 직업 면허·등록 필요 여부 확인하기'
    assert 'Licensing' not in item['description']
    assert item['evidence'][0]['text']==original

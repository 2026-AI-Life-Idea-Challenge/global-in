from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.consult import create_router
from app.models.user_profile import UserProfile
from app.models.consult import ProfileUpdateRequest

def test_frontend_profile_fields_round_trip_without_turning_text_into_rules():
    captured=[]
    class Graph:
        def invoke(self,state):captured.append(state);return {**state,'final_answer':'확인'}
    app=FastAPI();app.include_router(create_router(Graph()));client=TestClient(app)
    sid=client.post('/consult/sessions').json()['session_id']
    profile=dict(residence_country='KR',education='대학교',education_status='졸업',major='컴퓨터공학',career='웹 개발',career_duration='3년',languages='일본어',certifications='JLPT N2')
    response=client.post(f'/consult/sessions/{sid}/messages',json=dict(message='내 정보 확인',profile=profile))
    assert response.status_code==200
    assert all(response.json()['profile'][key]==value for key,value in profile.items())
    evaluator=UserProfile(**profile).to_evaluator_dict()
    assert evaluator=={'residence_country':'KR'}

def test_residence_country_uses_explicit_iso_code():
    import pytest
    from pydantic import ValidationError
    assert ProfileUpdateRequest(residence_country='JP').residence_country=='JP'
    with pytest.raises(ValidationError):ProfileUpdateRequest(residence_country='일본')

def test_full_response_can_round_trip_when_unset_internal_fields_are_null():
    profile=UserProfile(nationalities=['KR'],date_of_birth='1998-05-15').model_dump()
    assert 'insurance_medical_care' in profile
    request=ProfileUpdateRequest.model_validate(profile)
    assert request.nationalities==['KR']
    assert 'insurance_medical_care' not in request.model_dump()

def test_non_null_unknown_fields_are_not_silently_discarded():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):ProfileUpdateRequest.model_validate({'invented_approval':True})

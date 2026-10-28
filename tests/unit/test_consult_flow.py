"""C 상담 흐름: 추가 질문 → 결과·출처·체크리스트 → 정보 변경 후 재검토. (LLM 대신 가짜 추출기, A·B는 stubs)"""

import re
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.graph import build_graph
from app.api.consult import create_router
from app.models.consult import ProfileDelta
from app.models.user_profile import UserProfile

_COUNTRIES = {"캐나다": "canada", "호주": "australia", "일본": "japan", "미국": "usa", "독일": "germany"}


def fake_extractor(message: str, profile: UserProfile) -> ProfileDelta:
    delta = ProfileDelta()
    for word, country in _COUNTRIES.items():
        if word in message:
            delta.target_country = country
    if "워홀" in message:
        delta.target_visa_type = "working_holiday"
    if m := re.search(r"\d{4}-\d{2}-\d{2}", message):
        delta.date_of_birth = m.group(0)
    return delta


def dob_for_age(age: int) -> str:
    """오늘 기준 만 age살이 되는 생년월일."""
    today = date.today()
    try:
        return today.replace(year=today.year - age).isoformat()
    except ValueError:  # 2월 29일
        return today.replace(year=today.year - age, day=28).isoformat()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(create_router(build_graph(fake_extractor)))
    return TestClient(app)


@pytest.fixture
def session_id(client):
    return client.post("/consult/sessions").json()["session_id"]


def say(client, session_id, message):
    res = client.post(f"/consult/sessions/{session_id}/messages", json={"message": message})
    assert res.status_code == 200, res.text
    return res.json()


def test_full_consult_flow(client, session_id):
    # 1. 기본 정보가 부족하면 추가 질문
    first = say(client, session_id, "캐나다 워홀 가고 싶어요")
    assert first["stage"] == "asking"
    assert [q["field"] for q in first["follow_up_questions"]] == ["date_of_birth"]

    # 2. 답하면 검토 결과 + 출처 있는 준비 항목
    second = say(client, session_id, f"생년월일은 {dob_for_age(28)}이에요")
    assert second["stage"] == "result"
    assert second["profile"]["date_of_birth"] == dob_for_age(28)
    [result] = second["eligibility"]
    assert result["program_id"] == "CA:iec_working_holiday"
    assert result["overall"] == "추가 확인 필요"
    assert result["unknown_requirement_ids"] == ["REVIEW:POLICY:CA_IEC_WH_POL_01"]
    statuses = {item["status"] for item in second["prep_items"]}
    assert statuses == {"check_needed", "todo"}
    assert all(item["citations"] for item in second["prep_items"])

    # 3. 정보가 바뀌면 다시 검토
    third = say(client, session_id, f"사실 {dob_for_age(40)}생이에요")
    assert third["eligibility"][0]["overall"] == "조건 미충족"
    assert "date_of_birth" in third["reply"]
    assert any(item["status"] == "blocked" for item in third["prep_items"])


def test_profile_patch_rechecks(client, session_id):
    say(client, session_id, f"캐나다 워홀 가고 싶어요, {dob_for_age(40)}생이에요")
    res = client.patch(f"/consult/sessions/{session_id}/profile", json={"date_of_birth": dob_for_age(30)})
    assert res.status_code == 200
    assert res.json()["eligibility"][0]["overall"] == "추가 확인 필요"


def test_invalid_input_rejected(client, session_id):
    assert client.patch(f"/consult/sessions/{session_id}/profile", json={"date_of_birth": "1800-01-01"}).status_code == 422
    assert client.patch(f"/consult/sessions/{session_id}/profile", json={"date_of_birth": "not-a-date"}).status_code == 422
    assert client.patch(f"/consult/sessions/{session_id}/profile", json={"age": 30}).status_code == 422
    assert client.patch(f"/consult/sessions/{session_id}/profile", json={"unknown": 1}).status_code == 422
    assert client.post("/consult/sessions/nope/messages", json={"message": "hi"}).status_code == 404


def test_extracted_invalid_value_is_dropped(client, session_id):
    body = say(client, session_id, "캐나다 워홀, 1800-01-01생이에요")
    assert body["profile"]["date_of_birth"] is None
    assert body["stage"] == "asking"


def test_main_app_requires_internal_api_key(monkeypatch):
    from app.api import main

    monkeypatch.setattr(main, "INTERNAL_API_KEY", "test-key")
    client = TestClient(main.app)  # lifespan(DB 연결)은 실행하지 않는다
    assert client.post("/consult/sessions").status_code == 401
    assert client.post("/consult/sessions", headers={"x-internal-api-key": "test-key"}).status_code == 200


def test_eligibility_receives_evaluator_dict(client, session_id, monkeypatch):
    from app.agent import stubs

    seen = {}
    original = stubs.check_eligibility

    def spy(profile, program_ids, as_of):
        seen["profile"] = profile
        return original(profile, program_ids, as_of)

    monkeypatch.setattr(stubs, "check_eligibility", spy)
    say(client, session_id, f"캐나다 워홀, {dob_for_age(28)}생이에요")
    # A에는 to_evaluator_dict() 형식으로 간다: 검색용 필드는 빠지고 생년월일은 그대로
    assert seen["profile"] == {"date_of_birth": dob_for_age(28)}

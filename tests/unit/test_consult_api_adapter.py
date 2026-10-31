"""Current graph to D contract integration without DB or paid model calls."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.consult import create_router


class FakeGraph:
    def __init__(self):
        self.inputs = []

    def invoke(self, state):
        self.inputs.append(state)
        return {**state, 'final_answer': '근거 기반 안내',
                'candidate_programs': [dict(program_id='CA:iec', name='IEC', country='canada',
                                            category='working_holiday', description='교류 프로그램')],
                'eligibility_results': [dict(target_type='program', target_id='CA:iec',
                                             status='추가 확인 필요', condition_results=[])],
                'validated_evidence': [dict(chunk_id='c1', source_title='공식 안내', source_url='https://canada.ca/')],
                'checklist': [dict(item_id='p1', target_id='CA:iec', title='서류 확인', description='원문 확인')]}


def setup_client(graph=None):
    graph = graph or FakeGraph()
    app = FastAPI()
    app.include_router(create_router(graph))
    client = TestClient(app)
    session_id = client.post('/consult/sessions').json()['session_id']
    return client, session_id, graph


def test_current_graph_response_and_session_history():
    client, sid, graph = setup_client()
    response = client.post(f'/consult/sessions/{sid}/messages', json={'message': '캐나다 워홀'})
    assert response.status_code == 200
    data = response.json()
    assert data['programs'][0]['program_id'] == 'CA:iec'
    assert data['eligibility'][0]['overall'] == '추가 확인 필요'
    assert data['citations'][0]['source_url'] == 'https://canada.ca/'
    assert data['prep_items'][0]['status'] == 'check_needed'
    assert data['prep_items'][0]['done'] is False
    assert graph.inputs[0]['user_query'] == '캐나다 워홀'
    response = client.patch(f'/consult/sessions/{sid}/profile', json={'nationalities': ['KR']})
    assert response.status_code == 200
    assert graph.inputs[1]['user_profile']['nationalities'] == ['KR']
    assert len(graph.inputs[1]['history']) == 2
    client.post(f'/consult/sessions/{sid}/messages', json={'message': '준비 항목 알려줘'})
    assert len(graph.inputs[2]['history']) == 4


def test_missing_session_and_validation():
    client, sid, _ = setup_client()
    assert client.post('/consult/sessions/missing/messages', json={'message': '질문'}).status_code == 404
    assert client.post(f'/consult/sessions/{sid}/messages', json={'message': ''}).status_code == 422
    assert client.patch(f'/consult/sessions/{sid}/profile', json={'unexpected': True}).status_code == 422


def test_failure_releases_lock_and_does_not_save_turn():
    graph = FakeGraph()
    original = graph.invoke
    graph.invoke = lambda state: (_ for _ in ()).throw(RuntimeError('test failure'))
    client, sid, _ = setup_client(graph)
    assert client.post(f'/consult/sessions/{sid}/messages', json={'message': '질문'}).status_code == 503
    graph.invoke = original
    assert client.post(f'/consult/sessions/{sid}/messages', json={'message': '재시도'}).status_code == 200
    assert graph.inputs[0]['history'] == []


def test_questions_and_session_isolation():
    class QuestionGraph(FakeGraph):
        def invoke(self, state):
            self.inputs.append(state)
            return {**state, 'follow_up_question': '생년월일을 알려주세요.'}

    client, sid, graph = setup_client(QuestionGraph())
    response = client.patch(f'/consult/sessions/{sid}/profile', json={'nationalities': ['KR']}).json()
    assert response['stage'] == 'asking'
    assert response['follow_up_questions'][0]['question'] == '생년월일을 알려주세요.'
    other = client.post('/consult/sessions').json()['session_id']
    client.post(f'/consult/sessions/{other}/messages', json={'message': '다른 사용자'})
    assert graph.inputs[-1]['user_profile'] == {}
    assert graph.inputs[-1]['history'] == []

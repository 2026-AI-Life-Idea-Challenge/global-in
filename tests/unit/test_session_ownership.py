"""Ownership, capacity and failure rollback without real model calls."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.consult import create_router
from app.services.consultation_sessions import MemorySessions, SQLiteSessions, MissingSession

@pytest.mark.parametrize('backend',['memory','sqlite'])
def test_foreign_owner_cannot_acquire_or_clear_lease(tmp_path,backend):
    store=MemorySessions() if backend=='memory' else SQLiteSessions(tmp_path/'owned.sqlite')
    sid=store.create('owner-a')
    with pytest.raises(MissingSession): store.acquire(sid,'owner-b')
    _,token=store.acquire(sid,'owner-a');store.commit(sid,token,{'private':True});store.release(sid,token)
    with pytest.raises(MissingSession): store.acquire(sid,'')
    state,token=store.acquire(sid,'owner-a');assert state=={'private':True};store.release(sid,token)

def test_owner_required_for_messages_and_profile():
    class Graph:
        def invoke(self,state):return {**state,'final_answer':'확인'}
    app=FastAPI();app.include_router(create_router(Graph(),require_owner=True))
    client=TestClient(app);owner={'X-Consult-Owner':'a'*64};foreign={'X-Consult-Owner':'b'*64}
    assert client.post('/consult/sessions').status_code==401
    sid=client.post('/consult/sessions',headers=owner).json()['session_id']
    for method,payload,path in [('POST',{'message':'질문'},'messages'),('PATCH',{'nationalities':['KR']},'profile')]:
        assert client.request(method,f'/consult/sessions/{sid}/{path}',json=payload).status_code==401
        assert client.request(method,f'/consult/sessions/{sid}/{path}',json=payload,headers=foreign).status_code==404
        assert client.request(method,f'/consult/sessions/{sid}/{path}',json=payload,headers=owner).status_code==200

def test_capacity_rejects_without_model_execution_and_recovers(monkeypatch):
    monkeypatch.setenv('CONSULT_MAX_CONCURRENT','1')
    entered,finish=Event(),Event()
    class Graph:
        def invoke(self,state):entered.set();assert finish.wait(10);return {**state,'final_answer':'확인'}
    app=FastAPI();app.include_router(create_router(Graph()));client=TestClient(app)
    first=client.post('/consult/sessions').json()['session_id'];second=client.post('/consult/sessions').json()['session_id']
    with ThreadPoolExecutor(max_workers=1) as pool:
        active=pool.submit(client.post,f'/consult/sessions/{first}/messages',json={'message':'질문'})
        try:
            assert entered.wait(10)
            assert client.post(f'/consult/sessions/{first}/messages',json={'message':'중복'}).status_code==409
            rejected=client.post(f'/consult/sessions/{second}/messages',json={'message':'질문'})
            assert rejected.status_code==503 and rejected.headers['retry-after']=='2'
        finally:finish.set()
        assert active.result().status_code==200
    assert client.post(f'/consult/sessions/{second}/messages',json={'message':'재시도'}).status_code==200

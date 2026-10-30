"""Persistent restart recovery, cross-worker exclusion and lease ownership."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.consult import create_router
from app.services.consultation_sessions import SQLiteSessions, MissingSession, BusySession
from app.services import consultation_sessions as module


def test_restart_and_two_workers_share_committed_state(tmp_path):
    path=tmp_path/'sessions.sqlite'
    first=SQLiteSessions(path); sid=first.create()
    state,token=first.acquire(sid)
    first.commit(sid,token,dict(user_profile={'nationalities':['KR']})); first.release(sid,token)
    second=SQLiteSessions(path); state,token=second.acquire(sid)
    assert state['user_profile']['nationalities']==['KR']
    with pytest.raises(BusySession): first.acquire(sid)
    second.release(sid,token)


def test_expired_session_is_missing(tmp_path,monkeypatch):
    monkeypatch.setattr(module.time,'time',lambda:1000)
    store=SQLiteSessions(tmp_path/'s.sqlite',ttl=10); sid=store.create()
    monkeypatch.setattr(module.time,'time',lambda:1011)
    with pytest.raises(MissingSession): store.acquire(sid)


def test_stale_worker_cannot_commit_or_release_new_lease(tmp_path,monkeypatch):
    monkeypatch.setattr(module.time,'time',lambda:1000)
    first=SQLiteSessions(tmp_path/'s.sqlite',lease_seconds=10); sid=first.create()
    _,old=first.acquire(sid)
    monkeypatch.setattr(module.time,'time',lambda:1011)
    second=SQLiteSessions(tmp_path/'s.sqlite'); _,new=second.acquire(sid)
    with pytest.raises(BusySession): first.commit(sid,old,{'bad':True})
    first.release(sid,old)
    with pytest.raises(BusySession): first.acquire(sid)
    second.commit(sid,new,{'good':True}); second.release(sid,new)
    state,token=first.acquire(sid); assert state=={'good':True}; first.release(sid,token)


def test_failed_serialization_does_not_save_invalid_state(tmp_path):
    store=SQLiteSessions(tmp_path/'s.sqlite'); sid=store.create(); _,token=store.acquire(sid)
    with pytest.raises(ValueError): store.commit(sid,token,{'value':float('nan')})
    store.release(sid,token); state,token=store.acquire(sid)
    assert state=={}; store.release(sid,token)


def test_api_restart_preserves_profile_history_and_single_first_execution(tmp_path):
    calls=[]
    class Graph:
        def invoke(self,state): calls.append(state); return {**state,'final_answer':'검증 응답'}
    def client():
        app=FastAPI(); app.include_router(create_router(Graph(),SQLiteSessions(tmp_path/'s.sqlite')))
        return TestClient(app)
    first=client(); sid=first.post('/consult/sessions').json()['session_id']
    result=first.post(f'/consult/sessions/{sid}/messages',json=dict(message='첫 질문',profile={'nationalities':['KR']}))
    assert result.status_code==200
    assert len(calls)==1
    second=client(); result=second.post(f'/consult/sessions/{sid}/messages',json={'message':'다음 질문'})
    assert result.status_code==200
    assert calls[-1]['user_profile']['nationalities']==['KR']
    assert len(calls[-1]['history'])==2

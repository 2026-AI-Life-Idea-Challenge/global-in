from contextlib import contextmanager
from app.services import consultation_catalog as catalog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.consult import create_router

def test_detail_uses_current_target_bound_dataset_and_exact_body(monkeypatch):
    monkeypatch.setattr(catalog,'load_catalog',lambda:{'items':[dict(id='AU:test',kind='program',name='Test')]})
    calls=[]
    class Connection:
        def execute(self,query,params=None):calls.append((query,params));return self
        def fetchall(self):return [dict(chunk_id='c',body='Age condition\n원문과 예외를 그대로 유지한다.',title='Official document',metadata={'verified_at':'2026-10-28','source_references':[dict(source_url='https://example.org')]} )]
    @contextmanager
    def connect():yield Connection()
    monkeypatch.setattr(catalog.db,'get_conn',connect)
    result=catalog.load_catalog_detail('AU:test')
    assert 'READ ONLY' in calls[0][0]
    assert calls[1][1]==('PROGRAM','AU:test')
    assert 'd.active AND c.active' in calls[1][0]
    assert result['sections'][0]['body']=='Age condition\n원문과 예외를 그대로 유지한다.'
    assert result['sections'][0]['sources'][0]['source_url']=='https://example.org'

def test_detail_missing_target_and_database_error_are_distinct(monkeypatch):
    app=FastAPI();app.include_router(create_router(graph=object()));client=TestClient(app)
    monkeypatch.setattr(catalog,'load_catalog_detail',lambda _:None)
    assert client.get('/consult/catalog/missing').status_code==404
    def fail(_):raise RuntimeError('private failure')
    monkeypatch.setattr(catalog,'load_catalog_detail',fail)
    result=client.get('/consult/catalog/missing')
    assert result.status_code==503 and 'private failure' not in result.text

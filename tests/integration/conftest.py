"""Offline integration tests use real imports and explicit boundary mocks."""
import pytest


@pytest.fixture(autouse=True)
def deny_external_io(monkeypatch):
    import psycopg
    from app.services import llm
    def blocked(*args, **kwargs):
        raise AssertionError('Integration test attempted unmocked DB or paid LLM access')
    monkeypatch.setattr(psycopg, 'connect', blocked)
    monkeypatch.setattr(llm, 'extract_json', blocked)

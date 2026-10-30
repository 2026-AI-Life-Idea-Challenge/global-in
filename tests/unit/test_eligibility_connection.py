"""A-C bridge contract; no live DB, LLM or embedding calls."""
from contextlib import contextmanager
from copy import deepcopy

import pytest

from app.agent import eligibility_review as bridge
from app.rules.evaluator import PASS, FAIL, UNKNOWN


def fixtures(target_type='PROGRAM'):
    target = dict(target_type=target_type, target_id='test:1')
    rules = dict(**target, requirement_ids=['r1'], coverage_complete=False,
                 application_availability='UNKNOWN', blockers=['partial coverage'])
    requirement = dict(requirement_id='r1', target=target, source_document_ids=['doc1'],
                       expression=dict(operator='gte', field='funds', value=2500))
    return rules, requirement


def install_db(monkeypatch, rules, requirements, missing=False, broken=False):
    calls = []

    class Cursor:
        def fetchone(self):
            return None if missing else dict(definition=deepcopy(rules), release_id='release1')

        def fetchall(self):
            return [dict(definition=deepcopy(item)) for item in requirements]

    class Conn:
        def execute(self, query, params=None):
            calls.append((query, params))
            if broken:
                raise RuntimeError('database unavailable')
            return Cursor()

    @contextmanager
    def connect():
        yield Conn()

    monkeypatch.setattr(bridge.db, 'get_conn', connect)
    return calls


@pytest.mark.parametrize('target_type', ['program', 'support_program'])
@pytest.mark.parametrize('funds,expected', [(2499, FAIL), (2500, PASS), (None, UNKNOWN)])
def test_canonical_definitions_and_real_evaluator(monkeypatch, target_type, funds, expected):
    rules, requirement = fixtures(target_type.upper())
    calls = install_db(monkeypatch, rules, [requirement])
    result = bridge._run_rule_evaluator(target_type, 'test:1', {} if funds is None else {'funds': funds}, '2026-10-31')
    assert result['target_type'] == target_type  # C's public contract is unchanged.
    assert result['status'] == UNKNOWN  # Partial source coverage is not final eligibility.
    assert result['condition_results'][0]['status'] == expected
    assert calls[1][1] == (target_type.upper(), 'test:1')
    assert calls[2][1] == (target_type.upper(), 'test:1', 'release1')
    assert 'READ ONLY' in calls[0][0]


def test_absent_rules_and_missing_requirement_are_distinct(monkeypatch):
    rules, _ = fixtures()
    install_db(monkeypatch, rules, [], missing=True)
    assert bridge._run_rule_evaluator('program', 'test:1', {}, '2026-10-31') is None
    install_db(monkeypatch, rules, [])
    result = bridge._run_rule_evaluator('program', 'test:1', {}, '2026-10-31')
    assert result['condition_results'][0]['reason'] == '요건 자료 누락'


def test_db_errors_are_not_silently_reported_as_missing_rules(monkeypatch):
    rules, requirement = fixtures()
    install_db(monkeypatch, rules, [requirement], broken=True)
    with pytest.raises(RuntimeError):
        bridge._load_requirements('program', 'test:1')


def test_wrong_target_definition_is_rejected(monkeypatch):
    rules, requirement = fixtures()
    rules['target_id'] = 'other'
    install_db(monkeypatch, rules, [requirement])
    with pytest.raises(ValueError):
        bridge._load_requirements('program', 'test:1')

"""Canonical DB definitions and source-date guards for A's dedicated checker."""
from copy import deepcopy
from dataclasses import replace

import pytest

from app.agent.eligibility.checker import check_eligibility, recheck_with_updated_profile
from app.agent.eligibility.fetcher import RuleSet, RequirementRecord
from app.rules.evaluator import PASS, FAIL, UNKNOWN, evaluate_requirement


def records(complete=False):
    target = dict(target_type='PROGRAM', target_id='TEST:1')
    definition = dict(requirement_id='r1', target=target, verified_at='2026-10-31',
                      source_document_ids=['doc1'], expression=dict(operator='gte', field='funds', value=2500))
    rule_set = RuleSet('rs1', 'PROGRAM', 'TEST:1', complete, dict(requirement_ids=['r1']), 'v1')
    return rule_set, RequirementRecord('r1', 'PROGRAM', 'TEST:1', 'conditional', definition, 'v1')


@pytest.mark.parametrize('funds,outcome', [(2499, FAIL), (2500, PASS), (None, UNKNOWN)])
def test_full_definition_matches_shared_evaluator(funds, outcome):
    rules, req = records()
    profile = {} if funds is None else {'funds': funds}
    result = check_eligibility(rules, [req], profile, '2026-10-31')
    expected = evaluate_requirement(req.definition, profile, '2026-10-31')
    assert result.requirements[0].outcome == expected['status'] == outcome
    if outcome == PASS:
        assert result.overall == UNKNOWN


@pytest.mark.parametrize('day', ['2026-10-30', '2026-11-01'])
def test_stale_or_future_verification_is_not_current(day):
    rules, req = records(True)
    result = check_eligibility(rules, [req], {'funds': 3000}, day)
    assert result.overall == UNKNOWN
    assert result.requirements[0].reason == '요청 시점의 근거 재확인 필요'


@pytest.mark.parametrize('field,value', [('effective_from', '2026-11-01'), ('effective_until', '2026-10-30')])
def test_effective_period_boundaries(field, value):
    rules, req = records(True)
    req.definition[field] = value
    result = check_eligibility(rules, [req], {'funds': 3000}, '2026-10-31')
    assert result.overall == UNKNOWN
    assert result.requirements[0].reason == '적용 기간 밖의 조건'


@pytest.mark.parametrize('change', ['row_target', 'definition_target', 'release', 'identity', 'duplicate'])
def test_cross_target_release_and_duplicate_isolation(change):
    rules, req = records(True)
    req = deepcopy(req)
    if change == 'row_target': req = replace(req, target_id='OTHER')
    if change == 'definition_target': req.definition['target']['target_id'] = 'OTHER'
    if change == 'release': req = replace(req, release_id='v2')
    if change == 'identity': req.definition['requirement_id'] = 'OTHER'
    result = check_eligibility(rules, [req, req] if change == 'duplicate' else [req], {'funds': 3000}, '2026-10-31')
    assert result.overall == UNKNOWN


def test_missing_expected_rule_is_preserved_as_unknown():
    rules, req = records(True)
    rules.definition['requirement_ids'].append('missing')
    result = check_eligibility(rules, [req], {'funds': 3000}, '2026-10-31')
    assert result.overall == UNKNOWN
    assert result.requirements[-1].reason == '요건 자료 누락'


def test_recheck_and_legacy_expression_are_supported_without_false_pass():
    rules, req = records()
    req.definition = req.definition['expression']
    initial = check_eligibility(rules, [req], {'funds': 2000}, '2026-10-31')
    rechecked = recheck_with_updated_profile(rules, [req], {'funds': 3000}, '2026-10-31')
    assert initial.requirements[0].outcome == FAIL
    assert rechecked.requirements[0].outcome == PASS
    assert rechecked.overall == UNKNOWN


def test_nested_boolean_definition_accepts_shared_tuple_context():
    rules, req = records()
    req.definition['expression'] = dict(operator='all', children=[
        dict(operator='gte', field='funds', value=2500),
        dict(operator='any', children=[dict(operator='equals', field='ticket', value=True), dict(operator='equals', field='extra_funds', value=True)]),
    ])
    result = check_eligibility(rules, [req], {'funds': 3000, 'ticket': True}, '2026-10-31')
    assert result.requirements[0].outcome == PASS
    assert result.overall == UNKNOWN

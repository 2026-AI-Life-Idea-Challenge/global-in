"""Current function-node profile validation and selective questions."""
import json
import pytest
from app.agent import user_understanding as node
from app.agent.state import initial_state


@pytest.mark.parametrize('query,dob,expected', [('28세', '1998-01-01', None), ('1998-05-15생', '1998-05-15', '1998-05-15'), ('1800-01-01생', '1800-01-01', None)])
def test_birth_date_is_explicit_and_valid(monkeypatch, query, dob, expected):
    monkeypatch.setattr(node, 'load_catalog', lambda: ([], []))
    monkeypatch.setattr(node.llm, 'extract_json', lambda *a, **k: json.dumps(dict(intent='eligibility_review', profile_updates={'date_of_birth':dob})))
    result=node.run(initial_state('test',query))
    assert result['user_profile'].get('date_of_birth')==expected
    assert result['next_node']=='ask_user'  # Nationality is still absent.


def test_general_search_does_not_require_personal_info(monkeypatch):
    monkeypatch.setattr(node,'load_catalog',lambda:([],[]))
    monkeypatch.setattr(node.llm,'extract_json',lambda *a,**k:json.dumps(dict(intent='official_information')))
    assert node.run(initial_state('test','제도 알려줘'))['next_node']=='route_recommendation'


def test_unknown_target_id_is_rejected(monkeypatch):
    monkeypatch.setattr(node,'load_catalog',lambda:([],[]))
    monkeypatch.setattr(node.llm,'extract_json',lambda *a,**k:json.dumps(dict(intent='official_information',program_ids=['invented'])))
    result=node.run(initial_state('test','비자'))
    assert result['next_node']=='ask_user'
    assert result['requested_program_ids']==[]
    assert '공식 이름' in result['follow_up_question']

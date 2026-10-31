"""B answers remain unchanged; only claim-bound evidence is exposed."""
from app.agent import official_information as node


def test_grounded_answer_and_only_claim_sources(monkeypatch):
    result=dict(answer='B의 원문 답변',claims=[dict(text='조건',citations=[dict(chunk_id='c',source_urls=['https://example.org','javascript:bad'],quote='원문',title='자료')])],
                evidence=[dict(chunk_id='unused',source_urls=['https://unused.org'])])
    monkeypatch.setattr(node,'answer',lambda state:[result])
    output=node.run(dict(user_query='질문'))
    assert output['final_answer']=='조건'
    assert [e['source_url'] for e in output['validated_evidence']]==['https://example.org']


def test_empty_candidates_are_not_an_eligibility_denial(monkeypatch):
    monkeypatch.setattr(node,'answer',lambda state:[])
    result=node.run(dict(user_query='질문'))
    assert '찾지 못했습니다' in result['final_answer']
    assert result['validated_evidence']==[]

"""Exercise the real graph and PostgreSQL reads; no paid LLM or embeddings.

Only generation and vector inference/search are replaced. Keyword retrieval,
support source loading, B citation validation and A evaluation remain real.
"""
from pathlib import Path
import json
import re
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.graph import _make_graph
from app.api.consult import create_router
from app.models.rag import RagDraft, RagGeneration
from app.services import db
from app.services.rag_llm import build_citation_spans
from app.retrieval.keyword_search import search_program_evidence_by_keyword


def counts():
    with db.get_conn() as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        return {table: conn.execute('SELECT count(*) AS n FROM '+table).fetchone()['n']
                for table in ('programs', 'policy_candidates', 'knowledge_chunks', 'knowledge_chunk_embeddings')}


def main():
    load_dotenv(ROOT/'.env')
    before = counts()
    with db.get_conn() as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        row = conn.execute("""SELECT c.body FROM knowledge_chunks c
            JOIN knowledge_document_targets t USING(document_id,revision_id)
            WHERE t.target_id=%s AND c.active=true LIMIT 1""", ('CA:iec_working_holiday',)).fetchone()
    assert row, 'Current CA source chunk is absent'
    candidates = ['passport', 'age', 'work', 'Canada', 'application', '여권', '국적'] + re.findall(r'[A-Za-z]{5,}', row['body'])[:15]
    word = next((word for word in candidates if search_program_evidence_by_keyword('CA:iec_working_holiday', word, limit=1)), None)
    assert word, 'No representative keyword matched the current CA chunks'
    calls = {'interpreter': 0, 'generation': 0}

    def extract(prompt, **kwargs):
        calls['interpreter'] += 1
        question = json.loads(prompt)['question']
        return json.dumps(dict(intent='official_information', profile_updates={},
                               program_ids=[] if question == '지원' else ['CA:iec_working_holiday'],
                               support_program_ids=['CA_WATERLOO_IMAE'] if question == '지원' else [],
                               information_scope='support' if question == '지원' else 'program'))

    def generate(target, question, evidence, **kwargs):
        calls['generation'] += 1
        spans = build_citation_spans(evidence)
        assert spans
        draft = RagDraft.model_validate(dict(items=[dict(question_part='공식 근거 확인',
                answer='공식 원문의 해당 구절을 확인해 주세요.', citation_ids=[next(iter(spans))])]))
        return RagGeneration(draft, 'synthetic-readonly-test', 'synthetic-readonly-test')

    with patch('app.agent.user_understanding.llm.extract_json', side_effect=extract), \
         patch('app.retrieval.hybrid_search.embed_query_local', return_value=[]), \
         patch('app.retrieval.hybrid_search.search_program_evidence_by_vector', return_value=[]), \
         patch('app.services.program_rag.generate_rag_draft', side_effect=generate), \
         patch('app.services.support_rag.generate_support_draft', side_effect=generate):
        app = FastAPI()
        app.include_router(create_router(_make_graph().compile()))
        client = TestClient(app)
        sid = client.post('/consult/sessions').json()['session_id']
        response = client.post(f'/consult/sessions/{sid}/messages', json=dict(message=word,
                     profile=dict(nationalities=['KR'], date_of_birth='1998-05-15', target_country='canada', target_visa_type='working_holiday')))
        assert response.status_code == 200, response.text
        visa = response.json()
        assert calls['interpreter'] == 1
        assert visa['citations'], 'Real keyword passages did not produce bound citations'
        assert visa['eligibility'][0]['requirements']
        response = client.post(f'/consult/sessions/{sid}/messages', json=dict(message='지원'))
        assert response.status_code == 200, response.text
        support = response.json()
        assert support['support_programs'] and support['support_eligibility']
        assert support['citations']
        interpretations = calls['interpreter']
        response = client.patch(f'/consult/sessions/{sid}/profile', json=dict(target_country='australia', target_visa_type='student'))
        assert response.status_code == 200, response.text
        assert calls['interpreter'] == interpretations
        assert response.json()['programs']
        assert all(p['country'] == 'australia' and p['visa_type'] == 'student' for p in response.json()['programs'])
    after = counts()
    assert before == after
    report = dict(keyword_graph_passed=True, support_graph_passed=True, profile_recheck_passed=True,
                  first_message_interpreter_calls=1, profile_patch_interpreter_calls=0,
                  source_citations=len(visa['citations']), support_citations=len(support['citations']),
                  counts_before=before, counts_after=after, model_calls_replaced=calls,
                  paid_llm_executed=False, embeddings_generated=False, knowledge_db_modified=False,
                  semantic_answer_quality_verified=False)
    (ROOT/'docs/architecture/bc-readonly-verification-20261031.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

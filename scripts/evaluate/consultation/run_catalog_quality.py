"""Full-catalog, paid, real-graph evaluation; synthetic profiles, no video."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--limit', type=int, default=52)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--max-model-calls', type=int, default=200)
    parser.add_argument('--output', default='data/processed/quality/consultation/catalog_quality.json')
    args = parser.parse_args()
    if not args.live: raise SystemExit('Explicit --live required: paid API calls.')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    import truststore
    truststore.inject_into_ssl()
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.consult import create_router
    from app.agent.graph import _make_graph
    from app.services import llm, rag_llm, support_rag, multi_program_rag, grounding_review
    from app.services.consultation_catalog import load_catalog
    from app.services.consultation_sessions import MemorySessions
    catalog = load_catalog()['items'][args.start:args.start+args.limit]
    original_chat, original_rag = llm.chat, rag_llm._request_rag_draft
    original_review=grounding_review.review_draft
    calls, records, states = [], [], []
    def bounded(kind, fn):
        def run(*a, **kw):
            if len(calls) >= args.max_model_calls: raise RuntimeError('Model call budget exhausted')
            calls.append(kind)
            return fn(*a, **kw)
        return run
    graph = _make_graph().compile()
    class Trace:
        def invoke(self, state):
            result = graph.invoke(state); states.append(result); return result
    app = FastAPI(); app.include_router(create_router(Trace(), MemorySessions()))
    client = TestClient(app)
    output = ROOT / args.output; output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        output.write_text(json.dumps(dict(records=records, calls=calls, real_graph=True,
            synthetic_profile=True, semantic_judge_is_not_legal_approval=True,
            updated_at=datetime.now().astimezone().isoformat()), ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    from pydantic import BaseModel, ConfigDict
    class Grade(BaseModel):
        model_config = ConfigDict(extra='forbid')
        claim_index: int
        supported: bool
        reason: str
    class Grades(BaseModel):
        model_config = ConfigDict(extra='forbid')
        claims: list[Grade]
    judge = __import__('openai').OpenAI(timeout=45, max_retries=0)
    judge_model = os.environ.get('CONSULT_EVAL_MODEL') or os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    judged_chat = bounded('semantic_judge', judge.responses.parse)
    try:
        with patch.object(llm,'chat',side_effect=bounded('understanding',original_chat)), \
             patch.object(rag_llm,'_request_rag_draft',side_effect=bounded('rag',original_rag)), \
             patch.object(support_rag,'_request_rag_draft',side_effect=bounded('support_rag',original_rag)), \
             patch.object(multi_program_rag,'_request_rag_draft',side_effect=bounded('multi_rag',original_rag)), \
             patch.object(grounding_review,'review_draft',side_effect=bounded('runtime_grounding_review',original_review)):
            for index, item in enumerate(catalog, args.start+1):
                if len(calls)+4 > args.max_model_calls: break
                sid = client.post('/consult/sessions').json()['session_id']
                question = f"{item['name']}에 대해 한국인 기준 핵심 신청 조건과 준비할 일을 공식 근거로 간단히 알려주세요."
                profile = dict(nationalities=['KR'],date_of_birth='1998-05-15')
                if item['kind']=='program':
                    profile.update(target_country=item['country'],target_visa_type='student' if item['category']=='study' else item['category'])
                started = time.monotonic(); before = len(states)
                response = client.post(f'/consult/sessions/{sid}/messages',json=dict(message=question,profile=profile))
                data = response.json()
                record = dict(target_id=item['id'],kind=item['kind'],country=item['country'],question=question,
                              status=response.status_code,seconds=round(time.monotonic()-started,2),response=data)
                state = states[-1] if len(states)>before else {}
                record['intent']=state.get('intent');record['scope']=state.get('information_scope')
                claims = [dict(text=c['text'],quotes=[x['quote'] for x in c.get('citations',[])])
                          for r in state.get('rag_results',[]) for c in r.get('claims',[])]
                record['claim_evidence']=claims
                record['has_answer_or_explicit_followup']=bool(claims) or bool(data.get('follow_up_questions')) or bool(data.get('rag_statuses'))
                targets = [p['program_id'] for p in data.get('programs',[])] if item['kind']=='program' else [s['support_program_id'] for s in data.get('support_programs',[])]
                record['target_exact'] = targets == [item['id']]
                record['asking'] = data.get('stage')=='asking'
                if claims:
                    try:
                        result=judged_chat(model=judge_model,store=False,max_output_tokens=2200,text_format=Grades,input=[
                            dict(role='system',content=grounding_review.SYSTEM+'\n출력 필드는 claim_index이며 0부터 빠짐없이 각 항목을 채점합니다.'),
                            dict(role='user',content=json.dumps(claims,ensure_ascii=False))])
                        if result.output_parsed is None: raise ValueError('Missing judge output')
                        grades=result.output_parsed.model_dump()['claims']
                        if sorted(g['claim_index'] for g in grades)!=list(range(len(claims))): raise ValueError('Judge coverage mismatch')
                        record['semantic_grades']=grades
                    except Exception as error: record['judge_error']=type(error).__name__
                records.append(record); save()
                failed=sum(not g['supported'] for g in record.get('semantic_grades',[]))
                print(f"{index}/52 {item['id']} HTTP={response.status_code} exact={record['target_exact']} claims={len(claims)} flagged={failed} calls={len(calls)}",flush=True)
    finally:
        save(); judge.close()
    print('Report: '+str(output),flush=True)

if __name__=='__main__': main()

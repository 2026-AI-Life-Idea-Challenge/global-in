"""Run bounded real-model quality tests, without recording video or replaying answers."""
import argparse
from datetime import datetime
import json
import re
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--max-turns', type=int, default=2)
    parser.add_argument('--max-model-calls', type=int, default=8)
    parser.add_argument('--case', choices=['baseline', 'support', 'comparison'], default='baseline')
    parser.add_argument('--output', default='data/processed/quality/consultation/live_result.json')
    args = parser.parse_args()
    if not args.live:
        raise SystemExit('Pass --live to explicitly run paid model calls against the real DB.')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    # Use the system trust store; certificate verification stays enabled.
    import truststore
    truststore.inject_into_ssl()
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.agent.graph import _make_graph
    from app.api.consult import create_router
    from app.services import llm, rag_llm, support_rag, multi_program_rag
    from app.services.consultation_sessions import MemorySessions
    original_chat = llm.chat
    original_rag = rag_llm._request_rag_draft
    calls = []
    def budgeted(kind, function):
        def call(*a, **kw):
            if len(calls) >= args.max_model_calls:
                raise RuntimeError('Quality-test model-call budget reached')
            calls.append(dict(kind=kind, started_at=datetime.now().astimezone().isoformat()))
            print('Model call '+str(len(calls))+': '+kind, flush=True)
            return function(*a, **kw)
        return call
    states = []
    actual = _make_graph().compile()
    class TraceGraph:
        def invoke(self, state):
            result = actual.invoke(state)
            states.append(result)
            return result
    app = FastAPI()
    app.include_router(create_router(TraceGraph(), MemorySessions()))
    client = TestClient(app)
    sid = client.post('/consult/sessions').json()['session_id']
    steps = [
        ('캐나다 워킹홀리데이를 준비하고 싶어요. 제 상황에서 먼저 확인할 조건과 준비 순서를 알려주세요.',
         dict(nationalities=['KR'], date_of_birth='1998-05-15', target_country='canada', target_visa_type='working_holiday')),
        ('해외취업정착지원금도 함께 받을 수 있나요? 지원 내용과 추가로 확인할 조건을 알려주세요.', None),
        ('그 지원금은 지금 신청할 수 있나요? 공식 출처와 확인한 날짜도 알려주세요.', None),
        ('캐나다 워홀과 호주 417 워홀을 비교해 주세요. 제 조건만으로 발급이 확정되는 것은 아니죠?', None),
    ]
    if args.case == 'support':
        steps = [(steps[1][0], steps[0][1]), steps[2]]
    elif args.case == 'comparison':
        steps = [('캐나다 워홀과 호주 417 첫 신청 프로그램을 비교해 주세요. 제 조건만으로 발급이 확정되는 것은 아니죠?', steps[0][1]), ('그럼 호주 워킹홀리데이 417 첫 신청의 준비 서류와 다음에 확인할 일을 알려주세요.', None)]
    report = dict(started_at=datetime.now().astimezone().isoformat(), real_models=True, replayed_answers=False,
                  max_model_calls=args.max_model_calls, turns=[], dataset_embeddings_modified=False)
    destination = ROOT/args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with patch.object(llm, 'chat', side_effect=budgeted('understanding', original_chat)), \
             patch.object(rag_llm, '_request_rag_draft', side_effect=budgeted('program_rag', original_rag)), \
             patch.object(support_rag, '_request_rag_draft', side_effect=budgeted('support_rag', original_rag)), \
             patch.object(multi_program_rag, '_request_rag_draft', side_effect=budgeted('multi_program_rag', original_rag)):
            for question, profile in steps[:args.max_turns]:
                if len(calls) >= args.max_model_calls:
                    report['stopped_at_call_budget'] = True
                    break
                body = dict(message=question)
                if profile:
                    body['profile'] = profile
                started = time.monotonic()
                response = client.post(f'/consult/sessions/{sid}/messages', json=body)
                result = response.json()
                record = dict(question=question, status_code=response.status_code,
                              elapsed_seconds=round(time.monotonic()-started, 2), response=result)
                expected_programs = ({'CA:iec_working_holiday', 'AU:subclass_417_first'} if len(report['turns']) == 0 else {'AU:subclass_417_first'}) if args.case == 'comparison' else None
                record['checks'] = dict(http_ok=response.status_code == 200,
                    expected_program_scope=expected_programs is None or {p['program_id'] for p in result.get('programs', [])} == expected_programs,
                    expected_support_scope=args.case != 'support' or {s['support_program_id'] for s in result.get('support_programs', [])} == {'KR_SUPPORT_SETTLEMENT'},
                    sections_have_sources=all(section.get('citations') for section in result.get('answer_sections', [])),
                    no_positive_final_approval=not bool(re.search(r'발급(?:이)?\s*확정(?:됩니다|입니다|되었|됐)|무조건\s*승인|100%\s*합격', result.get('reply', ''))))
                if response.status_code == 200 and states:
                    record['rag_results'] = states[-1].get('rag_results', [])
                    record['intent'] = states[-1].get('intent')
                    record['scope'] = states[-1].get('information_scope')
                report['turns'].append(record)
                destination.write_text(json.dumps({**report, 'model_calls': calls}, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
                print(json.dumps(dict(turn=len(report['turns']), status_code=response.status_code,
                                     elapsed_seconds=record['elapsed_seconds'], reply=result.get('reply', result.get('detail'))), ensure_ascii=False), flush=True)
                if response.status_code != 200:
                    break
    finally:
        report['model_calls'] = calls
        report['completed_at'] = datetime.now().astimezone().isoformat()
        report['automated_checks_passed'] = bool(report['turns']) and all(all(turn['checks'].values()) for turn in report['turns'])
        report['validation_scope'] = 'transport_target_scope_citation_presence_only_not_semantic_or_legal_approval'
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        print('Report: '+str(destination), flush=True)
    if not report['automated_checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

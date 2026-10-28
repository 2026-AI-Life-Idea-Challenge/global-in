"""Offline semantic and integrity checks; no DB or paid service calls."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from app.models.knowledge import KnowledgeDocument,Requirement,SupportProfile
from app.rules.contracts import validate_expression


def main():
    folder=ROOT/'data/processed/knowledge/20261028'
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    raw=(ROOT/manifest['payload_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==manifest['payload_sha256']
    data=json.loads(raw)
    program_ids={p['program_id'] for p in data['program_profiles']}
    supports={p['support_program_id']:p for p in data['support_profiles']}
    assert len(program_ids)==40 and len(supports)==12
    for path,expected in {**data['inputs'],**manifest['source_files']}.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected
    registry=json.loads((ROOT/'data/processed/legal_review/policy_content_approval_registry_20261028.json').read_text(encoding='utf-8'))
    documents={d['document_id']:d for d in data['documents']}
    assert len(documents)==583
    for d in documents.values():
        KnowledgeDocument.model_validate(d)
        assert hashlib.sha256(d['text'].encode()).hexdigest()==d['content_sha256']
        assert not any(d[k] for k in ('embedding_approved','answer_approved','eligibility_decision_approved'))
        for t in d['targets']:
            assert t['target_id'] in (program_ids if t['target_type']=='PROGRAM' else supports)
    assert {k.removeprefix('POLICY:') for k in documents if k.startswith('POLICY:')}==set(registry['policies'])
    assert sum(d['knowledge_kind']=='reviewer_interpretation' for d in documents.values())==2
    assert len(data['rule_sets'])==52
    assert not data['scope']['full_eligibility_rules_complete'],'Unfinished predicates cannot be marked complete'
    rule_ids={r['requirement_id'] for r in data['requirements']}
    for group in data['rule_sets']:
        assert not group['coverage_complete'] and not group['final_eligibility_approved']
        assert set(group['requirement_ids'])<=rule_ids
    for sid,s in supports.items():
        SupportProfile.model_validate(s)
        assert s['source']['source_url'] in (ROOT/s['source']['capture_file']).read_text(encoding='utf-8')
        assert not s['automatic_eligibility_approved']
        assert s['availability'] in ('UNKNOWN','CLOSED')
        if s['availability']=='CLOSED':
            assert (s['application_end'] and s['application_end']<data['verified_at']) or s['additional_sources']
    links=data['program_support_links']
    assert len({(l['program_id'],l['support_program_id']) for l in links})==len(links)
    for link in links:
        assert link['program_id'] in program_ids and link['support_program_id'] in supports
        assert not link['eligibility_implied']
    pairs={(l['program_id'],l['support_program_id']) for l in links}
    assert {p for p,s in pairs if s=='US_FULBRIGHT_GRADUATE_2027'}=={'US:US-ST-03'}
    for sid in ('KR_US_WEST','KR_US_WEST_LANGUAGE_LOAN'):
        assert {p for p,s in pairs if s==sid}=={'US:US-WEST-01'}
    for r in data['requirements']:
        Requirement.model_validate(r)
        validate_expression(r['expression'])
        assert r['execution_path_complete']
        assert r['judgeability'] in ('manual_check','conditional')
        assert not r['all_requirements_complete']
        assert all(did in documents for did in r['source_document_ids'])
        if r['judgeability']=='manual_check':
            assert r['expression']['resolution_kind'] in ('policy_rule_transcription_pending','full_support_criteria_pending')
    assert not any('topic_pending_review' in d['topics'] for d in data['documents'])
    assert all(item['definition']['deadline'] is None and item['definition']['processing_days'] is None for item in data['preparation_items'])
    print(json.dumps(dict(result='passed',counts=manifest['counts'],availability=dict(Counter(s['availability'] for s in supports.values())),
        structured_condition_count=data['scope']['structured_automatic_rules'],embedding_executed=False),ensure_ascii=False))


if __name__=='__main__':
    main()

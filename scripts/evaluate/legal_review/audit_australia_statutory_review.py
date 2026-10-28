"""Independent coverage, provenance, and approval-gate audit for the AU review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'data/processed/legal_review'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    raw = (OUT/'inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    snapshot = json.loads(raw)
    original = {p['policy_id']:p for p in snapshot['policy_candidates'] if p['policy_id'].startswith('AU_')}
    original_evidence = {e['evidence_id'] for e in snapshot['evidence']}
    review = json.loads((OUT/'australia_statutory_scope_20261028.json').read_text(encoding='utf-8'))
    supplement = json.loads((OUT/'australia_evidence_supplement_20261028.json').read_text(encoding='utf-8'))
    assert review['input_sha256'] == supplement['input_sha256'] == sha(raw)
    assert set(review['policies']) == set(original) and len(original) == 223
    assert len(review['programs']) == 20
    flat = [p for program in review['programs'].values() for p in program['policy_ids']]
    assert len(flat) == len(set(flat)) == 223 and set(flat) == set(original)
    for source in review['sources'].values():
        assert sha((ROOT/source['source_file']).read_bytes()) == source['sha256']
    for evidence in review['evidence'].values():
        source = review['sources'][evidence['source_id']]
        assert evidence['source_file'] == source['source_file']
        assert evidence['source_sha256'] == source['sha256']
        assert len(evidence['normalized_clause_sha256']) == 64
        assert evidence['normalized_clause_characters'] > len(evidence['provision'])+8
    for rule in review['rules'].values():
        assert set(rule['sources']) <= set(review['sources'])
    for pid, row in review['policies'].items():
        assert row['original_policy_text_sha256'] == sha(original[pid]['policy_text'].encode())
        assert row['original_source_evidence_ids'] == original[pid]['source_evidence_ids']
        assert set(row['original_source_evidence_ids']) <= original_evidence
        assert set(row['statutory_evidence_refs']) <= set(review['evidence'])
        assert set(row['scope_rule_ids']) <= set(review['rules'])
        assert set(row['pending_issue_ids']) <= set(review['unresolved_issues'])
        for flag in ['original_text_changed','final_legal_validation_completed','approved_for_user_answers',
                     'approved_for_embedding','approved_for_eligibility_decision','database_applied']:
            assert row[flag] is False, (pid, flag)
    assert len(supplement['policies']) == 4
    for pid, evidence in supplement['policies'].items():
        capture = (ROOT/evidence['source_file']).read_bytes()
        assert sha(capture) == evidence['source_file_sha256']
        assert sha(evidence['source_text'].encode()) == evidence['normalized_section_sha256']
        assert json.loads(capture)['sections'][pid] == evidence['source_text']
        assert review['policies'][pid]['supplemental_evidence_id'] == evidence['evidence_id']
        assert evidence['evidence_id'] not in original_evidence
        assert evidence['original_evidence_replaced'] is False
    result = dict(reviewed_at='2026-10-28', status='passed', input_sha256=sha(raw),
        program_coverage='20/20', policy_coverage='223/223',
        verified_source_hashes=len(review['sources']), provision_references=len(review['evidence']),
        supplemental_sections_verified=4, original_policy_text_changed=False,
        approval_gate_violations=0, ready_for_database_or_embedding=0,
        pending_issue_groups={k:len(v['policies']) for k,v in review['unresolved_issues'].items()},
        limitation='원문·연결·승인 차단 검증이다. 법적 정확성에 대한 독립적인 최종 승인이 아니다.')
    (OUT/'australia_statutory_integrity_20261028.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()

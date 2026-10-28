"""Verify follow-up provenance and occupation rows against downloaded originals."""
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'data/processed/legal_review'


def main():
    review=json.loads((OUT/'australia_public_followup_20261028.json').read_text(encoding='utf-8'))
    index=json.loads((OUT/'australia_occupation_reference_index_20261028.json').read_text(encoding='utf-8'))
    parent=json.loads((OUT/'australia_statutory_scope_20261028.json').read_text(encoding='utf-8'))
    assert review['input_sha256']==index['input_sha256']==parent['input_sha256']
    assert set(review['states'])=={'NSW','VIC','TAS','ACT','NT','QLD','SA','WA'}
    assert len(set(review['linked_policy_ids']))==23
    raw_tables={}
    for sid,value in index['tables'].items():
        source=value['source']
        raw=(ROOT/source['source_file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==source['sha256']
        raw_tables[sid]=BeautifulSoup(raw,'html.parser').find_all('table')
    entries=0
    for code,rows in index['code_index'].items():
        assert len(code)==6 and code.isdigit()
        for row in rows:
            cells=[' '.join(c.get_text(' ',strip=True).split()) for c in raw_tables[row['source_id']][row['table_index']].find_all('tr')[row['row_index']].find_all(['td','th'],recursive=False)]
            assert cells==row['cells'] and code in cells
            assert row['row_sha256']==hashlib.sha256(json.dumps(cells,ensure_ascii=False).encode()).hexdigest()
            assert row['eligibility_approved'] is False
            entries+=1
    for state in review['states'].values():
        assert not state['individual_pathway_eligibility_approved'] and not state['nomination_guaranteed']
        for source in state['source_references']:
            if source['status']=='downloaded':
                assert hashlib.sha256((ROOT/source['source_file']).read_bytes()).hexdigest()==source['sha256']
            else:
                assert 'sha256' not in source
    thapa=review['issue_disposition']['THAPA_PRIMARY_JUDGMENT']
    assert thapa['source']['status']=='download_failed' and '403' in thapa['source']['error']
    corrections=json.loads((OUT/'australia_english_timing_corrections_v1_20261028.json').read_text(encoding='utf-8'))
    assert corrections['input_sha256']==parent['input_sha256'] and len(corrections['policies'])==2
    for pid,row in corrections['policies'].items():
        assert not row['legal_validation_approved'] and not row['database_applied'] and not row['approved_for_embedding']
        assert row['original_policy_text_sha256']==parent['policies'][pid]['original_policy_text_sha256']
        assert all(key in parent['evidence'] for key in row['provision_refs'])
        assert row['source']==parent['sources']['english_482_2025']
    report=dict(status='passed',jurisdictions=8,policy_links=23,occupation_codes=len(index['code_index']),
        index_entries_replayed=entries,primary_judgment_hold_preserved=True,
        bounded_english_correction_drafts_checked=2,
        download_failures_not_misrepresented_as_archived=True,database_changed=False)
    (OUT/'australia_public_followup_integrity_20261028.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()

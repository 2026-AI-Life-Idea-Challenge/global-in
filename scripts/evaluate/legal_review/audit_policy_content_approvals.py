"""Check bounded content approvals against immutable input and release gates."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'data/processed/legal_review'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    raw=(OUT/'inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    snapshot=json.loads(raw)
    original={p['policy_id']:p for p in snapshot['policy_candidates']}
    registry=json.loads((OUT/'policy_content_approval_registry_20261028.json').read_text(encoding='utf-8'))
    assert registry['input_sha256']==sha(raw)
    expected=set(registry['policies'])
    ledger=json.loads((OUT/'global_policy_wording_decisions_20261028.json').read_text(encoding='utf-8'))
    assert ledger['input_sha256']==registry['input_sha256']
    assert ledger['decisions']==registry['review_queue']
    assert set(registry['review_queue'])==set(original) and len(original)==590
    for pid,row in registry['policies'].items():
        assert row['original_policy_text_sha256']==sha((original[pid]['policy_text'] or '').encode())
        assert row['reviewed_policy_text_sha256']==sha(row['reviewed_policy_text'].encode())
        assert row['legal_validation_approved'] and row['approval_status']=='policy_content_review_passed'
        assert all(row['review_checks'].values())
        assert row['scope'] and row['version'] and row['reviewer'] and row['re_review_triggers']
        for ref in row['source_references']:
            assert sha((ROOT/ref['source_file']).read_bytes())==ref['sha256']
        for key in ['approved_for_user_answers','approved_for_embedding','approved_for_eligibility_decision','database_applied','original_policy_replaced','lawyer_signed']:
            assert row[key] is False
        assert not original[pid]['legal_validation_approved']
    for pid,row in ledger['decisions'].items():
        assert row['policy_id']==pid and row['reason']
        assert row['country']==original[pid]['country']
        if pid in expected:
            assert row['legal_validation_approved'] is True
            assert row['approved_text_sha256']==registry['policies'][pid]['reviewed_policy_text_sha256']
        else:
            assert row['legal_validation_approved'] is False
            assert row['decision']=='not_approved' and row['next_action']
    # Substantive release blockers must never disappear under a broad approval.
    assert '현재 납부 명령으로 사용하지 않는다' in registry['policies']['US-WK-01-POL-0008']['reviewed_policy_text']
    for pid in ['AU_189_PT_POL_03', 'AU_190_POL_04', 'AU_491_POL_04']:
        assert '60일 초청 유효기간' in registry['policies'][pid]['reviewed_policy_text']
        assert registry['policies'][pid]['completion_findings']
    english = registry['policies']['AU_462_FIRST_POL_05']
    assert english['completion_findings'] and '6(c)(ii)' in english['reviewed_policy_text']
    assert '885에 관한 것' in english['reviewed_policy_text']
    assert '문언·산술 해석' in registry['policies']['DE_WH_POL_03']['reviewed_policy_text']
    assert '0개는 3,500, 1개는 2,500' in registry['policies']['DE_WH_POL_03']['reviewed_policy_text']
    assert registry['summary']['interpretations_not_agency_rulings'] == ['AU_462_FIRST_POL_05', 'DE_WH_POL_03']
    assert registry['policies']['US-WK-01-POL-0092']['completion_findings']
    assert '공식 USCIS cap-gap 안내' in registry['policies']['US-WK-01-POL-0092']['scope']
    assert '2023-02-01 당일 이후' in registry['policies']['CA_PGWP_POL_06']['reviewed_policy_text']
    assert '2024-05-15 당일 이후' in registry['policies']['CA_PGWP_POL_06']['reviewed_policy_text']
    assert '2025-03-11' in registry['policies']['CA_PGWP_POL_03']['reviewed_policy_text']
    historical = [r for r in ledger['decisions'].values() if r.get('lifecycle_disposition') == 'historical_notice_excluded']
    assert len(historical) == 20 and all(not r['legal_validation_approved'] for r in historical)
    for pid in expected:
        if original[pid]['country']=='canada':
            assert original[pid]['policy_text'] is None
            assert registry['policies'][pid]['original_policy_text_was_null'] is True
            assert registry['policies'][pid]['reviewed_policy_text'].strip()
    assert '점수 증거를 제공한 날' in registry['policies']['AU_482_CORE_POL_13']['reviewed_policy_text']
    assert 'section 7 경과 경로' in registry['policies']['AU_482_CORE_POL_13']['reviewed_policy_text']
    assert '995 주기준 Division995.2' in registry['policies']['AU_500_POL_06']['reviewed_policy_text']
    # Japanese approval preserves documentary scope; no scalar-country promotion.
    uj=json.loads((OUT/'us_jp_policy_review_20261028.json').read_text(encoding='utf-8'))
    for pid,source in uj['policies']['japan'].items():
        detail=source.get('detailed_scope_review',{})
        pdf=detail.get('official_pdf_row')
        if not pdf:
            continue
        row=registry['policies'][pid]
        body=json.loads(row['reviewed_policy_text'])
        assert body['official_pdf_row']==pdf
        for key,value in detail['application_scope'].items():
            assert body['application_scope'][key]==value
        if 'nationality_column_scalar_status_unsafe' in detail.get('issue_codes',[]):
            assert body['application_scope']['requirement_status']=='varies_by_nationality_column'
            assert body['application_scope']['nationality_reference']['other_country_code_mappings_verified'] is False
    assert '만 16세' in registry['policies']['AU_491_POL_11']['reviewed_policy_text']
    assert 'Philippines' in registry['policies']['AU_462_FIRST_POL_01']['reviewed_policy_text']
    progress=json.loads((ROOT/'docs/legal_review/progress_20261028.json').read_text(encoding='utf-8'))
    count=len(expected)
    percent=round(count/590*100,2)
    assert progress['final_legal_validation_completed']==count and progress['final_legal_validation_percent']==percent
    assert sum(registry['summary']['queue_counts'].values())==590
    for pid in expected:
        assert registry['review_queue'][pid]['status']=='approved_bounded_content_version'
    assert registry['summary']['policy_content_versions_approved']==count
    assert registry['summary']['policy_content_not_approved']==590-count
    for country,row in registry['summary']['countries'].items():
        assert row['total']==sum(p['country']==country for p in original.values())
        assert row['approved']==sum(original[pid]['country']==country for pid in expected)
        assert row['not_approved']==row['total']-row['approved']
    result=dict(status='passed',approved_content_versions=count,total_policies=590,
        not_approved=590-count,decisions_recorded=590,
        percentage=percent,source_hashes_verified=True,original_snapshot_unchanged=True,
        service_release_approvals=0,lawyer_signatures=0,database_changed=False,
        meaning='Bounded policy wording/version review; no individual visa eligibility or government approval.')
    (OUT/'policy_content_approval_integrity_20261028.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    main()

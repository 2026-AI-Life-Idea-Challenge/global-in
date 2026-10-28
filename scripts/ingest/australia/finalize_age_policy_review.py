"""Finalize six bounded policy-content versions; never approve a person's visa."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'data/processed/legal_review'
TARGET=OUT/'australia_age_content_approvals_20261028.json'
MASTER=OUT/'policy_content_approval_registry_20261028.json'
IDS_417=['AU_417_FIRST_POL_02','AU_417_SECOND_POL_05','AU_417_THIRD_POL_05']
IDS_462=['AU_462_FIRST_POL_02','AU_462_SECOND_POL_05','AU_462_THIRD_POL_05']
ALIASES={'Cyprus':'Republic of Cyprus','Ireland':'Republic of Ireland',
    'Hong Kong Special Administrative Region of the People’s Republic of China':"Hong Kong Special Administrative Region of the People's Republic of China"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def norm(value):
    return ' '.join(value.split())


def update_progress(registry):
    if MASTER.exists():
        active=json.loads(MASTER.read_text(encoding='utf-8'))
        assert active['input_sha256']==registry['input_sha256']
        registry=active
    path=ROOT/'docs/legal_review/progress_20261028.json'
    progress=json.loads(path.read_text(encoding='utf-8'))
    count=registry['summary']['policy_content_versions_approved']
    stage=('global_wording_batch_decided_with_explicit_holds' if registry['summary'].get('batch_decisions_recorded')==590
           else 'partial_policy_content_final_review_completed_service_release_pending')
    progress.update(stage=stage,
        final_legal_validation_completed=count,final_legal_validation_percent=round(count/590*100,2),
        final_legal_validation_definition='bounded policy-content version review by Codex; not lawyer sign-off, government approval, or individual eligibility approval',
        final_legal_validation_registry=MASTER.relative_to(ROOT).as_posix(),database_changed=False,
        policy_content_approval=registry['summary'])
    path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main(check=False):
    raw=(OUT/'inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    snapshot=json.loads(raw)
    policies={p['policy_id']:p for p in snapshot['policy_candidates']}
    parent=json.loads((OUT/'australia_statutory_scope_20261028.json').read_text(encoding='utf-8'))
    assert parent['input_sha256']==sha(raw) and len(policies)==590
    sources=parent['sources']
    for sid in ['regulations_volume1','regulations_volume2','regulations_volume3','wh_age_reform_2026','wh_417_arrangements','wh_462_arrangements']:
        assert sha((ROOT/sources[sid]['source_file']).read_bytes())==sources[sid]['sha256']
    def country_rows(sid):
        soup=BeautifulSoup((ROOT/sources[sid]['source_file']).read_bytes(),'html.parser')
        rows=[]
        for row in soup.find_all('tr'):
            cells=[norm(c.get_text(' ',strip=True)) for c in row.find_all(['td','th'],recursive=False)]
            if len(cells)==4 and cells[0].isdigit():
                rows.append(cells)
        return rows
    rows417=country_rows('wh_417_arrangements')
    rows462=country_rows('wh_462_arrangements')
    assert len(rows417)==19 and len(rows462)==31
    assert all(c[3]=='30' for c in rows462)
    ages={row[1]:(30 if row[3]=='30' else 35) for row in rows417}
    assert ages==parent['passport_age_matrix_417']
    commencement=norm(BeautifulSoup((ROOT/sources['wh_age_reform_2026']['source_file']).read_bytes(),'html.parser').get_text(' ',strip=True))
    assert 'The whole of this instrument 1 July 2026' in commencement
    for pid in IDS_417:
        local={}
        for line in policies[pid]['policy_text'].splitlines():
            match=re.match(r'^(.+?)\s+[–-]\s+18 to (30|35) years',line.strip())
            if match:
                name=match[1]
                if name.startswith('The United Kingdom'):
                    name='United Kingdom'
                elif name.startswith('Taiwan'):
                    name='Taiwan'
                local[name]=int(match[2])
        expected={ALIASES.get(k,k):v for k,v in ages.items()}
        assert local==expected,(pid,local,expected)
    for pid in IDS_462:
        assert '18 to 30 years old (inclusive) when you apply' in policies[pid]['policy_text']
    # Explicit adverse boundary examples: neither 65 points nor age alone is a grant.
    cases=[('Republic of Korea',17,False),('Republic of Korea',18,True),
           ('Republic of Korea',35,True),('Republic of Korea',36,False),
           ('Japan',30,True),('Japan',31,False),('United Kingdom',35,True),('United Kingdom',36,False)]
    for country,age,expected in cases:
        assert (18<=age<=ages[country]) is expected
    approved={}
    for pid in IDS_417+IDS_462:
        assert not parent['policies'][pid]['pending_issue_ids']
        is417=pid in IDS_417
        age_text=('여권국별 상한은 다음과 같다: '+ '; '.join(k+': '+str(v)+'세' for k,v in ages.items())) if is417 else '열거된 적격 여권국의 연령 상한은 모두 만 30세다.'
        text='2026-07-01 이후 신청하는 subclass '+('417' if is417 else '462')+'의 연령 조건: 신청 접수 시 만 18세 이상이며 해당 여권국 상한 이하여야 한다. '+age_text+' 해당 상한의 다음 생일(31세 또는 36세) 이전에 신청해야 한다. 연령을 충족해 접수했다면 결정 전에 다음 생일이 지나도 그 사실만으로 접수 당시 연령 조건을 잃지는 않는다. 접수 날짜는 공식 안내의 AEST/AEDST를 기준으로 확인한다. 적격 여권·이전 비자·지정 근무 및 나머지 비자 요건은 별도로 충족해야 하며 이 기록은 연령 조건만 검증한다. 시행 전 신청은 당시 규정을 별도 확인한다.'
        source_ids=['regulations_volume1','regulations_volume3','wh_age_reform_2026','wh_417_arrangements' if is417 else 'wh_462_arrangements']
        approved[pid]=dict(policy_id=pid,version='age-scope-v1-20261028',reviewed_policy_text=text,
            reviewed_policy_text_sha256=sha(text.encode()),original_policy_text_sha256=sha(policies[pid]['policy_text'].encode()),
            approval_status='policy_content_review_passed',legal_validation_approved=True,
            scope='general published age condition only; applications on or after 2026-07-01; reviewed as of 2026-10-28',
            reviewer='Codex: source-backed policy-content review; no independent lawyer signature',lawyer_signed=False,
            source_references=[sources[s] for s in source_ids],
            parent_scope_evidence=parent['policies'][pid]['statutory_evidence_refs'],
            review_checks=dict(authority=True,current_version_checked=True,commencement=True,
                country_specific_limits=True,transition_and_separate_requirements=True,
                original_country_age_table_compared=True,boundary_examples=True),
            not_approved_for=['individual_eligibility_decision','automatic_visa_grant','unbounded_historical_cases'],
            approved_for_user_answers=False,approved_for_embedding=False,approved_for_eligibility_decision=False,
            database_applied=False,original_policy_replaced=False,
            re_review_triggers=['age or passport instrument amendment','different application period','source or wording changes'])
    queue={}
    for pid in policies:
        if pid in approved:
            status='approved_bounded_content_version'
        elif pid in parent['policies']:
            blockers=set(parent['policies'][pid]['pending_issue_ids']) & {'THAPA_PRIMARY_JUDGMENT','GUIDANCE_LAW_TIMING'}
            status='specific_textual_issue_requires_resolution' if blockers else 'policy_content_review_pending_context_checks_retained'
        else:
            status='other_country_final_content_review_pending'
        context=parent['policies'].get(pid,{}).get('pending_issue_ids',[])
        queue[pid]=dict(status=status,approved_version=approved.get(pid,{}).get('version'),
            context_issue_ids=context,content_blocker_ids=[k for k in context if k in {'THAPA_PRIMARY_JUDGMENT','GUIDANCE_LAW_TIMING'}],
            context_definition='Context checks remain visible. A real applicant file or employer agreement is required for a dependent individualized claim, not automatically for validation of a general conditional policy statement.')
    counts={key:sum(r['status']==key for r in queue.values()) for key in sorted({r['status'] for r in queue.values()})}
    registry=dict(reviewed_at='2026-10-28',input_sha256=sha(raw),policies=approved,review_queue=queue,
        definition='Final for the explicitly bounded data wording/version, not a legal-practitioner certification or government/individual eligibility decision. Original snapshot and DB approval flags remain unchanged.',
        criteria=['정책 문구·버전·주장을 고정','공식 1차 근거·해시 확보','기준일·시행일 확인','예외·경과·적용 범위 확인','미해소 쟁점 없음 확인','판정자·재검토 조건·근거·변경 전후 해시 기록'],
        summary=dict(policy_total=590,policy_content_versions_approved=6,final_legal_validation_percent=round(6/590*100,2),
            australia_policy_total=223,australia_content_approval_percent=round(6/223*100,2),
            queue_counts=counts,lawyer_signed=0,service_release_approved=0,database_changed=False,embedding_run=False))
    if check:
        assert json.loads(TARGET.read_text(encoding='utf-8'))==registry
    else:
        TARGET.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if not MASTER.exists():
            MASTER.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        update_progress(registry)
    print(json.dumps(registry['summary']))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    main(check=parser.parse_args().check)

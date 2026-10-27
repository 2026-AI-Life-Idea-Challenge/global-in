"""Review F-1 clauses and exceptions against archived official provisions.

This records substantive checks without granting final legal or DB approval.
"""
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[5]
TARGET = ROOT / 'data/processed/legal_review/f1_statutory_review_20261028.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def attach_f1_review(result):
    if not TARGET.exists():
        return
    review = json.loads(TARGET.read_text(encoding='utf-8'))
    assert review['input_sha256'] == result['input_sha256']
    for pid, record in review['policies'].items():
        result['policies']['usa'][pid]['statutory_review'] = record
    result['f1_statutory_review_summary'] = review['summary']


def main():
    snapshot_raw = (ROOT/'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    snapshot = json.loads(snapshot_raw)
    policies = {p['policy_id']:p for p in snapshot['policy_candidates'] if p['program_id']=='US:US-ST-01'}
    assert len(policies)==7
    manifest = json.loads((ROOT/'data/raw/legal_review/20261028/fetch_manifest.json').read_text(encoding='utf-8-sig'))
    sources = {r['source_url']:r for r in manifest}

    def clause(section, paragraph):
        url=next(url for url in sources if 'ecfr.gov' in url and url.endswith('/section-'+section))
        ref=sources[url]
        assert ref['status']=='downloaded'
        raw=(ROOT/ref['source_file']).read_bytes()
        assert sha(raw)==ref['sha256']
        soup=BeautifulSoup(raw,'html.parser')
        node=soup.find(id='p-'+section+paragraph)
        assert node is not None, paragraph
        text=' '.join(node.get_text(' ',strip=True).split())
        return dict(source_url=url, source_file=ref['source_file'], source_sha256=ref['sha256'],
                    provision=section+paragraph, normalized_paragraph_sha256=sha(text.encode()),
                    text=text, legal_force_and_litigation_approval=False)

    i20=clause('214.2','(f)(1)(i)(A)')
    dependents=clause('214.2','(f)(3)')
    entry=clause('214.2','(f)(5)(i)')
    admission=clause('214.2','(f)(1)(ii)')
    fee_first=clause('214.13','(d)(1)')
    fee_dependents=clause('214.13','(b)(2)')
    fee_repeat=clause('214.13','(e)')
    fee_change=clause('214.13','(d)(3)')
    assert 'before issuance of the visa' in fee_first['text']
    assert 'not required to pay a separate fee' in fee_dependents['text']
    assert '30 days before' in entry['text']
    assert 'individually present' in dependents['text']
    dos_url='https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html'
    dos=dict(source_url=dos_url, method='official web tool page read on 2026-10-28',
             automated_download_status=sources[dos_url]['status'],
             archived_response_available=False,
             observation='국무부 안내는 신규 학생의 비자 발급 최대 365일 전과 입국 최대 30일 전을 구분한다. 계속 재학 중인 학생은 SEVP 학교·SEVIS 등록 조건 아래 수업 시작 전 입국을 별도로 안내한다.')
    definitions={
        '001': ([i20], ['학교의 F-1 인증과 해당 과정의 허용 범위를 확인한다. 학교 검색 지도는 탐색 도구이며 개별 입학·비자·입국 승인 자체가 아니다.'], ['program_specific_school_certification_and_admission_requirements']),
        '002': ([i20], ['F-1 입국 자료는 본인 명의의 SEVP 인증 학교 I-20가 필요하다. 입학과 DSO 발행, 비자 발급, 입국 심사를 구분한다.'], ['funding_full_course_intent_and_other_admissibility_conditions']),
        '003': ([dependents], ['적격 배우자·미성년 자녀는 각자 명의의 I-20를 제시한다. 동반과 추후 합류 조건을 구분한다.', 'F-1과 M-1의 학교·과정 유형, 본인·학교 관계자 서명 및 미성년자의 서명 안내는 서로 다른 조건으로 보존한다.'], ['minor_signature_form_instructions_and_m1_cross_category_review']),
        '004': ([fee_first,fee_dependents,fee_repeat,fee_change], ['해외 최초 학생비자 신청자는 비자 발급 전에 SEVIS 수수료를 납부해야 한다. 비자 면제 입국과 미국 내 신분변경은 각 절차의 납부 시점을 따로 적용한다.', 'F-2·M-2 동반가족의 별도 수수료 면제와 연장·전학·학위 단계 변경·실습·계속 재학·거절 후 재신청 등 재납부 예외를 구분한다. I-20를 새로 받았다는 사실만으로 재납부를 일률 요구하지 않는다.'], ['case_specific_new_fee_triggers_and_effective_rule_check']),
        '005': ([entry], ['신규 학생의 비자 발급 가능 시점과 입국 가능 시점을 구분한다. 계속 재학 중인 학생에게 신규 학생의 30일 전 제한을 일률 적용하지 않는다.'], ['student_admission_rule_litigation_and_initial_vs_continuing_case']),
        '006': ([admission,entry], ['입국 시 I-20 제시를 확인하고 원문의 끝 or 추출 흔적을 제거한 검토본을 사용한다. 신규·계속 학생 구분 없이 모든 입국을 30일 전으로 제한하지 않는다.'], ['student_admission_rule_litigation_and_reentry_conditions']),
        '007': ([i20,fee_change], ['미국 내 F-1 신분변경에는 I-20 및 해당 수수료 절차를 확인한다. I-20 발행은 신분변경 승인이나 즉시 학업 개시 허가 자체가 아니다.'], ['8_cfr_248_eligibility_exclusions_and_timing']),
    }
    records={}
    for suffix,(references,findings,remaining) in definitions.items():
        pid='US-F1-POL-'+suffix
        records[pid]=dict(policy_id=pid, reviewed_at='2026-10-28',
                          review_stage='statutory_clause_and_exception_review_recorded',
                          original_policy_text_sha256=sha(policies[pid]['policy_text'].encode()),
                          provisions=references, findings=findings,
                          dos_observation=dos if suffix in ('003','005','006') else None,
                          text_kind='reviewer_summary_not_source_quote', remaining_review=remaining,
                          legal_validation_completed=False, legal_validation_approved=False,
                          approved_for_user_answers=False, approved_for_embedding=False,
                          approved_for_eligibility_decision=False, database_applied=False)
    court_check=dict(reviewed_at='2026-10-28', covered_policy_count=8,
                     method='public official-site searches; not a complete court docket audit',
                     queries=['site.ca1.uscourts.gov "26-1699"', 'site.govinfo.gov "Global Nurse Force" "October 2026"', 'site.supremecourt.gov "Global Nurse Force"'],
                     later_order_absence_proven=False, complete_docket_accessed=False,
                     superseding_orders_excluded=False, priority_holds_remaining=8,
                     finding='검색 결과만으로 후속 명령 부재를 증명할 수 없다. 기존 3개 명령의 검토와 우선 보류 8개를 유지한다.')
    summary=dict(reviewed_at='2026-10-28', program='F-1', statutory_review_recorded=7,
                 program_policy_total=7, recording_percent=100,
                 final_legal_validation_completed=0, database_changed=False)
    result=dict(input_sha256=sha(snapshot_raw), summary=summary, policies=records,
                court_followup_search=court_check,
                rule_enforcement_note='eCFR의 조문 수록과 해당 조문의 현행 집행·소송 상태 확인은 별개다. 고정 체류기간 조문의 현행 집행을 승인하지 않았다.')
    write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write(TARGET,result)
    canonical_path=ROOT/'data/processed/legal_review/us_jp_policy_review_20261028.json'
    canonical=json.loads(canonical_path.read_text(encoding='utf-8'))
    attach_f1_review(canonical)
    write(canonical_path,canonical)
    progress_path=ROOT/'docs/legal_review/progress_20261028.json'
    progress=json.loads(progress_path.read_text(encoding='utf-8'))
    progress['f1_statutory_review']=summary
    progress['git_checkpoint_before_statutory_review']='ff5177d'
    write(progress_path,progress)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

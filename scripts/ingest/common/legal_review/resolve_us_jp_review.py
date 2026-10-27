"""Versioned review corrections and evidence re-extraction; never a DB approval."""
import hashlib
import json
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / 'data/processed/legal_review/us_jp_resolution_v1_20261028.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def norm(text):
    return ' '.join(text.split())


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def attach_resolution(result):
    """Called by the canonical audit generator; preserve its historical checks."""
    if not PACKAGE.exists():
        return
    package = json.loads(PACKAGE.read_text(encoding='utf-8'))
    assert package['input_sha256'] == result['input_sha256']
    for group in result['policies'].values():
        for pid, row in group.items():
            if pid in package['policy_resolutions']:
                row['followup_resolution'] = package['policy_resolutions'][pid]
    result['followup_resolution_summary'] = package['summary']


def update_progress():
    if not PACKAGE.exists():
        return
    package = json.loads(PACKAGE.read_text(encoding='utf-8'))
    path = ROOT / 'docs/legal_review/progress_20261028.json'
    progress = json.loads(path.read_text(encoding='utf-8'))
    progress['stage'] = 'review_corrections_versioned_and_evidence_reextracted_final_law_pending'
    progress['us_jp_followup_resolution'] = package['summary']
    progress['us_jp_detailed_scope_review']['original_broad_evidence_reextraction_pending'] = 0
    progress['us_jp_detailed_scope_review']['priority_authority_holds'] = 8
    progress['final_legal_validation_completed'] = 0
    progress['final_legal_validation_percent'] = 0
    progress['database_changed'] = False
    write(path, progress)


US_TEXT = {
    'US-WK-01-POL-EMP-003': [
        '관련 비생산 기간 기준을 전제로, H-1B 근로자가 실제로 근무 가능 상태가 되거나 고용주의 지휘 아래 배정 대기·교육 등을 시작한 날부터 필요한 임금 지급 의무가 발생한다.',
        '아직 고용을 시작하지 않았어도 LCA 인증 및 청원 승인을 받은 고용주는 해당 청원에 따른 최초 입국 30일 후, 또는 청원 승인 당시 미국에 있던 근로자가 해당 고용주를 위해 일할 자격을 얻은 날부터 60일 후에는 임금을 지급해야 한다. 이 기간은 더 일찍 고용을 시작한 근로자에 대한 무급 유예가 아니다.',
    ],
    'US-J1-INTERN-POL-001': ['인턴은 미국 밖 학위·자격증 수여 고등교육기관의 전일제 재학생이거나, 해당 기관 졸업 후 교류 프로그램 시작일까지 12개월이 지나지 않은 외국인이어야 한다. 스폰서가 이를 확인한다.'],
    'US-J1-INTERN-POL-005': ['스폰서는 성공적인 종전 참가 이력이 없는 호스트 중 직원 수가 25명 미만이거나 연매출이 300만 달러 미만인 곳을 현장 방문해야 한다. 학술기관 및 연방·주·지방 정부기관 배치는 이 방문 요건에서 제외된다.'],
    'US-J1-TRAINEE-POL-008': ['스폰서는 성공적인 종전 참가 이력이 없는 호스트 중 직원 수가 25명 미만이거나 연매출이 300만 달러 미만인 곳을 현장 방문해야 한다. 학술기관 및 연방·주·지방 정부기관 배치는 이 방문 요건에서 제외된다.'],
    'US-J1-INTERN-POL-008': ['6개월 이하의 훈련·인턴십은 최소 종료 평가가 필요하다. 6개월 초과는 최소 중간·종료 평가가 필요하다. 평가를 종료 전에 완료하고 참가자·직속 감독자가 서명하며 스폰서는 프로그램 종료 후 최소 3년간 보존한다.'],
    'US-J1-TRAINEE-POL-011': ['6개월 이하의 훈련·인턴십은 최소 종료 평가가 필요하다. 6개월 초과는 최소 중간·종료 평가가 필요하다. 평가를 종료 전에 완료하고 참가자·직속 감독자가 서명하며 스폰서는 프로그램 종료 후 최소 3년간 보존한다.'],
    'US-J1-COLLEGE-POL-001': [
        'J-1 대학생 선정에는 22 CFR 62.23(c)의 정부·국제기구 재원, 정부·교육기관 간 협정, 개인·가족 외의 상당한 재원, 또는 규정상 학생 인턴 등의 경로 중 적용 경로를 확인한다.',
        '비학위 과정의 전일제 학업 및 최대 24개월 조건은 선정 재원·협정 요건과 별도다. 비학위 등록만으로 선정 기준을 충족하는 새 경로를 만들지 않는다.',
    ],
    'US-SWT-POL-009': [
        'VWP 국적 참가자의 사전 고용 없는 입국에 관한 구직·재정 지원 조건은 해당 참가자 범위로 구분한다. 이 조건이 비자면제 입국으로 SWT 취업을 허용한다는 뜻은 아니다.',
        '스폰서는 모든 SWT 참가자의 임금에 대해 적용 연방·주·지방 최저임금과 유사한 미국인 근로자의 임금·혜택 기준 중 필요한 높은 수준을 확인하고, 최소 월별 개인 연락을 문서화하며 건강·안전·복지 문제에 대응해야 한다.',
    ],
    'US-WK-01-POL-0092': [
        '연구기관 등에 대한 H-1B cap 면제는 해당 기관 정의와 개별 고용·업무 요건에 따라 판단하며 F-1 cap-gap과 구분한다.',
        '적격 F-1의 H-1B 신분변경 청원에 따른 cap-gap 체류 연장과 해당되는 기존 취업허가 연장은 8 CFR 214.2(f)(5)(vii)의 요건·종료 사유에 따라 별도로 판단한다.',
    ],
}


def main():
    raw = (ROOT / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    snapshot = json.loads(raw)
    policies = {p['policy_id']: p for p in snapshot['policy_candidates']}
    evidence = {e['evidence_id']: e for e in snapshot['evidence']}
    canonical_path = ROOT / 'data/processed/legal_review/us_jp_policy_review_20261028.json'
    base = json.loads(canonical_path.read_text(encoding='utf-8'))
    assert digest(raw) == base['input_sha256']
    rows = {k:v for group in base['policies'].values() for k,v in group.items()}
    candidate_data = json.loads((ROOT / 'data/processed/legal_review/us_jp_scope_correction_candidates_20261028.json').read_text(encoding='utf-8'))
    assert candidate_data['input_sha256'] == digest(raw)
    manifest = json.loads((ROOT / 'data/raw/legal_review/20261028/fetch_manifest.json').read_text(encoding='utf-8-sig'))
    sources = {r['source_url']:r for r in manifest if r['status']=='downloaded'}

    def source(url):
        r = sources[url]
        content = (ROOT / r['source_file']).read_bytes()
        assert digest(content) == r['sha256']
        return r, content

    student_url = 'https://www.moj.go.jp/isa/applications/status/student.html'
    nationality_url = 'https://www.moj.go.jp/isa/content/001363332.pdf'
    page_ref, page_raw = source(student_url)
    page = BeautifulSoup(page_raw, 'html.parser')
    assert page.find('a', href='/isa/content/001363332.pdf')
    nation_ref, nation_raw = source(nationality_url)
    with pymupdf.open(stream=nation_raw, filetype='pdf') as doc:
        nation_text = '\n'.join(p.get_text(sort=True) for p in doc)
    assert '韓国' in nation_text and '以外' in nation_text
    nation_review = dict(source_url=nationality_url, source_file=nation_ref['source_file'], source_sha256=nation_ref['sha256'],
                         linked_from=student_url, linking_page_sha256=page_ref['sha256'],
                         verified_member_mapping={'KOR':'listed_countries'},
                         other_country_code_mappings_verified=False,
                         finding='원문은 열거된 국가 이외를 신중심사 대상으로 지정한다. 한국은 열거된 국가에 포함된다. 전체 국가의 ISO 코드 자동 매핑은 승인하지 않았다.')
    resolutions = {}
    corrected = []
    for candidate in candidate_data['candidates']:
        if candidate['action'] != 'versioned_correction_candidate':
            continue
        pid = candidate['policy_id']
        review = rows[pid]['detailed_scope_review']
        version = dict(version='review-v1-20261028', status='correction_text_and_scope_fixed_in_review_package',
                       original_policy_text_sha256=digest(policies[pid]['policy_text'].encode()),
                       resolved_review_issue_codes=candidate['issue_codes'],
                       source_urls=candidate['source_urls'],
                       legal_validation_approved=False, approved_for_user_answers=False,
                       approved_for_embedding=False, approved_for_eligibility_decision=False,
                       automatic_eligibility_rules_enabled=False, database_applied=False,
                       remaining_review=['full_statutory_exceptions_and_final_approval', 'versioned_import_not_applied'])
        if pid.startswith('JP-'):
            scope = review['application_scope']
            version['corrected_scope'] = {k:scope[k] for k in ('application_type', 'school_category', 'school_classification', 'observed_requirement_symbols')}
            version['official_pdf_row'] = review['official_pdf_row']
            version['reviewer_text'] = review['findings']
            if 'nationality_column_scalar_status_unsafe' in candidate['issue_codes']:
                version['corrected_scope'].update(requirement_status='varies_by_nationality_column', nationality_reference=nation_review)
                version['remaining_review'].append('non_KOR_country_code_mapping_not_approved')
            if 'source_condition_missing_in_structured_record' in candidate['issue_codes']:
                version['corrected_scope']['condition_original_ja'] = scope['source_condition_ja']
                assert scope['source_condition_ja']=='中学校又は小学校に入学する場合'
            if 'renewal_row_group_condition_requires_preservation' in candidate['issue_codes']:
                version['corrected_scope']['row_group_condition_original_ja'] = scope['row_group_condition_ja']
                version['corrected_scope']['condition_logic'] = 'language_activity_change_note' if scope['source_row']==12 else 'first_renewal_after_change_to_category_3_or_4_employer'
                if scope['source_row']==13:
                    version['corrected_scope']['category_3_document_excluded_by_group_note'] = True
        elif pid=='US-F1-POL-006':
            version['corrected_policy_text'] = candidate['proposal']['clean_clause_candidate']
            version['text_kind'] = 'edited_clause_not_verbatim_source_quote'
        else:
            version['corrected_review_components'] = US_TEXT[pid]
            version['text_kind'] = 'reviewer_summary_not_source_quote'
            ref = review.get('legal_reference_check') or rows[pid].get('normative_clarification')
            version['legal_reference'] = ref
        resolutions[pid] = dict(correction_v1=version)
        corrected.append(pid)
    assert len(corrected)==26

    context_ids = base['six_policy_context_review_ids']
    for pid in context_ids:
        review = rows[pid]['detailed_scope_review']['evidence_context_review']
        ref, html = source(review['source_url'])
        soup = BeautifulSoup(html, 'html.parser')
        heading = next(h for h in soup.find_all('h3') if h.get_text(' ',strip=True) in ('Hosts are required to:', 'Host Organizations are required to:', 'Host employers are required to:'))
        listing = heading.find_next('ul')
        items = [li.get_text(' ',strip=True) for li in listing.find_all('li',recursive=False)]
        assert items
        clause = norm(policies[pid]['policy_text'])
        full = norm(heading.get_text(' ',strip=True)+' '+' '.join(items))
        assert clause in full, pid
        quote = heading.get_text(' ',strip=True)+'\n'+'\n'.join(items)
        originals = [dict(evidence_id=eid, original_quote_sha256=digest(evidence[eid]['exact_quote'].encode())) for eid in policies[pid]['source_evidence_ids']]
        replacement = dict(version='context-r1-20261028', status='reextracted_with_obligation_heading',
                           original_evidence=originals, source_url=ref['source_url'], source_file=ref['source_file'],
                           source_sha256=ref['sha256'], selector_heading=heading.get_text(' ',strip=True),
                           replacement_quote=quote, replacement_quote_sha256=digest(quote.encode()),
                           target_clause_reproduced=True, original_source_quote_overwritten=False,
                           database_applied=False, legal_validation_approved=False)
        resolutions.setdefault(pid,{})['evidence_context_r1']=replacement
    assert len(context_ids)==6

    fee_url='https://www.ecfr.gov/current/title-8/chapter-I/subchapter-B/part-106/section-106.2'
    fee_ref, fee_raw=source(fee_url)
    fee_soup=BeautifulSoup(fee_raw,'html.parser')
    fee_text=norm(fee_soup.find(id='p-106.2(c)(8)').get_text(' ',strip=True))
    assert all(s in fee_text for s in ('50 or more','more than 50 percent','$4,000','September 30, 2027','amended petition'))
    fr_url='https://www.govinfo.gov/content/pkg/FR-2026-08-10/html/2026-16231.htm'
    fr_ref, fr_raw=source(fr_url)
    assert 'September 9, 2026' in fr_raw.decode('utf-8')
    fee_record=dict(status='threshold_exception_and_sunset_confirmed_in_rule_text', source_url=fee_url,
                    source_file=fee_ref['source_file'], source_sha256=fee_ref['sha256'], provision='8 CFR 106.2(c)(8)-(9)',
                    effective_date='2026-09-09', statutory_last_filing_date='2027-09-30',
                    employer_us_headcount_minimum=50, aggregate_h1b_l1_share_strictly_greater_than_percent=50,
                    h1b_fee_usd=4000, l1_fee_usd=4500,
                    amended_petition_without_status_extension_exempt=True,
                    final_rule_source_url=fr_url, final_rule_sha256=fr_ref['sha256'],
                    current_case_specific_payment_decision_approved=False, legal_validation_approved=False,
                    remaining_review=['post_2026_10_23_changes_and_individual_case_application', 'final_approval_not_granted'])
    for pid in ('US-WK-01-POL-0001','US-WK-01-POL-0061'):
        resolutions.setdefault(pid,{})['fee_scope_review']=fee_record

    district_url='https://www.govinfo.gov/content/pkg/USCOURTS-mad-1_25-cv-13829/pdf/USCOURTS-mad-1_25-cv-13829-0.pdf'
    appeal_url='https://www.ca1.uscourts.gov/sites/ca1/files/opnfiles/26-1699O-01A.pdf'
    later_url='https://www.govinfo.gov/content/pkg/USCOURTS-cand-4_25-cv-08454/pdf/USCOURTS-cand-4_25-cv-08454-17.pdf'
    district_ref, district_raw=source(district_url)
    appeal_ref, appeal_raw=source(appeal_url)
    later_ref, later_raw=source(later_url)
    with pymupdf.open(stream=district_raw,filetype='pdf') as doc:
        district_last=norm(doc[-1].get_text())
    with pymupdf.open(stream=appeal_raw,filetype='pdf') as doc:
        appeal_last=norm(doc[-1].get_text())
    assert 'VACATED in its entirety' in district_last
    assert "deny the defendants' motion to stay" in appeal_last
    with pymupdf.open(stream=later_raw,filetype='pdf') as doc:
        later_order=norm(doc[33].get_text())
    assert 'Proclamation No. 11069' in later_order and 'VACATED' in later_order and 'enjoined' in later_order
    court=dict(status='primary_orders_read_current_docket_hold_retained',
               district_order=dict(source_url=district_url, source_file=district_ref['source_file'], sha256=district_ref['sha256'], decision_date='2026-06-08', operative_page=42),
               appellate_order=dict(source_url=appeal_url, source_file=appeal_ref['source_file'], sha256=appeal_ref['sha256'], decision_date='2026-07-24', operative_page=7),
               later_district_order=dict(source_url=later_url, source_file=later_ref['source_file'], sha256=later_ref['sha256'], decision_date='2026-09-30', operative_page=34,
                                         case_number='4:25-cv-08454-HSG', includes_2026_extension_proclamation=True),
               finding='6월 지방법원은 포고령 이행 정책을 무효화했고 7월 항소법원은 집행정지 신청을 기각했다. 9월 30일 Global Nurse Force 명령은 10973 및 연장 포고령 11069의 이행 정책을 무효화·환송하고 APA 의견수렴 및 RFA 분석 전 집행을 금지했다. 9월 30일 이후 명령과 항소·기관 조치의 현행 상태까지 확정한 것은 아니다.',
               current_docket_complete=False, current_payment_obligation_approved=False,
               remaining_review=['post_2026_09_30_orders_in_all_related_cases', 'subsequent_agency_actions_and_final_approval'])
    payment_ids=[c['policy_id'] for c in candidate_data['candidates'] if 'court_order_scope_unresolved' in c['issue_codes']]
    assert len(payment_ids)==8
    for pid in payment_ids:
        resolutions.setdefault(pid,{})['court_order_review']=court

    summary=dict(reviewed_at='2026-10-28', correction_versions_recorded=26, correction_total=26,
                 correction_recording_percent=100, evidence_context_reextracted=6, evidence_context_total=6,
                 evidence_reextraction_percent=100, fee_rule_scope_checked=2, priority_authority_holds_remaining=8,
                 court_order_primary_documents_checked=3, final_legal_validation_completed=0,
                 final_legal_validation_percent=0, database_changed=False)
    package=dict(reviewed_at='2026-10-28', input_sha256=digest(raw),
                 definition='versioned review corrections and replacement evidence; no DB import or final legal approval',
                 nationality_reference=nation_review, summary=summary, policy_resolutions=resolutions)
    write(PACKAGE,package)
    attach_resolution(base)
    write(canonical_path,base)
    write(ROOT/'docs/legal_review/us_jp_resolution_summary_20261028.json',summary)
    update_progress()
    assert (ROOT/'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json').read_bytes()==raw
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

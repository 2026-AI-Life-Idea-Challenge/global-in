"""Dated public-source follow-up and lossless occupation-table routing index."""
import hashlib
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'data/processed/legal_review'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def norm(text):
    return ' '.join(text.split())


STATES = {
 'NSW': dict(sources=['nsw_190','nsw_491','nsw_skills'],
     status_190='selection_and_invitation',status_491='closed_on_published_page',
     note='190은 NSW 직종 unit group·거주 등 요건과 초청 절차를 별도 적용한다. 491 안내는 접수 종료와 기존 신청의 추후 처리 방침을 명시한다. 190 개방을 491 개방으로 전용하지 않는다.'),
 'VIC': dict(sources=['victoria_2026'],status_190='roi_open',status_491='roi_not_accepted_allocation_pending',
     note='2026-27의 190 ROI는 접수 중이다. 491 배정은 미확정이고 ROI를 받지 않는다는 공식 안내를 구분한다. 웹 도구에서 본문을 읽었으나 CLI 보관 요청은 403이므로 원문 해시는 주장하지 않는다.'),
 'TAS': dict(sources=['tasmania_2026'],status_190='2026_27_roi_opening_announced',status_491='2026_27_roi_opening_announced',
     note='2026-27 ROI 개시일 2026-08-17, 배정 190 1,250·491 800을 공식 공지에서 확인했다. 공지의 과거 URL 경로를 프로그램 연도로 오인하지 않는다. 모든 경로의 개별 우선순위 충족은 별도다.'),
 'ACT': dict(sources=['act_190','act_491','act_guidelines'],status_190='matrix_ranked_invitation',status_491='matrix_ranked_invitation',
     note='Canberra Matrix와 거주자/해외 신청자 기준을 분리한다. 지명 기준 충족이 초청 보장은 아니다. 2026-07-27 거주자 지침 링크 및 190/491의 2년 정착 약정을 확인했다. 약정을 비자 자체의 별도 취소 조건으로 단정하지 않는다.'),
 'NT': dict(sources=['nt_status'],status_190='no_new_applications',status_491='restricted_onshore_exceptions',
     note='2026-27 충분한 신청 접수로 190 및 해외 신규 신청은 받지 않는다. 491은 NT Graduate/Resident의 호주 내 신청자 중 지정 비자·연령·점수 기한이 2027-09-30까지 도래하는 예외만 확인한다. 지명을 기한 내 보장하지 않는다.'),
 'QLD': dict(sources=['queensland_skilled','queensland_roi'],status_190='2026_27_opening_not_confirmed',status_491='2026_27_opening_not_confirmed',
     note='ROI 안내는 2025-26 마감 및 후속 배정·개시 공지 대기를 명시한다. 일반 자격 안내 페이지가 있다는 사실만으로 2026-27 접수 개방을 확정하지 않는다.'),
 'SA': dict(sources=['sa_update_2026','sa_skilled'],status_190='cohort_conditions_apply',status_491='cohort_conditions_apply',
     note='2026-10-22 공지는 SA 거주·근무자 중 현재 비자 만료일이 2027-01-31까지인 사람의 ROI 접수를 안내한다. 해외 후보는 ROI 없이 SkillSelect EOI에서 직접 초청한다. 우선 분야 외 고순위도 고려할 수 있으며 비자별·경로별 조건은 별도다.'),
 'WA': dict(sources=['wa_program'],status_190='2026_27_invitation_activity_published',status_491='2026_27_invitation_activity_published',
     note='공식 원문에 2026-27 초청 실적 표가 있다. 예전 2025-26 소제목만 보고 금년도 미운영으로 단정하지 않는다. General/Graduate 및 WASMOL 구분과 고용계약 면제를 별도 적용한다. 직업 면허는 기술심사·지명과 별개다.'),
}


def main():
    parent = json.loads((OUT/'australia_statutory_scope_20261028.json').read_text(encoding='utf-8'))
    rows = json.loads((OUT/'australia_followup_source_manifest_20261028.json').read_text(encoding='utf-8-sig'))
    manifest = {r['source_id']:r for r in rows}
    for row in rows:
        if row['status'] == 'downloaded':
            assert sha((ROOT/row['source_file']).read_bytes()) == row['sha256']
    states = {}
    for state, spec in STATES.items():
        refs = [manifest[k] for k in spec['sources']]
        states[state] = dict(**spec, checked_at='2026-10-28', source_references=refs,
            verification_method='official public web page read; local download status recorded separately',
            individual_pathway_eligibility_approved=False, nomination_guaranteed=False)
    index = {}
    summaries = {}
    tables_out = {}
    for source_id in ['skilled_occupations','occupations_186','occupations_482','occupations_494','mandatory_skills_482']:
        source = parent['sources'][source_id]
        raw = (ROOT/source['source_file']).read_bytes()
        assert sha(raw) == source['sha256']
        soup = BeautifulSoup(raw,'html.parser')
        indexed_rows = 0
        tables = []
        for ti, table in enumerate(soup.find_all('table')):
            table_rows = []
            for ri, row in enumerate(table.find_all('tr')):
                cells = [norm(c.get_text(' ',strip=True)) for c in row.find_all(['td','th'],recursive=False)]
                if not cells:
                    continue
                table_rows.append(cells)
                codes = [c for c in cells if re.fullmatch(r'\d{6}',c)]
                if not codes:
                    continue
                indexed_rows += 1
                for code in codes:
                    index.setdefault(code,[]).append(dict(source_id=source_id,table_index=ti,row_index=ri,
                        cells=cells,row_sha256=sha(json.dumps(cells,ensure_ascii=False).encode()),
                        source_sha256=source['sha256'],eligibility_approved=False))
            if table_rows:
                heading = table.find_previous('p',class_=re.compile('Head'))
                tables.append(dict(table_index=ti,heading=norm(heading.get_text(' ',strip=True)) if heading else None,rows=table_rows))
        assert indexed_rows > 0, source_id
        tables_out[source_id] = dict(source=source,tables=tables)
        summaries[source_id] = dict(indexed_occupation_rows=indexed_rows,table_count=len(tables))
    occupation = dict(reviewed_at='2026-10-28',input_sha256=parent['input_sha256'],
        sources=summaries,tables=tables_out,code_index=index,
        caveats='전체 표의 원래 열과 조건·평가기관·국적 표를 보존한 검색용 색인이다. 동일 코드라도 비자별 목록·직무·제외 조건·시점이 다르며 등재만으로 자격을 승인하지 않는다.',
        individualized_eligibility_approved=False,database_applied=False)
    (OUT/'australia_occupation_reference_index_20261028.json').write_text(json.dumps(occupation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    english_source=parent['sources']['english_482_2025']
    english_raw=(ROOT/english_source['source_file']).read_bytes()
    assert sha(english_raw)==english_source['sha256']
    english_text=norm(BeautifulSoup(english_raw,'html.parser').get_text(' ',strip=True))
    assert 'not more than 3 years before the day on which the applicant provided evidence' in english_text
    assert '3 years immediately before the day on which the relevant visa application was made' in english_text
    timing_text='2025-09-13 이후 신청에 적용되는 LIN 25/082의 경로를 구분한다. 제6조 경로의 시험일 유효기간은 해당 점수의 증거를 제출한 날 전 3년 이하이며, 구성 영역 재응시가 있는 경우 원래 시험일과 재응시일을 구분한다. 재응시일만으로 원래 시험일의 유효기간이 자동 연장되지는 않는다. 시행 전 시험에 제7조를 적용하는 경우에는 해당 신청일 직전 3년 및 해당 표의 점수를 단일 응시에서 취득한 조건을 확인한다. 이 교정본은 유효기간 설명만 다루며 면제·시험별 점수·승인된 시험 방식은 별도 검토 대상이다.'
    corrections={pid:dict(policy_id=pid,version='english-timing-v1-20261028',
        scope='timing clarification only; not a replacement for the complete English requirement',
        reviewer_paraphrase=timing_text,source=english_source,
        provision_refs=['english_482_2025:6','english_482_2025:7','english_482_2025:8'],
        original_policy_text_sha256=parent['policies'][pid]['original_policy_text_sha256'],
        status='correction_prepared_awaiting_complete_policy_content_review',
        legal_validation_approved=False,database_applied=False,approved_for_embedding=False)
        for pid in ['AU_482_CORE_POL_13','AU_482_SPECIALIST_POL_12']}
    (OUT/'australia_english_timing_corrections_v1_20261028.json').write_text(json.dumps(dict(
        input_sha256=parent['input_sha256'],policies=corrections,original_policy_replaced=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    state_ids = [p for p in parent['policies'] if p.startswith(('AU_190_','AU_491_'))]
    assert len(state_ids) == 23
    result = dict(reviewed_at='2026-10-28',input_sha256=parent['input_sha256'],states=states,
        linked_policy_ids=state_ids,
        issue_disposition={
            'STATE_NOMINATION':'8 jurisdictions public-source scope recorded; individual streams and fresh opening checks remain',
            'INDIVIDUAL_OCCUPATION':'5 instruments indexed losslessly with source hashes; individual caveat and facts still conditional',
            'THAPA_PRIMARY_JUDGMENT':dict(status='primary_archive_fetch_403_hold_preserved',source=manifest['thapa_primary_archive']),
            'AGREEMENT_TEXT':'Public generic and DAMA guidance cannot establish a particular employer agreement; agreement text is required only for a claim depending on that concession',
            'ACT_CHARACTER_HISTORY':'General policy content review does not require a real applicant file; case-specific decisions remain separate',
            'GUIDANCE_LAW_TIMING':'Two bounded timing correction drafts prepared; complete English-policy review remains. Unrelated policies are not withheld.'},
        summary=dict(jurisdictions_recorded=8,linked_policies=23,occupation_instruments_indexed=5,
            unique_occupation_codes=len(index),indexed_rows=sum(r['indexed_occupation_rows'] for r in summaries.values()),
            english_timing_correction_drafts=2,
            downloaded_followup_sources=sum(r['status']=='downloaded' for r in rows),
            download_failures=sum(r['status']!='downloaded' for r in rows),final_legal_validation_completed=0,database_changed=False))
    (OUT/'australia_public_followup_20261028.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    progress_path=ROOT/'docs/legal_review/progress_20261028.json'
    progress=json.loads(progress_path.read_text(encoding='utf-8'))
    progress['australia_public_followup']=result['summary']
    progress_path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()

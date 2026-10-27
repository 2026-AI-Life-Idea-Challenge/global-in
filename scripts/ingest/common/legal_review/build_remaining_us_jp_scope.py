"""Build the remaining 300 scope records without approving law or changing DB.

JP: fresh official PDF table cells + visually inspected document headers/notes.
US: explicit reviewer notes keyed by policy ID + checked legal paragraph anchors.
All records are bound to the exact snapshot and policy text.
"""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[4]
import sys
sys.path.insert(0, str(ROOT))
from scripts.ingest.usa.shared.review.us_policy_scope_notes import NOTES
SNAPSHOT = ROOT / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json'
EXPECTED_INPUT_SHA = '043cf9bbb1d00c864d77912dca662e98960f5374766a219c36749bf7d2c69bd8'
OUT = ROOT / 'data/processed/legal_review/us_jp_remaining_scope_20261028.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def compact(text):
    return re.sub(r'\s+', '', text or '')


def symbol(cell):
    return next((ch for ch in cell or '' if ch in '○△－-'), None)


def main():
    raw = SNAPSHOT.read_bytes()
    assert sha(raw) == EXPECTED_INPUT_SHA, 'New snapshot requires a new review'
    data = json.loads(raw)
    manifest = json.loads((ROOT / 'data/raw/legal_review/20261028/fetch_manifest.json').read_text(encoding='utf-8-sig'))
    sources = {r['source_url']: r for r in manifest if r['status'] == 'downloaded'}
    evidence = {e['evidence_id']: e for e in data['evidence']}
    tables = {}
    pdf_audits = []
    policy_pdf_urls = {p['metadata'].get('source_url') for p in data['policy_candidates']
                       if p['country']=='japan' and p['program_id']!='JP:JP-WH-01'}
    for url, source in sources.items():
        if url not in policy_pdf_urls:
            continue
        original = (ROOT / source['source_file']).read_bytes()
        assert sha(original) == source['sha256']
        rows = {}
        page_notes = {}
        with pymupdf.open(stream=original, filetype='pdf') as doc:
            for page_index, page in enumerate(doc):
                for table in page.find_tables().tables:
                    previous_remark = None
                    for cells in table.extract():
                        if not cells[0] or not cells[0].strip().isdigit():
                            if cells[0] and '転職後の初回' in cells[0]:
                                page_notes[page_index + 1] = cells[0]
                            continue
                        number = int(cells[0].strip())
                        inherited = cells[-1] is None and previous_remark is not None
                        remark = previous_remark if inherited else cells[-1]
                        if cells[-1] is not None:
                            previous_remark = cells[-1]
                        assert number not in rows, (url, number)
                        rows[number] = dict(page=page_index + 1, cells=cells,
                                            effective_remark=remark,
                                            remark_inherited_from_merged_cell=inherited)
        tables[url] = dict(rows=rows, page_notes=page_notes, **source)
        pdf_audits.append(dict(source_url=url, source_sha256=source['sha256'],
                              source_file=source['source_file'], table_rows=len(rows),
                              visual_review='header, columns and conditions inspected in rendered official PDF',
                              extraction_method='PyMuPDF table cell extraction; not plain-text column guessing'))

    law_soups = {}
    for url, source in sources.items():
        if 'www.ecfr.gov' in url:
            original = (ROOT / source['source_file']).read_bytes()
            assert sha(original) == source['sha256']
            law_soups[url] = BeautifulSoup(original, 'html.parser')

    records = {}
    for policy in data['policy_candidates']:
        pid = policy['policy_id']
        if policy['country'] not in ('usa', 'japan') or policy['program_id'] == 'JP:JP-WH-01' or pid in ('US-J1-INTERN-POL-008', 'US-J1-TRAINEE-POL-011'):
            continue
        evs = [evidence[ref] for ref in policy['source_evidence_ids']]
        review = dict(reviewed_at='2026-10-28', status='scope_recorded_with_open_legal_checks',
                      policy_text_sha256=sha(policy['policy_text'].encode()),
                      text_kind='reviewer_summary_not_source_quote',
                      source_urls=sorted({e['source_url'] for e in evs}),
                      automatic_eligibility_rule_enabled=False,
                      remaining_review=['final_current_law_and_exception_approval_pending'])
        if policy['country'] == 'japan':
            meta = policy['metadata']
            record = meta['source_record']
            url = meta['source_url']
            pdf = tables[url]
            current = pdf['rows'][record['row_number']]
            cells = current['cells']
            is_student = policy['program_id'] == 'JP:JP-ST-01'
            notes = []
            issues = []
            scope = {key: meta.get(key) for key in ('application_type', 'school_category', 'school_classification')}
            scope.update(source_page=current['page'], source_row=record['row_number'],
                         source_record_id=record.get('document_id'),
                         original_category_requirements=record.get('category_requirements'),
                         original_nationality_columns=record.get('nationality_columns'))
            if is_student:
                observed = {'listed_countries': symbol(cells[2]), 'other_countries': symbol(cells[3])} if len(cells) == 7 else {'all_in_this_table': symbol(cells[2])}
                scope.update(observed_requirement_symbols=observed,
                             source_condition_ja=current['effective_remark'],
                             source_condition_inherited_from_merged_cell=current['remark_inherited_from_merged_cell'])
                if record.get('nationality_columns'):
                    for group, original in record['nationality_columns'].items():
                        assert symbol(original['symbol']) == observed[group], (pid, group)
                    if len(set(observed.values())) > 1:
                        issues.append('nationality_column_scalar_status_unsafe')
                        notes.append('국적 열별 요구가 다르므로 단일 requirement_status를 모든 국적에 사용하지 않는다.')
                        review['remaining_review'].append('listed_nationality_group_membership_requires_official_list')
                else:
                    assert symbol(record.get('requirement_symbol')) == observed['all_in_this_table'], pid
                assert cells[1], pid
                notes.append('COE 신청의 해당 학교 유형·적정교 분류에만 적용하며 변경·갱신 및 다른 학교로 확장하지 않는다.')
                if '△' in observed.values():
                    notes.append('조건부 표시와 비고를 함께 적용한다. 조건부를 공통 필수 또는 무조건 면제로 변환하지 않는다.')
                if record.get('condition_original_ja') is None and current['effective_remark']:
                    issues.append('source_condition_missing_in_structured_record')
                    notes.append('가공본에 빠진 조건을 원문 셀에서 복원해 검토 기록에 보존했다.')
                if record['row_number'] == 2:
                    notes.append('본표와 별지 각종확인서의 제출을 구분한다. 별지의 학교·학력·국적 및 동일 기관 재신청 예외와 추가 자료 요구 가능성을 보존한다.')
                if '日本語能力' in cells[1]:
                    notes.append('언어 증빙은 해당 표의 시험·면접·학력 조건을 확인하며 JLPT 일률 필수로 변환하지 않는다.')
                if '－' in observed.values() or '-' in observed.values():
                    notes.append('대시 표시는 이 표·국적 열의 제출 범위이며 자금·학업 등 실체 요건 전체의 면제가 아니다.')
            else:
                cats = ['3', '4'] if len(cells) == 5 else ['1', '2', '3', '4']
                observed = {cat: symbol(cells[2 + idx]) for idx, cat in enumerate(cats)}
                scope['observed_requirement_symbols'] = observed
                if record['row_number'] == 4:
                    scope['category_evidence_cells_ja'] = dict(zip(cats, cells[2:2+len(cats)]))
                    notes.append('소속 기관 분류를 증명하는 열별 자료다. 셀 안의 항목 글머리 ○와 제출 필요 표시 ○를 혼동하지 않는다. 증명이 없을 때의 카테고리 4 처리도 보존한다.')
                else:
                    for category, item in record['category_requirements'].items():
                        assert symbol(item.get('symbol')) == observed[category], (pid, category)
                notes.append('기술·인문지식·국제업무의 해당 COE·변경·갱신 신청과 소속 기관 카테고리에만 적용한다. 제출서류 목록을 실체 자격 승인으로 바꾸지 않는다.')
                if None in observed.values():
                    notes.append('공란을 모든 법령상 의무의 면제로 해석하지 않으며 다른 카테고리의 필수 표시를 복사하지 않는다.')
                if meta['application_type'] == 'renewal' and record['row_number'] >= 8:
                    scope['row_group_condition_ja'] = pdf['page_notes'][2]
                    issues.append('renewal_row_group_condition_requires_preservation')
                    notes.append('이직 후 카테고리 3·4 기관에서 첫 갱신하는 공통 조건을 보존한다. 13번은 카테고리 3 제외이며 12번의 업무 변경 주석은 별도로 적용한다.')
                body = cells[1]
                if 'いずれか' in body:
                    notes.append('원문의 활동·기관 유형별 선택 자료를 모두 동시에 요구하는 누적 조건으로 변환하지 않는다.')
                if '新規事業' in body:
                    notes.append('신규 사업의 사업계획서 대체 조건을 유지한다.')
                if 'Ｂ２' in body or 'B2' in body:
                    notes.append('주로 언어 능력을 사용하는 대인 업무라는 조건과 갱신 주석을 보존한다. 모든 직종의 일본어 B2 필수로 확대하지 않는다.')
            review.update(method='explicit document visual inspection plus current PDF cell re-extraction and snapshot metadata comparison',
                          actor='applicant_and_accepting_institution', application_scope=scope,
                          official_pdf_row=dict(source_url=url, source_file=pdf['source_file'], source_sha256=pdf['sha256'],
                                                page=current['page'], row=record['row_number'], cells=cells),
                          findings=notes, issue_codes=issues)
            review['remaining_review'].append('substantive_residence_criteria_and_document_specific_exceptions')
        else:
            note = NOTES[pid]
            review.update(method='explicit policy-ID reviewer note after reading policy text; current official sources and legal paragraph anchors distinguished',
                          actor=note['actor'], source_section=note['reference_section'],
                          finding=note['finding'], issue_codes=[note['issue']] if note['issue'] else [])
            anchor = re.match(r'^(8|20|22) CFR (\d+\.\d+)((?:\([^\)]+\))*)', note['reference_section'])
            if anchor:
                title, section, paragraph = anchor.groups()
                candidate = next((url for url in law_soups if f'/title-{title}/' in url and url.endswith('/section-'+section)), None)
                if candidate:
                    node = law_soups[candidate].find(id='p-'+section+paragraph)
                    ref = dict(source_url=candidate, provision=section+paragraph, paragraph_anchor_found=bool(node),
                               source_file=sources[candidate]['source_file'], source_sha256=sources[candidate]['sha256'])
                    if node:
                        paragraph_text = ' '.join(node.get_text(' ', strip=True).split())
                        ref['normalized_paragraph_sha256'] = sha(paragraph_text.encode())
                        if note['issue'] == 'site_visit_and_or_conflict':
                            assert 'fewer than 25 employees or less than three million dollars' in paragraph_text, pid
                        if note['issue'] == 'full_time_condition_missing_in_brochure':
                            assert 'enrolled full-time' in paragraph_text, pid
                    else:
                        review['remaining_review'].append('exact_legal_paragraph_anchor_not_found')
                    review['legal_reference_check'] = ref
                else:
                    review['remaining_review'].append('supplemental_legal_reference_not_archived')
            else:
                review['remaining_review'].append('underlying_legal_or_procedural_reference_still_requires_full_review')
            if policy['program_id'] == 'US:US-WEST-01':
                review.update(temporal_scope='2026_first_half_only', current_recruitment_verified=False)
                review['remaining_review'].append('new_recruitment_notice_required_for_current_application')
            if note['issue']:
                review['remaining_review'].append(note['issue'])
            context_ids = {'US-J1-INTERN-POL-009', 'US-J1-INTERN-POL-010', 'US-J1-INTERN-POL-011',
                           'US-J1-TRAINEE-POL-013', 'US-J1-TRAINEE-POL-014', 'US-SWT-POL-010'}
            if pid in context_ids:
                source_url = evs[0]['source_url']
                archive = sources[source_url]
                original = (ROOT / archive['source_file']).read_bytes()
                assert sha(original) == archive['sha256']
                soup = BeautifulSoup(original, 'html.parser')
                for tag in soup(['script', 'style']):
                    tag.decompose()
                full = ' '.join(soup.get_text(' ', strip=True).split())
                quote = ' '.join(policy['policy_text'].split())
                assert quote in full, pid
                review['evidence_context_review'] = dict(
                    status='policy_clause_and_actor_confirmed_original_broad_excerpt_still_pending',
                    source_url=source_url, source_file=archive['source_file'], source_sha256=archive['sha256'],
                    verified_policy_clause=policy['policy_text'],
                    quote_match_method='exact after whitespace normalization',
                    obligation_actor=note['actor'], legal_reference=note['reference_section'],
                    original_evidence_rewritten=False)
                review['remaining_review'].append('original_broad_evidence_excerpt_requires_reextraction')
        records[pid] = review

    assert len(records) == 300
    result = dict(reviewed_at='2026-10-28', input_sha256=sha(raw),
                  definition='scope observations recorded, including unresolved issues; not final legal approval',
                  counts=dict(Counter('japan' if pid.startswith('JP-') else 'usa' for pid in records)),
                  issue_counts=dict(Counter(issue for r in records.values() for issue in r['issue_codes'])),
                  pdf_document_checks=pdf_audits, records=records,
                  database_applied=False, final_legal_validation_completed=0)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    assert SNAPSHOT.read_bytes() == raw
    print(json.dumps({k:v for k,v in result.items() if k not in ('records', 'pdf_document_checks')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

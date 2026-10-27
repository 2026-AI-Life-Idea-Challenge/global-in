"""Review all US/JP snapshot policies against newly retrieved official archives.

Writes a sidecar so hash-linked Japanese processed originals remain unchanged.
No database updates or eligibility approvals are performed.
"""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf
from bs4 import BeautifulSoup
from legal_scope_clarifications import apply_scope_clarifications
from resolve_us_jp_review import attach_resolution

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'docs/legal_review'
ARCHIVES = ROOT / 'data/raw/legal_review/20261028/fetch_manifest.json'
WEST_ATTACHMENT = 'https://www.niied.go.kr/web/main/file/download/uu/d38331d7144c4042b8069bfbbb7855da'
J1_RULES = {
    'US:US-EM-02': 'https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.22',
    'US:US-EM-03': 'https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.22',
    'US:US-ST-03': 'https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.23',
    'US:US-WH-01': 'https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-B/section-62.32',
}
JP_WEB = {
    'https://www.kr.emb-japan.go.jp/itpr_ko/visa_working_documents.html': '2025-11-04',
    'https://www.kr.emb-japan.go.jp/itpr_ko/visa_working.html': '2026-09-30',
    'https://www.mofa.go.jp/j_info/visit/w_holiday/': '2026-04-01',
}
US_WEB_MANUAL = {
    'https://travel.state.gov/content/travel/en/us-visas/employment/temporary-worker-visas.html',
    'https://travel.state.gov/en/newsroom/visas/2025/restriction-on-entry-of-certain-nonimmigrant-workers.html',
    'https://travel.state.gov/en/newsroom/visas/2025/announcement-of-expanded-screening-and-vetting-for-h-1b-and-dependent-h-4-visa-applicants.html',
}
DOL_LAW = 'https://www.dol.gov/agencies/whd/laws-and-regulations/laws/ina/h1b'
DOL_LAW_MAIN_SHA = '2d635f89b54beac139c25f94e41ad9e785959287a7f7d48fd0119e1c554236f8'
DOL_CLAUSE_SHA = {
    'US-WK-01-POL-0004': '057cd65a52a4eb4863fd77399f6546165fad857a25ab532effbf78c3f5352835',
    'US-WK-01-POL-0020': '7025985fc2b88f182a076d9d21fed76694d00a90d322bceae92d5fa647b749b0',
}


def norm(value):
    return ' '.join(re.sub('[\u200b\u200c\u200d\ufeff]', '', value or '').split())


def compact(value):
    return re.sub(r'\s+', '', norm(value))


def main():
    input_path = ROOT / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json'
    original_input = input_path.read_bytes()
    data = json.loads(original_input)
    manifest = json.loads(ARCHIVES.read_text(encoding='utf-8-sig'))
    sources = {r['source_url']: r for r in manifest}
    evidence = {e['evidence_id']: e for e in data['evidence']}
    corrections = json.loads((OUT / 'quote_corrections_20261028.json').read_text(encoding='utf-8'))
    overrides = {r['evidence_id']: r['replacement_quote'] for r in corrections['replacements']}
    cache = {}

    def content(url):
        if url in cache:
            return cache[url]
        source = sources.get(url)
        if not source or source['status'] != 'downloaded':
            return None
        raw = (ROOT / source['source_file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source['sha256']
        if raw.startswith(b'%PDF'):
            with pymupdf.open(stream=raw, filetype='pdf') as doc:
                text = '\n'.join(page.get_text(sort=True) for page in doc)
        else:
            soup = BeautifulSoup(raw, 'html.parser')
            for tag in soup(['script', 'style']):
                tag.decompose()
            text = soup.get_text(' ', strip=True)
            if any(marker in (soup.title.get_text().lower() if soup.title else '') for marker in ('access denied', 'just a moment', 'error 403')):
                return None
        result = {'sha256': source['sha256'], 'source_file': source['source_file'], 'text': text,
                  'normalized': norm(text), 'compact': compact(text), 'is_pdf': raw.startswith(b'%PDF')}
        cache[url] = result
        return result

    policy_rows = []
    for policy in data['policy_candidates']:
        if policy['country'] not in ('usa', 'japan'):
            continue
        checks = []
        holds = []
        for ref in policy['source_evidence_ids']:
            ev = evidence[ref]
            url = ev['source_url']
            current_url = WEST_ATTACHMENT if policy['program_id'] == 'US:US-WEST-01' and ev['source_file'].endswith('.pdf') else url
            current = content(current_url)
            quote = overrides.get(ref, ev.get('exact_quote') or '')
            check = {'evidence_id': ref, 'source_url': url, 'retrieved_document_url': current_url}
            if current:
                check.update(current_source_file=current['source_file'], current_sha256=current['sha256'])
                if ev.get('source_sha256') == current['sha256']:
                    check['status'] = 'current_official_document_bytes_match_archive'
                elif quote and norm(quote) in current['normalized']:
                    check['status'] = 'quote_reproduced_in_current_official_text'
                elif quote and compact(quote) in current['compact']:
                    check['status'] = 'quote_reproduced_ignoring_whitespace'
                elif policy.get('policy_text') and not re.search('[가-힣]', policy['policy_text']) and norm(policy['policy_text']) in current['normalized']:
                    check.update(status='policy_clause_reproduced_broader_evidence_context_pending', broader_evidence_quote_reproduced=False)
                    holds.append('broader_evidence_section_extraction_review')
                else:
                    check['status'] = 'current_source_retrieved_quote_requires_review'
                    holds.append('quote_context_or_extraction_review')
                check['corrected_quote_used'] = ref in overrides
            elif policy['country'] == 'japan' and url in JP_WEB:
                check.update(status='official_web_manual_review_recorded', displayed_source_date=JP_WEB[url],
                             method='official page read through web tool; automated download returned 403; not byte equality')
            elif url == DOL_LAW:
                archived = BeautifulSoup((ROOT / ev['source_file']).read_bytes(), 'html.parser')
                main = archived.find('main')
                main_text = norm(main.get_text(' ', strip=True))
                assert hashlib.sha256(main_text.encode()).hexdigest() == DOL_LAW_MAIN_SHA
                assert norm(quote) in main_text or compact(quote) in compact(main_text)
                check.update(status='current_browser_main_body_sha256_matches_archive', normalized_main_body_sha256=DOL_LAW_MAIN_SHA,
                             method='full SHA-256 of live browser main text equals archived main text')
            elif policy['policy_id'] in DOL_CLAUSE_SHA:
                expected = DOL_CLAUSE_SHA[policy['policy_id']]
                assert hashlib.sha256(norm(quote).encode()).hexdigest() == expected
                check.update(status='current_browser_quote_match', normalized_quote_sha256=expected)
            elif url in US_WEB_MANUAL:
                check.update(status='official_web_manual_review_recorded', method='official web page read; not byte equality')
            else:
                check.update(status='current_source_fetch_blocked', http_status=sources.get(url, {}).get('http_status'))
                holds.append('official_source_access_or_alternative_reference_required')
            checks.append(check)
        if policy['country'] == 'japan':
            holds.append('document_scope_category_symbols_and_statutory_eligibility_require_separate_review')
            if policy['program_id'] == 'JP:JP-WH-01':
                holds.append('nationality_age_exception_and_current_application_window_check')
        else:
            holds.append('policy_summary_semantic_support_and_legal_exceptions_require_review')
        row = {'policy_id': policy['policy_id'], 'program_id': policy['program_id'], 'country': policy['country'],
               'reviewed_at': '2026-10-28', 'source_checks': checks, 'legal_holds': holds,
               'legal_validation_completed': False, 'approved_for_eligibility_decision': False}
        if policy['program_id'] in J1_RULES:
            law = J1_RULES[policy['program_id']]
            current = content(law)
            row['supplemental_legal_reference'] = {'source_url': law, 'retrieved': bool(current)}
            if current:
                row['supplemental_legal_reference']['source_file'] = current['source_file']
            # Program brochure says '< six'; regulation explicitly includes exactly six.
            if 'less than six months' in (policy.get('policy_text') or '').lower():
                row['legal_holds'].append('evaluation_exactly_six_months_boundary_requires_regulation_over_brochure')
                row['normative_clarification'] = {
                    'source_url': J1_RULES[policy['program_id']], 'provision': '22 CFR 62.22(l)',
                    'reviewed_policy_text': '평가 주기는 6개월 초과와 6개월 이하로 구분한다. 정확히 6개월인 프로그램을 종료 평가 의무에서 제외하면 안 된다.',
                    'text_kind': 'reviewer_summary_not_source_quote', 'historical_quote_changed': False,
                    'automatic_eligibility_rule_enabled': False,
                }
        original = policy['metadata'].get('original_policy') or {}
        if policy['program_id'] == 'US:US-EM-01':
            row['historical_review_decision'] = policy['metadata'].get('human_review_decision')
            payment_source = any(any(marker in evidence[ref]['source_url'] for marker in ('H1B_Proc_Memo_FINAL.pdf', '2026-19554.htm', 'restriction-on-entry-of-certain-nonimmigrant-workers')) for ref in policy['source_evidence_ids'])
            if payment_source or any(term in (policy.get('policy_text') or '') for term in ('$100,000', '10만')):
                row['legal_holds'].append('historical_h1b_payment_guidance_court_order_and_appeal_status')
                row['current_authority_observation'] = {
                    'source_url': 'https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations',
                    'observation': 'USCIS 현재 공지는 2026-06-08 지침 무효화와 2026-07-24 집행정지 요청 기각 및 법원 명령 준수를 설명한다. 옛 납부 지침만으로 현재 납부 의무를 단정하지 않는다.',
                    'court_docket_review_complete': False,
                }
        if policy['program_id'] == 'US:US-WEST-01':
            row['legal_holds'].append('historical_2026_first_half_notice_not_current_recruitment')
            row['temporal_scope'] = '2026_first_half_only'
        row['legal_holds'] = sorted(set(row['legal_holds']))
        policy_rows.append(row)
    assert len(policy_rows) == 327 and len({r['policy_id'] for r in policy_rows}) == 327
    assert Counter(r['country'] for r in policy_rows) == {'usa': 161, 'japan': 166}
    scope_review_ids = apply_scope_clarifications(policy_rows)
    grouped = defaultdict(dict)
    for row in policy_rows:
        grouped[row['country']][row['policy_id']] = row
    result = {'reviewed_at': '2026-10-28', 'input_sha256': hashlib.sha256(original_input).hexdigest(),
              'scope': 'all 327 policies inspected; source match and legal approval are distinct',
              'country_counts': dict(Counter(r['country'] for r in policy_rows)),
              'source_check_counts': dict(Counter(s['status'] for r in policy_rows for s in r['source_checks'])),
              'policy_legal_hold_counts': dict(Counter(h for r in policy_rows for h in r['legal_holds'])),
              'legal_validation_completed': 0, 'database_applied': False, 'policies': dict(grouped)}
    result['six_month_boundary_policy_ids'] = [r['policy_id'] for r in policy_rows if r.get('normative_clarification')]
    result['detailed_scope_review_policy_ids'] = scope_review_ids
    result['detailed_scope_review_count'] = len(scope_review_ids)
    result['six_policy_context_review_ids'] = [r['policy_id'] for r in policy_rows if 'broader_evidence_section_extraction_review' in r['legal_holds']]
    attach_resolution(result)
    target = ROOT / 'data/processed/legal_review/us_jp_policy_review_20261028.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT / 'us_jp_batch_summary_20261028.json').write_text(json.dumps({k:v for k,v in result.items() if k!='policies'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert input_path.read_bytes() == original_input
    print(json.dumps({k:v for k,v in result.items() if k!='policies'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

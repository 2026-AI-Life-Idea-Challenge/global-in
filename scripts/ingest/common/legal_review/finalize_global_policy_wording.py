"""Dated reviewer decisions for the fixed 590-policy snapshot, not visa decisions.

This is a reproducible publication of the review, not an approval classifier.
New snapshots and new policy IDs fail closed. Source availability alone is never
an approval criterion. Exceptions below are substantive reviewer decisions.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'data/processed/legal_review'
DATE = '2026-10-28'
SNAPSHOT_SHA = '043cf9bbb1d00c864d77912dca662e98960f5374766a219c36749bf7d2c69bd8'
MASTER = OUT / 'policy_content_approval_registry_20261028.json'
LEDGER = OUT / 'global_policy_wording_decisions_20261028.json'
FLAGS = ['approved_for_user_answers', 'approved_for_embedding',
         'approved_for_eligibility_decision', 'database_applied',
         'original_policy_replaced', 'lawyer_signed']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def reference(row):
    return dict(source_url=row['source_url'], source_file=row.get('source_file', row.get('current_source_file')),
                sha256=row.get('sha256', row.get('source_sha256', row.get('current_sha256'))))


def verify(refs):
    assert refs
    for ref in refs:
        assert ref['source_url'].startswith('https://')
        assert sha((ROOT / ref['source_file']).read_bytes()) == ref['sha256'], ref


# These are content-level holds, not requests for actual applicants' private data.
AU_HOLDS = {
    'AU_189_PT_POL_03': 'Thapa 판결 주문·후속 판례와 초청 후 60일 내 기술심사 취득 안내의 현재 적용을 확정해야 한다.',
    'AU_190_POL_04': 'Thapa 판결·현재 행정 적용과 초청 전 3년/초청 후 60일 취득 경로를 함께 확정해야 한다.',
    'AU_491_POL_04': 'Thapa 판결·현재 행정 적용과 초청 전 3년/초청 후 60일 취득 경로를 함께 확정해야 한다.',
    'AU_482_CORE_POL_13': 'LIN 25/082의 시험별 점수·면제와 신청 전/결정 전 3년 기준을 하나의 완전한 영어 문구로 병합해야 한다. 시점 수정안만으로 전체 항목을 승인하지 않는다.',
    'AU_482_SPECIALIST_POL_12': '하나의 원문에 후원 대가 지급 및 영어 요건이 섞여 있다. 두 법적 주제와 LIN 25/082의 시험 점수·면제·기준일을 분리한 전체 수정본이 필요하다.',
    'AU_500_POL_04': 'LIN 25/090의 시험일 구간·시험별 점수·면제 및 streamlined/regular evidence 기준일을 모두 담은 대체 문구 확정이 필요하다.',
    'AU_500_POL_02': '2026-10-02 이후 호주 내 재신청의 코스 패키징 제한과 CoE 예외를 신청 분류별 문구에 반영해야 한다.',
    'AU_500_POL_06': '2026-10-02 LIN 20/158의 현행 신청 가능 비자 목록과 995 주/부신청자 구분을 완전한 대체 목록으로 확정해야 한다.',
    'AU_500_POL_07': '2026-10-02 이후 호주 내 재신청의 6개 예외와 주/부신청자 전환 제한을 정확한 논리 분기로 다시 작성해야 한다.',
    'AU_500_POL_08': '가족 동시 신청·소재지·기존 비자 및 2026-10-02 경과조치가 결합된다. ASEAN/Pacific 국적만으로 모든 예외를 승인하지 않는다.',
    'AU_186_DE_POL_03': '학술직 면제의 안내문 B–E와 LIN 19/216 A–E 차이 및 다른 연령 면제를 포함한 전체 수정 문구를 확정해야 한다.',
    'AU_186_TRT_POL_06': '연령 면제의 고소득·지역 의료·학술직 정의와 과거 457 경과조치의 종료일을 포함한 대체 문구가 필요하다.',
    'AU_494_EMPLOYER_SPONSORED_POL_01': 'LIN 19/216 연령 면제의 직무·경력·급여 정의를 원문 주장 각각과 함께 최종 대조해야 한다.',
    'AU_190_POL_03': '지명 철회 시 application becomes invalid라는 안내와 법정 승인 요건 불충족을 구별한 수정 문구가 필요하다.',
    'AU_191_REGIONAL_PROVISIONAL_POL_06': '정부 채무와 거절·취소 이력이 한 레코드에 결합되어 있다. 비동반 가족 범위와 s48/s501E를 각각 명시한 전체 수정본이 필요하다.',
}


def build():
    raw = (OUT / 'inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    assert sha(raw) == SNAPSHOT_SHA
    original = {p['policy_id']: p for p in json.loads(raw)['policy_candidates']}
    assert len(original) == 590
    age = read(OUT / 'australia_age_content_approvals_20261028.json')
    au = read(OUT / 'australia_statutory_scope_20261028.json')
    au_corrected = read(ROOT / 'data/processed/australia/australia_wording_corrections_v2_20261028.json')['corrections']
    uj = read(OUT / 'us_jp_policy_review_20261028.json')
    resolution = read(OUT / 'us_jp_resolution_v1_20261028.json')['policy_resolutions']
    us_new = read(ROOT / 'data/processed/usa/shared/usa_policy_wording_supplement_20261028.json')['policies']
    ca = read(ROOT / 'docs/legal_review/canada_policy_review_20261028.json')
    de = read(OUT / 'germany_statutory_scope_20261028.json')
    collected = read(OUT / 'global_policy_source_manifest_20261028.json')
    fresh = {r['source_url']: reference(r) for r in collected if r['status'] == 'downloaded'}
    approvals = dict(age['policies'])
    decisions = {}
    jp_web_path = OUT / 'japan_wh_web_capture_20261028.json'
    jp_web = read(jp_web_path)
    ca_web_path = OUT / 'canada_program_web_capture_20261028.json'
    ca_web = read(ca_web_path)
    ca_urls = {url for batch in ca_web['batches'] for url in batch.get('urls', [])}
    def web_reference(url, path):
        return dict(source_url=url, source_file=path.relative_to(ROOT).as_posix(),
            sha256=sha(path.read_bytes()), capture_kind='web_tool_rendered_text_not_origin_html_bytes',
            hash_scope='saved tool-result capture, not origin HTML or byte equality')

    def hold(pid, reason, sources=None, draft=None, kind='content_revision_required'):
        decisions[pid] = dict(policy_id=pid, country=original[pid]['country'],
            decision='not_approved', status=kind, reason=reason,
            next_action=reason, source_urls=sources or [], proposed_wording=draft,
            legal_validation_approved=False, reviewed_at=DATE)

    def approve(pid, text, scope, refs, findings, structured=None):
        assert text.strip() and findings
        verify(refs)
        old = original[pid]['policy_text']
        approvals[pid] = dict(policy_id=pid, version='wording-v2-20261028',
            original_source_evidence_ids=original[pid]['source_evidence_ids'],
            reviewed_policy_text=text, reviewed_policy_text_sha256=sha(text.encode()),
            original_policy_text_sha256=sha((old or '').encode()),
            original_policy_text_was_null=old is None,
            approval_status='policy_content_review_passed', legal_validation_approved=True,
            scope=scope, reviewer='Codex: source-backed bounded policy wording review',
            source_references=refs, substantive_comparison=findings,
            structured_scope=structured,
            review_checks=dict(authority=True, dated_scope=True, wording_compared=True,
                               exceptions_preserved=True, unresolved_content_issue_absent_in_approved_scope=True),
            re_review_triggers=['source or policy wording changes', 'different application period',
                               'amending law, instrument, court order or official notice'],
            not_approved_for=['automatic individual eligibility', 'visa grant', 'unbounded historical applications'],
            **{key: False for key in FLAGS})

    # AU: all texts were compared by subclass and stream, not by phrase similarity.
    # Broader individualized checks remain separate from a general conditional text.
    au_holds = dict(AU_HOLDS)
    for pid, row in au['policies'].items():
        if pid in approvals:
            continue
        p = original[pid]
        refs = [reference(au['evidence'][eid]) for eid in row['statutory_evidence_refs']]
        sources = {r['source_url']: r for r in refs}
        for sid in ['regulations_volume1', 'regulations_volume2', 'regulations_volume3']:
            # Full governing volumes preserve secondary/family criteria not repeated in a topic route.
            ref = reference(au['sources'][sid])
            sources[ref['source_url']] = ref
        if pid in au_corrected:
            correction = au_corrected[pid]
            text = correction['text']
            if correction.get('include_complete_text_of'):
                text += '\n\n' + au_corrected[correction['include_complete_text_of']]['text']
            for sid in correction['source_ids']:
                sources[au['sources'][sid]['source_url']] = reference(au['sources'][sid])
            for url in correction.get('additional_source_urls', []):
                path = OUT / correction.get('additional_capture_file', 'australia_additional_instruments_web_capture_20261028.json')
                assert url in read(path)['urls']
                sources[url] = web_reference(url, path)
            approve(pid, text, '2026-10-28 현재 지정 법령의 일반 조건을 대체 문구로 검증. 새 문구에 명시한 범위만 승인하며 원본 안내문의 다른 주장·개별 자격은 제외.',
                    list(sources.values()), [row['reviewed_policy_text'],
                    '추가 실질 대조 후 완전한 대체 문구로 수정했다. 이전 timing-only draft 또는 구 안내문 전체의 승인이 아니다.'])
            continue
        if pid in au_holds:
            hold(pid, au_holds[pid], list(sources), row['reviewed_policy_text'])
            continue
        text = (p['policy_text'] or '').strip()
        text = re.split(r'\nMeet all these criteria\?', text)[0]
        findings = [row['reviewed_policy_text']]
        conditions = []
        topic = p['topic']
        # Replace headings-only extraction with an actual scoped condition.
        replacements = {
            'AU_189_PT_POL_01': '호주 내 subclass 189 points-tested 신청 시 실체 비자 또는 BVA/BVB/BVC를 보유해야 한다. 현재 또는 마지막 실체 비자가 491/494이면 신청 시 그 비자를 최소 3년 보유한 조건도 확인한다.',
            'AU_189_PT_POL_02': 'subclass 189 points-tested는 SkillSelect EOI 제출만으로 신청할 수 없고 장관의 초청을 받은 뒤 초청에서 정한 기간 내 신청해야 한다.',
            'AU_189_PT_POL_04': 'subclass 189 points-tested 연령은 초청 당시 만 45세 미만이다. EOI 제출 시 나이가 아니라 초청 시 나이를 사용하며 초청 후 45세가 되어도 그 사실만으로 초청 당시 연령 조건을 잃지는 않는다.',
            'AU_494_LABOUR_AGREEMENT_POL_03': 'subclass 494 노동협약 스트림에서는 해당 노동협약이 지정한 직종 업무를 수행할 기술·자격·고용 경력을 충족해야 한다. 고용 경력 기간과 양허는 해당 협약 및 494.235에 따라 확인하며 모든 협약에 무조건 3년 전일제 경력을 부과하지 않는다.',
        }
        if pid in replacements:
            text = replacements[pid]
            findings.append('해당 법정 경로와 대조한 대체 문구를 사용한다. 원본 레코드는 교체하지 않는다.')
        if 'values' in topic or text.startswith('Sign the Australian values statement'):
            minimum = 16 if pid.startswith(('AU_191_', 'AU_491_', 'AU_494_')) else 18
            text = f'이 비자·스트림의 해당 신청자는 만 {minimum}세 이상인 경우 Life in Australia 내용을 읽거나 설명을 듣고, PIC 4019 및 Schedule 4 Part 3에 따른 Australian Values Statement의 요구되는 선언·확인을 해야 한다. 해당 비자 조문의 연령과 주/부신청자 적용 범위를 사용한다.'
            findings.append(f'비자별 연령 {minimum}세 확인; 특히 491 안내문의 18세를 법령의 16세로 수정.')
        if 'health' in topic and 'insurance' not in topic or text.startswith(('Meet our health requirement', 'Meet the health requirement')):
            health_code = '4007' if pid.startswith(('AU_186_TRT_', 'AU_482_', 'AU_191_', 'AU_494_EMPLOYER_')) else '4005'
            if pid.startswith('AU_500_'):
                health_code = '4005 (DFAT/Defence 학생의 해당 분기는 4007)'
            text = f'해당 비자·스트림의 건강 기준은 PIC {health_code}이다. 해당 비자 조문이 정한 주신청자·동반 및 비동반 가족 범위에 적용한다. PIC 4007(2)의 면제는 정해진 비용·서비스 접근 기준에 대한 재량이며 결핵·공중보건 위험을 일괄 면제하지 않는다. PIC 4005/4007의 호주 출생·통상 거주 미성년자 비용 관련 예외를 별도로 보존한다. 검사 요청 및 검사·의견의 유효성은 실제 신청 경로에 따라 확인한다.'
            findings.append('PIC 4005/4007 및 가족 범위를 분리하고 비용 면제와 감염병 요건을 구별했다.')
        if 'character' in topic or text.startswith('Meet our character requirement'):
            conditions.append('PIC 4001 및 Migration Act s501을 구분한다. 경찰 증명서 안내의 16세 기준은 16세 미만의 모든 법적 인성 요건을 면제한다는 뜻이 아니다. 가족 범위는 해당 비자 조문을 따른다. 482의 공인 후원자 관련 해외 경찰증명 제출 예외도 인성 심사나 별도로 요청되는 호주 경찰증명을 일괄 면제하지 않는다.')
        if topic == 'government_debt' or text.startswith(('Have paid back your debt', 'Pay back your debt')):
            text = 'PIC 4004에 따라 Commonwealth에 미상환 채무가 없거나 상환을 위한 적절한 조치를 마련해야 한다. 전액 선납만이 유일한 경로는 아니다. 가족 중 누구에게 별도 기준이 적용되는지는 해당 비자 조문의 주/부신청자 및 비동반 가족 범위를 따른다. 모든 친족에게 자동으로 같은 채무 기준을 확장하지 않는다.'
        if topic == 'immigration_history':
            text = '과거 거절·취소만으로 모든 비자 신청이 자동 금지되지는 않는다. s48은 호주 내 소재, 실체 비자 미보유 및 최근 입국 후 해당 거절·취소 등을 함께 판단한다. reg 2.12에 허용되는 비자 class가 있어도 나머지 유효 신청·승인 기준을 충족해야 한다. 인성 관련 s501E, PIC 4013/4014 및 특별 재입국 기준은 각각 별도로 적용한다.'
        if topic == 'health_insurance':
            if pid == 'AU_500_POL_05':
                text = 'subclass 500 신청자와 해당 동반가족은 원칙적으로 호주 도착일부터 전체 체류 기간에 필요한 OSHC를 유지해야 한다. 코스 개강일부터만 가입하는 것으로 도착 전후 공백을 만들지 않는다. 노르웨이 National Insurance, 스웨덴 Kammarkollegiet 및 벨기에 상호의료협정에 따른 지정 예외는 해당 자격·보장 조건을 실제로 충족할 때만 적용한다. 건강 심사와 보험은 별도 요건이다.'
            else:
                text = '해당 주신청자와 부신청자는 의도한 전체 호주 체류 기간 동안 적절한 의료보험을 갖추고 요구되는 비자 조건 8501을 지켜야 한다. 의료비에 대한 개인 부담 책임이 있으며, 상호의료협정 자격만으로 모든 필요한 보험 보장이 자동 충족되는 것은 아니다. 건강 심사 통과와 보험 유지 의무는 별도다.'
        if topic == 'points' or pid == 'AU_491_POL_05':
            conditions.append('65점은 법정 통과점이며 초청 보장이 아니다. 실제 심사 시 초청장에 기재된 점수 이상을 입증해야 하고, 나이·영어 등은 각 조문의 초청/신청/결정 시점을 따른다.')
            sources[au['sources']['points_pass_mark']['source_url']] = reference(au['sources']['points_pass_mark'])
        if topic == 'eligible_occupation' or pid == 'AU_491_POL_07':
            conditions.append('공고상 직종명만으로 판단하지 않는다. 해당 비자·스트림의 지정 instrument, ANZSCO 코드, 평가기관 및 지명/후원 분기별 직종 범위를 적용한다. 현재 어느 주가 해당 직종 지명을 모집하는지까지 승인한 문구는 아니다.')
            for sid in ['skilled_occupations', 'occupations_186', 'occupations_482', 'occupations_494']:
                sources[au['sources'][sid]['source_url']] = reference(au['sources'][sid])
        if pid.startswith('AU_407_'):
            text = text.replace('Administrative Appeals Tribunal', 'Administrative Review Tribunal').replace('AAT', 'ART')
            conditions.append('현행 심판기관 명칭은 ART다. 2026-03-11부터의 신청 시점 후원·지명 선행 조건과 Commonwealth 기관 예외를 적용한다. 일반 회사의 지명 신청만으로 모든 사전 승인 조건을 충족했다고 보지 않는다.')
            sources[au['sources']['training_reform_2026']['source_url']] = reference(au['sources']['training_reform_2026'])
        if pid.startswith(('AU_186_', 'AU_494_')):
            sources[au['sources']['exemptions_186_494']['source_url']] = reference(au['sources']['exemptions_186_494'])
            conditions.append('노동협약 양허는 실제 해당 협약이 허용하는 요건에만 적용한다. LIN 19/216의 면제는 요건별 지정 대상·정의·기간을 모두 충족해야 하며, 종료된 2024-06-30 legacy 457 신청 특례를 신규 신청의 현재 면제로 재사용하지 않는다.')
        if pid.startswith('AU_482_'):
            conditions.append('Core/Specialist/Labour Agreement 스트림을 구분한다. 관련 경력은 적용 기준일 전 5년 중 12개월 상당 및 허용되는 동등 시간·협약 예외를 해당 조문대로 판단한다. 주어진 실제 협약의 양허 수치나 개별 후원자의 자격 자체를 승인하지 않는다.')
            for sid in ['sid_reform_2024', 'mandatory_skills_482', 'occupations_482']:
                sources[au['sources'][sid]['source_url']] = reference(au['sources'][sid])
        if pid.startswith(('AU_417_', 'AU_462_')):
            conditions.append('첫째/둘째/셋째 비자의 이전 발급·입국·체류 이력을 구분한다. 서류 제출 생략은 실체 요건 면제가 아니다. 모집·연간 cap·ballot의 현재 접수 가능 상태는 이 문구의 승인 범위에 포함하지 않는다.')
            sid = 'wh_417_arrangements' if pid.startswith('AU_417_') else 'wh_462_arrangements'
            sources[au['sources'][sid]['source_url']] = reference(au['sources'][sid])
            if topic == 'financial_capacity':
                conditions.append('AUD 5,000은 초기 체류를 위한 공식 안내의 통상 금액이며 법령상 모든 신청에 동일한 확정 최소액으로 변환하지 않는다. 출국 항공료 또는 그에 충분한 자금은 별도다.')
            if topic == 'specified_work':
                conditions.append('지정 업무의 업종·지역·날짜·보수 및 둘째/셋째 비자에 산입 가능한 수행 기간은 해당 instrument를 따른다. 단순히 임의의 3개월/6개월 근무를 뜻하지 않는다. 417은 2024-07-01 이후 영국 여권으로 신청하는 지정근무 면제 분기를 별도로 적용한다.')
                for instrument in ['specified_work_417', 'specified_work_462', 'wh_uk_exemption_2024']:
                    sources[au['sources'][instrument]['source_url']] = reference(au['sources'][instrument])
        if pid.startswith('AU_462_') and (topic in {'passport', 'education', 'government_support'}):
            soup = BeautifulSoup((ROOT / au['sources']['wh_462_arrangements']['source_file']).read_bytes(), 'html.parser')
            rows = [[c.get_text(' ', strip=True) for c in r.find_all(['td', 'th'], recursive=False)] for r in soup.find_all('tr')]
            education = [r for r in rows if len(r) == 4 and r[0].isdigit()]
            exempt = [r[1] for r in rows if len(r) == 2 and r[0].isdigit()]
            assert len(education) == 31 and len(exempt) == 19
            if topic == 'passport':
                text = 'LIN 26/072에 열거된 subclass 462 여권·국적 대상은 다음과 같다: ' + '; '.join(r[1] for r in education) + '. 유효한 해당 여권을 보유해야 하며 다른 신청·입국 이력 및 유효 신청 기준도 충족해야 한다. 이 승인은 31개국 목록에 한정하며 ballot 또는 연간 접수 가능 상태를 확정하지 않는다.'
            elif topic == 'education':
                text = 'LIN 26/072의 국가별 학력 조건(각 행 내부의 or/and를 그대로 적용):\n' + '\n'.join(r[1] + ': ' + r[2] for r in education)
            else:
                text = 'subclass 462 첫 신청의 정부 지원은 462.213 및 지정 instrument에 따른다. LIN 26/072 section 5의 지원 면제 국가: ' + '; '.join(exempt) + '. 목록 밖의 지정국은 해당 정부의 지원 요건을 별도 충족해야 한다. Good Conduct Certificate 등 제출 형식은 해당 공관의 안내와 함께 확인한다.'
            findings.append('31개 국가별 법령 표와 19개 지원 면제국을 재추출해 대조했다. 옛 목록의 Philippines 누락 및 Czech Republic/Spain/PNG 등의 학력 문구 차이를 대체 버전에 반영했다.')
        # An unknown unresolved scope issue must not silently pass.
        if pid in {'AU_462_FIRST_POL_05', 'AU_500_POL_09'}:
            reason = 'LIN25/014 section6(c)는 신청일 이후 시험 경로도 두지만 첫462 안내는 신청 전12개월로 설명한다. 이 시점 차이 및 이스라엘 Bagrut의 Minister-assessed 경로를 확정하기 전 안내문 전체를 승인하지 않는다.'
            hold(pid, reason, list(sources) + ['https://www.legislation.gov.au/F2025L00904/asmade/2025-08-06/text/original/epub/OEBPS/document_1/document_1.html'], text)
            continue
        if conditions:
            text += '\n\n적용 범위·예외: ' + ' '.join(conditions)
        approve(pid, text, '2026-10-28 현재 해당 subclass/stream의 명시된 일반 조건. 법령의 별도 시행·경과 시점 적용; 개별 자격·현재 모집 상태 제외.', list(sources.values()), findings)

    # JP documentary rows: publish a scoped record, never a nationality-wide scalar.
    for pid, row in uj['policies']['japan'].items():
        detailed = row.get('detailed_scope_review', {})
        pdf = detailed.get('official_pdf_row')
        refs = []
        for source in row['source_checks']:
            if source.get('current_source_file'):
                refs.append(reference(source))
            else:
                assert source['status'] == 'official_web_manual_review_recorded'
                assert source['source_url'] in jp_web['sources']
                refs.append(dict(source_url=source['source_url'],
                    source_file=jp_web_path.relative_to(ROOT).as_posix(),
                    sha256=sha(jp_web_path.read_bytes()),
                    capture_kind='web_tool_rendered_text_not_origin_html_bytes',
                    hash_scope='saved tool-result capture, not origin HTML or byte equality'))
        if pdf:
            scope = dict(detailed['application_scope'])
            corrected = resolution.get(pid, {}).get('correction_v1', {})
            scope.update(corrected.get('corrected_scope', {}))
            refs.append(reference(pdf))
            nat = scope.get('nationality_reference')
            if nat:
                refs.append(reference(nat))
            body = dict(application_scope=scope, official_pdf_row=pdf,
                findings=detailed['findings'],
                interpretation='○は当該列の提出対象、△は原文条件付き、－は当該一覧の対象外。空欄を一般的免除に変換しない。行内の選択肢を累積条件にしない。',
                limitation='提出資料の当該一覧に限る。実体的な在留資格要件の充足、申請の許可及び自動国籍コード判定は含まない。')
            text = json.dumps(body, ensure_ascii=False, indent=2)
            approve(pid, text, '2026-10-28に確認した公式提出資料表の指定申請種類・機関区分・学校区分・国籍列・条件付き行のみ。',
                    refs, detailed['findings'] + ['原文の全セル、行グループ条件、選択・条件を版に固定。国籍別の列を保持し単一状態へ縮約しない。'], scope)
        else:
            text = original[pid]['policy_text']
            suffix = '대한민국 거주 대한민국 국민을 위한 주한 일본대사관 안내의 해당 조건이다. 신청 시 연령·실제 발급 횟수 및 공관의 예외 판단을 따른다. 현재 분기의 접수가 열려 있다는 의미가 아니며 전체 사증 요건 충족을 확정하지 않는다.'
            if pid in {'JP-POL-7402f3813d9aa398419d6397', 'JP-POL-54f47ecde2bc322be711ab35'}:
                suffix = '외무성의 양자 워킹홀리데이 협정 참가 자격 설명 중 여권·귀국 항공권 또는 구매 자금 조건만 검증한다. 모든 국가 국민에게 일본 내 일반 취업 허가를 준다는 의미가 아니며 국별 협정과 공관의 별도 조건을 따른다.'
            if pid == 'JP-POL-6b986824f1c3095d6c1b0cf4':
                suffix += ' 미사용 발급 사증도 원칙적으로 횟수에 포함되며 별도 예외 인정 없이 무시하지 않는다. 2025-10-01 이후 한국과의 제도는 1회당 최대 1년, 최대 2회이며 일본 내 기간 연장이 아니다.'
            if pid == 'JP-POL-6ff49b598065727f4e9ebb0f':
                suffix += ' 병역 종사 사실이 있는 경우의 증빙이며 모든 신청자에게 병역 이행 자체를 요구하는 뜻은 아니다.'
            approve(pid, text + '\n\n' + suffix, '2026-10-28 확인된 해당 워킹홀리데이 일반 조건/제출자료; 모집 일정·개별 사증 승인 제외.', refs,
                    ['해당 공식 원문의 선택 제출·가족 계좌·언어 증빙 대체 및 발급 횟수·연령 예외를 원문 범위대로 보존했다.', suffix])

    # USA: reviewed paragraph-backed claims and explicit corrections. Non-anchored
    # material is retained for review rather than treated as approved by a URL.
    for pid, row in uj['policies']['usa'].items():
        d = row.get('detailed_scope_review', {})
        correction = resolution.get(pid, {}).get('correction_v1', {})
        legal = d.get('legal_reference_check') or correction.get('legal_reference')
        if pid in {'US-J1-INTERN-POL-008', 'US-J1-TRAINEE-POL-011'}:
            base = uj['policies']['usa']['US-J1-INTERN-POL-005']['detailed_scope_review']['legal_reference_check']
            soup = BeautifulSoup((ROOT / base['source_file']).read_bytes(), 'html.parser')
            clause = soup.find(id='p-62.22(l)')
            clause_text = ' '.join(clause.get_text(' ', strip=True).split())
            assert "six months or less" in clause_text and "exceeding six months" in clause_text
            legal = dict(base, provision='62.22(l)', normalized_paragraph_sha256=sha(clause_text.encode()))
        source_urls = [s['source_url'] for s in row['source_checks']]
        if 'court_order_scope_unresolved' in d.get('issue_codes', []):
            hold(pid, '2026-09-30 이후 관련 소송의 후속 주문·항소 및 기관 조치를 확인하기 전 H-1B 10만 달러의 현재 납부 의무를 승인할 수 없다.', source_urls, kind='current_legal_effect_unresolved')
        elif 'WEST' in pid:
            hold(pid, '2026년 상반기 WEST 공고는 해당 과거 모집 자료다. 현재 모집 정책으로 사용하려면 후속 모집 공고·현재 참가 조건을 대조해야 한다.', source_urls, kind='historical_notice_not_current_policy')
        elif pid in us_new:
            refs = [reference(s) for s in row['source_checks'] if s.get('current_source_file')]
            path = OUT / 'usa_procedure_lca_web_capture_20261028.json'
            if pid in {'US-WK-01-POL-0006', 'US-WK-01-POL-0031', 'US-WK-01-POL-0052', 'US-WK-01-POL-0064', 'US-WK-01-POL-0076', 'US-WK-01-POL-0078', 'US-WK-01-POL-0012'}:
                refs.append(web_reference(source_urls[0], path))
            extra = {
                'US-WK-01-POL-ADD-005': '655.732',
                'US-WK-01-POL-ADD-006': '655.733',
                'US-WK-01-POL-ADD-007': '655.734',
            }
            if pid in extra:
                refs.append(web_reference('https://www.ecfr.gov/current/title-20/chapter-V/part-655/subpart-H/section-' + extra[pid], path))
            prior_browser = [s for s in row['source_checks'] if s['status'] == 'current_browser_main_body_sha256_matches_archive']
            if prior_browser:
                file = ROOT / 'data/raw/usa/employment/h1b_specialty_occupation/dol_h1b_lca_law.html'
                main = BeautifulSoup(file.read_bytes(), 'html.parser').find('main')
                normalized = ' '.join(main.get_text(' ', strip=True).split())
                assert sha(normalized.encode()) == prior_browser[0]['normalized_main_body_sha256']
                refs.append(dict(source_url=prior_browser[0]['source_url'], source_file=file.relative_to(ROOT).as_posix(),
                    sha256=sha(file.read_bytes()), normalized_main_body_sha256=sha(normalized.encode()),
                    capture_kind='archived_origin_html_with_earlier_same_day_browser_main_comparison',
                    limitation='Later web-tool HTTP 403 is retained separately and is not a body re-download.'))
            if pid == 'US-WK-01-POL-AGL-002':
                base = read(OUT / 'f1_statutory_review_20261028.json')['policies']['US-F1-POL-001']['provisions'][0]
                soup = BeautifulSoup((ROOT / base['source_file']).read_bytes(), 'html.parser')
                clause = soup.find(id='p-214.2(h)(4)(i)(B)(1)(v)')
                clause_text = ' '.join(clause.get_text(' ', strip=True).split())
                assert 'at least 1 year from the date of receipt' in clause_text
                refs.append(dict(reference(base), provision='214.2(h)(4)(i)(B)(1)(v)', normalized_paragraph_sha256=sha(clause_text.encode())))
            approve(pid, us_new[pid], '2026-10-28 확인된 해당 일반 절차·서류·노동조건 의무만. 각 통합본 기준일까지의 조문이며 개별 자격·소송 효력·현재 모집/수수료 계산 제외.',
                    refs, [d.get('finding', ''), '행위자·해당 절차·기한·예외를 본문과 추가 실질 대조하고 별도 새 버전으로 고정했다.'],
                    dict(original_reference=d.get('source_section'), approved_scope='named procedural or statutory condition only'))
        elif pid in {'US-F1-POL-001', 'US-F1-POL-002', 'US-F1-POL-004'}:
            f1 = read(OUT / 'f1_statutory_review_20261028.json')['policies'][pid]
            texts = {
                'US-F1-POL-001': 'F-1 과정은 SEVP가 F-1 학생 수학을 허용한 인증 학교의 해당 과정이어야 한다. 학교 검색 지도 또는 학교 이름 검색 성공만으로 특정 과정의 인증·개인 입학·비자·입국을 승인하지 않는다.',
                'US-F1-POL-002': 'F-1 입국 자료로 본인 명의의 SEVP 인증 학교 발행 I-20 또는 후속 양식을 제시해야 한다. 학교 입학·DSO 발행과 국무부 비자 발급 및 국경 입국 심사는 별도다. I-20만으로 다른 재정·학업·입국 요건이 충족되거나 즉시 입국이 허용되지는 않는다.',
                'US-F1-POL-004': '최초 유학·교환 참여를 위한 해당 F/M/J 주신청자는 원칙적으로 사증 발급 전에 I-901 SEVIS 수수료를 납부해야 한다. 단순히 최초 입국 직전에만 납부하면 된다는 뜻이 아니다. F-2/M-2/J-2 부양가족은 별도 수수료 대상이 아니다. 214.13(e)의 지정 연장·학교 이전·학업 수준 변경·OPT 및 계속 재학 등의 새 납부 면제는 해당 조건을 충족할 때 적용하며 새 I-20 발급만으로 재납부를 자동 요구하지 않는다.'
            }
            approve(pid, texts[pid], '해당 학교 인증/I-20/SEVIS 납부 조건만. F-1 고정 체류기간·취업·입국 시점 및 개인 허가 제외.',
                    [reference(r) for r in f1['provisions']], f1['findings'] + ['고정 체류기간 규칙에 관한 별도 쟁점이 이 자료·수수료 조건의 포괄 보류 사유는 아니다.'])
        elif pid in {'US-F1-POL-003', 'US-F1-POL-007'}:
            hold(pid, 'I-20 서명·F-2/M-1 교차 범주 또는 8 CFR 248 신분변경의 별도 제한·기준일을 해당 복합 문구 전체와 대조해야 한다.', source_urls, d, kind='primary_content_comparison_incomplete')
        elif pid.startswith('US-F1-') or pid == 'US-WK-01-POL-0092':
            hold(pid, 'F-1 고정 체류기간 규칙·입국/SEVIS/cap-gap 분기의 현재 효력과 법원 명령을 확인해야 한다. 현재 CFR 수록 또는 안내문만으로 효력을 단정하지 않는다.', source_urls, correction or d, kind='current_legal_effect_unresolved')
        elif pid in {'US-WK-01-POL-0001', 'US-WK-01-POL-0061'}:
            fee = resolution[pid]['fee_scope_review']
            text = '8 CFR 106.2(c)(8)–(9)의 추가 수수료는 미국 내 직원이 50명 이상이고 그 중 H-1B와 L-1 신분 직원 합계가 50%를 초과하는 해당 고용주 청원에 적용하는 조건이다. 2026-09-09 시행 규정의 H-1B USD 4,000/L-1 USD 4,500 분기를 구분한다. 연장을 요청하지 않는 amendment의 지정 면제를 보존한다. 해당 법정 적용 대상 접수는 2027-09-30까지라는 일몰을 따르며, 실제 고용주 인원·신분 비율·청원 유형·접수일을 개별 확인해야 한다. 이 문구는 H-1B 10만 달러 포고령 납부 의무와 별개이며 특정 청원의 현재 청구액을 계산하거나 확정하지 않는다.'
            approve(pid, text, '2026-09-09 시행/2027-09-30 접수 일몰인 추가 수수료의 일반 조건. 10만 달러 포고령·개별 납부액 제외.',
                    [reference(fee)], ['50명 이상과 50% 초과를 구분하고 H-1B/L-1 합산·amendment 면제·일몰을 보존했다.', '실제 고용주 인원 자료 부재는 이 일반 조건의 문구 승인과 별도다.'])
        elif legal and legal.get('paragraph_anchor_found'):
            refs = [reference(s) for s in row['source_checks'] if s.get('current_source_file')] + [reference(legal)]
            components = correction.get('corrected_review_components')
            if components:
                text = '\n'.join(components)
            else:
                text = original[pid]['policy_text']
            finding = d.get('finding', '')
            if finding:
                text += '\n\n적용 범위·예외: ' + finding
            if pid.startswith(('US-J1-INTERN-', 'US-J1-TRAINEE-')):
                text += '\nIntern/Trainee는 해당 자격·주당 32시간 및 DS-7002 계획 조건을 따르는 별도 경로다. 호스트 방문은 성공적 종전 참가 이력 없는 경우 직원 25명 미만 또는 매출 300만 달러 미만의 조합과 대학/정부기관 제외를 적용한다. 평가서는 6개월 이하 종료 평가, 6개월 초과 중간·종료 평가를 구분하며 참가자·현장 감독자 서명과 스폰서 보존 의무를 따른다.'
            if pid.startswith('US-SWT-'):
                text += '\nSummer Work Travel의 계절·일시적 직무, 금지 직종 및 정규 장기방학 중 최대 4개월·연장 불가 제한은 별도다. VWP 국적 예외는 사전 일자리 확보 분기이며 사증 없이 취업할 수 있다는 뜻이 아니다. 임금·스폰서 월별 연락은 해당 모든 참가자에게 적용한다.'
            approve(pid, text, '2026-10-28 확인한 지정 CFR 조항의 해당 정책 주장·행위자·시간 조건. 비자 발급·개별 고용·모집 상태 제외.', refs,
                    [finding or '명시된 수정 문구의 기간·행위자·선택 조건을 해당 조문과 대조했다.', '조문 앵커 외에 개별 원문과 예외 범위를 실질 비교한 항목만 포함한다.'],
                    dict(provision=legal['provision'], paragraph_sha256=legal.get('normalized_paragraph_sha256')))
        else:
            hold(pid, '공식 안내와 적용 범위 기록은 확보했지만 해당 주장 전체의 현행 1차 조문·예외·시행 시점 대조가 미완료다. 안내 URL 또는 재추출 성공만으로 최종 문구 승인하지 않는다.', source_urls, d, kind='primary_content_comparison_incomplete')

    # CA: null originals stay null. Approve only a fully written, new version.
    ca_new = read(ROOT / 'data/processed/canada/canada_policy_wording_v2_20261028.json')
    ca_rows = ca['policy_reviews']
    if isinstance(ca_rows, list):
        ca_rows = {r['policy_id']: r for r in ca_rows}
    for pid, row in ca_rows.items():
        urls = [s['source_url'] for s in row['source_references']]
        if pid in ca_new['held_policy']:
            hold(pid, ca_new['held_policy'][pid], urls, row.get('reviewed_policy_text'), kind='official_guidance_boundary_unresolved')
            continue
        refs = [fresh[url] if url in fresh else web_reference(url, ca_web_path) for url in urls if url in fresh or url in ca_urls]
        if pid.startswith('CA_IEC_WH_'):
            refs.append(web_reference('https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility/eligibility-by-country.html', ca_web_path))
        approve(pid, ca_new['policies'][pid],
            '2026-10-28 확인된 캐나다 프로그램의 명시된 일반 조건을 새 문구로 작성. 원본 NULL 유지; 개별 사실·permit 발급·자동 국적/생일 계산 제외.', refs,
            ['기존 빈 문구가 아니라 별도의 완전한 새 문구 버전만 승인한다.',
             'IRCC 프로그램별 시점·면제와 관련 IRPR 조문을 대조했다. 실제 고용주·지원자의 사실 확인은 일반 조건의 문구 승인과 별도다.',
             'HTTP 다운로드 실패와 웹 도구 본문 확인을 구분한다. 증거 해시는 저장한 웹 결과이며 원본 HTML 바이트 일치를 주장하지 않는다.'])

    # DE: dated statutes and current official guidance captured in this batch.
    de_text = {
        'DE_SKILLED_POL_01': '§18a의 직업자격 전문인력은 독일의 적격 직업훈련 또는 그와 동등한 외국 직업자격을 갖추고 적격 고용을 하려는 경로다. §18의 구체적 고용 제안·필요한 연방고용청 동의(지정 면제 별도)·필요 직업허가의 발급 또는 약속·실제 고용 의사를 충족해야 한다. 최초 §18a/18b 발급이 만 45세를 채운 뒤이면 연금보험 연간 산정상한 55%의 급여(2026년 EUR 55,770) 또는 적정 노후 보장을 확인하며 법정 공익상 재량 예외는 별도다. 모든 직무가 Blue Card의 학위-직무 일치·급여 기준을 따르는 것은 아니다.',
        'DE_SKILLED_POL_02': '§18b의 학위 전문인력은 독일 학위, 독일에서 인정되는 외국 학위 또는 독일 학위에 비교 가능한 외국 학위를 갖추고 적격 고용을 하려는 경로다. §18의 실제 고용 제안·필요한 연방고용청 동의(지정 면제 별도)·필요 직업허가의 발급 또는 약속·실제 고용 의사를 확인한다. 최초 §18a/18b 발급이 만 45세를 채운 뒤이면 연금보험 연간 산정상한 55%의 급여(2026년 EUR 55,770) 또는 적정 노후 보장 및 법정 공익상 재량 예외를 구분한다. 학위와 직접 관련되지 않은 적격 고용도 가능한 일반 경로이며 Blue Card의 별도 기준을 일괄 부과하지 않는다.',
        'DE_OPP_POL_01': '독일에서 인정되는 전문인력 자격 경로의 Chancenkarte는 §20a에 따른 경로다. 독일 학위·직업자격 또는 독일에서 동등성이 인정된 해당 외국 자격을 확인한다. 이 경로에 점수 경로의 6점·A1/B2 언어 증명 요건을 일괄 부과하지 않는다. 생계 확보는 별도다.',
        'DE_OPP_POL_02': '점수 경로는 해당 외국 자격의 법정 조건 및 독일어 A1 이상 또는 영어 B2 이상을 갖추고 §20b·부속표의 최소 6점을 충족해야 한다. 독일에서 인정된 전문인력 경로와 구분한다. 연령 점수는 신청 당시 만 35세 이하 2점, 35세 초과 40세 이하 1점이며 독립적인 모든 경로의 최고 연령 제한이 아니다. 생계 확보도 필요하다.',
        'DE_BLUE_CARD_POL_01': 'EU Blue Card의 일반 경로는 §18g의 독일 학위·비교 가능한 외국 학위 또는 지정 수준의 최소 3년 고등교육 자격과 그 자격에 부합하는 최소 6개월 고용 제안을 요구한다. 2026년 일반 연봉 기준은 EUR 50,700(연금보험 산정상한의 50%)이며 규제 직종의 직업허가는 별도다. 낮은 급여 경로 및 학위 없는 지정 IT 경로는 별도 조건이다.',
        'DE_BLUE_CARD_POL_02': '§18g의 지정 부족직종(ISCO 그룹) 경로는 2026년 연간 총급여 EUR 45,934.20 이상(산정상한의 45.3%) 및 필요한 연방고용청 동의를 충족해야 한다. 최소 6개월의 자격에 부합하는 고용 제안 등 나머지 Blue Card 요건도 적용한다. 단순히 인력 부족이라고 주장하는 모든 직종에 적용하지 않는다.',
        'DE_BLUE_CARD_POL_03': '최근 학위·동등 고등교육 자격 경로는 신청 전 취득 후 3년을 초과하지 않은 경우다. 정확히 3년인 경계를 less than three years로 배제하지 않는다. 2026년 연간 총급여 EUR 45,934.20 이상 및 필요한 연방고용청 동의를 요구하며 부족직종 여부와 별도로 적용 가능한 경로다. 나머지 §18g 요건도 충족해야 한다.',
        'DE_BLUE_CARD_POL_04': '§18g의 학위 없는 지정 IT 경로는 ISCO 133/25에 해당하는 IT 고용 제안(최소 6개월), 신청 전 7년 중 최소 3년의 해당 고등교육 수준 전문 경력 및 필요한 연방고용청 동의를 요구한다. 2026년 연간 총급여 기준은 EUR 45,934.20 이상이며 모든 비학위 IT 경력자에게 자동 적용하지 않는다.',
        'DE_STUDY_VISA_POL_01': '§16b의 학업 체류는 국가·국가인정 또는 동등 기관의 전일제 과정 입학을 기본 경로로 하며 법정 입학준비·조건부 입학 분기는 별도다. 입학허가서만으로 생계·언어 등 모든 체류 요건을 충족했다고 판단하지 않는다.',
        'DE_STUDY_VISA_POL_02': '학업 기간의 생계를 확보해야 한다. 2026년 공식 일반 안내의 재정 증명 기준은 연 EUR 11,904이며 blocked account만이 유일한 방식은 아니다. 인정 장학금·Verpflichtungserklärung 등 허용되는 증명과 개별 범위를 구분한다. 다른 목적의 대학 진학처 탐색 금액으로 대체하지 않는다.',
        'DE_STUDY_VISA_POL_03': '§16b에 따른 과정별 언어 요건을 확인한다. 입학 절차에서 이미 언어 능력을 확인했거나 준비 과정에서 취득하도록 하는 해당 경우를 구분한다. 모든 독일 학업 사증에 독일어 B2라는 단일 기준을 부과하지 않는다.',
        'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_01': '대학 진학처 탐색은 §17(2)의 해당 대학 입학·준비과정 자격을 요구한다. 최대 9개월의 해당 체류 기간 안에 충족하도록 하는 법정 경로도 구분한다. §17(1)의 직업훈련처 탐색에 관한 35세 미만 조건을 이 대학 진학처 탐색 경로에 옮겨 적용하지 않는다.',
        'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_02': '대학 진학처 탐색의 언어 요건은 §17(2) 및 희망 과정의 기준을 따른다. 이미 충족한 경우와 법정 최대 9개월 안에 취득하도록 하는 허용 경로를 구분한다. 모든 신청에 동일 언어·동일 등급을 요구하지 않는다.',
        'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_03': '대학 진학처 탐색 기간 전체의 생계 확보가 필요하다. 2026년 해당 공식 안내 기준은 월 EUR 1,091이며 허용되는 재정 증명 방식과 예정 체류 기간을 함께 확인한다. 학업 입학 후 §16b의 연간 EUR 11,904 기준과 혼용하지 않는다.',
    }
    for pid, row in de['policies'].items():
        urls = row['official_sources_read']
        if pid == 'DE_WH_POL_03':
            hold(pid, '재정 EUR 3,500에서 항공권·3개월 숙박 증빙에 따른 EUR 1,000 공제의 중첩 가능 범위가 명확하지 않다. 임의로 EUR 1,500으로 계산하지 않고 공관의 정확한 제출 안내를 확정해야 한다.', urls, row['reviewer_paraphrase'])
            continue
        refs = [fresh[url] for url in urls if url in fresh]
        if pid in {'DE_SKILLED_POL_01', 'DE_SKILLED_POL_02'}:
            path = OUT / 'germany_sections_18_18b_web_capture_20261028.json'
            refs += [web_reference(url, path) for url in read(path)['sources']]
        if pid.startswith('DE_WH_'):
            text = original[pid]['policy_text']
            text += '\n주한 독일대사관의 대한민국 신청자 대상 안내다. 체류 최대 12개월, 1회 참가 조건과 별도 사증 심사를 따른다. 처리기간 3–5일은 안내상 예상이며 발급 보장이 아니다. 수수료 환산액·접수 방식은 실제 신청 시 재확인한다.'
        else:
            text = de_text[pid]
        approve(pid, text, '2026-10-28 확인된 해당 독일 체류 경로; 금액은 2026년 한정, 개별 승인 제외.', refs,
                [row['reviewer_paraphrase'], '원문 안내와 현행 지정 조문을 구분하고 선택 경로·경계일·연간 금액을 해당 버전으로 고정했다.'])

    followup = read(OUT / 'policy_hold_followup_20261028.json')
    final_followup = read(OUT / 'policy_final_followup_decisions_20261028.json')
    team_completion = read(OUT / 'team_completion_adjudication_20261028.json')
    followup['wording_updates'].update(final_followup['wording_updates'])
    followup['wording_updates'].update(team_completion['wording_updates'])
    for pid, item in followup['wording_updates'].items():
        previous = approvals.get(pid)
        refs = [web_reference(url, OUT / item['capture_file']) for url in item['source_urls']]
        for ref in refs:
            if item['capture_file'] in ['team_completion_browser_evidence_20261028.json', 'team_final_interpretive_evidence_20261028.json']:
                ref.update(capture_kind='reviewer_transcription_of_browser_accessibility_output',
                           hash_scope='saved reviewer transcription, not origin HTML bytes')
        for sid in item.get('supplemental_source_ids', []):
            refs.append(reference(au['sources'][sid]))
        for ref in item.get('additional_source_files', []):
            refs.append(dict(ref, sha256=sha((ROOT / ref['source_file']).read_bytes())))
        if previous:
            refs = previous['source_references'] + refs
        approve(pid, item['text'], item['scope'], refs, item['findings'])
        approvals[pid]['version'] = 'wording-v3-20261028'
        approvals[pid]['supersedes_text_sha256'] = previous['reviewed_policy_text_sha256'] if previous else None
        if pid in final_followup['wording_updates']:
            approvals[pid]['version'] = 'wording-v4-20261028'
            approvals[pid]['excluded_scope_issue'] = final_followup['remaining_scope_issues'][pid]
        if pid in team_completion['wording_updates']:
            approvals[pid]['version'] = 'wording-v5-20261028'
            approvals[pid].pop('excluded_scope_issue', None)
            approvals[pid]['completion_findings'] = item['findings']
            if item.get('interpretation_type'):
                approvals[pid]['legal_basis_type'] = item['interpretation_type']
                approvals[pid]['new_agency_ruling_obtained'] = False
    for pid, item in followup['remaining_dispositions'].items():
        if pid in final_followup['wording_updates'] or pid in team_completion['wording_updates']:
            continue
        assert pid not in approvals
        decisions[pid].update(item)
        if pid in final_followup['remaining_policy_ids']:
            decisions[pid].update(final_followup_source_access=final_followup['source_access_results'],
                batch_disposition='unapproved_pending_external_primary_verification',
                excluded_from_service_use=True,
                followup_source_capture='data/processed/legal_review/final14_primary_access_20261028.json')

    for pid, row in approvals.items():
        decisions[pid] = dict(policy_id=pid, country=original[pid]['country'],
            decision='approved_bounded_wording', status='approved_bounded_content_version',
            approved_version=row['version'], approved_text_sha256=row['reviewed_policy_text_sha256'],
            reason='고정한 문구·적용 범위·공식 원문·예외를 대조한 프로젝트 내부 문구 승인.',
            legal_validation_approved=True, reviewed_at=DATE)
    assert set(decisions) == set(original), (set(original) - set(decisions))
    countries = {}
    for country in sorted({p['country'] for p in original.values()}):
        total = sum(p['country'] == country for p in original.values())
        count = sum(original[pid]['country'] == country for pid in approvals)
        countries[country] = dict(total=total, approved=count, not_approved=total-count,
                                  approval_percent=round(count/total*100, 2))
    summary = dict(policy_total=590, batch_decisions_recorded=590,
        batch_decision_recording_percent=100,
        policy_content_versions_approved=len(approvals),
        policy_content_not_approved=590-len(approvals),
        final_legal_validation_percent=round(len(approvals)/590*100, 2),
        australia_policy_total=223, australia_content_approval_percent=countries['australia']['approval_percent'],
        countries=countries, queue_counts=dict(Counter(r['status'] for r in decisions.values())),
        historical_notice_excluded=sum(r.get('lifecycle_disposition') == 'historical_notice_excluded' for r in decisions.values()),
        active_legal_holds=sum(not r['legal_validation_approved'] and r.get('lifecycle_disposition') != 'historical_notice_excluded' for r in decisions.values()),
        additional_excluded_scope_issues=team_completion['additional_excluded_scope_issues'],
        internal_content_review_complete=team_completion.get('internal_content_review_complete', False),
        interpretations_not_agency_rulings=team_completion.get('interpretations_not_agency_rulings', []),
        lawyer_signed=0, service_release_approved=0, database_changed=False, embedding_run=False,
        definition='590 decisions recorded is not 590 substantive approvals or 100% legal validation.')
    registry = dict(reviewed_at=DATE, input_sha256=SNAPSHOT_SHA,
        policies=approvals, review_queue=decisions,
        definition=age['definition'], criteria=age['criteria'], summary=summary)
    ledger = dict(reviewed_at=DATE, input_sha256=SNAPSHOT_SHA, summary=summary,
        review_method='Fixed-snapshot substantive reviewer decisions; source checks are necessary but not sufficient; no automatic approval for availability or missing issue IDs.',
        source_collection_summary=dict(attempted=len(collected), captured=len(fresh),
            failed=len(collected)-len(fresh)), decisions=decisions)
    return registry, ledger


def main(check=False):
    registry, ledger = build()
    if check:
        assert read(MASTER) == registry
        assert read(LEDGER) == ledger
    else:
        save(MASTER, registry)
        save(LEDGER, ledger)
        p = ROOT / 'docs/legal_review/progress_20261028.json'
        progress = read(p)
        progress.update(stage='global_wording_batch_decided_with_explicit_holds',
            final_legal_validation_completed=registry['summary']['policy_content_versions_approved'],
            final_legal_validation_percent=registry['summary']['final_legal_validation_percent'],
            final_legal_validation_registry=MASTER.relative_to(ROOT).as_posix(),
            policy_content_approval=registry['summary'], global_policy_wording_batch=ledger['summary'],
            database_changed=False)
        receipt_path = ROOT / 'docs/legal_review/db_review_update_20261028.json'
        if receipt_path.exists():
            receipt = read(receipt_path)
            if receipt.get('registry_sha256') == sha(MASTER.read_bytes()) and receipt.get('mode') == 'applied_and_verified':
                progress.update(database_changed=True, database_review_metadata_update=receipt,
                                stage=('internal_wording_review_completed_and_saved_to_db'
                                    if registry['summary']['active_legal_holds'] == 0
                                    else 'bounded_wording_review_saved_to_db_with_explicit_holds'))
        save(p, progress)
        report = ['# 590개 정책 문구 일괄 판정 — 2026-10-28', '',
            '**590개 모두 판정 기록을 작성했다. 이는 전부 승인되었다는 뜻이 아니다.**', '',
            '| 국가 | 전체 | 문구 승인 | 미승인 | 승인율 |', '|---|---:|---:|---:|---:|']
        for country, row in registry['summary']['countries'].items():
            report.append(f"| {country} | {row['total']} | {row['approved']} | {row['not_approved']} | {row['approval_percent']}% |")
        report += ['', f"총 승인 **{len(registry['policies'])}/590 ({registry['summary']['final_legal_validation_percent']}%)**. 미승인은 아래 사유별 후속 작업을 완료해야 한다.", '',
            '승인은 Codex의 프로젝트 내부 정책 문구·버전 검증이다. 독립 변호사 서명, 정부 사증 승인, 특정인 자격 승인과 구분한다. 이 생성기는 DB를 변경하지 않는다. 별도 DB 검토 버전 저장 결과는 db_review_update_20261028.json을 확인한다. 원본 문구·서비스 허용·임베딩은 유지한다.', '',
            '## 반영한 주요 수정', '',
            '- 호주 491 Values Statement: 안내문의 18세를 법령의 16세 기준으로 대체.',
            '- 호주 462: Philippines가 빠진 30개국 목록을 현행 31개국 법령 표로 대체. 국가별 학력 조건과 정부 지원 면제국도 별도 보존.',
            '- 일본: 141개 PDF 행의 신청 유형·기관/학교 분류·국적 열·조건부 기호·행 묶음 조건을 그대로 보존. 제출자료 요구를 실체 자격 승인으로 확대하지 않음.',
            '- 미국: J-1 호스트 방문 AND/OR 및 평가의 6개월 경계 등을 수정 버전에 반영. 법원 명령·과거 모집 공고·현행 1차 대조 미완료는 보류.',
            '- 독일: Blue Card 학위 취득 후 정확히 3년의 경계, 언어 조건 예외 및 2026년 금액의 범위를 명시.', '',
            '- 캐나다: 원본 NULL은 유지. 후속 IRCC 업무 지침에서 P3 날짜 경계와 언어·전공 경과조치를 확인해 v3 문구로 보완.',
            '- 호주 482: LIN 25/082 새 시험은 점수 증거 제공일 기준 3년, 시행 전 시험의 경과 경로는 신청일 직전 3년으로 분리. Specialist 레코드의 후원 대가 금지와 영어를 함께 대체.',
            '- 호주 500: 영어의 신청 시 증빙/미제출 분기, 가족 신청·재신청의 2026-10-02 규정 및 법정 예외를 대체 문구로 고정.', '',
            '웹 도구 본문을 저장한 증거와 원본 HTML/PDF 다운로드를 구분한다. 웹 결과 파일 해시는 원본 서버 바이트와 같다는 뜻이 아니다. 법령 통합본의 현행 기준일·별도 법원 효력 제한은 각 근거와 승인 범위를 따른다.', '',
            '## 현행 승인 외 자료의 보관·후속 판정', '',
            f"과거 공고 보관 {registry['summary']['historical_notice_excluded']}개, 내부 문구 보류 {registry['summary']['active_legal_holds']}개. 검토자의 해석은 기관의 새 회신과 구분한다.", '']
        for pid, row in ledger['decisions'].items():
            if not row['legal_validation_approved']:
                report.append(f"- **{pid}** — {row['reason']}")
        report += ['', '## 재현·검증', '', '```powershell',
            '.venv\\Scripts\\python.exe scripts/ingest/australia/finalize_age_policy_review.py --check',
            '.venv\\Scripts\\python.exe scripts/ingest/common/legal_review/finalize_global_policy_wording.py --check',
            '.venv\\Scripts\\python.exe scripts/evaluate/legal_review/audit_policy_content_approvals.py', '```', '']
        (ROOT / 'docs/legal_review/global_policy_wording_decisions_20261028.md').write_text('\n'.join(report), encoding='utf-8')
    print(json.dumps(registry['summary'], ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    main(parser.parse_args().check)

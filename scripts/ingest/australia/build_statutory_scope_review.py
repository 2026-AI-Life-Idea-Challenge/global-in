"""Build dated Australian statutory scope records without altering policy drafts.

Requires the official HTML collected by collect_australia_statutory_sources.ps1.
References carry document and normalized clause hashes; notes are paraphrases.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'data/processed/legal_review'
DATE = '2026-10-28'
TARGET = OUT/'australia_statutory_scope_20261028.json'
SUPPLEMENT = OUT/'australia_evidence_supplement_20261028.json'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def normalize(value):
    return ' '.join(value.split())


# Explicit policy-to-provision routes. Schedule 1 routes use a v1: prefix.
ROUTES = {
 'AU_186_DE': ['186.234','186.234','186.211','186.234','186.233','186.231','186.235','186.213','186.213','186.232','186.213','186.214'],
 'AU_186_LA': ['186.243','186.211','186.242','186.241','186.243','186.244','186.213','186.213','186.213','186.214'],
 'AU_186_TRT': ['186.225','186.227','186.211','186.223','186.223','186.221','186.222','186.226','186.224','186.213','186.213','186.213','186.214'],
 'AU_189_PT': ['v1:1137','189.221','189.222','v1:1137','189.224','189.223','189.222','189.225','189.211','189.211','189.211','189.212'],
 'AU_190': ['v1:1138','190.211','190.215','190.212','v1:1138','190.214','190.213','190.212','190.216','190.216','190.216','190.216'],
 'AU_191_REGIONAL_PROVISIONAL': ['v1:1139','191.222','191.211','191.211','191.211','191.211'],
 'AU_407': ['v1:1238','v1:1238','407.211','v1:1238','407.219A','407.219A','407.216','407.217','407.212','407.219A','407.219A','407.219B','407.219A'],
 'AU_482_CORE': ['v1:1240','v1:1240','482.211','482.212','482.233','482.231','482.231','482.231','482.214','482.217','482.217','482.213','482.232','482.218','482.217','482.217'],
 'AU_482_SPECIALIST': ['v1:1240','v1:1240','482.211','482.212','482.223','482.221','482.221','482.221','482.214','482.217','482.217','482.213','482.218','482.217','482.217'],
 'AU_482_LA': ['482.241','482.242','482.212','482.217','482.217','482.243','482.217','482.214','482.217','482.218'],
 'AU_491': ['491.213','491.217','v1:1241','491.214','491.216','491.215','491.214','491.211','491.211','491.211','491.211'],
 'AU_494_EMPLOYER_SPONSORED': ['494.223','494.213','494.225','494.224','494.226','494.221','494.211','494.211','494.211'],
 'AU_494_LABOUR_AGREEMENT': ['494.232','494.233','494.235','494.235','494.234','494.231','494.211','494.211','494.211'],
 'AU_500': ['500.216','500.211','500.217','500.213','500.215','v1:1222','v1:1222','v1:1222','500.214','500.212','500.217','500.217','500.217','500.217','500.218','500.217'],
 'AU_417_FIRST': ['v1:1225','v1:1225','v1:1225','417.211','417.221','417.221','417.221','417.221','417.221'],
 'AU_417_SECOND': ['v1:1225','v1:1225','417.211','417.211','v1:1225','417.221','417.221','417.221','417.221','417.221'],
 'AU_417_THIRD': ['v1:1225','v1:1225','417.211','417.211','v1:1225','417.221','417.221','417.221','417.221','417.221'],
 'AU_462_FIRST': ['v1:1224A','v1:1224A','v1:1224A','462.216','462.215','462.213','462.217','462.221','462.221','462.221','462.221','462.221'],
 'AU_462_SECOND': ['v1:1224A','v1:1224A','462.217','462.218','v1:1224A','462.221','462.221','462.221','462.221'],
 'AU_462_THIRD': ['v1:1224A','v1:1224A','462.217','462.219','v1:1224A','462.221','462.221','462.221','462.221'],
}

# Rule notes describe reviewed scope, not an exhaustive eligibility determination.
RULES = {
 'health': dict(note='비자·스트림별 PIC 4005/4007을 구분한다. 4007(2)의 재량 면제는 비용·서비스 접근 요건에 한정되고 결핵·공중보건 요건 전체를 면제하지 않는다. 호주 출생·통상 거주 미성년자의 비용 관련 예외도 별도다.', sources=['regulations_volume3']),
 'character': dict(note='경찰 증명 안내의 16세 기준과 법적 인성 요건 자체를 구분한다. PIC 4001과 Migration Act s501의 인성 심사·재량 거절·의무 취소를 구분한다. 범죄 기록 외 사유와 형량 합산·판결 취소 규정도 있어 단순 전과 유무로 자동 판정하지 않는다.', sources=['regulations_volume3','act_volume2']),
 'debt': dict(note='PIC 4004는 정부 채무가 없거나 상환을 위한 적절한 조치를 마련한 경우를 포함한다. 반드시 전액 선납해야 한다고 축약하지 않는다. 비동반 가족에 대한 범위는 해당 비자 조문을 따른다.', sources=['regulations_volume3']),
 'values': dict(note='PIC 4019 및 Schedule 4 Part 3의 선언·확인 방식과 각 비자의 16세/18세 적용 기준을 함께 보존한다. 모든 비자에 동일 연령을 적용하지 않는다.', sources=['regulations_volume3']),
 'history': dict(note='과거 거절·취소만으로 모든 신청이 자동 금지되는 것은 아니다. s48은 호주 내 위치·실체 비자 미보유·최근 입국 후의 해당 거절/취소 등을 함께 따진다. reg2.12의 허용 class에는 190·491·494 경로가 포함되지만 나머지 신청·승인 요건도 필요하다. 인성 관련 s501E 금지와 PIC 4013/4014·특별 재입국 기준은 별도다.', sources=['act_volume1','act_volume2','regulations_volume1','regulations_volume3']),
 'insurance': dict(note='건강 심사 통과와 전 체류 기간의 적절한 의료보험은 별도다. 주신청자·동반가족, 비자 조건 8501 및 해당 제도의 보험 예외를 함께 확인한다.', sources=['regulations_volume3']),
 'points': dict(note='65점은 법정 통과점이며 초청을 보장하지 않는다. 실제 심사 점수는 초청장 기재 점수 이상이어야 한다. 초청 시 연령·영어·기술심사와 주정부 지명/가족 후원 경로를 구분한다.', sources=['points_pass_mark','skilled_occupations','english_levels_2025']),
 'employer_exemptions': dict(note='LIN 19/216의 면제는 스트림·요건별 지정 대상에게만 적용한다. 학술·과학·의료·고소득·444/461 경력의 정의와 기간을 함께 검토한다. legacy 457의 신청 마감 2024-06-30을 현행 신규 신청 면제로 재사용하지 않는다.', sources=['exemptions_186_494']),
 'labour_agreement': dict(note='노동협약 경로의 연령·영어·경력·기술심사 양허는 실제 체결된 협약의 대상 직종·기준·기간에 달려 있다. 다른 스트림의 일반 요건 또는 면제를 일괄 복사하지 않는다. 개별 협약이 없는 상태에서 양허를 확정하지 않는다.', sources=['regulations_volume2']),
 'sid': dict(note='2024-12-07 전후 지명일·비자 신청일을 분리한다. Schedule 13 Part 145는 미사용 TSS 지명의 SID 전환과 기존 8607 조건 보존을 구분한다. 새 급여 기준은 지명·인덱싱 기준일을 확인하고 현재 값으로 과거 신청을 재심사하지 않는다.', sources=['sid_reform_2024','regulations_volume1','regulations_volume3']),
 'sid_english': dict(note='Core/Specialist는 LIN 25/082의 면제와 시험일별 표를 적용한다. 2025-09-13 이후 제6조는 증거 제출일 전 3년을 기준으로 하고 재응시 규정을 포함한다. 이전 시험은 제7조의 신청일 전 3년·단일 응시 기준이다. Labour Agreement 영어는 실제 협약 기준이다.', sources=['english_482_2025']),
 'training': dict(note='2026-03-11 이후 신청은 신청 전에 승인된 temporary activities sponsor와 유효한 지명 승인이 필요하다. Commonwealth agency의 지명 예외를 보존한다. 이전 신청에 새 신청 유효성 조건을 일괄 소급하지 않는다.', sources=['training_reform_2026','regulations_volume1']),
 'student': dict(note='2026-10-02 이후 신규 신청은 Schedule 1의 신청 유효성·위치·가족 허용 범위와 Schedule 2의 승인 요건을 분리한다. 기존 비자 효력, 시행 전 신청 및 시행 후 신규 신청을 혼합하지 않는다.', sources=['student_reform_2026','student_classes']),
 'student_location': dict(note='호주 내 신청 가능한 비자 보유 여부와 기존 학생비자 소지자의 재신청 예외를 순서대로 확인한다. 박사·학교·DFAT/Defence·provider default·동일 과정 추가 12개월·상위 과정 진학은 각각 요건이 다르다. 진학은 원칙적으로 추가 과정 1개 및 AQF·교육기관 요건을 확인한다.', sources=['student_classes','student_reform_2026']),
 'student_family': dict(note='가족 신청은 본인 재신청 면제와 별개다. 정부 후원·지정 여권·외국 정부 전액 장학·박사·provider default·과정 마무리·기존 부신청자·호주 출생 자녀의 각 조건을 구분한다. 같은 시점의 결합 신청 요건도 해당 범주별 확인한다.', sources=['student_classes','student_reform_2026']),
 'student_english': dict(note='영어 증명 요청 여부와 LIN 25/090의 명시적 증거 면제를 구분한다. 시험일, 신청일, ELICOS 기간 및 지정 pathway 과정을 함께 적용하며 모든 학생에게 동일 점수·면제를 적용하지 않는다.', sources=['english_500_2025']),
 'wh_age': dict(note='2026-07-01 이후 연령은 Schedule 1의 유효 신청 요건이다. 417은 여권별 30/35세를 적용하며 한국 여권은 35세까지다. 462의 LIN 26/072 Schedule 1은 열거된 여권국 모두 상한 30세다. 현지 생일이 아니라 신청 접수 시 호주 기준 날짜를 구분한다.', sources=['wh_age_reform_2026','wh_417_arrangements','wh_462_arrangements']),
 'wh_work': dict(note='두 번째/세 번째 비자의 지정 근무는 3/6개월 및 인정 비자·근무일·지역·업종·보수 기준을 함께 확인한다. 영국 여권의 417 면제는 2024-07-01 이후 해당 여권으로 신청한 경우이며 462에 전용하지 않는다. 종료된 COVID 신청 창구와 일반 신규 신청도 구분한다.', sources=['wh_uk_exemption_2024','specified_work_417','specified_work_462','regulations_volume2']),
 'regional': dict(note='191은 적격 지역 임시비자 보유기간, 지역 조건 준수 및 3개 과세연도 ATO 자료를 구분한다. 현재 안내의 최저 소득 없음과 191.222(3)의 위임 근거를 함께 기록하고 494의 지명 급여 하한을 191에 옮기지 않는다.', sources=['regulations_volume1','regulations_volume2']),
 'skills': dict(note='학위·경력, 직업 면허 및 이민용 기술심사는 서로 별도다. 지정 직종 코드·평가기관·심사 유효기간·평가 시점·국적별 의무 심사와 명시적 면제만 적용한다. 호주 졸업만으로 일률 면제하지 않는다.', sources=['skilled_occupations','mandatory_skills_482','occupations_186','occupations_482','occupations_494']),
}


class Sources:
    def __init__(self):
        manifest = json.loads((OUT/'australia_source_manifest_20261028.json').read_text(encoding='utf-8-sig'))
        self.rows, self.soups, self.evidence, self.texts = {}, {}, {}, {}
        for row in manifest:
            assert row['status'] == 'downloaded', row
            raw = (ROOT/row['source_file']).read_bytes()
            assert digest(raw) == row['sha256'], row['source_id']
            soup = BeautifulSoup(raw, 'html.parser')
            text = normalize(soup.get_text(' ', strip=True))
            assert 'Table of contents Enter text to search' not in text, row['source_id']
            assert len(text) > 900, row['source_id']
            self.rows[row['source_id']] = row
            self.soups[row['source_id']] = soup

    def clause(self, source_id, key):
        evidence_id = source_id+':'+key
        if evidence_id in self.evidence:
            return evidence_id
        soup = self.soups[source_id]
        candidates = []
        for node in soup.find_all(['p','h1','h2','h3','h4','h5','h6']):
            text = normalize(node.get_text(' ', strip=True))
            classes = ' '.join(node.get('class', []))
            if (text == key or text.startswith(key+' ')) and ('Head' in classes or node.name.startswith('h')):
                candidates.append(node)
        if not candidates:
            candidates = [node for node in soup.find_all('p')
                          if (normalize(node.get_text(' ',strip=True)) == key or
                              normalize(node.get_text(' ',strip=True)).startswith(key+' '))
                          and 'TOC' not in ' '.join(node.get('class', []))]
        assert candidates, (source_id, key)
        node = candidates[-1]
        parts = [normalize(node.get_text(' ', strip=True))]
        for sibling in node.find_next_siblings():
            classes = ' '.join(sibling.get('class', []))
            sibling_text = normalize(sibling.get_text(' ',strip=True))
            is_heading = 'Head' in classes or sibling.name in ['h1','h2','h3','h4','h5','h6']
            if is_heading and re.match(r'^(\d|Part\b|Schedule\b|Subclass\b|Division\b)', sibling_text):
                break
            if re.match(r'^\d{4}(?:\s|$)', sibling_text):
                break
            parts.append(normalize(sibling.get_text(' ', strip=True)))
        text = normalize(' '.join(parts))
        assert len(text) > len(key)+8, (source_id, key, text)
        anchor = node.get('id') or next((a.get('id') for a in node.find_all('a') if a.get('id')), None)
        row = self.rows[source_id]
        self.texts[evidence_id] = text
        self.evidence[evidence_id] = dict(source_id=source_id, provision=key, anchor=anchor,
            source_url=(row.get('resolved_source_url') or row['source_url'])+('#'+anchor if anchor else ''),
            source_file=row['source_file'], source_sha256=row['sha256'],
            normalized_clause_sha256=digest(text.encode()), normalized_clause_characters=len(text),
            extraction='provision heading plus siblings through unnumbered subheadings, ending at next numbered/structural heading; hash is normalized text')
        return evidence_id


def policy_key(pid):
    if pid.startswith('AU_482_LA_'):
        return 'AU_482_LA', int(pid.split('_')[3])
    prefix, number = pid.rsplit('_POL_', 1)
    return prefix, int(number)


def classify(policy):
    header = policy['policy_text'].splitlines()[0].lower()
    if 'health' in header and 'insurance' not in header:
        return 'health'
    if 'character' in header:
        return 'character'
    if 'debt' in header:
        return 'debt'
    if 'values' in header:
        return 'values'
    if 'cancelled' in header or 'refused' in header:
        return 'history'
    if 'insurance' in header:
        return 'insurance'
    if any(word in header for word in ['skills','experience','qualifications','assessment','occupation','licensing']):
        return 'skills'
    return None


def main(check=False):
    raw = (OUT/'inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    snapshot = json.loads(raw)
    policies = {p['policy_id']:p for p in snapshot['policy_candidates'] if p['policy_id'].startswith('AU_')}
    old = json.loads((ROOT/'docs/legal_review/australia_policy_review_20261028.json').read_text(encoding='utf-8'))
    previous = {p['policy_id']:p for p in old['policy_reviews']}
    assert set(policies) == set(previous) and len(policies) == 223
    sources = Sources()
    capture_path = ROOT/'data/raw/legal_review/20261028/australia/189_rendered_sections.json'
    capture_raw = capture_path.read_bytes()
    capture = json.loads(capture_raw)
    captured = {}
    for pid, text in capture['sections'].items():
        sha = digest(text.encode())
        assert sha.startswith(previous[pid]['current_section_fingerprint']), pid
        captured[pid] = dict(evidence_id='AU_189_RECAPTURE_'+pid.rsplit('_',1)[1]+'_20261028',
            policy_id=pid, source_url=capture['source_url'], source_file=capture_path.relative_to(ROOT).as_posix(),
            source_file_sha256=digest(capture_raw), normalized_section_sha256=sha,
            source_text=text, text_kind='normalized_rendered_official_page_text',
            captured_at=DATE, capture_method=capture['capture_method'], original_evidence_replaced=False)
    records = {}
    programs = {}
    for pid, policy in sorted(policies.items()):
        prefix, number = policy_key(pid)
        route = ROUTES[prefix][number-1]
        source_id, clause = ('regulations_volume1', route[3:]) if route.startswith('v1:') else ('regulations_volume2', route)
        refs = [sources.clause(source_id, clause)]
        rules = []
        category = classify(policy)
        if category:
            rules.append(category)
        if prefix in ['AU_189_PT','AU_190','AU_491']:
            rules.append('points')
        if prefix in ['AU_186_DE','AU_186_TRT','AU_494_EMPLOYER_SPONSORED']:
            rules.append('employer_exemptions')
        if prefix in ['AU_186_LA','AU_482_LA','AU_494_LABOUR_AGREEMENT']:
            rules.append('labour_agreement')
        if prefix.startswith('AU_482') or prefix == 'AU_186_TRT':
            rules.append('sid')
        if pid == 'AU_482_CORE_POL_13' or pid == 'AU_482_SPECIALIST_POL_12':
            rules.append('sid_english')
            refs.append(sources.clause('regulations_volume2', '482.222' if 'SPECIALIST' in pid else '482.232'))
        if prefix == 'AU_407':
            rules.append('training')
        if prefix == 'AU_500':
            rules.append('student')
            if number in [6,7]:
                rules.append('student_location')
            if number == 8:
                rules.append('student_family')
            if number == 4:
                rules.append('student_english')
        if prefix.startswith(('AU_417','AU_462')):
            rules.append('wh_age')
            if number == 4 and not prefix.endswith('FIRST'):
                rules.append('wh_work')
        if prefix == 'AU_191_REGIONAL_PROVISIONAL':
            rules.append('regional')
            if number == 2:
                refs.append(sources.clause('regulations_volume2','191.221'))
        # Common public-interest rules are linked to the actual subclass route,
        # not treated as a replacement for that subclass's family/age limits.
        if category == 'health':
            health = ('4007' if prefix in ['AU_186_TRT','AU_191_REGIONAL_PROVISIONAL','AU_494_EMPLOYER_SPONSORED'] or prefix.startswith('AU_482') else '4005')
            refs.append(sources.clause('regulations_volume3', health))
            if prefix == 'AU_500':
                refs.append(sources.clause('regulations_volume3','4007'))
            assert health in sources.texts[refs[0]], ('Health route lacks applicable PIC', pid)
        if category in ['debt','values','character']:
            refs.append(sources.clause('regulations_volume3', {'debt':'4004','values':'4019','character':'4001'}[category]))
            assert {'debt':'4004','values':'4019','character':'4001'}[category] in sources.texts[refs[0]], ('Common PIC route mismatch',pid)
        if category == 'character':
            refs.append(sources.clause('act_volume2','501'))
        if category == 'history':
            refs += [sources.clause('act_volume1','48'), sources.clause('regulations_volume1','2.12'), sources.clause('act_volume2','501E')]
        if pid in ['AU_186_DE_POL_06','AU_186_TRT_POL_06','AU_494_EMPLOYER_SPONSORED_POL_01']:
            refs.append(sources.clause('exemptions_186_494', '8' if '494' in pid else '6'))
        if prefix.startswith(('AU_417','AU_462')) and 'Be this age' in policy['policy_text']:
            refs.append(sources.clause('wh_age_reform_2026','2'))
        program = previous[pid]['program']
        programs.setdefault(program, dict(policy_ids=[], prefix=prefix, pending_items=[]))['policy_ids'].append(pid)
        records[pid] = dict(policy_id=pid, program=program, original_policy_text_sha256=digest(policy['policy_text'].encode()),
            original_source_evidence_ids=policy['source_evidence_ids'], original_text_changed=False,
            primary_provision_route=refs[0], statutory_evidence_refs=refs, scope_rule_ids=sorted(set(rules)),
            comparison_status='statutory_route_and_scope_notes_recorded_not_final_approval',
            reviewed_policy_text=' '.join(RULES[k]['note'] for k in dict.fromkeys(rules)) or
                '해당 비자 조문과 신청 유효성 요건을 구분해 원문 조건을 보존한다. 세부 적용 시점과 개별 사정은 최종 심사 대상으로 남긴다.',
            text_kind='reviewer_paraphrase_not_source_quote', final_legal_validation_completed=False,
            approved_for_user_answers=False, approved_for_embedding=False, approved_for_eligibility_decision=False,
            database_applied=False)
        if pid in captured:
            records[pid]['supplemental_evidence_id'] = captured[pid]['evidence_id']
        if pid == 'AU_189_PT_POL_03':
            records[pid]['reviewed_policy_text'] += ' 현행 공식 안내는 Thapa [2021] FCCA 686에 따라 60일 초청 유효기간 중 취득한 적합한 심사도 수용한다고 명시한다. 조문만으로 초청일 이전 취득을 절대 요건으로 단정하지 않는다. 판결 1차 원문과 후속 효력은 별도 확인 대상으로 남긴다.'
    assert len(programs) == 20
    # Read together: adjacent subordinate criteria and transitional provisions.
    provisions = {
        'regulations_volume1':['1.15C','2.72','2.72C','5.19','5.42A','1222','1238','1224A','1225','1240','1241'],
        'regulations_volume3':['4004','4005','4007','4019','8105','8501','8547','8579','8607','14502','14503','16001','16301','16401','16402','16601'],
        'english_482_2025':['6','7','8'], 'exemptions_186_494':['5','6','8','13'],
        'student_classes':['16','17','18','19','20','21','22','23','24'],
        'wh_417_arrangements':['7','8','9'], 'points_pass_mark':['6'],
        'wh_462_arrangements':['7','8','9'],
        'english_500_2025':['6','7','8','9'],
        'english_levels_2025':['7','10','11'],
        'mandatory_skills_482':['5','6','7','8'],
        'specified_work_417':['5','6','7','8','8A','9','10'],
        'specified_work_462':['5','6','7','8','9','9A','10','11'],
        'occupations_186':['6','8','9','10','11','12'],
        'occupations_482':['6'], 'occupations_494':['5'],
        'act_volume1':['48','245AR','245AS'], 'act_volume2':['501','501E'],
    }
    for source_id, keys in provisions.items():
        for key in keys:
            sources.clause(source_id, key)
    # Checks include exception tails that a premature heading boundary loses.
    assert 'Recent assessments' in sources.texts['regulations_volume2:494.224']
    assert 'Subclass 444/461 workers' in sources.texts['exemptions_186_494:6']
    assert 'evidence' in sources.texts['english_482_2025:6']
    assert 'not more than 3 years' in sources.texts['english_482_2025:6']
    assert 'undue cost' in sources.texts['regulations_volume3:4007']
    ages = {}
    for row in sources.soups['wh_417_arrangements'].find_all('tr'):
        cells = [normalize(c.get_text(' ',strip=True)) for c in row.find_all(['td','th'],recursive=False)]
        if len(cells) == 4 and cells[0].isdigit():
            ages[cells[1]] = 30 if cells[3] == '30' else 35
    assert len(ages) == 19 and ages['Republic of Korea'] == 35 and ages['Japan'] == 30
    age_462_rows = []
    for row in sources.soups['wh_462_arrangements'].find_all('tr'):
        cells = [normalize(c.get_text(' ',strip=True)) for c in row.find_all(['td','th'],recursive=False)]
        if len(cells) == 4 and cells[0].isdigit():
            age_462_rows.append(cells)
    assert len(age_462_rows) == 31 and all(c[-1] == '30' for c in age_462_rows)
    boundary_checks = dict(wh_417_passport_rows=19, wh_462_passport_rows=31,
        korea_417_upper_age=35, japan_417_upper_age=30, all_listed_462_upper_age=30,
        training_reform_commencement='2026-03-11', student_reform_commencement='2026-10-02',
        sid_transition_commencement='2024-12-07', wh_age_application_rule_commencement='2026-07-01',
        policy_routes_with_common_pic_semantically_checked=sum(classify(p) in ['health','debt','values','character'] for p in policies.values()))
    holds = {
        'ACT_CHARACTER_HISTORY': dict(reason='공통 s48·s501·s501E 및 reg2.12의 class별 범위는 확인했다. 개인별 입국·보유 비자·거절/취소 근거·형량·재량의 최종 적용에는 사건 자료가 필요하다.', policies=[p for p,r in records.items() if any(k in r['scope_rule_ids'] for k in ['character','history'])]),
        'AGREEMENT_TEXT': dict(reason='개별 노동협약 원문이 없으므로 직종별 양허를 확정하지 않음', policies=[p for p,r in records.items() if 'labour_agreement' in r['scope_rule_ids']]),
        'STATE_NOMINATION': dict(reason='주/준주별 지명 기준과 신청 기간은 연방 기준과 별도. 모든 지역의 2026년 운영 요건 검증은 이번 범위에서 미완료', policies=[p for p in records if p.startswith(('AU_190_','AU_491_'))]),
        'INDIVIDUAL_OCCUPATION': dict(reason='직종별 caveat·국적·평가기관·지역 우편번호를 전체 행 단위로 최종 승인하지 않음', policies=[p for p,r in records.items() if any(k in r['scope_rule_ids'] for k in ['skills','wh_work'])]),
        'THAPA_PRIMARY_JUDGMENT': dict(reason='189 현행 공식 안내의 60일 초청 기간 내 기술심사 수용을 기록했다. Thapa [2021] FCCA 686 판결의 1차 원문·후속 효력 검토는 완료하지 못했으므로 조문과 안내의 시점 차이를 최종 해소하지 않음', policies=['AU_189_PT_POL_03']),
        'GUIDANCE_LAW_TIMING': dict(reason='482 영어 시험 유효기간의 안내상 신청일 표현과 LIN 25/082 s6(2)(c)의 증거 제출일 표현을 구분. 실제 시험·제출일 확인 필요', policies=['AU_482_CORE_POL_13','AU_482_SPECIALIST_POL_12']),
    }
    for pid, record in records.items():
        record['pending_issue_ids'] = [key for key, hold in holds.items() if pid in hold['policies']]
        record['pending_items'] = ['최종 개별 적용·효력·원문 증거 승인 미완료']
    for program in programs.values():
        program['policy_count'] = len(program['policy_ids'])
        program['scope_rule_ids'] = sorted({k for p in program['policy_ids'] for k in records[p]['scope_rule_ids']})
        program['pending_items'] = sorted({k for p in program['policy_ids'] for k in records[p]['pending_issue_ids']})
        program['statutory_scope_recorded'] = True
        program['final_legal_validation_completed'] = False
    result = dict(reviewed_at=DATE, input_sha256=digest(raw), sources=sources.rows,
        evidence=sources.evidence, rules=RULES, programs=programs, policies=records, unresolved_issues=holds,
        boundary_checks=boundary_checks, passport_age_matrix_417=ages,
        resolved_issues=dict(AU_189_SOURCE_DETAIL=dict(status='four_rendered_sections_recaptured_and_linked', policy_ids=sorted(captured),
            original_policy_text_changed=False, original_evidence_replaced=False, final_legal_approval=False)),
        summary=dict(program_total=20, program_scope_records=20, program_recording_percent=100,
            policy_total=223, policy_scope_records=223, policy_recording_percent=100,
            official_documents_archived=len(sources.rows), clause_anchors_recorded=len(sources.evidence),
            supplemental_source_sections_recaptured=len(captured),
            final_legal_validation_completed=0, final_legal_validation_percent=0, database_changed=False, embedding_run=False),
        limitation='정책-조문 경로는 명시적 매핑, 정책별 요약은 검토한 공통 규칙의 조합이다. 모든 223개 조건의 독립적인 최종 법률 검증 완료를 뜻하지 않는다.')
    if check:
        assert json.loads(TARGET.read_text(encoding='utf-8')) == result, 'Generated review is stale'
        assert json.loads(SUPPLEMENT.read_text(encoding='utf-8'))['policies'] == captured
    else:
        SUPPLEMENT.write_text(json.dumps(dict(reviewed_at=DATE, input_sha256=digest(raw), policies=captured,
            database_applied=False, approved_for_embedding=False), ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
        TARGET.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        progress_path = ROOT/'docs/legal_review/progress_20261028.json'
        progress = json.loads(progress_path.read_text(encoding='utf-8'))
        progress['australia_statutory_scope'] = result['summary']
        if 'australia_germany_followup' in progress:
            progress['australia_germany_followup'].update(australia_scope_notes=223, australia_statutory_pending=223,
                australia_statutory_pending_definition='final individual legal validation pending; common statutory scope records now exist for all 223')
        progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        followup_path = OUT/'australia_germany_followup_20261028.json'
        followup = json.loads(followup_path.read_text(encoding='utf-8'))
        followup['countries']['australia'].update(statutory_scope_records=223, programs_reviewed=20,
            newly_completed_statutory_reviews_definition='final legal approvals; scope-note recording is counted separately',
            pending_policy_ids_definition='final individual legal validation pending, not missing scope notes',
            next_action='공통 법령·면제·경과조치 기록 및 189 본문 4개 보완 완료. unresolved_issues의 협약·주정부·직종·판결·실제 적용 시점을 보완한 뒤 최종 승인.')
        followup_path.write_text(json.dumps(followup, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    main(check=parser.parse_args().check)

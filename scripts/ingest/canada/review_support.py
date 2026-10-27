"""Attach dated official-source desk review; never synthesize original quotes or approvals."""
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEW_DATE = '2026-10-28'
BASE = 'https://www.canada.ca/en/immigration-refugees-citizenship/services/'
LAW = 'https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/section-'
SOURCES = {
    'pgwp': BASE + 'study-canada/work/after-graduation/eligibility.html',
    'pgwp_docs': BASE + 'study-canada/work/after-graduation/get-documents.html',
    'pgwp_apply': BASE + 'study-canada/work/after-graduation/apply.html',
    'pgwp_after': BASE + 'study-canada/work/after-graduation/after-you-apply.html',
    'pgwp_duration': BASE + 'study-canada/work/after-graduation/about.html',
    'cip': BASE + 'study-canada/work/after-graduation/eligibility/field-of-study.html',
    'study': BASE + 'study-canada/study-permit/eligibility.html',
    'finance': BASE + 'study-canada/study-permit/get-documents/financial-support.html',
    'study_conditions': BASE + 'study-canada/study-permit/while-you-study/study-permit-conditions.html',
    'change_school': BASE + 'study-canada/change-schools.html',
    'employer': BASE + 'work-canada/employer-specific.html',
    'imp': BASE + 'work-canada/hire-temporary-foreign/international-mobility-program/how-to-hire.html',
    'iec': BASE + 'work-canada/iec/eligibility.html?selection=kr-wh',
    'iec_arrival': BASE + 'work-canada/iec/prepare-arrival.html',
    'iec_family': BASE + 'work-canada/iec/eligibility/family-members.html',
    'iec_profile': BASE + 'work-canada/iec/become-candidate.html',
    'iec_apply': BASE + 'work-canada/iec/apply-work-permit.html',
    'r216': LAW + '216.html', 'r220': LAW + '220.html?txthl=issue',
    'r220_1': LAW + '220.1.html', 'r200': LAW + '200.html', 'r203': LAW + '203.html',
}

# Each summary is reviewer-authored, NOT an exact quotation or an executable rule.
SPECS = {
    'CA_PGWP_POL_01': (
        '적격 DLI·과정, 최소 과정기간, 전일제 이수와 마지막 학기 예외, 수료확인 후 180일 및 허가 유효성 조건을 함께 검토한다.',
        ['pgwp'], ['Quebec 900시간·특수사례 및 허가 유효기간의 실제 날짜 확인']),
    'CA_PGWP_POL_02': (
        '학위·기타 대학·비대학·비행학교 경로를 구분하며 DLI 졸업만으로 PGWP 자격이 보장되지는 않는다.',
        ['pgwp', 'pgwp_duration'], ['개별 학교·과정 적격 여부와 비행학교 경로 확인']),
    'CA_PGWP_POL_03': (
        '언어요건의 전환일은 PGWP 신청일이다. 학위·기타 대학은 CLB/NCLC 7, 비대학은 5를 기준으로 네 영역을 검토한다. 적격 비행학교 예외가 있다.',
        ['pgwp', 'pgwp_docs'], ['승인 시험 종류·2년 미만 유효성·장애에 따른 평균점수 절차 검토']),
    'CA_PGWP_POL_04': (
        '전공요건은 study permit 신청일·학위 예외·CIP 적용시점으로 구분한다. 학사·석사·박사 등 면제 경로를 먼저 확인한다.',
        ['pgwp', 'cip'], ['개별 CIP 코드와 과거 신청일별 적격 상태 확인; 표의 개수 일치는 승인 아님']),
    'CA_PGWP_POL_05': (
        '원격수업은 lock-in 날짜와 캐나다 내 대면수업 비율, 해외수학 기간 공제 및 과거 COVID 예외를 구분한다.',
        ['pgwp'], ['개인별 수업 시작일·신청 접수일·수학 위치와 기간 재구성']),
    'CA_PGWP_POL_06': (
        '단축과정·학교이전·휴학·기존 PGWP 및 공사립 제휴과정의 예외를 개별 검토한다.',
        ['pgwp', 'study_conditions'], ['주간 제휴과정의 2023-02-01 경계일이 안내 문구상 공백이므로 단정 금지; 승인휴학·기존허가 이력 확인']),
    'CA_PGWP_POL_07': (
        '신청·신분회복·대기 중 취업·허가기간을 구분한다. 신분회복 신청 중에는 취업을 자동 허용하지 않으며 기간은 학위·과정·여권에 좌우된다.',
        ['pgwp_apply', 'pgwp_after', 'pgwp_duration', 'pgwp_docs'], ['180일 신청기간과 90일 신분회복기간 별도 계산; 수수료 최신표; 대기취업 조건; 석사 특례 및 여권제한 검토']),
    'CA_ESWP_POL_01': (
        '일자리 제안과 고용주 적격성을 확인한다. 고용계약이 있다는 사실만으로 취업허가를 승인하지 않는다.',
        ['employer', 'r200'], ['고용주 불이행 목록·진정성·계약과 제출정보의 일치 확인']),
    'CA_ESWP_POL_02': (
        '일반 신청요건·입국적격성·필요서류와 취업허가 면제 여부를 함께 검토한다.',
        ['employer', 'r200'], ['일반요건 구 URL이 허브로 이동함; 신청 위치별 안내와 개별 입국불허 사유 검토']),
    'CA_ESWP_POL_03': (
        'LMIA가 필요한 경로는 고용주의 선행 절차와 긍정 LMIA 및 관련 서류를 확인한다.',
        ['employer', 'r203'], ['LMIA 면제 분류·유효기간·직무별 조건·고용주 절차 확인']),
    'CA_ESWP_POL_04': (
        'LMIA 면제는 면제 코드별로 확인한다. 일반 IMP의 Employer Portal·고용제안 번호·고용주 수수료에도 예외가 있다.',
        ['imp', 'r200'], ['적용 면제코드 및 포털·수수료 면제 여부 확인; open permit 절차와 혼동 금지']),
    'CA_ESWP_POL_05': (
        '허가서의 고용주·직종·근무지·추가조건을 준수해야 하며 고용주 변경이 자동 허용되는 것은 아니다.',
        ['employer', 'imp'], ['연장·조건변경·신청 위치·임시정책상 개별 허가와 maintained status 검토']),
    'CA_STUDY_POL_01': (
        'DLI 입학과 입학허가 자료를 확인한다. 고등교육기관의 입학확인 및 퀘벡 CAQ 요건도 적용될 수 있다.',
        ['study', 'r216'], ['LOA 진위확인·PAL/TAL 면제·학교/과정·퀘벡 적용범위 확인']),
    'CA_STUDY_POL_02': (
        '캐나다 취업에 의존하지 않는 학비·생활비·왕복교통비를 검토한다. 생활비는 신청일·가족 수·지역별로 분리한다.',
        ['finance', 'r220'], ['IRPR 215(1)(d)/(e) 예외 및 퀘벡 기준 확인; 재원 가용성과 전체 과정 재정계획 검토']),
    'CA_STUDY_POL_03': (
        '입국적격성·필요시 경찰증명/검진·허가기간 종료 시 출국 의사를 검토한다. 전과를 일률적 영구 부적격 규칙으로 만들지 않는다.',
        ['study', 'r216'], ['IRPR 216(2)의 출국요건 예외 및 개별 입국불허·회복 관련 법조문 검토']),
    'CA_STUDY_POL_04': (
        '학업 지속·허가조건 준수와 고등교육 DLI 변경 절차를 구분한다. 재학/학업진행 의무에는 법정 예외가 있다.',
        ['study_conditions', 'change_school', 'r220_1'], ['IRPR 220.1(2)/(3) 예외·변경허가 대기 중 새 DLI 수학 가능 사례·취업조건 검토']),
    'CA_IEC_WH_POL_01': (
        '한국 국적의 Working Holiday 경로는 18~35세를 포함한다. 연령 계산 단계와 초청 여부는 별도 확인한다.',
        ['iec', 'iec_profile'], ['생일과 프로필/초청/신청 단계별 연령 경계 처리 확인']),
    'CA_IEC_WH_POL_02': (
        '한국인은 IEC 최대 두 번, 회당 최대 24개월이며 여권 유효기간 제한을 적용한다. 구 협정 참여도 총 횟수 검토에 포함한다.',
        ['iec', 'iec_arrival'], ['2023-12-11 전 신청 경과규정·카테고리별 참여횟수·보험/생체정보 만료 확인']),
    'CA_IEC_WH_POL_03': (
        '최소 CAD 2,500과 출국 항공권 또는 구입 재원을 검토한다. 입국 시 재정증명과 출발 전 발급시점도 확인한다.',
        ['iec', 'iec_arrival'], ['출발 전 1주 이내 은행증명·실제 입국단계·지역 생활비 확인']),
    'CA_IEC_WH_POL_04': (
        '체류 전 기간의 의료·입원·본국송환 보험과 입국적격성을 확인한다. 보험기간은 발급 허가기간에 영향을 준다.',
        ['iec_arrival', 'iec'], ['보험증빙·부족 보험기간의 연장 제한·개별 입국불허 사유 확인']),
    'CA_IEC_WH_POL_05': (
        '가족은 IEC에 부양가족으로 포함될 수 없지만 별도 방문·유학·취업 신청은 가능하다. 프로필과 ITA 및 허가신청은 별개 단계다.',
        ['iec_family', 'iec_profile', 'iec_apply'], ['현재 시즌 운영상태·수수료·초청/제출기한 및 가족 개별 자격 확인']),
}

FINANCE_REFERENCE = {
    'source_key': 'finance', 'application_date_from': '2026-09-01',
    'region': 'Canada excluding Quebec', 'currency': 'CAD', 'period': 'one_year',
    'includes_applicant_in_family_count': True,
    'amount_by_family_size': {'1': 23448, '2': 29192, '3': 35888, '4': 43572, '5': 49419, '6': 55736, '7': 62054},
    'additional_person_above_seven': 6318, 'tuition_included': False, 'transportation_included': False,
    'automatic_eligibility_rule': False,
}

EXCEPTION_REVIEWS = {
    'CA_STUDY_POL_02': {
        'checked_provisions': ['IRPR 220', 'IRPR 215(1)(d)', 'IRPR 215(1)(e)'],
        'finding': '재정요건의 명시적 예외는 집행 불가능한 추방명령 대상자 및 최소 6개월 유효한 IRPA 24(1) 임시거주허가 보유자와 연결된다.',
        'source_urls': [LAW + '220.html', LAW + '215.html'],
        'scope': '해당 조문 교차참조 확인; 일반 방문자 신분과 임시거주허가를 혼동하지 않음',
        'remaining': ['2026-09-30 이후 법령 변경 여부', '퀘벡 및 개별 재정예외 적용 검토'],
    },
    'CA_STUDY_POL_03': {
        'checked_provisions': ['IRPR 216(2)', 'IRPR 206', 'IRPR 207(c)', 'IRPR 207(d)'],
        'finding': '출국요건의 명시적 예외는 206 및 207(c)/(d) 대상자에 한정해 교차참조해야 하며 207 전체로 확대하면 안 된다.',
        'source_urls': [LAW + '216.html', LAW + '206.html', LAW + '207.html'],
        'scope': '보호신청·추방명령·보호대상자·특정 장관면제 관련 경로의 조문 연결 확인',
        'remaining': ['2026-09-30 이후 법령 변경 여부', '개별 입국불허·의료·전과 관련 조항 검토'],
    },
    'CA_STUDY_POL_04': {
        'checked_provisions': ['IRPR 220.1(2)', 'IRPR 220.1(3)', 'IRPR 215(2)(a)-(i)', 'IRPR 300(2)(a)-(i)'],
        'finding': '300조 원문을 확보했다. 220.1(3)은 300(2)(a)-(i)의 특정 사람 및 215(2)(a)-(i) 대상자의 특정 가족을 참조하므로 재학·학업진행 의무의 예외를 일반 학생에게 확대하지 않는다.',
        'source_urls': [LAW + '220.1.html', LAW + '215.html', LAW + '300.html'],
        'source_archive': 'data/raw/legal_review/20261028/aca953c4f9b8e675.html',
        'source_archive_sha256': '788b98349e3604f58947a2a8044722491913d2d95d04d61db8bfbd3df92e2e83',
        'scope': '300조 접근 실패 보류 해소 및 예외 범주 확인; 조항별 개인 적용은 별도',
        'remaining': ['2026-09-30 이후 변경 및 학교변경 사례', '법정 예외 범주별 개인 적용 확인'],
    },
}


def attach_official_review(record):
    candidates = record.get('policy_candidates', [])
    for policy in candidates:
        pid = policy['policy_id']
        if pid not in SPECS:
            raise ValueError(f'Unknown Canadian policy: {pid}')
        if policy.get('legal_validation_approved') or policy.get('approved_for_eligibility_decision'):
            raise ValueError(f'Refuse to overwrite approved policy: {pid}')
        summary, source_keys, pending = SPECS[pid]
        policy['official_review'] = {
            'reviewed_at': REVIEW_DATE, 'stage': 'official_desk_review_recorded',
            'reviewed_policy_text': summary, 'text_kind': 'reviewer_summary_not_source_quote',
            'source_references': [{'source_key': key, 'source_url': SOURCES[key]} for key in source_keys],
            'pending_items': pending, 'legal_validation_completed': False,
            'law_consolidation_limit': 'Justice Laws pages inspected were current to 2026-09-30; later amendments must be checked',
        }
        if pid == 'CA_STUDY_POL_02':
            policy['official_review']['financial_reference'] = deepcopy(FINANCE_REFERENCE)
        if pid == 'CA_IEC_WH_POL_05':
            policy['official_review']['season_observation'] = {
                'season': 2026, 'observed_at': REVIEW_DATE, 'pool_status': 'closed',
                'source_url': SOURCES['iec_profile'], 'recheck_before_answering': True,
                'existing_invitation_or_application_status_not_determined': True,
            }
        if pid in EXCEPTION_REVIEWS:
            policy['official_review']['exception_review'] = deepcopy(EXCEPTION_REVIEWS[pid])
    record['official_review_summary'] = {
        'reviewed_at': REVIEW_DATE, 'policy_count': len(candidates),
        'legal_validation_completed_count': 0, 'approval_flags_changed': False,
        'scope': 'dated official-source desk review; original evidence and candidate rules preserved',
    }
    return record

"""Explicit policy scope observations recorded after reading the policy clauses.

References are review anchors, not assertions that every exception is approved.
"""
NOTES = {}


def add(prefix, ids, actor, section, finding, issue=None):
    for suffix in ids.split():
        key = prefix + suffix
        assert key not in NOTES, key
        NOTES[key] = dict(actor=actor, reference_section=section, finding=finding,
                          issue=issue)


H = 'US-WK-01-POL-'
add(H, '0008 0007 0072 0103 0022 0053 0057 0100', 'petitioner_and_beneficiary',
    'historical proclamation/memo; subsequent court orders required',
    '원문은 과거 납부·입국 지침의 설명이다. 청원일·수혜자 소재지·신분변경 및 예외 범위를 구분해야 하며, 현재 의무로 사용하려면 판결 주문과 후속 명령을 확인해야 한다.',
    'court_order_scope_unresolved')
add(H, '0016', 'petitioner', '8 CFR 214.2(h)(4)(iii)(A)(4)',
    '전문적·복잡·독특한 직무 요건 경로다. 수혜자에게 학위가 있다는 사실과 직무 자체의 전문직 판단을 구분한다.')
add(H, '0037', 'petitioner', '8 CFR 214.2(h)(4)(iii)(A)(2)',
    '동종 조직의 유사 직무 기준이며 모든 기업의 모든 직무에 적용되는 학위 요건으로 넓히지 않는다.')
add(H, '0004', 'petitioner', '8 CFR 214.2(h)(4)(ii)',
    '전문직 정의와 직접 관련된 전공 요건을 확인한다. 학사 보유만으로 승인되는 규칙이 아니다.')
add(H, '0024 ADD-001 ADD-002 ADD-003', 'beneficiary', '8 CFR 214.2(h)(4)(iii)(C)',
    '미국 학위·동등 외국 학위·면허·교육훈련경력 동등성은 선택 가능한 경로다. 네 경로를 모두 충족해야 하는 누적 조건으로 바꾸지 않는다.')
add(H, '0023 REG-001', 'registrant_and_petitioner', '8 CFR 214.2(h)(8)(iii)',
    'cap 대상의 해당 회계연도·해당 수혜자 등록과 선정 통지에 한정한다. cap 면제 청원 및 등록 중단 예외와 구분한다.')
add(H, 'WGT-001', 'registrant_and_petitioner', '8 CFR 214.2(h)(8)(iii)',
    '선정 등록과 실제 청원의 수혜자·청원인·직무·SOC·임금수준 일치를 확인한다. 허용 변경을 임의 교체 권한으로 해석하지 않는다.')
add(H, 'WGT-002', 'registrant_and_petitioner', '8 CFR 214.2(h)(8)(iii)',
    '복수 근무지·복수 직무의 가장 낮은 임금수준을 선택하는 조건이다. 단일 근무지의 임금수준 산정과 혼동하지 않는다.')
add(H, 'WGT-003', 'petitioner', '8 CFR 214.2(h)(8)(iv)',
    'USCIS가 해당 회계연도의 등록을 중단한 경우에만 청원 기반 선정 절차를 검토한다. 상시 등록 절차의 대체 선택지가 아니다.')
add(H, '0002 0010 REG-002', 'registrant_and_petitioner', '8 CFR 214.2(h)(8)(iii)',
    '임금 가중 선정과 OEWS 수준 산정은 cap 대상 선정의 범위다. 회계연도·시행일과 실제 제시 임금 근거를 확인하며 임금 지급 하한 규정과 별도로 다룬다.')
add(H, 'REG-003 REG-004 REG-005', 'registrant_and_petitioner', '8 CFR 214.2(h)(8)(iii)',
    '등록 진술·공모 금지·허위 및 중복 등록의 효과다. 다른 적법한 고용주의 독립된 채용 제의와 동일 고용주의 중복 등록을 구분한다.')
add(H, '0030', 'registrant_or_representative', 'USCIS electronic registration account guidance',
    'H-1B 전자등록용 계정 유형에 관한 절차다. 개인의 비자 실체 자격 요건으로 사용하지 않는다.')
add(H, '0045', 'registrant_and_beneficiary', '8 CFR 214.2(h)(8)(iii)',
    '등록 시 여권·여행증명서의 신원 식별 범위다. 여권 변경 예외와 비자 발급 시 유효기간 규칙은 따로 확인한다.')
add(H, '0050', 'registrant_and_petitioner', '8 CFR 214.2(h)(8)(iii)',
    '등록의 진실성과 실제 채용 제의에 대한 진술이다. 등록 선정 자체를 청원 승인으로 안내하지 않는다.')
add(H, 'DEF-001', 'adjudicator_and_petitioner', '8 CFR 214.1(c)(5)',
    '동일 당사자·동일 기초 사실에 대한 이전 판단 존중 원칙이다. 중대한 오류·변경·새 정보 예외와 계속되는 입증 책임을 보존한다.')
add(H, 'EMP-001 EMP-002', 'employer', '20 CFR 655.731(c)(7)',
    '고용 시작 후 비생산 기간의 정규직·시간제 임금 의무다. 근로자 개인 사정에 의한 자발적 부재와 적법한 고용 종료 예외를 확인하며 단순 무근무=무임금으로 판단하지 않는다.')
add(H, 'EMP-003', 'employer', '20 CFR 655.731(c)(6)-(7)',
    '30일·60일은 고용 시작 전에도 의무가 발생하는 최종 시점에 관한 조건이다. 더 일찍 고용을 시작한 경우 임금을 유예할 수 있다는 뜻이 아니다.',
    'wage_start_trigger_requires_clarification')
add(H, 'EMP-004', 'employer', '20 CFR 655.731(c)(3)',
    '복리후생의 동일한 제공 기준에 관한 의무다. 모든 근로자의 실제 혜택 총액이 항상 같아야 한다는 의미로 넓히지 않는다.')
add(H, 'EMP-005', 'labor_authority', 'INA 212(n)(2); DOL H-1B law',
    '당국의 미지급 임금 인정 및 지급명령 절차다. 신청자 개인의 입국 자격 조건으로 변환하지 않는다.')
add(H, '0020', 'employer', '20 CFR 655.731(a)',
    '실제 임금과 통상임금 중 높은 수준을 지급하는 LCA 임금 의무다. 추첨의 OEWS 가중 수준과 구분한다.')
add(H, '0068', 'employer', '20 CFR 655.731(c)(10)',
    '중도 퇴사 벌금 금지와 주법상 손해배상 예정액은 구분해야 한다. 계약 명칭만으로 허용 여부를 단정하지 않는다.')
add(H, '0005 0028 ADD-004 MOD-002', 'petitioner_and_employer', '8 CFR 214.2(h)(4)(iii)(B)',
    'H-1B의 LCA 인증·청원 내용 일치와 I-129 제출 관계다. LCA 인증을 청원·비자·입국 승인으로 보지 않는다.')
add(H, 'ADD-005 ADD-006 ADD-007', 'employer', 'INA 212(n)(1); DOL H-1B law',
    'LCA의 근무조건·노동쟁의·통지 의무다. 노조 유무·해당 근무지·통지 방법 및 시점별 의무를 별도로 적용한다.')
add(H, 'ADD-008', 'employer', '8 CFR 214.2(h)(4)(iii)(E)',
    '승인기간 전 고용주 해고 시 합리적 귀국 교통비와 자발적 퇴사를 구분한다. 임금·일반 퇴직금 의무와 동일시하지 않는다.')
add(H, 'ADD-009 ADD-012', 'beneficiary_and_new_petitioner', '8 CFR 214.2(h)(2)(i)(H)',
    '적격 H-1B의 이직·동시취업에 관한 portability다. 적법한 nonfrivolous 청원 접수와 요청 시작일 중 늦은 때 및 무허가 취업·기한 조건을 보존한다.')
add(H, 'ADD-010', 'beneficiary_and_adjudicator', '8 CFR 214.1(l)(2)',
    '최대 60일 또는 기존 유효기간 종료일까지 중 짧은 기간의 재량 유예다. 자동 60일 취업허가나 비자 연장을 뜻하지 않는다.')
add(H, 'ADD-011', 'petitioner_and_beneficiary', '8 CFR 214.2(h)(8)',
    'cap 면제 고용에서 cap 대상 고용으로 이동하는 경우다. 과거 cap 산입 이력 등 개별 예외를 확인한다.')
add(H, '0006 0031', 'petitioner_and_visa_applicant', 'temporary worker visa petition guidance',
    '임시취업비자 일반 절차 중 청원과 영사 비자 발급의 순서를 설명한다. 다른 분류의 청원 예외를 H-1B 전체에 전용하지 않는다.')
add(H, '0062', 'beneficiary_and_border_authority', '8 CFR 214.2(h); USCIS admission guidance',
    '청원 승인 후 필요한 비자 신청 및 CBP 입국 심사는 별도 단계다. I-129 승인만으로 입국 보장이라고 안내하지 않는다.')
add(H, '0052', 'beneficiary', 'temporary worker visa change-of-status guidance',
    '미국 내 적법한 신분변경과 해외 비자 발급을 구분한다. 출국 후 재입국에 필요한 비자 여부는 따로 판단한다.')
add(H, '0064', 'visa_applicant', 'DOS temporary worker visa fee guidance',
    '영사 비자 신청 수수료와 국적별 발급 수수료다. I-129·전자등록·I-907 수수료와 구분하고 납부 시점의 표를 확인한다.')
add(H, '0076', 'visa_applicant', 'DOS passport validity guidance',
    '예정 체류 종료 후 여권 유효기간 원칙과 국가별 협정 예외를 함께 적용한다. 등록 여권 규칙과 구분한다.')
add(H, '0078', 'beneficiary', 'I-94/admission and extension guidance',
    '체류 허가 기간과 비자 스티커 만료일을 구분한다. 연장 신청 접수의 효과와 취업 지속 가능성은 개별적으로 확인한다.')
add(H, '0090 0088', 'dependent_spouse_or_child', '8 CFR 214.2(h)(9)(iv)',
    'H-4 동반 범위와 특정 배우자의 별도 EAD 자격을 구분한다. H-4라는 이유만으로 배우자·자녀 모두의 취업을 허용하지 않는다.')
add(H, '0012', 'visa_applicant_and_consular_authority', 'DOS 2025 expanded screening notice',
    'H-1B/H-4 영사 심사 공지의 대상·시행일 범위다. 미국 내 모든 근로자의 일반 의무로 확장하지 않는다.')
add(H, '0001 0061', 'petitioner_and_employer', '2026 9/11 biometric fee final rule',
    '해당 수수료는 모든 I-129에 일률 적용되는 것이 아니다. 고용주 규모·H/L 비율·청원 유형·접수일·법정 종료일을 현행 규칙과 함께 확인한다.',
    'fee_employer_threshold_and_sunset_review')
add(H, '0069', 'registrant_or_representative', 'H-1B electronic registration fee guidance',
    '수혜자별 등록 수수료이며 청원·비자 수수료와 별개다. 납부 시점 금액과 적용 회계연도를 확인한다.')
add(H, '0048', 'selected_registrant_and_petitioner', '8 CFR 214.2(h)(2)(i)(J); (h)(8)(iii)',
    '선정 통지의 제출기간·요청 시작일과 6개월 전 접수 제한을 함께 본다. 선정일 즉시 무제한 접수 가능한 규칙이 아니다.')
add(H, '0058', 'beneficiary_and_petitioner', '8 CFR 214.2(h)(4)(v)',
    '주·지역 면허 원칙과 임시면허·감독하 업무·면허 발급의 기술적 장애 예외를 구분한다.')
add(H, '0079 0084', 'beneficiary_and_petitioner', '8 CFR 214.2(h)(13)(iii)(E)',
    '승인된 이민청원 및 비자번호 사유의 6년 초과 연장 경로다. 비자 사용 가능 후 신청 지연과 불가항력 예외, 대체 경로를 별도로 확인한다.')
add(H, 'STAY-001', 'beneficiary_owner_and_petitioner', '8 CFR 214.2(h)(9)(iii); (h)(13)(iii)',
    '일반 3년·6년 상한과 수혜자 소유주의 최초·첫 연장 18개월 제한을 구분한다. 각 승인은 LCA 및 실제 고용기간에도 제한된다.')
add(H, 'STAY-002', 'beneficiary_and_petitioner', '8 CFR 214.2(h)(13)(iii)(D)',
    '365일 경과에 따른 연장은 접수 사실만으로 자동 발생하지 않는다. 관련 절차의 지속·거절·철회 및 신청 지연 조건을 확인한다.')
add(H, 'MOD-001', 'petitioner', '8 CFR 214.2(h)(4)(iii)(F)',
    '요청 시작일에 실제 전문직 자리가 존재해야 한다는 청원인 입증 범위다. 등록의 채용제의 진술과 청원 심사 증거를 구분한다.')
add(H, 'MOD-003', 'petitioner_and_adjudicator', '8 CFR 214.2(h)(4)(i)(B)(2)',
    '청원 준수 검증을 위한 현장 실사 및 비협조의 심사상 효과다. 모든 실사 요청이 자동 취소를 뜻하지 않는다.')
add(H, 'MOD-004 MOD-005 MOD-006', 'petitioner_beneficiary_owner_or_third_party', '8 CFR 214.2(h)(4)(ii)-(iii)',
    '미국 고용주의 실체·제3자 배치의 실제 직무 요건·수혜자 소유주의 주된 전문직 업무 조건을 구분한다. 소유 또는 원격근무만으로 부적격·적격을 단정하지 않는다.')
add(H, 'MOD-007', 'cap_exempt_petitioner_and_beneficiary', '8 CFR 214.2(h)(8)(iii)(F)',
    '적격 기관 직접 고용 외의 cap 면제 경로다. 근무시간 비율과 적격 기관의 핵심 목적 지원 요건을 개별적으로 확인한다.')
add(H, 'MOD-008', 'petitioner_and_adjudicator', '8 CFR 214.2(h)(11)(ii)',
    '자동 취소 사유와 별도 통지에 의한 취소 사유를 구분한다. 모든 고용조건 변경이 자동 취소라는 의미가 아니다.')
add(H, 'MOD-009', 'adjudicator_and_petitioner', '8 CFR 214.2(h)(9)',
    '심사 지연으로 최초 요청기간이 지난 경우의 RFE·새 기간 절차다. 청원인의 LCA 및 새 기간 입증 의무를 보존한다.')
add(H, '0086 0096', 'petitioner_and_beneficiary', '8 CFR 214.1(c); 8 CFR 214.2(h)',
    '체류 연장·변경의 신분 유지 증빙과 지연 접수 재량 예외다. 해외 영사 처리까지 같은 신분 유지 조건을 일률 전용하지 않는다.')
add(H, '0097', 'petitioner_and_beneficiary', '8 CFR 214.2(h)(2)(i)(E)',
    '중요 고용조건 변경 전 개정·신규 청원 원칙과 근무지 예외를 구분한다. LCA 갱신만으로 모든 변경이 승인되지 않는다.')
add(H, 'CAPGAP-001 0095', 'f1_student_and_h1b_petitioner', '8 CFR 214.2(f)(5)(vii)',
    '적격 F-1 cap-gap의 체류 연장과 해당되는 기존 취업허가 연장을 구분한다. 청원 거절·철회·취소 및 요청 시작일 조건을 보존하고 취업허가가 없던 학생에게 새 허가를 만들지 않는다.')
add(H, '0092', 'cap_exempt_petitioner_or_f1_student', '8 CFR 214.2(h)(8); (f)(5)(vii)',
    '연구기관 cap 면제와 F-1 cap-gap은 서로 다른 요건이다. 복합 정책을 하나의 자격 조건으로 합치지 않는다.',
    'multiple_legal_subjects_require_split')
add(H, '0019', 'cap_subject_petitioner', '8 CFR 214.2(h)(8)',
    '일반 cap 및 미국 고급학위 면제의 연간 수치다. 협정 유보·이월·cap 면제 기관 등과 실제 회계연도 가용 수는 별도로 확인한다.')
add(H, 'WPR-001', 'covered_employer', 'INA 212(n)(1)(E)-(G); DOL H-1B law',
    '근로자 대체 제한은 해당 의무의 적용 대상 고용주와 예외 수혜자를 확인해야 한다. 모든 고용주에게 같은 90일 제한을 적용하지 않는다.')
add(H, 'WPR-002', 'employer', 'INA 212(n)(2)(C)(iv); DOL H-1B law',
    '정보 공개·절차 협조에 대한 보복 금지다. 전직 근로자·지원자 등 보호 범위를 임의로 현재 고용 중인 사람으로 좁히지 않는다.')
add(H, 'WPR-003 WPR-004 ENF-001 ENF-002', 'labor_authority_and_investigated_employer', 'INA 212(n)(2); DOL H-1B law',
    '조사 개시·사전 통지·기간·무작위 조사·제보 보호의 각각 다른 절차다. 특정 조사 경로의 60일 또는 5년을 모든 조사에 일반화하지 않는다.')
add(H, 'AGL-001', 'us_agent_and_actual_employer', '8 CFR 214.2(h)(2)(i)(F)',
    '명시된 특정 대리·다수 단기고용·해외 고용주 관계의 agent 청원이다. 미국 agent라는 이유만으로 모든 H-1B 청원을 허용하지 않는다.')
add(H, 'AGL-002', 'labor_and_immigration_authorities', 'INA 212(n)(2); 8 CFR 214.2(h)(10)',
    '특정 위반 통지에 따른 고용주 제재다. 모든 법 위반의 동일한 승인 금지 기간으로 넓히지 않는다.')
add(H, 'AGL-003', 'employer_and_adjudicator', '8 CFR 214.2(h)(11)',
    'LCA 중단·무효화 후 기존 근로자에 대한 계속 준수 인증 예외다. 신규 청원이나 모든 취소 사유에 확대하지 않는다.')

I = 'US-J1-INTERN-POL-'
T = 'US-J1-TRAINEE-POL-'
add(I, '001', 'sponsor_and_applicant', '22 CFR 62.22(d)(3)',
    '해외 고등교육기관의 전일제 재학생 또는 시작일 기준 졸업 12개월 이내 경로다. 안내문에서 빠진 전일제 조건을 규정과 함께 보존한다.', 'full_time_condition_missing_in_brochure')
add(T, '001', 'sponsor_and_applicant', '22 CFR 62.22(d)(2)',
    '해외 학위·전문 자격과 해외 관련 경력 1년 또는 해외 관련 경력 5년이라는 두 경로를 구분한다.')
for prefix, ids in [(I, '002'), (T, '002')]:
    add(prefix, ids, 'sponsor_and_host', '22 CFR 62.22(j)(1)',
        '단순노동·돌봄·환자 접촉 금지의 배치 제한이다. 허용 직종 목록의 의료 관련 분야가 환자 진료를 허용한다는 뜻이 아니다.')
for prefix, ids in [(I, '003'), (T, '003')]:
    add(prefix, ids, 'sponsor_and_host', '22 CFR 62.22(j)(4)',
        '사무업무 비중이 20%를 초과하는 배치를 금지한다. 정확히 20%와 초과를 구분한다.')
for prefix, ids in [(I, '004'), (T, '007')]:
    add(prefix, ids, 'designated_sponsor', '22 CFR 62.22(c)(2); (j)',
        '지정 스폰서의 허용 직종 범위와 금지 업무를 함께 적용한다. 직종명이 목록에 있다는 이유로 개별 배치가 자동 허용되지 않는다.')
for prefix, ids in [(I, '005'), (T, '008')]:
    add(prefix, ids, 'sponsor', '22 CFR 62.22(g)(4)',
        '성공적인 종전 참가 이력이 없는 호스트에서 직원 25명 미만 또는 연매출 300만달러 미만이면 방문 기준을 검토한다. 대학·정부기관 배치 제외를 보존한다. 안내문의 두 규모 조건을 AND로 적용하면 규정보다 좁다.',
        'site_visit_and_or_conflict')
for prefix, ids in [(I, '006'), (T, '009')]:
    add(prefix, ids, 'sponsor', '22 CFR 62.22(g)(3)',
        '호스트 EIN·사업 실체·산재보험 또는 주법상 면제 증빙을 확인하는 스폰서 의무다. 참가자가 고용주 보험에 가입해야 한다는 자격 조건이 아니다.')
for prefix, ids in [(I, '007'), (T, '010')]:
    add(prefix, ids, 'sponsor_host_and_participant', '22 CFR 62.22(l)',
        '6개월 초과 프로그램의 최소 중간·종료 평가다. 참가자와 직속 감독자 서명, 종료 전 완료 및 스폰서 보존 의무를 함께 확인한다.')
for prefix, ids in [(I, '009'), (T, '013')]:
    add(prefix, ids, 'host_with_sponsor_oversight', '22 CFR 62.22(h)(1); (i)(1)',
        '호스트의 DS-7002 서명과 스폰서의 모든 필수 서명 확보를 구분한다. 양식 완결과 DS-2019 발행·비자 신청의 순서를 보존한다.')
add(I, '010', 'host_with_sponsor_oversight', '22 CFR 62.22(h)(2)',
    '훈련계획 이탈·변경·우려와 긴급상황을 호스트가 스폰서에 통지하는 의무다. 참가자 자격 요건으로 변환하지 않는다.')
for prefix, ids in [(I, '011'), (T, '014')]:
    add(prefix, ids, 'host_with_sponsor_certification', '22 CFR 62.22(f)(2)(ii)',
        '숙련 직원의 현장 감독·멘토링을 제공하는 호스트 및 이를 인증하는 스폰서의 의무다.')
add(T, '004 005', 'sponsor_and_host', '22 CFR 62.22(b); (f)(2)(v)',
    '교육·훈련 목적과 미국 근로자 대체·일손 충원 금지를 함께 본다. 참가를 일반 취업 프로그램으로 사용하지 않는다.')
add(T, '006', 'sponsor_and_participant', '22 CFR 62.22(e)(3)',
    '기존 경력·훈련의 단순 반복을 금지하며 새로운 지식·기술 확장 목적을 확인한다.')
add(T, '012', 'sponsor_and_host', '22 CFR 62.22(f)(1)(iv)',
    '주 32시간 이상은 훈련·인턴십 프로그램의 전일제 편성 기준이다. 일반 노동자의 모든 법정 근로시간을 뜻하지 않는다.')

F = 'US-F1-POL-'
add(F, '001', 'student_and_school', 'DHS SEVP school search; 8 CFR 214.2(f)(1)',
    '학교의 F-1/M-1 인증 범위와 해당 교육과정을 구분한다. 학교검색 등재만으로 개인 입학·비자·입국이 승인되지 않는다.')
add(F, '002', 'school_dso_and_student', '8 CFR 214.2(f)(1)(i)',
    'SEVP 인증 학교의 입학 후 DSO가 발행하는 I-20 절차다. I-20는 비자 또는 입국허가 자체가 아니다.')
add(F, '003', 'student_dependent_and_dso', 'DHS Form I-20 guidance; 8 CFR 214.2(f)',
    '적격 동반가족의 개별 I-20와 본인 I-20 서명을 구분한다. 미성년 서명 조건과 F/M 과정 유형을 보존한다.')
add(F, '004', 'student', 'DHS I-901 SEVIS fee guidance',
    'I-20 수령 후 해당 I-901 수수료를 확인한다. 동반 F-2/M-2와 기존 학생의 재납부 예외를 별도 확인하며 모든 사람·입국에 새 납부를 강제하지 않는다.')
add(F, '005', 'initial_student_and_consular_authority', 'DHS Form I-20 guidance; 8 CFR 214.2(f)(5)(i)',
    '최초 학생의 비자 발급 가능 시점과 입국 가능 시점은 다르다. 365일 전 발급을 365일 전 입국 허용으로 사용하지 않는다.')
add(F, '006', 'initial_student_and_border_authority', '8 CFR 214.2(f)(1); (f)(5)(i)',
    '시작일 30일 전 최초 입국과 I-20 제시를 설명한다. 원문 끝의 or는 다른 사용 목적 항목으로 이어지는 추출 흔적이며 새 대체 요건을 만들지 않는다.', 'trailing_or_extraction_boundary')
add(F, '007', 'change_of_status_applicant', 'DHS Form I-20 guidance; 8 CFR 214.2(f)',
    '미국 내 F/M 신분변경에 필요한 I-20다. 발행만으로 신분변경 승인이나 학업 개시 허가가 되지 않는다.')

C = 'US-J1-COLLEGE-POL-'
add(C, '001', 'sponsor_and_student', '22 CFR 62.23(c); (e)(4); (h)',
    '재원·협정·학생 인턴 등 선택 가능한 선정 경로와 비학위 과정의 기간·학업 조건이 섞여 있다. 비학위 등록만으로 선정 요건 충족이라고 사용하지 않는다.', 'selection_and_nondegree_conditions_mixed')
add(C, '002', 'student_and_sponsor', '22 CFR 62.23(h)',
    '학위 과정의 정상 진도·재학 조건과 비학위 과정 최대 24개월을 구분한다. 학문 훈련 포함 기간과 학생 인턴 별도 유형을 확인한다.')
add(C, '003', 'student_and_responsible_officer', '22 CFR 62.23(g)',
    '성적·학업 유지 외에 허용 고용 유형과 RO의 사전 서면 승인이 필요하다. 주 20시간 제한과 공식 방학 예외를 함께 보존한다.')
add(C, '004', 'student_dean_and_responsible_officer', '22 CFR 62.23(f)',
    'academic training은 전공 관련성·사전 서면 승인·기간 제한이 있다. 무급이라고 자유롭게 가능하지 않으며 일반 취업과 학생 인턴을 구분한다.')
add(C, '005', 'sponsor', '22 CFR 62.23(c)',
    '선정 전 학업 자격 정보를 확보하는 스폰서 의무다. 지원자가 모든 배경자료를 동일 양식으로 제출해야 한다는 뜻은 아니다.')
add(C, '006', 'sponsor', '22 CFR 62.23(d)',
    'DS-2019에 기재된 기관의 입학·학생 인턴 수락을 발행 전에 확인하는 의무다.')
add(C, '007', 'student_and_sponsor', '22 CFR 62.23(e)',
    '전일제 학업 원칙과 공식 방학·질병·학업 사유·마지막 학기·승인된 훈련 등의 예외를 함께 보존한다.')

S = 'US-SWT-POL-'
add(S, '001', 'sponsor_and_applicant', '22 CFR 62.32(d)(2)',
    '영어 회화·독해 확인은 인정 시험 또는 문서화된 인터뷰로 진행한다. 단일 공인시험 점수를 임의로 만들지 않는다.')
add(S, '002 003', 'sponsor_and_applicant', '22 CFR 62.32(d)(4)',
    '신청 시 해외 소재 인가된 대면 고등교육기관 전일제 재학과 최소 한 학기 이수를 함께 확인한다. 졸업 직전 학년도 학생도 조문 범위에서 구분한다.')
add(S, '004', 'sponsor_and_participant', '22 CFR 62.32(n); BridgeUSA SWT guidance',
    '사전 고용 확보와 VWP 국적 예외는 J-1 프로그램의 조건이다. 비자면제 입국으로 SWT 취업이 가능하다는 뜻이 아니다.')
add(S, '005', 'sponsor_and_participant', '22 CFR 62.32(c)',
    '학년 사이 장기 방학의 최대 4개월과 연장 불가를 보존한다. 재참가는 매 회차 조건을 다시 확인하며 무제한 체류 연장이 아니다.')
add(S, '006', 'sponsor_and_host', '22 CFR 62.32(g)-(h)',
    '금지 배치 목록과 별도 J 분류·면허 직무·파견업체 조건을 구분한다. 파견업체의 허용 예외는 세 요건 모두 충족해야 한다.')
add(S, '007', 'sponsor_and_host', '22 CFR 62.32(g); (n)',
    '스폰서의 배치 심사·주거 교통 지원 및 호스트 검증 의무다. 합법적인 계절·일시 고용과 문화교류 기회를 함께 확인한다.')
add(S, '008', 'sponsor_and_participant', '22 CFR 62.32(e); BridgeUSA SWT guidance',
    '출국 전 정보 제공·고용 검증과 참가자의 도착·주소 통지 의무를 구분한다. 검증 전 새 고용 개시를 허용하지 않는다.')
add(S, '009', 'sponsor', '22 CFR 62.32(i)-(j); BridgeUSA SWT guidance',
    'VWP 국적자의 구직 지원 부분과 모든 참가자에 대한 임금·월별 연락 의무를 분리한다. 임금은 연방·주·지방 하한 및 유사 미국 근로자 대우를 함께 검토한다.', 'vwp_heading_overgeneralizes_wage_and_monitoring')
add(S, '010', 'host_employer', '22 CFR 62.32(o)',
    '호스트의 약정 근로시간 제공·해당 초과근무 지급·스폰서 통지 의무다. 참가자의 사전 자격이나 스폰서 자체 의무로 혼동하지 않는다.')

W = 'US-WEST-01-POL-2026H1-'
add(W, 'ELIG-001', 'applicant', '2026 H1 recruitment eligibility', '해당 회차 대한민국 국적 요건이며 복수국적 제한과 함께 본다.')
add(W, 'ELIG-002', 'applicant_and_consular_authority', '2026 H1 recruitment eligibility', '국내 선발과 미국 비자 발급 심사는 별개이며 WEST 합격이 비자 발급을 보장하지 않는다.')
add(W, 'ELIG-003', 'enrolled_or_on_leave_applicant', '2026 H1 recruitment eligibility', '지원 시점의 대학 유형별 이수학기를 구분하고 졸업생 경로와 누적 조건으로 합치지 않는다.')
add(W, 'ELIG-004', 'graduate_applicant', '2026 H1 recruitment eligibility', '이 회차의 2025년 8월·2026년 2월 졸업생 범위다. 현재 시점의 최근 1년으로 이동시켜 적용하지 않는다.')
add(W, 'ELIG-005', 'applicant_and_home_university', '2026 H1 university recommendation', '소속 대학 추천 절차다. 본인 온라인 지원만으로 대학 추천을 대체하지 않는다.')
add(W, 'LANG-SHORT_TERM LANG-MID_TERM', 'applicant', '2026 H1 language score table', '단기·중기 각각 1그룹 AND 2그룹이며 그룹 안은 OR다. 시험 종류·단계·점수·접수 마감 기준 2년 유효기간을 회차별로 유지한다.')
add(W, 'PROGRAM-SHORT_TERM PROGRAM-MID_TERM', 'selected_participant', '2026 H1 program schedule', '어학·인턴십·여행 구성과 예정 인원은 해당 공고의 일정이다. J-1 일반 최대 체류기간이나 보장 인턴십 기간으로 전용하지 않는다.')
add(W, 'DOC-COND-001 DOC-COND-002', 'applicable_applicant', '2026 H1 conditional documents', '해당자 또는 졸업생이라는 조건부 제출 범위를 유지하며 모든 신청자의 공통 필수 서류로 바꾸지 않는다.')
add(W, 'DOC-COMMON-001 DOC-COMMON-002 DOC-COMMON-003 DOC-COMMON-004', 'applicant_and_home_university', '2026 H1 common documents', '공통 서류의 해당 학적·성적·시험 증명 및 제출 경로를 유지한다. 온라인 지원과 대학 제출 절차를 구분한다.')
add(W, 'RESTRICT-001 RESTRICT-002 RESTRICT-003 RESTRICT-004', 'applicant', '2026 H1 exclusions', '복수국적·해외 대학·기참가·납부 마감 후 포기 등 해당 공고의 제한 범위다. 모든 해외 인턴십 또는 다른 회차의 영구 제한으로 일반화하지 않는다.')
add(W, 'APPLY-001', 'applicant', '2026 H1 duplicate applications', '단기·중기 동시 지원 금지다. 다른 사업과의 중복 가능성까지 이 문장으로 판단하지 않는다.')

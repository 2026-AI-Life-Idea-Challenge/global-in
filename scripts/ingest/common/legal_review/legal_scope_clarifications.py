"""Recorded, policy-specific scope review; not an eligibility approval."""
import hashlib
import json
from pathlib import Path

JP_MAIN = 'https://www.kr.emb-japan.go.jp/itpr_ko/visa_working.html'
JP_DOCS = 'https://www.kr.emb-japan.go.jp/itpr_ko/visa_working_documents.html'
JP_MOFA = 'https://www.mofa.go.jp/j_info/visit/w_holiday/'

# Explicit IDs prevent a new, unreviewed policy from inheriting this review.
JP_FINDINGS = {
    '8401a71247c0d4e43fc4bb1b': ('documents.required.3', '이유 진술서는 일본어 또는 영어로 본인이 작성한다.'),
    'ef5d4fd5e19af42ba7396365': ('documents.required.1', '소정 신청서와 최근 사진의 규격·촬영기간을 함께 확인한다.'),
    'b46cdf6c4ac08aaa18fb3fe0': ('documents.required.2', '이력서는 소정양식이며 일본어 또는 영어로 본인이 작성한다.'),
    '6f5d3e261683b64d5aa32b26': ('documents.required.10', '일본 출입국 기록 외에도 성년 이후 장기 해외체류 및 과거 워킹홀리데이 사증 페이지 조건을 보존한다.'),
    '970136ab34cc66d61e5fe5df': ('documents.required.4', '활동계획 진술서는 본인이 작성한다. 영어능력 입증자료가 없어도 신청 가능하다는 예외를 보존한다.'),
    'c715475547da0fcc0fefacce': ('documents.required.5', '조사표는 일본어로 본인이 작성하고 서명한다.'),
    '8370a129bb7b33c4bb8ed3b1': ('documents.required.6', '기본증명서는 상세 형식이다.'),
    '297287b35131c1aaab60aa22': ('documents.required.7', '주민등록초본 외 안내된 대체 자료를 허용한다.'),
    '0f19738f76eff5ce3e7f990b': ('documents.required.8', '학적별 증명, 과거 일본 유학 및 특정 언어 증명의 번역 조건을 별도로 적용한다.'),
    '09a2d07f4b60ba8ae617d8c3': ('documents.required.9', '잔고증명은 초기 체재·귀국자금 입증이다. 가족 부양 계좌 사용 시 관계증명이 필요하다.'),
    '667c3c85a1be643c890d7102': ('documents.required.11', '출생부터 현재까지 기록이며 개명 전후 기록도 포함한다.'),
    '45947cca52da3ec434549dd9': ('documents.required.12', '체크리스트는 신청인이 직접 작성한다.'),
    '6ff49b598065727f4e9ebb0f': ('documents.conditional.1', '병역 증명은 해당자 조건부 서류이며 주민등록초본과 겸용 가능하다.'),
    'b4d544dfd74665d49a77a136': ('documents.conditional.2', 'JLPT 일률 필수 조건으로 바꾸지 않는다. 자료가 없으면 학습이력을 설명하는 경로가 있다.'),
    'f8393e8d6f1d8da8055cdb11': ('requirements.1', '한국 국적과 한국 거주를 모두 확인한다. 중복 문장의 동일성만으로 정책 ID를 삭제하지 않는다.'),
    '8b804fe3bfeb2309fd2b2b60': ('requirements.1', '한국 국적과 한국 거주를 모두 확인한다. 동일 문장 정책과 중복 후보 관계를 기록한다.'),
    'f2b3c13e3729ec466981acca': ('requirements.3', '신청 시 원칙 연령은 18~25세다. 30세까지의 예외는 사정 인정이 필요하며 자동 허용하지 않는다.'),
    '6b986824f1c3095d6c1b0cf4': ('requirements.7', '과거 발급 0~1회이며 미사용 실효도 안내된 사정에 따라 발급 횟수에 산입한다.'),
    '042a6b29505bb2833baa2522': ('requirements.4', '대사관의 자녀 동반 제한과 외무성의 부양가족 안내를 구분하고 동반인 개별 범위를 추가 확인한다.'),
    'c19b5e960c1c6cf759cdcf07': ('requirements.5', '약 280만원은 안내상의 자금 규모다. 환율·사정과 무관한 고정 법정금액으로 단정하지 않는다.'),
    'f65c32fc6375614b0646e162': ('requirements.6', '건강 요건을 확인하되 이 문장만으로 진단서 일률 제출 의무를 만들지 않는다.'),
    '90c2c98c2f9ec0360560d8b1': ('requirements.8', '최소 일본어 능력 또는 습득 의욕이라는 대체 조건을 보존한다.'),
    '1b1a2b57a695802cf1a9358e': ('requirements.2', '주목적은 휴가다. 교육과정 인턴십을 워킹홀리데이 대상으로 일반화하지 않는다.'),
    '7402f3813d9aa398419d6397': ('mofa.eligibility.passport', '유효 여권 및 귀국 항공권 또는 구매 자금이라는 선택 조건이다. 한국인 신청에는 대사관 세부 안내를 함께 적용한다.'),
    '54f47ecde2bc322be711ab35': ('mofa.eligibility.passport', '동일 여권·귀국자금 문장의 중복 후보다. 개별 ID는 보존하고 대사관 제출서류와 함께 해석한다.'),
}


def apply_scope_clarifications(rows):
    reviewed = []
    for row in rows:
        if row['program_id'] == 'JP:JP-WH-01':
            suffix = row['policy_id'].removeprefix('JP-POL-')
            section, finding = JP_FINDINGS[suffix]
            source = JP_DOCS if section.startswith('documents') else JP_MOFA if section.startswith('mofa') else JP_MAIN
            row['detailed_scope_review'] = {
                'reviewed_at': '2026-10-28', 'status': 'official_guidance_scope_clarified',
                'source_url': source, 'source_section': section,
                'finding': finding, 'text_kind': 'reviewer_summary_not_source_quote',
                'method': 'official web pages read; policy-by-policy manual scope review',
                'application_scope': 'South Korean nationals residing in South Korea; not a universal nationality rule',
                'application_window': {'year': 2026, 'quarter': 4, 'start': '2026-10-12', 'end': '2026-10-16', 'status_on_review_date': 'closed', 'source_url': JP_MAIN},
                'remaining_review': ['statutory_basis_and_individual_case_applicability', 'final_approval_not_granted'],
            }
            reviewed.append(row['policy_id'])
        elif row['policy_id'] in ('US-J1-INTERN-POL-008', 'US-J1-TRAINEE-POL-011'):
            row['detailed_scope_review'] = {
                'reviewed_at': '2026-10-28', 'status': 'six_month_boundary_resolved_for_reviewer_summary',
                'source_url': row['normative_clarification']['source_url'], 'source_section': '22 CFR 62.22(l)',
                'finding': '6개월 이하는 최소 종료 평가, 6개월 초과는 최소 중간·종료 평가다. 스폰서 평가 절차 의무이며 참가자·직속 감독자 서명과 3년 보존도 분리해 보존한다.',
                'text_kind': 'reviewer_summary_not_source_quote',
                'remaining_review': ['original_brochure_policy_requires_corrected_version_before_use', 'other_program_conditions_and_final_approval_pending'],
            }
            reviewed.append(row['policy_id'])
    assert len(reviewed) == 27 and len(set(reviewed)) == 27
    root = Path(__file__).resolve().parents[4]
    path = root / 'data/processed/legal_review/us_jp_remaining_scope_20261028.json'
    remaining = json.loads(path.read_text(encoding='utf-8'))
    snapshot_raw = (root / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    assert hashlib.sha256(snapshot_raw).hexdigest() == remaining['input_sha256']
    policies = {p['policy_id']: p for p in json.loads(snapshot_raw)['policy_candidates']}
    assert len(remaining['records']) == 300
    for row in rows:
        pid = row['policy_id']
        if pid in remaining['records']:
            assert 'detailed_scope_review' not in row
            record = remaining['records'][pid]
            assert hashlib.sha256(policies[pid]['policy_text'].encode()).hexdigest() == record['policy_text_sha256']
            row['detailed_scope_review'] = record
            row['legal_holds'] = sorted(set(row['legal_holds'] + record['issue_codes']))
            reviewed.append(pid)
    assert len(reviewed) == len(set(reviewed)) == 327
    return reviewed

"""Publish explicit source-based interpretations, retaining their provenance."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'data/processed/legal_review'


def main():
    path = OUT / 'team_completion_adjudication_20261028.json'
    completion = json.loads(path.read_text(encoding='utf-8'))
    last = json.loads((OUT / 'team_last_two_rule_decisions_20261028.json').read_text(encoding='utf-8'))
    english = last['english']
    extra = dict(source_url='https://immi.homeaffairs.gov.au/help-support/meeting-our-requirements/english-language/functional-english',
                 source_file='data/processed/legal_review/team_final_english_sources_20261028.json')
    if extra not in english['additional_source_files']:
        english['additional_source_files'].append(extra)
    completion['wording_updates']['AU_462_FIRST_POL_05'] = english
    previous = json.loads((OUT / 'policy_final_followup_decisions_20261028.json').read_text(encoding='utf-8'))['wording_updates']['DE_WH_POL_03']
    old = '두 증빙을 함께 제출했을 때의 합산 최저액을 이 문구로 산출하지 않으며 공관의 실제 증빙 인정에 따른다.'
    new = '공관 원문의 각(je) 감액과 각 지급증명 조건에 따른 검토자의 조건부 계산은 3,500−1,000×n 유로다. n은 실제 인정되는 별개의 증빙 항목 수(0·1·2)이며, 0개는 3,500, 1개는 2,500, 2개 모두 인정되면 1,500유로로 산출된다. 이는 공관이 별도로 제시한 숫자 예시의 인용이나 신청인의 증빙 수리 보장이 아니라 원문에 대한 문언·산술 해석이다. 항공권 예약만 하거나 숙박 대금을 지급하지 않은 경우를 인정 증빙으로 자동 계산하지 않는다.'
    assert old in previous['text']
    previous['text'] = previous['text'].replace(old, new)
    previous.update(scope='2026-10-28 공관 서류·보험·재정 조건과 각 지급증명이 실제 인정된 경우의 문언상 계산 해석. 개별 증빙 수리·비자 발급 보장 제외.',
        findings=['독문 je(각)와 jeweils mit Zahlungsnachweis(각 지급증명)를 한국어 1,000유로씩 감액 안내와 대조했다.',
                  '3,500−1,000×n은 검토자의 조건부 파생값임을 표시한다. 별도 기관 회신이나 공식 숫자 예시를 확보했다고 주장하지 않는다.'],
        interpretation_type='reviewer_conditional_arithmetic_from_official_wording_not_agency_confirmation')
    previous['additional_source_files'] = [dict(source_url='https://seoul.diplo.de/kr-de/service/05-visaeinreise/1991194-1991194',
        source_file='data/processed/legal_review/team_final_interpretive_evidence_20261028.json')]
    completion['wording_updates']['DE_WH_POL_03'] = previous
    completion.update(unresolved_policy_ids=[], additional_excluded_scope_issues={},
        unresolved_reason=None, internal_content_review_complete=True,
        agency_confirmations_obtained=False, lawyer_signed=False,
        interpretations_not_agency_rulings=['AU_462_FIRST_POL_05','DE_WH_POL_03'],
        meaning='All current-catalog policy texts have dated bounded internal adjudications. Two explicit reviewer interpretations are retained, not passed off as agency rulings. No individual eligibility or production gate is granted.')
    path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Published last two conditional rule interpretations; no agency or lawyer sign-off claimed.')


if __name__ == '__main__':
    main()

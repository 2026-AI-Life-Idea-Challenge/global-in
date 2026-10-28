"""Record Germany scope observations; preserve source text and approval gates."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'data/processed/legal_review'
DATE = '2026-10-28'
LAW = 'https://www.gesetze-im-internet.de/aufenthg_2004/'

# Reviewer paraphrases, not quotations or approval of individual eligibility.
NOTES = {
 'DE_OPP_POL_01': ('20a', '독일에서 인정되는 전문인력 경로는 점수 경로와 구분한다. 점수·언어 증명 면제와 생계 확보 요건을 혼동하지 않는다.'),
 'DE_OPP_POL_02': ('20a,20b,anlage', '점수 경로는 인정 대상 외국 자격, 독일어 A1 또는 영어 B2 및 최소 6점을 함께 검토한다. §20b상 신청 시 만 35세 이하는 2점, 35세 초과 40세 이하는 1점이다. 언어 점수 중복과 경력 산정 기간은 별도 확인한다.'),
 'DE_SKILLED_POL_01': ('18a', '직업교육 전문인력은 자격을 요하는 취업을 할 수 있다. 모든 일자리가 허용된다는 뜻은 아니다. 규제 직업 면허, 고용 승인, 45세 관련 조건은 별도 심사한다.'),
 'DE_SKILLED_POL_02': ('', '학위 전문인력 경로의 공식 안내는 확인했으나 §18b 및 공통 §18 본문 직접 열람은 시간 초과로 완료하지 못했다. 공통 요건과 45세 관련 예외는 보류한다.'),
 'DE_BLUE_CARD_POL_01': ('18g', '자격과 직무의 적합성, 최소 6개월 고용 및 해당 연도 급여 기준을 함께 적용한다. 동등 고등교육 자격은 최소 3년 및 ISCED/EQF 수준 조건을 확인한다. 2026년 안내의 일반 급여 기준은 연 50,700유로이다.'),
 'DE_BLUE_CARD_POL_02': ('18g', '부족 직종은 법정 ISCO 분류로 확인한다. 2026년 하한 연 45,934.20유로와 연방고용청 승인 조건을 함께 기록하며 직함만으로 부족 직종을 확정하지 않는다.'),
 'DE_BLUE_CARD_POL_03': ('18g', '신규 졸업자 경로는 신청 전 학위 취득 후 3년 이하인 경우를 포함한다(§18g(1)). 원문 안내의 less than 3 years를 엄격한 3년 미만으로 적용하지 않는다. 하한 급여와 연방고용청 승인도 필요하며 갱신은 별도 조건이다.'),
 'DE_BLUE_CARD_POL_04': ('18g', '무학위 IT 경로는 해당 직종 분류, 최근 7년 중 최소 3년의 학위 수준 경력, 최소 6개월 고용, 급여 및 연방고용청 승인을 함께 확인한다.'),
 'DE_STUDY_VISA_POL_01': ('16b', '원칙적인 전일제 입학과 조건부 입학·준비 과정·시간제의 별도 허가 경로를 구분한다. 모든 교육기관의 입학이 동일한 체류 근거가 되는 것은 아니다.'),
 'DE_STUDY_VISA_POL_02': ('16b', '2026년 공식 안내의 연 11,904유로는 입학 후 유학 경로의 기준이다. 차단계좌 외 장학금·보증서 대안과 입학처 탐색 경로의 월 1,091유로를 구분한다.'),
 'DE_STUDY_VISA_POL_03': ('16b', '언어 증명은 입학 심사에서 이미 확인되지 않았고 준비 과정에서 취득할 예정도 아닌 경우 요구된다(§16b(1)). 안내의 통상 B2를 모든 신청자의 일률적 별도 증명 의무로 적용하지 않는다.'),
 'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_01': ('17', '§17(2)는 학업 자격이 이미 있거나 최대 9개월 탐색 체류 중 취득할 수 있는 경우를 포함한다. §17(1)의 직업훈련 탐색 연령 제한을 대학 입학처 탐색에 옮겨 적용하지 않는다.'),
 'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_02': ('17', '§17(2)의 언어 조건은 이미 충족하거나 해당 탐색 체류 중 충족할 수 있는 경우를 포함한다. 반드시 입국 전 전부 충족해야 한다는 요건으로 축약하지 않는다.'),
 'DE_SEEKING_HIGHER_EDUCATION_PLACE_POL_03': ('17', '생계 확보를 별도로 확인한다. 2026년 안내의 월 1,091유로와 차단계좌·보증서 대안을 기록한다. 최대 체류 기간 및 부수 취업은 유학 허가와 구분한다.'),
 'DE_WH_POL_01': ('wh', '한국 국적 대상 워킹홀리데이는 최대 12개월이며 취업은 여행 경비 보충 목적이라는 안내 범위를 보존한다.'),
 'DE_WH_POL_02': ('wh', '서울 독일 공관 안내의 신청 시 18~34세, 자녀 동반 불가 및 배우자 별도 자격 조건을 보존한다. 배우자 동반과 모든 가족의 독립 입국을 동일시하지 않는다.'),
 'DE_WH_POL_03': ('wh', '기본 3,500유로와 항공권·선납 숙소 관련 감액 증빙을 구분한다. 감액의 중복 적용은 자동 계산하지 않는다. 최근 발급 영문 잔고 및 전 체류 기간 보험의 담보별 조건을 보존한다.'),
 'DE_WH_POL_04': ('wh', '수수료 75유로의 원화 환산은 신청일 환율에 따르며 환불 조건과 분리한다. 원화 고정 금액으로 저장하지 않는다.'),
 'DE_WH_POL_05': ('wh', '통상 3~5일은 처리 보장이 아니다. 추가 서류, 본인 신청 및 1회 참여 조건을 각각 보존한다.'),
}


def main():
    raw = (OUT/'inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    snapshot = json.loads(raw)
    de = {p['policy_id']: p for p in snapshot['policy_candidates'] if p['policy_id'].startswith('DE_')}
    assert set(de) == set(NOTES) and len(de) == 19
    records = {}
    for pid, (sections, note) in NOTES.items():
        urls = []
        for section in sections.split(',') if sections else []:
            urls.append('https://seoul.diplo.de/kr-ko/service/1694216-1694216' if section == 'wh' else LAW + ('anlage.html' if section == 'anlage' else '__'+section+'.html'))
        if sections != 'wh':
            guide = ('opportunity-card/job-search' if 'OPP' in pid else
                     'visa-types/qualified-professionals' if 'SKILLED' in pid else
                     'visa-types/eu-blue-card' if 'BLUE_CARD' in pid else 'visa-types/studying')
            urls.append('https://www.make-it-in-germany.com/en/visa-recognition/'+guide)
        records[pid] = dict(policy_id=pid, program_id=de[pid]['program_id'], reviewer_paraphrase=note,
            official_sources_read=urls, source_capture_method='official web page read on 2026-10-28; no local source hash asserted',
            pending_items=['적용 시점·경과조치·개별 예외에 대한 최종 법률 승인 미완료', '§18 및 §18b 직접 대조 미완료'] if 'SKILLED' in pid else ['최종 법률 승인 및 개별 적용 심사 미완료'],
            original_policy_text_changed=False, legal_validation_approved=False, database_applied=False)
    result = dict(reviewed_at=DATE, input_sha256=hashlib.sha256(raw).hexdigest(), policies=records,
        summary=dict(total=19, scope_notes_recorded=19, final_legal_validation_completed=0, database_changed=False),
        limitations=['공식 웹 열람에 근거한 검토자 요약이며 법령 원문 인용이나 최종 승인 기록이 아니다.', '§18 및 §18b 직접 본문은 시간 초과로 확인 미완료. 급여는 2026년 안내 값이며 매년 재확인한다.'])
    (OUT/'germany_statutory_scope_20261028.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    au = json.loads((ROOT/'docs/legal_review/australia_policy_review_20261028.json').read_text(encoding='utf-8'))
    au_ids = {p['policy_id'] for p in snapshot['policy_candidates'] if p['policy_id'].startswith('AU_')}
    assert {p['policy_id'] for p in au['policy_reviews']} == au_ids and len(au_ids) == 223
    followup = dict(reviewed_at=DATE, input_sha256=result['input_sha256'], countries=dict(
        australia=dict(total=223, existing_source_comparison_records=223, newly_completed_statutory_reviews=0,
            pending_policy_ids=sorted(au_ids), next_action='비자별 법령·위임명령과 면제·경과조치 대조. 기존 DOM 대조를 법률 승인으로 계산하지 않는다.'),
        germany=result['summary']), total_coverage=242, final_legal_validation_completed=0, database_changed=False, embedding_run=False)
    followup_path = OUT/'australia_germany_followup_20261028.json'
    if followup_path.exists():
        previous = json.loads(followup_path.read_text(encoding='utf-8'))
        assert previous['input_sha256'] == result['input_sha256']
        if previous['countries']['australia'].get('statutory_scope_records'):
            followup['countries']['australia'].update(previous['countries']['australia'])
    followup_path.write_text(json.dumps(followup, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    path = ROOT/'docs/legal_review/progress_20261028.json'
    progress = json.loads(path.read_text(encoding='utf-8'))
    progress['germany_statutory_scope'] = result['summary']
    progress.setdefault('australia_germany_followup', {}).update(total=242, coverage_records=242, germany_scope_notes=19, australia_statutory_pending=223, final_legal_validation_completed=0)
    path.write_text(json.dumps(progress, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()

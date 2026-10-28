"""Publish dated follow-up findings; preserve the immutable original input."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'data/processed/legal_review'


def main():
    path = OUT / 'policy_hold_followup_20261028.json'
    follow = json.loads(path.read_text(encoding='utf-8'))
    checkpoint = json.loads((OUT / 'policy_content_approval_registry_checkpoint_553_20261028.json').read_text(encoding='utf-8'))
    ca_source = 'https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/study-permits/post-graduation-work-permit-program.html'
    additions = {
        'CA_PGWP_POL_01': ' 180일은 최종 성적 통지·수료 서면 통지·학위 등 증서 발급 중 최초 시점부터 계산하며 졸업식 날짜로 임의 대체하지 않는다.',
        'CA_PGWP_POL_03': ' 경과조치: 비대학 기관의 학사·석사·박사 학위 졸업자가 2024-11-01부터 2025-03-10까지 PGWP를 신청한 경우 CLB/NCLC 5 기준이며 2025-03-11부터 학위 졸업자 7 기준이다. 여권 유효기간 때문에 단축된 최초 PGWP의 연장 및 허가 조건 변경의 지정 언어 면제도 구분한다.',
        'CA_PGWP_POL_04': ' 2024-11-01 전 study permit 신청에 따른 전공 면제는 동일 학업을 마치기 위한 이후 연장에도 적용 가능하다. 과거 permit 보유만으로 그날 이후 새 study permit 신청까지 면제하지 않는다.',
        'CA_PGWP_POL_07': ' 업무 지침상 캐나다 내 R199 신청 자격과 R197의 국외 처리 신청을 구분한다. 유학허가가 만료·무효인 경우 방문자 신분 유지 자체로 R199 자격이 생기지 않는다. R182 회복을 통한 동시 신청은 새 입학허가서 등 정규 유학허가 요건 및 그 허가 발급을 조건으로 처리하며 승인 전 R186(w) 취업을 허용하지 않는다.'
    }
    for pid, suffix in additions.items():
        follow['wording_updates'][pid] = dict(text=checkpoint['policies'][pid]['reviewed_policy_text'] + suffix,
            scope='IRCC 업무 지침의 해당 PGWP 조건 및 명시된 경과조치. 원본 NULL 유지·개별 적격/취업 판단 제외.',
            findings=['기존 승인 문구에 누락된 업무 지침의 날짜·예외·절차 분기를 대조해 새 버전으로 보완했다.'],
            source_urls=[ca_source], capture_file='follow_ca_operational_web_capture_20261028.json')
    for pid, row in checkpoint['review_queue'].items():
        if row['legal_validation_approved'] or pid in follow['wording_updates']:
            continue
        if pid.startswith('US-WEST-'):
            item = dict(lifecycle_disposition='historical_notice_excluded', review_closed_for_current_catalog=True,
                reason='2026 상반기 특정 모집 공고의 과거 레코드. 현행 일반 정책으로 승인하지 않고 원문·기간을 보존한다.',
                next_action='향후 공고는 새 기간·새 ID로 별도 검토. 기존 H1 ID를 H2 문구로 덮어쓰지 않는다.',
                successor_notice_url='https://www.niied.go.kr/web/niied/nid/niied_board/5749',
                successor_approved=False,
                followup_finding='H2 공식 공고 존재 확인. 보유 H2 PDF는 공고(안) 표기·FAQ 오류·재정 차이 및 첨부파일 출처 독립 확인이 남아 현행 승인에 사용하지 않는다.')
        else:
            item = dict(followup_checked_at='2026-10-28', review_closed_for_current_catalog=False)
            if pid.startswith('US-'):
                item['followup_finding'] = 'H-1B: 2026-09-30 Doc130 p34의 시행정책 vacatur·금지명령 확인. F-1: 2026-09-14 Doc50은 APA705 시행 연기이며 vacatur는 기각(재신청 가능). 이후 항소·명령 변동까지 확인한 것은 아니므로 현재 효력 보류 유지.'
            elif pid == 'DE_WH_POL_03':
                item['followup_finding'] = '공관 독일어 원문의 각 EUR1000 공제·각 지급증명 문구 확인. 두 공제 합산 최저액의 명시적 설명은 확보하지 못해 EUR1500 자동 산정 보류.'
            elif pid == 'AU_462_FIRST_POL_05':
                item['followup_finding'] = '법정 영어 증빙의 신청 후 시험 경로와 안내문 신청 전 12개월의 차이 및 Minister 판단 경로를 확인할 명시적 근거가 필요하다.'
            else:
                item['followup_finding'] = 'Thapa 및 Herath 2024 FCA547 원문 접근 실패. 2차 요약만으로 후속 판례와 현행 기술심사 날짜 경로를 승인하지 않았다.'
        follow['remaining_dispositions'][pid] = item
    path.write_text(json.dumps(follow, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert len(follow['remaining_dispositions']) == 34
    print('7 wording versions; 20 historical exclusions; 14 active holds')


if __name__ == '__main__':
    main()

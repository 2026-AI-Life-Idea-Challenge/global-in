"""Produce reviewable correction candidates and a single consistent progress report."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from resolve_us_jp_review import update_progress

ROOT = Path(__file__).resolve().parents[4]


def save(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    base = json.loads((ROOT / 'data/processed/legal_review/us_jp_policy_review_20261028.json').read_text(encoding='utf-8'))
    batch = json.loads((ROOT / 'data/processed/legal_review/us_jp_remaining_scope_20261028.json').read_text(encoding='utf-8'))
    snapshot_raw = (ROOT / 'data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json').read_bytes()
    assert hashlib.sha256(snapshot_raw).hexdigest() == base['input_sha256'] == batch['input_sha256']
    policies = {p['policy_id']: p for p in json.loads(snapshot_raw)['policy_candidates']}
    rows = {k:v for group in base['policies'].values() for k,v in group.items()}
    assert len(rows) == base['detailed_scope_review_count'] == 327
    assert all(r.get('detailed_scope_review') and not r['legal_validation_completed'] and not r['approved_for_eligibility_decision'] for r in rows.values())
    candidates = []
    for pid, row in rows.items():
        review = row['detailed_scope_review']
        issues = list(review.get('issue_codes') or [])
        if pid in base['six_month_boundary_policy_ids']:
            issues.append('evaluation_exactly_six_months_boundary_requires_regulation_over_brochure')
        if not issues:
            continue
        action = 'retain_hold_pending_authority_review' if set(issues) & {'court_order_scope_unresolved', 'fee_employer_threshold_and_sunset_review'} else 'versioned_correction_candidate'
        proposal = {'reviewer_text': review.get('finding') or review.get('findings'),
                    'original_policy_text': policies[pid]['policy_text']}
        if row['country'] == 'japan':
            scope = review['application_scope']
            proposal.update(application_type=scope['application_type'],
                            school_category=scope['school_category'],
                            school_classification=scope['school_classification'])
            if 'nationality_column_scalar_status_unsafe' in issues:
                proposal['requirement_status'] = 'varies_by_nationality_column'
                proposal['requirement_symbols_by_nationality'] = scope['observed_requirement_symbols']
                proposal['nationality_group_membership_verified'] = False
            if 'source_condition_missing_in_structured_record' in issues:
                proposal['condition_original_ja'] = scope['source_condition_ja']
            if 'renewal_row_group_condition_requires_preservation' in issues:
                proposal['row_group_condition_original_ja'] = scope['row_group_condition_ja']
        if 'trailing_or_extraction_boundary' in issues:
            original = policies[pid]['policy_text']
            assert original.endswith('; or')
            proposal['clean_clause_candidate'] = original[:-4] + '.'
        if 'evidence_context_review' in review:
            proposal['reviewed_evidence_context'] = review['evidence_context_review']
        candidates.append(dict(policy_id=pid, program_id=row['program_id'], country=row['country'],
                               action=action, issue_codes=issues, proposal=proposal,
                               source_urls=review.get('source_urls') or [review['source_url']],
                               legal_reference=review.get('legal_reference_check'),
                               approved_for_user_answers=False, approved_for_embedding=False,
                               legal_validation_approved=False, approved_for_eligibility_decision=False,
                               database_applied=False))
    assert len(candidates) == 36
    counts = Counter(c['action'] for c in candidates)
    assert counts['versioned_correction_candidate'] == 26 and counts['retain_hold_pending_authority_review'] == 10
    context_count = sum('evidence_context_review' in r['detailed_scope_review'] for r in rows.values())
    assert context_count == 6
    jp_rows = [r['detailed_scope_review'] for r in rows.values() if 'official_pdf_row' in r['detailed_scope_review']]
    assert len(jp_rows) == 141
    assert sum('nationality_column_scalar_status_unsafe' in r.get('issue_codes', []) for r in jp_rows) == 9
    anchor_rows = [r['detailed_scope_review']['legal_reference_check'] for r in rows.values() if 'legal_reference_check' in r['detailed_scope_review']]
    assert all(a['paragraph_anchor_found'] for a in anchor_rows)
    save('data/processed/legal_review/us_jp_scope_correction_candidates_20261028.json',
         dict(reviewed_at='2026-10-28', input_sha256=base['input_sha256'],
              definition='Review proposals only; source quotations and DB not overwritten; not publishable approvals',
              action_counts=dict(counts), candidates=candidates))
    progress = json.loads((ROOT / 'docs/legal_review/progress_20261028.json').read_text(encoding='utf-8'))
    progress['stage'] = 'us_jp_scope_recording_complete_legal_resolution_pending'
    progress['us_jp_detailed_scope_review'] = dict(total=327, recorded=327, remaining=0, percent=100,
        definition='policy-specific scope observations recorded, including unresolved issues; not final legal validation',
        country_counts=base['country_counts'], added_in_this_batch=300,
        previous_recorded=27, scope_correction_candidates=26, priority_authority_holds=10,
        context_clauses_checked=6, original_broad_evidence_reextraction_pending=6,
        official_pdf_table_rows_reextracted=141, legal_paragraph_anchors_checked=len(anchor_rows),
        legal_resolution_complete=False)
    progress['final_legal_validation_completed'] = 0
    progress['final_legal_validation_percent'] = 0
    progress['database_changed'] = False
    save('docs/legal_review/progress_20261028.json', progress)
    summary = dict(reviewed_at='2026-10-28', input_sha256=base['input_sha256'],
                   scope_recorded=327, scope_total=327, new_records=300,
                   issue_counts=batch['issue_counts'], correction_action_counts=dict(counts),
                   original_evidence_context_pending=6, pdf_rows=141,
                   legal_paragraph_anchors=len(anchor_rows),
                   final_legal_validation_completed=0, database_changed=False)
    save('docs/legal_review/us_jp_scope_summary_20261028.json', summary)
    lines = [
        '# 미국·일본 적용 범위 상세 검토 기록', '',
        '기준일: 2026-10-28. 기존 27개에 남은 300개를 추가해 미국 161개·일본 166개, 총 327개에 정책별 검토 기록을 작성했다. 이 단계는 미해소 쟁점까지 기록하는 작업이며 최종 법률 승인과 다르다.', '',
        '## 이번에 확인하고 반영한 내용', '',
        '- 일본 취업·유학 141개: 공식 PDF 13개의 제목·표 열·비고를 화면으로 확인하고 표 셀을 다시 추출했다. 원문 PDF 해시와 연결한 뒤 COE·변경·갱신, 학교 분류, 소속 기관 카테고리, 국적별 열, 조건부·공란·대시를 별도로 보존했다.',
        '- 일본 국적 열 9개: 기존 단일 상태값으로는 적용 범위를 표현할 수 없어 국적 열별 기호를 교정 후보에 기록했다. 별표 국적 목록의 실제 구성 확인은 아직 남아 있다.',
        '- 일본 갱신 6개: 페이지 상단의 이직 후 첫 갱신 조건과 언어업무 변경 주석을 행에 연결했다. 갱신 13번의 카테고리 3 제외도 보존했다.',
        '- 일본 초중등학교 표 14번: 가공본에서 누락된 초등학교·중학교 진학 조건을 원문 셀에서 복원해 별도 교정 후보로 기록했다.',
        '- 미국: 정책 ID별로 신청자·고용주·스폰서·호스트·당국의 의무를 구분하고 회계연도·모집 회차·선택 경로·기간·절차를 기록했다. 확인 가능한 eCFR 문단은 앵커 존재와 문단 해시를 별도로 기록했다. 앵커 존재는 정책의 법적 타당성 승인과 다르다.',
        '- J-1: 현장방문 기준의 AND/OR 충돌 2개와 인턴 전일제 조건 1개를 추가 확인했다. 기존 6개월 평가 경계 2개와 함께 교정 후보에 포함했다.',
        '- J-1/SWT 문맥 6개: 정책 문장이 현재 공식 본문에서 재현되는지 다시 확인하고 의무 주체와 법조문을 연결했다. 원래의 넓은 evidence 인용 전체를 재추출하는 작업은 여전히 남는다.',
        '- 그 외: F-1 끝의 or 추출 흔적, J-1 college 선정·비학위 조건 혼합, SWT의 VWP 문단에 섞인 일반 임금·연락 의무, H-1B 임금 발생 시점 및 복합 정책을 교정 후보로 정리했다.', '',
        '## 처리 상태', '',
        '| 지표 | 결과 |', '|---|---:|',
        '| 미국·일본 상세 검토 기록 | 327/327, 100% |',
        '| 이번 추가 기록 | 300 |',
        '| 구체적인 교정 후보 | 26개 정책 |',
        '| 우선 효력·규칙 확인 보류 | 10개 정책 |',
        '| 전체 최종 법률 승인 | 0/590, 0% |', '',
        '우선 보류 10개는 H-1B 납부·법원 명령 8개와 수수료 적용범위·종료일 2개다. 26개 교정 후보와 10개 우선 보류는 서로 다른 정책 ID다. 이것이 남은 법률 검증 전체 목록은 아니다. 나머지 정책도 개별 예외·법령 근거·현행 효력 확인과 최종 승인 전까지 보류를 유지한다. WEST 20개는 2026년 상반기 공고의 범위이며 현재 모집을 확인한 것으로 처리하지 않는다.', '',
        '## 다음 작업', '',
        '1. 교정 후보 26개의 버전과 근거를 확정한다. 일본 별표 국적 구성, 공통 비고의 세부 적용과 미국 복합 문장의 분리를 함께 확인한다.',
        '2. H-1B 납부 8개의 판결 주문·후속 명령과 수수료 2개의 고용주 기준·접수 유형·법정 종료일을 확인한다.',
        '3. 원래 evidence 문맥 6개를 재추출하고 전체 정책의 법률·예외 검토를 이어간다. 호주·캐나다·독일도 기존 미해소 사항의 최종 검증이 남아 있다.', '',
        '## 파일과 재현', '',
        '- 정본 원장: `data/processed/legal_review/us_jp_policy_review_20261028.json`',
        '- 이번 300개 상세 결과: `data/processed/legal_review/us_jp_remaining_scope_20261028.json`',
        '- 36개 정책의 교정·보류 제안: `data/processed/legal_review/us_jp_scope_correction_candidates_20261028.json`',
        '- 집계: `docs/legal_review/us_jp_scope_summary_20261028.json`', '',
        '```powershell',
        '.venv\\Scripts\\python.exe scripts/ingest/common/legal_review/build_remaining_us_jp_scope.py',
        '.venv\\Scripts\\python.exe scripts/ingest/common/legal_review/audit_us_jp_official_review.py',
        '.venv\\Scripts\\python.exe scripts/ingest/common/legal_review/summarize_us_jp_scope.py',
        '```', '',
        '재실행은 확보된 원문과 기록된 검토 관찰을 재현한다. 새 시점의 웹 재확인으로 집계하지 않는다. 원본 22개 미국·일본 가공 JSON과 DB를 변경하지 않으며 승인 플래그를 올리지 않는다.', '',
        '## 정책별 교정·우선 보류 목록', '',
        '| 정책 ID | 처리 | 쟁점 |', '|---|---|---|',
    ]
    for c in candidates:
        lines.append('| '+c['policy_id']+' | '+('교정 후보' if c['action']=='versioned_correction_candidate' else '효력·규칙 확인 보류')+' | '+', '.join(c['issue_codes'])+' |')
    (ROOT / 'docs/legal_review/us_jp_scope_review_20261028.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    update_progress()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

# 미국·일본 적용 범위 상세 검토 기록

기준일: 2026-10-28. 기존 27개에 남은 300개를 추가해 미국 161개·일본 166개, 총 327개에 정책별 검토 기록을 작성했다. 이 단계는 미해소 쟁점까지 기록하는 작업이며 최종 법률 승인과 다르다.

## 이번에 확인하고 반영한 내용

- 일본 취업·유학 141개: 공식 PDF 13개의 제목·표 열·비고를 화면으로 확인하고 표 셀을 다시 추출했다. 원문 PDF 해시와 연결한 뒤 COE·변경·갱신, 학교 분류, 소속 기관 카테고리, 국적별 열, 조건부·공란·대시를 별도로 보존했다.
- 일본 국적 열 9개: 기존 단일 상태값으로는 적용 범위를 표현할 수 없어 국적 열별 기호를 교정 후보에 기록했다. 별표 국적 목록의 실제 구성 확인은 아직 남아 있다.
- 일본 갱신 6개: 페이지 상단의 이직 후 첫 갱신 조건과 언어업무 변경 주석을 행에 연결했다. 갱신 13번의 카테고리 3 제외도 보존했다.
- 일본 초중등학교 표 14번: 가공본에서 누락된 초등학교·중학교 진학 조건을 원문 셀에서 복원해 별도 교정 후보로 기록했다.
- 미국: 정책 ID별로 신청자·고용주·스폰서·호스트·당국의 의무를 구분하고 회계연도·모집 회차·선택 경로·기간·절차를 기록했다. 확인 가능한 eCFR 문단은 앵커 존재와 문단 해시를 별도로 기록했다. 앵커 존재는 정책의 법적 타당성 승인과 다르다.
- J-1: 현장방문 기준의 AND/OR 충돌 2개와 인턴 전일제 조건 1개를 추가 확인했다. 기존 6개월 평가 경계 2개와 함께 교정 후보에 포함했다.
- J-1/SWT 문맥 6개: 정책 문장이 현재 공식 본문에서 재현되는지 다시 확인하고 의무 주체와 법조문을 연결했다. 원래의 넓은 evidence 인용 전체를 재추출하는 작업은 여전히 남는다.
- 그 외: F-1 끝의 or 추출 흔적, J-1 college 선정·비학위 조건 혼합, SWT의 VWP 문단에 섞인 일반 임금·연락 의무, H-1B 임금 발생 시점 및 복합 정책을 교정 후보로 정리했다.

## 처리 상태

| 지표 | 결과 |
|---|---:|
| 미국·일본 상세 검토 기록 | 327/327, 100% |
| 이번 추가 기록 | 300 |
| 구체적인 교정 후보 | 26개 정책 |
| 우선 효력·규칙 확인 보류 | 10개 정책 |
| 전체 최종 법률 승인 | 0/590, 0% |

우선 보류 10개는 H-1B 납부·법원 명령 8개와 수수료 적용범위·종료일 2개다. 26개 교정 후보와 10개 우선 보류는 서로 다른 정책 ID다. 이것이 남은 법률 검증 전체 목록은 아니다. 나머지 정책도 개별 예외·법령 근거·현행 효력 확인과 최종 승인 전까지 보류를 유지한다. WEST 20개는 2026년 상반기 공고의 범위이며 현재 모집을 확인한 것으로 처리하지 않는다.

## 다음 작업

1. 교정 후보 26개의 버전과 근거를 확정한다. 일본 별표 국적 구성, 공통 비고의 세부 적용과 미국 복합 문장의 분리를 함께 확인한다.
2. H-1B 납부 8개의 판결 주문·후속 명령과 수수료 2개의 고용주 기준·접수 유형·법정 종료일을 확인한다.
3. 원래 evidence 문맥 6개를 재추출하고 전체 정책의 법률·예외 검토를 이어간다. 호주·캐나다·독일도 기존 미해소 사항의 최종 검증이 남아 있다.

## 파일과 재현

- 정본 원장: `data/processed/legal_review/us_jp_policy_review_20261028.json`
- 이번 300개 상세 결과: `data/processed/legal_review/us_jp_remaining_scope_20261028.json`
- 36개 정책의 교정·보류 제안: `data/processed/legal_review/us_jp_scope_correction_candidates_20261028.json`
- 집계: `docs/legal_review/us_jp_scope_summary_20261028.json`

```powershell
.venv\Scripts\python.exe scripts/ingest/common/legal_review/build_remaining_us_jp_scope.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/audit_us_jp_official_review.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/summarize_us_jp_scope.py
```

재실행은 확보된 원문과 기록된 검토 관찰을 재현한다. 새 시점의 웹 재확인으로 집계하지 않는다. 원본 22개 미국·일본 가공 JSON과 DB를 변경하지 않으며 승인 플래그를 올리지 않는다.

## 정책별 교정·우선 보류 목록

| 정책 ID | 처리 | 쟁점 |
|---|---|---|
| US-WK-01-POL-0008 | 효력·규칙 확인 보류 | court_order_scope_unresolved |
| US-WK-01-POL-EMP-003 | 교정 후보 | wage_start_trigger_requires_clarification |
| US-WK-01-POL-0007 | 효력·규칙 확인 보류 | court_order_scope_unresolved |
| US-WK-01-POL-0001 | 효력·규칙 확인 보류 | fee_employer_threshold_and_sunset_review |
| US-WK-01-POL-0072 | 효력·규칙 확인 보류 | court_order_scope_unresolved |
| US-WK-01-POL-0103 | 효력·규칙 확인 보류 | court_order_scope_unresolved |
| US-J1-INTERN-POL-008 | 교정 후보 | evaluation_exactly_six_months_boundary_requires_regulation_over_brochure |
| US-J1-INTERN-POL-001 | 교정 후보 | full_time_condition_missing_in_brochure |
| US-J1-INTERN-POL-005 | 교정 후보 | site_visit_and_or_conflict |
| US-J1-TRAINEE-POL-008 | 교정 후보 | site_visit_and_or_conflict |
| US-J1-TRAINEE-POL-011 | 교정 후보 | evaluation_exactly_six_months_boundary_requires_regulation_over_brochure |
| US-F1-POL-006 | 교정 후보 | trailing_or_extraction_boundary |
| US-J1-COLLEGE-POL-001 | 교정 후보 | selection_and_nondegree_conditions_mixed |
| US-SWT-POL-009 | 교정 후보 | vwp_heading_overgeneralizes_wage_and_monitoring |
| US-WK-01-POL-0022 | 효력·규칙 확인 보류 | court_order_scope_unresolved |
| US-WK-01-POL-0053 | 효력·규칙 확인 보류 | court_order_scope_unresolved |
| US-WK-01-POL-0057 | 효력·규칙 확인 보류 | court_order_scope_unresolved |
| US-WK-01-POL-0061 | 효력·규칙 확인 보류 | fee_employer_threshold_and_sunset_review |
| US-WK-01-POL-0092 | 교정 후보 | multiple_legal_subjects_require_split |
| US-WK-01-POL-0100 | 효력·규칙 확인 보류 | court_order_scope_unresolved |
| JP-POL-c08a57e18828062296b1df68 | 교정 후보 | renewal_row_group_condition_requires_preservation |
| JP-POL-6ecaea9a53746d2375e1030a | 교정 후보 | renewal_row_group_condition_requires_preservation |
| JP-POL-24b8dcfa215958b1c273d206 | 교정 후보 | renewal_row_group_condition_requires_preservation |
| JP-POL-7b1270fdbb1a4af5185bbf4e | 교정 후보 | renewal_row_group_condition_requires_preservation |
| JP-POL-010dbd338448e60e988b89f8 | 교정 후보 | renewal_row_group_condition_requires_preservation |
| JP-POL-d9230a5db8928c5c381eb6a4 | 교정 후보 | renewal_row_group_condition_requires_preservation |
| JP-POL-3228e6b88dd0a3afc04560d6 | 교정 후보 | source_condition_missing_in_structured_record |
| JP-POL-dea199897c1c19accaa2c825 | 교정 후보 | nationality_column_scalar_status_unsafe |
| JP-POL-56ae4c8b16ed9662e837ac2d | 교정 후보 | nationality_column_scalar_status_unsafe |
| JP-POL-1876437904d6e87279c3d1a1 | 교정 후보 | nationality_column_scalar_status_unsafe |
| JP-POL-0d70e9278e88f64b8c077284 | 교정 후보 | nationality_column_scalar_status_unsafe |
| JP-POL-1b88638293274a686b68dfd8 | 교정 후보 | nationality_column_scalar_status_unsafe |
| JP-POL-f8e5c63e09ac1cf41f14d627 | 교정 후보 | nationality_column_scalar_status_unsafe |
| JP-POL-28f3d28212d56e8d0e20f62d | 교정 후보 | nationality_column_scalar_status_unsafe |
| JP-POL-83a9c91916eefaa8685b916e | 교정 후보 | nationality_column_scalar_status_unsafe |
| JP-POL-9546044a4ab845b176431d0b | 교정 후보 | nationality_column_scalar_status_unsafe |

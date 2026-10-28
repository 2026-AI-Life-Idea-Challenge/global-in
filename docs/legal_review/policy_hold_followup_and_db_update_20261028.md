# 후속 검토 및 DB 반영 — 2026-10-28

정책 문구 승인 556/590개(94.24%), 과거 모집 공고 제외 20개, 추가 법률 확인 보류 14개다. 원본 590개를 분모로 유지했다. 과거 공고 제외는 승인이 아니다. 독립 변호사 서명과 서비스 사용 승인은 0개다.

## 이번 보완

- 캐나다 PGWP 06: IRCC 업무 지침의 타주 제휴과정 2023-02-01, 동일 주 제휴과정 2024-05-15의 당일 포함 부적격 경계를 출처에 한정해 명시했다. 일반 안내와의 표현 차이를 자동 개인 판정에 사용하지 않는다.
- 캐나다 PGWP 01·03·04·07: 180일 기산점, 비대학 학위 졸업자 언어 요건의 2025-03-11 경과조치, 기존 학업 연장과 새 유학허가 신청의 전공 면제 차이, R199/R197/R182 절차를 보완했다.
- 미국 F-1 005·006: 신규 학생 365일 사증 발급과 30일 입국 경계를 구분하고 계속 재학 예외를 보존했다. 체류기간 소송 효력은 승인 범위에 포함하지 않는다.
- WEST 상반기 20개: 과거 공고로 분류하고 H2 공식 공고를 연결했다. H1 ID를 H2 문구로 덮어쓰지 않았다. 보유 H2 PDF의 공고(안) 표기·출처 독립 확인·FAQ/재정 쟁점은 기존 H2 검토 자료와 함께 남겼다.

근거: [IRCC 업무 지침](https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals/temporary-residents/study-permits/post-graduation-work-permit-program.html), [미 국무부 학생 비자](https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html), [NIIED H2 공고](https://www.niied.go.kr/web/niied/nid/niied_board/5749). 저장한 웹 결과의 해시는 서버 원본 HTML 바이트와 같은 의미가 아니다.

## 남은 14개와 해제 조건

| 묶음 | 개수 | 다음 확인 |
|---|---:|---|
| 미국 H-1B 포고령·시행정책 | 8 | 2026-09-30 Doc130 이후 항소·집행정지·명령 변경을 공식 사건 자료로 확인 |
| 미국 cap-gap | 1 | F-1 규칙 시행 연기와 이후 항소 명령이 해당 현행 조문에 미치는 범위 확인 |
| 호주 Thapa 관련 기술심사 | 3 | Thapa 주문과 Herath 등 후속 1차 판례 및 현행 행정 적용 대조 |
| 호주 462 영어 | 1 | 법령의 신청 후 시험 경로와 안내문의 신청 전 시험 기준, 장관 판단 경로의 명시적 관계 확인 |
| 독일 WH 재정 | 1 | 항공권·숙박 공제의 중첩 가능 범위에 관한 공관 명시 안내 확인 |

F-1 2026-09-14 명령은 APA705에 따른 시행 연기다. vacatur 등 추가 구제는 재신청 가능하게 기각했다. H-1B 2026-09-30 Doc130 p34는 시행정책 vacatur·환송 및 지정 절차 전 시행 금지를 명시한다. 각 주문의 의미와 이후 현재 효력 확인 완료를 구분한다. 접근하지 못한 원문과 확인하지 못한 후속 사건을 확인 완료로 기록하지 않았다.

## DB 저장 범위

`policy_candidates.metadata.bounded_policy_review_20261028`에 590개 판정 및 승인 문구의 별도 버전·해시·근거·범위를 저장했다. 새 문구는 `reviewed_version.reviewed_policy_text`에서 조회할 수 있다. 원래 `policy_text`, 원문 URL 연결, 상위 법률/답변/임베딩/개인 판정 플래그는 보존했다. 따라서 현재 사용자용 정책 본문을 교체하거나 서비스 사용을 개방한 것은 아니다.

트랜잭션 내 원본 스냅샷 대조·행 잠금·변경 전 백업·메타데이터 외 컬럼 불변 검증 후 커밋했다. 별도 읽기 연결에서 저장된 590개를 재검증했다. DB 반영 영수증은 `db_review_update_20261028.json`, 백업 위치는 그 파일의 `backup_file`이다. 이 작업의 DB 저장 성공과 남은 14개 법률 쟁점의 해결은 별개다.

## 재현

```powershell
.venv\Scripts\python.exe scripts/ingest/common/legal_review/complete_policy_hold_followup.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/finalize_global_policy_wording.py --check
.venv\Scripts\python.exe scripts/evaluate/legal_review/audit_policy_content_approvals.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/apply_policy_review_metadata.py
```

마지막 명령은 읽기 전용 미리보기다. `--apply`일 때만 별도 검토 버전을 저장하며 같은 원장으로 재실행하면 변경 대상은 0개다. 검토한 스냅샷에서 DB의 원문·출처·플래그가 달라졌으면 적용을 중단한다. 이후 원장 버전이 바뀌면 재검증·백업 후 같은 방식으로 갱신한다.

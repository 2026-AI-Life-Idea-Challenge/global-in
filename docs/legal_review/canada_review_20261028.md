# 캐나다 정책 후보 21개 공식 자료 1차 대조 및 파일 반영

검토일: 2026-10-28 (Asia/Seoul). 대상: 고용주 지정 취업허가 5개, PGWP 7개, 유학허가 4개, 한국인 IEC Working Holiday 5개.

## 반영한 파일

`data/processed/canada/` 아래 기존 evidence_draft JSON 4개에 정책별 `official_review`와 파일별 검토 요약을 추가했다. 상세 내용은 `canada_policy_review_20261028.json`의 21개 레코드와 공식 출처 목록을 참조한다.

`scripts/ingest/canada/review_support.py`에 공통 검토 레지스트리를 추가하고 기존 추출 스크립트 4개에 연결했다. 원문에서 다시 생성해도 검토 정보가 유지된다. `scripts/ingest/canada/apply_canada_official_review.py`로 4개 파일을 사전 검사 후 일괄 반영하고 `--check`로 저장 결과를 검증한다.

작성한 설명은 `reviewer_summary_not_source_quote`로 구분했다. 원문 인용문이나 기존 source_text 필드를 임의로 채우지 않았다. 정책 본문 공란이라는 이전 감사 결과는 원문 source_text가 없다는 의미로 그대로 해석해야 하며, 이번 검토 문장과 혼동하지 않는다.

## 주요 보강

| 항목 | 보강 내용 | 공식 출처 |
|---|---|---|
| 유학 재정 | 신청일·퀘벡 제외·신청자 포함 가족 수·통화·학비/교통비 별도 기준을 명시한 참조 데이터 추가 | [IRCC 재정증명](https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/study-permit/get-documents/financial-support.html) |
| PGWP | 언어·전공의 서로 다른 신청일 기준, 학위/비행학교 예외, 기간 및 신분회복·대기취업 구분 | [자격](https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/eligibility.html), [서류](https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/get-documents.html), [신청](https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/apply.html), [대기 중 취업](https://www.canada.ca/en/immigration-refugees-citizenship/services/study-canada/work/after-graduation/after-you-apply.html) |
| IEC 가족 | IEC에 부양가족으로 포함되는 것과 가족이 별도로 방문·유학·취업 신청하는 것을 구분 | [가족 안내](https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility/family-members.html) |
| IEC 운영 상태 | 2026년 풀이 closed임을 조회일과 함께 기록. 기존 초청/진행 중 신청의 상태를 이 관찰로 판정하지 않음 | [프로필 및 초청](https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/become-candidate.html) |
| 취업허가 | LMIA 경로와 면제 경로, 고용주 포털·수수료 예외를 구분 | [고용주 지정 허가](https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/employer-specific.html), [IMP](https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/hire-temporary-foreign/international-mobility-program/how-to-hire.html) |

법령은 IRPR 200·203·216·220·220.1을 직접 조회했다. 법령의 조항별 예외와 안내 사이의 관계를 레코드의 pending_items로 남겼다. 조회한 Justice Laws 통합본은 2026-09-30까지의 현행 상태라고 표시돼 있으므로 10월 중 변경 여부가 별도로 남는다. PGWP 주간 제휴과정의 2023-02-01 경계에는 안내 문구상 공백이 있어 임의로 조건을 확정하지 않았다.

## 검증 결과

- 기존 추출 스크립트 4개 실행 성공: 내부 원문 위치·일관성 검사 통과.
- 21개 정책 ID의 누락·중복 없음 및 재생성 후 검토 정보 유지 확인.
- 검토 필드 외 기존 JSON 데이터가 Git HEAD와 의미적으로 동일함을 확인.
- 알 수 없는 정책 및 승인된 정책에 검토 정보를 덮어쓰는 요청은 거부됨을 확인.
- diff 공백 검사 통과.

기존 Evidence와 자격 규칙·법률 승인 상태는 보존했다. DB는 수정하지 않았다. 새로 조회한 URL은 supplementary source_references이며, 기존 Evidence ID의 공식 원문으로 바꿔치기하지 않았다.

## 진행률

- 캐나다 공식 자료 1차 대조 기록: **21/21(100%)**. 상세 법률 검증 완료율과 다르다.
- 전체 정책의 공식 자료 1차 대조 기록: 독일 19개 + 캐나다 21개 = **40/590(6.8%)**. 부분 일치와 보류 항목도 기록한 작업 범위 지표다.
- 정책별 법률 검증 완료: **0/590(0%)**. 법령의 시점·예외·보충 근거까지 닫힌 정책만 완료로 올린다.

다음 작업은 캐나다의 pending_items 중 법령 현행성·예외 근거와 경계일 문제를 먼저 해소하고, 호주 정책 223개의 공식 자료 대조를 진행하는 것이다. 모든 수정은 현 단계에서 필요한 로컬 파일에 반영했으며, 이후 DB 반영은 현재 레코드와 원래 값의 일치 여부를 먼저 검사해야 한다.

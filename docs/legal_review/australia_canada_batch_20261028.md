# 호주 전수 본문 대조 및 캐나다 예외 검토 후속 결과

기준일: 2026-10-28 (Asia/Seoul).

## 호주: 20개 프로그램, 정책 후보 223개

공식 immi.homeaffairs.gov.au 페이지 20개를 브라우저에서 직접 열고 Eligibility 및 중첩된 Details를 전부 펼쳤다. 현재 상위 조건 섹션은 225개였으며 기존 정책 후보 수 223개와 다르다. 섹션 분할·결합을 확인했으며 새 정책 ID를 자동 생성하지 않았다.

| 결과 | 정책 수 |
|---|---:|
| 정규화 본문의 SHA-256 앞 64비트 지문 일치 | 213 |
| 현재 섹션을 분할·결합하거나 기존 안내 꼬리말을 포함하면 기존 본문 재현 | 6 |
| 보관 자료에 제목만 있어 현재 조건의 검토 요약을 보강 | 4 |
| 합계 | 223 |

이는 텍스트 대조 결과다. 법령상 승인이나 원본 HTTP 바이트의 동일성 증명이 아니다. 지문 비교에는 공백·제로폭 문자 및 별도 줄의 Hide/Details UI 제거를 사용했다. 64비트 접두 지문에는 충돌 가능성이 있어 전체 원문 보관과 강한 바이트 검증을 대체하지 않는다. SHA-256 구현은 알려진 abc 테스트 벡터로 확인했다.

현재 지문 225개와 개별 정책 결과는 `australia_policy_review_20261028.json`, 재적용 로직은 `scripts/ingest/australia/review_support.py`에 기록했다. 이 명령을 재실행하는 것은 저장된 관찰과의 비교이며 웹사이트를 새로 조회하는 작업이 아니다.

## 실제 수정·보강

- 호주 기존 데이터 JSON 20개에 `official_review`와 검토 요약을 추가했다. 원래 인용문과 정책 후보·승인 플래그는 보존했다.
- 생성 스크립트 12개에 검토 정보 재부착을 연결했다. 각 스크립트가 생성하는 프로그램만 갱신해 다른 스크립트의 산출물과 쓰기 범위가 겹치지 않도록 했다.
- 189의 네 정책 `AU_189_PT_POL_01~04`는 과거 본문이 없으므로 현재 보유비자·초청·기술심사·연령 조건의 검토자 요약을 추가했다. 새 요약을 원문 인용으로 표시하지 않았다. 정식 원문 보관 및 Evidence 연결은 여전히 필요하다.
- 186 TRT의 두 정책은 현재 하나의 고용주 지명 섹션 안에서 재현됐다. 191의 소득/조건 준수 및 채무/이민 이력은 현재 두 섹션씩 결합하면 기존 두 정책과 일치했다.
- 482 Specialist의 정책 12는 현재 별도인 스폰서십 대가 금지와 영어 조건을 함께 담고 있었다. 정책 15에는 다음 절차 안내가 붙어 있었다. 분할/꼬리말 차이를 명시하고 자격 판정 규칙으로 바로 사용하지 않도록 보류했다.

주요 공식 출처: [189](https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189/points-tested), [186 TRT](https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/employer-nomination-scheme-186/temporary-residence-transition-stream), [191](https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-regional-191/regional-provisional), [482 Specialist](https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skills-in-demand-visa-subclass-482/specialist-skills-stream), [500](https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/student-500). 나머지 출처는 정책별 레코드에 기록했다.

중간 수집에서는 중첩된 버튼이 남아 491·500이 다르게 보였으나, 모든 버튼을 펼치고 UI 문구를 제외한 재검사에서 각각 11개·16개 정책 모두 일치했다. 이를 법률 내용 변경으로 집계하지 않았다.

## 캐나다 예외 교차참조 보강

캐나다 검토 레지스트리와 데이터 4개, 정책별 검토 원장을 함께 갱신했다.

- 재정요건: [IRPR 220](https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/section-220.html)의 예외가 [215(1)(d)/(e)](https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/section-215.html)에 연결됨을 확인했다. 특정 추방명령 및 최소 유효기간을 갖춘 임시거주허가 범위이며 일반 방문자에게 넓혀 적용하지 않는다.
- 출국요건: [216(2)](https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/section-216.html)가 [206](https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/section-206.html) 및 [207(c)/(d)](https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/section-207.html)를 참조함을 확인했다. 207 전체가 예외라는 규칙으로 만들면 안 된다.
- 재학·학업진행: [220.1](https://laws-lois.justice.gc.ca/eng/regulations/SOR-2002-227/section-220.1.html)의 경과규정·특정 가족 예외를 추적했다. 300(2)(a)-(i)는 조회 실패로 남았으며 확인 완료로 기록하지 않았다.

법령 통합본은 여전히 2026-09-30까지라고 표시돼 있어 기준일 이후 변경 확인이 필요하다. PGWP 제휴과정의 경계일 문제와 기타 개별 pending_items도 남아 있다. 캐나다의 모든 법률 보류 사항을 닫은 상태는 아니다.

## 검증과 진행률

189·500 생성 스크립트를 실제 실행해 검토 정보가 유지됨을 확인했다. 전체 20개 JSON의 정책 ID 수·중복, 승인 상태, 공식 URL, 기존 데이터 보존을 검사했다. 나머지 생성 스크립트는 구문과 연결 범위를 검사했으며 모두 실행했다고 주장하지 않는다.

| 지표 | 현재 |
|---|---:|
| 호주 공식 본문 대조 기록 | 223/223, 100% |
| 그중 기존 본문 재현(지문 또는 경계 대조) | 219/223, 98.2% |
| 전체 정책의 공식 자료 1차 대조 기록 | 독일 19 + 캐나다 21 + 호주 223 = 263/590, 44.6% |
| 정책별 법률 검증 최종 완료 | 0/590, 0% |

원문과 일치하는 설명이라도 현행 법령·위임명령·경과규정·예외까지 확인한 정책만 법률 검증 완료로 올린다. DB와 서비스 사용 승인 상태는 바꾸지 않았다. 남은 큰 묶음은 미국 161개와 일본 166개의 공식 자료 대조이며, 호주 189 보강 근거와 각국 법률 보류 항목도 별도로 남는다.

재검사:

```
.venv\Scripts\python.exe scripts/ingest/australia/apply_australia_official_review.py --check
.venv\Scripts\python.exe scripts/ingest/canada/apply_canada_official_review.py --check
```

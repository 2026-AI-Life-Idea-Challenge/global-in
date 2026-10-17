# scripts

Global-In의 데이터 수집, 데이터 적재, 품질 평가를 위한 작업용 스크립트를 관리하는 디렉터리입니다.

이 디렉터리는 실제 서비스 요청을 처리하는 `app/`과 분리하여,
반복 실행하거나 개발·검증 과정에서 사용하는 스크립트를 관리합니다.

---

## 주요 역할

`scripts/`는 크게 다음 세 가지 역할을 담당합니다.

```text
공식 데이터 수집
   ↓
crawl

수집 데이터 가공 및 DB 적재
   ↓
ingest

검색 / 판정 / 응답 품질 평가
   ↓
evaluate
```

---

## 디렉터리 구조

```text
scripts/
├─ crawl/
├─ ingest/
├─ evaluate/
└─ README.md
```

---

## `crawl/`

공식 기관의 데이터를 수집하는 스크립트를 관리합니다.

수집 대상 예시:

```text
정부 공식 사이트
이민기관
대사관
영사관
노동 관련 기관
교육 관련 기관
공공기관
지원사업 운영기관
공식 FAQ
법령 / 행정 안내
```

---

## 기본 수집 방식

가능한 경우 다음 순서로 수집 방식을 선택합니다.

```text
공식 API / Open Data
   ↓
requests
   ↓
BeautifulSoup
   ↓
Playwright
```

JavaScript 렌더링이 필요한 페이지에 한해서
Playwright 사용을 고려합니다.

---

## 수집 시 저장할 정보

공식 자료를 수집할 때 본문만 저장하지 않고,
가능한 한 다음 Metadata를 함께 저장합니다.

```text
official_agency
issuer_country
destination_country
source_title
source_url
source_type
original_published_at
original_updated_at
effective_from
effective_until
verified_at
collected_at
```

원문에 날짜가 없는 경우
임의로 추정하지 않고 `null` 또는 미확인 상태로 유지합니다.

---

## 수집 대상 정보

현재 Global-In의 주요 정보 범위는 다음과 같습니다.

### 한국 측 해외 진출 지원

```text
해외 취업 지원
해외 연수 지원
준비 교육
지원금
해외 진출 가이드
```

### 목적지 국가 지원

```text
외국 인재 유치
취업 지원
유학 지원
장학 지원
정착 지원
```

### 비자 / 법률 / 체류 정보

```text
비자
입국
체류
근로
학업
자격 조건
신청 절차
필요 서류
제한
의무
예외 규정
```

---

## 지원제도 수집 시 확인할 항목

지원제도는 다음 세 가지를 각각 확인합니다.

```text
제도가 실제로 존재하는가
한국인이 이용할 수 있는가
현재 신청 가능한 상태인가
```

예:

```text
제도 존재
≠
한국인 적용 가능

한국인 적용 가능
≠
현재 모집 중
```

공식적으로 확인되지 않은 정보는
임의로 신청 가능 상태로 저장하지 않습니다.

---

## 예상 crawl 파일 구조

```text
scripts/crawl/
├─ common/
├─ japan/
├─ australia/
├─ usa/
├─ germany/
├─ canada/
└─ support/
```

또는 실제 수집 구조에 따라
기관별·국가별로 조정할 수 있습니다.

---

## 수집 스크립트 구현 원칙

- 공식 출처 우선
- 필요한 범위만 수집
- robots 및 이용약관 확인
- HTML 구조 변화에 대비
- 원문 URL 유지
- 수집 실패 기록
- 재실행 가능하도록 구성
- 동일 문서 중복 저장 최소화
- 원문을 임의로 수정하지 않음

---

# ingest

`ingest/`는 수집 및 정제된 데이터를 PostgreSQL과 pgvector에 적재하는 스크립트를 관리합니다.

기본 흐름:

```text
data/raw
   ↓
정제
   ↓
data/processed
   ↓
Schema Validation
   ↓
PostgreSQL / pgvector
```

---

## PostgreSQL 적재

구조화된 데이터는 PostgreSQL에 저장합니다.

예:

```text
Program
Support Program
Eligibility Requirement
Application Information
Required Documents
Fee
Stay Condition
Work Condition
Support Detail
Source Metadata
```

---

## pgvector 적재

비정형 공식 문서는 다음 과정을 거칩니다.

```text
공식 문서
   ↓
Text Extraction
   ↓
Cleaning
   ↓
Chunking
   ↓
Embedding
   ↓
pgvector 저장
```

---

## Chunking

공식 문서를 검색 가능한 단위로 나눕니다.

Chunk에 함께 저장할 Metadata 예:

```text
document_id
chunk_id
country
purpose
program_id
support_program_id
official_agency
source_title
source_url
document_type
original_updated_at
verified_at
```

---

## Embedding

Chunk를 Embedding Vector로 변환하여 pgvector에 저장합니다.

```text
Chunk Text
   ↓
Embedding Model
   ↓
Vector
   ↓
pgvector
```

Embedding Model은 구현 단계에서 결정합니다.

---

## ingest 작업 순서

```text
1. processed 데이터 읽기
2. Schema Validation
3. 중복 확인
4. 구조화 데이터 PostgreSQL 적재
5. 공식 문서 Chunking
6. Embedding 생성
7. pgvector 적재
8. 적재 결과 검증
```

---

## 중복 처리

같은 문서를 여러 번 적재하지 않도록
다음 항목을 활용할 수 있습니다.

```text
source_url
document_id
program_id
original_updated_at
```

실제 중복 기준은 DB Schema 확정 후 결정합니다.

---

# evaluate

`evaluate/`는 Global-In의 검색, 자격 판정, 응답 품질을 평가하는 스크립트를 관리합니다.

평가 대상:

```text
Program Resolver
Rule Evaluator
RAG Retrieval
Evidence Check
LLM Response
Agent Workflow
```

---

## Retrieval 평가

다음 항목을 확인합니다.

```text
관련 문서가 검색되는가
올바른 국가의 문서인가
올바른 프로그램의 문서인가
지원제도와 비자 정보가 혼동되지 않는가
공식 출처가 유지되는가
관련 없는 문서가 상위에 나오지 않는가
```

---

## Rule Evaluator 평가

다음 상황을 테스트합니다.

```text
정상 조건
조건 미충족
사용자 정보 부족
예외 조건
지원제도 자격
비자 자격
```

검증 내용:

```text
조건 충족을 정확히 판정하는가
조건 미충족을 정확히 판정하는가
정보 부족과 미충족을 구분하는가
예외 조건을 임의로 확정하지 않는가
```

---

## Evidence Check 평가

다음 항목을 확인합니다.

```text
질문 관련성
국가 일치
프로그램 일치
대상 일치
공식 기관 여부
적용 시점
확인 시점
```

근거가 부족한 경우
잘못된 근거를 억지로 선택하지 않는지도 확인합니다.

---

## LLM Response 평가

최종 응답에서는 다음을 확인합니다.

```text
공식 근거에 없는 내용을 만들어내지 않는가
Rule 결과를 임의로 변경하지 않는가
비자와 지원제도를 구분하는가
자격과 최종 승인 결과를 혼동하지 않는가
현재 신청 가능 여부를 임의로 단정하지 않는가
출처를 제공하는가
추가 확인 항목을 명확히 표시하는가
```

---

## Agent Workflow 평가

Agent 간 협업 흐름도 테스트합니다.

예:

```text
사용자 질문
   ↓
사용자 이해
   ↓
경로 탐색
   ↓
자격 검토
   ↓
공식 정보 확인
   ↓
준비 계획
```

필요한 경우 모든 Agent를 호출하지 않고
질문에 필요한 Agent만 호출되는지도 확인합니다.

---

## 시나리오 평가

현재 MVP에서는 5개 국가와 3개 상위 진출 경로를 지원합니다.

```text
5개 국가 × 3개 경로 = 15개 상위 경로
```

각 경로마다 최소 다음 4가지 상황을 테스트합니다.

```text
정상 조건
조건 미충족
사용자 정보 부족
예외 / 추가 확인 필요
```

기본 목표:

```text
15개 경로 × 4개 상황 = 최소 60개 Scenario
```

지원제도 테스트는 해당 경로와 연결된 제도를 기준으로 추가합니다.

---

## 예상 파일 구조

```text
scripts/
├─ crawl/
│  └─ ...
│
├─ ingest/
│  ├─ load_programs.py
│  ├─ load_support_programs.py
│  ├─ load_documents.py
│  └─ build_embeddings.py
│
├─ evaluate/
│  ├─ evaluate_retrieval.py
│  ├─ evaluate_rules.py
│  ├─ evaluate_evidence.py
│  └─ evaluate_scenarios.py
│
└─ README.md
```

실제 파일명은 구현 과정에서 조정될 수 있습니다.

---

## app과 scripts의 차이

### `app/`

실제 서비스 요청을 처리하는 코드입니다.

예:

```text
FastAPI
Agent
Retrieval
Rule Evaluator
Services
```

### `scripts/`

개발 및 데이터 작업을 위해 필요할 때 실행하는 코드입니다.

예:

```text
데이터 수집
DB 적재
Embedding 생성
평가
검증
```

즉:

```text
app
→ 서비스 실행

scripts
→ 개발 / 데이터 작업
```

으로 구분합니다.

---

## 실행 원칙

스크립트는 가능한 한 프로젝트 Root에서 실행합니다.

예:

```bash
python scripts/crawl/example.py
```

```bash
python scripts/ingest/load_programs.py
```

```bash
python scripts/evaluate/evaluate_retrieval.py
```

실제 실행 명령은 각 스크립트 구현 후 문서화합니다.

---

## 보안

수집 및 적재 코드에도 실제 Credential을 직접 작성하지 않습니다.

사용 예:

```text
DATABASE_URL
OPENAI_API_KEY
ANTHROPIC_API_KEY
```

`.env` 또는 배포 환경의 Secret을 사용합니다.

---

## 로그

수집이나 적재 과정에서 다음 내용을 확인할 수 있도록 로그를 남기는 것을 권장합니다.

```text
작업 시작 시간
처리 문서 수
성공 건수
실패 건수
실패 URL
DB 적재 건수
중복 건수
```

API Key나 개인정보 등 민감 정보는 로그에 남기지 않습니다.

---

## 구현 원칙

- 서비스 코드와 작업용 Script를 분리
- Script는 가능한 한 재실행 가능하도록 구현
- 실패한 데이터와 원인을 확인할 수 있도록 구성
- 공식 출처 Metadata 유지
- 적재 전 Schema 검증
- 중복 데이터 최소화
- 평가 결과를 재현할 수 있도록 관리
- 특정 국가에만 의존하는 공통 로직 최소화

---

## 개발 순서

```text
1. 데이터 수집 기준 확정
2. crawl 공통 구조 작성
3. 국가별 데이터 수집
4. processed 데이터 생성
5. PostgreSQL ingest 구현
6. Chunking 구현
7. Embedding 생성
8. pgvector ingest 구현
9. Retrieval 평가 Script
10. Rule 평가 Script
11. Scenario 평가 Script
```

---

## 현재 상태

현재는 디렉터리 구조만 생성된 상태이며,
실제 Script는 데이터 Schema와 수집 대상이 확정되는 순서에 맞춰 구현합니다.

# scripts

Global-In의 데이터 수집, 데이터 적재, 평가 및 검증을 위한 실행 Script를 관리하는 디렉터리입니다.

실제 서비스 실행 로직은 `app/`과 `frontend/`에서 관리하고,
반복적인 데이터 처리 작업이나 개발 보조 작업은 `scripts/`에서 관리합니다.

주요 목적은 다음과 같습니다.

```text
공식 데이터 수집

Raw Data 저장

Processed Data 변환

PostgreSQL Seed 적재

pgvector 문서 적재

Embedding 생성

Retrieval 평가

Rule Evaluator 평가

Agent Scenario 평가
```

---

## 기본 디렉터리 구조

```text
scripts/
├─ crawl/
├─ ingest/
├─ evaluate/
└─ README.md
```

각 디렉터리는 역할을 분리하여 사용합니다.

---

# `crawl/`

공식 사이트에서 필요한 정보를 수집하는 Script를 관리합니다.

수집 대상:

```text
실제 비자 / 체류 Program

한국 해외 진출 지원제도

목적지 국가 지원제도

비자 / 체류 / 근로 / 학업 규정

공식 FAQ

법령

행정 안내

공식 Guide
```

---

## 기본 수집 흐름

```text
Official Website
   ↓
Crawler
   ↓
Raw Response
   ↓
Metadata 기록
   ↓
data/raw/
```

수집한 원본은 바로 수정하지 않고
가능한 한 Raw 상태로 보존합니다.

---

## 기본 기술

초기 수집은 다음 라이브러리를 우선 사용합니다.

```text
requests

BeautifulSoup4
```

JavaScript Rendering이 반드시 필요한 경우에만
추후 Playwright 사용을 검토합니다.

---

## 수집 우선순위

공식 정보를 우선합니다.

예:

```text
정부 기관

공식 이민기관

공식 법령

대사관 / 영사관

공공기관

지원제도 운영기관

공식 교육기관

공식 FAQ / Guide
```

비공식 Blog나 커뮤니티는
핵심 Eligibility 근거 수집 대상으로 사용하지 않습니다.

---

## 한국 측 정보 수집

예:

```text
해외취업 지원

해외 연수

준비 교육

지원금

해외 진출 Guide
```

주요 대상:

```text
한국 정부

공공기관

지원사업 운영기관
```

---

## 목적지 국가 지원 정보 수집

예:

```text
외국 인재 유치

외국인 취업 지원

유학 지원

장학 지원

정착 지원
```

수집 시 다음을 확인합니다.

```text
지원제도가 실제 존재하는가

한국인에게 적용 가능한가

적용 대상이 누구인가

현재 시행 중인 제도인가

현재 신청 가능한가
```

이 정보들을 하나의 Boolean 값으로 합치지 않습니다.

---

## 비자 / 법률 정보 수집

예:

```text
비자

입국

체류

근로

학업

신청 자격

신청 절차

필요 서류

제한

의무

예외 규정
```

가능하면 관할 기관 자료를 우선합니다.

---

## 수집 Metadata

Crawler는 가능한 한 다음 정보를 함께 기록합니다.

```text
official_agency

issuer_country

destination_country

target_nationality

source_title

source_url

source_type

information_topic

original_published_at

original_updated_at

effective_from

effective_until

verified_at
```

---

## `verified_at`

`verified_at`은 Global-In에서
해당 URL과 내용을 확인한 날짜입니다.

예:

```text
verified_at = 2026-10-17
```

중요:

```text
verified_at이 최근
≠
해당 제도 자체가 현재 유효함
```

원문의 적용 기간과 현재 모집 상태는 별도로 확인합니다.

---

## 날짜 처리

공식 페이지에 날짜가 없으면
임의로 생성하지 않습니다.

예:

```text
original_updated_at = null
```

처럼 저장합니다.

---

## URL 보존

수집한 모든 핵심 정보에는
가능한 한 원문 URL을 유지합니다.

예:

```text
source_url
```

향후 Evidence 표시 및 검증에 사용합니다.

---

## Raw Data 저장

수집 결과는 우선:

```text
data/raw/
```

에 저장합니다.

예:

```text
scripts/crawl/
   ↓
data/raw/
```

---

## 국가별 Crawler

처음부터 다음처럼 완전히 별도의 구조를
과도하게 만들지 않습니다.

```text
japan_crawler.py

germany_crawler.py

canada_crawler.py
```

공통 수집 로직이 있다면 재사용합니다.

단, 국가별 사이트 구조가 크게 다르면
필요한 범위에서 별도 Parser를 둘 수 있습니다.

---

## 예상 파일 예

```text
scripts/crawl/
├─ fetch_page.py
├─ parse_program.py
├─ parse_support_program.py
├─ parse_document.py
└─ ...
```

실제 파일 구조는
수집 대상 사이트를 확인하면서 정합니다.

---

# `ingest/`

정제된 데이터를
PostgreSQL과 pgvector에 적재하는 Script를 관리합니다.

---

## 기본 흐름

```text
data/processed/
   ↓
Validation
   ↓
scripts/ingest/
   ↓
PostgreSQL / pgvector
```

Seed Data의 경우:

```text
data/seed/
   ↓
scripts/ingest/
   ↓
PostgreSQL
```

---

## PostgreSQL 적재 대상

예:

```text
Program

SupportProgram

ProgramSupportLink

EligibilityRequirement

ApplicationInfo

ApplicationAvailability

RequiredDocument

SupportDetail

Evidence Metadata
```

---

## pgvector 적재 대상

예:

```text
Official Document

Document Chunk

Embedding

Chunk Metadata
```

---

## Program 적재

Program은 실제 해외 진출 경로를 의미합니다.

예:

```text
취업 비자

학생 비자

워킹홀리데이

교환 프로그램

체류 자격
```

---

## SupportProgram 적재

SupportProgram은 해외 진출을 지원하는
별도 지원제도입니다.

예:

```text
해외취업 지원금

연수 프로그램

장학금

취업 준비 교육

현지 정착 지원
```

Program과 SupportProgram을
같은 Table에 무분별하게 섞지 않습니다.

---

## ProgramSupportLink

하나의 SupportProgram이
여러 Program과 연결될 수 있습니다.

예:

```text
Program
   ↑
   │
ProgramSupportLink
   │
   ↓
SupportProgram
```

적재 Script에서도
이 관계를 별도로 처리할 수 있습니다.

---

## EligibilityRequirement 적재

구조화 가능한 공식 자격조건을 저장합니다.

예:

```json
{
  "field": "career_years",
  "operator": ">=",
  "value": 2,
  "required": true,
  "judgeability": "rule_based"
}
```

---

## judgeability

예:

```text
rule_based

manual_check

conditional
```

자동 판정이 어려운 조건을
억지로 Rule로 변환하지 않습니다.

---

## Evidence 연결

각 핵심 Data는
가능하면 공식 Evidence와 연결합니다.

예:

```text
Program
   ↓
Evidence
```

```text
EligibilityRequirement
   ↓
Evidence
```

```text
SupportProgram
   ↓
Evidence
```

---

## 적재 전 Validation

DB에 넣기 전에 최소한 다음을 확인합니다.

```text
필수 ID 존재

Program / SupportProgram 구분

destination_country 정상

issuer_country 정상

공식 기관 정보 존재

원문 URL 존재

Eligibility 구조 정상

날짜 Format 정상

Evidence 연결 정상
```

---

## 중복 처리

동일한 Program이 여러 Source에서 발견되더라도
무조건 새로운 Program으로 생성하지 않습니다.

예:

```text
Program A
   ├─ Evidence 1
   ├─ Evidence 2
   └─ Evidence 3
```

처럼 하나의 Entity에
여러 Evidence를 연결할 수 있습니다.

---

## Upsert

반복 적재가 필요한 경우
중복 Record를 무한히 생성하지 않도록
Upsert 전략을 고려합니다.

예:

```text
program_id 기준

support_program_id 기준

evidence_id 기준
```

실제 기준은 DB Schema 확정 후 결정합니다.

---

# Document Processing

공식 문서를 pgvector에 넣기 전에
다음 과정을 거칠 수 있습니다.

```text
Raw Document
   ↓
Text Extraction
   ↓
Cleaning
   ↓
Section Parsing
   ↓
Chunking
   ↓
Metadata 추가
   ↓
Embedding
   ↓
pgvector
```

---

## Chunking

하나의 긴 공식 문서를
의미 있는 작은 단위로 나눕니다.

예:

```text
Eligibility Section

Required Documents Section

Work Restrictions Section

FAQ Question / Answer
```

---

## Chunk Metadata

각 Chunk에는 가능한 한 다음 정보를 유지합니다.

```text
document_id

chunk_id

issuer_country

destination_country

program_id

support_program_id

target_nationality

information_topic

source_type

official_agency

source_title

source_url

original_updated_at

effective_from

effective_until

verified_at
```

---

## Embedding 생성

예상 흐름:

```text
Document Chunk
   ↓
Embedding Service
   ↓
Vector
   ↓
pgvector
```

Embedding 호출 로직은
가능하면 `app/services/`의 공통 기능을 재사용합니다.

---

# `evaluate/`

Global-In의 Retrieval, Rule Evaluator, Agent Workflow 등의
품질을 평가하는 Script를 관리합니다.

---

## 평가 대상

```text
Program Resolver

Rule Evaluator

Retrieval

Evidence Validation

Agent Routing

Agent Response

Checklist

Roadmap
```

---

# Rule Evaluator 평가

구조화된 공식 조건이
정확하게 판정되는지 확인합니다.

예:

```text
age <= 30
```

Test:

```text
20
→ PASS

30
→ PASS

31
→ FAIL

null
→ UNKNOWN
```

---

## 반드시 확인할 항목

```text
Missing Information과 FAIL을 구분하는가

manual_check 조건을 자동 PASS하지 않는가

Program Eligibility와 SupportProgram Eligibility를 구분하는가

동일 입력에 동일 결과가 나오는가
```

---

# Retrieval 평가

공식 문서 검색이
정확하게 작동하는지 평가합니다.

예:

```text
사용자 질문:
독일 취업 비자의 근로 조건
```

Expected:

```text
독일 관련 문서

해당 Program 관련 문서

work 관련 Section

공식 기관 자료
```

---

## Retrieval 평가 항목

```text
올바른 국가 문서인가

Program이 일치하는가

SupportProgram이 일치하는가

질문 Topic이 일치하는가

적용 대상이 일치하는가

공식 Source인가

불필요한 다른 국가 문서가 섞이지 않는가
```

---

## Retrieval Metric

필요한 경우 다음 지표를 사용할 수 있습니다.

```text
Hit Rate

Recall@K

MRR

Precision@K
```

초기 MVP에서는
정량 평가와 수동 검토를 함께 사용할 수 있습니다.

---

# Evidence Validation 평가

검색 결과가
잘못된 최종 Evidence로 사용되지 않는지 확인합니다.

예:

```text
다른 국가 문서

다른 Program 문서

한국인에게 적용되지 않는 지원제도

적용 기간이 종료된 자료
```

등이 최종 Evidence로 사용되지 않는지 검증합니다.

---

# Agent Routing 평가

질문에 필요한 Agent만 호출되는지 확인합니다.

예:

```text
독일 취업 비자의 근로 제한 알려줘.
```

불필요하게:

```text
사용자 이해
→ 추천
→ 자격
→ 준비 계획
```

전체 Agent를 호출하지 않아야 합니다.

필요한 경우:

```text
공식 정보 안내 에이전트
```

중심으로 처리할 수 있습니다.

---

## Routing Test 예

```text
경로 추천 질문
→ 진출 경로 탐색·추천

자격 질문
→ 자격 검토

법률 / 공식 규정 질문
→ 공식 정보 안내

준비 순서 질문
→ 준비 계획
```

---

# 사용자 이해 Agent 평가

다음을 확인합니다.

```text
필요한 정보만 질문하는가

이미 확인된 정보를 반복 질문하지 않는가

Missing Information을 제대로 탐지하는가

사용자 답변으로 Profile이 갱신되는가
```

---

# 진출 경로 탐색·추천 Agent 평가

```text
실제 Program을 올바르게 탐색하는가

SupportProgram을 구분하는가

한국인 적용 여부가 불명확한 제도를 확정적으로 추천하지 않는가

자격 검토 결과를 추천에 반영하는가
```

---

# 자격 검토 Agent 평가

```text
Rule Evaluator 결과를 임의로 변경하지 않는가

조건 미충족 이유를 정확히 설명하는가

추가 확인 필요 조건을 확정적으로 말하지 않는가

비자와 지원제도 Eligibility를 분리하는가
```

---

# 공식 정보 안내 Agent 평가

```text
공식 Source를 사용하는가

근거와 답변이 일치하는가

원문 URL을 제공하는가

공식 규정과 AI 해석을 구분하는가

Evidence가 없으면 내용을 만들어내지 않는가
```

---

# 준비 계획 Agent 평가

```text
비자와 지원제도 준비 항목을 구분하는가

필요 서류를 임의로 생성하지 않는가

확인되지 않은 일정이나 처리기간을 만들지 않는가

Checklist가 Eligibility 결과를 반영하는가

Roadmap이 현재 상태에 맞게 조정되는가
```

---

# Scenario Evaluation

실제 사용자 흐름을 기준으로
End-to-End Scenario를 평가합니다.

예:

```text
독일 취업 준비자

캐나다 유학 준비자

일본 워킹홀리데이 준비자

미국 교환 프로그램 준비자

호주 취업 준비자
```

---

## Scenario 예시

```text
User:
독일로 취업하고 싶어요.

↓

사용자 이해 에이전트

↓

필요 정보 추가 질문

↓

Program 후보 탐색

↓

SupportProgram 탐색

↓

Eligibility 검토

↓

공식 Evidence 확인

↓

Checklist / Roadmap
```

전체 결과가 논리적으로 연결되는지 확인합니다.

---

## Scenario Test 데이터

Scenario 입력 Data는
다음과 같이 관리할 수 있습니다.

```text
tests/scenarios/
```

또는 평가용 별도 Dataset이 필요한 경우:

```text
scripts/evaluate/data/
```

형태를 고려할 수 있습니다.

실제 구조는 테스트 구현 과정에서 결정합니다.

---

# 평가 결과 저장

평가 결과는 필요하면 다음 형태로 저장할 수 있습니다.

```text
JSON

JSONL

CSV
```

예:

```text
evaluation_result.json
```

대량 결과 파일은
Git Commit 여부를 별도로 판단합니다.

---

# Hallucination 검증

Global-In에서는 특히
공식 정보 Hallucination을 주의합니다.

평가 항목:

```text
존재하지 않는 Program 생성

존재하지 않는 SupportProgram 생성

공식 문서에 없는 자격조건 생성

확인되지 않은 신청 기간 생성

확인되지 않은 처리 기간 생성

잘못된 기관명 생성

잘못된 URL 생성

Rule Evaluator 결과 변경
```

---

# Application Availability 검증

현재 신청 가능 여부는
Eligibility와 별도로 평가합니다.

예:

```text
Eligibility
→ 조건 충족

Application Availability
→ UNKNOWN
```

이 경우 답변에서:

```text
지금 신청할 수 있습니다.
```

라고 말하면 안 됩니다.

---

# 한국인 적용 여부 검증

목적지 국가의 외국인 지원제도를 검색할 때
한국인에게 실제 적용되는지 확인합니다.

평가 예:

```text
외국인 지원제도 존재
→ PASS

한국인 적용 여부 확인 안 됨
→ 추가 확인 필요
```

자동으로 추천 가능한 제도로 확정하지 않습니다.

---

# 최신성 관련 평가

Global-In 초기 MVP에서는
실시간 정책 자동 갱신을 구현하지 않습니다.

따라서 다음을 구분해서 평가합니다.

```text
공식 원문 수정일

제도 적용 기간

Global-In 확인일

현재 모집 여부
```

단순히 `verified_at`이 최근이라는 이유로
현재 신청 가능하다고 판단하지 않습니다.

---

# Script 실행 원칙

각 Script는 가능하면
독립적으로 실행할 수 있도록 구성합니다.

예:

```bash
python scripts/crawl/example.py
```

또는:

```bash
python scripts/ingest/example.py
```

---

# Root 기준 실행

Python Import 문제를 줄이기 위해
가능하면 Repository Root에서 실행합니다.

예:

```text
global-in/
```

위치에서:

```bash
python scripts/ingest/load_seed.py
```

처럼 실행합니다.

---

# 환경변수

Script에서도 `.env`를 통해 설정을 읽습니다.

예:

```text
OPENAI_API_KEY

ANTHROPIC_API_KEY

DATABASE_URL
```

API Key나 Password를
Script 내부에 Hard Coding하지 않습니다.

---

# Dry Run

DB 적재나 대량 처리 Script에서는
가능하면 Dry Run 옵션을 고려합니다.

예:

```text
실제로 DB에 저장하지 않고

몇 개 Record가 생성되는지

어떤 값이 들어가는지

Validation Error가 있는지
```

확인합니다.

초기 개발 과정에서 데이터 오류를 줄이는 데 도움이 됩니다.

---

# Idempotency

동일한 Ingest Script를 여러 번 실행해도
불필요한 중복 데이터가 생성되지 않도록 고려합니다.

예:

```text
같은 program_id 중복 생성 방지

같은 support_program_id 중복 생성 방지

같은 document_id 중복 적재 방지
```

---

# Logging

Script 실행 시 최소한 다음 정보를 확인할 수 있도록 합니다.

예:

```text
처리 시작

처리 대상 수

성공 수

실패 수

Skip 수

오류 내용
```

예:

```text
Programs: 25

Success: 24

Failed: 1
```

---

# 실패 데이터 처리

하나의 Record 오류로
전체 Data Pipeline이 무조건 중단되지 않도록
필요한 경우 실패 항목을 별도로 기록합니다.

예:

```text
failed_records.json
```

단, 핵심 Schema 오류처럼
전체 작업을 중단해야 하는 경우도 구분합니다.

---

# 재현성

데이터 처리 결과를 재현할 수 있도록
가능하면 다음을 유지합니다.

```text
Source URL

Raw Data

Processing Script

Schema Version

Verification Date
```

---

# Git 관리

Script는 기본적으로 Git에 Commit합니다.

단 다음은 제외 여부를 검토합니다.

```text
대용량 실행 결과

Temporary File

Embedding Dump

Database Dump

Crawler Cache

민감 정보
```

---

# 예상 파일 구조 예

향후 구현이 진행되면 예를 들어:

```text
scripts/
│
├─ crawl/
│  ├─ crawl_programs.py
│  ├─ crawl_support_programs.py
│  └─ crawl_documents.py
│
├─ ingest/
│  ├─ load_programs.py
│  ├─ load_support_programs.py
│  ├─ load_requirements.py
│  └─ load_documents.py
│
├─ evaluate/
│  ├─ evaluate_rules.py
│  ├─ evaluate_retrieval.py
│  ├─ evaluate_agents.py
│  └─ evaluate_scenarios.py
│
└─ README.md
```

와 같은 구조로 확장할 수 있습니다.

실제 파일은 필요한 시점에 추가합니다.

---

# 개발 순서

현재 예상 Script 개발 순서는 다음과 같습니다.

```text
1. Sample Data 수집 Script

2. Raw Data 저장

3. Parsing / Cleaning

4. Program 변환 Script

5. SupportProgram 변환 Script

6. EligibilityRequirement 변환

7. Evidence Metadata 생성

8. PostgreSQL Seed 적재

9. Document Chunking

10. Embedding 생성

11. pgvector 적재

12. Rule Evaluator 평가

13. Retrieval 평가

14. Agent Scenario 평가

15. 전체 데이터 Pipeline 검증
```

---

# 테스트 포인트

```text
Crawler가 공식 URL에서 데이터를 수집하는가

Source URL이 유지되는가

원문 날짜가 올바르게 저장되는가

verified_at과 원문 날짜가 구분되는가

Program과 SupportProgram이 구분되는가

한국인 적용 여부 정보가 유지되는가

Eligibility와 Application Availability가 구분되는가

DB 적재 시 중복이 발생하지 않는가

Document Chunk Metadata가 유지되는가

잘못된 Record가 검출되는가

평가 Script가 재현 가능한 결과를 생성하는가
```

---

# 구현 원칙

- 공식 출처 우선
- Raw Data 보존
- Program과 SupportProgram 구분
- 원문 URL 유지
- 원문 날짜와 확인 날짜 구분
- 현재 모집 여부를 별도 관리
- 한국인 적용 여부를 별도 확인
- 데이터 적재 전 Validation 수행
- 반복 실행 시 중복 생성 최소화
- Script에 Secret을 Hard Coding하지 않음
- 국가별 중복 코드를 가능한 한 공통화
- 실제 데이터 특성을 확인하면서 Schema를 보완
- 평가 결과를 기반으로 Retrieval과 Agent 구조 개선

---

# 현재 상태

현재는 다음 기본 디렉터리가 생성된 상태입니다.

```text
scripts/crawl/

scripts/ingest/

scripts/evaluate/
```

아직 실제 수집 및 적재 Script 구현 전 단계이며,
다음 개발 과정에서 5개 국가의 공식 데이터를 Sample로 수집한 뒤
데이터 구조와 DB Schema를 검증하면서 Script를 추가합니다.

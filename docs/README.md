# docs

법률 검토 보고서·진행률·코드 위치와 실행 안내는 [legal_review/README.md](legal_review/README.md)에서 확인하세요.

Global-In의 기획, 시스템 설계, Agent 구조, Database / ERD, 데이터 정책 등
프로젝트의 상세 설계 문서를 관리하는 디렉터리입니다.

실제 실행 코드는 `app/`, `frontend/`, `scripts/`에서 관리하고,
팀원이 함께 참고해야 하는 설계 내용과 의사결정은 `docs/`에서 관리합니다.

---

## 주요 역할

`docs/`에서는 다음 내용을 관리합니다.

```text
서비스 기획

Agent Architecture

LangGraph Workflow

System Architecture

Database / ERD

Data Schema

정보 수집 정책

Evidence 관리 정책

API 설계

테스트 전략

주요 기술 의사결정
```

---

## 기본 디렉터리 구조

```text
docs/
├─ architecture/
├─ planning/
└─ README.md
```

개발 과정에서 필요한 경우 하위 디렉터리를 추가할 수 있습니다.

예:

```text
docs/
├─ architecture/
├─ planning/
├─ database/
├─ api/
└─ README.md
```

처음부터 불필요한 문서 디렉터리를 모두 만들지 않고,
실제 설계 문서가 필요한 시점에 추가합니다.

---

# `planning/`

서비스 기획과 정책 관련 문서를 관리합니다.

주요 내용:

```text
서비스 목적

사용자 문제 정의

Target User

MVP 범위

대상 국가

상위 진출 경로

정보 제공 범위

Agent 역할 정의

기능 요구사항

제외 기능

데이터 수집 기준

공식 정보 사용 원칙
```

---

## 대상 사용자

Global-In의 초기 Target User는
해외 진출을 준비하는 한국의 20~30대 청년층입니다.

예:

```text
워킹홀리데이 준비자

교환학생 준비자

유학생

해외 취업 준비자

해외 정착 가능성을 검토하는 사용자
```

---

## 대상 국가

초기 MVP에서는 다음 5개 국가를 대상으로 합니다.

```text
일본

호주

미국

독일

캐나다
```

---

## 상위 진출 경로

```text
워킹홀리데이 / 교환

유학

취업
```

이 세 가지는 사용자에게 제공하는 상위 분류입니다.

```text
5개 국가
×
3개 상위 경로
=
15개 상위 국가-경로 조합
```

이것이 15개의 개별 비자를 의미하지는 않습니다.

각 상위 경로 아래에
실제 비자·체류·교환 Program을 연결합니다.

---

## 예시

```text
USA
+
워킹홀리데이 / 교환
```

미국에는 일반적인 Working Holiday Visa가 없으므로
실제 구현에서는 J-1 등
해당 목적에 맞는 실제 Exchange Program을 연결합니다.

---

# 정보 제공 범위

Global-In은 크게 다음 세 영역의 공식 정보를 다룹니다.

---

## 1. 한국의 해외 진출 지원 정보

예:

```text
해외 취업 지원

해외 연수

준비 교육

지원금

해외 진출 Guide
```

주요 출처:

```text
정부 기관

공공기관

지원사업 운영기관
```

---

## 2. 목적지 국가의 외국인 지원 정보

예:

```text
외국 인재 유치

외국인 취업 지원

유학 지원

장학 지원

정착 지원
```

주요 출처:

```text
목적지 국가 정부

공공기관

교육기관

지원사업 운영기관
```

---

## 3. 목적지 국가의 비자·법률 정보

예:

```text
비자

입국

체류

근로

학업

Eligibility

Application

Required Documents

Restrictions

Duties

Exceptions
```

주요 출처:

```text
공식 법령

이민기관

대사관 / 영사관

노동 관련 기관

교육 관련 기관

관할 행정기관
```

---

# Program과 SupportProgram

Global-In에서는
해외 진출 Program과 지원제도를 별도의 Entity로 관리합니다.

---

## Program

실제 해외 진출에 직접 연결되는 경로입니다.

예:

```text
Working Holiday

Student Visa

Employment Visa

Exchange Program

Residence Status
```

---

## SupportProgram

해외 진출 과정에서 활용할 수 있는 지원제도입니다.

예:

```text
해외취업 지원

해외 연수

취업 준비 교육

장학금

지원금

외국인 정착 지원
```

---

## 관계

하나의 SupportProgram이
여러 Program과 연결될 수 있습니다.

```text
Program
   ↑
   │
ProgramSupportLink
   │
   ↓
SupportProgram
```

따라서 초기 ERD에서도
1:1 관계를 전제로 하지 않습니다.

---

# Agent 설계

Global-In은 LangGraph 기반의
5개 Agent 구조를 사용합니다.

```text
1. 사용자 이해 에이전트

2. 진출 경로 탐색·추천 에이전트

3. 자격 검토 에이전트

4. 공식 정보 안내 에이전트

5. 준비 계획 에이전트
```

각 Agent는 하나의 명확한 주요 역할을 담당합니다.

---

# 1. 사용자 이해 에이전트

## 목적

사용자의 목적과 현재 상황을 파악하고,
진출 경로·비자·지원제도를 검토하기 위해 필요한 정보를 정리합니다.

---

## 주요 역할

```text
Onboarding

Intent 파악

UserProfile 생성

UserProfile 갱신

Missing Information 탐지

추가 질문 생성
```

---

## 주요 사용자 정보

예:

```text
나이

국적

현재 거주지

학력

전공

경력

언어

희망 국가

진출 목적

희망 시기
```

지원제도에 따라:

```text
재학 여부

취업 상태

기존 참여 이력

기존 수혜 이력

중복 수혜 여부
```

등을 추가로 확인할 수 있습니다.

---

## 중요한 구분

```text
사용자 정보 없음
≠
공식 조건 미충족
```

사용자 정보가 없다면:

```text
Missing Information
```

으로 처리하고 추가 질문합니다.

사용자 정보가 존재하지만
공식 조건을 만족하지 못한다면:

```text
조건 미충족
```

으로 처리합니다.

---

# 2. 진출 경로 탐색·추천 에이전트

## 목적

사용자 목적과 조건에 맞는
국가·진출 경로·실제 Program 후보를 찾고,
관련 SupportProgram을 함께 탐색합니다.

---

## 주요 역할

```text
국가 추천

진출 유형 추천

Program Resolver

Program 후보 탐색

SupportProgram 탐색

후보 비교

추천 이유 생성
```

---

## Program Resolver

상위 진출 경로를
실제 Program과 연결합니다.

예:

```text
Germany
+
Employment
   ↓
실제 독일 취업 Program 후보
```

---

## SupportProgram 검토

지원제도는 최소 다음을 확인합니다.

```text
제도가 실제 존재하는가

한국인에게 적용 가능한가

현재 시행되는 제도인가

현재 신청 가능한가
```

이 네 가지는 서로 다른 상태입니다.

---

# 3. 자격 검토 에이전트

## 목적

Program 및 SupportProgram의 공식 자격조건을
UserProfile과 비교합니다.

---

## 주요 역할

```text
Program Eligibility 검토

SupportProgram Eligibility 검토

Rule Evaluator 사용

부족 조건 정리

예외 조건 정리

추가 확인 항목 생성
```

---

## 판정 상태

```text
조건 충족

조건 미충족

추가 확인 필요
```

---

## Rule Evaluator

구조화 가능한 공식 조건은
LLM이 아니라 Python Rule Evaluator가 판정합니다.

예:

```text
career_years >= 2
```

사용자:

```text
career_years = 3
```

결과:

```text
조건 충족
```

---

## 자동 판정하지 않는 경우

예:

```text
기관 재량

예외 규정

법률 해석 필요

공식 근거 충돌

구조화하기 어려운 조건
```

결과:

```text
추가 확인 필요
```

---

# 4. 공식 정보 안내 에이전트

## 목적

공식 문서와 지원제도 자료를 검색하고
사용자에게 근거 기반으로 설명합니다.

---

## 주요 역할

```text
RAG Retrieval

Evidence Validation

비자 / 체류 정보 설명

근로 / 학업 규정 설명

SupportProgram 설명

신청 절차 설명

공식 Source 제공
```

---

## 검색 대상

```text
공식 법령

행정 안내

이민기관 문서

대사관 / 영사관 안내

공식 FAQ

지원사업 공고

공식 Guide
```

---

## 공식 정보와 AI 해석

다음 두 내용을 구분합니다.

```text
공식 규정 / 공식 사업 내용

AI의 설명 / 추천 / 준비 조언
```

AI의 해석을
공식 규정처럼 표현하지 않습니다.

---

# 5. 준비 계획 에이전트

## 목적

Program 준비와 SupportProgram 신청을
하나의 실행 계획으로 구성합니다.

---

## 주요 역할

```text
필요 서류 정리

Checklist

단계별 Guide

Roadmap

현재 상태 관리

Next Action
```

---

## 기본 준비 단계

```text
준비
   ↓
신청
   ↓
승인 후
   ↓
출국 준비
   ↓
입국 후
```

실제 단계는 Program에 따라 달라질 수 있습니다.

---

# Agent 간 협업 구조

대표적인 전체 흐름:

```text
User
   ↓
사용자 이해 에이전트
   ↓
진출 경로 탐색·추천 에이전트
   ↓
자격 검토 에이전트
   ↓
공식 정보 안내 에이전트
   ↓
준비 계획 에이전트
   ↓
Final Response
```

하지만 모든 질문에서
5개 Agent를 전부 호출하지 않습니다.

---

## 선택적 Agent 호출

예:

```text
독일 취업 비자의 근로 제한 알려줘.
```

필요한 핵심 Agent:

```text
공식 정보 안내 에이전트
```

불필요한 Agent 실행을 최소화합니다.

---

# 공통 Module

다음 기능은 별도의 Agent가 아니라
Agent들이 공유하는 Module 또는 Service입니다.

```text
Program Resolver

Rule Evaluator

Retrieval

Evidence Validation

PostgreSQL Access

pgvector Search

LLM Service

Embedding Service
```

---

# System Architecture

`architecture/`에서는
전체 기술 구조를 문서화합니다.

기본 구조:

```text
User
  ↓
Streamlit
  ↓
FastAPI
  ↓
LangGraph Orchestrator
  │
  ├─ 사용자 이해 에이전트
  ├─ 진출 경로 탐색·추천 에이전트
  ├─ 자격 검토 에이전트
  ├─ 공식 정보 안내 에이전트
  └─ 준비 계획 에이전트
  │
  └─ Common Modules
       ├─ Program Resolver
       ├─ Rule Evaluator
       ├─ Retrieval
       ├─ Evidence Validation
       └─ Services
            ├─ PostgreSQL
            ├─ pgvector
            └─ LLM
```

---

# `architecture/`

다음과 같은 기술 문서를 관리합니다.

```text
전체 System Architecture

Agent Collaboration Architecture

LangGraph Workflow

Backend Architecture

RAG Architecture

Database Architecture

Frontend / Backend Communication
```

---

## 예상 문서 예

```text
docs/architecture/system.md

docs/architecture/agents.md

docs/architecture/langgraph.md

docs/architecture/rag.md
```

실제로 필요한 시점에 생성합니다.

---

# LangGraph 문서

LangGraph 설계 문서에서는
다음 내용을 관리합니다.

```text
Node

Edge

Conditional Edge

Agent Routing

Shared State

Loop

Termination Condition
```

---

## Shared State 예

```text
user_query

user_profile

intent

missing_fields

candidate_programs

candidate_support_programs

selected_program

eligibility_results

retrieved_documents

validated_evidence

checklist

roadmap

final_answer
```

실제 구조는 구현 후 문서에 반영합니다.

---

# Database / ERD

Database 설계가 시작되면
관련 문서를 `docs/`에서 관리합니다.

필요한 경우:

```text
docs/database/
```

를 추가합니다.

예:

```text
docs/database/erd.md

docs/database/schema.md
```

---

## 현재 예상 핵심 Entity

```text
UserProfile

Program

SupportProgram

ProgramSupportLink

EligibilityRequirement

ApplicationInfo

ApplicationAvailability

RequiredDocument

EvidenceSource

OfficialDocument

DocumentChunk
```

실제 Entity와 Field는
공식 데이터를 수집하면서 조정합니다.

---

# Entity 설계 원칙

초기부터 모든 Field를 고정하지 않습니다.

다음 순서로 진행합니다.

```text
Agent 요구사항 확인
   ↓
필요 데이터 확인
   ↓
핵심 Entity 정의
   ↓
관계 정의
   ↓
Sample 공식 데이터 수집
   ↓
실제 데이터 구조 확인
   ↓
Field 보완
```

국가별 데이터를
초기 Schema에 억지로 끼워 맞추지 않습니다.

---

# 국가 Field 설계

국가 정보는 역할별로 구분합니다.

예:

```text
issuer_country

destination_country

target_nationality

residence_requirement
```

---

## `issuer_country`

제도 또는 문서를 발행한 국가

---

## `destination_country`

사용자가 진출하려는 국가

---

## `target_nationality`

적용 대상 국적

---

## `residence_requirement`

현재 거주지 관련 조건

---

# Evidence 설계

Global-In은 주요 정보의 공식 근거를
추적할 수 있도록 설계합니다.

기본 Metadata:

```text
official_agency

source_title

source_url

source_type

original_published_at

original_updated_at

effective_from

effective_until

verified_at
```

---

## 날짜 구분

```text
original_published_at
→ 최초 게시일

original_updated_at
→ 원문 수정일

effective_from
→ 실제 적용 시작일

effective_until
→ 실제 적용 종료일

verified_at
→ Global-In에서 확인한 날짜
```

---

## 중요한 원칙

```text
verified_at이 최근
≠
현재 정책이 유효함
```

현재 적용 여부와
현재 신청 가능 여부는 별도로 확인합니다.

---

# Evidence Validation

검색된 문서가
바로 최종 Evidence가 되는 것은 아닙니다.

```text
Retrieval Result
   ↓
Evidence Validation
   ↓
Validated Evidence
```

검증 항목:

```text
질문과 관련 있는가

국가가 맞는가

Program이 맞는가

SupportProgram이 맞는가

적용 대상이 맞는가

공식 출처인가

적용 시점이 맞는가
```

---

# Eligibility와 Application Availability

다음 두 개념은 반드시 구분합니다.

```text
Eligibility
→ 사용자가 자격 요건을 충족하는가
```

```text
Application Availability
→ 현재 실제 신청 가능한가
```

예:

```text
Eligibility = 조건 충족

Application Availability = CLOSED
```

가능합니다.

---

# API 설계 문서

API 구조가 구체화되면
필요한 경우:

```text
docs/api/
```

를 추가합니다.

예:

```text
docs/api/endpoints.md
```

관리할 내용:

```text
Endpoint

HTTP Method

Request Schema

Response Schema

Error

Agent Workflow 연결
```

FastAPI Swagger와 별개로
서비스 구조와 설계 이유를 기록할 수 있습니다.

---

# Data Schema 문서

다음 개념을 문서화합니다.

```text
Program

SupportProgram

EligibilityRequirement

ApplicationInfo

RequiredDocument

Evidence

AgentState

Checklist

Roadmap
```

역할 구분:

```text
docs/
→ 설계 문서

app/models/
→ Python Schema

data/
→ 실제 Data

PostgreSQL
→ 운영 Data 저장
```

---

# 데이터 수집 정책 문서

공식 정보 수집 기준도
`docs/`에서 관리할 수 있습니다.

예:

```text
공식 Source 우선순위

한국인 적용 여부 확인 기준

날짜 검증 기준

지원제도 모집 상태 기준

Evidence 충돌 처리 기준

Crawler 정책

데이터 갱신 정책
```

---

# 공식 Source 우선 원칙

비자 / 체류 조건:

```text
관할 이민기관

공식 법령

대사관 / 영사관

관할 행정기관
```

지원제도:

```text
해당 지원제도 운영기관

정부 기관

공공기관

교육기관
```

---

# 근거 충돌 정책

공식 자료가 서로 충돌할 경우:

```text
관할 기관

적용 대상

Program

SupportProgram

Source Type

적용 시점

원문 수정일
```

을 비교합니다.

충돌을 해결할 수 없다면:

```text
추가 확인 필요
```

로 처리합니다.

---

# 현재 모집 상태

지원제도나 Program이 존재한다고 해서
현재 신청 가능한 것은 아닙니다.

따라서 다음을 구분합니다.

```text
Program 존재 여부

지원제도 존재 여부

Eligibility

현재 Application Availability
```

모집 상태를 확인하지 못한 경우:

```text
UNKNOWN
```

으로 유지합니다.

---

# Architecture Decision Record

중요한 기술 선택은
단순 결과뿐 아니라 선택 이유도 기록하는 것을 권장합니다.

예:

```text
왜 LangGraph를 사용하는가

왜 Agent를 5개 역할로 분리하는가

왜 Rule Evaluator를 LLM과 분리하는가

왜 PostgreSQL + pgvector를 사용하는가

왜 Program과 SupportProgram을 분리하는가

왜 Streamlit + FastAPI 구조를 사용하는가
```

---

## ADR 예시 구조

향후 필요하면:

```text
docs/architecture/adr/
```

를 만들 수 있습니다.

예:

```text
001-use-langgraph.md

002-use-postgresql-pgvector.md

003-separate-rule-evaluator.md
```

초기 MVP 단계에서는
필요한 결정부터 기록합니다.

---

# 테스트 설계 문서

상세 테스트 전략이 필요할 경우
`docs/`에서 별도 문서를 관리할 수 있습니다.

예:

```text
Unit Test

Integration Test

Scenario Test

Retrieval Evaluation

Hallucination Evaluation
```

실제 Test Code는:

```text
tests/
```

에서 관리합니다.

---

# Scenario 기준

초기 Scenario는 다음 범위를 기준으로 합니다.

```text
5개 국가
×
3개 상위 진출 경로
```

그리고 사용자 상태를:

```text
조건 충족

조건 미충족

정보 부족

추가 확인 필요
```

등으로 확장할 수 있습니다.

---

# MVP 제외 기능

초기 MVP에서는 다음을 우선 제외합니다.

```text
실시간 채용공고

항공권

주거 추천

지역 Community

실시간 환율

Map 기반 추천

생활비 계산기

실제 비자 신청 자동화

실시간 정책 자동 갱신
```

문서에서도 이러한 기능을
현재 구현된 기능처럼 표현하지 않습니다.

---

# README와 docs의 차이

## README

해당 디렉터리의 역할과
현재 개발 방향을 빠르게 이해하기 위한 문서입니다.

예:

```text
app/README.md

app/agent/README.md

data/README.md
```

---

## docs

더 상세한 설계와
팀의 의사결정을 기록합니다.

예:

```text
Agent 상세 설계

ERD

Database Schema

System Architecture

API 설계

데이터 수집 정책
```

즉:

```text
README
→ 빠른 이해

docs
→ 상세 설계 및 의사결정
```

으로 구분합니다.

---

# 문서 작성 원칙

- 실제 구현과 문서 내용이 다르지 않도록 유지
- 확정된 내용과 계획 중인 내용을 구분
- 존재하지 않는 기능을 구현 완료처럼 작성하지 않음
- Agent 역할 변경 시 관련 문서를 함께 수정
- DB Schema 변경 시 ERD와 Model 문서를 함께 수정
- 공식 정보 정책 변경 시 Data / Retrieval 문서를 함께 수정
- 중요한 기술 선택에는 이유를 기록
- 날짜와 정책 상태를 임의로 추정하지 않음
- 실제 코드가 확정되면 문서가 코드를 따라가도록 갱신

---

# 문서 변경 시 함께 확인할 README

Agent Architecture 변경:

```text
README.md

app/README.md

app/agent/README.md

app/models/README.md

tests/README.md
```

---

## Data Schema 변경

확인 대상:

```text
app/models/README.md

data/README.md

app/rules/README.md

app/retrieval/README.md

app/services/README.md
```

---

## API 변경

확인 대상:

```text
app/api/README.md

frontend/README.md

README.md
```

---

## Retrieval 변경

확인 대상:

```text
app/retrieval/README.md

data/README.md

scripts/README.md

tests/README.md
```

---

# 향후 작성 예정 문서

실제 개발 진행에 따라 다음 문서를 추가할 수 있습니다.

```text
Agent 상세 설계

LangGraph Workflow

System Architecture

Database ERD

Database Schema

Program / SupportProgram Schema

Evidence Policy

공식 정보 수집 기준

API Specification

Scenario Test 기준

Retrieval Evaluation 기준
```

---

# 현재 상태

현재는 다음 내용이 정의된 상태입니다.

```text
5개 Agent 역할

대상 국가 5개

상위 진출 경로 3개

Program / SupportProgram 구분

공식 정보 제공 범위

Eligibility 판정 정책

Evidence 관리 원칙

기본 Backend Architecture
```

다음 단계에서는
실제 Agent Skeleton과 공식 Sample Data를 기준으로:

```text
Agent File Structure

Shared State

Database Entity

ERD

Program Schema

SupportProgram Schema

Evidence Schema
```

를 구체화하고,
구현 결과에 맞춰 Architecture 문서를 작성합니다.

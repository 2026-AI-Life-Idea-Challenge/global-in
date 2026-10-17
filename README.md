# 🌍 Global-In

해외 진출을 준비하는 사용자를 위해
국가별 진출 경로, 실제 비자·체류 Program, 지원제도, 공식 규정과 준비 절차를
통합적으로 안내하는 AI 기반 해외 진출 지원 서비스입니다.

Global-In은 단순한 정보 검색 서비스가 아니라,
사용자의 상황을 이해하고,
적합한 진출 경로와 관련 지원제도를 탐색한 뒤,
공식 근거를 바탕으로 자격 검토와 준비 계획까지 연결하는 것을 목표로 합니다.

---

## Project Overview

Global-In은 다음 흐름을 중심으로 동작합니다.

```text
사용자 입력
   ↓
사용자 상황 이해
   ↓
진출 경로 탐색
   ↓
실제 Program 및 SupportProgram 탐색
   ↓
자격 검토
   ↓
공식 정보 확인
   ↓
준비 계획 생성
```

사용자의 질문에 따라 모든 기능을 항상 실행하는 것이 아니라,
필요한 Agent만 선택적으로 호출하는 구조를 사용합니다.

---

## Target Users

Global-In의 주요 대상 사용자는
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

## Target Countries

초기 MVP에서는 다음 5개 국가를 대상으로 합니다.

```text
일본
호주
미국
독일
캐나다
```

---

## Top-Level Advancement Paths

상위 진출 경로는 다음 3개로 구성합니다.

```text
워킹홀리데이 / 교환
유학
취업
```

5개 국가 × 3개 경로는
15개의 개별 비자를 의미하지 않습니다.

각 상위 경로 아래에
실제 비자·체류·교환 Program을 연결합니다.

예:

```text
Germany
+
Employment
   ↓
실제 독일 취업 관련 Program 후보
```

미국처럼 일반적인 Working Holiday Visa가 없는 국가의 경우,
상위 사용자 경험에서는 `워킹홀리데이 / 교환`으로 유지하되,
실제 구현에서는 J-1 등 관련 교환 Program과 연결합니다.

---

## Core Information Scope

Global-In은 크게 다음 3가지 정보 영역을 다룹니다.

### 1. 한국에서 제공하는 해외 진출 지원 정보

예:

```text
해외 취업 지원
해외 연수
준비 교육
지원금
해외 진출 가이드
```

주요 출처:

```text
한국 정부
공공기관
지원사업 운영기관
```

---

### 2. 목적지 국가의 외국인 진출·정착 지원 정보

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
지원제도 운영기관
```

---

### 3. 목적지 국가의 비자·법률 정보

예:

```text
비자
입국
체류
근로
학업
자격 요건
신청 절차
필요 서류
제한
의무
예외 규정
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

## Agent Architecture

Global-In은 LangGraph 기반의 5개 Agent 구조를 사용합니다.

```text
1. 사용자 이해 에이전트
2. 진출 경로 탐색·추천 에이전트
3. 자격 검토 에이전트
4. 공식 정보 안내 에이전트
5. 준비 계획 에이전트
```

LangGraph는 각 Agent의 실행 순서와 분기를 관리합니다.

---

## 1. 사용자 이해 에이전트

사용자의 목적과 현재 상황을 파악합니다.

주요 역할:

```text
Intent 파악
User Profile 생성
User Profile 갱신
Missing Information 탐지
추가 질문 생성
```

확인할 수 있는 정보 예:

```text
나이
국적
현재 거주지
학력
전공
경력
언어 능력
희망 국가
진출 목적
희망 시기
```

지원제도 검토가 필요한 경우:

```text
재학 여부
취업 상태
기존 참여 이력
기존 수혜 이력
중복 수혜 여부
```

등을 추가로 확인할 수 있습니다.

---

## 2. 진출 경로 탐색·추천 에이전트

사용자 조건을 기반으로
적합한 국가, 실제 Program, 관련 SupportProgram을 탐색하고 비교합니다.

주요 역할:

```text
국가 추천
진출 유형 추천
Program Resolver 사용
실제 Program 후보 탐색
SupportProgram 탐색
후보 비교
추천 이유 생성
```

추천 결과는
자격 검토 에이전트의 판정 결과를 반영할 수 있습니다.

---

## 3. 자격 검토 에이전트

공식 자격조건과 UserProfile을 비교합니다.

주요 역할:

```text
Program Eligibility 검토
SupportProgram Eligibility 검토
Rule Evaluator 호출
부족 조건 확인
예외 조건 확인
추가 확인 항목 정리
```

기본 판정 상태:

```text
조건 충족
조건 미충족
추가 확인 필요
```

구조화 가능한 조건은 Python 기반 Rule Evaluator가 판단하고,
Agent는 결과를 설명하고 정리합니다.

---

## 4. 공식 정보 안내 에이전트

공식 문서를 검색하여
비자, 체류, 근로, 학업, 지원제도 관련 정보를
근거 기반으로 설명합니다.

주요 역할:

```text
RAG Retrieval
Evidence 확인
공식 규정 설명
지원제도 설명
신청 절차 설명
공식 출처 제공
```

중요한 제도명이나 법률 용어는
필요한 경우 원문 명칭을 함께 제공합니다.

---

## 5. 준비 계획 에이전트

선택된 경로를 기준으로
비자 준비와 지원제도 신청을 하나의 실행 계획으로 구성합니다.

주요 역할:

```text
필요 서류 정리
Checklist 생성
단계별 Guide
Roadmap 생성
진행 상태 관리
다음 행동 제안
```

기본 단계:

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

---

## LangGraph Orchestration

대표적인 전체 Workflow는 다음과 같습니다.

```text
User Input
   ↓
사용자 이해 에이전트
   ↓
정보 충분?
   │
   ├─ NO
   │   ↓
   │ 추가 질문
   │   ↓
   │ User Answer
   │   ↓
   │ User Profile Update
   │   ↓
   │ 사용자 이해 에이전트
   │
   └─ YES
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

모든 질문이 이 전체 흐름을 사용하는 것은 아닙니다.

예:

```text
독일 취업 비자의 근로 조건만 알려줘.
```

와 같은 질문은
공식 정보 안내 에이전트를 중심으로 처리할 수 있습니다.

---

## Program과 SupportProgram

Global-In에서는 해외 진출 Program과
지원제도를 별도의 개념으로 관리합니다.

### Program

실제 비자·체류·교환 등
해외 진출에 직접 연결되는 Program입니다.

예:

```text
Working Holiday
Student Visa
Employment Visa
Exchange Program
Residence Status
```

### SupportProgram

해외 진출 과정에서 활용할 수 있는
국내외 지원제도입니다.

예:

```text
해외취업 지원금
해외 연수
준비 교육
장학 지원
외국인 취업 지원
정착 지원
```

하나의 SupportProgram은
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

---

## Eligibility와 Application Availability

다음 두 개념은 반드시 구분합니다.

```text
Eligibility
→ 사용자가 공식 자격 요건을 충족하는가
```

```text
Application Availability
→ 현재 실제 신청 가능한 상태인가
```

예:

```text
자격 조건 충족
+
현재 모집 종료
```

가 동시에 존재할 수 있습니다.

따라서:

```text
조건 충족
≠
현재 신청 가능
```

입니다.

현재 접수 상태가 확인되지 않은 경우
신청 가능하다고 단정하지 않습니다.

---

## Missing Information과 Failed Requirement

사용자 정보 부족과 조건 미충족도 구분합니다.

### Missing Information

```text
공식 조건은 존재
+
사용자 정보 없음
```

예:

```text
경력 2년 필요
사용자 경력 정보 없음
```

이 경우:

```text
사용자 이해 에이전트
→ 추가 질문
```

---

### Failed Requirement

```text
공식 조건 존재
+
사용자 정보 확인
+
조건 미충족
```

예:

```text
경력 2년 필요
사용자 경력 1년
```

이 경우:

```text
자격 검토 에이전트
→ 조건 미충족
```

---

## Information Validation Principles

Global-In은 다음 내용을 별도로 검증합니다.

```text
해당 Program이 실제 존재하는가

해당 SupportProgram이 실제 존재하는가

한국인에게 적용 가능한가

현재 적용 가능한 제도인가

현재 실제 신청 가능한가
```

이 정보들은 서로 동일하지 않습니다.

---

## Evidence Principles

Global-In은 공식 출처 기반 답변을 우선합니다.

Evidence에는 가능한 한 다음 정보를 저장합니다.

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

날짜가 없는 경우 임의로 생성하지 않습니다.

---

## Evidence Validation

검색된 문서가 바로 최종 Evidence가 되는 것은 아닙니다.

```text
Retrieval Result
   ↓
Evidence Validation
   ↓
Validated Evidence
```

확인 항목:

```text
질문과 관련 있는가

국가가 일치하는가

Program이 일치하는가

SupportProgram이 일치하는가

적용 대상이 일치하는가

공식 출처인가

적용 시점이 맞는가
```

공식 근거가 충돌하고 해소할 수 없는 경우:

```text
추가 확인 필요
```

로 처리합니다.

---

## Technology Stack

### Backend

```text
Python 3.11
FastAPI
LangGraph
LangChain
Pydantic
```

### LLM

```text
OpenAI
Claude
```

### Database / Retrieval

```text
PostgreSQL
pgvector
```

### Frontend

```text
Streamlit
```

### Data Collection

```text
requests
BeautifulSoup4
```

JavaScript Rendering이 반드시 필요한 사이트의 경우
추후 Playwright 사용을 검토합니다.

---

## System Architecture

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

## Project Structure

```text
global-in/
├─ app/
│  ├─ agent/
│  ├─ api/
│  ├─ models/
│  ├─ retrieval/
│  ├─ rules/
│  └─ services/
│
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ seed/
│
├─ docs/
│  ├─ architecture/
│  └─ planning/
│
├─ frontend/
│
├─ scripts/
│  ├─ crawl/
│  ├─ ingest/
│  └─ evaluate/
│
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ scenarios/
│
├─ .env.example
├─ .gitignore
├─ requirements.txt
└─ README.md
```

---

## Directory Roles

### `app/`

Backend 핵심 로직

```text
FastAPI
Agent
Models
Retrieval
Rules
Services
```

---

### `app/agent/`

LangGraph Orchestrator와
5개 Agent 구현

---

### `app/api/`

FastAPI Endpoint 구현

---

### `app/models/`

공통 Data Schema와
Agent State 정의

---

### `app/retrieval/`

공식 문서 검색 및
pgvector 기반 RAG 구현

---

### `app/rules/`

구조화된 공식 조건을 판정하는
Rule Evaluator 구현

---

### `app/services/`

Database, LLM, Embedding 등
공통 외부 Service 연결

---

### `data/`

수집된 원본 데이터,
정제 데이터,
초기 Seed Data 관리

---

### `docs/`

기획 및 설계 문서 관리

예:

```text
Agent 설계
System Architecture
ERD
Database Schema
API 설계
```

---

### `frontend/`

Streamlit 기반 사용자 인터페이스

---

### `scripts/`

데이터 수집, 적재, 평가용 Script

---

### `tests/`

Unit, Integration, Scenario Test 관리

---

## Current Main Files

현재 초기 구현 파일은 다음과 같습니다.

### FastAPI

```text
app/api/main.py
```

현재 Endpoint:

```text
GET /
GET /health
```

---

### Streamlit

```text
frontend/app.py
```

현재 기본 Frontend 화면을 구성합니다.

---

### Environment Variables

```text
.env.example
```

예:

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DATABASE_URL=
```

실제 Key는 `.env`에 저장하고
Git에 Commit하지 않습니다.

---

## MVP Scope

초기 MVP에서는 다음 기능을 구현합니다.

```text
사용자 Profile 파악

진출 목적 파악

실제 Program 탐색

SupportProgram 탐색

자격 검토

공식 정보 Retrieval

Evidence 기반 설명

필요 서류 안내

Checklist

Roadmap

Follow-up Question
```

---

## MVP에서 제외하는 기능

초기 구현에서는 다음 기능을 우선 제외합니다.

```text
실시간 공고 수집
실시간 채용 공고
항공권
주거 추천
지역 Community
환율
Map 기반 추천
생활비 계산기
실제 비자 신청 자동화
정책 실시간 자동 갱신
```

---

## Data Storage Strategy

### PostgreSQL

구조화된 정보를 저장합니다.

예:

```text
Program
SupportProgram
EligibilityRequirement
ApplicationInfo
RequiredDocument
Fee
Support Detail
Evidence Metadata
```

---

### pgvector

공식 비정형 문서 검색에 사용합니다.

예:

```text
법령
공식 Guide
FAQ
예외 규정
행정 안내
지원제도 상세 설명
```

---

## Data Collection Principles

공식 출처를 우선 수집합니다.

각 데이터에는 가능한 한 다음을 기록합니다.

```text
공식 기관
원문 제목
원문 URL
원문 게시일
원문 수정일
적용 기간
Global-In 확인일
```

다음도 구분하여 관리합니다.

```text
issuer_country
destination_country
target_nationality
residence_requirement
```

---

## Rule-Based Evaluation

구조화할 수 있는 공식 조건은
LLM이 아니라 Python Rule Evaluator가 판단합니다.

예:

```text
공식 조건:
age <= 30

사용자:
age = 27

결과:
조건 충족
```

자동 판정이 어려운 경우:

```text
추가 확인 필요
```

로 처리합니다.

---

## Retrieval Strategy

공식 문서를 검색할 때
가능한 한 Metadata Filtering 후 Vector Search를 수행합니다.

예:

```text
destination_country
purpose
program_id
support_program_id
target_nationality
information_topic
source_type
```

이를 통해 다른 국가나 다른 Program의 정보가
잘못 검색되는 문제를 줄입니다.

---

## Development Principles

```text
공식 출처 우선

Program과 SupportProgram 구분

Agent 역할 분리

LangGraph는 Workflow 관리

구조화 가능한 판단은 Rule Evaluator 사용

공식 문서 검색은 Retrieval 사용

외부 시스템 접근은 Service Layer 사용

공통 데이터는 Models 사용

공식 정보와 AI 해석 구분

Missing Information과 Failed Requirement 구분

Eligibility와 Application Availability 구분

확인되지 않은 정보를 임의로 생성하지 않음

모든 질문에서 모든 Agent를 호출하지 않음
```

---

## Branch Strategy

기본 개발 Branch:

```text
develop
```

안정된 버전:

```text
main
```

개발 흐름:

```text
feature/*
   ↓
develop
   ↓
main
```

---

### `develop`

현재 프로젝트의 기본 개발 Branch입니다.

새로운 기능과 문서 변경은
기본적으로 `develop`을 기준으로 진행합니다.

---

### `main`

배포 또는 안정된 버전을 유지합니다.

검증되지 않은 코드를
직접 Push하지 않는 것을 원칙으로 합니다.

---

### Feature Branch

기능 단위로 필요할 경우 별도 Branch를 생성합니다.

예:

```text
feature/agent
feature/database
feature/retrieval
feature/frontend
```

개발 완료 후:

```text
feature/*
   ↓
develop
```

형태로 Merge합니다.

---

## Development Environment

Python Version:

```text
Python 3.11
```

가상환경 생성:

```bash
python -m venv .venv
```

Windows 활성화:

```bash
.venv\Scripts\activate
```

Package 설치:

```bash
pip install -r requirements.txt
```

---

## Run FastAPI

```bash
uvicorn app.api.main:app --reload
```

기본 주소:

```text
http://127.0.0.1:8000
```

Health Check:

```text
http://127.0.0.1:8000/health
```

---

## Run Streamlit

```bash
streamlit run frontend/app.py
```

기본 주소:

```text
http://localhost:8501
```

---

## Development Roadmap

초기 개발 순서는 다음과 같이 진행합니다.

```text
1. Project Structure 구성

2. Agent 역할 정의

3. 공통 Data Schema 정의

4. Database / ERD 설계

5. 공식 데이터 수집

6. PostgreSQL Seed Data 구성

7. pgvector 문서 적재

8. User Profile / Agent State 구현

9. Program Resolver 구현

10. Rule Evaluator 구현

11. 진출 경로 탐색·추천 구현

12. 자격 검토 구현

13. Retrieval 구현

14. Evidence Validation 구현

15. 공식 정보 안내 구현

16. Checklist / Roadmap 구현

17. 준비 계획 구현

18. LangGraph Routing 통합

19. FastAPI 연결

20. Streamlit 연결

21. Unit / Integration / Scenario Test

22. Demo 및 최종 검증
```

---

## Testing

테스트는 크게 다음 세 영역으로 나눕니다.

```text
Unit Test
Integration Test
Scenario Test
```

### Unit Test

개별 Module 검증

예:

```text
Rule Evaluator
Program Resolver
Metadata Filter
Evidence Validator
```

### Integration Test

여러 Module 간 연결 검증

예:

```text
Agent + Rule Evaluator

Agent + Retrieval

FastAPI + Agent

Frontend + FastAPI
```

### Scenario Test

실제 사용자 질문 흐름을 기준으로 검증합니다.

예:

```text
독일 취업 준비자

캐나다 유학 준비자

일본 워킹홀리데이 준비자

미국 교환 프로그램 준비자
```

---

## Important Validation Points

```text
사용자 정보가 부족하면 적절한 질문을 하는가

Missing Information과 미충족 조건을 구분하는가

실제 Program을 올바르게 연결하는가

SupportProgram이 해당 사용자에게 적용되는가

Program과 SupportProgram 자격을 별도로 판정하는가

현재 접수 여부와 자격 여부를 혼동하지 않는가

올바른 공식 Evidence를 사용하는가

다른 국가의 근거가 섞이지 않는가

근거가 부족한 정보를 확정적으로 설명하지 않는가

Checklist와 Roadmap이 검토 결과에 맞게 생성되는가

불필요한 Agent 호출이 없는가

Workflow가 정상 종료되는가
```

---

## Current Status

현재 완료된 기본 작업:

```text
Python 3.11 개발 환경 구성

Project Directory 구성

FastAPI 기본 실행 확인

Streamlit 기본 실행 확인

Git Repository 연결

main / develop Branch 구성

GitHub 기본 문서 구조 구성

5개 Agent 역할 정의

공식 정보 범위 정의
```

현재는 다음 단계로 진행 중입니다.

```text
Agent 상세 구조 구체화
Database / ERD 설계
공통 Schema 정의
공식 데이터 수집 구조 설계
```

실제 Agent Skeleton과 DB 구조가 확정되면
README와 Architecture 문서를 구현 결과에 맞게 지속적으로 갱신합니다.

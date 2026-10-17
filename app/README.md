# app

Global-In의 Backend 핵심 로직을 구현하는 디렉터리입니다.

FastAPI, LangGraph 기반 Agent, 데이터 Model, Retrieval, Rule Evaluator, Service Layer를 포함하며,
사용자 입력을 받아 해외 진출 경로·비자·지원제도를 탐색하고 검토한 뒤
공식 근거 기반의 답변과 준비 계획을 생성합니다.

---

## 전체 역할

`app/`은 다음 영역을 담당합니다.

```text
API
Agent Orchestration
공통 Data Model
RAG Retrieval
Eligibility Rule Evaluation
Database / LLM Service
```

전체 흐름은 다음과 같습니다.

```text
User
  ↓
Streamlit
  ↓
FastAPI
  ↓
LangGraph Orchestrator
  ↓
5개 Agent
  ↓
공통 Module / Service
  ↓
PostgreSQL / pgvector / LLM
  ↓
Final Response
```

---

## 디렉터리 구조

현재 기본 구조는 다음과 같습니다.

```text
app/
├─ __init__.py
├─ agent/
├─ api/
├─ models/
├─ retrieval/
├─ rules/
├─ services/
└─ README.md
```

각 디렉터리는 책임을 분리하여 관리합니다.

---

# `agent/`

LangGraph 기반 Agent와 전체 Workflow를 구현합니다.

Global-In은 하나의 Agent가 모든 업무를 처리하는 구조가 아니라,
역할이 분리된 5개 Agent를 사용합니다.

```text
1. 사용자 이해 에이전트
2. 진출 경로 탐색·추천 에이전트
3. 자격 검토 에이전트
4. 공식 정보 안내 에이전트
5. 준비 계획 에이전트
```

LangGraph는 이 Agent들의 실행 순서와 분기를 관리합니다.

---

## 사용자 이해 에이전트

사용자의 목적과 상황을 파악하고
Profile 및 Missing Information을 관리합니다.

주요 역할:

```text
Intent 파악
User Profile 생성
User Profile 갱신
Missing Information 탐지
추가 질문 생성
```

예:

```text
사용자:
독일로 취업하고 싶어요.

↓

확인:

나이
국적
학력
전공
경력
언어
희망 시기
```

---

## 진출 경로 탐색·추천 에이전트

사용자 조건을 바탕으로 실제 진출 Program과
관련 SupportProgram을 탐색하고 비교합니다.

주요 역할:

```text
국가 후보 탐색
진출 유형 탐색
Program Resolver 사용
실제 Program 후보 생성
SupportProgram 탐색
후보 비교
추천 이유 생성
```

---

## 자격 검토 에이전트

공식 자격 조건과 UserProfile을 비교합니다.

주요 역할:

```text
Program Eligibility 검토
SupportProgram Eligibility 검토
Rule Evaluator 호출
부족 조건 탐지
추가 확인 조건 정리
```

기본 판정 상태:

```text
조건 충족
조건 미충족
추가 확인 필요
```

---

## 공식 정보 안내 에이전트

공식 자료를 검색하고
근거가 확인된 정보를 한국어로 설명합니다.

주요 역할:

```text
RAG Retrieval
Evidence 확인
비자 / 체류 규정 설명
지원제도 설명
신청 절차 안내
공식 출처 제공
```

---

## 준비 계획 에이전트

검토 결과를 기반으로
사용자별 준비 절차를 구성합니다.

주요 역할:

```text
필요 서류 정리
Checklist 생성
단계별 Guide
Roadmap 생성
진행 상태 관리
다음 행동 제안
```

자세한 내용은:

```text
app/agent/README.md
```

에서 관리합니다.

---

# `api/`

FastAPI 기반 Backend API를 구현합니다.

Frontend와 Agent Layer 사이의 진입점 역할을 담당합니다.

기본 구조:

```text
Streamlit
   ↓
FastAPI
   ↓
Agent Workflow
```

주요 역할:

```text
HTTP Request 수신
Request Validation
Agent 호출
Response 반환
Health Check
Error Handling
```

현재 기본 API:

```text
GET /
GET /health
```

향후 Chat Endpoint 등을 추가합니다.

예:

```text
POST /chat
```

API가 Agent 내부 구현을 직접 담당하지 않도록 합니다.

자세한 내용은:

```text
app/api/README.md
```

에서 관리합니다.

---

# `models/`

프로젝트 전체에서 사용하는 공통 Data Schema를 관리합니다.

주요 Model:

```text
UserProfile
AgentState

Program
SupportProgram

EligibilityRequirement
EligibilityResult

ApplicationInfo
ApplicationAvailability

RequiredDocument
Evidence

Checklist
Roadmap

ChatRequest
ChatResponse
```

API, Agent, Rules, Retrieval, Services가
가능한 한 동일한 Model을 사용하도록 합니다.

자세한 내용은:

```text
app/models/README.md
```

에서 관리합니다.

---

# `retrieval/`

공식 문서를 검색하는 RAG Retrieval Module을 구현합니다.

구조:

```text
User Query
   ↓
Agent State
   ↓
Metadata Filtering
   ↓
Embedding
   ↓
pgvector Search
   ↓
Evidence 후보
```

검색 대상:

```text
한국 해외 진출 지원 정보
목적지 국가 지원제도
비자 / 체류 / 근로 / 학업 규정
공식 법령
행정 안내
공식 FAQ
예외 규정
```

검색 결과가 바로 최종 근거가 되는 것은 아닙니다.

```text
Retrieval Result
   ↓
Evidence Validation
   ↓
Validated Evidence
```

자세한 내용은:

```text
app/retrieval/README.md
```

에서 관리합니다.

---

# `rules/`

구조화된 공식 조건을 기반으로
사용자 자격을 판정하는 Rule Evaluator를 구현합니다.

LLM이 자격 조건을 임의로 판단하지 않고,
명확한 공식 조건은 Python Code로 비교합니다.

예:

```text
공식 조건:
age <= 30

사용자:
age = 27

↓

조건 충족
```

기본 상태:

```text
조건 충족
조건 미충족
추가 확인 필요
```

---

## Rule Evaluator가 처리하는 정보

예:

```text
나이
국적
거주지
학력
경력
언어
재정
재학 여부
취업 상태
수혜 이력
중복 참여 제한
```

---

## Rule Evaluator로 판단하지 않는 경우

예:

```text
예외 규정
기관 재량
복잡한 법률 해석
구조화되지 않은 조건
공식 근거 충돌
```

이 경우:

```text
추가 확인 필요
```

로 처리합니다.

자세한 내용은:

```text
app/rules/README.md
```

에서 관리합니다.

---

# `services/`

외부 시스템과 연결하는 공통 Service Layer입니다.

예:

```text
Database Service
LLM Service
Embedding Service
Program Service
SupportProgram Service
```

Agent가 PostgreSQL이나 LLM API에
직접 반복 접근하지 않도록 공통화합니다.

예:

```text
Agent
   ↓
Service
   ↓
PostgreSQL
```

또는:

```text
Agent
   ↓
LLM Service
   ↓
OpenAI / Claude
```

자세한 내용은:

```text
app/services/README.md
```

에서 관리합니다.

---

# Program과 SupportProgram 구분

Global-In에서는 해외 진출 Program과
지원제도를 별도의 개념으로 관리합니다.

### Program

사용자가 해외에 진출하기 위해 필요한
실제 비자·체류·교환 등의 경로입니다.

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
한국 또는 목적지 국가의 지원제도입니다.

예:

```text
해외취업 지원
해외연수 지원
준비 교육
지원금
장학금
외국인 정착 지원
```

관계:

```text
Program
   ↑
   │
ProgramSupportLink
   │
   ↓
SupportProgram
```

하나의 SupportProgram은
여러 Program과 연결될 수 있습니다.

---

# 정보 범위

Global-In은 다음 세 영역의 정보를 다룹니다.

---

## 1. 한국에서 제공하는 해외 진출 지원 정보

예:

```text
해외 취업 지원
해외 연수
준비 교육
지원금
해외 진출 Guide
```

출처:

```text
한국 정부
공공기관
지원사업 운영기관
```

---

## 2. 목적지 국가의 외국인 진출·정착 지원 정보

예:

```text
외국 인재 유치
외국인 취업 지원
유학 지원
장학 지원
정착 지원
```

출처:

```text
목적지 국가 정부
공공기관
교육기관
지원제도 운영기관
```

---

## 3. 목적지 국가 비자·법률 정보

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
예외
```

출처:

```text
이민기관
대사관 / 영사관
공식 법령
노동 관련 기관
교육 관련 기관
관할 행정기관
```

---

# 데이터 계층

Global-In은 크게 두 종류의 데이터를 사용합니다.

```text
Structured Data
+
Unstructured Official Documents
```

---

## Structured Data

PostgreSQL에 저장합니다.

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

## Unstructured Official Documents

pgvector를 이용하여 검색합니다.

예:

```text
법령 본문
공식 Guide
FAQ
예외 규정
행정 안내
지원제도 상세 설명
```

---

# Evidence 관리

Global-In은 답변에 사용한 공식 근거를
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

날짜가 존재하지 않는 경우
임의로 생성하지 않습니다.

---

## Evidence 검증 기준

```text
질문과 관련 있는가

국가가 일치하는가

Program이 일치하는가

SupportProgram이 일치하는가

적용 대상이 일치하는가

공식 출처인가

적용 시점이 맞는가
```

충돌을 해결할 수 없는 경우:

```text
추가 확인 필요
```

로 처리합니다.

---

# Eligibility와 Application Availability 구분

다음 두 개념은 반드시 구분합니다.

```text
Eligibility

사용자가 공식 자격 요건을 충족하는가?
```

```text
Application Availability

현재 실제 신청 가능한 상태인가?
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

---

# 사용자 정보 부족과 조건 미충족 구분

다음 두 상태 역시 별도로 처리합니다.

---

## Missing Information

```text
공식 조건은 확인됨
+
사용자 정보 없음
```

예:

```text
경력 2년 필요
사용자 경력 정보 없음
```

처리:

```text
사용자 이해 에이전트
→ 추가 질문
```

---

## Failed Requirement

```text
공식 조건 확인
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

처리:

```text
자격 검토 에이전트
→ 조건 미충족
```

---

# 기본 Agent Workflow

대표적인 전체 흐름은 다음과 같습니다.

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

모든 질문에서 전체 Agent를 실행하지 않습니다.

필요한 Agent만 선택적으로 호출합니다.

---

## 예시 1

사용자:

```text
독일로 취업하려는데 어떤 방법이 있어?
```

흐름:

```text
사용자 이해
   ↓
진출 경로 탐색·추천
   ↓
필요 시 자격 검토
```

---

## 예시 2

사용자:

```text
독일 취업 비자의 근로 제한만 알려줘.
```

흐름:

```text
공식 정보 안내 에이전트
   ↓
Retrieval
   ↓
Evidence
```

---

## 예시 3

사용자:

```text
이 비자 신청 준비 순서 알려줘.
```

흐름:

```text
공식 정보 확인
   ↓
준비 계획 에이전트
```

---

# 초기 MVP 범위

대상 국가:

```text
일본
호주
미국
독일
캐나다
```

상위 진출 경로:

```text
워킹홀리데이 / 교환
유학
취업
```

여기서 5개 국가 × 3개 상위 경로는
15개의 개별 비자를 의미하지 않습니다.

각 상위 경로 아래에
실제 비자·체류·교환 Program을 연결합니다.

---

## 예시

```text
USA
+
워킹홀리데이 / 교환
```

미국에는 일반적인 Working Holiday Visa가 없으므로,
실제 구현에서는 관련 교환 프로그램과 J-1 등
해당 목적에 맞는 실제 Program을 연결합니다.

---

# MVP에서 제외하는 기능

초기 구현에서는 다음 기능을 우선 제외합니다.

```text
실시간 채용 공고
실시간 항공권 정보
실시간 환율
주거 추천
지역 Community
Map 기반 추천
생활비 계산기
실제 비자 신청 자동화
정책 실시간 자동 갱신
```

향후 확장 가능하도록
현재 Architecture에서는 영역을 분리해 둡니다.

---

# 구현 원칙

```text
Agent는 명확한 역할을 가짐

LangGraph는 Workflow를 관리

Agent가 모든 기능을 직접 구현하지 않음

구조화된 판단은 Rule Evaluator 사용

공식 문서 검색은 Retrieval 사용

외부 시스템 접근은 Service Layer 사용

공통 데이터는 Models 사용

Program과 SupportProgram을 구분

공식 정보와 AI 해석을 구분

사용자 정보 부족과 조건 미충족을 구분

Eligibility와 Application Availability를 구분

확인되지 않은 정보를 임의로 생성하지 않음

공식 근거가 부족한 경우 확정적으로 답하지 않음

모든 Agent를 항상 호출하지 않음
```

---

# 디렉터리 간 관계

```text
app/
│
├─ api/
│    │
│    └─ HTTP Interface
│
├─ agent/
│    │
│    └─ LangGraph + 5 Agents
│
├─ models/
│    │
│    └─ Shared Schema
│
├─ retrieval/
│    │
│    └─ RAG / pgvector
│
├─ rules/
│    │
│    └─ Rule Evaluator
│
└─ services/
     │
     ├─ Database
     ├─ LLM
     └─ External Service
```

---

# 개발 의존 관계

대략적인 의존 방향은 다음과 같습니다.

```text
API
 ↓
Agent
 ↓
Models
 ↓
Rules / Retrieval / Services
 ↓
PostgreSQL / pgvector / LLM
```

가능하면 하위 Module이
상위 Agent 구현에 직접 의존하지 않도록 합니다.

---

# 개발 순서

현재 기준 예상 순서:

```text
1. Models 기본 Schema 정의

2. Agent State 정의

3. PostgreSQL 기본 Schema 설계

4. Program / SupportProgram 데이터 구조 정의

5. 사용자 이해 에이전트 구현

6. Program Resolver 구현

7. Rule Evaluator 구현

8. 진출 경로 탐색·추천 에이전트 구현

9. 자격 검토 에이전트 구현

10. pgvector Retrieval 구현

11. Evidence Validation 구현

12. 공식 정보 안내 에이전트 구현

13. Checklist / Roadmap 구현

14. 준비 계획 에이전트 구현

15. Agent Routing 구현

16. FastAPI 연결

17. Frontend 연결

18. Integration / Scenario Test
```

실제 개발 과정에서는
데이터 수집과 일부 Backend 구현을 병렬로 진행할 수 있습니다.

---

# 테스트 원칙

`app/` 내부 기능은 각각 분리하여 검증합니다.

### Agent

```text
올바른 Agent가 호출되는가
State 전달이 정상적인가
불필요한 Agent 호출이 없는가
Loop가 정상 종료되는가
```

### Rules

```text
공식 조건을 정확히 판정하는가
Missing Information과 미충족을 구분하는가
자동 판단 불가능 조건을 확정하지 않는가
```

### Retrieval

```text
올바른 국가 자료를 검색하는가
Program이 일치하는가
SupportProgram이 일치하는가
공식 근거를 유지하는가
```

### Services

```text
DB 연결
LLM 연결
예외 처리
Timeout
환경변수 처리
```

### API

```text
Request Validation
Agent 연결
Response Schema
Error Response
Health Check
```

---

# 현재 상태

현재 Backend 기본 디렉터리와 FastAPI 실행 환경이 구성되어 있으며,
5개 Agent 역할과 정보 범위를 기준으로
Models, Database, Retrieval, Rule Evaluator 및 Workflow를 구체화하는 단계입니다.

실제 데이터 수집과 Agent Skeleton 구현이 진행되면
세부 파일 구조와 책임은 구현 결과에 맞춰 지속적으로 갱신합니다.

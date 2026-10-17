# app/services

Global-In에서 외부 시스템과 연결되는 공통 Service Layer를 구현하는 디렉터리입니다.

Agent, Retrieval, API가 PostgreSQL, pgvector, LLM API, Embedding API 같은 외부 시스템에
직접 반복 접근하지 않도록 공통 기능을 `app/services/`에서 관리합니다.

Service Layer는 비즈니스 판단을 수행하는 Agent나 Rule Evaluator와 달리,
외부 리소스 접근과 공통 연결 로직을 담당합니다.

---

## 주요 역할

`app/services/`는 다음과 같은 기능을 담당합니다.

```text
Database 연결
PostgreSQL Query
pgvector 접근
LLM 호출
Embedding 호출
Program 조회
SupportProgram 조회
Evidence 조회
Session / Conversation 저장
공통 외부 Service 예외 처리
```

---

## 전체 구조에서의 위치

```text
Frontend
   ↓
FastAPI
   ↓
LangGraph / Agent
   ↓
Service Layer
   ↓
External Resources
```

예:

```text
자격 검토 에이전트
   ↓
Program Service
   ↓
PostgreSQL
```

```text
공식 정보 안내 에이전트
   ↓
Retrieval
   ↓
Embedding Service
   ↓
Embedding API
```

```text
Agent
   ↓
LLM Service
   ↓
OpenAI / Claude
```

---

## Service Layer를 사용하는 이유

외부 시스템 연결 코드를 각 Agent에 직접 작성하면
다음 문제가 발생할 수 있습니다.

```text
DB 연결 코드 중복
LLM 호출 코드 중복
Timeout 처리 중복
Retry 정책 불일치
환경변수 사용 방식 불일치
Exception 처리 방식 불일치
테스트 어려움
```

따라서 외부 연결 로직을 Service Layer로 분리합니다.

---

## 기본 원칙

```text
Agent는 비즈니스 흐름 담당

Rules는 결정적 자격 판정 담당

Retrieval은 검색 로직 담당

Services는 외부 시스템 연결 담당
```

즉:

```text
Agent
→ 무엇을 해야 하는지 결정

Service
→ 필요한 외부 데이터와 기능 제공
```

으로 역할을 분리합니다.

---

## 예상 파일 구조

현재 구조를 기준으로 다음과 같은 구성을 고려합니다.

```text
app/services/
├─ __init__.py
├─ database.py
├─ program_service.py
├─ support_service.py
├─ evidence_service.py
├─ llm.py
├─ embedding.py
├─ session_service.py
└─ README.md
```

실제 구현 과정에서 파일명과 구조는 변경될 수 있습니다.

---

# `database.py`

PostgreSQL과 연결되는 공통 Database Service입니다.

주요 역할:

```text
Database Connection
Connection Pool
Transaction 관리
공통 Query 실행
예외 처리
```

---

## Database 연결

환경변수:

```text
DATABASE_URL
```

을 사용합니다.

예:

```text
postgresql://user:password@host:port/database
```

실제 연결 정보는 `.env`에 저장하고
Git에 Commit하지 않습니다.

---

## Database Connection 흐름

```text
Agent / Module
   ↓
Service
   ↓
Database Connection
   ↓
PostgreSQL
```

각 Agent가 직접 새로운 DB Connection을 생성하지 않는 구조를 지향합니다.

---

## PostgreSQL 역할

구조화된 정보를 저장합니다.

예:

```text
Program
SupportProgram
EligibilityRequirement
ApplicationInfo
ApplicationAvailability
RequiredDocument
SupportDetail
Evidence Metadata
```

---

## pgvector 역할

PostgreSQL의 `pgvector` 확장을 이용하여
공식 문서 Embedding을 저장하고 검색합니다.

예:

```text
Official Document
Document Chunk
Embedding
Metadata
```

Vector Search 자체의 검색 전략은
`app/retrieval/`에서 담당합니다.

Service Layer는 DB Query 실행을 지원합니다.

---

# `program_service.py`

비자·체류·교환 등 실제 해외 진출 Program 관련
구조화 데이터를 조회하는 Service입니다.

---

## 주요 역할

```text
Program 조회

국가별 Program 조회

목적별 Program 조회

Program 상세 정보 조회

Eligibility Requirement 조회

ApplicationInfo 조회

RequiredDocument 조회

관련 SupportProgram 조회
```

---

## 조회 예시

```text
destination_country = Germany
purpose = Employment
```

입력:

```text
Germany
Employment
```

출력:

```text
관련 실제 Program 목록
```

---

## Program Resolver와의 관계

Program Resolver는:

```text
사용자의 국가와 목적에 맞는 실제 Program 후보 결정
```

을 담당합니다.

Program Service는:

```text
Program Resolver가 사용할 구조화된 Program 데이터 제공
```

을 담당합니다.

구조:

```text
진출 경로 탐색·추천 에이전트
   ↓
Program Resolver
   ↓
Program Service
   ↓
PostgreSQL
```

---

# `support_service.py`

한국 또는 목적지 국가의 SupportProgram 데이터를 조회합니다.

SupportProgram 예:

```text
해외취업 지원
해외 연수
준비 교육
지원금
장학금
외국인 취업 지원
정착 지원
```

---

## 주요 역할

```text
SupportProgram 조회

issuer_country 기준 조회

destination_country 기준 조회

목적별 지원제도 조회

한국인 적용 가능 대상 조회

관련 Program 조회

Eligibility Requirement 조회

ApplicationInfo 조회

RequiredDocument 조회

Support Detail 조회
```

---

## SupportProgram 검색 예

사용자:

```text
독일 취업 준비할 때 받을 수 있는 지원 알려줘.
```

조건 예:

```text
destination_country = Germany
purpose = Employment
target_nationality = Korean
```

Service는 해당 조건과 관련된
SupportProgram 후보를 반환합니다.

---

## 한국 측 지원제도 예

```text
issuer_country = Korea
destination_country = Germany
purpose = Employment
```

---

## 목적지 국가 지원제도 예

```text
issuer_country = Germany
destination_country = Germany
target_nationality = Korean
```

한국 국적 사용자에게 적용 가능한지
별도로 확인해야 합니다.

---

## Program과 SupportProgram 관계

하나의 SupportProgram은
여러 Program과 연결될 수 있습니다.

예:

```text
SupportProgram A
   ├─ Germany Employment Program
   ├─ Canada Employment Program
   └─ Japan Employment Program
```

DB에서는 연결 Entity를 사용할 수 있습니다.

예:

```text
ProgramSupportLink
```

구조:

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

# `evidence_service.py`

공식 Evidence Metadata와 문서 정보를 조회하는 Service입니다.

---

## 주요 역할

```text
Evidence 조회

Program 관련 Evidence 조회

SupportProgram 관련 Evidence 조회

공식 기관 기준 조회

URL 기준 조회

날짜 Metadata 조회

Document / Chunk 조회
```

---

## Evidence 기본 정보

예:

```text
evidence_id

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
```

---

## Evidence Service와 Retrieval의 차이

Evidence Service는:

```text
DB에 저장된 Evidence 정보 조회
```

를 담당합니다.

Retrieval은:

```text
사용자 질문과 가장 관련 있는 Evidence 후보 검색
```

을 담당합니다.

즉:

```text
Evidence Service
→ 데이터 접근

Retrieval
→ 검색 전략
```

으로 구분합니다.

---

# `llm.py`

Global-In에서 사용하는 LLM 호출을 공통화합니다.

현재 사용할 수 있는 모델 Provider:

```text
OpenAI
Claude
```

---

## 주요 역할

```text
LLM Client 생성

Prompt 전달

Response 반환

Model 설정

Temperature 설정

Timeout

Retry

Provider 선택

Exception 처리
```

Agent마다 직접 OpenAI Client를 생성하지 않는 구조를 목표로 합니다.

---

## LLM Service 사용 예

```text
사용자 이해 에이전트
   ↓
LLM Service
   ↓
Intent / Profile Extraction
```

```text
진출 경로 탐색·추천 에이전트
   ↓
LLM Service
   ↓
추천 이유 생성
```

```text
공식 정보 안내 에이전트
   ↓
LLM Service
   ↓
Evidence 기반 한국어 설명
```

```text
준비 계획 에이전트
   ↓
LLM Service
   ↓
Roadmap 설명
```

---

## LLM이 하지 않는 역할

다음 기능을 LLM Service가 직접 담당하지 않습니다.

```text
공식 Program 조회

SupportProgram 조회

Eligibility Rule 판정

Vector Search

Evidence Validity 판정

Database Transaction
```

LLM Service는 모델 호출 Wrapper 역할에 집중합니다.

---

## OpenAI 환경변수

```text
OPENAI_API_KEY
```

---

## Claude 환경변수

```text
ANTHROPIC_API_KEY
```

---

## Provider 추상화

향후 Provider 변경에 대응하기 위해
가능하면 Agent 코드가 특정 SDK에 강하게 의존하지 않도록 합니다.

예:

```text
Agent
   ↓
LLM Service
   ↓
Provider Adapter
   ├─ OpenAI
   └─ Claude
```

초기 MVP에서 지나치게 복잡한 추상화를 만들 필요는 없지만,
Agent 내부에 Provider 전용 코드를 반복 작성하지 않습니다.

---

# `embedding.py`

문서와 사용자 Query의 Embedding 생성을 담당합니다.

---

## 주요 역할

```text
Query Embedding 생성

Document Embedding 생성

Embedding Model 설정

Batch Embedding

Timeout

Retry

Exception 처리
```

---

## Retrieval과의 관계

```text
Retrieval
   ↓
Embedding Service
   ↓
Embedding Model
```

검색 흐름:

```text
User Query
   ↓
Embedding Service
   ↓
Query Vector
   ↓
pgvector Search
```

문서 적재:

```text
Document Chunk
   ↓
Embedding Service
   ↓
Embedding Vector
   ↓
PostgreSQL / pgvector
```

---

## Embedding Model 선택 기준

```text
한국어 성능

영어 성능

다국어 성능

비용

Latency

Embedding Dimension
```

실제 모델은 Retrieval 평가 후 결정합니다.

---

# `session_service.py`

여러 Turn에 걸친 사용자 대화를 관리하기 위한 Service입니다.

초기 MVP에서 실제 구현 여부와 저장 방식은
Agent Workflow 구현 과정에서 결정합니다.

---

## 필요한 이유

Global-In은 사용자에게 추가 질문을 할 수 있습니다.

예:

```text
User:
독일 취업하고 싶어요.

AI:
경력은 몇 년인가요?

User:
2년입니다.
```

두 번째 User Message를 처리할 때
이전 UserProfile과 AgentState를 확인할 필요가 있습니다.

---

## 예상 역할

```text
Session 조회

Conversation 조회

UserProfile 저장

UserProfile 갱신

Selected Program 저장

Agent State 일부 저장

Conversation History 저장
```

---

## Session 관련 예상 정보

```text
session_id

user_profile

intent

selected_program

selected_support_programs

conversation_history

updated_at
```

민감하거나 불필요한 정보를
무조건 저장하지 않도록 합니다.

---

# Agent와 Service 관계

5개 Agent 기준 주요 Service 사용 예:

---

## 사용자 이해 에이전트

```text
LLM Service
Session Service
```

사용 목적:

```text
Intent Extraction
Profile Extraction
기존 UserProfile 조회 / 갱신
```

---

## 진출 경로 탐색·추천 에이전트

```text
Program Service
SupportProgram Service
LLM Service
```

사용 목적:

```text
Program 후보 조회
SupportProgram 후보 조회
후보 비교
추천 이유 생성
```

---

## 자격 검토 에이전트

```text
Program Service
SupportProgram Service
Evidence Service
```

그리고:

```text
Rule Evaluator
```

를 사용합니다.

Rule Evaluator는 Service가 아니라
`app/rules/`의 결정적 Module입니다.

---

## 공식 정보 안내 에이전트

```text
Evidence Service
Embedding Service
LLM Service
```

그리고:

```text
Retrieval
```

을 사용합니다.

---

## 준비 계획 에이전트

```text
Program Service
SupportProgram Service
Evidence Service
LLM Service
```

를 활용하여:

```text
필요 서류
신청 절차
공식 일정
Checklist
Roadmap
```

을 구성합니다.

---

# Services와 Models의 관계

Service가 반환하는 데이터는
가능한 한 `app/models/`의 공통 Model을 사용합니다.

예:

```text
Program Service
→ Program

SupportProgram Service
→ SupportProgram

Evidence Service
→ Evidence

Session Service
→ UserProfile / AgentState
```

Raw Dictionary를 프로젝트 전체에
무분별하게 전달하지 않는 것을 원칙으로 합니다.

---

# Services와 API의 관계

FastAPI도 필요한 경우 Service Layer를 사용할 수 있습니다.

예:

```text
Session 조회
Conversation 저장
```

구조:

```text
API
   ↓
Session Service
   ↓
Database
```

하지만 비즈니스 흐름을 API에서 직접 조합하지 않습니다.

---

# Database Service와 Repository Pattern

프로젝트 규모가 커질 경우
Service와 DB Query 책임을 더 분리할 수 있습니다.

예:

```text
Agent
   ↓
Service
   ↓
Repository
   ↓
PostgreSQL
```

예상 구조:

```text
ProgramService
   ↓
ProgramRepository
```

초기 MVP에서는 불필요한 계층 증가를 피하고,
DB Query가 복잡해지는 시점에 Repository Layer 도입을 검토합니다.

---

# 환경변수 관리

현재 주요 환경변수:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
DATABASE_URL
```

`.env.example`:

```text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DATABASE_URL=
```

실제 값은 `.env`에서 관리합니다.

`.env`는 `.gitignore`에 포함하여
Repository에 업로드하지 않습니다.

---

# Service Configuration

향후 공통 설정값이 증가하면
별도 Config Module을 둘 수 있습니다.

예:

```text
app/config.py
```

관리할 수 있는 설정:

```text
Database URL

LLM Model Name

Embedding Model

Timeout

Retry Count

Retrieval Top-K
```

환경변수 해석을 여러 Service 파일에서
반복하지 않는 것을 권장합니다.

---

# Timeout

외부 Service 호출에는 Timeout을 설정합니다.

예:

```text
Database Connection Timeout

LLM Request Timeout

Embedding Request Timeout
```

외부 서비스 장애로 인해
Agent Workflow가 무한 대기하지 않도록 합니다.

---

# Retry

일시적인 네트워크 오류에 대해서는
제한된 Retry를 사용할 수 있습니다.

예:

```text
LLM 5xx

Rate Limit

일시적인 DB 연결 실패
```

다만 모든 Error를 무조건 재시도하지 않습니다.

예:

```text
Authentication Error

잘못된 Request

잘못된 SQL

Schema Validation Error
```

등은 Retry로 해결되지 않습니다.

---

# Error Handling

Service Layer에서는
외부 SDK Exception을 그대로 상위 Layer에 노출하지 않는 것을 권장합니다.

예:

```text
OpenAI SDK Exception
   ↓
LLM Service
   ↓
공통 Service Error
   ↓
Agent / API
```

이를 통해 Provider 변경 시
상위 코드 변경을 줄일 수 있습니다.

---

# Logging

Service Layer에서는
외부 연결 문제를 추적할 수 있도록
필요한 Logging을 남길 수 있습니다.

예:

```text
Service Name

Request Type

처리 시간

Error Type

Retry 여부
```

단 다음 정보는 Log에 직접 남기지 않도록 주의합니다.

```text
API Key

Database Password

민감한 User Data

전체 Prompt

전체 개인정보
```

---

# Database Transaction

여러 DB 변경이 하나의 작업으로 묶이는 경우
Transaction을 사용합니다.

예:

```text
Program 저장

Eligibility Requirement 저장

Evidence 연결
```

중간에 실패하면
부분적으로 데이터가 남지 않도록 처리할 수 있습니다.

---

# Connection Pool

FastAPI 환경에서는 Request마다
새로운 Database Connection을 무제한 생성하는 것을 피합니다.

필요한 경우 Connection Pool을 사용합니다.

예:

```text
FastAPI
   ↓
DB Connection Pool
   ↓
PostgreSQL
```

실제 방식은 사용하는 PostgreSQL Driver에 맞춰 결정합니다.

현재 설치 환경:

```text
psycopg
```

---

# Async 여부

Service 함수의 동기 / 비동기 여부는
실제 API 및 Agent 실행 방식에 맞춰 결정합니다.

예:

```python
async def call_llm(...):
    ...
```

또는:

```python
def get_program(...):
    ...
```

모든 함수를 이유 없이 `async`로 만들 필요는 없습니다.

외부 I/O와 LangGraph 실행 구조를 기준으로 결정합니다.

---

# Cache

초기 MVP에서는 Cache를 필수로 두지 않습니다.

향후 다음 데이터는 Cache 후보가 될 수 있습니다.

```text
변경이 적은 Program 정보

SupportProgram 기본 정보

Embedding 결과

공식 문서 Metadata
```

단, 정책과 신청 상태처럼 시점에 민감한 정보는
오래된 Cache가 잘못된 안내로 이어질 수 있으므로
별도 정책이 필요합니다.

---

# Program Service 예시 Interface

예상 형태:

```python
def get_program(program_id: str):
    ...
```

```python
def find_programs(
    destination_country: str,
    purpose: str
):
    ...
```

---

# SupportProgram Service 예시 Interface

예:

```python
def get_support_program(
    support_program_id: str
):
    ...
```

```python
def find_support_programs(
    destination_country: str,
    purpose: str,
    nationality: str | None = None
):
    ...
```

실제 Type은 Pydantic Model과 DB Schema 확정 후 정의합니다.

---

# Evidence Service 예시 Interface

```python
def get_evidence(
    evidence_id: str
):
    ...
```

```python
def get_program_evidence(
    program_id: str
):
    ...
```

```python
def get_support_program_evidence(
    support_program_id: str
):
    ...
```

---

# LLM Service 예시 Interface

```python
async def generate(
    messages,
    model=None,
    temperature=0
):
    ...
```

또는 Provider별 기능을 내부에서 분기할 수 있습니다.

---

# Embedding Service 예시 Interface

```python
async def embed_query(
    text: str
):
    ...
```

```python
async def embed_documents(
    texts: list[str]
):
    ...
```

---

# Service 테스트

Service Layer는 Agent와 별도로 테스트할 수 있어야 합니다.

---

## Database Service Test

```text
DB 연결 성공

DB 연결 실패 처리

Query 실행

Transaction Rollback
```

---

## Program Service Test

```text
program_id 조회

country + purpose 조회

없는 Program 처리

관련 Requirement 반환
```

---

## SupportProgram Service Test

```text
지원제도 조회

issuer_country Filter

destination_country Filter

target_nationality Filter

Program 연결 관계 조회
```

---

## Evidence Service Test

```text
Evidence 조회

잘못된 Evidence ID

URL / Agency Metadata 유지

날짜 Metadata 유지
```

---

## LLM Service Test

```text
정상 Response

Timeout

Provider Error

잘못된 API Key

Response Parsing
```

실제 외부 API 호출 대신 Mock을 활용할 수 있습니다.

---

## Embedding Service Test

```text
Query Embedding

Document Batch Embedding

빈 문자열 처리

Timeout

Embedding Dimension
```

---

## Session Service Test

```text
Session 생성

Profile 저장

Profile 조회

Profile 갱신

없는 Session 처리
```

---

# Integration Test 예시

```text
진출 경로 탐색·추천 에이전트
   ↓
Program Service
   ↓
PostgreSQL
```

또는:

```text
공식 정보 안내 에이전트
   ↓
Retrieval
   ↓
Embedding Service
   ↓
pgvector
```

또는:

```text
사용자 이해 에이전트
   ↓
Session Service
   ↓
UserProfile
```

---

# 구현 원칙

- Agent에서 외부 SDK Client를 반복 생성하지 않음
- Database 접근을 공통 Service로 관리
- Program과 SupportProgram Service를 구분
- Retrieval 전략과 Database 연결 책임을 구분
- Rule Evaluator를 Service Layer에 섞지 않음
- 공통 Model을 사용하여 반환값 구조를 유지
- API Key를 코드에 직접 작성하지 않음
- Timeout과 Error Handling을 고려
- 민감한 정보를 Log에 남기지 않음
- 국가별 Service를 불필요하게 별도로 만들지 않음
- 변경 가능한 정책 Data를 Python 코드에 Hard Coding하지 않음
- Service는 데이터 접근과 외부 연결 책임에 집중
- 과도한 추상화는 초기 MVP에서 피함

---

# 개발 순서

현재 예상 개발 순서는 다음과 같습니다.

```text
1. Database Service 구현

2. PostgreSQL 연결 테스트

3. Program Service 구현

4. SupportProgram Service 구현

5. Evidence Service 구현

6. LLM Service 구현

7. Embedding Service 구현

8. Agent / Retrieval 연결

9. Error Handling 추가

10. Timeout / Retry 정책 추가

11. 필요 시 Session Service 구현

12. Unit Test

13. Integration Test

14. 필요 시 Repository Layer 분리
```

---

# 현재 상태

현재는 Service Layer의 책임과 구조를 정의한 단계입니다.

초기 구현에서는 우선 다음 기능을 중심으로 시작합니다.

```text
Database 연결

Program 조회

SupportProgram 조회

LLM 호출

Embedding 호출
```

이후 Agent와 데이터베이스 구조가 구체화되면서:

```text
Evidence Service

Session Service

공통 Error Handling

Connection Pool

Retry / Timeout
```

등을 단계적으로 추가합니다.

Service Layer는 Global-In의 Agent가
외부 시스템 구현 세부사항에 과도하게 의존하지 않도록 만드는
공통 연결 계층으로 사용합니다.

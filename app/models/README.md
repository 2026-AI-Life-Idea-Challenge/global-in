# app/models

Global-In에서 사용하는 공통 데이터 구조와 Schema를 정의하는 디렉터리입니다.

API, Agent, Rule Evaluator, Retrieval, Service Layer가 서로 다른 형태의 데이터를 사용하면
모듈 간 연결 과정에서 데이터 불일치가 발생할 수 있기 때문에,
프로젝트 전체에서 사용하는 공통 데이터 구조를 `app/models/`에서 관리합니다.

주로 Pydantic Model을 사용하며,
Agent 간 공유 State와 API Request / Response 구조도 가능한 한 동일한 Model을 재사용합니다.

---

## 주요 역할

`app/models/`에서는 다음과 같은 데이터 구조를 정의합니다.

```text
UserProfile
AgentState

Program
SupportProgram

EligibilityRequirement
EligibilityResult

ApplicationAvailability
ApplicationInfo

RequiredDocument
Evidence

Checklist
Roadmap

ChatRequest
ChatResponse
```

각 Agent와 Module은 가능한 한 동일한 Schema를 사용합니다.

---

## Models가 필요한 이유

예를 들어 사용자 정보를 한 모듈에서는 다음과 같이 사용하고:

```text
age
education
career
language
```

다른 모듈에서는:

```text
user_age
degree
work_years
language_score
```

처럼 사용하면 데이터 변환이 복잡해지고 오류 가능성이 높아집니다.

따라서 Global-In에서는 공통 Model을 기준으로 데이터를 전달합니다.

```text
Frontend
   ↓
API Model
   ↓
Agent State
   ↓
Program / Rule / Retrieval
   ↓
Response Model
```

---

## 예상 파일 구조

현재 Agent 구조를 기준으로 다음과 같은 구성을 고려합니다.

```text
app/models/
├─ __init__.py
├─ user.py
├─ state.py
├─ program.py
├─ support_program.py
├─ eligibility.py
├─ application.py
├─ document.py
├─ evidence.py
├─ checklist.py
├─ roadmap.py
├─ chat.py
└─ README.md
```

실제 구현 과정에서 파일 구성은 변경될 수 있습니다.

---

# User 관련 Model

## `user.py`

사용자 Profile에 필요한 Schema를 정의합니다.

사용자 이해 에이전트가 사용자 발화에서 정보를 추출하고,
기존 Profile을 갱신할 때 사용합니다.

---

## UserProfile

예상 정보:

```text
user_id
age
nationality
current_residence
education
major
career_years
career_field
language
budget
preferred_country
preferred_purpose
preferred_departure_date

student_status
employment_status
previous_participation
previous_benefit_history
```

지원제도를 검토할 경우
일반 비자 검토보다 더 많은 정보가 필요할 수 있습니다.

예:

```text
현재 재학 여부
현재 취업 상태
기존 지원사업 참여 여부
기존 수혜 여부
현재 거주 지역
```

---

## UserProfile 예시

```python
from pydantic import BaseModel


class UserProfile(BaseModel):
    age: int | None = None
    nationality: str | None = None
    current_residence: str | None = None

    education: str | None = None
    major: str | None = None

    career_years: float | None = None
    career_field: str | None = None

    preferred_country: str | None = None
    preferred_purpose: str | None = None

    student_status: str | None = None
    employment_status: str | None = None
```

실제 Field는 DB 및 Agent 설계에 맞춰 조정합니다.

---

# Agent State

## `state.py`

LangGraph에서 5개 Agent가 공유하는 공통 State 구조를 정의합니다.

Agent가 서로 직접 내부 구현에 의존하지 않고,
State를 통해 필요한 데이터를 전달할 수 있도록 합니다.

예상 State:

```python
{
    "user_query": "",
    "user_profile": {},
    "intent": "",

    "missing_fields": [],

    "candidate_countries": [],
    "candidate_programs": [],
    "candidate_support_programs": [],

    "selected_program": None,
    "selected_support_programs": [],

    "eligibility_results": [],

    "retrieved_documents": [],
    "validated_evidence": [],

    "checklist": [],
    "roadmap": [],

    "final_answer": ""
}
```

---

## Agent별 주요 State 사용

### 사용자 이해 에이전트

```text
user_query
user_profile
intent
missing_fields
```

### 진출 경로 탐색·추천 에이전트

```text
candidate_countries
candidate_programs
candidate_support_programs
selected_program
```

### 자격 검토 에이전트

```text
user_profile
selected_program
selected_support_programs
eligibility_results
```

### 공식 정보 안내 에이전트

```text
retrieved_documents
validated_evidence
```

### 준비 계획 에이전트

```text
checklist
roadmap
```

---

# Program 관련 Model

## `program.py`

해외 진출에 직접 관련된 실제 비자·체류·교환 프로그램 정보를 정의합니다.

Global-In의 상위 진출 경로:

```text
워킹홀리데이 / 교환
유학
취업
```

아래에 실제 Program을 연결합니다.

예:

```text
국가
   ↓
상위 진출 경로
   ↓
실제 Program
```

---

## Program 기본 정보

예상 Field:

```text
program_id

country
destination_country
purpose

official_program_name
display_name
description

program_type

eligibility
application
documents
stay
preparation

evidence
```

---

## Program 예시 구조

```text
Program

program_id
country
purpose

official_program_name
display_name
description

eligibility
 ├─ age
 ├─ nationality
 ├─ residence
 ├─ education
 ├─ career
 ├─ language
 ├─ financial
 ├─ other
 ├─ mandatory_conditions
 ├─ conditional_conditions
 ├─ exceptions
 └─ judgeability

application
 ├─ agency
 ├─ method
 ├─ timing
 ├─ availability
 └─ fee

documents
 ├─ mandatory
 └─ conditional

stay
 ├─ duration
 ├─ work_allowed
 ├─ work_restrictions
 ├─ study_allowed
 └─ extension

preparation
 ├─ pre_application
 ├─ application
 ├─ post_approval
 ├─ pre_departure
 └─ post_entry

evidence
 └─ source references
```

---

# Support Program 관련 Model

## `support_program.py`

한국 또는 목적지 국가에서 제공하는
해외 진출 지원제도 정보를 정의합니다.

Program과 SupportProgram은 같은 개념으로 취급하지 않습니다.

---

## Program과 SupportProgram 차이

### Program

사용자가 실제 해외 진출을 위해 검토하는 비자·체류·교환 등의 경로입니다.

예:

```text
취업 비자
학생 비자
워킹홀리데이
교환 프로그램
체류 자격
```

### SupportProgram

해외 진출 과정에서 함께 활용할 수 있는 지원제도입니다.

예:

```text
해외취업 지원금
해외 연수
취업 준비 교육
장학 지원
외국인 정착 지원
현지 취업 지원
```

---

## SupportProgram 예상 Field

```text
support_program_id

official_name
display_name
description

issuer_country
destination_country

official_agency

target_nationality
target_region

purpose
support_type

eligibility

application
support_detail

related_programs

evidence
```

---

## 하나의 지원제도와 여러 진출 경로

하나의 지원제도가 여러 Program 또는 상위 진출 경로와 연결될 수 있습니다.

예:

```text
SupportProgram A
   ├─ Germany Employment
   ├─ Canada Employment
   └─ Japan Employment
```

따라서 Program과 SupportProgram은
1:1 관계로 가정하지 않습니다.

실제 DB에서는 연결 Table을 사용할 수 있습니다.

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

---

# Eligibility 관련 Model

## `eligibility.py`

비자·Program 및 SupportProgram의 공식 자격조건과
자격 검토 결과를 표현합니다.

---

## EligibilityRequirement

구조화 가능한 공식 조건을 표현합니다.

예:

```json
{
  "field": "age",
  "operator": "<=",
  "value": 30,
  "required": true
}
```

또는:

```json
{
  "field": "career_years",
  "operator": ">=",
  "value": 2,
  "required": true
}
```

---

## 예상 Condition Field

```text
requirement_id

target_type
target_id

field
operator
value

required

judgeability

description
evidence_id
```

---

## `target_type`

어떤 대상의 조건인지 구분합니다.

예:

```text
PROGRAM
SUPPORT_PROGRAM
```

이를 통해 비자 자격과 지원제도 자격을 별도로 관리합니다.

---

## `judgeability`

Rule Evaluator로 자동 판정할 수 있는지 구분합니다.

예:

```text
rule_based
manual_check
conditional
```

예외 규정이나 기관 판단이 필요한 조건은
Rule Evaluator에서 강제로 판정하지 않습니다.

---

## EligibilityResult

자격 검토 에이전트가 사용하는 판정 결과를 표현합니다.

기본 상태:

```text
조건 충족
조건 미충족
추가 확인 필요
```

---

## 예상 EligibilityResult

```python
class EligibilityResult(BaseModel):
    target_type: str
    target_id: str

    status: str

    passed_conditions: list = []
    failed_conditions: list = []
    uncertain_conditions: list = []
    missing_information: list = []
```

실제 구현 시 Mutable Default 사용 방식은
Pydantic 권장 방식에 맞춰 조정합니다.

---

## EligibilityResult 예시

```json
{
  "target_type": "PROGRAM",
  "target_id": "example_program",
  "status": "추가 확인 필요",
  "passed_conditions": [
    "nationality",
    "education"
  ],
  "failed_conditions": [],
  "uncertain_conditions": [
    "age_exception"
  ],
  "missing_information": []
}
```

---

## 사용자 정보 부족과 조건 미충족 구분

다음 두 상황은 별도로 표현해야 합니다.

### Missing Information

```text
공식 조건 존재
+
사용자 정보 없음
```

예:

```text
career >= 2 years

UserProfile:
career = null
```

결과:

```text
missing_information
```

사용자 이해 에이전트에 추가 질문을 요청합니다.

---

### Failed Condition

```text
공식 조건 존재
+
사용자 정보 확인 완료
+
공식 조건 미충족
```

예:

```text
career >= 2 years

UserProfile:
career = 1 year
```

결과:

```text
조건 미충족
```

---

# 신청 가능 여부 관련 Model

## `application.py`

Program이나 SupportProgram의 신청 관련 정보를 정의합니다.

예:

```text
application_agency
application_method
application_period
application_url
fee
```

---

## ApplicationAvailability

자격 여부와 현재 접수 가능 여부를 분리하기 위한 구조입니다.

예:

```text
Eligibility
→ 사용자가 요건을 충족하는가?

ApplicationAvailability
→ 현재 실제 신청 가능한가?
```

---

## 예상 상태

```text
OPEN
CLOSED
UPCOMING
UNKNOWN
```

또는 구현 단계에서 이에 준하는 Enum을 사용할 수 있습니다.

---

## 중요한 원칙

다음은 서로 다른 상태입니다.

```text
조건 충족
≠
현재 신청 가능
```

현재 모집 여부를 확인하지 못한 경우:

```text
UNKNOWN
```

등으로 관리하고
신청 가능하다고 임의로 판단하지 않습니다.

---

# Required Document

## `document.py`

Program 및 SupportProgram의 필요 서류를 정의합니다.

예상 Field:

```text
document_id

target_type
target_id

document_name
description

required
conditional

stage

evidence_id
```

---

## 서류 구분

```text
Program 필수 서류
Program 조건부 서류

SupportProgram 필수 서류
SupportProgram 조건부 서류

공통 준비 서류
```

준비 계획 에이전트가 이 정보를 이용하여
Checklist 및 Roadmap을 구성합니다.

---

# Evidence 관련 Model

## `evidence.py`

공식 정보 안내 에이전트와 Retrieval에서 사용하는
공식 근거 구조를 정의합니다.

---

## 예상 Field

```text
evidence_id

official_agency

issuer_country
destination_country

source_title
source_url
source_type

information_topic

program_id
support_program_id

original_published_at
original_updated_at

effective_from
effective_until

verified_at

content
```

---

## 날짜 정보

다음 날짜는 서로 다른 의미를 가집니다.

### `original_published_at`

원문 최초 게시일

### `original_updated_at`

원문 수정일

### `effective_from`

제도·규정 적용 시작일

### `effective_until`

제도·규정 적용 종료일

### `verified_at`

Global-In에서 마지막으로 해당 정보를 확인한 날짜

원문에 날짜가 없는 경우
임의로 추정하지 않고 `null` 또는 미확인 상태로 유지합니다.

---

## Evidence 검증 상태

검색된 문서가 최종 Evidence로 사용 가능한지 표현하는 Model도 둘 수 있습니다.

예:

```text
relevance
country_match
program_match
target_match
source_validity
recency_check
```

Evidence 검증 로직의 실제 위치는
Agent 또는 Retrieval 구조 확정 후 결정합니다.

---

# Checklist 관련 Model

## `checklist.py`

준비 계획 에이전트가 생성하는
사용자별 준비 Checklist를 표현합니다.

예상 Field:

```text
item_id

category
title
description

target_type
target_id

stage

status

required
deadline

evidence_id
```

---

## Checklist 상태

```text
완료
준비 필요
추가 확인
```

실제 구현에서는 Enum 형태로 관리할 수 있습니다.

---

## Checklist 단계

예:

```text
준비
신청
승인 후
출국 준비
입국 후
```

Program 및 SupportProgram에 따라
사용되는 단계가 달라질 수 있습니다.

---

# Roadmap 관련 Model

## `roadmap.py`

사용자의 선택 경로와 현재 준비 상태를 기반으로
단계별 Roadmap을 표현합니다.

예:

```text
Step 1
자격 검토

Step 2
필수 조건 준비

Step 3
지원제도 신청

Step 4
Program 신청

Step 5
승인 후 준비

Step 6
출국

Step 7
입국 후 절차
```

---

## 예상 Field

```text
step_id
order

title
description

status

related_program
related_support_program

required_actions

start_date
deadline

evidence
```

확인되지 않은 일정은
LLM이 임의로 생성하지 않습니다.

---

# Chat 관련 Model

## `chat.py`

Frontend와 FastAPI 사이에서 사용하는
Request / Response Schema를 정의합니다.

---

## ChatRequest 예시

```python
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
```

필요한 경우 향후 다음 정보를 추가할 수 있습니다.

```text
user_id
conversation_id
current_profile
selected_program
```

---

## ChatResponse 예상 구조

```text
answer

intent

user_profile

recommendations

eligibility_results

support_programs

sources

checklist

roadmap

follow_up_question
```

---

## ChatResponse 예시

```json
{
  "answer": "...",
  "eligibility_results": [],
  "support_programs": [],
  "sources": [],
  "checklist": [],
  "roadmap": [],
  "follow_up_question": null
}
```

실제 Response 구조는
Agent Workflow와 Frontend 구현 과정에서 조정합니다.

---

# Agent와 Models의 관계

5개 Agent는 다음 Model을 주로 사용합니다.

```text
사용자 이해 에이전트
→ UserProfile
→ AgentState

진출 경로 탐색·추천 에이전트
→ Program
→ SupportProgram
→ AgentState

자격 검토 에이전트
→ EligibilityRequirement
→ EligibilityResult
→ UserProfile

공식 정보 안내 에이전트
→ Evidence
→ Retrieval Result

준비 계획 에이전트
→ RequiredDocument
→ Checklist
→ Roadmap
```

---

# Database와 Models의 관계

PostgreSQL의 Entity와 Python Model은
가능한 한 의미가 일치하도록 설계합니다.

예:

```text
PostgreSQL
program

        ↓

Python
Program
```

```text
PostgreSQL
support_program

        ↓

Python
SupportProgram
```

```text
PostgreSQL
eligibility_requirement

        ↓

Python
EligibilityRequirement
```

완전히 동일한 구조일 필요는 없지만,
불필요한 변환 로직이 많아지지 않도록 설계합니다.

---

# PostgreSQL과 pgvector 데이터 구분

Models에서도 구조화된 데이터와
검색용 비정형 데이터를 구분합니다.

### PostgreSQL 중심

```text
Program
SupportProgram
EligibilityRequirement
ApplicationInfo
ApplicationAvailability
RequiredDocument
Checklist 관련 기준 데이터
Evidence Metadata
```

### pgvector 중심

```text
Official Document
Document Chunk
FAQ
법령 본문
예외 규정
행정 안내
지원사업 상세 안내
```

검색 결과는 최종적으로 Evidence Model 형태로
Agent에 전달할 수 있습니다.

---

# Entity 관계 예시

현재 기획 기준 핵심 관계는 다음과 같은 형태를 고려할 수 있습니다.

```text
Program
   │
   ├─ EligibilityRequirement
   ├─ ApplicationInfo
   ├─ RequiredDocument
   └─ Evidence
   │
   │ N:M
   ↓
ProgramSupportLink
   ↑
   │
SupportProgram
   │
   ├─ EligibilityRequirement
   ├─ ApplicationInfo
   ├─ RequiredDocument
   └─ Evidence
```

실제 관계와 Cardinality는
DB ERD 설계 과정에서 확정합니다.

---

# 구현 원칙

- 프로젝트 전체에서 동일한 개념은 동일한 Field명을 사용
- API Request / Response는 Pydantic으로 검증
- Agent State에서도 가능한 한 공통 Model 재사용
- Program과 SupportProgram을 구분
- 비자 자격과 지원제도 자격을 구분
- 사용자 정보 부족과 조건 미충족을 구분
- 신청 자격과 현재 신청 가능 여부를 구분
- 구조화 가능한 조건은 Rule Evaluator가 사용 가능한 형태로 저장
- 자동 판정하기 어려운 조건은 별도 상태로 표현
- Evidence에는 Source와 날짜 Metadata를 포함
- 공식 데이터와 AI 생성 정보를 혼합하지 않음
- 특정 국가에만 적용되는 Field를 무분별하게 공통 Schema에 추가하지 않음
- 실제 데이터 수집 결과를 확인하면서 Schema를 보완

---

# 개발 순서

현재 예상 개발 순서는 다음과 같습니다.

```text
1. UserProfile Model 정의

2. AgentState 정의

3. Program Model 정의

4. SupportProgram Model 정의

5. EligibilityRequirement 정의

6. EligibilityResult 정의

7. ApplicationInfo / Availability 정의

8. RequiredDocument 정의

9. Evidence Model 정의

10. Checklist / Roadmap 정의

11. Chat Request / Response 정의

12. PostgreSQL Schema와 Mapping

13. Agent 연결

14. API 연결
```

---

# 향후 변경 가능 항목

현재 Schema는 초기 기획 기준입니다.

다음 내용은 실제 데이터 수집 및 ERD 설계 과정에서 변경될 수 있습니다.

```text
Entity 분리 방식
Field명
Program / SupportProgram 관계
Eligibility Rule 표현
Application Availability 표현
Evidence Metadata
Agent State 구조
Checklist / Roadmap 구조
Chat Response 구조
```

처음부터 모든 Field를 고정하지 않고,
실제 일본·호주·미국·독일·캐나다의 공식 데이터를 수집하면서
필요한 Field를 검증하고 확장하는 것을 원칙으로 합니다.

---

## 현재 상태

현재는 5개 Agent 구조를 기준으로
프로젝트에서 필요한 공통 데이터 Model을 설계하는 단계입니다.

다음 단계에서는 실제 데이터 수집과 DB ERD 설계를 진행하면서
Models와 PostgreSQL Schema를 함께 구체화합니다.

# app/models

Global-In에서 사용하는 공통 데이터 구조와 Schema를 정의하는 디렉터리입니다.

API, Agent, Rule Evaluator, Retrieval, Service Layer가 서로 다른 형태의 데이터를 사용하면
연결 과정에서 오류가 발생하기 쉽기 때문에,
공통 데이터 형식을 `app/models/`에서 관리합니다.

주로 Pydantic Model을 사용합니다.

---

## 주요 역할

`app/models/`는 다음 데이터를 정의합니다.

```text
User Profile
Program
Eligibility Result
Evidence
Checklist
Roadmap
Chat Request
Chat Response
```
**각 모듈은 이 Schema를 공통으로 사용합니다.**

---

## 왜 별도 Model Layer가 필요한가

예를 들어 사용자 정보를 Agent에서는 다음처럼 사용하고,
```
age
education
career
language
```
API에서는 다른이름으로 사용하면 
```
user_age
degree
work_years
language_score
```
모듈 간 데이터 전달 과정에서 문제가 생길 수 있습니다.

따라서 공통 Model을 정의하여 모든 기능이 동일한 데이터 구조를 사용하도록 합니다.

---

## 예상 구조

향후 다음과 같은 파일 구성을 사용할 수 있습니다.
```
app/models/
├─ __init__.py
├─ user.py
├─ program.py
├─ eligibility.py
├─ evidence.py
├─ checklist.py
├─ roadmap.py
├─ chat.py
└─ README.md
```
실제 구현 과정에서 파일 구조는 조정될 수 있습니다.


## user.py

사용자 Profile과 관련된 Schema를 정의합니다.

예상 정보:
```
user_id
age
nationality
education
major
career
language
budget
preferred_country
preferred_purpose
```
예시:
```
from pydantic import BaseModel


class UserProfile(BaseModel):
    age: int | None = None
    nationality: str | None = None
    education: str | None = None
    major: str | None = None
    career_years: float | None = None
    preferred_country: str | None = None
    preferred_purpose: str | None = None
```
사용자가 모든 정보를 처음부터 제공하지 않을 수 있기 때문에 많은 필드는 초기에 `None`을 허용할 수 있습니다.

Agent는 대화를 진행하면서 Profile을 갱신합니다.


### program.py

국가별 실제 비자 프로그램 정보를 표현한느 Schema를 정의합니다.

Global-In에서는 15개의 상위 진출 경로 아래에 실제 프로그램이 연결되는 구조를 사용합니다.

기본 정보 예시:
```
program_id
country
purpose
official_program_name
display_name
description
```

---

## Program 공통 Schema

프로그램 데이터는 가능한 한 다음 구조로 통일합니다.
```
program_id

country
purpose

official_program_name
display_name
description

eligibility
 ├ age
 ├ nationality
 ├ education
 ├ career
 ├ language
 ├ financial
 ├ other
 ├ mandatory_conditions
 ├ conditional_conditions
 ├ exceptions
 └ judgeability

application
 ├ agency
 ├ method
 ├ timing
 └ fee

documents
 ├ mandatory
 └ conditional

stay
 ├ duration
 ├ work_allowed
 ├ work_restrictions
 └ extension

preparation
 ├ pre_application
 ├ application
 ├ post_approval
 ├ pre_departure
 └ post_entry

evidence
 ├ official_agency
 ├ original_title
 ├ source_url
 ├ original_updated_at
 └ verified_at
```
국가마다 공식 정보의 형태는 다르지만, Global-In 내부에서는 가능한 한 동일한 Schema로 변환하여 사용합니다.

---

## Eligibility 조건 구조

자격 조건은 단순 문자열만 저장하는 것이 아니라 가능한 경우 `Rule Evaluator`가 사용할 수 있도록 구조화합니다.

예:
```
{
  "field": "age",
  "operator": "<=",
  "value": 30,
  "required": true
}
```
이런 형태로 저장하면 `Rule Evaluator`가 사용자의 나이와 프로그램 조건을 직접 비교할 수 있습니다.

반면 **자동 판정이 어려운 조건은 별도로 표시**합니다.

예:
```
judgeability = manual_check
```
또는 **이에 준하는 상태를 사용합니다.**


### eligibility.py

Rule Evaluator의 결과를 표현합니다.

기본 상태:
```
조건 충족
추가 확인 필요
조건 미충족
```
예상 구조:
```
class EligibilityResult(BaseModel):
    status: str
    passed_conditions: list = []
    failed_conditions: list = []
    uncertain_conditions: list = []
```
실제 필드명은 구현 과정에서 조정할 수 있습니다.


## Eligibility Result 예시
```
{
  "status": "추가 확인 필요",
  "passed_conditions": [
    "nationality"
  ],
  "failed_conditions": [],
  "uncertain_conditions": [
    "age_exception"
  ]
}
```
최종 LLM 응답은 이 결과를 임의로 변경하지 않고, 사용자에게 이해하기 쉬운 형태로 설명합니다.


### evidence.py

공식 근거 정보를 표현합니다.

예상 필드:
```
source_id
official_agency
title
url
country
program_id
document_type
original_updated_at
verified_at
content
```
RAG의 검색 결과와 최종 응답의 출처 정보를 연결하는 데 사용합니다.


## Evidence 관련 날짜

공식 자료는 다음 날짜를 구분하여 관리합니다.
```
original_updated_at
→ 원문 자체의 게시 또는 수정 날짜

verified_at
→ Global-In 시스템이 해당 정보를 마지막으로 확인한 날짜
```
두 값을 분리하여 정보 최신성을 관리합니다.


### checklist.py

사용자의 해외 진출 준비 Checklist를 표현합니다.

예:
```
항목
설명
상태
필수 여부
관련 단계
출처
```
상태 예시:
```
완료
준비 필요
주가 확인
```


### roadmap.py

사용자에게 제공하는 개인화 Roadmap 구조를 정의합니다.

예:
```
Step 1. 지원 가능 여부 확인
Step 2. 언어 요건 준비
Step 3. 필요 서류 준비
Step 4. 신청
Step 5. 승인 후 준비
Step 6. 출국 및 입국
```
프로그램의 `preparation` 데이터와 사용자의 현재 상태를 바탕으로 생성합니다.


### chat.py

Frontend와 Backend 사이의 `Chat Request` / `Response Schema`를 정의합니다.

예상 Request:
```
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
```
예상 Response:
```
class ChatResponse(BaseModel):
    answer: str
    eligibility: EligibilityResult | None = None
    sources: list = []
    checklist: list = []
    roadmap: list = []
```
실제 응답 형식은 Agent 구조 확정 후 조정합니다.

---

## Models와 API의 관계

FastAPI는 Request와 Response를 검증할 때 `app/models/`의 Pydantic Model을 사용합니다.
```
Frontend
   ↓
ChatRequest
   ↓
FastAPI
   ↓
Agent
   ↓
ChatResponse
   ↓
Frontend
```


## Models와 Agent의 관계

Agent State에서 사용하는 구조화된 데이터도 가능한 경우 Models를 재사용합니다.

예:
```
UserProfile
Program
EligibilityResult
Evidence
```
이를 통해 Agent 내부에서 임의 Dictionary 구조가 계속 생기는 것을 방지합니다.


## Models와 Database의 관계

PostgreSQL Schema와 Python Model은 가능한 한 의미가 일치하도록 설계합니다.
```
PostgreSQL
program_id
country
purpose

        ↓

Python
Program
```
완전히 동일한 구조일 필요는 없지만, 변환 로직이 복잡해지지 않도록 설계합니다.

---

## 구현 원칙
- 공통 데이터 구조는 Models에서 관리
- 동일한 개념에 서로 다른 필드명을 사용하지 않음
- API Request / Response는 Pydantic으로 검증
- 필수값과 선택값을 명확히 구분
- 국가별 차이가 있어도 가능한 한 공통 Schema 유지
- 구조화 가능한 Eligibility 조건은 Rule Evaluator가 사용할 수 있게 저장
- 자동 판단할 수 없는 조건은 별도로 표시
- Evidence에는 출처와 날짜 Metadata를 함께 저장
- LLM 출력만을 데이터 구조의 기준으로 사용하지 않음

---

## 개발 순서
```
1. UserProfile Model
2. Program Model
3. Eligibility Condition Model
4. Eligibility Result Model
5. Evidence Model
6. Chat Request / Response Model
7. Checklist / Roadmap Model
8. API / Agent 연결
```

---

## 향후 변경 가능 항목

Agent 구조와 DB Schema가 확정되면 다음 항목은 변경될 수 있습니다.
```
Model 분리 방식
필드명
Eligibility Condition 표현 방식
Chat Response 구조
Agent State와 Model의 연결 방식
```
공통 데이터 의미 자체는 최대한 유지하고, 구현 구조만 조정하는 것을 원칙으로 합니다.

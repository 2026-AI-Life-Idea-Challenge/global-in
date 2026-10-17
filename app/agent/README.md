# app/agent

Global-In의 LangGraph 기반 Agent Orchestration을 구현하는 디렉터리입니다.

Global-In은 하나의 거대한 Agent가 모든 기능을 처리하는 구조가 아니라,
역할이 명확하게 분리된 여러 Agent와 공통 Module을 LangGraph가 연결하고 조정하는 구조를 사용합니다.

LangGraph는 전체 Workflow와 상태 전이를 관리하고,
각 Agent는 자신의 담당 업무에 집중합니다.

---

## 전체 구조

Global-In의 Agent 구조는 다음과 같습니다.

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
  │
  ├─ 진출 경로 탐색·추천 에이전트
  │
  ├─ 자격 검토 에이전트
  │
  ├─ 공식 정보 안내 에이전트
  │
  └─ 준비 계획 에이전트
  │
  └─ 공통 Module / Service
       ├─ Program Resolver
       ├─ Rule Evaluator
       ├─ Retrieval
       ├─ Evidence Validation
       ├─ PostgreSQL
       ├─ pgvector
       └─ LLM Service
```

LangGraph는 각 Agent의 실행 순서와 분기를 관리합니다.

질문에 따라 모든 Agent를 항상 호출하는 것은 아니며,
현재 요청에 필요한 Agent만 선택적으로 호출할 수 있도록 구성합니다.

---

## Agent 구성

Global-In에서는 다음 5개 Agent를 사용합니다.

```text
1. 사용자 이해 에이전트
2. 진출 경로 탐색·추천 에이전트
3. 자격 검토 에이전트
4. 공식 정보 안내 에이전트
5. 준비 계획 에이전트
```

각 Agent는 하나의 주요 책임을 담당합니다.

---

## 1. 사용자 이해 에이전트

### 목적

사용자의 목적과 현재 상황을 파악하고,
진출 경로·비자·지원제도를 검토하기 위해 필요한 사용자 정보를 정리합니다.

필요한 정보가 부족한 경우 추가 질문을 생성합니다.

### 주요 역할

```text
온보딩
의도 분류
사용자 Profile 생성
사용자 Profile 갱신
Missing Information 탐지
추가 질문 생성
```

### 확인할 사용자 정보

현재 질문에 따라 필요한 정보만 확인합니다.

예:

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
예산
```

지원제도를 검토할 경우 추가로 다음 정보를 확인할 수 있습니다.

```text
재학 여부
현재 취업 상태
기존 참여 이력
기존 수혜 이력
현재 거주 지역
중복 수혜 여부
```

### 중요한 구분

다음 두 상황을 반드시 구분합니다.

#### 사용자 정보 부족

```text
공식 조건은 존재하지만
사용자 정보가 아직 없음
```

예:

```text
경력 2년 이상 필요
사용자 경력 정보 없음
```

이 경우:

```text
추가 질문 필요
```

로 처리합니다.

#### 공식 조건 미충족

```text
사용자 정보는 확인되었지만
공식 조건을 충족하지 못함
```

예:

```text
경력 2년 이상 필요
사용자 경력 1년
```

이 경우 자격 검토 에이전트에서:

```text
조건 미충족
```

으로 판정합니다.

### 결과물

사용자 이해 에이전트는 다음 정보를 반환합니다.

```text
User Profile
현재 Intent
Missing Information
추가 확인이 필요한 사용자 정보
```

### 예시

사용자:

```text
독일로 취업하고 싶어요.
```

응답 흐름:

```text
취업이 목적이시군요.
현재 전공과 관련 경력을 알려주세요.
```

지원제도 후보가 정해진 이후에는
해당 제도 검토에 필요한 정보만 추가로 질문합니다.

---

## 2. 진출 경로 탐색·추천 에이전트

### 목적

사용자 조건과 목적에 맞는 국가 및 실제 비자·프로그램 후보를 찾고,
함께 활용할 수 있는 국내외 지원제도를 탐색하고 비교합니다.

### 주요 역할

```text
국가 추천
진출 유형 추천
실제 프로그램 탐색
Program Resolver 사용
경로 비교
추천 이유 생성
관련 지원제도 탐색
```

### Program Resolver

사용자가 선택한 상위 진출 경로를
실제 비자·프로그램과 연결합니다.

예:

```text
Germany
+
Employment
   ↓
실제 취업 관련 Program 후보
```

Program Resolver는 주로 PostgreSQL의 구조화된 데이터를 사용합니다.

### 지원제도 탐색

진출 경로와 함께 활용할 수 있는 지원제도도 찾습니다.

예:

```text
한국 정부 해외취업 지원
해외 연수 지원
목적지 국가 외국인 취업 지원
유학생 지원
정착 지원
```

지원제도는 실제 Program과 별도로 관리하지만,
필요한 경우 서로 연결합니다.

### 검토 기준

지원제도를 추천할 때 다음 항목을 확인합니다.

```text
지원 대상
지원 내용
신청 시기
진출 경로와의 관련성
한국인 적용 가능 여부
현재 확인 가능한 모집 상태
```

외국인을 대상으로 하는 제도라도
한국인에게 실제 적용 가능한지 확인해야 합니다.

불명확한 경우:

```text
추가 확인 필요
```

상태로 유지합니다.

### 자격 검토 결과 활용

추천 Agent가 자격을 직접 최종 판정하지는 않습니다.

자격 검토 에이전트의 결과를 받아
추천 결과에 반영합니다.

예:

```text
Program A
→ 자격 조건 충족

Program B
→ 경력 조건 미충족

Program C
→ 예외 조건 추가 확인 필요
```

이 결과를 바탕으로 추천 우선순위를 조정할 수 있습니다.

### 결과물

```text
후보 국가
후보 진출 경로
실제 Program 후보
연결 가능한 Support Program
후보별 비교 결과
추천 이유
추가 확인 사항
```

---

## 3. 자격 검토 에이전트

### 목적

후보 비자·프로그램과 각 지원제도의 공식 자격 요건을
사용자 조건과 비교합니다.

실제 조건 비교는 Python 기반 Rule Evaluator를 사용하고,
Agent는 결과를 조정하고 설명하는 역할을 담당합니다.

### 주요 역할

```text
비자 자격 검토
지원제도 자격 검토
Rule Evaluator 호출
부족 조건 정리
예외 조건 처리
추가 확인 항목 정리
```

### 비자와 지원제도 자격 분리

다음 두 자격은 서로 별도로 평가합니다.

```text
비자 / 체류 Program Eligibility

Support Program Eligibility
```

예:

```text
취업 비자
→ 조건 충족

한국 지원제도 A
→ 추가 확인 필요

현지 지원제도 B
→ 조건 미충족
```

하나의 자격 결과로 통합하지 않습니다.

### 주요 검토 조건

```text
국적
연령
거주지
학력
전공
경력
언어
재정
재학 여부
취업 상태
기존 참여 이력
기존 수혜 이력
중복 수혜 제한
```

프로그램마다 필요한 조건만 사용합니다.

### Rule Evaluator

구조화 가능한 공식 조건은
Python Rule Evaluator가 비교합니다.

예:

```text
공식 조건:
career >= 2 years

사용자:
career = 3 years

결과:
조건 충족
```

LLM이 이 결과를 임의로 변경하지 않습니다.

### 기본 판정 상태

```text
조건 충족
조건 미충족
추가 확인 필요
```

### `추가 확인 필요` 처리

다음 상황은 자동으로 확정하지 않습니다.

```text
예외 규정 존재
공식 근거 충돌
사용자 정보 부족
기관 판단 필요
구조화하기 어려운 조건
한국인 적용 여부 불명확
현재 적용 상태 불명확
```

이 경우:

```text
추가 확인 필요
```

상태로 처리하고,
추가로 확인해야 할 기관 또는 항목을 안내합니다.

### 신청 자격과 실제 승인 결과 구분

다음은 같은 의미가 아닙니다.

```text
공개된 자격 요건 충족
≠
비자 발급 확정
```

또한:

```text
지원제도 신청 자격 충족
≠
지원 대상 최종 선정
```

Global-In은 공식적으로 공개된 조건을 기준으로 검토하며,
최종 승인 결정은 관할 기관이 수행합니다.

### 현재 신청 가능 여부와 자격 구분

다음 정보도 별도로 관리합니다.

```text
Eligibility
→ 사용자가 자격 요건을 충족하는가

Application Availability
→ 현재 실제 신청 가능한 기간인가
```

현재 접수 여부를 확인하지 못한 경우
신청 가능하다고 단정하지 않습니다.

### 결과물

```text
비자별 Eligibility Result
지원제도별 Eligibility Result
조건별 충족 상태
부족 조건
추가 확인 항목
필요 시 추가 질문
관련 공식 근거
```

---

## 4. 공식 정보 안내 에이전트

### 목적

질문에 필요한 국내외 지원제도와
비자·법률 관련 공식 문서를 검색하고,
사용자에게 적용되는 내용을 한국어로 설명합니다.

### 주요 역할

```text
RAG 검색
공식 정보 설명
비자 / 체류 / 근로 / 학업 규정 안내
지원제도 내용 설명
신청 절차 설명
비용 안내
출처 표시
Evidence 공유
```

### 검색 대상

```text
한국 정부 해외 진출 지원제도
목적지 국가 외국인 지원제도
이민기관 공식 안내
대사관 / 영사관 안내
공식 법령
행정 안내
교육기관 공식 안내
공식 FAQ
예외 규정
```

### 검색 기준

검색 시 가능한 한 다음 Metadata를 사용합니다.

```text
country
destination_country
purpose
program_id
support_program_id
target_nationality
source_type
information_topic
```

먼저 범위를 좁힌 뒤
pgvector 기반 Retrieval을 수행합니다.

### 정보 구분

다음 정보를 서로 구분하여 설명합니다.

```text
한국 측 해외 진출 지원제도

목적지 국가의 외국인 지원제도

비자 / 입국 / 체류 / 근로 / 학업 규정
```

사용자가 각 정보의 성격을 혼동하지 않도록 합니다.

### 공식 용어 표시

중요한 제도명이나 법률 용어는
필요한 경우 원문 명칭을 함께 표시합니다.

예:

```text
한국어 설명
+
Official Program Name
```

### Evidence

다음 정보를 함께 제공합니다.

```text
공식 기관명
원문 제목
원문 URL
원문 게시 / 수정일
시행 / 적용 기간
Global-In 확인일
```

날짜가 공식 문서에 없는 경우 임의로 추정하지 않습니다.

### Evidence 검증

검색된 자료가 바로 최종 Evidence가 되는 것은 아닙니다.

다음 항목을 확인합니다.

```text
질문 관련성
국가 일치
Program 일치
지원제도 일치
적용 대상 일치
공식 출처 여부
적용 시점
확인 시점
```

근거가 충돌하거나 부족한 경우:

```text
추가 확인 필요
```

로 처리합니다.

### 공식 정보와 AI 해석 구분

최종 설명에서는 다음 두 내용을 구분합니다.

```text
공식 규정 / 공식 지원 내용

AI의 설명 / 추천 / 준비 전략
```

AI의 제안을 공식 규정처럼 표현하지 않습니다.

### 결과물

```text
공식 근거 기반 한국어 설명
공식 기관명
원문 제목
원문 URL
확인일
적용 시점
추가 확인 사항
```

검색된 Evidence는 다른 Agent와 공유할 수 있습니다.

---

## 5. 준비 계획 에이전트

### 목적

선택한 진출 경로에 맞춰
비자 준비와 국내외 지원제도 신청을 하나의 실행 계획으로 구성합니다.

### 주요 역할

```text
필요 서류 정리
Checklist 생성
단계별 Guide
Personalized Roadmap
신청 순서 구성
진행 상태 관리
다음 행동 제안
```

### 준비 단계

기본적으로 다음 단계로 구성할 수 있습니다.

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

### 비자와 지원제도 준비 연결

비자와 지원제도 신청은 별도로 구분하되
하나의 일정 안에서 연결합니다.

예:

```text
지원제도 신청
   ↓
필요 교육 / 지원금 확인
   ↓
비자 서류 준비
   ↓
비자 신청
   ↓
출국 준비
```

### 서류 구분

```text
비자 필수 서류
비자 조건부 서류

지원제도 필수 서류
지원제도 조건부 서류

공통 준비 서류
```

중복 준비할 수 있는 서류는 함께 정리할 수 있습니다.

### 공식 일정 반영

공식적으로 확인된 정보가 있을 경우 다음을 반영합니다.

```text
신청 기간
선행 조건
접수 마감
프로그램 시작 시점
입국 후 의무
```

반면 확인되지 않은 처리 기간이나 마감일은
임의로 생성하지 않습니다.

### Checklist 상태

```text
완료
준비 필요
추가 확인
```

사용자 정보나 자격 검토 결과가 변경되면
Checklist와 Roadmap도 갱신합니다.

### 결과물

```text
비자별 준비 항목
지원제도별 준비 항목
통합 Checklist
단계별 일정
현재 진행 상태
다음 행동
추가 확인 사항
```

---

## 공통 정보 관리 및 근거 검증

다음 기능은 별도의 Agent로 추가하지 않고
5개 Agent가 공동으로 사용하는 Module과 데이터 계층으로 구성합니다.

---

## 정보 구분

다음 데이터를 서로 구분하여 저장합니다.

```text
Program
→ 비자 / 체류 / 교환 등 해외 진출 Program

Support Program
→ 지원금 / 장학 / 연수 / 정착 등 지원제도
```

하나의 Support Program이 여러 Program 또는 진출 경로와 연결될 수 있습니다.

---

## 국가 관련 정보

다음 국가 정보를 별도로 관리합니다.

```text
issuer_country
→ 정보를 발행하거나 제도를 운영하는 국가

destination_country
→ 사용자가 진출하려는 국가

target_nationality
→ 적용 대상 국적

residence_requirement
→ 신청자의 거주 조건
```

---

## 정보 주제

예:

```text
employment
study
working_holiday
exchange
training
support
scholarship
visa
residence
work
education
settlement
```

---

## 원문 유형

예:

```text
law
administrative_guidance
program_notice
official_guide
faq
embassy_notice
```

법령과 일반 안내 문서의 성격을 구분합니다.

---

## 공통 구조화 데이터

예상 공통 저장 정보:

```text
program_id
support_program_id

official_name
display_name

issuer_country
destination_country

target_nationality
target_region

purpose
information_topic

eligibility

application_agency
application_method
application_period

required_documents

fee
support_detail

related_program
related_support_program
```

실제 Field는 데이터 수집 과정에서 조정합니다.

---

## Evidence Metadata

다음 정보를 공식 근거와 함께 저장합니다.

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

원문에 날짜가 없는 경우:

```text
미확인 / null
```

로 유지합니다.

---

## PostgreSQL과 pgvector 역할

### PostgreSQL

구조화된 데이터를 저장합니다.

```text
Program
Support Program
Eligibility Requirement
Application Information
Required Document
Fee
Support Detail
Relationship
Evidence Metadata
```

### pgvector

공식 문서 및 비정형 텍스트 검색에 사용합니다.

```text
법령
FAQ
예외 규정
행정 안내
지원사업 상세 설명
공식 Guide
```

---

## 검색 및 검증 원칙

검색 시 다음 기준으로 범위를 좁힙니다.

```text
국가
목적
Program
Support Program
적용 대상
정보 주제
```

비자 요건은 해당 비자의 관할 기관 자료를 우선 사용합니다.

지원제도 요건은 해당 제도 운영기관의 자료를 우선 사용합니다.

---

## 근거 충돌

공식 근거가 서로 충돌할 경우:

```text
적용 대상
관할
적용 시점
원문
```

을 다시 비교합니다.

충돌이 해소되지 않는 경우:

```text
추가 확인 필요
```

상태로 처리합니다.

---

## LangGraph Orchestration

LangGraph는 5개 Agent의 실행 순서와 분기를 관리합니다.

기본 흐름 예시는 다음과 같습니다.

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

하지만 모든 질문이 이 전체 흐름을 사용하는 것은 아닙니다.

예:

```text
독일 취업 비자의 근로 조건만 알려줘.
```

이런 질문은 필요한 공식 정보 안내 기능만 중심적으로 실행할 수 있습니다.

---

## Agent 간 공유 State

Agent들은 공통 State를 통해 필요한 정보를 공유합니다.

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

    "eligibility_results": [],

    "retrieved_documents": [],
    "validated_evidence": [],

    "checklist": [],
    "roadmap": [],

    "final_answer": ""
}
```

실제 구조는 `app/models/`와 LangGraph 구현 과정에서 조정합니다.

---

## 예상 파일 구조

현재 Agent 설계를 기준으로 다음과 같은 구조를 고려할 수 있습니다.

```text
app/agent/
├─ __init__.py
├─ state.py
├─ graph.py
├─ router.py
│
├─ user_understanding.py
├─ route_recommendation.py
├─ eligibility_review.py
├─ official_information.py
├─ preparation_planning.py
│
└─ README.md
```

실제 구조는 구현 과정에서 조정될 수 있습니다.

---

### `state.py`

Agent 간 공유 State를 정의합니다.

예:

```text
User Profile
Intent
Missing Information
Candidate Programs
Candidate Support Programs
Eligibility Results
Evidence
Checklist
Roadmap
```

---

### `graph.py`

LangGraph 전체 Workflow를 구성합니다.

담당:

```text
Agent Node 등록
Edge 연결
Conditional Routing
시작 지점
종료 조건
Loop 구성
```

---

### `router.py`

현재 State와 사용자 질문을 기준으로
어떤 Agent를 다음에 호출할지 결정합니다.

예:

```text
정보 부족
→ 사용자 이해 에이전트

경로 추천 필요
→ 진출 경로 탐색·추천 에이전트

자격 질문
→ 자격 검토 에이전트

규정 질문
→ 공식 정보 안내 에이전트

준비 계획 요청
→ 준비 계획 에이전트
```

---

### `user_understanding.py`

사용자 이해 에이전트를 구현합니다.

담당:

```text
Profile Extraction
Intent Detection
Missing Information
Additional Question
Profile Update
```

---

### `route_recommendation.py`

진출 경로 탐색·추천 에이전트를 구현합니다.

담당:

```text
Country Recommendation
Program Resolution
Support Program Exploration
Candidate Comparison
Recommendation Reason
```

---

### `eligibility_review.py`

자격 검토 에이전트를 구현합니다.

담당:

```text
Rule Evaluator 호출
Program Eligibility 검토
Support Program Eligibility 검토
부족 조건 정리
추가 확인 항목 정리
```

---

### `official_information.py`

공식 정보 안내 에이전트를 구현합니다.

담당:

```text
RAG Retrieval
Evidence Validation
공식 정보 설명
Source 표시
불확실성 안내
```

---

### `preparation_planning.py`

준비 계획 에이전트를 구현합니다.

담당:

```text
Checklist
Required Documents
Preparation Steps
Roadmap
Progress State
Next Action
```

---

## 다른 Module과의 관계

```text
Agent Layer
   │
   ├─ Program Resolver
   ├─ Rule Evaluator
   ├─ Retrieval
   ├─ Evidence Validation
   └─ Services
          ├─ PostgreSQL
          ├─ pgvector
          ├─ OpenAI
          └─ Claude
```

Agent는 모든 기능을 직접 구현하지 않습니다.

각 Agent는 자신의 업무를 수행하기 위해
필요한 Module이나 Service를 호출합니다.

---

## 구현 원칙

- 하나의 Agent는 명확한 주요 책임을 가짐
- LangGraph는 Agent 간 Workflow를 조정
- 모든 질문에서 모든 Agent를 호출하지 않음
- 구조화 가능한 자격 판단은 Rule Evaluator 사용
- 공식 정보 검색은 Retrieval 사용
- DB 접근은 Service Layer 사용
- 공식 근거와 AI 해석을 구분
- 사용자 정보 부족과 조건 미충족을 구분
- 비자와 지원제도 자격을 구분
- 신청 자격과 현재 접수 여부를 구분
- 자동 판단하기 어려운 항목은 `추가 확인 필요` 처리
- 특정 국가에만 종속된 Agent 구조를 최소화
- Agent 간 데이터 전달은 공통 State 사용

---

## 협업 예시

사용자:

```text
독일로 취업하고 싶고, 받을 수 있는 지원도 알고 싶어.
```

처리 흐름:

```text
1. 사용자 이해 에이전트

전공
경력
언어
희망 시기
지원제도 검토에 필요한 조건 확인

        ↓

2. 진출 경로 탐색·추천 에이전트

독일 취업 Program 탐색
한국 측 지원제도 탐색
독일 측 지원제도 탐색

        ↓

3. 자격 검토 에이전트

비자 자격 검토
각 지원제도 신청 자격 검토

        ↓

4. 공식 정보 안내 에이전트

공식 규정
지원 내용
신청 방법
출처
확인일 제공

        ↓

5. 준비 계획 에이전트

비자 준비
지원제도 신청
서류
일정
Checklist
Roadmap 구성
```

정보가 부족하거나 조건이 변경되면
해당 Agent로 다시 돌아갈 수 있습니다.

---

## 초기 구현 범위

초기 MVP에서는 다음 5개 국가를 대상으로 합니다.

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

다음 정보를 연결합니다.

```text
실제 비자 / 체류 Program
한국 측 해외 진출 지원제도
목적지 국가의 지원제도
비자 / 법률 / 근로 / 학업 관련 공식 정보
```

초기 MVP에서는 다음 기능을 우선 제외합니다.

```text
실시간 채용 공고 연동
실시간 정책 자동 갱신
실제 비자 신청 자동화
```

신청 기간이나 모집 상태를 안내할 때는
확인 시점을 함께 표시합니다.

현재 접수 여부가 확인되지 않은 경우
신청 가능하다고 단정하지 않습니다.

---

## 개발 순서

현재 예상 개발 순서는 다음과 같습니다.

```text
1. 공통 Agent State 정의
2. LangGraph 기본 Orchestrator 구성
3. 사용자 이해 에이전트 구현
4. Program Resolver 연결
5. 진출 경로 탐색·추천 에이전트 구현
6. Rule Evaluator 연결
7. 자격 검토 에이전트 구현
8. Retrieval / Evidence Validation 연결
9. 공식 정보 안내 에이전트 구현
10. Checklist / Roadmap 구조 구현
11. 준비 계획 에이전트 구현
12. Agent Routing 구현
13. 전체 Workflow 통합 테스트
14. Scenario Test
```

실제 개발 우선순위에 따라 일부 단계는 병렬로 진행할 수 있습니다.

---

## 테스트 포인트

Agent 구조에서는 다음을 검증합니다.

```text
각 Agent가 담당 업무만 수행하는가
질문에 필요한 Agent만 호출되는가
사용자 정보가 부족하면 필요한 정보만 다시 질문하는가
Profile이 정상적으로 갱신되는가
Program과 Support Program이 구분되는가
비자 자격과 지원제도 자격이 구분되는가
Rule Evaluator 결과를 AI가 임의로 변경하지 않는가
올바른 공식 Evidence를 사용하는가
근거가 부족한 경우 확정적으로 답하지 않는가
현재 접수 여부와 신청 자격을 혼동하지 않는가
Checklist와 Roadmap이 검토 결과에 따라 갱신되는가
Agent 간 State가 정상적으로 전달되는가
불필요한 Agent 호출이 반복되지 않는가
무한 Loop가 발생하지 않는가
```

---

## 현재 상태

현재는 5개 Agent의 역할과 협업 구조가 정의된 상태입니다.

```text
사용자 이해 에이전트
진출 경로 탐색·추천 에이전트
자격 검토 에이전트
공식 정보 안내 에이전트
준비 계획 에이전트
```

세부 파일 구조와 Agent 내부 구현 방식은
실제 데이터 Schema, DB 구조, LangGraph 구현 과정에서 추가 조정할 수 있습니다.

# app/agent

Global-In의 LangGraph 기반 Workflow 및 Agent Orchestration을 구현하는 디렉터리입니다.

이 디렉터리는 사용자 입력부터 최종 응답 생성까지의 전체 처리 흐름을 관리합니다.
현재 구조에서는 LangGraph가 전체 흐름을 조정하고, 실제 기능은 역할별 Agent 또는 Module이 담당하도록 구성합니다.
세부 Agent 구성은 추후 확정되는 Agent 설계에 따라 변경될 수 있습니다.



---



## 주요 역할

`app/agent/`는 다음 작업의 실행 순서와 상태 전이를 관리합니다.

```
text

User Input
   ↓
User Understanding
   ↓
Intent / Missing Information
   ↓
Additional Question
   ↓
Program Resolution
   ↓
Eligibility Evaluation
   ↓
Evidence Retrieval
   ↓
Evidence Validation
   ↓
Response Generation
```
LangGraph는 각 기능을 직접 수행하기보다는 각 기능을 담당하는 Agent 또는 Module을 연결하고 실행 순서를 관리합니다.



---



## Agent State

LangGraph에서 각 단계의 데이터를 공유하기 위해 State를 사용합니다.

예상 State:
```
{
    "user_query": "",
    "user_profile": {},
    "intent": "",
    "missing_fields": [],
    "selected_country": "",
    "selected_purpose": "",
    "selected_program": {},
    "eligibility_result": {},
    "retrieved_documents": [],
    "evidence_result": {},
    "final_answer": ""
}
```
각 단계는 필요한 데이터를 State에서 읽고, 처리 결과를 다시 State에 저장합니다.



---



## 주요 처리 단계

### User Understanding

사용자 발화에서 해외 진출에 필요한 정보를 파악합니다.

예시:
```
나이
국적
학력
전공
경력
언어 능력
예산
희망 국가
희망 진출 목적
```
기존 Profile이 존재하면 새로운 사용자 정보를 반영하여 갱신합니다.



### Intent Detection

사용자가 어떤 작업을 원하는지 파악합니다.

예:
```
국가 추천
진출 경로 추천
자격 확인
필요 서류 확인
신청 절차 확인
국가 비교
자유 질문
```



### Missing Information Check

현재 사용자 정보만으로 다음 단계를 수행할 수 있는지 확인합니다.
필요한 정보가 부족한 경우 부족한 필드를 기록합니다.

예:
```
missing_fields:
- education
- career
```



### Additional Question

판단에 필요한 정보가 부족할 경우 사용자에게 추가 질문을 생성합니다.

사용자의 답변을 받은 뒤 Profile을 갱신하고 다시 Workflow를 진행합니다.



### Program Resolution

사용자의 국가, 목적, 조건에 해당하는 실제 프로그램을 탐색합니다.

Program Resolver는 PostgreSQL의 구조화된 데이터를 이용하여 검토 대상 프로그램을 결정합니다.



### Eligibility Evaluation

사용자의 조건과 프로그램의 공식 자격 요건을 비교합니다.

자격 판정 자체는 `app/rules/` 의 Rule Evaluator가 담당합니다.

기본 판정 상태:
```
조건 충족
추가 확인 필요
조건 미충족
```



### Evidence Retrieval

공식 근거가 필요한 경우 `app/retrieval/`의 검색 기능을 호출합니다.

검색 대상 예시:
```
정부 공식 문서
대사관 안내
출입국 기관 안내
FAQ
예외 규정
세부 조건
```



### Evidence Validation

검색된 자료가 현재 질문과 프로그램의 근거로 사용할 수 있는지 확인합니다.

주요 확인 항목:
```
질문 관련성
국가 일치 여부
프로그램 일치 여부
공식 출처 여부
정보 최신성
```



### Response Generation

Rule 결과와 공식 근거를 이용하여 최종 사용자 응답을 생성합니다.

최종 응답에는 필요에 따라 다음 정보를 포함합니다.
```
개인화된 설명
자격 상태
판정 이유
공식 근거
출처
Checklist
Roadmap
Follow-up Question
```



---



## 다른 모듈과의 관계
```
app/agent
   │
   ├─ app/models
   │    데이터 구조 사용
   │
   ├─ app/services
   │    DB / LLM / 외부 서비스 호출
   │
   ├─ app/rules
   │    자격 조건 판정
   │
   └─ app/retrieval
        공식 문서 검색
```
`app/agent/`는 각 기능을 직접 구현하기보다 필요한 Module 또는 Agent를 호출하여 전체 Workflow를 조정합니다.



---



## 구현 예정 파일

현재 예상 구조:
```
app/agent/
├─ __init__.py
├─ state.py
├─ graph.py
├─ nodes.py
├─ router.py
└─ README.md
```

### state.py

LangGraph에서 사용하는 State 구조를 정의합니다.



### graph.py

Node와 Edge를 연결하여 전체 Workflow를 구성합니다.



### nodes.py

각 Workflow 단계에서 실행되는 Node 로직을 정의합니다.



### router.py

현재 State를 기준으로 다음 실행 단계를 결정합니다.



---



## 구현 원칙
- LangGraph는 전체 Workflow 및 상태 전이를 관리
- 기능별 책임을 분리
- Agent와 일반 Module의 역할을 구분
- 자격 조건은 Rule Evaluator에 위임
- 공식 문서 검색은 Retrieval에 위임
- DB 및 외부 API 접근은 Service Layer를 통해 처리
- 사용자 정보가 부족한 경우 임의로 추정하지 않음
- 판단 불가능한 경우 추가 확인 필요 상태 사용
- 특정 국가에만 의존하는 하드코딩 최소화



---



## 향후 변경 가능 항목

Agent 역할과 이름은 최종 Agent 설계에 따라 변경될 수 있습니다.

변경 가능 항목:
```
Agent 구성
Agent 명칭
Node 분리 기준
Routing 구조
Agent와 Module의 경계
```
전체 LangGraph Workflow는 Agent 설계 확정 후 최종 조정합니다.

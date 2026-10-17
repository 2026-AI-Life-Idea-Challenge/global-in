# app/api

Global-In의 FastAPI 기반 Backend API를 구현하는 디렉터리입니다.

Frontend와 LangGraph Agent Workflow 사이의 진입점 역할을 담당하며,
HTTP Request를 검증하고 Agent Workflow를 호출한 뒤
구조화된 Response를 반환합니다.

API Layer는 Agent 내부 판단 로직이나 Retrieval, Rule Evaluation을 직접 구현하지 않습니다.

---

## 주요 역할

`app/api/`는 다음 역할을 담당합니다.

```text
HTTP Request 수신
Request Validation
Session / Conversation 식별
LangGraph Workflow 호출
Response Validation
Error Handling
Health Check
```

전체 흐름은 다음과 같습니다.

```text
User
  ↓
Streamlit
  ↓
FastAPI
  ↓
Request Validation
  ↓
LangGraph Orchestrator
  ↓
5개 Agent
  ↓
Response Model
  ↓
FastAPI Response
  ↓
Streamlit
```

---

## 전체 구조에서의 위치

```text
Frontend
   ↓
app/api/
   ↓
app/agent/
   ↓
LangGraph
   ↓
Agent / Module
   ↓
PostgreSQL / pgvector / LLM
```

FastAPI는 Agent Layer의 외부 Interface 역할을 합니다.

---

## 기본 원칙

API Layer에서는 다음 원칙을 따릅니다.

```text
Agent 내부 로직을 API에 작성하지 않음

Eligibility 판정을 API에서 직접 수행하지 않음

RAG Retrieval을 API에서 직접 수행하지 않음

Database Query를 Endpoint에 직접 반복 작성하지 않음

공통 Request / Response Schema는 app/models 사용

LangGraph Workflow를 하나의 서비스처럼 호출

HTTP 관련 책임과 Agent 책임을 분리
```

---

## 현재 파일

현재 기본 API Entry Point는 다음 파일입니다.

```text
app/api/main.py
```

현재 구현된 Endpoint:

```text
GET /
GET /health
```

---

## 현재 `main.py`

초기 구조는 다음과 같습니다.

```python
from fastapi import FastAPI

app = FastAPI(
    title="Global-In API",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Global-In API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }
```

실제 구현 과정에서 Router 구조로 분리할 수 있습니다.

---

## 예상 파일 구조

향후 API 규모가 커지면 다음과 같은 구조를 고려합니다.

```text
app/api/
├─ __init__.py
├─ main.py
├─ routes/
│  ├─ __init__.py
│  ├─ chat.py
│  └─ health.py
├─ dependencies.py
├─ errors.py
└─ README.md
```

실제 구현 규모에 따라 단순화하거나 변경할 수 있습니다.

---

## `main.py`

FastAPI Application을 생성하고
각 Router를 등록합니다.

예상 역할:

```text
FastAPI App 생성
Middleware 등록
Router 등록
Exception Handler 등록
Startup / Shutdown 처리
```

예:

```python
from fastapi import FastAPI

app = FastAPI(
    title="Global-In API",
    version="0.1.0"
)
```

---

## `routes/chat.py`

사용자와 Global-In Agent Workflow 사이의
주요 Chat Endpoint를 구현합니다.

예상 Endpoint:

```text
POST /chat
```

기본 흐름:

```text
ChatRequest
   ↓
Request Validation
   ↓
LangGraph Workflow 호출
   ↓
AgentState 실행
   ↓
ChatResponse 생성
   ↓
Response 반환
```

---

## `routes/health.py`

서비스 상태 확인용 Endpoint를 관리합니다.

예:

```text
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

필요한 경우 향후 다음 상태를 추가할 수 있습니다.

```text
Database 연결
LLM Service 상태
pgvector 연결
```

초기 MVP에서는 단순 Health Check부터 사용합니다.

---

## 예상 Chat API

### Request

예:

```json
{
  "message": "독일로 취업하고 싶은데 어떤 방법이 있어?",
  "session_id": "example-session"
}
```

---

### Response

예:

```json
{
  "answer": "...",
  "intent": "employment",

  "recommendations": [],

  "eligibility_results": [],

  "support_programs": [],

  "sources": [],

  "checklist": [],

  "roadmap": [],

  "follow_up_question": null
}
```

실제 Response Schema는
`app/models/`에서 정의합니다.

---

## ChatRequest

예상 기본 구조:

```python
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
```

향후 필요에 따라 다음 Field를 추가할 수 있습니다.

```text
user_id
conversation_id
selected_program_id
```

API Layer에서 UserProfile 전체를 직접 관리할지,
서버 State 또는 별도 저장소에서 관리할지는
구현 단계에서 결정합니다.

---

## ChatResponse

ChatResponse는 단순 문자열 하나보다
Frontend에서 활용할 수 있는 구조화된 결과를 반환하는 것을 목표로 합니다.

예:

```text
answer

intent

recommendations

eligibility_results

support_programs

sources

checklist

roadmap

follow_up_question
```

다만 모든 요청에서 모든 Field가 반드시 채워지는 것은 아닙니다.

예:

```text
독일 취업 비자의 근로 제한만 알려줘.
```

와 같은 질문에서는:

```text
answer
sources
```

중심의 Response가 반환될 수 있습니다.

---

## API와 5개 Agent의 관계

Global-In은 다음 5개 Agent를 사용합니다.

```text
1. 사용자 이해 에이전트
2. 진출 경로 탐색·추천 에이전트
3. 자격 검토 에이전트
4. 공식 정보 안내 에이전트
5. 준비 계획 에이전트
```

FastAPI가 이 Agent들을 각각 직접 호출하는 구조로 만들지 않습니다.

기본 구조:

```text
FastAPI
   ↓
LangGraph Orchestrator
   ↓
필요한 Agent 선택
```

즉:

```text
FastAPI
→ 사용자 이해 Agent 직접 호출
→ 추천 Agent 직접 호출
→ 자격 Agent 직접 호출
```

처럼 Endpoint가 Workflow를 직접 관리하지 않습니다.

---

## LangGraph 호출

Chat Endpoint에서는
Agent Layer에 정의된 Workflow Entry Point를 호출합니다.

예상 형태:

```python
result = await graph.ainvoke(initial_state)
```

또는 실제 구현 방식에 따라:

```python
result = graph.invoke(initial_state)
```

를 사용할 수 있습니다.

동기 / 비동기 방식은
실제 LLM 호출과 Streaming 요구사항을 확인한 뒤 결정합니다.

---

## AgentState 생성

API는 사용자 Request를
Agent가 사용할 수 있는 초기 State로 변환합니다.

예:

```python
initial_state = {
    "user_query": request.message,
    "session_id": request.session_id,
}
```

기존 UserProfile이나 Conversation State가 존재하는 경우
Service Layer를 통해 불러온 뒤 포함할 수 있습니다.

예:

```text
ChatRequest
   ↓
Session 조회
   ↓
기존 UserProfile 조회
   ↓
Initial AgentState 생성
   ↓
LangGraph 실행
```

---

## Session 관리

Global-In은 여러 Turn에 걸쳐
사용자의 정보를 추가로 질문할 수 있습니다.

예:

```text
User:
독일 취업하고 싶어요.

AI:
관련 경력이 몇 년인가요?

User:
2년이요.
```

따라서 이전 대화 상태를 구분하기 위해
Session 또는 Conversation 식별자가 필요할 수 있습니다.

예:

```text
session_id
conversation_id
```

초기 MVP의 실제 저장 방식은
구현 복잡도에 따라 결정합니다.

---

## Missing Information 처리

사용자 정보가 부족한 경우
API가 직접 필요한 질문을 판단하지 않습니다.

처리 흐름:

```text
User Request
   ↓
FastAPI
   ↓
LangGraph
   ↓
사용자 이해 에이전트
   ↓
Missing Information 발견
   ↓
추가 질문 생성
   ↓
ChatResponse
```

API는 생성된 Follow-up Question을
Frontend에 전달합니다.

---

## Program Recommendation 처리

사용자가 진출 경로 추천을 요청하는 경우:

```text
FastAPI
   ↓
LangGraph
   ↓
사용자 이해 에이전트
   ↓
진출 경로 탐색·추천 에이전트
   ↓
Response
```

API가 Program Resolver를 직접 호출하지 않는 것을 원칙으로 합니다.

---

## Eligibility 처리

자격 검토 요청:

```text
FastAPI
   ↓
LangGraph
   ↓
자격 검토 에이전트
   ↓
Rule Evaluator
   ↓
EligibilityResult
   ↓
Response
```

API Endpoint에서 직접:

```python
if user.age <= 30:
```

와 같은 자격 판정 로직을 작성하지 않습니다.

---

## 공식 정보 안내 처리

공식 정보 관련 요청:

```text
FastAPI
   ↓
LangGraph
   ↓
공식 정보 안내 에이전트
   ↓
Retrieval
   ↓
Evidence Validation
   ↓
Response
```

API는 검색된 Chunk나 pgvector Query를 직접 관리하지 않습니다.

---

## 준비 계획 처리

준비 계획 요청:

```text
FastAPI
   ↓
LangGraph
   ↓
준비 계획 에이전트
   ↓
Checklist
   ↓
Roadmap
   ↓
Response
```

---

## Error Handling

API Layer에서는 HTTP 수준의 Error Handling을 담당합니다.

예:

```text
잘못된 Request
필수 Field 누락
Agent Workflow 오류
Database 연결 오류
LLM Timeout
예상하지 못한 Internal Error
```

---

## 예상 HTTP Status

예:

```text
200
→ 정상 처리

400
→ 잘못된 Request

422
→ Request Validation Error

500
→ Internal Server Error

503
→ 외부 Service 사용 불가
```

실제 Error 정책은 구현 과정에서 구체화합니다.

---

## Agent 오류와 HTTP 오류 구분

다음 상황은 반드시 서버 오류가 아닙니다.

예:

```text
공식 근거 부족

사용자 정보 부족

Eligibility 추가 확인 필요

현재 신청 가능 여부 미확인
```

이런 경우는 정상적인 Agent 결과입니다.

예:

```json
{
  "answer": "추가 확인이 필요합니다.",
  "follow_up_question": "...",
  "sources": []
}
```

HTTP `500`으로 처리하지 않습니다.

---

## Validation Error

FastAPI와 Pydantic을 이용하여
잘못된 Request를 자동 검증합니다.

예:

```json
{
  "message": ""
}
```

빈 Message 허용 여부 등은
ChatRequest Model에서 정의합니다.

---

## Response Validation

Agent가 반환한 결과도
Response Model을 통해 검증하는 것을 권장합니다.

예:

```python
@app.post(
    "/chat",
    response_model=ChatResponse
)
```

이를 통해 Frontend와 Backend 간
Response 구조를 안정적으로 유지합니다.

---

## API와 Models의 관계

```text
FastAPI
   ↓
ChatRequest
   ↓
AgentState
   ↓
LangGraph
   ↓
ChatResponse
```

Model 정의 위치:

```text
app/models/
```

API에 동일한 Schema를 중복 정의하지 않는 것을 원칙으로 합니다.

---

## API와 Services의 관계

API는 필요한 경우 Service Layer를 사용할 수 있습니다.

예:

```text
Session 조회
UserProfile 조회
Conversation 저장
```

구조:

```text
API
 ↓
Service
 ↓
Database
```

Endpoint에서 직접 SQL Query를 반복 작성하지 않습니다.

---

## Frontend와의 관계

Frontend는 Streamlit을 사용합니다.

기본 흐름:

```text
Streamlit
   ↓
HTTP Request
   ↓
FastAPI
   ↓
Agent
   ↓
FastAPI Response
   ↓
Streamlit
```

Frontend가 Agent 내부 코드를 직접 Import하여 호출하지 않고,
API를 통해 통신하는 구조를 기본으로 합니다.

---

## CORS

Frontend와 Backend가 서로 다른 Origin에서 실행될 경우
CORS 설정이 필요할 수 있습니다.

예:

```python
from fastapi.middleware.cors import CORSMiddleware
```

개발 환경에서는 필요한 Origin만 허용하고,
운영 환경에서 무조건 전체 Origin을 허용하지 않는 것을 권장합니다.

---

## Streaming

초기 MVP에서는 일반 HTTP Response부터 구현할 수 있습니다.

향후 답변 Streaming이 필요한 경우
다음 구조를 검토할 수 있습니다.

```text
Streamlit
   ↓
FastAPI
   ↓
SSE / StreamingResponse
   ↓
LangGraph / LLM Stream
```

Streaming은 기본 Chat API가 안정된 뒤 추가하는 것을 권장합니다.

---

## API Versioning

초기에는 단순 구조로 시작합니다.

예:

```text
POST /chat
GET /health
```

API 규모가 커지면 다음과 같은 Versioning을 고려할 수 있습니다.

```text
/api/v1/chat
/api/v1/health
```

MVP 초기부터 불필요하게 복잡한 Versioning 구조를 만들 필요는 없습니다.

---

## 예상 Endpoint

초기 MVP 기준:

```text
GET /
GET /health
POST /chat
```

필요한 경우 향후 추가 가능:

```text
GET /programs/{program_id}

GET /support-programs/{support_program_id}

GET /sessions/{session_id}
```

다만 Agent 기반 Chat에서 처리 가능한 기능을
불필요하게 별도 Endpoint로 분리하지 않습니다.

---

## API Response의 Source 정보

공식 정보가 포함된 Response에는
사용한 Evidence 정보를 전달할 수 있어야 합니다.

예:

```json
{
  "sources": [
    {
      "official_agency": "Example Agency",
      "source_title": "Official Guide",
      "source_url": "https://example.com",
      "verified_at": "2026-10-17"
    }
  ]
}
```

이를 통해 Frontend에서
공식 출처를 사용자에게 표시할 수 있습니다.

---

## 지원제도 Response

SupportProgram이 포함된 경우
Program과 구분하여 전달합니다.

예:

```json
{
  "recommendations": [],
  "support_programs": []
}
```

Program과 SupportProgram을
하나의 배열에 무분별하게 섞지 않습니다.

---

## Eligibility Response

비자·Program과 SupportProgram 자격 결과 역시
대상을 식별할 수 있어야 합니다.

예:

```json
{
  "target_type": "PROGRAM",
  "target_id": "example_program",
  "status": "조건 충족"
}
```

또는:

```json
{
  "target_type": "SUPPORT_PROGRAM",
  "target_id": "support_example",
  "status": "추가 확인 필요"
}
```

---

## Application Availability Response

Eligibility와 현재 신청 가능 여부는
별도의 Field로 반환할 수 있습니다.

예:

```json
{
  "eligibility_status": "조건 충족",
  "application_status": "UNKNOWN"
}
```

이를 통해 Frontend에서:

```text
자격 요건 충족

현재 접수 여부
→ 추가 확인 필요
```

처럼 구분하여 표시할 수 있습니다.

---

## Security

API Key와 Database URL은
코드에 직접 작성하지 않습니다.

환경변수 사용:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
DATABASE_URL
```

실제 값은:

```text
.env
```

에서 관리하고 Git에 Commit하지 않습니다.

Repository에는:

```text
.env.example
```

만 포함합니다.

---

## Logging

초기 구현부터 최소한의 Logging을 고려합니다.

예:

```text
Request ID
Session ID
Endpoint
Agent 실행 결과
Exception
처리 시간
```

단, 개인정보나 민감한 사용자 입력을
불필요하게 그대로 Log에 저장하지 않도록 주의합니다.

---

## Timeout

LLM과 Database 등 외부 Service 호출에서는
무한 대기를 방지하기 위해 Timeout 처리를 고려합니다.

예:

```text
LLM Timeout
Database Timeout
Embedding Timeout
```

Timeout 발생 시
사용자에게 Internal Stack Trace를 그대로 노출하지 않습니다.

---

## 개발 순서

초기 API 구현 순서는 다음과 같습니다.

```text
1. 현재 /health 유지

2. ChatRequest Model 정의

3. ChatResponse Model 정의

4. POST /chat Endpoint 추가

5. Agent Workflow Entry Point 연결

6. Session ID 전달

7. Error Handling 추가

8. Frontend 연결

9. Integration Test

10. 필요 시 Streaming 추가
```

---

## 테스트 포인트

### Health Check

```text
GET /health가 정상 응답하는가
```

### Request Validation

```text
message가 정상 검증되는가

잘못된 Request에 적절한 Error가 반환되는가
```

### Agent 연결

```text
POST /chat이 LangGraph Workflow를 정상 호출하는가
```

### Response

```text
ChatResponse Schema와 일치하는가
```

### Missing Information

```text
사용자 정보가 부족할 때 Follow-up Question이 반환되는가
```

### Eligibility

```text
Program과 SupportProgram Eligibility가 구분되는가
```

### Evidence

```text
공식 출처 정보가 Response에 포함되는가
```

### Error

```text
Agent 오류를 정상적으로 처리하는가

내부 Stack Trace가 사용자에게 노출되지 않는가
```

---

## Integration Test 예시

```text
Streamlit
   ↓
POST /chat
   ↓
FastAPI
   ↓
LangGraph
   ↓
사용자 이해 에이전트
   ↓
Follow-up Question
   ↓
FastAPI
   ↓
Streamlit
```

또는:

```text
FastAPI
   ↓
LangGraph
   ↓
공식 정보 안내 에이전트
   ↓
Retrieval
   ↓
Evidence
   ↓
ChatResponse
```

---

## 현재 상태

현재 FastAPI 기본 Application이 구성되어 있으며,
다음 Endpoint가 실행 가능한 상태입니다.

```text
GET /
GET /health
```

다음 구현 단계에서는
공통 ChatRequest / ChatResponse Model과
LangGraph Workflow Entry Point를 연결하여:

```text
POST /chat
```

Endpoint를 구현하는 것을 목표로 합니다.

Agent 내부 구조와 API Layer의 책임을 분리하고,
Frontend가 하나의 안정된 API Interface를 통해
Global-In 기능을 사용할 수 있도록 구성합니다.

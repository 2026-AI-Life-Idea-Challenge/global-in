# app/api

Global-In의 FastAPI 기반 Backend API를 구현하는 디렉터리입니다.

Frontend에서 들어오는 요청을 받고, 요청 데이터를 검증한 뒤, Agent 또는 Service Layer를 호출하여 결과를 반환합니다.

API 계층은 복잡한 비즈니스 로직을 직접 처리하지 않고 요청/응답 처리와 내부 기능 연결에 집중합니다.



---



## 주요 역할

`app/api/`는 다음 역할을 담당합니다.

```text
Frontend Request
   ↓
FastAPI
   ↓
Request Validation
   ↓
Agent / Service 호출
   ↓
Response 생성
   ↓
Frontend 반환
```

주요 책임:
- HTTP 요청 수신
- Request 데이터 검증
- Agent 호출
- Service 호출
- API Response 생성
- 오류 처리
- Health Check
- 향후 인증/권한 처리 확장 가능



---



# 현재 구현

현재는 기본 서버 동작 확인을 위한 최소 API가 구현되어 있습니다.

파일:
```
app/api/main.py
```

현재 Endpoint:
```
Get /
Get /health
```



## Get /

FastAPI 서버가 정상 실행 중인지 간단히 확인하기 위한 Endpoint입니다.

현재 응답 예시:
```
{
  "message": "Global-In API is running"
}
```



## GET /health

서비스 Health Check를 위한 Endpoint입니다.

현재 응답:
```
{
  "status": "ok"
}
```

향후에는 필요에 따라 다음 상태까지 확인하도록 확장할 수 있습니다.
```
FastAPI 상태
PostgreSQL 연결 상태
pgvector 연결 상태
LLM API 연결 상태
```



---



## 향후 APi 구성

향후 다음과 같은 API를 추가할 수 있습니다.
```
POST /chat
POST /profile
POST /recommend
POST /compare
GET /programs
GET /health
```
실제 Endpoint 구성은 개발 과정에서 조정될 수 있습니다.



### POST /chat

사용자와 AI Agent 간 대화를 처리하는 핵심 API입니다.
```
User Message
   ↓
POST /chat
   ↓
Request Validation
   ↓
LangGraph Workflow 호출
   ↓
Agent 실행
   ↓
최종 응답 반환
```
예상 Request
```
{
  "message": "일본 취업을 준비하고 싶은데 어떤 경로가 있어?",
  "session_id": "example-session"
}
```
실제 Schema는 `app/models/`에서 정의합니다.



### POST /profile

사용자 Profile을 생성하거나 갱신하는 API로 확장할 수 있습니다.

예상 Profile 정보:
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
Profile 데이터 구조는 `app/models/`에서 관리합니다.



### POST /recommend

사용자의 Profile을 기반으로 국가 또는 진출 경로를 요청하는 API로 사용할 수 있습니다.

예:
```
User Profile
   ↓
Recommendation Logic
   ↓
추천 국가 / 경로
   ↓
추천 이유
```
추천 로직은 API에서 직접 구현하지 않고 Agent 또는 Service Layer를 호출합니다.



---



## API와 Agent의 관계

API는 Agent의 내부 Workflow를 직접 구현하지 않습니다.
```
FastAPI
   ↓
Agent 호출
   ↓
LangGraph Workflow
   ↓
Rule / Retrieval / Service
   ↓
결과
   ↓
FastAPI Response
```
즉:
```
API = 외부 요청과 내부 시스템 사이의 진입점

Agent = 실제 Workflow 조정
```
으로 역할을 분리합니다.



## API와 Models의 관계

Request와 Response 구조는 가능한 한 `app/models/`에서 정의한 Pydantic Model을 사용합니다.

예:
```
ChatRequest
ChatResponse
UserProfile
EligibilityResult
ProgramResponse
```
이를통해:
- 데이터 형식 통일
- 자동 Validation
- API 문서 자동 생성
- 잘못된 Request 차단
이 가능해집니다.



### API와 Services의 관계

DB조회나 LLM API 호출 같은로직은 API 파일 안에서 직접 구현하지 않습니다.

예:
```
FastAPI
   ↓
Service
   ├─ PostgreSQL
   ├─ OpenAI
   ├─ Claude
   └─ Embedding
```
이렇게 분리하여 유지보수성과 테스트 용이성을 높입니다.



---



## 오류 처리

API에서는 향후 공통 오류 처리 방식을 적용합니다.

예:
```
400
잘못된 요청

404
프로그램 또는 데이터 없음

422
Request Validation 실패

500
서버 내부 오류

503
외부 API 또는 DB 사용 불가
```
사용자에게 내부 에러 로그나 민감한 정보를 그대로 노출하지 않습니다. 



----



## 구현 예정 구조
```
app/api/
├─ __init__.py
├─ main.py
├─ routes/
│  ├─ chat.py
│  ├─ profile.py
│  ├─ recommend.py
│  └─ health.py
└─ README.md
```
현재는 기능 규모가 작기 때문에 `main.py`에서 시작하고, Endpoint가 많아질 경우 `routes/` 단위로 분리합니다.



### main.py

FastAPI Application의 진입점입니다.

현재 역할:
```
FastAPI App 생성
기본 Endpoint 등록
Health Check 제공
```

향후 역할:
```
Router 등록
Middleware 등록
Exception Handler 등록
CORS 설정
Application Lifecycle 관리
```



---



## 구현 원칙
- API에서는 복잡한 비즈니스 로직을 직접 구현하지 않음
- Request / Response는 Pydantic Model 사용
- Agent 실행은 별도 Workflow에 위임
- DB 및 LLM 호출은 Service Layer에 위임
- 오류 응답 형식을 가능한 한 통일
- API Key 등 민감정보를 Response에 포함하지 않음
- Endpoint 기능이 커지면 Router 단위로 분리
- Frontend가 내부 DB나 Agent를 직접 호출하지 않도록 구성



---



## 현재 개발 상태

현재 완료:
```
FastAPI 기본 Application 생성
GET /
GET /health
로컬 서버 실행 확인
```

현재 실행 명령:
```
uvicorn app.api.main:app --reload
```

기본 주소:
```
http://127.0.0.1:8000
```

API 문서:
```
http://127.0.0.1:8000/docs
```



---



## 향후 개발 순서
```
1. API Request / Response Model 정의
2. /chat Endpoint 생성
3. LangGraph Workflow 연결
4. Session / Profile 처리
5. Error Handling
6. Frontend 연결
7. Integration Test
```
세부 Endpoint와 Agent 연결 방식은 Agent 구조 확정 후 함께 조정합니다.

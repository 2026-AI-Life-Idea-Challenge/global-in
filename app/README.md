# app

Global-In의 핵심 백엔드 로직을 관리하는 디렉터리입니다.

사용자 입력을 받아 프로필을 해석하고,
적절한 해외 진출 경로를 탐색한 뒤
자격 조건 판정, 공식 문서 검색, 근거 검증, 최종 응답 생성을 수행합니다.

---

## 전체 역할

`app/` 내부에서는 다음과 같은 흐름을 처리합니다.

```text
사용자 요청
   ↓
FastAPI
   ↓
LangGraph Agent
   ↓
User Profile 확인
   ↓
Intent / Missing Information 분석
   ↓
Program Resolver
   ↓
Rule Evaluator
   ↓
RAG Retrieval
   ↓
Evidence Check
   ↓
LLM Response Generator
   ↓
최종 응답
```

Frontend는 핵심 비즈니스 로직을 직접 수행하지 않고, FastAPI를 통해 app/ 내부 기능을 호출합니다.



---



# 디렉터리 구조

```
app/
├─ agent/
├─ api/
├─ models/
├─ retrieval/
├─ rules/
├─ services/
└─ __init__.py
```


## agent/

LangGraph 기반 AI Agent를 구현합니다.

담당 기능:
- 사용자 상태 관리
- Intent 분석
- Missing Information 탐지
- 추가 질문 생성
- 사용자 Profile 갱신
- Program Resolver 호출
- Rule Evaluator 호출
- RAG 검색 호출
- Evidence Check
- 최종 응답 생성
- Agent Node 간 Routing
Agent의 전체 실행 흐름을 관리하는 핵심 디렉터리입니다.

세부 구현 내용은 아래의 아래의 파일에서 관리합니다.
```
app/agent/README.md
```



## api/

FastAPI 기반 Backend API를 구현합니다.

담당 기능:
- Frontend 요청 수신
- 요청 데이터 검증
- Agent 호출
- API 응답 반환
- Health Check
- 오류 처리

현재 구현:
```
GET /
GET /health
```

향후에 다음 API를 추가할 수 있습니다.
```
POST /chat
POST /profile
POST /recommend
POST /programs
```
API 게층에서는 복잡한 비즈니스 로직을 직접 처리하지 않고 Agent 또는 Service Layer에 작업을 위임하는 것으로 원칙으로 합니다.

세부 구현 내용은 아래의 아래의 파일에서 관리합니다.
```
app/api/README.md
```



## models/

프로젝트 전반에서 사용하는 데이터 구조를 정의합니다.
주로 Pydantic Model을 사용합니다.

예정 모델:
```
UserProfile
Program
EligibilityResult
Evidence
ChatRequest
ChatResponse
Checklist
Roadmap
```
API, Agent, Rule Evaluator, Retrieval 등이 동일한 데이터 구조를 사용하도록 만드는 역할을 합니다.

세부 구현 내용은 아래의 아래의 파일에서 관리합니다.
```
app/models/README.md
```



## retrieval/

공식 문서 검색 및 RAG 로직을 구현합니다.

담당 기능:
- pgvector 검색
- Query 생성
- Metadata Filtering
- 공식 문서 Retrieval
- 검색 결과 정렬
- Evidence 후보 생성

예를 들어 사용자가:
```
일본 워킹홀리데이는 나이 제한이 어떻게 돼?
```
라고 질문하면,
```
country = Japan
purpose = Working Holiday
```
등의 Metadata를 활용하여 검색 범위를 좁힌 뒤 관련 공식 문서를 검색합니다.

세부 구현 내용은 아래의 아래의 파일에서 관리합니다.
```
app/retrieval/README.md
```



## rules/

구조화된 자격 조건을 판정합니다.
명확하게 코드로 판단할 수 있는 조건은 LLM에게 판정을 맡기지 않습니다.

예:
```
나이
국적
학력
경력
언어 점수
재정 조건
필수 자격
```

판정 결과는 기본적으로 다음 세 상태를 사용합니다.
```
조건 충족
추가 확인 필요
조건 미충족
```
예외 규정이나 공식 자료만으로 자동 판정할 수 없는 조건은 `추가 확인 필요`로 처리합니다.

세부 구현 내용은 아래의 아래의 파일에서 관리합니다.
```
app/rules/README.md
```



## services/

여러 모듈에서 공통으로 사용하는 기능을 구현합니다.

예:
```
OpenAI API 호출
Claude API 호출
PostgreSQL 연결
Embedding 생성
환경 변수 로딩
Program 조회
공통 외부 API 처리
```
Agent Node에서 직접 모든 외부 서비스 코드를 작성하지 않고, Service Layer를 통해 호출하도록 구성합니다.
이를 통해 Agent와 외부 서비스 구현의 결합도를 낮춥니다.

세부 구현 내용은 아래의 아래의 파일에서 관리합니다.
```
app/services/README.md
```



## __init__.py

Python이 app 디렉터리를 Python Package로 인식하도록 하는 파일입니다.

예를 들어 다음과 같은 import가 가능하도록 합니다.
```
from app.api.main import app
```
현재는 별도의 로직을 넣지 않고 빈 파일로 유지합니다.



---



## 모듈 역할 분리 원칙

Global-In에서는 다음과 같이 역할을 구분합니다.

```
API
→ 요청/응답 처리

Agent
→ 전체 Workflow 관리

Models
→ 데이터 구조 정의

Rules
→ 결정 가능한 조건 판정

Retrieval
→ 공식 근거 검색

Services
→ DB / LLM / 외부 서비스 연결
```
특정 기능을 하나의 파일이나 모듈에 모두 넣지 않고 역할에 따라 분리하는 것을 원칙으로 합니다.



---



## 처리 흐름 예시

사용자가 다음과 같이 질문한다고 가정합니다. 

```
29살이고 일본 워킹홀리데이를 가고싶은데 가능해?
```

처리 흐름:
```
1. API
   사용자 질문 수신

2. Agent
   사용자 의도 및 Profile 분석

3. Missing Information
   현재 정보만으로 판단 가능한지 확인

4. Program Resolver
   관련 일본 프로그램 탐색

5. Rule Evaluator
   구조화된 자격 조건 비교

6. Retrieval
   관련 공식 문서 검색

7. Evidence Check
   검색 결과의 관련성 / 출처 / 최신성 확인

8. LLM
   Rule 결과와 공식 근거를 이용하여 설명 생성

9. API
   최종 응답 반환
```



---



## 구현 원칙

`app/` 내부 개발에서는 다음 원칙을 따릅니다.
- 구조화 가능한 조건은 Rule 기반으로 처리
- LLM이 자격 조건을 임의로 판정하지 않도록 구성
- 공식 근거와 AI 설명을 구분
- API 계층에 복잡한 비즈니스 로직을 넣지 않음
- 데이터 구조는 가능한 한 Pydantic Model로 통일
- DB 및 외부 API 접근은 Service Layer로 분리
- Agent State를 통해 단계 간 데이터를 전달
- 특정 국가만 예외적으로 하드코딩하는 구조를 최소화

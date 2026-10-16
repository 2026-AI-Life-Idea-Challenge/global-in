# Global-In🌍



해외 진출을 준비하는 사용자를 위한 AI 기반 글로벌 진출 경로 탐색 서비스입니다.



Global-In은 여러 국가와 기관에 흩어져 있는 해외 진출 정보를 구조화하고,

사용자의 조건을 분석하여 적합한 진출 경로, 자격 요건, 준비 절차를 공식 근거와 함께 제공합니다.



---



## 프로젝트 목적



해외 취업, 유학, 워킹홀리데이 및 교환 프로그램을 준비할 때 필요한 정보는

국가별 정부기관, 대사관, 출입국 기관, KOTRA 등 여러 곳에 분산되어 있습니다.



또한 동일한 프로그램이라도 사용자의 나이, 학력, 경력, 언어 능력, 재정 조건 등에 따라

적용 가능 여부가 달라질 수 있습니다.



Global-In은 다음을 목표로 합니다.



> 분산된 해외 진출 정보를 하나의 기준으로 구조화하고,

> AI가 사용자의 조건을 분석하여 적합한 진출 경로·자격 요건·준비 절차를

> 공식 근거와 함께 제공함으로써 해외 진출 과정의 정보 비대칭과

> 의사결정 부담을 줄입니다.



---



## 대상 국가



MVP에서는 다음 5개 국가를 대상으로 합니다.



- 일본

- 호주

- 미국

- 독일

- 캐나다



---



## 진출 경로



각 국가마다 다음 3개의 상위 진출 경로를 다룹니다.



- 워킹홀리데이 / 교환

- 유학

- 취업



따라서 전체 범위는 다음과 같습니다.



```text

5개 국가 × 3개 상위 진출 경로 = 15개 경로

(단, 위 15개 항목은 실제 비자 15개를 의미하지 않습니다.

각 상위 진출 경로 아래에 실제 국가별 비자, 프로그램, 체류 자격이 연결되는 구조입니다.)
```



---



## 프로젝트 구조

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



## app/

서비스의 핵심 백엔드 로직을 구현하는 디렉터리입니다.

- app/agent/
  - LangGraph 기반 Agent 흐름 구현
  - 사용자 상태 관리
  - Node / Edge / Routing 로직
  - Missing Information 처리
  - 추가 질문 및 Agent 상태 전이
- app/api/
  - FastAPI 기반 API 서버
  - Frontend와 Agent 연결
  - 현재 main.py에서 기본 서버 및 /health API 제공
  - 향후 /chat, /profile, /recommend 등의 API 구현 예정
- app/models/
  - 프로젝트에서 사용하는 데이터 구조 정의
  - Pydantic Model
  - UserProfile, Program, EligibilityResult, ChatRequest/Response 등 구현 예정
- app/retrieval/
  - RAG 검색 로직
  - pgvector 검색
  - Metadata Filtering
  - 공식 문서 검색 및 Evidence Retrieval 구현
- app/rules/
  - 자격 조건 판정 로직
  - 연령, 학력, 경력, 언어, 재정 조건 등을 Rule 기반으로 평가
  - 조건 충족 / 추가 확인 필요 / 조건 미충족 상태 결정
- app/services/
  - 여러 모듈에서 공통으로 사용하는 기능
  - OpenAI API 호출
  - Claude API 호출
  - PostgreSQL 연결
  - Embedding 생성
  - 환경 변수 관리


---



## data/

수집 및 가공한 데이터를 관리합니다.

- data/raw/
  - 공식 사이트에서 수집한 원본 데이터
- data/processed/
  - 공통 Schema에 맞게 정제한 데이터
- data/seed/
  - PostgreSQL 초기 적재용 데이터



---



## docs/

프로젝트 설계 및 기획 문서를 관리합니다.

- docs/architecture/
  - 시스템 구조 및 아키텍처 문서
- docs/planning/
  - 프로젝트 기획, 정책, 데이터 설계 문서



---



## frontend/

Streamlit 기반 사용자 화면을 구현합니다.
현재 frontend/app.py는 기본 실행 확인용 화면이며,
향후 다음 기능을 구현할 예정입니다.

- 온보딩
- AI 상담
- 사용자 Profile
- 국가 / 경로 추천
- Eligibility 결과
- Checklist
- Roadmap
- 공식 출처 표시



---



## scripts/

서비스 실행 코드와 분리된 작업용 스크립트를 관리합니다.

- scripts/crawl/
  - 공식 사이트 데이터 수집
- scripts/ingest/
  - PostgreSQL 및 pgvector 데이터 적재
- scripts/evaluate/
  - RAG, Rule Evaluator, 응답 품질 평가



---



## tests/

테스트 코드를 관리합니다.

- tests/unit/
  - 개별 함수 및 모듈 테스트
- tests/integration/
  - API, Agent, DB 등 연결 테스트
- tests/scenarios/
  - 실제 사용자 상황 기반 시나리오 테스트



---



## .env.example

필요한 환경 변수의 형식을 공유하는 파일입니다.

```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DATABASE_URL=
```
실제 API Key는 입력하지 않습니다.



---



##  .gitignore

Git에 포함하지 않을 파일을 정의합니다. 

```
.venv/
.env
__pycache__/
.vscode/
.idea/
```



---



## requirements.txt

프로젝트에서 사용하는 Python 패키지와 버전을 관리합니다.
다른 팀원이 프로젝트를 Clone한 뒤 다음 명령으로 동일한 환경을 구성할 수 있습니다.

```
pip install -r requirements.txt
```



---



## app/api/main.py

현재 FastAPI 서버의 진입점입니다.

```
Ex.
GET /
GET /health
```
향후 Agent API와 서비스 API를 이 계층에서 연결합니다. 



---



## frontend/app.py

현재 Streamlit Frontend의 진입점입니다.
현재는 실행 확인용 기본 화면이며, 향후 실제 사용자 상담 UI를 구현합니다.



---



# Branch Strategy

## main

안정 버전을 관리합니다.

주요 용도:
- 최종 배포
- 대회 제출
- 안정 버전 관리

**일반적인 개발 작업은 main에서 직접 진행하지 않습니다.**



## develop

현재 프로젝트의 Default Branch입니다.

```
Default Branch = develop
```

**일반적인 개발 작업과 기능 통합은 develop을 기준으로 진행합니다.**



## 기본 흐름
```
feature/*
   ↓
develop
   ↓
Pull Request
   ↓
main
```

**현재 대부분의 개발은 develop을 기준으로 진행합니다.**

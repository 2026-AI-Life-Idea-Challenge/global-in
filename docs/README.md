# docs

Global-In의 기획, 설계, 아키텍처, 데이터베이스 구조 등 개발 문서를 관리하는 디렉터리입니다.

실제 서비스 실행 코드는 `app/`, `frontend/`, `scripts/`에서 관리하고,
개발 과정에서 팀원들이 함께 참고해야 하는 설계 및 기획 문서는 `docs/`에서 관리합니다.

---

## 주요 역할

`docs/`에서는 다음과 같은 문서를 관리합니다.

```text
서비스 기획
Agent 설계
System Architecture
Database / ERD 설계
Data Schema
API 설계
개발 정책
기능 정의
데이터 수집 기준
테스트 계획
```

---

## 디렉터리 구조

현재 기본 구조는 다음과 같습니다.

```text
docs/
├─ architecture/
├─ planning/
└─ README.md
```

필요한 경우 개발 과정에서 하위 디렉터리를 추가할 수 있습니다.

예:

```text
docs/
├─ architecture/
├─ planning/
├─ database/
├─ api/
└─ README.md
```

---

## `planning/`

프로젝트 기획 관련 문서를 관리합니다.

예:

```text
서비스 목적
사용자 문제 정의
MVP 범위
대상 국가
진출 경로
기능 목록
Agent 역할 정의
정보 범위
정책 및 구현 원칙
```

현재 Global-In의 주요 기획 내용에는 다음이 포함됩니다.

```text
대상 국가
- 일본
- 호주
- 미국
- 독일
- 캐나다

상위 진출 경로
- 워킹홀리데이 / 교환
- 유학
- 취업
```

또한 다음과 같은 Agent 구성을 관리할 수 있습니다.

```text
사용자 이해 에이전트
진출 경로 탐색·추천 에이전트
자격 검토 에이전트
공식 정보 안내 에이전트
준비 계획 에이전트
```

Agent 구조가 변경되면 기획 문서와 관련 README도 함께 갱신합니다.

---

## `architecture/`

Global-In의 시스템 구조와 기술 설계를 관리합니다.

예:

```text
전체 System Architecture
LangGraph Workflow
Agent 간 연결 구조
FastAPI 구조
Frontend / Backend 연결
PostgreSQL / pgvector 구성
외부 LLM 연결
```

전체 구조 예:

```text
User
   ↓
Streamlit
   ↓
FastAPI
   ↓
LangGraph
   ↓
Agent / Module
   ↓
PostgreSQL / pgvector / LLM
```

---

## Agent 설계 문서

Agent별로 다음 정보를 문서화합니다.

```text
Agent 이름
Agent 목적
담당 업무
입력 데이터
사용하는 Tool / Module
출력 데이터
다른 Agent와의 연결 관계
호출 조건
예외 처리
```

예:

```text
사용자 이해 에이전트

목적
→ 사용자의 목적과 현재 상황 파악

입력
→ 사용자 발화
→ 기존 User Profile

출력
→ 갱신된 User Profile
→ Intent
→ Missing Information
```

Agent 세부 설계는 실제 구현 구조가 확정되면서 보완합니다.

---

## Database / ERD 문서

PostgreSQL Schema 및 Entity 관계를 설계할 때 관련 문서를 `docs/`에서 관리합니다.

예상 문서:

```text
docs/database/erd.md
docs/database/schema.md
```

ERD에서는 다음과 같은 핵심 Entity를 정의할 수 있습니다.

```text
UserProfile
Program
SupportProgram
EligibilityRequirement
ApplicationInfo
RequiredDocument
EvidenceSource
```

실제 Entity와 Field는 공식 데이터를 수집하면서 조정합니다.

---

## Entity 설계 원칙

처음부터 모든 Field를 고정하기보다
현재 서비스가 반드시 필요로 하는 핵심 Entity와 관계부터 정의합니다.

```text
Agent 요구사항
   ↓
필요 데이터 확인
   ↓
Entity 도출
   ↓
Entity 관계 정의
   ↓
실제 데이터 수집
   ↓
Field 보완
```

실제 국가별 데이터 구조가 서로 다를 수 있기 때문에
세부 Field는 데이터 수집 결과를 확인하면서 확장합니다.

---

## Data Schema 문서

프로그램과 지원제도 등 공통 데이터 구조를 문서화합니다.

예:

```text
Program
Support Program
Eligibility Requirement
Evidence
Application Information
Document Requirement
```

Python Model은 `app/models/`,
실제 데이터는 `data/`,
설계 문서는 `docs/`에서 관리합니다.

즉:

```text
docs
→ 설계

app/models
→ 코드상의 Schema

data
→ 실제 데이터
```

로 역할을 구분합니다.

---

## 정보 범위 문서

Global-In에서 수집하고 제공하는 정보 범위도 문서화합니다.

주요 범위:

```text
한국에서 제공하는 해외 진출 지원 정보
목적지 국가의 외국인 진출·정착 지원 정보
목적지 국가의 비자·법률 정보
```

공식 출처 우선 원칙과
지원제도 적용 여부·현재 신청 가능 여부 등의 검증 기준도 함께 관리합니다.

---

## API 설계 문서

API 구조가 복잡해질 경우 별도 문서를 추가할 수 있습니다.

예:

```text
docs/api/endpoints.md
```

문서화 대상:

```text
Endpoint
HTTP Method
Request
Response
Error
사용하는 Agent / Service
```

FastAPI의 자동 Swagger 문서와 별개로
서비스 차원의 API 설계 이유를 기록할 때 사용합니다.

---

## Architecture Decision 기록

개발 과정에서 중요한 기술 선택이 발생하면
선택 이유를 문서로 남기는 것을 권장합니다.

예:

```text
왜 LangGraph를 사용하는가
왜 PostgreSQL + pgvector를 사용하는가
왜 Rule Evaluator를 LLM과 분리하는가
왜 Streamlit을 사용하는가
```

이를 통해 팀원이 나중에 구조를 봤을 때
단순히 "무엇을 사용했는가"뿐 아니라
"왜 사용했는가"도 이해할 수 있도록 합니다.

---

## 문서 관리 원칙

- 실제 구현과 문서 내용이 다르지 않도록 유지
- 기획 변경 시 관련 문서도 함께 수정
- 확정된 내용과 예정된 내용을 구분
- 실제 존재하지 않는 기능을 구현 완료처럼 작성하지 않음
- 데이터 출처 및 정책 관련 내용은 근거를 유지
- 중요한 구조 변경은 변경 이유를 함께 기록

---

## README와 docs의 차이

### README

각 디렉터리의 역할과 개발 방향을 빠르게 이해하기 위한 문서입니다.

예:

```text
app/README.md
app/agent/README.md
data/README.md
```

### docs

보다 상세한 기획 및 설계 문서를 관리합니다.

예:

```text
Agent 상세 설계
ERD
Database Schema
System Architecture
API 설계
```

즉:

```text
README
→ 해당 영역을 빠르게 이해하기 위한 설명

docs
→ 실제 설계와 의사결정을 기록하는 상세 문서
```

로 구분합니다.

---

## 향후 작성 예정 문서

현재 예상되는 주요 문서는 다음과 같습니다.

```text
Agent 상세 설계
System Architecture
ERD
Database Schema
Program / Support Program Schema
공식 정보 수집 기준
API 설계
시나리오 테스트 기준
```

실제 개발 진행 상황에 따라 필요한 문서를 순차적으로 추가합니다.

---

## 현재 상태

현재는 프로젝트 초기 구조를 구성하는 단계입니다.

Agent 역할과 데이터 범위는 기획되어 있으며,
향후 실제 데이터 수집과 DB 설계를 진행하면서
Architecture 및 Database 문서를 구체화합니다.

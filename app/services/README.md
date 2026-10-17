# app/services

Global-In에서 여러 모듈이 공통으로 사용하는 외부 서비스 연결 및 공통 기능을 구현하는 디렉터리입니다.

Agent, API, Retrieval, Rule Evaluator가
DB나 LLM API를 직접 호출하지 않고
`app/services/`를 통해 필요한 기능을 사용할 수 있도록 구성합니다.

이를 통해 외부 서비스 연결 로직과 비즈니스 로직을 분리합니다.

---

## 주요 역할

`app/services/`는 다음 기능을 담당합니다.

```text
PostgreSQL 연결
pgvector 연결
OpenAI API 호출
Claude API 호출
Embedding 생성
환경 변수 로딩
Program 조회
Support Program 조회
공통 외부 서비스 처리
```

전체 관계는 다음과 같습니다.
```
Agent / API / Retrieval
        ↓
     Services
        ↓
 ┌──────┼───────────┐
 ↓      ↓           ↓
DB     LLM       Embedding
```

---

## Services를 분리하는 이유
예를 들어 Agent 안에서 직접 OpenAI API를 호출하고, Retrieval 안에서 직접 PostgreSQL Connection을 만들면 같은 코드가 여러 곳에 반복될 수 있습니다.

다음과 같은 구조를 피합니다.
```
Agent
 └─ OpenAI API 직접 호출

Retrieval
 └─ PostgreSQL 직접 연결

API
 └─ Claude API 직접 호출
```
대신:
```
Agent
Retrieval
API
   ↓
Services
   ↓
외부 서비스
```
형태로 통일합니다.

---

## 예상 파일 구조
```
app/services/
├─ __init__.py
├─ config.py
├─ database.py
├─ llm.py
├─ embedding.py
├─ program_service.py
├─ support_service.py
└─ README.md
```

### config.py

환경 변수와 서비스 설정을 관리합니다.

예:
```
OPENAI_API_KEY
ANTHROPIC_API_KEY
DATABASE_URL
Embedding Model
LLM Model
```
환경 변수는 실제 코드에 직접 작성하지 않고 `.env`에서 읽어옵니다.

예:
```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DATABASE_URL=
```
**GitHub에는 실제 Key를 올리지 않습니다.**


### database.py

PostgreSQL 및 pgvector 연결을 담당합니다.

주요 역할:
```
Database Connection 생성
Connection 관리
Transaction 처리
Query 실행
pgvector 사용 환경 구성
```
예상 흐름:
```
Application
   ↓
database service
   ↓
PostgreSQL
   ↓
Structured Data / Vector Data
```
DB 접속 정보는 `DATABASE_URL` 환경 변수를 사용합니다.

---

## PostgreSQL에서 관리하는 데이터

PostgreSQL은 구조화된 정보를 저장합니다.

예:
```
진출 프로그램
지원제도
자격 조건
신청 방법
신청 기간
필요 서류
체류 조건
지원 내용
공식 출처 Metadata
```
구조화된 데이터는 `Program Resolver`, `Rule Evaluator`, `준비 계획` 기능 등에서 사용합니다. 

---

## pgvector에서 관리하는 데이터

공식 문서와 FAQ 등 긴 텍스트는 Chunk 단위로 나누어 Embedding과 함께 저장합니다.

예:
```
공식 법령
이민기관 안내
대사관 안내
지원사업 상세 안내
FAQ
예외 규정
행정 안내
```
`Retrieval Module`이 pgvector 검색을 통해 필요한 근거를 조회합니다.

---

## 11m.py

LLM API 호출을 공통으로 관리합니다.

사용 예정:
```
OpenAI API
Claude API
```
OpenAI API를 기본 모델로 사용하고, 필요한 경우 Claude API를 비교·검증 용도로 사용할 수 있습니다.

--- 

## LLM Service 역할

예:
```
사용자 발화 해석
추가 질문 생성
추천 이유 설명
공식 정보 한국어 설명
최종 응답 생성
```
Agent는 특정 SDK의 세부 호출 방식보다 필요한 기능에 집중하도옥 구성합니다.

---

## embedding.py

Embedding 생성 기능을 담당합니다. 

사용 대상:
```
공식 문서 Chunk
사용자 검색 Query
```
기본 흐름:
```
Text
   ↓
Embedding Service
   ↓
Embedding Model
   ↓
Vector
```
생셩된 Vector는 pgvector 검색에 사용합니다.

---

## Embedding Model

Embedding Model은 실제 구현 단계에서 결정합니다.

선택 시 다음을 고려합니다.
```
한국어 검색 성능
영어 및 다국어 검색 성능
비용
응답 속도
Embedding Dimension
API 사용 편의성
```
Global-In은 여러 국가의 공식 자료를 다루기 때문에 다국어 검색 성능도 고려합니다.

---

## program_service.py

국가별 실제 진출 프로그램을 조회하는 기능을 담당합니다.

예:
```
Japan
+
Employment
   ↓
관련 실제 Program 조회
```
Program Resolver가 직접 SQL을 작성하는 대신 Program Service를 통해 필요한 데이터를 가져올 수 있습니다.

주요 조회 조건:
```
country
purpose
program_id
program_type
```


## super_service.py

한국 또는 목적지 국가에서 제공하는 지원제도 정보를 조회합니다.

예:
```
한국 정부 해외취업 지원
해외 연수 지원
목적지 국가 외국인 취업 지원
유학생 지원
정착 지원
```
주요 조회 기준은 다음과 같을 수 있습니다.
```
issuer_country
destination_country
target_nationality
residence
purpose
related_program
support_type
```
지원제도는 하나의 진출 경로에만 연결되지 않을 수 있기 때문에 Program과 별도의 구조로 관리합니다.

---

## Program과 Supper Program의 차이

### Program 
사용자가 실제로 해외에 진출하기 위해 검토하는 비자·체류·교환 등의 경로입니다.

예:
```
취업 비자
학생 비자
워킹홀리데이
교환 프로그램
```


### Support Program
해외 진출 과정에서 활용할 수 있는 지원제도입니다.

예:
```
취업 준비 지원
연수 지원
지원금
장학 지원
정착 지원
```
**두 정보는 구분하여 저장하되, 필요한 경우 서로 연결합니다.**

---

## Program Resolver와 Services의 관계

Program Resolver는 어떤 프로그램이 사용자의 질문과 관련 있는지 결정합니다.
실제 데이터 조회는 Service Layer를 통해 수행할 수 있습니다.
```
Program Resolver
       ↓
Program Service
       ↓
PostgreSQL
       ↓
Program Data
```
즉:
```
Resolver
→ 어떤 데이터를 찾을지 결정

Service
→ 실제 데이터를 조회
```
로 역할을 분리합니다.

---

## Agent와 Services의 관계
Agent는 전체 흐름을 조정하고, 필요한 기능을 Service Layer에 요청합니다.
```
Agent
 ├─ LLM Service
 ├─ Program Service
 ├─ Support Service
 └─ Database Service
```
**Agent 내부에 외부 서비스 세부 구현을 직접 작성하지 않는 것을 원칙으로 합니다.**

---

## Retrieval과 Services의 관계

Retrieval은 공식 문서 검색 로직을 담당하고, 필요한 DB 연결 또는 Embedding 생성은 Services를 사용할 수 있습니다.
```
Retrieval
   ↓
Services
   ├─ Database
   └─ Embedding
```

---

## Rule Evaluator와 Services의 관계

Rule Evaluator 자체는 가능한 한 순수한 비교 로직으로 유지합니다.
```
User Profile
+
Requirement
   ↓
Rule Evaluator
```
필요한 Requirement 데이터는 `Service` 또는 `Program 조회` 단계에서 먼저 가져옵니다.
즉 **Rule Evaluator가 직접 DB에 접근하는 구조는 최소화합니다.**

---

## 오류 처리

외부 서비스는 다양한 이유로 실패할 수 있습니다.

예:
```
Database 연결 실패
LLM API Timeout
Rate Limit
Embedding API 실패
잘못된 API Key
외부 서비스 장애
```
Services에서는 이러한 오류를 가능한 한 공통된 방식으로 처리합니다.
Agent 또는 API에 외부 SDK의 원본 오류를 그대로 전달하지 않도록 합니다.

---

## 보안 원칙

다음 정보는 코드에 직접 작성하지 않습니다.
```
API Key
Database Password
Secret
Token
Credential
```
모든 민감 정보는 `.env` 또는 배포 환경의 Secret 관리 기능을 사용합니다.
`.env`는 GitHub에 업로드하지 않습니다.

--- 

## 구현 원칙
- DB 연결을 여러 모듈에 중복 작성하지 않음
- LLM 호출 방식을 Service Layer에서 통일
- API Key를 코드에 직접 작성하지 않음
- Agent가 특정 SDK 구현에 강하게 의존하지 않도록 구성
- Rule Evaluator는 가능한 한 DB나 외부 API와 분리
- Program과 Support Program을 구분
- 외부 서비스 오류를 공통된 방식으로 처리
- 테스트 시 실제 외부 API를 Mock으로 대체할 수 있도록 설계
- 특정 국가에 종속된 Service 구조를 최소화

---

## 개발 순서
```
1. 환경 변수 로딩
2. PostgreSQL 연결
3. Program 조회 Service
4. Support Program 조회 Service
5. OpenAI Service
6. Claude Service
7. Embedding Service
8. Retrieval 연결
9. Agent 연결
10. 오류 처리 및 테스트
```

---

## 테스트 포인트
```
환경 변수가 정상적으로 로딩되는가
DB 연결이 정상적으로 이루어지는가
Program을 조건에 맞게 조회하는가
Support Program을 올바르게 조회하는가
LLM API 호출이 정상적인가
Embedding 생성이 정상적인가
외부 서비스 오류를 안전하게 처리하는가
API Key가 로그나 응답에 노출되지 않는가
```


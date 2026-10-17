# tests

Global-In의 기능이 예상대로 동작하는지 검증하기 위한 테스트 코드를 관리하는 디렉터리입니다.

단일 함수 수준의 테스트부터
API·Agent·DB 연결 테스트,
실제 사용자 상황 기반 시나리오 테스트까지 단계별로 관리합니다.

---

## 주요 역할

`tests/`는 크게 다음 세 종류의 테스트를 관리합니다.

```text
개별 함수 / 모듈 검증
   ↓
unit

여러 모듈 연결 검증
   ↓
integration

실제 사용자 상황 검증
   ↓
scenarios
```

---

## 디렉터리 구조

```text
tests/
├─ unit/
├─ integration/
├─ scenarios/
└─ README.md
```

---

## `unit/`

개별 함수 또는 모듈이 독립적으로 올바르게 동작하는지 확인합니다.

예:

```text
Rule Operator
Eligibility 조건 비교
Metadata Filter
Program Resolver 일부 로직
Pydantic Model Validation
Checklist 상태 계산
```

외부 DB나 실제 LLM API 호출 없이
가능한 한 빠르고 독립적으로 실행할 수 있도록 구성합니다.

---

## Unit Test 예시

예를 들어 연령 조건이 다음과 같다고 가정합니다.

```text
age <= 30
```

다음 상황을 각각 테스트할 수 있습니다.

```text
age = 29
→ 조건 충족

age = 30
→ 조건 충족

age = 31
→ 조건 미충족

age = null
→ 사용자 정보 부족
```

경계값을 포함하여 테스트하는 것이 중요합니다.

---

## `integration/`

여러 모듈이 연결되었을 때 정상적으로 동작하는지 확인합니다.

예:

```text
FastAPI → LangGraph
LangGraph → Services
Services → PostgreSQL
Retrieval → pgvector
Rule Evaluator → Response Generator
Frontend → FastAPI
```

개별 모듈이 정상이어도
연결 과정에서 데이터 구조나 상태 전달 문제가 발생할 수 있기 때문에
Integration Test를 별도로 수행합니다.

---

## Integration Test 예시

```text
POST /chat
   ↓
ChatRequest Validation
   ↓
LangGraph 실행
   ↓
Program 조회
   ↓
Rule Evaluator
   ↓
Retrieval
   ↓
ChatResponse 반환
```

각 단계에서 데이터 형식이 유지되는지 확인합니다.

---

## `scenarios/`

실제 사용자 상담 상황을 기반으로 전체 동작을 검증합니다.

Global-In MVP에서는 다음 5개 국가를 대상으로 합니다.

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

따라서:

```text
5개 국가 × 3개 경로 = 15개 상위 진출 경로
```

를 테스트합니다.

---

## 기본 시나리오 유형

각 상위 진출 경로마다 최소 다음 4가지 상황을 테스트합니다.

```text
1. 정상 조건
2. 조건 미충족
3. 사용자 정보 부족
4. 예외 / 추가 확인 필요
```

따라서 최소 목표는:

```text
15개 경로 × 4개 상황 = 60개 Scenario
```

입니다.

---

## 정상 조건 시나리오

사용자가 주요 자격 조건을 충족하고
필요한 정보도 충분히 제공한 상황입니다.

검증 내용:

```text
올바른 Program이 선택되는가
Eligibility 결과가 정상인가
관련 Evidence가 검색되는가
최종 응답에 출처가 포함되는가
Checklist / Roadmap이 생성되는가
```

---

## 조건 미충족 시나리오

사용자 정보는 충분하지만
공식 요건 중 하나 이상을 충족하지 못하는 상황입니다.

예:

```text
필수 경력 2년
사용자 경력 1년
```

검증 내용:

```text
조건 미충족으로 판정되는가
부족 조건이 표시되는가
LLM이 결과를 임의로 충족으로 변경하지 않는가
```

---

## 사용자 정보 부족 시나리오

판정에 필요한 정보가 아직 없는 상황입니다.

예:

```text
경력 조건 필요
사용자 경력 정보 없음
```

검증 내용:

```text
조건 미충족으로 잘못 판정하지 않는가
Missing Information으로 처리되는가
필요한 추가 질문이 생성되는가
답변 후 Profile이 정상 갱신되는가
```

---

## 예외 / 추가 확인 필요 시나리오

단순 Rule만으로 판정하기 어려운 상황입니다.

예:

```text
예외 규정 존재
기관 판단 필요
공식 근거 충돌
적용 대상 불명확
현재 접수 가능 여부 미확인
```

검증 내용:

```text
임의로 확정하지 않는가
추가 확인 필요 상태를 사용하는가
확인할 기관이나 항목을 안내하는가
```

---

## 비자와 지원제도 테스트

비자 또는 체류 프로그램 자격과
지원제도 신청 자격을 별도로 검증합니다.

예:

```text
취업 비자
→ 조건 충족

한국 지원제도 A
→ 추가 확인 필요

현지 지원제도 B
→ 조건 미충족
```

하나의 결과를 전체 자격으로 합쳐버리지 않는지 확인합니다.

---

## 지원제도 테스트 포인트

지원제도에는 다음 상황을 별도로 테스트합니다.

```text
제도 존재 여부
한국인 적용 여부
현재 접수 여부
중복 수혜 제한
기존 참여 이력
현재 거주지 조건
재학 / 취업 상태
```

특히:

```text
제도 존재
≠
현재 신청 가능
```

을 시스템이 혼동하지 않는지 확인합니다.

---

## Retrieval 테스트

공식 정보 검색 기능은 다음 항목을 검증합니다.

```text
관련 문서가 검색되는가
국가가 일치하는가
Program이 일치하는가
Support Program이 일치하는가
적용 대상이 일치하는가
공식 기관 자료인가
Source URL이 유지되는가
날짜 Metadata가 유지되는가
```

---

## Evidence Check 테스트

검색 결과가 최종 근거로 사용되기 전에
다음 항목을 확인합니다.

```text
질문 관련성
국가 일치
Program 일치
대상 일치
공식 출처 여부
적용 시점
확인 시점
```

잘못된 검색 결과가 최종 Evidence로 통과하지 않는지 확인합니다.

---

## Rule Evaluator 테스트

다음 조건 유형을 테스트합니다.

```text
연령
국적
거주지
학력
경력
언어
재정
재학 여부
취업 상태
참여 이력
수혜 이력
중복 수혜 제한
```

다음 결과를 올바르게 구분하는지 확인합니다.

```text
조건 충족
조건 미충족
추가 확인 필요
사용자 정보 부족
```

---

## Agent Workflow 테스트

5개 Agent 또는 Agent 역할 간의 흐름도 검증합니다.

현재 기획 기준:

```text
사용자 이해
   ↓
진출 경로 탐색·추천
   ↓
자격 검토
   ↓
공식 정보 안내
   ↓
준비 계획
```

질문에 따라 필요한 Agent만 호출되는지도 확인합니다.

예:

```text
"독일 취업 비자의 근로 조건만 알려줘."

→ 모든 Agent를 처음부터 실행할 필요 없이
관련 공식 정보 검색과 응답 처리 중심으로 진행
```

---

## 추가 질문 Loop 테스트

사용자 정보가 부족한 경우:

```text
질문
   ↓
Missing Information
   ↓
추가 질문
   ↓
사용자 답변
   ↓
Profile Update
   ↓
다시 판단
```

흐름이 정상적으로 작동하는지 확인합니다.

특히 무한 반복이 발생하지 않는지 테스트합니다.

---

## 준비 계획 테스트

Checklist와 Roadmap이 사용자 상태에 맞게 생성되는지 확인합니다.

예:

```text
완료
준비 필요
추가 확인
```

지원제도 신청과 비자 준비가 서로 구분되면서도
하나의 일정으로 연결되는지 확인합니다.

---

## API 테스트

FastAPI Endpoint에 대해 다음을 확인합니다.

```text
정상 Request
잘못된 Request
필수값 누락
Agent 오류
DB 오류
외부 LLM 오류
```

예상 HTTP 상태 코드:

```text
200
400
404
422
500
503
```

실제 오류 정책은 API 구현 단계에서 확정합니다.

---

## Mock 사용

Unit Test에서는 가능한 한 실제 외부 서비스를 직접 호출하지 않습니다.

예:

```text
OpenAI API
Claude API
PostgreSQL
Embedding API
```

대신 Mock 또는 Test Double을 사용하여
테스트 속도와 재현성을 높입니다.

---

## 예상 파일 구조

```text
tests/
├─ unit/
│  ├─ test_rules.py
│  ├─ test_models.py
│  └─ test_retrieval_filters.py
│
├─ integration/
│  ├─ test_api_agent.py
│  ├─ test_database.py
│  └─ test_retrieval.py
│
├─ scenarios/
│  ├─ japan/
│  ├─ australia/
│  ├─ usa/
│  ├─ germany/
│  └─ canada/
│
└─ README.md
```

실제 구조는 구현 과정에서 변경될 수 있습니다.

---

## 테스트 데이터 원칙

테스트 데이터는 실제 공식 조건을 기반으로 작성하되,
테스트 목적과 기대 결과가 명확하게 정의되어야 합니다.

예:

```text
Input
사용자 나이: 31

Requirement
age <= 30

Expected
조건 미충족
```

LLM 응답 문장 자체보다
구조화된 결과가 먼저 올바른지 확인합니다.

---

## 테스트 우선순위

초기 MVP에서는 다음 순서로 테스트합니다.

```text
1. Models
2. Rule Evaluator
3. Program Resolver
4. Retrieval
5. Evidence Check
6. Agent Workflow
7. FastAPI Integration
8. Scenario Test
9. Frontend 연결
```

---

## 테스트 실행

Python 테스트 프레임워크는 구현 단계에서 `pytest` 사용을 권장합니다.

예:

```bash
pytest
```

특정 테스트:

```bash
pytest tests/unit/
```

```bash
pytest tests/integration/
```

```bash
pytest tests/scenarios/
```

`pytest` 패키지는 실제 테스트 구현 시 `requirements.txt`에 추가합니다.

---

## 테스트 원칙

- 예상 결과를 먼저 명확히 정의
- 정상 상황뿐 아니라 실패 상황도 테스트
- 경계값 테스트
- 사용자 정보 부족과 조건 미충족 구분
- 비자와 지원제도 결과 구분
- 실제 승인 결과처럼 표현하지 않는지 확인
- 공식 근거 없는 답변 생성 여부 확인
- 국가 및 Program 간 Evidence 혼입 여부 확인
- 외부 API 장애 상황 테스트
- 테스트가 반복 실행 가능하도록 구성

---

## 현재 상태

현재는 테스트 디렉터리 구조와 테스트 전략을 정의하는 단계입니다.

실제 테스트 코드는 각 기능 구현과 함께 추가합니다.

최소 목표는 15개 상위 진출 경로에 대해
4가지 기본 Scenario를 구축하여
총 60개 이상의 핵심 Scenario를 검증하는 것입니다.

# tests

Global-In의 Unit Test, Integration Test, Scenario Test를 관리하는 디렉터리입니다.

Global-In은 단순한 LLM 응답 품질만 확인하는 것이 아니라,
Program 탐색, SupportProgram 탐색, Rule Evaluator, Retrieval,
Evidence Validation, Agent Routing, Checklist, Roadmap까지 전체 흐름을 검증합니다.

테스트의 목적은 다음과 같습니다.

```text
잘못된 자격 판정 방지

잘못된 공식 근거 사용 방지

Program / SupportProgram 혼동 방지

Missing Information과 조건 미충족 혼동 방지

불필요한 Agent 호출 방지

Agent 간 State 전달 오류 방지

전체 사용자 흐름 검증
```

---

## 기본 디렉터리 구조

```text
tests/
├─ unit/
├─ integration/
├─ scenarios/
└─ README.md
```

---

# 테스트 구분

Global-In에서는 테스트를 크게 세 단계로 나눕니다.

```text
Unit Test

Integration Test

Scenario Test
```

---

# `unit/`

개별 Module 또는 Function 단위의 동작을 검증합니다.

외부 LLM이나 전체 Agent Workflow를 실행하지 않고도
결정적으로 검증 가능한 로직을 우선 테스트합니다.

주요 대상:

```text
Rule Evaluator

Program Resolver

Metadata Filter

Evidence Validator

Data Normalizer

Service Utility

Model Validation
```

---

## Unit Test의 목적

예:

```text
age <= 30
```

이라는 조건이 있을 때:

```text
age = 29
→ PASS

age = 30
→ PASS

age = 31
→ FAIL

age = null
→ UNKNOWN
```

처럼 정확한 결과가 나오는지 확인합니다.

---

# Rule Evaluator Unit Test

Rule Evaluator는 Global-In에서
가장 결정적으로 검증해야 하는 Module 중 하나입니다.

---

## 숫자 조건

예:

```text
career_years >= 2
```

테스트:

```text
3
→ PASS

2
→ PASS

1
→ FAIL

null
→ UNKNOWN
```

---

## 국적 조건

예:

```text
nationality in ["KR"]
```

테스트:

```text
KR
→ PASS

US
→ FAIL

null
→ UNKNOWN
```

---

## 존재 여부 조건

예:

```text
language exists
```

테스트:

```text
language = "B2"
→ PASS

language = null
→ FAIL 또는 UNKNOWN
```

정확한 정책은 Rule Schema에 맞춰 고정합니다.

---

## `manual_check`

예:

```text
judgeability = manual_check
```

결과:

```text
UNKNOWN
```

또는 내부 상태:

```text
NEEDS_REVIEW
```

로 처리되어야 합니다.

자동 PASS 또는 FAIL로 판단하면 안 됩니다.

---

# Missing Information Test

다음 두 상황을 반드시 구분합니다.

---

## 사용자 정보 없음

```text
Requirement:
career_years >= 2

UserProfile:
career_years = null
```

결과:

```text
Missing Information
```

또는:

```text
UNKNOWN
```

---

## 사용자 정보는 있지만 조건 미충족

```text
Requirement:
career_years >= 2

UserProfile:
career_years = 1
```

결과:

```text
FAIL
```

최종:

```text
조건 미충족
```

이어야 합니다.

---

# Program과 SupportProgram Unit Test

다음 두 대상은 별도로 처리되어야 합니다.

```text
PROGRAM

SUPPORT_PROGRAM
```

예:

```text
Program A
→ 조건 충족

SupportProgram A
→ 조건 미충족
```

하나의 결과로 합쳐지지 않는지 확인합니다.

---

# Eligibility와 Application Availability Test

다음 두 상태 역시 분리되어야 합니다.

```text
Eligibility
→ 조건 충족

Application Availability
→ CLOSED
```

이 경우:

```text
현재 신청 가능
```

으로 잘못 해석되면 안 됩니다.

---

# Program Resolver Unit Test

Program Resolver는
사용자의 국가와 목적을 실제 Program 후보에 연결합니다.

예:

```text
destination_country = Germany
purpose = Employment
```

Expected:

```text
독일 취업 관련 Program 후보
```

---

## 테스트 항목

```text
올바른 국가 Program을 반환하는가

올바른 목적 Program을 반환하는가

다른 국가 Program이 섞이지 않는가

Program이 없는 경우 안전하게 처리하는가
```

---

# 미국 경로 Test

미국에는 일반적인 Working Holiday Visa가 없기 때문에
다음과 같은 상위 경로 입력이 들어올 수 있습니다.

```text
USA
+
워킹홀리데이 / 교환
```

이 경우 실제 구현에서는:

```text
관련 Exchange Program
J-1 계열 Program
```

등으로 연결되어야 하며,
존재하지 않는 일반 Working Holiday Visa를 생성하면 안 됩니다.

---

# Metadata Filter Unit Test

Retrieval 전 Metadata Filtering을 검증합니다.

예:

```text
destination_country = Germany

purpose = Employment

program_id = example_program

information_topic = Work
```

Expected:

```text
독일 + 해당 Program + Work 관련 문서만 검색 대상으로 유지
```

---

## Filter Test 항목

```text
country filter

program filter

support_program filter

target_nationality filter

information_topic filter

source_type filter
```

---

# Evidence Validation Unit Test

Retrieval Result가 실제 Evidence로 사용 가능한지 검증하는 로직을 테스트합니다.

검토 항목:

```text
국가 일치

Program 일치

SupportProgram 일치

적용 대상 일치

공식 출처 여부

적용 시점

Evidence Metadata 존재 여부
```

---

## 잘못된 Evidence 예

질문:

```text
독일 취업 Program의 근로 조건
```

검색 결과:

```text
Canada
Student Program
Study Information
```

Expected:

```text
Evidence Reject
```

---

# Evidence 날짜 Test

다음 날짜가 혼동되지 않는지 확인합니다.

```text
original_published_at

original_updated_at

effective_from

effective_until

verified_at
```

예:

```text
verified_at = 2026-10-17
```

이라고 해서 자동으로:

```text
현재 유효
```

판정하면 안 됩니다.

---

# Model Validation Test

`app/models/`의 Pydantic Model이
잘못된 데이터를 적절하게 검증하는지 확인합니다.

예:

```text
필수 ID 누락

잘못된 Status 값

잘못된 Date Format

잘못된 target_type
```

등을 테스트할 수 있습니다.

---

# `integration/`

여러 Module이 함께 동작할 때
정상적으로 연결되는지 검증합니다.

주요 대상:

```text
Agent + Service

Agent + Rule Evaluator

Agent + Retrieval

Retrieval + pgvector

FastAPI + LangGraph

Frontend + FastAPI
```

---

# 사용자 이해 Agent Integration Test

예:

```text
User:
독일로 취업하고 싶어요.
```

Expected:

```text
Intent = Employment

희망 국가 = Germany

Missing Information 탐지

필요한 추가 질문 생성
```

---

## 추가 Turn

```text
AI:
관련 경력이 몇 년인가요?

User:
2년이에요.
```

Expected:

```text
UserProfile 업데이트

career_years = 2

같은 질문 반복하지 않음
```

---

# 진출 경로 탐색·추천 Agent Integration Test

입력:

```text
destination_country = Germany

purpose = Employment

UserProfile 존재
```

흐름:

```text
진출 경로 탐색·추천 에이전트
   ↓
Program Resolver
   ↓
Program Service
   ↓
PostgreSQL
```

Expected:

```text
실제 Program 후보 반환

관련 SupportProgram 후보 반환
```

---

# 자격 검토 Agent Integration Test

흐름:

```text
Candidate Program
   ↓
자격 검토 에이전트
   ↓
EligibilityRequirement 조회
   ↓
Rule Evaluator
   ↓
EligibilityResult
```

Expected:

```text
조건 충족

조건 미충족

추가 확인 필요
```

중 하나가 공식 Rule과 일치해야 합니다.

---

## Rule 결과 변경 방지 Test

Rule Evaluator 결과:

```text
조건 미충족
```

일 때 Agent가:

```text
조건 충족
```

으로 변경하면 안 됩니다.

Agent는 결과를 설명할 수는 있지만,
결정적 Rule 결과를 임의로 뒤집으면 안 됩니다.

---

# 공식 정보 안내 Agent Integration Test

흐름:

```text
User Question
   ↓
공식 정보 안내 에이전트
   ↓
Retrieval
   ↓
Evidence Validation
   ↓
LLM
   ↓
Response
```

검증 항목:

```text
검색된 Evidence와 답변이 일치하는가

공식 URL이 유지되는가

근거에 없는 내용을 추가하지 않는가
```

---

# 준비 계획 Agent Integration Test

흐름:

```text
Selected Program

Eligibility Result

SupportProgram

Official Evidence
   ↓
준비 계획 에이전트
   ↓
Checklist

Roadmap
```

검증 항목:

```text
조건 미충족 항목을 준비 완료로 표시하지 않는가

추가 확인 필요 항목을 확정하지 않는가

확인되지 않은 날짜를 생성하지 않는가

비자 서류와 지원제도 서류가 구분되는가
```

---

# FastAPI Integration Test

기본 Endpoint:

```text
GET /

GET /health

POST /chat
```

를 검증합니다.

---

## `/health`

Expected:

```json
{
  "status": "ok"
}
```

---

## `/chat`

Request 예:

```json
{
  "message": "독일로 취업하고 싶어요.",
  "session_id": "test-session"
}
```

검증:

```text
Request Validation

LangGraph 호출

Response Schema

Error Handling
```

---

# Session Integration Test

여러 Turn에 걸친 Profile이 유지되는지 확인합니다.

예:

```text
Turn 1

User:
캐나다 유학하고 싶어요.

↓

preferred_country = Canada
preferred_purpose = Study
```

```text
Turn 2

User:
컴퓨터공학 전공이에요.

↓

major = Computer Science
```

Expected:

```text
Turn 1의 정보가 유지됨

Turn 2 정보가 추가됨
```

---

# Retrieval Integration Test

실제 pgvector와 연결된 경우:

```text
Query
   ↓
Embedding
   ↓
Metadata Filter
   ↓
Vector Search
   ↓
Result
```

전체 검색 흐름을 검증합니다.

---

## Retrieval 검증 기준

```text
올바른 국가

올바른 Program

올바른 SupportProgram

올바른 Topic

공식 Source

Source URL

Metadata 유지
```

---

# `scenarios/`

실제 사용자가 서비스를 사용하는 것과 유사한
End-to-End Scenario를 테스트합니다.

Scenario Test는 개별 Function이 아니라
전체 서비스 흐름이 논리적으로 동작하는지 확인하는 것이 목적입니다.

---

## Scenario 구조

예:

```text
사용자 Profile

사용자 질문

Expected Agent Flow

Expected Program

Expected Eligibility

Expected SupportProgram

Expected Evidence

Expected Checklist

Expected Roadmap
```

---

# 기본 Scenario 범위

초기 MVP 대상 국가:

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

기본적으로:

```text
5개 국가 × 3개 상위 경로
```

의 대표 Scenario를 구성할 수 있습니다.

단, 이것은 15개의 개별 비자를 의미하지 않습니다.

---

# Scenario Test 예시 1

## 독일 취업 준비자

Profile:

```text
국적:
대한민국

희망 국가:
독일

목적:
취업

전공:
컴퓨터공학

경력:
2년
```

질문:

```text
독일로 취업하고 싶은데 어떤 방법이 있고
받을 수 있는 지원이 있는지 알려줘.
```

Expected Flow:

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

검증:

```text
실제 독일 취업 Program 후보가 나오는가

한국 / 독일 SupportProgram이 구분되는가

자격 결과가 공식 Rule과 일치하는가

공식 Source가 존재하는가

Checklist와 Roadmap이 생성되는가
```

---

# Scenario Test 예시 2

## 캐나다 유학 준비자

질문:

```text
캐나다로 유학을 준비하고 있어.
어떤 경로가 있고 장학 지원도 알고 싶어.
```

검증:

```text
Study 관련 Program 탐색

관련 SupportProgram 탐색

자격 검토

공식 학업 / 체류 정보

준비 계획
```

---

# Scenario Test 예시 3

## 일본 워킹홀리데이 준비자

질문:

```text
일본 워킹홀리데이를 준비하려고 해.
```

검증:

```text
관련 실제 Program 연결

연령 / 국적 등 자격 검토

필요 서류

공식 Source

출국 전 준비
```

---

# Scenario Test 예시 4

## 미국 교환 프로그램 준비자

질문:

```text
미국으로 워킹홀리데이처럼 갈 수 있는 방법이 있어?
```

Expected:

```text
미국 일반 Working Holiday Visa 생성 금지

관련 Exchange Program 탐색

J-1 등 실제 적용 가능한 Program 후보 검토
```

잘못된 결과:

```text
미국 워킹홀리데이 비자가 있습니다.
```

처럼 존재하지 않는 Program을 생성하면 실패입니다.

---

# Scenario Test 예시 5

## 호주 취업 준비자

질문:

```text
호주에서 일하고 싶은데
내 조건으로 가능한 경로를 확인해줘.
```

검증:

```text
Profile Missing Information 질문

실제 Employment Program 탐색

Eligibility

Evidence

Preparation
```

---

# Missing Information Scenario

사용자:

```text
독일로 취업하고 싶어.
```

하지만 경력 정보가 필요한 상황:

Expected:

```text
경력 정보 질문
```

잘못된 결과:

```text
경력 조건 미충족
```

사용자 정보가 없는 것을
조건 미충족으로 처리하면 실패입니다.

---

# Failed Requirement Scenario

공식 조건:

```text
career_years >= 2
```

사용자:

```text
career_years = 1
```

Expected:

```text
조건 미충족
```

잘못된 결과:

```text
추가 정보 필요
```

이미 사용자 정보가 존재하기 때문에
Missing Information으로 처리하면 안 됩니다.

---

# Application Availability Scenario

Eligibility:

```text
조건 충족
```

Current Application Status:

```text
UNKNOWN
```

Expected Response:

```text
공개된 자격 조건은 충족하지만
현재 접수 여부는 추가 확인이 필요합니다.
```

잘못된 Response:

```text
지금 신청 가능합니다.
```

---

# SupportProgram 적용 여부 Scenario

목적지 국가에 외국인 대상 SupportProgram이 존재하지만
한국인 적용 여부가 확인되지 않은 경우:

Expected:

```text
지원제도 존재

한국인 적용 여부
→ 추가 확인 필요
```

잘못된 결과:

```text
한국인이 신청 가능합니다.
```

---

# 공식 근거 부족 Scenario

Retrieval Result:

```text
[]
```

Expected:

```text
현재 확인된 공식 근거가 부족함

추가 확인 필요
```

잘못된 결과:

```text
LLM이 임의의 조건이나 기관 정보를 생성
```

---

# 근거 충돌 Scenario

Source A:

```text
age <= 30
```

Source B:

```text
age <= 35
```

그리고 충돌 원인을 해결할 수 없는 경우:

Expected:

```text
추가 확인 필요
```

LLM이 임의로 하나를 선택하면 안 됩니다.

---

# Agent Routing Scenario

질문:

```text
독일 취업 비자의 근로 제한만 알려줘.
```

필요한 핵심 Agent:

```text
공식 정보 안내 에이전트
```

불필요하게:

```text
사용자 이해
→ 추천
→ 자격
→ 공식 정보
→ 준비 계획
```

전체 Workflow를 항상 실행하지 않는지 확인합니다.

---

# Agent Collaboration Scenario

질문:

```text
독일로 취업하고 싶고,
받을 수 있는 지원도 알려줘.
```

Expected Flow:

```text
사용자 이해
   ↓
경로 탐색·추천
   ↓
자격 검토
   ↓
공식 정보 안내
   ↓
준비 계획
```

필요한 경우 사용자 정보 부족 시
다시 사용자 이해 단계로 돌아갈 수 있습니다.

---

# Shared State Test

Agent 간 State 전달을 검증합니다.

예:

```text
사용자 이해 에이전트
→ user_profile 생성
```

이후:

```text
자격 검토 에이전트
→ 동일 user_profile 사용
```

해야 합니다.

---

## 주요 State

예:

```text
user_query

user_profile

intent

missing_fields

candidate_programs

candidate_support_programs

selected_program

eligibility_results

retrieved_documents

validated_evidence

checklist

roadmap

final_answer
```

---

# State Overwrite Test

새 Agent가 기존 State를
잘못 덮어쓰지 않는지 확인합니다.

예:

```text
user_profile
```

에 이미:

```text
nationality = KR
```

이 존재하는데,
다른 Agent 실행 후 사라지면 실패입니다.

---

# Infinite Loop Test

LangGraph Workflow에서
무한 Loop가 발생하지 않는지 확인합니다.

예:

```text
Missing Information
   ↓
추가 질문
   ↓
사용자 답변
   ↓
Profile Update
   ↓
같은 Missing Information 반복
```

같은 질문이 무한히 반복되지 않아야 합니다.

---

# 불필요한 Agent 호출 Test

다음 질문:

```text
캐나다 학생 비자 공식 사이트 알려줘.
```

같은 단순 정보 요청에서
불필요한 Recommendation이나 Roadmap Agent를 호출하지 않는지 확인합니다.

---

# Hallucination Test

다음 유형의 Hallucination을 중점적으로 확인합니다.

```text
존재하지 않는 Program

존재하지 않는 SupportProgram

존재하지 않는 정부기관

잘못된 공식 URL

공식 문서에 없는 자격조건

임의의 신청 기간

임의의 처리 기간

임의의 지원금 금액

임의의 예외 규정
```

---

# Evidence Grounding Test

최종 답변의 주요 사실이
실제 Evidence에 의해 뒷받침되는지 확인합니다.

예:

```text
Final Answer:
경력 2년 이상 필요
```

Evidence에도 실제로:

```text
경력 2년 이상
```

이라는 조건이 존재해야 합니다.

---

# Rule / LLM Consistency Test

Rule Evaluator:

```text
조건 미충족
```

Final Answer:

```text
조건 충족
```

이면 실패입니다.

---

# Checklist Grounding Test

Checklist 항목이
공식 Program / SupportProgram 정보와 연결되는지 확인합니다.

예:

```text
Checklist:
특정 서류 제출
```

이라면 해당 서류가:

```text
RequiredDocument

또는 공식 Evidence
```

에 의해 뒷받침되어야 합니다.

---

# Roadmap Grounding Test

Roadmap의 단계와 일정이
공식 정보에서 벗어나지 않는지 확인합니다.

특히:

```text
처리 기간

마감일

신청 시기

입국 기한
```

을 임의로 생성하지 않는지 확인합니다.

---

# Source Test

최종 Response에 포함된 Source는 최소 다음을 유지해야 합니다.

```text
official_agency

source_title

source_url

verified_at
```

가능하면:

```text
original_updated_at

effective_from

effective_until
```

도 유지합니다.

---

# Source URL Test

다음과 같은 URL을 생성하지 않는지 확인합니다.

```text
LLM이 추측한 URL

존재하지 않는 URL

검색되지 않은 URL
```

Response에 표시하는 URL은
실제 저장된 Evidence URL을 사용합니다.

---

# 테스트 데이터

테스트용 데이터는
실제 운영 데이터와 분리할 수 있습니다.

예:

```text
tests/fixtures/
```

향후 필요하면 추가할 수 있습니다.

예상 구조:

```text
tests/
├─ fixtures/
│  ├─ users/
│  ├─ programs/
│  ├─ support_programs/
│  └─ evidence/
├─ unit/
├─ integration/
├─ scenarios/
└─ README.md
```

초기에는 필요한 시점에 추가합니다.

---

# Mock 사용

외부 LLM과 API 호출은
Unit Test에서 가능한 한 Mock을 사용합니다.

예:

```text
OpenAI API

Claude API

Embedding API
```

매 테스트마다 실제 API를 호출하면:

```text
비용 발생

응답 변동

속도 저하

Rate Limit
```

문제가 생길 수 있습니다.

---

# 실제 API Test

실제 LLM 또는 외부 Service를 사용하는 테스트는
별도 Integration / Evaluation 단계에서 수행합니다.

예:

```text
pytest marker

환경변수

별도 실행 Script
```

등으로 분리할 수 있습니다.

---

# 테스트 재현성

가능한 테스트는
동일 입력에서 동일 결과가 나와야 합니다.

특히:

```text
Rule Evaluator

Program Resolver

Metadata Filter

Evidence Validation
```

은 결정적으로 검증할 수 있어야 합니다.

---

# LLM 테스트

LLM 결과는 완전히 동일한 문자열보다
필수 조건 충족 여부를 중심으로 평가할 수 있습니다.

예:

```text
필수 Program명 포함

공식 Source 존재

잘못된 지원제도 생성 없음

Rule 결과 변경 없음
```

---

# 테스트 실행

향후 `pytest`를 사용할 수 있습니다.

예:

```bash
pytest
```

특정 디렉터리:

```bash
pytest tests/unit
```

```bash
pytest tests/integration
```

```bash
pytest tests/scenarios
```

현재 `pytest`가 개발 환경에 아직 없다면
실제 테스트 구현 시 설치합니다.

---

# 파일명 규칙

pytest 기준 예:

```text
test_rule_evaluator.py

test_program_resolver.py

test_retrieval.py

test_agent_routing.py

test_chat_api.py
```

---

# Test Function 이름

예:

```python
def test_age_requirement_pass():
    ...
```

```python
def test_missing_career_is_not_failed_requirement():
    ...
```

```python
def test_support_program_is_separate_from_program():
    ...
```

이름만 보고 어떤 행동을 검증하는지
알 수 있도록 작성합니다.

---

# 최소 Scenario 수

초기 MVP에서는
국가 × 상위 진출 경로별 대표 Scenario를 우선 구성합니다.

```text
5개 국가
×
3개 상위 진출 경로
```

에 대해 기본 Scenario를 만들고,
각 Scenario에 여러 사용자 Profile을 추가하여 확장할 수 있습니다.

예:

```text
조건 충족 사용자

조건 미충족 사용자

정보 부족 사용자

예외 규정 사용자
```

---

# 60개 Scenario 구성 예시

초기 테스트 목표를 60개 정도로 잡는다면:

```text
15개 국가 × 경로 조합
×
4개 상태
```

형태로 구성할 수 있습니다.

예:

```text
조건 충족

조건 미충족

정보 부족

추가 확인 필요
```

즉:

```text
5 countries
×
3 top-level paths
×
4 user conditions
=
60 scenarios
```

실제 테스트 수는
Program과 데이터 수집 결과에 맞춰 조정합니다.

---

# Scenario ID

각 Scenario에는
식별 가능한 ID를 둘 수 있습니다.

예:

```text
DE_EMP_001

DE_EMP_002

CA_STUDY_001

JP_WH_001
```

예상 규칙:

```text
국가
+
경로
+
번호
```

---

# Expected Result 저장

Scenario마다 예상 결과를
JSON 또는 YAML 형태로 관리할 수 있습니다.

예:

```json
{
  "scenario_id": "DE_EMP_001",
  "expected": {
    "intent": "employment",
    "country": "Germany",
    "eligibility_status": "조건 충족"
  }
}
```

실제 구조는 Agent Output Schema가 확정된 뒤 결정합니다.

---

# 테스트 실패 분류

테스트 실패를 다음처럼 분류할 수 있습니다.

```text
DATA_ERROR

RULE_ERROR

RETRIEVAL_ERROR

EVIDENCE_ERROR

ROUTING_ERROR

LLM_ERROR

API_ERROR

UI_ERROR
```

이를 통해 원인을 빠르게 구분할 수 있습니다.

---

# MVP 핵심 테스트 우선순위

초기에는 모든 테스트를 동일하게 만들기보다
다음 순서로 우선합니다.

```text
1. Rule Evaluator

2. Program Resolver

3. Program / SupportProgram 분리

4. Missing Information 처리

5. Retrieval

6. Evidence Validation

7. Agent Routing

8. FastAPI Integration

9. Scenario Test

10. Frontend Integration
```

---

# 테스트에서 반드시 방지할 오류

```text
없는 비자를 추천

없는 지원사업을 추천

한국인 적용이 확인되지 않은 지원사업을 확정 추천

사용자 정보 부족을 조건 미충족으로 판단

조건 미충족을 정보 부족으로 판단

Rule Evaluator 결과를 LLM이 변경

과거 / 다른 국가 공식 문서를 현재 근거로 사용

Eligibility와 현재 신청 가능 여부 혼동

비자 발급 가능성을 확정적으로 표현

지원제도 최종 선정을 확정적으로 표현

확인되지 않은 날짜 생성

잘못된 공식 URL 제공
```

---

# 구현 원칙

- Unit Test는 가능한 한 결정적으로 구성
- Rule Evaluator는 LLM 없이 테스트 가능해야 함
- Program과 SupportProgram을 별도로 검증
- Missing Information과 Failed Requirement를 구분
- Eligibility와 Application Availability를 구분
- Retrieval Result와 Validated Evidence를 구분
- Agent 내부 역할 분리를 검증
- 필요한 Agent만 호출되는지 확인
- 공식 Evidence와 Final Answer 일치 여부 검증
- Hallucination을 핵심 실패 조건으로 취급
- 실제 API 호출은 Unit Test에서 최소화
- Scenario Test는 실제 사용자 흐름을 반영

---

# 개발 순서

현재 예상 테스트 구현 순서는 다음과 같습니다.

```text
1. pytest 환경 구성

2. Model Validation Test

3. Rule Evaluator Unit Test

4. Program Resolver Unit Test

5. Metadata Filter Test

6. Evidence Validation Test

7. Service Test

8. Agent 개별 Integration Test

9. Agent Routing Test

10. FastAPI Integration Test

11. Session / Multi-turn Test

12. 국가 × 경로 기본 Scenario 작성

13. 조건 충족 / 미충족 / 정보 부족 / 추가 확인 Scenario 확장

14. Retrieval / Evidence Grounding 평가

15. Frontend Integration Test

16. Demo 전 End-to-End 검증
```

---

# 현재 상태

현재 다음 기본 테스트 디렉터리가 생성되어 있습니다.

```text
tests/unit/

tests/integration/

tests/scenarios/
```

아직 실제 Test Case 구현 전 단계이며,
Agent Skeleton, DB Schema, Rule Evaluator, Retrieval 구조가 구현되는 순서에 맞춰
테스트를 함께 추가합니다.

특히 초기 구현에서는:

```text
Rule Evaluator

Program Resolver

Missing Information

Program / SupportProgram 분리

Evidence Validation
```

관련 테스트를 우선 작성합니다.

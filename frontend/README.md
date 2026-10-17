# frontend

Global-In의 Streamlit 기반 사용자 인터페이스를 구현하는 디렉터리입니다.

사용자는 Frontend를 통해 자신의 해외 진출 목적과 현재 상황을 입력하고,
Global-In이 추천한 진출 경로, 실제 Program, SupportProgram, 자격 검토 결과,
공식 근거, Checklist, Roadmap 등을 확인합니다.

Frontend는 Agent 내부 로직을 직접 수행하지 않고,
FastAPI를 통해 Backend와 통신하는 역할에 집중합니다.

---

## 주요 역할

`frontend/`는 다음 역할을 담당합니다.

```text
사용자 입력

대화형 Chat UI

UserProfile 관련 입력

추가 질문 표시

진출 경로 추천 결과 표시

Program 정보 표시

SupportProgram 정보 표시

Eligibility 결과 표시

공식 Evidence 표시

Checklist 표시

Roadmap 표시

Backend API 호출

오류 / Loading 상태 표시
```

---

## 전체 구조에서의 위치

```text
User
  ↓
Streamlit
  ↓
FastAPI
  ↓
LangGraph Orchestrator
  ↓
5개 Agent
  ↓
Backend Result
  ↓
FastAPI
  ↓
Streamlit
  ↓
User
```

Frontend는 Backend 내부 Agent를 직접 Import하여 사용하지 않고,
HTTP API를 통해 통신하는 구조를 기본으로 합니다.

---

## 현재 파일

현재 기본 Streamlit Entry Point는 다음과 같습니다.

```text
frontend/app.py
```

현재 초기 화면은 다음 역할을 수행합니다.

```text
Page 설정

서비스 제목 표시

서비스 설명 표시

Frontend 실행 확인
```

---

## 현재 기본 코드

초기 구조는 다음과 같습니다.

```python
import streamlit as st

st.set_page_config(
    page_title="Global-In",
    page_icon="🌍"
)

st.title("Global-In")
st.write("해외 진출 경로 탐색 AI 서비스")

st.success("Frontend is running")
```

실제 개발 과정에서 Chat UI와 결과 표시 영역을 추가합니다.

---

## 예상 파일 구조

초기 MVP에서는 `app.py` 중심으로 시작할 수 있습니다.

서비스 규모가 커지면 다음과 같은 구조를 고려합니다.

```text
frontend/
├─ app.py
├─ components/
│  ├─ chat.py
│  ├─ profile.py
│  ├─ recommendation.py
│  ├─ eligibility.py
│  ├─ support_program.py
│  ├─ evidence.py
│  ├─ checklist.py
│  └─ roadmap.py
├─ api_client.py
├─ state.py
└─ README.md
```

초기부터 불필요하게 많은 파일로 분리하지 않고,
UI가 복잡해지는 시점에 Component를 분리합니다.

---

# 기본 사용자 흐름

대표적인 사용자 흐름은 다음과 같습니다.

```text
서비스 진입
   ↓
사용자 질문 입력
   ↓
Backend 요청
   ↓
추가 정보 필요?
   │
   ├─ YES
   │   ↓
   │ 추가 질문 표시
   │   ↓
   │ 사용자 답변
   │   ↓
   │ Backend 재요청
   │
   └─ NO
       ↓
진출 경로 / Program 결과
       ↓
자격 검토 결과
       ↓
지원제도
       ↓
공식 정보 / Evidence
       ↓
Checklist
       ↓
Roadmap
```

---

# Chat UI

Global-In은 기본적으로
대화형 인터페이스를 중심으로 구성합니다.

예:

```text
User:
독일로 취업하고 싶어.

Global-In:
현재 전공과 관련 경력을 알려주세요.

User:
컴퓨터공학 전공이고 관련 경력은 2년이에요.

Global-In:
조건을 바탕으로 확인한 결과...
```

Streamlit의 Chat Component를 활용할 수 있습니다.

예:

```python
st.chat_message(...)
st.chat_input(...)
```

---

# Backend API 연결

Frontend는 FastAPI와 HTTP로 통신합니다.

예:

```text
Streamlit
   ↓
POST /chat
   ↓
FastAPI
```

Request 예:

```json
{
  "message": "독일로 취업하고 싶어요.",
  "session_id": "example-session"
}
```

Response 예:

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

실제 Schema는 Backend `app/models/`와 맞춥니다.

---

# API Client

Frontend에서 API 호출 코드가 복잡해질 경우
별도 파일로 분리할 수 있습니다.

예:

```text
frontend/api_client.py
```

예상 역할:

```text
FastAPI Base URL 관리

POST /chat 호출

Timeout 처리

Error 처리

Response Parsing
```

예:

```python
def send_chat_message(
    message: str,
    session_id: str | None = None
):
    ...
```

---

# Session 관리

Global-In은 여러 Turn에 걸쳐
사용자 Profile을 보완할 수 있습니다.

따라서 Frontend에서도
현재 Session을 유지해야 할 수 있습니다.

Streamlit에서는:

```text
st.session_state
```

를 사용할 수 있습니다.

---

## 예상 Session 정보

예:

```text
session_id

messages

user_profile

selected_program

selected_support_programs

last_response
```

실제 저장 범위는 Backend 구현 방식에 맞춰 결정합니다.

---

## Session 예시

```python
if "messages" not in st.session_state:
    st.session_state.messages = []
```

사용자가 페이지를 사용하는 동안
대화 내용을 유지할 수 있습니다.

---

# 5개 Agent 결과 표시

Frontend에서는 Agent 내부 구조를
사용자에게 그대로 노출할 필요는 없습니다.

하지만 각 Agent가 생성한 결과를
적절한 UI로 표현할 수 있습니다.

---

## 사용자 이해 에이전트 결과

사용자가 직접 볼 수 있는 대표 결과:

```text
추가 질문

확인된 사용자 조건

현재 목적
```

예:

```text
현재 확인된 정보

희망 국가: 독일
목적: 취업
전공: 컴퓨터공학
경력: 2년
```

모든 내부 State를 그대로 노출하지 않습니다.

---

## 진출 경로 탐색·추천 에이전트 결과

UI에서 다음을 표시할 수 있습니다.

```text
추천 국가

추천 경로

실제 Program 후보

추천 이유

비교 정보
```

예:

```text
추천 경로

1. Program A
2. Program B
3. Program C
```

각 Program은 Card 형태로 표시할 수 있습니다.

---

# Program 표시

Program Card에서는 다음 정보를 보여줄 수 있습니다.

```text
Program 이름

국가

진출 목적

간단 설명

Eligibility 상태

신청 가능 상태

주요 조건

공식 출처
```

예:

```text
독일 취업 관련 Program A

자격 상태:
조건 충족

현재 신청 상태:
추가 확인 필요
```

---

# SupportProgram 표시

지원제도는 Program과 구분해서 표시합니다.

예:

```text
관련 지원제도

한국 측 지원
- SupportProgram A

독일 측 지원
- SupportProgram B
```

각 Card에는 다음 정보를 표시할 수 있습니다.

```text
지원제도명

운영기관

지원 내용

대상

Eligibility

Application Availability

공식 출처
```

---

# Program과 SupportProgram UI 구분

Program과 SupportProgram을
같은 목록에서 구분 없이 표시하지 않습니다.

예:

```text
진출 경로
────────────
Program A

지원제도
────────────
SupportProgram A
SupportProgram B
```

이렇게 역할을 분리합니다.

---

# Eligibility 표시

기본 상태:

```text
조건 충족

조건 미충족

추가 확인 필요
```

UI에서는 상태와 함께
조건별 상세 내용을 보여줄 수 있습니다.

예:

```text
자격 검토

국적
→ 조건 충족

학력
→ 조건 충족

경력
→ 조건 미충족

예외 규정
→ 추가 확인 필요
```

---

## Missing Information 표시

사용자 정보가 부족한 경우:

```text
조건 미충족
```

으로 표시하지 않습니다.

대신:

```text
추가 정보 필요
```

또는:

```text
추가 확인 필요
```

처럼 표시합니다.

예:

```text
경력 정보가 필요합니다.
```

---

# Eligibility와 Application Availability 구분

Frontend에서도 두 상태를 분리해서 보여줍니다.

좋은 예:

```text
자격 상태
→ 조건 충족

현재 신청 상태
→ 모집 여부 확인 필요
```

좋지 않은 예:

```text
신청 가능
```

하나의 문구로 합쳐 표시

---

# 공식 정보 표시

공식 정보 안내 에이전트의 결과를
사용자가 쉽게 이해할 수 있도록 정리합니다.

예:

```text
근로 조건

체류 기간

신청 절차

주의사항

예외 사항
```

공식 규정과 AI의 설명을 가능하면 구분하여 표시합니다.

---

# Evidence 표시

사용자에게 출처를 확인할 수 있도록
Evidence 정보를 제공합니다.

기본 정보:

```text
공식 기관

문서 제목

원문 URL

원문 수정일

Global-In 확인일
```

예:

```text
출처

기관:
Example Immigration Authority

문서:
Official Visa Guide

확인일:
2026-10-17
```

---

## Source Link

공식 원문 URL은
사용자가 직접 열어볼 수 있도록 제공합니다.

예:

```python
st.link_button(...)
```

또는 Markdown Link를 사용할 수 있습니다.

---

## 날짜 표시

가능하면 다음을 구분합니다.

```text
원문 게시일

원문 수정일

적용 기간

Global-In 확인일
```

모든 날짜가 존재하는 것은 아니므로,
없는 값을 임의로 표시하지 않습니다.

---

# 공식 정보와 AI 설명 구분

예:

```text
공식 기준
────────────
공식 문서에 따르면 ...

AI 안내
────────────
현재 조건을 기준으로 보면 ...
```

이렇게 구분할 수 있습니다.

초기 MVP에서는 디자인을 단순하게 유지하되,
사용자가 AI 해석을 공식 규정으로 오해하지 않도록 합니다.

---

# Checklist 표시

준비 계획 에이전트가 생성한 Checklist를 표시합니다.

상태:

```text
완료

준비 필요

추가 확인
```

예:

```text
[완료] 여권 확인

[준비 필요] 학력 증명서 준비

[추가 확인] 재정 증빙 기준 확인
```

---

## Checklist 구분

비자와 지원제도 항목을 구분할 수 있습니다.

예:

```text
비자 준비
────────────
여권
학력 증명서
경력 증명서

지원제도 준비
────────────
신청서
재학 증명서
중복 수혜 확인
```

---

# Roadmap 표시

사용자의 현재 상황을 기준으로
단계별 Roadmap을 보여줍니다.

예:

```text
1단계
자격 확인

2단계
필수 서류 준비

3단계
지원제도 신청

4단계
비자 / Program 신청

5단계
승인 후 준비

6단계
출국 준비

7단계
입국 후 절차
```

---

## Roadmap의 날짜

확인되지 않은 날짜를
Frontend에서 임의로 생성하지 않습니다.

예:

```text
신청 마감일:
확인 필요
```

처럼 표시할 수 있습니다.

---

# Loading 상태

LLM, Retrieval, Database 호출에는
응답 시간이 필요할 수 있습니다.

따라서 사용자에게
현재 처리 중임을 보여주는 UI를 제공합니다.

예:

```python
with st.spinner("공식 정보를 확인하고 있습니다..."):
    ...
```

---

## Loading 문구 예

```text
사용자 조건을 확인하고 있습니다.

진출 경로를 비교하고 있습니다.

공식 자료를 확인하고 있습니다.

준비 계획을 구성하고 있습니다.
```

Agent 내부 구현 세부사항을
지나치게 노출할 필요는 없습니다.

---

# Error UI

Backend 오류가 발생했을 때
Internal Stack Trace를 그대로 보여주지 않습니다.

예:

```text
현재 요청을 처리하지 못했습니다.
잠시 후 다시 시도해주세요.
```

필요한 경우:

```text
다시 시도
```

기능을 제공할 수 있습니다.

---

# 공식 근거 부족 상태

공식 Evidence가 부족한 경우
UI에서도 확정적인 결과처럼 표시하지 않습니다.

예:

```text
추가 확인 필요

현재 확인된 공식 근거만으로
확정적인 안내가 어렵습니다.
```

---

# Empty State

아직 결과가 없는 경우:

```text
궁금한 해외 진출 경로를 입력해 주세요.
```

예시 질문을 제공할 수 있습니다.

예:

```text
독일로 취업하고 싶어요.

일본 워킹홀리데이를 준비하고 있어요.

캐나다 유학을 생각하고 있어요.

해외 취업 지원금을 받을 수 있는지 궁금해요.
```

---

# 입력 UI

초기에는 Chat Input 중심으로 구성합니다.

필요한 경우 일부 Profile 정보를
Form 형태로 받을 수 있습니다.

예:

```text
희망 국가

진출 목적

나이

학력

경력

언어
```

다만 처음부터 긴 Form을 강제하지 않고,
대화 과정에서 필요한 정보만 질문하는 방식을 우선합니다.

---

# Profile 표시

사용자가 원할 경우
현재 확인된 Profile을 보여줄 수 있습니다.

예:

```text
현재 조건

국적
대한민국

희망 국가
독일

목적
취업

전공
컴퓨터공학

경력
2년
```

사용자가 잘못된 정보를 수정할 수 있는 UI는
향후 추가할 수 있습니다.

---

# Recommendation 비교 UI

여러 Program 후보를 비교할 때
Table이나 Card를 사용할 수 있습니다.

예:

| Program | Eligibility | 신청 상태 | 주요 특징 |
|---|---|---|---|
| Program A | 조건 충족 | 확인 필요 | 경력 중심 |
| Program B | 조건 미충족 | OPEN | 학위 조건 필요 |

실제 표시 항목은
Program Schema에 맞춰 조정합니다.

---

# 지원제도 비교 UI

예:

| SupportProgram | 운영기관 | Eligibility | 모집 상태 |
|---|---|---|---|
| Support A | 기관 A | 조건 충족 | OPEN |
| Support B | 기관 B | 추가 확인 필요 | UNKNOWN |

Eligibility와 모집 상태를
반드시 별도로 표시합니다.

---

# 국가별 UI 분리

일본, 호주, 미국, 독일, 캐나다를
완전히 다른 Frontend 코드로 구현하지 않습니다.

예:

```text
JapanPage

GermanyPage

CanadaPage
```

처럼 국가별 별도 화면을 만드는 것보다,
공통 Component가 데이터에 따라 렌더링되도록 구성합니다.

---

# Streamlit State

`st.session_state`를 사용하여
화면 상태를 관리할 수 있습니다.

예상 항목:

```text
session_id

messages

current_response

selected_program

expanded_sections
```

Backend의 AgentState 전체를
Frontend Session에 복제하지 않습니다.

---

# Backend State와 Frontend State 구분

### Backend State

```text
UserProfile

Intent

Candidate Programs

Eligibility Results

Evidence

Checklist

Roadmap
```

### Frontend State

```text
현재 대화 메시지

선택된 UI Tab

펼쳐진 Card

현재 Session ID
```

비즈니스 상태는 Backend가 관리하는 것을 기본으로 합니다.

---

# 보안

Frontend 코드에
API Key를 직접 작성하지 않습니다.

예:

```text
OPENAI_API_KEY
```

를 Streamlit 코드에 Hard Coding하지 않습니다.

Frontend는 FastAPI만 호출하고,
LLM Key는 Backend에서 관리합니다.

---

# FastAPI 주소 관리

초기 개발 환경에서는 예:

```text
http://127.0.0.1:8000
```

을 사용할 수 있습니다.

운영 환경에서는 환경변수나
Streamlit Secret 등을 이용해 관리할 수 있습니다.

예:

```text
API_BASE_URL
```

실제 관리 방식은 배포 구조 확정 후 결정합니다.

---

# Timeout

Frontend HTTP Request에도
적절한 Timeout을 설정합니다.

Backend 응답이 없을 때
페이지가 무한 대기하지 않도록 합니다.

---

# Retry

사용자가 직접 재시도할 수 있도록 하는 것이
초기 MVP에서는 단순하고 안전합니다.

자동 Retry는
중복 요청이나 중복 Agent 실행을 유발할 수 있으므로
필요성을 확인한 뒤 추가합니다.

---

# Streaming

초기 MVP에서는
일반 Response 방식으로 시작합니다.

향후 필요하다면:

```text
LLM Streaming
   ↓
FastAPI SSE / StreamingResponse
   ↓
Streamlit
```

구조를 검토할 수 있습니다.

기본 Chat Workflow가 안정된 뒤 추가합니다.

---

# 화면 구성 예시

초기 MVP는 다음 정도의 구조로 구성할 수 있습니다.

```text
┌───────────────────────────────┐
│          🌍 Global-In          │
├───────────────────────────────┤
│                               │
│ Chat History                  │
│                               │
│ User Message                  │
│ AI Response                   │
│                               │
├───────────────────────────────┤
│ 추천 진출 경로                │
│ Program Cards                 │
├───────────────────────────────┤
│ 관련 지원제도                 │
│ SupportProgram Cards          │
├───────────────────────────────┤
│ 자격 검토                     │
│ Eligibility Results           │
├───────────────────────────────┤
│ 준비 Checklist                │
├───────────────────────────────┤
│ Roadmap                       │
├───────────────────────────────┤
│ 공식 출처                     │
├───────────────────────────────┤
│ 질문 입력                     │
└───────────────────────────────┘
```

실제 UI는 결과가 많아질 수 있으므로
Expander나 Tab을 활용할 수 있습니다.

---

# Tab 구성 예시

예:

```text
추천 경로

자격 검토

지원제도

준비 계획

공식 출처
```

다만 초기 MVP에서 Tab이 반드시 필요한 것은 아닙니다.

---

# Expander 활용

세부 내용을 접어서 보여줄 수 있습니다.

예:

```python
with st.expander("자격 조건 상세"):
    ...
```

또는:

```python
with st.expander("공식 출처 보기"):
    ...
```

---

# Mobile 고려

Streamlit 기반 Demo이므로
초기에는 Desktop 중심으로 개발하되,
너무 넓은 고정 Layout은 피합니다.

Table이 지나치게 넓어지는 경우
Card나 세로 구조를 사용할 수 있습니다.

---

# 접근성

가능한 한 다음을 고려합니다.

```text
상태를 색상만으로 구분하지 않음

텍스트 Label 사용

링크 목적 명확히 표시

너무 작은 글자 사용하지 않음
```

예:

```text
🟢 조건 충족

🔴 조건 미충족

🟡 추가 확인 필요
```

처럼 색상과 문구를 함께 사용할 수 있습니다.

---

# 초기 MVP UI 우선순위

초기에는 다음 기능을 우선 구현합니다.

```text
1. Chat Input

2. Chat History

3. FastAPI 연결

4. Follow-up Question

5. Program 추천 표시

6. Eligibility 결과 표시

7. SupportProgram 표시

8. Evidence / Source 표시

9. Checklist 표시

10. Roadmap 표시
```

디자인 고도화는
기능 연결 이후 진행합니다.

---

# 구현하지 않는 기능

초기 MVP Frontend에서는 다음을 우선 제외합니다.

```text
실시간 채용공고 UI

항공권 검색 UI

실시간 환율 UI

주거 추천 UI

Map UI

지역 Community UI

생활비 계산기 UI

실제 비자 신청 제출 UI
```

Backend MVP 범위와 동일하게 유지합니다.

---

# API 연결 테스트

Frontend에서 최소 다음을 확인합니다.

```text
FastAPI 연결 성공

POST /chat 요청 성공

Response Parsing 성공

Error 상태 표시

Timeout 처리

Session ID 유지
```

---

# UI 테스트 포인트

```text
추가 질문이 정상적으로 표시되는가

Program과 SupportProgram이 구분되는가

Eligibility와 Application Availability가 구분되는가

조건 미충족과 정보 부족이 구분되는가

공식 Source가 표시되는가

URL을 직접 확인할 수 있는가

Checklist 상태가 구분되는가

Roadmap 순서가 정상적인가

Evidence가 없는 내용을 확정적으로 표시하지 않는가

Backend 오류가 사용자에게 Stack Trace로 노출되지 않는가
```

---

# Integration Test 예시

### 추가 질문

```text
User Input
   ↓
Streamlit
   ↓
POST /chat
   ↓
FastAPI
   ↓
사용자 이해 에이전트
   ↓
Follow-up Question
   ↓
FastAPI
   ↓
Streamlit
```

---

### 추천 결과

```text
User Input
   ↓
Backend
   ↓
Program Recommendation
   ↓
SupportProgram
   ↓
Eligibility
   ↓
Streamlit Card
```

---

### 공식 정보

```text
User Question
   ↓
Backend Retrieval
   ↓
Evidence
   ↓
FastAPI Response
   ↓
Frontend Source Section
```

---

# 개발 순서

```text
1. 현재 기본 Streamlit 화면 유지

2. Chat UI 구현

3. Session State 구현

4. API Client 구현

5. FastAPI /chat 연결

6. Follow-up Question 표시

7. Program 결과 UI 구현

8. Eligibility 결과 UI 구현

9. SupportProgram UI 구현

10. Evidence / Source UI 구현

11. Checklist UI 구현

12. Roadmap UI 구현

13. Error / Loading 상태 구현

14. Integration Test

15. Demo용 UI 정리
```

---

# 구현 원칙

- Frontend에서 Agent 내부 로직을 구현하지 않음
- FastAPI를 통해 Backend와 통신
- Program과 SupportProgram을 구분해서 표시
- Eligibility와 Application Availability를 구분
- Missing Information과 조건 미충족을 구분
- 공식 출처를 사용자가 확인할 수 있도록 표시
- 확인되지 않은 일정이나 상태를 임의로 표시하지 않음
- Agent 내부 State 전체를 사용자에게 노출하지 않음
- 국가별 UI Hard Coding을 최소화
- 기능 구현 후 디자인을 고도화
- API Key를 Frontend 코드에 직접 작성하지 않음

---

# 현재 상태

현재는 Streamlit 기본 실행 환경이 구성되어 있으며,
다음 화면이 정상적으로 실행되는 상태입니다.

```text
🌍 Global-In

해외 진출 경로 탐색 AI 서비스

Frontend is running
```

다음 구현 단계에서는 FastAPI의 Chat Endpoint와 연결하여:

```text
사용자 질문 입력

추가 질문

Program 추천

SupportProgram

Eligibility

Evidence

Checklist

Roadmap
```

을 하나의 대화형 UI에서 확인할 수 있도록 구현합니다.

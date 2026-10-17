# app/rules

Global-In의 자격 요건 검토 및 Rule 기반 판정 기능을 구현하는 디렉터리입니다.

비자·체류 프로그램과 국내외 지원제도의 공식 자격 요건을 사용자의 조건과 비교하여,
각 항목의 충족 여부와 추가 확인이 필요한 조건을 판정합니다.

명확하게 구조화할 수 있는 조건은 LLM이 임의로 판단하지 않고
Python 기반 Rule Evaluator가 처리합니다.

---

## 주요 역할

`app/rules/`는 다음 역할을 담당합니다.

```text
User Profile
   +
Program / Support Program Requirements
   ↓
Rule Evaluator
   ↓
조건별 비교
   ↓
Eligibility Result
```
기본 판정 상태는 다음 세 가지입니다.
```
조건 충족
조건 미충족
추가 확인 필요
```

---

## 검토 대상

Global-In에서는 크게 두 종류의 자격을 구분하여 검토합니다.

### 1. 비자·체류 프로그램 자격
예:
```
국적
연령
학력
전공
경력
언어
재정 조건
체류 자격
기타 공식 요건
```

### 지원제도 신청 자격
예:
```
국적
현재 거주지
재학 여부
취업 상태
학력
경력
연령
기존 참여 이력
기존 수혜 이력
중복 수혜 제한
기타 사업별 조건
```

**비자 자격과 지원제도 자격은 서로 다른  결과로 관리합니다.**

---

## Rule Evaluator

Rule Evaluator는 사용자 Profile과 공식 요건을 비교합니다.

예:
```
Program Requirement
age <= 30

User Profile
age = 27

Result
조건 충족
```
또는
```
Program Requirement
career >= 2 years

User Profile
career = 1 year

Result
조건 미충족
```

---

## 구조화 가능 조건

다음과 같이 명확하게 비교할 수 있는 조건은 Rule 기반으로 처리합니다.
```
연령
국적
거주지
학력
경력 연수
언어 점수
재정 기준
재학 여부
취업 상태
참여 이력
수혜 이력
```

예상 Rule 표현:
```
{
  "field": "age",
  "operator": "<=",
  "value": 30,
  "required": true
}
```
또는 
```
{
  "field": "career_years",
  "operator": ">=",
  "value": 2,
  "required": true
}
```

---

## 구조화하기 어려운 조건

공식 요건 중에는 단순 비교만으로 판단하기 어려운 조건이 있을 수 있습니다.

예:
```
예외 조항이 존재하는 경우
기관의 별도 판단이 필요한 경우
법률 해석이 필요한 경우
조건 설명이 모호한 경우
공식 근거가 서로 충돌하는 경우
사용자 정보가 부족한 경우
```
이 경우 자동으로 충족 또는 미충족으로 확정하지 않습니다.  `추가 확인 필요` 상태로 처리합니다.

---

## 사용자 정보 부족과 조건 미충족 구분

다음 두 상황은 반드시 구분합니다.

### 1. 사용자 정보 부족
예:
```
조건:
경력 2년 이상

사용자:
경력 정보 없음
```
결과:
```
추가 정보 필요
```
사용자 이해 영역에서 필요한 정보를 추가로 질문합니다.


### 2. 조건 미충족
예:
```
조건:
경력 2년 이상

사용자:
경력 1년
```
결과:
```
조건 미충족
```
이미 확인된 사용자 정보가 공식 조건을 충족하지 못하는 상황입니다.

---

## 신청 자격과 실제 승인 구분

Rule Evaluator의 결과는 실제 비자 발급이나 지원제도 최종 선정 결과를 의미하지 않습니다.
Global-In에서 확인하는 것은 다음과 같습니다.
```
공개된 공식 요건을 기준으로
현재 사용자가 해당 요건을 충족하는가?
```
따라서:
```
조건 충족
≠
비자 발급 확정

조건 충족
≠
지원사업 최종 선정 확정
```
입니다. 

최종 결정 권한은 해당 국가의 관할 기관이나 지원사업 운영기관에 있습니다.

---

## 신청 자격과 현재 신청 가능 여부 구분

다음 두 정보도 구분합니다.
```
Eligibility
→ 사용자가 신청 요건을 충족하는가?

Application Availability
→ 현재 실제 접수 기간인가?
```
사용자가 요건을 충족하더라도 현재 접수 기간이 아닐 수 있습니다.

현재 접속 여부를 공식적으로 확인하지 못한 경우 신청 가능하다고 단정하지 않습니다.

---

## 예상 결과 구조

Rule Evaluator는 각 조건별 결과를 구조화하여 반환합니다.

예:
```
{
  "status": "추가 확인 필요",
  "passed_conditions": [
    "nationality",
    "education"
  ],
  "failed_conditions": [],
  "uncertain_conditions": [
    "age_exception"
  ]
}
```
필요한 경우 비자와 지원제도 결과를 각각 분리합니다.

예:
```
Visa Eligibility
   ├─ nationality: 조건 충족
   ├─ age: 추가 확인 필요
   └─ career: 조건 충족

Support Program Eligibility
   ├─ residence: 조건 충족
   ├─ employment_status: 조건 미충족
   └─ previous_participation: 추가 확인 필요
```

---

## 공식 근거와의 연결

Rule은 반드시 공식 근거와 연결할 수 있어야 합니다.

예:
```
Rule
age <= 30
   ↓
Evidence
공식 기관의 연령 요건 안내
```
최종 사용자 응답에서는 가능한 경우 판정 결과와 함께 해당 조건의 공식 출처를 제공합니다.

---

## 예상 파일 구조
```
app/rules/
├─ __init__.py
├─ evaluator.py
├─ conditions.py
├─ operators.py
├─ result.py
└─ README.md
```
실제 파일 구조는 구현 과정에서 변경될 수 있습니다.


### evaluator.py

Rule Evaluator의 핵심 실행 로직을 구현합니다.

담당:
```
User Profile 입력
공식 Requirement 입력
조건별 비교
전체 상태 계산
Eligibility Result 반환
```


### conditions.py

자격 조건의 구조 및 처리 방식을 정의합니다.

예:
```
age
nationality
education
career
language
financial
residence
employment_status
participation_history
```


### operators.py

조건 비교에 사용하는 연산을 관리합니다.

예:
```
==
!=
>
>=
<
<=
IN
NOT IN
```
조건 종류에 따라 별도 비교 로직이 추가될 수 있습니다.


### result.py

Rule 평가 결과를 생성하거나 정리하는 기능을 담당합니다.

예:
```
passed
failed
uncertain
missing
```
실제 Result Schema는 `app/models/`와 연결합니다.

---

## 다른 모듈과의 관계
```
User Profile
   ↓
app/models

Program / Support Program
   ↓
PostgreSQL

        ↓

app/rules
Rule Evaluator

        ↓

Eligibility Result

        ↓

Agent / Response Generator
```
Rule Evaluator는 최종 자연어 답변을 생셩하지 않습니다.

판정 결과를 구조화하여 반환하고, AI는 해당 결과를 사용자에게 이해하기 쉽게 설명합니다.

---

## Retrieval과의 관계

Rule Evaluator는 구조화된 공식 조건을 이용해 판정합니다.

반면 공식 문서의 상세 설명이나 예외 규정이 필요한 경우 Retrieval을 통해 원문 근거를 확인합니다.
```
Structured Rule
   ↓
Rule Evaluator

Official Document / Exception
   ↓
Retrieval
```
예외 규정 또는 충돌하는 정보가 발견되면 Rule Evaluator 결과를 임의로 확정하지 않고 `추가 확인 필요` 상태를 사용할 수 있습니다.

---

## 구현 원칙
- 구조화 가능한 조건은 Python Rule로 처리
- LLM이 공식 자격 조건을 임의로 변경하지 않음
- 비자 자격과 지원제도 자격을 구분
- 사용자 정보 부족과 조건 미충족을 구분
- 신청 자격과 현재 접수 가능 여부를 구분
- 자격 검토 결과와 최종 승인 결과를 구분
- 예외 및 불확실한 조건은 추가 확인 필요 처리
- 각 Rule은 가능한 한 공식 Evidence와 연결
- 특정 국가만을 위한 하드코딩 최소화
- 동일한 Rule Engine을 여러 국가와 프로그램에서 재사용할 수 있도록 설계

---

## 개발 순서
```
1. Requirement Schema 정의
2. 기본 Operator 구현
3. 단일 조건 평가 구현
4. 복수 조건 평가 구현
5. Missing Information 처리
6. Eligibility Result 생성
7. 비자 / 지원제도 결과 구분
8. Evidence 연결
9. Agent 연결
10. Scenario Test
```

---

## 테스트 포인트
```
정상 조건을 정확히 판정하는가
조건 미충족을 정확히 판정하는가
사용자 정보 부족을 구분하는가
예외 조건을 무리하게 확정하지 않는가
비자와 지원제도 자격을 구분하는가
현재 신청 가능 여부와 자격을 혼동하지 않는가
공식 근거와 Rule이 올바르게 연결되는가
```

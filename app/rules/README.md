# app/rules

Global-In의 구조화된 자격 조건을 판정하는 Rule Evaluator를 구현하는 디렉터리입니다.

비자·체류 Program 및 국내외 SupportProgram의 공식 자격 요건 중
명확하게 구조화할 수 있는 조건을 Python 코드로 비교합니다.

LLM이 자격 조건을 임의로 해석하거나 판정하지 않도록 하며,
공식적으로 확인된 조건과 UserProfile을 기준으로
일관된 Eligibility Result를 생성하는 것이 목적입니다.

---

## 주요 역할

`app/rules/`는 다음 역할을 담당합니다.

```text
공식 Eligibility Requirement 입력
   ↓
UserProfile 입력
   ↓
Rule Evaluation
   ↓
조건별 판정
   ↓
Eligibility Result 생성
```

기본 판정 상태는 다음과 같습니다.

```text
조건 충족
조건 미충족
추가 확인 필요
```

---

## 전체 구조에서의 위치

Global-In의 자격 검토 흐름은 다음과 같습니다.

```text
사용자
   ↓
사용자 이해 에이전트
   ↓
UserProfile
   ↓
진출 경로 탐색·추천 에이전트
   ↓
Candidate Program / SupportProgram
   ↓
자격 검토 에이전트
   ↓
Rule Evaluator
   ↓
Eligibility Result
```

Rule Evaluator는 독립적인 Agent가 아니라
자격 검토 에이전트가 사용하는 공통 Module입니다.

---

## Agent와 Rule Evaluator의 역할 구분

### 자격 검토 에이전트

다음 역할을 담당합니다.

```text
검토 대상 선택

Program Eligibility 검토 요청

SupportProgram Eligibility 검토 요청

Rule Evaluator 결과 해석

부족 조건 정리

추가 확인 조건 정리

사용자에게 결과 설명
```

### Rule Evaluator

다음 역할을 담당합니다.

```text
구조화된 조건 비교

조건별 PASS / FAIL / UNKNOWN 판정

Missing Information 탐지

자동 판단 가능 여부 확인

최종 Eligibility Status 계산
```

즉:

```text
Agent
→ 무엇을 검토할지 결정하고 설명

Rule Evaluator
→ 구조화된 조건을 실제로 비교
```

로 역할을 분리합니다.

---

## Program과 SupportProgram 자격 분리

Global-In에서는 다음 두 종류의 자격을 별도로 평가합니다.

```text
Program Eligibility

SupportProgram Eligibility
```

### Program Eligibility

비자, 체류, 교환 등의 실제 해외 진출 Program에 대한 자격입니다.

예:

```text
취업 비자
학생 비자
워킹홀리데이
교환 프로그램
체류 자격
```

### SupportProgram Eligibility

해외 진출을 지원하는 별도 지원제도에 대한 자격입니다.

예:

```text
해외취업 지원금
해외 연수
취업 준비 교육
장학 지원
외국인 정착 지원
```

두 결과를 하나의 Eligibility로 합치지 않습니다.

예:

```text
Germany Employment Program
→ 조건 충족

Korean Support Program A
→ 조건 미충족

German Support Program B
→ 추가 확인 필요
```

---

## 기본 판정 상태

최종 자격 상태는 다음 세 가지를 기본으로 사용합니다.

```text
조건 충족
조건 미충족
추가 확인 필요
```

---

## 조건 충족

필수 조건이 모두 확인되었고,
구조화 가능한 공식 요건을 만족한 경우입니다.

예:

```text
공식 조건:
age <= 30

사용자:
age = 27

결과:
조건 충족
```

---

## 조건 미충족

사용자 정보가 확인되었고,
공식 필수 조건을 명확하게 충족하지 못하는 경우입니다.

예:

```text
공식 조건:
career_years >= 2

사용자:
career_years = 1

결과:
조건 미충족
```

---

## 추가 확인 필요

자동으로 확정적인 판정을 내리기 어려운 경우입니다.

예:

```text
사용자 정보 부족

예외 규정 존재

기관 판단 필요

복잡한 법률 조건

공식 근거 충돌

구조화되지 않은 조건

한국인 적용 여부 불명확

현재 조건 적용 여부 불명확
```

이 경우 LLM이 임의로 조건 충족 또는 미충족으로 변경하지 않습니다.

---

## Missing Information과 Failed Requirement 구분

Global-In에서 가장 중요하게 구분해야 하는 상태 중 하나입니다.

---

### Missing Information

공식 조건은 존재하지만
사용자의 해당 정보가 없는 경우입니다.

예:

```text
공식 조건:
career_years >= 2

사용자:
career_years = null
```

이 경우:

```text
조건 미충족
```

으로 처리하지 않습니다.

대신:

```text
missing_information = ["career_years"]
```

와 같이 반환합니다.

이후 사용자 이해 에이전트가
필요한 정보를 추가로 질문합니다.

---

### Failed Requirement

사용자 정보가 존재하지만
공식 조건을 만족하지 못하는 경우입니다.

예:

```text
공식 조건:
career_years >= 2

사용자:
career_years = 1
```

이 경우:

```text
조건 미충족
```

으로 판정합니다.

---

## 조건별 내부 상태

Rule Evaluator 내부에서는
최종 상태보다 세분화된 Condition Result를 사용할 수 있습니다.

예:

```text
PASS
FAIL
UNKNOWN
NOT_APPLICABLE
```

### PASS

공식 조건 충족

### FAIL

공식 조건 미충족

### UNKNOWN

정보 부족 또는 자동 판정 불가

### NOT_APPLICABLE

현재 사용자 또는 Program에 적용되지 않는 조건

실제 Enum 이름은 구현 단계에서 확정합니다.

---

## 예상 Eligibility Requirement 구조

예:

```json
{
  "requirement_id": "requirement_example",
  "target_type": "PROGRAM",
  "target_id": "program_example",

  "field": "career_years",
  "operator": ">=",
  "value": 2,

  "required": true,
  "judgeability": "rule_based",

  "description": "관련 분야 경력 2년 이상",
  "evidence_id": "evidence_example"
}
```

---

## 주요 Field

```text
requirement_id

target_type
target_id

field
operator
value

required

judgeability

description

evidence_id
```

---

## `target_type`

조건이 어느 대상에 속하는지 구분합니다.

예:

```text
PROGRAM
SUPPORT_PROGRAM
```

---

## `field`

UserProfile에서 비교할 항목입니다.

예:

```text
age
nationality
current_residence

education
major

career_years
career_field

language

financial_capacity

student_status
employment_status

previous_participation
previous_benefit_history
```

실제 Field는 데이터 수집 결과에 따라 확장합니다.

---

## `operator`

조건 비교 방식입니다.

예:

```text
==
!=
>
>=
<
<=

in
not_in

contains
not_contains

exists
not_exists
```

복잡한 조건은 단순 Operator로 억지로 표현하지 않습니다.

---

## `required`

필수 조건인지 선택 조건인지 구분합니다.

예:

```text
required = true
```

또는:

```text
required = false
```

필수 조건과 선택 조건의 최종 Status 반영 방식은
Rule 정책에서 명확히 정의합니다.

---

## `judgeability`

해당 조건을 자동으로 판정할 수 있는지 나타냅니다.

예:

```text
rule_based
manual_check
conditional
```

---

### `rule_based`

명확한 비교가 가능한 조건

예:

```text
age <= 30
career_years >= 2
nationality in [...]
```

---

### `manual_check`

기관 확인이나 사람의 판단이 필요한 조건

예:

```text
관련 분야로 인정되는 경력인지

특수 예외 대상인지

기관이 별도로 인정하는 자격인지
```

결과:

```text
추가 확인 필요
```

---

### `conditional`

다른 조건에 따라 적용 여부가 달라지는 경우입니다.

예:

```text
특정 학위를 가진 경우 경력 요건 완화
```

초기 MVP에서 안정적으로 구조화하기 어렵다면
무리하게 자동화하지 않고 `추가 확인 필요`로 처리합니다.

---

## 지원제도 자격 조건

SupportProgram은 비자와 다른 조건을 가질 수 있습니다.

예:

```text
연령

국적

현재 거주지

재학 여부

현재 취업 상태

소득 요건

특정 지역 거주 여부

기존 사업 참여 여부

기존 수혜 이력

중복 수혜 제한

신청 기간
```

단, 신청 기간은 Eligibility와
별도의 Application Availability로 관리하는 것을 원칙으로 합니다.

---

## Eligibility와 Application Availability 구분

다음 두 개념을 혼동하지 않습니다.

### Eligibility

```text
사용자가 공식 신청 자격을 충족하는가
```

### Application Availability

```text
현재 실제 신청을 접수하고 있는가
```

예:

```text
Eligibility
→ 조건 충족

Application Availability
→ CLOSED
```

가능합니다.

따라서 Rule Evaluator가:

```text
조건 충족
```

으로 판정했다고 해서:

```text
지금 신청할 수 있음
```

을 의미하지 않습니다.

---

## 신청 가능 상태 예시

Application Availability는 별도 Model에서 다음처럼 관리할 수 있습니다.

```text
OPEN
CLOSED
UPCOMING
UNKNOWN
```

현재 상태를 검증하지 못했다면:

```text
UNKNOWN
```

으로 유지합니다.

---

## 비자 발급과 Eligibility 구분

다음 두 표현은 같은 의미가 아닙니다.

```text
공개된 공식 자격 요건 충족
```

과:

```text
비자 발급 확정
```

은 다릅니다.

Global-In은 공개된 공식 조건을 기준으로
Eligibility를 검토하는 서비스입니다.

최종 비자 발급 여부는
관할 기관이 판단합니다.

---

## 지원제도 선정과 Eligibility 구분

마찬가지로:

```text
지원제도 신청 자격 충족
```

과:

```text
지원 대상 최종 선정
```

은 다릅니다.

선발형 지원사업의 경우
조건 충족이 최종 선정까지 의미하지 않습니다.

---

## Rule Evaluation 흐름

기본 흐름은 다음과 같습니다.

```text
Target 선택
   ↓
Eligibility Requirement 조회
   ↓
UserProfile 확인
   ↓
각 Requirement 평가
   ↓
Condition Result 생성
   ↓
Missing Information 정리
   ↓
Failed Requirement 정리
   ↓
Uncertain Requirement 정리
   ↓
Eligibility Result 생성
```

---

## Condition 평가 예시 1

```text
Requirement

field = age
operator = <=
value = 30

UserProfile

age = 27
```

결과:

```text
PASS
```

---

## Condition 평가 예시 2

```text
Requirement

field = career_years
operator = >=
value = 2

UserProfile

career_years = 1
```

결과:

```text
FAIL
```

---

## Condition 평가 예시 3

```text
Requirement

field = language
operator = >=
value = B2

UserProfile

language = null
```

결과:

```text
UNKNOWN

reason:
Missing Information
```

---

## Condition 평가 예시 4

```text
Requirement

description:
관련 학위 또는 이에 준하는 자격을 관할 기관이 인정할 것

judgeability:
manual_check
```

결과:

```text
UNKNOWN

reason:
기관 확인 필요
```

---

## 최종 Eligibility Status 계산

예상 기본 정책:

### 모든 필수 조건 PASS

```text
조건 충족
```

### 하나 이상의 필수 조건 FAIL

```text
조건 미충족
```

### FAIL은 없지만 UNKNOWN 존재

```text
추가 확인 필요
```

다만 실제 조건 간 OR / AND 관계가 존재할 수 있기 때문에
최종 정책은 Schema 설계 과정에서 확정합니다.

---

## AND 조건

예:

```text
age <= 30
AND
nationality == KR
```

두 조건을 모두 만족해야 합니다.

---

## OR 조건

예:

```text
education == bachelor
OR
career_years >= 5
```

둘 중 하나를 충족하면 되는 구조입니다.

이러한 조건은 단순 Requirement List만으로 부족할 수 있으므로
향후 Condition Group 구조를 도입할 수 있습니다.

---

## 예상 Condition Group

예:

```text
ConditionGroup

operator = AND
conditions = [...]
```

또는:

```text
ConditionGroup

operator = OR
conditions = [...]
```

실제 데이터에서 복합 조건이 얼마나 자주 나타나는지 확인한 뒤
필요한 수준으로 구현합니다.

---

## 예외 규정

비자 및 지원제도에는 예외 조건이 존재할 수 있습니다.

예:

```text
특정 국적 예외

특정 연령 예외

학위 보유자 경력 요건 완화

특정 직종에 대한 별도 조건
```

예외 규정을 충분히 구조화할 수 있는 경우에만
자동 Rule로 반영합니다.

그렇지 않은 경우:

```text
추가 확인 필요
```

로 처리합니다.

---

## 공식 근거

각 Eligibility Requirement는
가능하면 공식 Evidence와 연결합니다.

예:

```text
EligibilityRequirement
   ↓
evidence_id
   ↓
Evidence
```

이를 통해:

```text
왜 이 조건을 판정했는가?
```

에 대한 근거를 추적할 수 있습니다.

---

## 공식 근거가 없는 조건

Evidence가 확인되지 않은 Requirement를
확정적인 Rule로 사용하지 않는 것을 원칙으로 합니다.

예:

```text
source 없음
```

이라면:

```text
공식 Rule로 사용하지 않음
```

또는:

```text
추가 확인 필요
```

로 처리합니다.

---

## 근거 충돌

서로 다른 공식 자료에서 조건이 다르게 나타날 경우
Rule Evaluator가 임의로 최신 조건을 결정하지 않습니다.

예:

```text
Source A
age <= 30

Source B
age <= 35
```

이 경우 먼저:

```text
적용 대상
Program
관할 기관
원문 유형
적용 시점
```

을 확인해야 합니다.

해결되지 않는다면:

```text
추가 확인 필요
```

로 처리합니다.

---

## Rule Evaluator와 Retrieval 관계

기본 자격 판정은 구조화된 PostgreSQL Rule을 사용합니다.

```text
PostgreSQL
   ↓
Eligibility Requirement
   ↓
Rule Evaluator
```

다음 상황에서는 Retrieval이 추가로 필요할 수 있습니다.

```text
예외 규정 확인

조건 의미 확인

공식 자료 충돌

적용 대상 확인

법률 본문 확인
```

구조:

```text
자격 검토 에이전트
   ↓
Rule Evaluator
   ↓
추가 확인 필요
   ↓
Retrieval
   ↓
Official Evidence
```

---

## Rule Evaluator와 LLM 관계

LLM은 Rule Evaluator 결과를 설명할 수 있지만
결과를 임의로 변경하지 않습니다.

예:

```text
Rule Evaluator

조건 미충족
```

인데 LLM이:

```text
그래도 가능해 보입니다.
```

처럼 공식 판정을 뒤집지 않도록 합니다.

LLM의 역할:

```text
결과 설명

부족 조건 설명

추가 준비사항 설명

추가 확인 대상 설명
```

Rule Evaluator의 역할:

```text
공식 조건 비교
```

---

## 예상 파일 구조

```text
app/rules/
├─ __init__.py
├─ evaluator.py
├─ operators.py
├─ status.py
├─ helpers.py
└─ README.md
```

실제 구현 과정에서 변경할 수 있습니다.

---

## `evaluator.py`

Rule Evaluator의 핵심 로직입니다.

예상 역할:

```text
Requirement 입력

UserProfile 입력

조건별 평가

Condition Result 생성

최종 Eligibility Result 생성
```

---

## `operators.py`

공통 비교 Operator를 관리합니다.

예:

```text
equals
not_equals

greater_than
greater_than_or_equal

less_than
less_than_or_equal

in_list
not_in_list

contains

exists
```

중복된 조건 비교 코드를 방지합니다.

---

## `status.py`

Rule 판정에 사용하는 Enum이나 상수를 관리할 수 있습니다.

예:

```text
PASS
FAIL
UNKNOWN

ELIGIBLE
NOT_ELIGIBLE
NEEDS_REVIEW
```

사용자에게 표시하는 한국어 문구와
내부 상태 값을 분리할 수도 있습니다.

예:

```text
ELIGIBLE
→ 조건 충족

NOT_ELIGIBLE
→ 조건 미충족

NEEDS_REVIEW
→ 추가 확인 필요
```

---

## `helpers.py`

필요한 공통 전처리 로직을 관리할 수 있습니다.

예:

```text
문자열 정규화

국가 코드 정규화

Boolean 변환

숫자 변환

빈 값 확인
```

단, 지나치게 많은 비즈니스 로직을
Helper에 숨기지 않습니다.

---

## 예상 함수 형태

예:

```python
def evaluate_requirement(
    requirement,
    user_profile
):
    ...
```

또는:

```python
def evaluate_eligibility(
    requirements,
    user_profile
):
    ...
```

실제 Type은 `app/models/`의 Model을 사용합니다.

---

## 결과 예시

```json
{
  "target_type": "PROGRAM",
  "target_id": "example_program",

  "status": "추가 확인 필요",

  "passed_conditions": [
    "nationality",
    "education"
  ],

  "failed_conditions": [],

  "uncertain_conditions": [
    "career_exception"
  ],

  "missing_information": []
}
```

---

## Missing Information 결과 예시

```json
{
  "target_type": "SUPPORT_PROGRAM",
  "target_id": "support_example",

  "status": "추가 확인 필요",

  "passed_conditions": [
    "nationality"
  ],

  "failed_conditions": [],

  "uncertain_conditions": [],

  "missing_information": [
    "student_status"
  ]
}
```

이 경우 사용자 이해 에이전트가
`student_status`에 대한 추가 질문을 생성할 수 있습니다.

---

## 국가별 조건 처리

국가별 Rule Evaluator를 별도로 만드는 방식은
가능한 한 피합니다.

예:

```text
JapanRuleEvaluator
GermanyRuleEvaluator
CanadaRuleEvaluator
```

처럼 구현하기보다:

```text
공통 Rule Engine
+
국가별 Requirement Data
```

방식을 우선합니다.

구조:

```text
Germany Program
   ↓
Germany Requirement Data
   ↓

공통 Rule Evaluator

   ↑
Japan Requirement Data
   ↑
Japan Program
```

이를 통해 새로운 국가를 추가할 때
Rule Engine 자체를 크게 변경하지 않도록 합니다.

---

## SupportProgram별 조건 처리

지원제도 역시
각 제도마다 Python `if`문을 만드는 방식은 피합니다.

좋지 않은 예:

```python
if support_program == "A":
    ...

elif support_program == "B":
    ...
```

대신:

```text
SupportProgram
   ↓
Eligibility Requirement
   ↓
공통 Rule Evaluator
```

구조를 사용합니다.

---

## 구조화하지 않을 조건

모든 공식 문장을
억지로 Rule로 변환하지 않습니다.

예:

```text
기관이 적절하다고 판단하는 자

관련 분야라고 인정되는 경력

특별한 사유가 인정되는 경우
```

이러한 조건을 임의의 Boolean Rule로 만들면
오히려 잘못된 자동 판정이 발생할 수 있습니다.

따라서:

```text
judgeability = manual_check
```

등으로 표현하고:

```text
추가 확인 필요
```

로 반환합니다.

---

## 정보 변경 대응

정책이나 자격 조건이 변경되었을 때
Rule Evaluator 코드를 매번 수정하는 구조를 피합니다.

가능하면:

```text
Code
→ Rule 평가 방법

Database
→ 실제 공식 Requirement
```

로 역할을 구분합니다.

예:

```text
기존 조건:
age <= 30

변경 조건:
age <= 35
```

이라면 데이터 변경만으로
새 조건을 반영할 수 있는 구조를 목표로 합니다.

---

## Rule Version 관리

향후 필요할 경우 Requirement에
다음 Metadata를 추가할 수 있습니다.

```text
effective_from
effective_until
verified_at
```

이를 통해 시점별 조건을 구분합니다.

단순히 가장 최근에 저장된 Rule을
자동으로 현재 Rule이라고 가정하지 않습니다.

---

## 테스트 전략

Rule Evaluator는
LLM과 독립적으로 Unit Test가 가능해야 합니다.

---

## 기본 Test Case

### 숫자 비교

```text
age <= 30
```

테스트:

```text
age = 20
→ PASS

age = 30
→ PASS

age = 31
→ FAIL

age = null
→ UNKNOWN
```

---

## 국적 Test

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

## 경력 Test

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

## manual_check Test

```text
judgeability = manual_check
```

결과:

```text
UNKNOWN
```

으로 유지되어야 합니다.

---

## 복수 조건 Test

```text
Requirement 1
→ PASS

Requirement 2
→ PASS

Requirement 3
→ FAIL
```

필수 조건이라면 최종:

```text
조건 미충족
```

이어야 합니다.

---

## Missing Information Test

```text
Requirement 1
→ PASS

Requirement 2
→ UNKNOWN
   reason = missing user data

FAIL 없음
```

최종:

```text
추가 확인 필요
```

이며:

```text
missing_information
```

에 필요한 Field가 들어가야 합니다.

---

## Program / SupportProgram 분리 Test

같은 사용자를 기준으로:

```text
Program
→ 조건 충족

SupportProgram A
→ 조건 미충족

SupportProgram B
→ 추가 확인 필요
```

가 각각 독립적으로 반환되는지 확인합니다.

---

## 중요한 테스트 포인트

```text
Missing Information을 미충족으로 처리하지 않는가

명확한 FAIL을 추가 확인으로 숨기지 않는가

manual_check를 자동 PASS 처리하지 않는가

Program과 SupportProgram을 혼동하지 않는가

Evidence 없는 Rule을 무조건 적용하지 않는가

LLM 없이 동일 결과를 재현할 수 있는가

국가별 Hard Coding이 과도하지 않은가

Rule 변경 시 Code 수정이 최소화되는가
```

---

## 구현 원칙

- 구조화 가능한 조건만 Rule Evaluator에서 처리
- 공식 Evidence가 확인된 조건을 우선 사용
- 사용자 정보 부족과 조건 미충족을 구분
- Program과 SupportProgram Eligibility를 구분
- Eligibility와 Application Availability를 구분
- 자동 판정 불가능한 조건을 억지로 판단하지 않음
- 예외 규정을 무시하지 않음
- 공식 근거 충돌 시 확정 판정하지 않음
- LLM이 Rule 결과를 임의로 변경하지 않음
- 국가별 Hard Coding을 최소화
- Rule 자체와 Requirement Data를 가능한 한 분리
- 동일 입력에는 동일 판정이 나오도록 결정적으로 구현

---

## 개발 순서

```text
1. EligibilityRequirement Model 확정

2. EligibilityResult Model 확정

3. 내부 Condition Status 정의

4. 기본 Operator 구현

5. 단일 Requirement 평가 구현

6. Missing Information 처리

7. 여러 Requirement 통합 평가

8. Program Eligibility 연결

9. SupportProgram Eligibility 연결

10. judgeability 처리

11. Evidence 연결

12. 자격 검토 에이전트 연결

13. Unit Test

14. 실제 공식 데이터 기반 검증

15. 필요 시 AND / OR Condition Group 확장
```

---

## 현재 상태

현재는 Rule Evaluator의 역할과 판정 정책을 설계한 단계입니다.

다음 구현에서는 실제 공식 Program 및 SupportProgram 데이터를 기반으로:

```text
EligibilityRequirement Schema
Operator
Condition Group
judgeability
Eligibility Result
```

구조를 구체화합니다.

Rule Evaluator는 Global-In에서
자격 판단의 일관성과 재현성을 보장하는 핵심 Module로 사용합니다.

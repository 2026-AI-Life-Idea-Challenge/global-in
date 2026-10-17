# data

Global-In에서 사용하는 원본 데이터, 정제 데이터, 초기 적재용 데이터를 관리하는 디렉터리입니다.

이 디렉터리는 공식 기관에서 수집한 자료를 그대로 보관하고,
Global-In의 공통 Schema에 맞게 정제한 뒤,
PostgreSQL 및 pgvector에 적재할 수 있는 형태로 관리하기 위해 사용합니다.

---

## 주요 역할

`data/`는 크게 다음 세 단계의 데이터를 관리합니다.

```text
공식 원본 데이터
   ↓
raw
   ↓
정제 / 구조화
   ↓
processed
   ↓
DB 적재용 변환
   ↓
seed
```

각 단계의 데이터를 분리하여 원본과 가공 데이터를 구분하고,
필요할 경우 언제든 원문으로 돌아가 검증할 수 있도록 합니다.

---

## 디렉터리 구조

```text
data/
├─ raw/
├─ processed/
├─ seed/
└─ README.md
```

---

## `raw/`

공식 기관에서 수집한 원본 데이터를 저장합니다.

가능한 한 원본 내용을 수정하지 않고 보관합니다.

예:

```text
정부 공식 웹페이지
이민기관 안내
대사관 및 영사관 안내
지원사업 안내
공식 FAQ
법령 및 행정 안내
공식 PDF / HTML / JSON
```

원본 데이터를 별도로 보관하는 이유는 정제 과정에서 정보가 잘못 변환되었는지 다시 확인할 수 있도록 하기 위해서입니다.

---

## raw 데이터 저장 원칙

원본 데이터에는 가능하면 다음 정보를 함께 저장합니다.

```text
source_url
official_agency
source_title
source_type
issuer_country
destination_country
original_published_at
original_updated_at
verified_at
collected_at
```

원문에 게시일이나 수정일이 없는 경우 임의로 날짜를 생성하지 않고 `미확인` 또는 `null`로 기록합니다.

---

## `processed/`

원본 데이터를 Global-In의 공통 Schema에 맞게 정제한 데이터를 저장합니다.

예:

```text
국가명 통일
진출 목적 통일
비자 / 프로그램명 정리
지원제도명 정리
자격 조건 구조화
필요 서류 분리
신청 절차 정리
공식 출처 Metadata 연결
```

국가별 공식 사이트는 서로 다른 구조와 표현을 사용하기 때문에
서비스 내부에서 동일한 방식으로 사용할 수 있도록 정규화합니다.

---

## processed 데이터 예시

원본:

```text
Age:
Applicants must be between ...
```

정제 후 예시:

```json
{
  "field": "age",
  "operator": "<=",
  "value": 30,
  "required": true
}
```

구조화 가능한 조건은 Rule Evaluator가 사용할 수 있도록 변환합니다.

---

## 구조화하기 어려운 정보

모든 내용을 Rule 형태로 변환할 수 있는 것은 아닙니다.

예:

```text
예외 규정
복잡한 법률 설명
FAQ
조건부 해석
기관 판단이 필요한 내용
긴 행정 안내
```

이런 정보는 원문 또는 Chunk 형태로 유지하여 pgvector 기반 RAG 검색에 사용합니다.

---

## `seed/`

PostgreSQL 초기 데이터 적재에 사용할 데이터를 저장합니다.

예:

```text
programs.json
support_programs.json
requirements.json
documents.json
evidence.json
```

실제 파일 구조는 DB Schema 확정 후 결정합니다.

---

## Program과 Support Program 구분

Global-In에서는 해외 진출 자체에 필요한 프로그램과
진출 과정에서 활용할 수 있는 지원제도를 구분합니다.

### Program

예:

```text
워킹홀리데이
학생 비자
취업 비자
교환 프로그램
체류 자격
```

### Support Program

예:

```text
해외취업 지원
연수 지원
지원금
장학 지원
외국인 정착 지원
취업 준비 지원
```

두 데이터는 별도로 관리하되 필요한 경우 서로 연결합니다.

하나의 지원제도가 여러 진출 경로와 연결될 수 있습니다.

---

## 정보 범위

Global-In에서 수집하는 정보는 크게 다음 세 영역으로 구분합니다.

### 1. 한국에서 제공하는 해외 진출 지원 정보

예:

```text
해외 취업 지원
해외 연수 지원
준비 교육
지원금
해외 진출 가이드
```

주요 출처:

```text
한국 정부
공공기관
해당 지원사업 운영기관
```

---

### 2. 목적지 국가의 외국인 진출·정착 지원 정보

예:

```text
외국 인재 유치
외국인 취업 지원
유학 지원
장학 지원
정착 지원
```

주요 출처:

```text
목적지 국가 정부
공공기관
교육기관
해당 제도 운영기관
```

---

### 3. 목적지 국가의 비자·법률 정보

예:

```text
비자
입국
체류
근로
학업
신청 자격
신청 절차
필요 서류
제한
의무
예외 규정
```

주요 출처:

```text
공식 법령
이민기관
대사관
노동 관련 기관
교육 관련 기관
관할 행정기관
```

---

## 공식 정보 확인 원칙

지원제도를 수집할 때 다음 세 가지는 각각 별도로 확인합니다.

```text
1. 해당 제도가 실제로 존재하는가
2. 한국인에게 적용 가능한가
3. 현재 실제 신청 가능한 상태인가
```

하나가 확인되었다고 나머지도 자동으로 참이라고 판단하지 않습니다.

예:

```text
제도 존재 확인
≠
한국인 신청 가능

한국인 신청 가능
≠
현재 모집 중
```

실제로 확인된 제도와 공식 근거를 바탕으로 안내합니다.

---

## 국가 정보 관리

다음 국가 개념을 구분하여 저장합니다.

```text
issuer_country
→ 정보를 발행하거나 제도를 운영하는 국가

destination_country
→ 사용자가 실제로 진출하려는 국가

target_nationality
→ 해당 제도의 적용 국적

residence_requirement
→ 신청자의 현재 거주 조건
```

예를 들어 한국 정부가 독일 취업 준비자를 지원하는 프로그램이라면:

```text
issuer_country = Korea
destination_country = Germany
```

로 관리할 수 있습니다.

---

## 정보 주제 분류

수집한 정보는 가능한 한 주제를 구분합니다.

예:

```text
working_holiday
exchange
study
employment
training
support
scholarship
visa
residence
work
education
settlement
```

실제 Enum이나 분류 기준은 DB Schema 확정 후 조정할 수 있습니다.

---

## 원문 유형 분류

공식 자료의 성격도 구분합니다.

예:

```text
law
administrative_guidance
program_notice
official_guide
faq
embassy_notice
education_information
```

법령과 일반 안내 페이지의 성격이 다를 수 있기 때문에 원문 유형을 함께 저장합니다.

---

## 공통 저장 항목

프로그램 및 지원제도에는 가능한 한 다음 정보를 관리합니다.

```text
제도·프로그램 ID
발행 기관
발행 국가
목적지 국가
적용 대상
관할 지역
정보 주제
원문 유형
자격 조건
신청 기관
신청 방법
신청 기간
필요 서류
비용 또는 지원 내용
연결된 진출 경로
```

실제 DB Field는 실제 데이터를 수집하면서 조정합니다.

---

## Evidence Metadata

공식 근거에는 가능한 한 다음 정보를 저장합니다.

```text
official_agency
source_title
source_url
source_type
original_published_at
original_updated_at
effective_from
effective_until
verified_at
```

원문에 날짜가 없는 경우 날짜를 임의로 추정하지 않습니다.

---

## 날짜 관리

다음 날짜를 구분합니다.

### `original_published_at`

원문 최초 게시일

### `original_updated_at`

원문 수정일

### `effective_from`

정책 또는 규정 적용 시작일

### `effective_until`

정책 또는 규정 적용 종료일

### `verified_at`

Global-In에서 해당 정보를 마지막으로 확인한 날짜

### `collected_at`

데이터를 실제로 수집한 날짜

이 값들은 서로 다른 의미를 가지므로 가능한 한 혼합하지 않습니다.

날짜를 저장했다는 이유만으로 해당 정보가 현재 최신 정보라고 판단하지 않습니다.

---

## PostgreSQL과 pgvector 데이터 분리

### PostgreSQL

구조화된 데이터에 사용합니다.

예:

```text
Program
Support Program
Eligibility Requirement
Application Information
Required Document
Fee
Stay Condition
Work Condition
Support Detail
Official Source Metadata
```

### pgvector

공식 원문과 비정형 텍스트 검색에 사용합니다.

예:

```text
법령 본문
FAQ
예외 규정
공식 상세 설명
행정 안내
지원사업 상세 안내
```

---

## 데이터 처리 흐름

```text
Official Source
   ↓
수집
   ↓
data/raw
   ↓
정제 및 검증
   ↓
data/processed
   ↓
DB 적재 형태 생성
   ↓
data/seed
   ↓
PostgreSQL / pgvector
```

---

## 검색 및 검증 원칙

검색 시 다음 정보를 기준으로 범위를 좁힙니다.

```text
국가
진출 목적
실제 프로그램
적용 대상
정보 주제
```

비자 요건은 해당 비자 관할 기관의 자료를 우선 사용하고,
지원제도 요건은 해당 지원제도 운영기관의 공식 자료를 우선 사용합니다.

다음 항목을 검증합니다.

```text
질문과 근거가 관련 있는가
국가가 일치하는가
프로그램이 일치하는가
적용 대상이 일치하는가
적용 시점이 일치하는가
공식 기관 자료인가
확인 시점이 기록되어 있는가
```

근거가 서로 충돌하는 경우
대상, 관할, 적용 시점, 원문을 다시 확인합니다.

충돌이 해소되지 않거나 예외·근거 부족이 존재하면:

```text
추가 확인 필요
```

로 처리합니다.

---

## 데이터 검증

정제 전후 다음 항목을 확인합니다.

```text
공식 기관 자료인가
URL이 정상적인가
국가가 올바른가
프로그램이 올바른가
적용 대상이 올바른가
공식 요건이 원문과 일치하는가
날짜 정보가 원문과 일치하는가
지원제도와 비자 정보를 혼동하지 않았는가
한국인에게 적용 가능한 정보인지 확인했는가
```

---

## 데이터 변경 시 원칙

공식 자료가 변경된 경우 기존 값을 단순 덮어쓰기보다는
변경 사실을 추적할 수 있도록 관리하는 것을 고려합니다.

초기 MVP에서는 복잡한 Versioning 시스템을 구현하지 않더라도
최소한 다음 정보는 유지합니다.

```text
source_url
original_updated_at
verified_at
```

이를 통해 해당 정보가 언제 확인된 자료인지 추적할 수 있도록 합니다.

---

## 데이터 파일 관리 원칙

- 실제 API Key 또는 개인정보를 저장하지 않음
- 대용량 원본 데이터를 무조건 Git에 올리지 않음
- 저작권 및 이용약관을 확인
- 공식 출처 URL을 유지
- 원본과 정제 데이터를 구분
- 수집 과정에서 임의로 사실을 추가하지 않음
- 확인되지 않은 값은 추정하지 않고 미확인으로 유지
- 실제 DB 적재 데이터는 Schema에 맞게 검증 후 사용

---

## 데이터와 Agent의 관계

각 Agent는 서로 다른 데이터를 사용합니다.

```text
사용자 이해 에이전트
→ User Profile

진출 경로 탐색·추천 에이전트
→ Program / Support Program

자격 검토 에이전트
→ Eligibility Requirement

공식 정보 안내 에이전트
→ Evidence / Official Documents

준비 계획 에이전트
→ Application / Documents / Schedule
```

Agent가 데이터를 임의로 사실처럼 생성해서 저장하는 것이 아니라,
공식 자료에서 수집·검증된 데이터를 기반으로 사용합니다.

---

## 현재 개발 단계

현재는 공통 데이터 구조와 수집 기준을 정의하는 단계입니다.

처음부터 모든 Field를 완전히 확정하기보다
핵심 Entity와 공통 Field를 먼저 정의한 뒤,
실제 일본·호주·미국·독일·캐나다 데이터를 수집하면서 세부 Field를 조정합니다.

```text
기본 Entity / Schema 정의
   ↓
실제 데이터 수집
   ↓
필요 Field 확인
   ↓
Schema 보완
   ↓
DB 적재
```

즉 현재 Schema는 실제 데이터 수집 결과에 따라 확장 또는 수정될 수 있습니다.

---

## 향후 작업

```text
1. 핵심 Entity 정의
2. Entity 간 관계 정의
3. ERD 초안 작성
4. 국가별 공식 Source 목록 작성
5. 실제 데이터 수집
6. raw 저장
7. 공통 Schema 정제
8. processed 데이터 생성
9. DB Schema와 매핑
10. seed 데이터 생성
11. PostgreSQL 적재
12. pgvector 적재
13. 데이터 검증
```

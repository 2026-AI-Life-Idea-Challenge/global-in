# data

Global-In에서 사용하는 원본 데이터, 정제 데이터, Seed Data를 관리하는 디렉터리입니다.

Global-In은 단순한 비자 정보뿐 아니라,
실제 해외 진출 Program, 국내외 SupportProgram, 자격조건, 신청정보, 필요서류, 공식 Evidence를 함께 다룹니다.

데이터는 가능한 한 공식 기관의 원문을 기준으로 수집하고,
구조화 가능한 정보와 RAG용 비정형 문서를 구분하여 관리합니다.

---

## 주요 역할

`data/`는 다음 종류의 데이터를 관리합니다.

```text
원본 수집 데이터

정제된 구조화 데이터

Database Seed Data

Program 정보

SupportProgram 정보

Eligibility Requirement

Application Information

Required Document

Evidence Metadata

공식 문서 원문 / Chunk 생성 전 데이터
```

---

## 기본 디렉터리 구조

```text
data/
├─ raw/
├─ processed/
├─ seed/
└─ README.md
```

---

# `raw/`

공식 기관에서 최초 수집한 원본 데이터를 저장합니다.

가능한 한 원문 상태를 유지합니다.

예:

```text
HTML

JSON

CSV

PDF

TXT

공식 페이지에서 추출한 Text
```

원본을 바로 수정하지 않고,
정제 작업은 `processed/`에서 수행합니다.

---

## Raw Data 예시

```text
data/raw/
├─ japan/
├─ australia/
├─ usa/
├─ germany/
└─ canada/
```

국가별로 다시 다음과 같이 구분할 수 있습니다.

```text
germany/
├─ programs/
├─ support_programs/
├─ laws/
├─ guides/
└─ faq/
```

실제 구조는 수집되는 데이터 형태를 확인한 뒤 조정합니다.

---

# `processed/`

수집한 원본 데이터를
Global-In에서 사용할 수 있도록 정제한 데이터를 저장합니다.

예:

```text
정규화된 Program Data

정규화된 SupportProgram Data

Eligibility Requirement

Application Information

Required Document

Evidence Metadata

공식 문서 정제 Text
```

---

## Processed Data 역할

```text
Raw Data
   ↓
Parsing
   ↓
Cleaning
   ↓
Normalization
   ↓
Validation
   ↓
Processed Data
```

이후 Processed Data를 기반으로
PostgreSQL 또는 pgvector에 적재합니다.

---

# `seed/`

개발 및 초기 Database 구축에 사용할
Seed Data를 저장합니다.

예:

```text
Program Seed

SupportProgram Seed

Eligibility Requirement Seed

ApplicationInfo Seed

RequiredDocument Seed

Evidence Seed
```

---

## Seed Data의 목적

다음과 같은 상황에서 사용합니다.

```text
초기 Database 생성

개발 환경 재구성

테스트 환경 구성

Demo 환경 구성
```

Seed Data는 가능한 한
검증된 공식 정보를 기반으로 작성합니다.

---

# 데이터 범위

Global-In은 크게 다음 세 영역의 데이터를 수집합니다.

---

## 1. 한국에서 제공하는 해외 진출 지원 정보

예:

```text
해외 취업 지원

해외 연수

준비 교육

지원금

해외 진출 Guide
```

주요 출처:

```text
한국 정부

공공기관

지원사업 운영기관
```

---

## 2. 목적지 국가의 외국인 진출·정착 지원 정보

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

지원제도 운영기관
```

---

## 3. 목적지 국가의 비자·법률 정보

예:

```text
비자

입국

체류

근로

학업

자격 요건

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

대사관 / 영사관

노동 관련 기관

교육 관련 기관

관할 행정기관
```

---

# 대상 국가

초기 MVP에서는 다음 5개 국가를 대상으로 합니다.

```text
일본

호주

미국

독일

캐나다
```

---

# 상위 진출 경로

```text
워킹홀리데이 / 교환

유학

취업
```

이 3개는 사용자에게 보여주는 상위 진출 경로입니다.

5개 국가 × 3개 경로가
15개의 개별 비자를 의미하지 않습니다.

실제 데이터에서는 각 상위 경로와
실제 비자·체류·교환 Program을 연결합니다.

---

## 예시

```text
USA
+
워킹홀리데이 / 교환
   ↓
J-1 등 관련 Exchange Program
```

국가별 제도 구조가 다르므로
상위 경로와 실제 Program을 분리하여 저장합니다.

---

# Program

Program은 사용자가 실제 해외 진출을 위해 검토하는
비자·체류·교환 등의 경로입니다.

예:

```text
Working Holiday

Student Visa

Employment Visa

Exchange Program

Residence Status
```

---

## Program 예상 정보

```text
program_id

destination_country

purpose

official_program_name

display_name

description

program_type

eligibility

application

documents

stay

preparation

evidence
```

---

# SupportProgram

SupportProgram은 해외 진출 과정에서
사용할 수 있는 국내외 지원제도입니다.

예:

```text
해외취업 지원

해외 연수

준비 교육

장학금

지원금

외국인 취업 지원

정착 지원
```

---

## SupportProgram 예상 정보

```text
support_program_id

official_name

display_name

description

issuer_country

destination_country

official_agency

target_nationality

target_region

purpose

support_type

eligibility

application

support_detail

related_programs

evidence
```

---

# Program과 SupportProgram 관계

Program과 SupportProgram은 같은 개념이 아닙니다.

```text
Program
→ 실제 해외 진출 경로

SupportProgram
→ 해당 진출을 지원하는 제도
```

하나의 SupportProgram은
여러 Program과 연결될 수 있습니다.

예:

```text
SupportProgram A
   ├─ Germany Employment Program
   ├─ Canada Employment Program
   └─ Japan Employment Program
```

DB에서는 연결 Table을 둘 수 있습니다.

```text
Program
   ↑
   │
ProgramSupportLink
   │
   ↓
SupportProgram
```

---

# 국가 관련 Field

Global-In에서는 국가 정보를 단순히 `country` 하나로 저장하지 않고,
역할에 따라 구분합니다.

---

## `issuer_country`

제도 또는 문서를 발행한 국가입니다.

예:

```text
한국 정부 해외취업 지원제도

issuer_country = Korea
```

---

## `destination_country`

사용자가 진출하려는 목적지 국가입니다.

예:

```text
독일 취업 지원

destination_country = Germany
```

---

## `target_nationality`

해당 제도 또는 Program이 적용되는 대상 국적입니다.

예:

```text
target_nationality = Korean
```

---

## `residence_requirement`

신청자의 현재 거주 조건입니다.

예:

```text
한국 거주자만 신청 가능

특정 주 / 지역 거주 필요
```

이 정보는 `issuer_country`와 별도로 관리합니다.

---

# Eligibility Data

Program과 SupportProgram 각각의
공식 자격조건을 구조화합니다.

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

---

## Eligibility Requirement 예시

```json
{
  "field": "career_years",
  "operator": ">=",
  "value": 2,
  "required": true,
  "judgeability": "rule_based"
}
```

---

## 자동 판정 가능 여부

모든 공식 조건을
Rule로 강제 변환하지 않습니다.

예:

```text
rule_based

manual_check

conditional
```

---

### `rule_based`

Python Rule Evaluator로 비교 가능한 조건

예:

```text
age <= 30

career_years >= 2
```

---

### `manual_check`

기관 판단이나 별도 확인이 필요한 조건

예:

```text
관련 경력으로 인정되는지

예외 대상인지

특정 자격을 동등하게 인정하는지
```

---

### `conditional`

다른 조건에 따라 적용 여부가 달라지는 경우입니다.

---

# Eligibility와 Application Availability

다음 두 정보는 별도로 저장합니다.

```text
Eligibility
→ 사용자가 조건을 충족하는가
```

```text
Application Availability
→ 현재 실제 신청 가능한가
```

예:

```text
Eligibility = 조건 충족

Application Availability = CLOSED
```

가능합니다.

---

## 신청 가능 상태 예시

```text
OPEN

CLOSED

UPCOMING

UNKNOWN
```

현재 상태를 검증하지 못한 경우:

```text
UNKNOWN
```

으로 유지합니다.

---

# 지원제도 검증 항목

SupportProgram은 최소 다음 항목을 별도로 확인합니다.

```text
제도가 실제 존재하는가

한국인에게 적용 가능한가

현재 적용 가능한 제도인가

현재 신청 가능한가
```

이 항목들을 하나의 Boolean으로 합치지 않습니다.

---

# Application Information

Program 및 SupportProgram의 신청 정보를 관리합니다.

예:

```text
application_agency

application_method

application_url

application_period

application_status

fee
```

---

## 신청 기간

신청 기간이 공식적으로 확인된 경우에만 저장합니다.

예:

```text
application_start

application_end
```

확인할 수 없다면:

```text
null
```

또는:

```text
UNKNOWN
```

으로 유지합니다.

임의로 날짜를 생성하지 않습니다.

---

# Required Document

Program 및 SupportProgram의 필요 서류를 관리합니다.

예:

```text
document_id

target_type

target_id

document_name

description

required

conditional

stage

evidence_id
```

---

## 서류 구분

```text
Program 필수 서류

Program 조건부 서류

SupportProgram 필수 서류

SupportProgram 조건부 서류

공통 준비 서류
```

---

# 준비 단계

Program 및 SupportProgram의 준비 절차는
다음과 같이 단계별로 관리할 수 있습니다.

```text
preparation

application

post_approval

pre_departure

post_entry
```

사용자에게는 다음과 같이 표현할 수 있습니다.

```text
준비

신청

승인 후

출국 준비

입국 후
```

---

# Evidence

모든 핵심 정보는 가능한 한
공식 Evidence와 연결합니다.

Evidence에는 최소한 다음 정보를 저장합니다.

```text
evidence_id

official_agency

issuer_country

destination_country

source_title

source_url

source_type

information_topic

program_id

support_program_id

original_published_at

original_updated_at

effective_from

effective_until

verified_at
```

---

# 날짜 Field 구분

다음 날짜는 서로 다른 의미를 가집니다.

---

## `original_published_at`

공식 원문의 최초 게시일

---

## `original_updated_at`

공식 원문의 마지막 수정일

---

## `effective_from`

정책·제도·규정이 실제 적용되기 시작하는 시점

---

## `effective_until`

정책·제도·규정의 적용 종료 시점

---

## `verified_at`

Global-In이 해당 정보를 실제로 확인한 날짜

---

## 중요한 원칙

```text
verified_at이 최근
≠
정책 자체가 최신 / 현재 유효함
```

따라서 날짜를 각각 분리합니다.

공식 원문에 날짜가 없다면
임의로 추정하지 않습니다.

---

# Source Type

공식 자료의 성격을 구분합니다.

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

법령과 일반 FAQ를 동일한 수준의 자료처럼 취급하지 않습니다.

---

# Information Topic

문서가 어떤 정보를 담고 있는지도 구분합니다.

예:

```text
visa

entry

residence

work

employment

study

education

working_holiday

exchange

support

training

scholarship

settlement

eligibility

application

document

fee

exception
```

실제 값은 데이터 수집 결과를 보면서 정규화합니다.

---

# Structured Data와 Unstructured Data

Global-In은 두 종류의 데이터를 분리하여 관리합니다.

---

## Structured Data

PostgreSQL에 저장합니다.

예:

```text
Program

SupportProgram

EligibilityRequirement

ApplicationInfo

ApplicationAvailability

RequiredDocument

SupportDetail

Evidence Metadata
```

---

## Unstructured Data

긴 공식 문서나 FAQ 등은
pgvector 기반 RAG 검색에 사용합니다.

예:

```text
법령 본문

행정 안내

공식 Guide

FAQ

예외 규정

지원사업 상세 설명
```

---

# 공식 문서 처리 흐름

```text
Official Source
   ↓
Raw Data
   ↓
Text Extraction
   ↓
Cleaning
   ↓
Metadata 추가
   ↓
Processed Data
   ↓
Chunking
   ↓
Embedding
   ↓
PostgreSQL + pgvector
```

---

# 데이터 수집 원칙

가능하면 공식 출처를 우선합니다.

우선순위 예:

```text
관할 정부 / 법령

공식 이민기관

공식 운영기관

공식 대사관 / 영사관

공식 교육기관

공식 FAQ / Guide
```

비공식 Blog나 커뮤니티 글을
핵심 Eligibility 근거로 사용하지 않습니다.

---

# 비자 정보 출처 원칙

비자·체류 관련 조건은
가능하면 해당 국가의 관할 기관 자료를 우선합니다.

예:

```text
이민기관

외교기관

공식 법령

대사관
```

---

# SupportProgram 출처 원칙

지원제도의 자격조건과 신청정보는
해당 제도를 실제 운영하는 기관 자료를 우선합니다.

예:

```text
지원사업 운영기관

정부 부처

공공기관

교육기관
```

---

# 공식 정보 충돌 처리

서로 다른 공식 자료의 내용이 충돌할 수 있습니다.

예:

```text
Source A
age <= 30

Source B
age <= 35
```

이 경우 다음을 비교합니다.

```text
Program

SupportProgram

적용 대상

관할 기관

Source Type

적용 시점

원문 수정일
```

해결되지 않는다면:

```text
추가 확인 필요
```

로 유지합니다.

---

# 한국인 적용 여부

목적지 국가에서 제공하는 외국인 지원제도라고 해서
자동으로 한국인에게 적용되는 것은 아닙니다.

반드시 다음을 구분합니다.

```text
외국인 대상

한국인 포함 여부

특정 국적 제외 여부

거주 조건

학생 / 근로자 등 대상 상태
```

불명확하다면:

```text
추가 확인 필요
```

로 유지합니다.

---

# 데이터 정규화

국가마다 공식 용어와 데이터 형식이 다를 수 있습니다.

예:

```text
Germany
→ residence permit

USA
→ visa category

Japan
→ status of residence
```

원문 명칭을 유지하면서,
서비스 내부에서는 공통 개념과 연결합니다.

예:

```text
official_name
→ 원문 명칭

display_name
→ 사용자에게 보여줄 한국어 명칭

program_type
→ 내부 공통 분류
```

---

# 원문 보존

중요한 Program명,
법률 용어,
지원제도명은 원문을 보존합니다.

예:

```text
display_name:
독일 EU 블루카드

official_name:
EU Blue Card
```

번역명만 저장하지 않습니다.

---

# 데이터 ID

각 Entity는 안정적인 내부 ID를 사용합니다.

예:

```text
program_id

support_program_id

requirement_id

document_id

evidence_id
```

공식 명칭 자체를 Primary Key처럼 사용하는 것을 피합니다.

명칭은 변경될 수 있기 때문입니다.

---

# 데이터 수집 Script와 관계

실제 데이터 수집 Script는:

```text
scripts/crawl/
```

에서 관리합니다.

수집 흐름:

```text
scripts/crawl/
   ↓
data/raw/
```

---

# 데이터 처리 Script와 관계

정제 및 변환 Script는
필요에 따라 `scripts/`에서 관리합니다.

예:

```text
Raw Data
   ↓
Processing Script
   ↓
Processed Data
```

---

# Database 적재 Script와 관계

PostgreSQL 또는 pgvector 적재용 Script는:

```text
scripts/ingest/
```

에서 관리합니다.

흐름:

```text
data/processed/
   ↓
scripts/ingest/
   ↓
PostgreSQL / pgvector
```

---

# Seed Data 적재

초기 개발 환경에서는:

```text
data/seed/
   ↓
scripts/ingest/
   ↓
PostgreSQL
```

형태로 사용할 수 있습니다.

---

# 데이터 파일 형식

구조화 Data는 초기에는
다음 형식을 사용할 수 있습니다.

```text
JSON

JSONL

CSV
```

복잡한 중첩 구조가 많은 경우:

```text
JSON
```

을 우선 고려합니다.

실제 DB Schema가 확정되면
Seed Data 형식도 함께 확정합니다.

---

# JSON 예시

Program 예:

```json
{
  "program_id": "example_program",
  "destination_country": "Germany",
  "purpose": "employment",

  "official_program_name": "Example Program",
  "display_name": "예시 취업 프로그램",

  "eligibility": [],

  "evidence": []
}
```

---

# SupportProgram 예시

```json
{
  "support_program_id": "example_support",

  "issuer_country": "Korea",
  "destination_country": "Germany",

  "target_nationality": [
    "Korean"
  ],

  "purpose": "employment",

  "official_name": "Example Support Program",

  "eligibility": [],

  "evidence": []
}
```

---

# 저장하지 말아야 할 정보

다음 정보는 수집 Data에 포함하지 않습니다.

```text
API Key

Database Password

개인 Password

Secret Token

민감한 사용자 개인정보
```

환경변수와 사용자 Data는
별도 정책에 따라 관리합니다.

---

# Git 관리

모든 수집 Data를 무조건 Git Repository에 Commit하지 않습니다.

특히 다음을 고려합니다.

```text
파일 크기

저작권

공개 가능 여부

개인정보 포함 여부

재배포 가능 여부
```

---

## Git에 포함하기 좋은 데이터

예:

```text
작은 Seed Data

Schema Sample

테스트용 Dummy Data

공개 가능한 공식 Metadata
```

---

## Git 제외를 고려할 데이터

예:

```text
대용량 Raw Data

대량 PDF

대량 HTML

Embedding 결과

Database Dump

민감 정보가 포함된 자료
```

필요한 경우 `.gitignore`에 추가합니다.

---

# File Naming

파일명은 가능한 한 일관되게 작성합니다.

예:

```text
germany_employment_programs.json

korea_germany_support_programs.json

canada_study_programs.json
```

날짜 Snapshot이 필요한 경우:

```text
germany_employment_programs_2026-10-17.json
```

형태를 사용할 수 있습니다.

---

# 데이터 검증

수집한 Data는 DB에 넣기 전에
최소한 다음 항목을 확인합니다.

```text
필수 ID 존재

Program / SupportProgram 구분

국가 정보 정상

공식 기관 존재

원문 URL 존재

Eligibility 구조 정상

Application 정보 정상

Evidence 연결 정상

날짜 형식 정상
```

---

# 중복 데이터

같은 Program이나 SupportProgram이
여러 Source에서 등장할 수 있습니다.

단순히 각각 새로운 Entity로 저장하지 않고,
동일 Entity인지 확인한 후 Evidence를 여러 개 연결하는 방식을 고려합니다.

예:

```text
Program A
   ├─ Evidence 1
   ├─ Evidence 2
   └─ Evidence 3
```

---

# 정보 갱신

초기 MVP에서는
실시간 자동 갱신을 구현하지 않습니다.

대신:

```text
original_updated_at

effective_from

effective_until

verified_at
```

등을 저장하여
향후 정보 갱신이 가능하도록 설계합니다.

---

# 현재 모집 여부

SupportProgram이나 특정 Program의
신청 기간이 수시로 변경될 수 있습니다.

현재 모집 여부를 확인하지 못한 경우:

```text
UNKNOWN
```

으로 저장합니다.

다음처럼 임의로 표시하지 않습니다.

```text
현재 신청 가능
```

---

# 데이터 품질 상태

향후 필요하다면
각 데이터에 품질 상태를 추가할 수 있습니다.

예:

```text
verified

needs_review

conflicted

outdated
```

다만 실제 필요성이 확인되기 전까지
불필요한 Field를 과도하게 추가하지 않습니다.

---

# 데이터 설계 원칙

Global-In의 Schema는
처음부터 모든 국가의 모든 경우를 완벽하게 표현하려 하지 않습니다.

다음 순서로 확장합니다.

```text
Agent가 필요한 정보 정의
   ↓
공통 Entity 정의
   ↓
기본 Schema 정의
   ↓
실제 공식 데이터 수집
   ↓
국가별 차이 확인
   ↓
Field 수정 / 확장
```

즉:

```text
데이터를 Schema에 억지로 끼워맞춤
```

이 아니라:

```text
기본 Schema를 만든 뒤
실제 데이터를 확인하면서 보완
```

하는 방식입니다.

---

# Agent와 Data의 관계

---

## 사용자 이해 에이전트

주로 사용하는 데이터:

```text
UserProfile
Program이 요구하는 사용자 조건 Field
SupportProgram이 요구하는 사용자 조건 Field
```

---

## 진출 경로 탐색·추천 에이전트

주로 사용하는 데이터:

```text
Program

SupportProgram

ProgramSupportLink
```

---

## 자격 검토 에이전트

주로 사용하는 데이터:

```text
EligibilityRequirement

UserProfile

Evidence
```

---

## 공식 정보 안내 에이전트

주로 사용하는 데이터:

```text
Evidence

Official Document

Document Chunk
```

---

## 준비 계획 에이전트

주로 사용하는 데이터:

```text
ApplicationInfo

RequiredDocument

SupportDetail

Stay Information

Evidence
```

---

# Models와 Data의 관계

```text
data/
→ 실제 데이터

app/models/
→ Python에서 사용하는 데이터 구조
```

예:

```text
data/processed/programs.json
   ↓
Program Model
   ↓
PostgreSQL
```

---

# docs와 Data의 관계

```text
docs/
→ Schema 설계 및 ERD 문서

data/
→ 실제 데이터
```

예:

```text
docs/database/schema.md

data/processed/programs.json
```

---

# 개발 순서

현재 예상 데이터 작업 순서는 다음과 같습니다.

```text
1. 핵심 Entity 정의

2. Program 기본 Schema 정의

3. SupportProgram 기본 Schema 정의

4. EligibilityRequirement 정의

5. Evidence Metadata 정의

6. 국가별 공식 출처 목록 작성

7. Sample Data 수집

8. 실제 데이터 구조 확인

9. Schema 보완

10. Processed Data 생성

11. Seed Data 생성

12. PostgreSQL 적재

13. Official Document Chunk 생성

14. pgvector 적재

15. Agent 연결

16. 데이터 검증
```

---

# 테스트 포인트

```text
Program과 SupportProgram이 구분되는가

issuer_country와 destination_country가 구분되는가

한국인 적용 여부를 확인할 수 있는가

Eligibility와 Application Availability가 구분되는가

Evidence URL이 유지되는가

원문 날짜와 verified_at이 구분되는가

지원제도와 관련 Program 연결이 정상적인가

Missing Information에 필요한 Field를 알 수 있는가

Rule Evaluator가 사용할 수 있는 구조인가

Retrieval Metadata Filter에 사용할 수 있는 구조인가
```

---

# 현재 상태

현재는 Global-In의 공식 데이터 범위와
기본 Entity 구조를 정의한 단계입니다.

다음 단계에서는 실제 5개 국가의
Program, SupportProgram, 공식 규정 및 지원제도 데이터를 수집하면서:

```text
Field

Entity 관계

Eligibility 표현

Application Availability

Evidence Metadata

ProgramSupportLink
```

구조를 실제 데이터에 맞춰 구체화합니다.

초기 Schema를 절대적인 최종 구조로 고정하지 않고,
실제 공식 데이터와 Agent 요구사항을 기준으로 지속적으로 보완합니다.

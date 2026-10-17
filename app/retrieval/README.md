# app/retrieval

Global-In의 공식 문서 검색 및 RAG(Retrieval-Augmented Generation) 기능을 구현하는 디렉터리입니다.

사용자의 질문, 선택된 국가, 실제 Program, SupportProgram, 적용 대상 등의 조건을 기준으로
PostgreSQL의 pgvector에 저장된 공식 문서를 검색하고,
공식 정보 안내 에이전트가 사용할 Evidence 후보를 제공합니다.

Retrieval은 최종 답변을 생성하거나 자격을 판정하는 역할이 아니라,
공식 근거를 정확하게 찾아 반환하는 검색 Module입니다.

---

## 주요 역할

`app/retrieval/`은 다음 역할을 담당합니다.

```text
User Query
   ↓
Agent State 확인
   ↓
검색 조건 생성
   ↓
Metadata Filtering
   ↓
Query Embedding
   ↓
pgvector Search
   ↓
검색 결과 Ranking
   ↓
Evidence 후보 반환
   ↓
Evidence Validation
```

Retrieval은 검색된 공식 자료를
공식 정보 안내 에이전트 및 다른 Agent가 사용할 수 있도록 전달합니다.

---

## 5개 Agent 구조에서의 위치

현재 Global-In은 다음 5개 Agent를 사용합니다.

```text
1. 사용자 이해 에이전트
2. 진출 경로 탐색·추천 에이전트
3. 자격 검토 에이전트
4. 공식 정보 안내 에이전트
5. 준비 계획 에이전트
```

이 중 `app/retrieval/`을 가장 직접적으로 사용하는 Agent는:

```text
공식 정보 안내 에이전트
```

입니다.

기본 관계:

```text
공식 정보 안내 에이전트
        ↓
Retrieval Module
        ↓
PostgreSQL + pgvector
        ↓
공식 문서 검색
        ↓
Evidence 후보
        ↓
Evidence Validation
        ↓
공식 정보 안내 에이전트
```

다른 Agent도 필요한 경우 검색 결과를 공유받을 수 있습니다.

예:

```text
자격 검토 에이전트
→ 예외 규정 확인

진출 경로 탐색·추천 에이전트
→ 지원제도 공식 근거 확인

준비 계획 에이전트
→ 공식 신청 절차 / 서류 / 일정 확인
```

---

## 검색 대상

Global-In에서는 크게 다음 세 영역의 공식 자료를 검색합니다.

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
지원사업 운영기관
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
지원제도 운영기관
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

## PostgreSQL과 pgvector

Global-In은 별도의 Vector Database 대신
PostgreSQL의 `pgvector` 확장을 사용합니다.

구조는 다음과 같습니다.

```text
PostgreSQL
│
├─ Structured Data
│   ├─ Program
│   ├─ SupportProgram
│   ├─ EligibilityRequirement
│   ├─ ApplicationInfo
│   ├─ RequiredDocument
│   └─ Evidence Metadata
│
└─ Official Document Chunks
    ├─ content
    ├─ metadata
    └─ embedding
```

---

## PostgreSQL과 Retrieval의 역할 구분

### PostgreSQL Structured Search

정확하게 구조화된 사실을 조회합니다.

예:

```text
Program 이름
지원제도 이름
연령 조건
학력 조건
경력 조건
신청 기관
비용
필요 서류
지원 내용
```

### pgvector Retrieval

긴 공식 문서나 비정형 정보를 검색합니다.

예:

```text
법령 본문
FAQ
예외 규정
행정 안내
지원사업 상세 설명
체류 조건 설명
근로 제한 설명
```

---

## Program Resolver와 Retrieval의 차이

두 기능은 명확하게 구분합니다.

### Program Resolver

```text
어떤 실제 Program을 검토해야 하는가?
```

를 결정합니다.

예:

```text
Germany
+
Employment
   ↓
관련 실제 취업 Program 후보
```

주로 PostgreSQL의 구조화된 데이터를 사용합니다.

### Retrieval

```text
선택된 Program에 대한 공식 근거는 무엇인가?
```

를 검색합니다.

예:

```text
선택된 취업 Program
   ↓
공식 자격 규정
근로 조건
예외 규정
FAQ
```

주로 pgvector의 공식 문서를 사용합니다.

---

## SupportProgram 검색

Retrieval은 비자나 체류 Program뿐 아니라
국내외 SupportProgram의 공식 근거도 검색합니다.

예:

```text
한국 해외취업 지원제도
해외 연수 지원제도
장학 지원
외국인 취업 지원
정착 지원
```

SupportProgram 검색에서는 특히 다음을 확인해야 합니다.

```text
해당 제도가 실제 존재하는가
한국인에게 적용 가능한가
현재 신청 가능한 상태인가
```

이 세 가지는 서로 별개의 정보로 취급합니다.

---

## RAG 처리 흐름

기본 Retrieval 흐름은 다음과 같습니다.

```text
사용자 질문
   ↓
Agent State 확인
   ↓
검색 대상 결정
   ↓
Metadata Filter 생성
   ↓
Query Embedding 생성
   ↓
pgvector Similarity Search
   ↓
관련 Chunk 검색
   ↓
Ranking
   ↓
Evidence 후보 생성
   ↓
Evidence Validation
```

---

## Agent State 활용

Retrieval은 사용자의 질문만으로 검색하지 않고
현재 Agent State의 정보를 함께 활용합니다.

예:

```text
user_query

selected_country
selected_program
selected_support_programs

purpose
target_nationality
current_residence

information_topic
```

이를 이용하여 검색 범위를 좁힙니다.

---

## Metadata Filtering

Vector Similarity만 사용하면
다른 국가나 다른 Program의 문서가 검색될 수 있습니다.

따라서 Vector Search 전에
가능한 한 Metadata Filtering을 적용합니다.

예상 Metadata:

```text
issuer_country
destination_country

target_nationality
target_region

purpose

program_id
support_program_id

information_topic
source_type

official_agency

original_published_at
original_updated_at

effective_from
effective_until

verified_at
```

---

## Metadata Filtering 예시

사용자 질문:

```text
독일 취업 비자의 근로 조건을 알려줘.
```

현재 State:

```text
destination_country = Germany
purpose = Employment
selected_program = german_example_program
information_topic = Work
```

검색 조건:

```text
destination_country = Germany
program_id = german_example_program
information_topic = Work
```

그 범위에서 Vector Search를 수행합니다.

---

## SupportProgram 검색 예시

사용자 질문:

```text
독일 취업 준비할 때 한국에서 받을 수 있는 지원이 있어?
```

검색 조건 예:

```text
issuer_country = Korea
destination_country = Germany
purpose = Employment
information_topic = Support
target_nationality = Korean
```

검색 결과에는 지원제도 존재 여부뿐 아니라
한국인 적용 여부와 신청 관련 공식 근거도 포함해야 합니다.

---

## 원문 유형

공식 자료의 성격을 Metadata로 구분합니다.

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

법령과 일반 안내 페이지가 동일한 의미를 가지는 것은 아니므로
원문 유형을 유지합니다.

---

## 정보 주제

검색 정확도를 높이기 위해
문서의 정보 주제도 구분합니다.

예:

```text
visa
entry
residence
employment
work
study
education

working_holiday
exchange

support
training
scholarship
settlement

application
document
fee
eligibility
exception
```

실제 분류 체계는 데이터 수집 결과에 따라 조정합니다.

---

## Document Chunk

공식 문서 전체를 하나의 Embedding으로 저장하지 않고,
의미 있는 단위로 나누어 저장합니다.

기본 흐름:

```text
Official Document
   ↓
Text Extraction
   ↓
Cleaning
   ↓
Section Parsing
   ↓
Chunking
   ↓
Embedding
   ↓
pgvector
```

---

## Chunk Metadata

각 Chunk에는 본문과 함께
가능한 한 다음 정보를 유지합니다.

```text
chunk_id
document_id

content
embedding

issuer_country
destination_country

purpose

program_id
support_program_id

target_nationality

information_topic
source_type

official_agency
source_title
source_url

original_published_at
original_updated_at

effective_from
effective_until

verified_at
```

---

## Chunking 원칙

Chunking 시 다음을 고려합니다.

```text
의미 단위 유지
Section 경계 유지
너무 짧은 Chunk 방지
서로 다른 규정을 하나의 Chunk에 과도하게 혼합하지 않음
제목 정보 유지
출처 Metadata 유지
예외 규정의 문맥 유지
```

정확한 Chunk 크기와 Overlap은
실제 Retrieval 평가 결과를 보고 결정합니다.

---

## Embedding

문서 Chunk와 사용자 Query를 Vector로 변환합니다.

```text
Official Document Chunk
   ↓
Embedding Model
   ↓
Vector
```

```text
User Query
   ↓
Embedding Model
   ↓
Vector
```

이후 pgvector에서 Similarity Search를 수행합니다.

---

## Embedding Model 선택 기준

Global-In은 여러 국가의 공식 자료를 다루기 때문에
다음 항목을 고려합니다.

```text
한국어 검색 성능
영어 검색 성능
다국어 검색 성능
Embedding Dimension
비용
응답 속도
API 안정성
```

Embedding Model은 실제 구현 단계에서 결정합니다.

---

## Retrieval 결과

Retrieval 결과는 단순 문자열이 아니라
구조화된 형태로 반환합니다.

예:

```json
{
  "document_id": "document_example",
  "chunk_id": "chunk_example",

  "content": "공식 문서 내용",

  "destination_country": "Germany",
  "program_id": "example_program",

  "support_program_id": null,

  "information_topic": "work",

  "official_agency": "Example Agency",
  "source_title": "Official Guide",
  "source_url": "https://example.com",

  "original_updated_at": "2026-01-01",
  "effective_from": null,
  "effective_until": null,
  "verified_at": "2026-10-17",

  "score": 0.91
}
```

실제 Schema는 `app/models/`에서 정의합니다.

---

## Retrieval Result와 Evidence의 차이

검색 결과가 바로 최종 Evidence가 되는 것은 아닙니다.

```text
Retrieval Result
   ↓
Evidence Validation
   ↓
Validated Evidence
```

Retrieval은:

```text
관련 가능성이 높은 문서 검색
```

을 담당하고,

Evidence Validation은:

```text
실제로 이 질문의 근거로 사용할 수 있는가?
```

를 확인합니다.

---

## Evidence Validation

다음 항목을 검증합니다.

```text
질문과 관련 있는가

국가가 일치하는가

Program이 일치하는가

SupportProgram이 일치하는가

적용 대상이 일치하는가

공식 기관 자료인가

적용 시점이 맞는가

확인 시점이 기록되어 있는가
```

---

## 날짜 검증

다음 날짜를 구분합니다.

```text
original_published_at
→ 원문 최초 게시일

original_updated_at
→ 원문 수정일

effective_from
→ 제도 / 규정 적용 시작일

effective_until
→ 제도 / 규정 적용 종료일

verified_at
→ Global-In에서 마지막으로 확인한 날짜
```

`verified_at`이 최근이라고 해서
원문 내용 자체가 현재 유효하다고 자동 판단하지 않습니다.

---

## 근거 충돌 처리

공식 자료가 서로 충돌할 경우
다음 항목을 비교합니다.

```text
관할 기관
적용 대상
Program
SupportProgram
적용 지역
적용 시점
원문 유형
원문 내용
```

충돌을 해소할 수 없는 경우:

```text
추가 확인 필요
```

상태로 유지합니다.

LLM이 임의로 하나의 정보를 선택하여
확정적인 사실처럼 설명하지 않도록 합니다.

---

## 검색 결과가 없는 경우

관련 공식 근거가 검색되지 않은 경우
LLM이 근거를 생성하지 않도록 합니다.

예:

```text
retrieval_results = []
```

인 경우:

```text
현재 확인된 공식 근거가 부족합니다.
```

또는:

```text
추가 확인 필요
```

로 처리합니다.

---

## 예상 파일 구조

```text
app/retrieval/
├─ __init__.py
├─ retriever.py
├─ query.py
├─ embeddings.py
├─ filters.py
├─ ranking.py
├─ evidence.py
└─ README.md
```

실제 구현 과정에서 변경될 수 있습니다.

---

## `retriever.py`

Retrieval의 핵심 실행 로직을 구현합니다.

담당:

```text
Query 입력
Metadata Filter 적용
Vector Search
검색 결과 반환
```

---

## `query.py`

사용자 질문과 Agent State를 이용하여
검색 Query를 구성합니다.

예:

```text
사용자 질문
+
selected_program
+
information_topic
+
target_nationality
```

등을 이용합니다.

---

## `embeddings.py`

Embedding 관련 기능을 담당합니다.

```text
Query Embedding
Document Embedding
Embedding Model 설정
```

Embedding API 연결 자체는
`app/services/`로 분리할 수 있습니다.

---

## `filters.py`

Metadata Filtering 조건을 생성합니다.

예:

```text
destination_country
purpose
program_id
support_program_id
target_nationality
information_topic
source_type
```

---

## `ranking.py`

검색 결과의 Ranking을 담당합니다.

초기에는:

```text
Vector Similarity
```

중심으로 시작하고,
필요한 경우:

```text
Metadata Match
Source Priority
Re-ranking
```

등을 추가할 수 있습니다.

---

## `evidence.py`

검색된 Retrieval Result를
Evidence 후보로 변환하거나 검증하는 공통 기능을 둘 수 있습니다.

예:

```text
source 확인
대상 일치 확인
Program Match
SupportProgram Match
날짜 확인
```

최종 위치는 공식 정보 안내 에이전트 구현과 함께 조정합니다.

---

## Services와의 관계

Retrieval은 필요한 외부 서비스 기능을
`app/services/`를 통해 사용할 수 있습니다.

```text
Retrieval
   ↓
Services
   ├─ Database Service
   └─ Embedding Service
```

DB Connection이나 Embedding API 호출을
Retrieval 코드에 반복해서 작성하지 않는 것을 원칙으로 합니다.

---

## Models와의 관계

Retrieval은 다음 Model과 연결됩니다.

```text
Program
SupportProgram
Evidence
AgentState
```

검색 결과의 구조 역시
가능한 한 `app/models/`에서 정의합니다.

---

## 공식 정보 안내 에이전트와의 관계

```text
공식 정보 안내 에이전트
        ↓
Retrieval 호출
        ↓
공식 문서 후보 검색
        ↓
Evidence Validation
        ↓
Validated Evidence
        ↓
공식 정보 안내 에이전트
        ↓
사용자에게 한국어 설명
```

Retrieval은 자연어 설명을 생성하지 않습니다.

---

## 자격 검토 에이전트와의 관계

자격 검토의 기본 비교는
PostgreSQL에 저장된 구조화된 Rule을 사용합니다.

```text
Structured Requirement
   ↓
Rule Evaluator
```

하지만 다음 상황에서는 Retrieval이 필요할 수 있습니다.

```text
예외 규정
조건 해석
공식 근거 충돌
기관 판단이 필요한 항목
```

이 경우 공식 문서를 검색하여
추가 확인 근거를 제공합니다.

---

## 준비 계획 에이전트와의 관계

준비 계획 에이전트는 다음 공식 정보를 확인할 때
Retrieval 결과를 사용할 수 있습니다.

```text
신청 절차
필요 서류
공식 신청 기간
출국 전 의무
입국 후 의무
체류 조건
```

확인되지 않은 일정은 임의로 생성하지 않습니다.

---

## 구현 원칙

- 공식 출처를 우선 사용
- Program과 SupportProgram을 구분
- 검색 전에 Metadata Filtering 적용
- 다른 국가 자료 혼입 최소화
- 다른 Program 자료 혼입 최소화
- 적용 대상이 다른 자료 혼입 최소화
- Retrieval Result와 Validated Evidence를 구분
- 출처 URL을 유지
- 날짜 Metadata를 유지
- 날짜가 존재한다는 이유만으로 최신이라고 판단하지 않음
- 공식 자료 간 충돌을 무시하지 않음
- 검색 결과가 없을 때 LLM이 근거를 생성하지 않도록 처리
- 초기에는 단순하고 검증 가능한 Retrieval 구조로 구현
- 실제 평가 결과에 따라 Re-ranking을 추가

---

## 개발 순서

```text
1. Official Document Schema 확인

2. PostgreSQL / pgvector 연결

3. Chunk Schema 정의

4. Embedding Service 연결

5. Metadata Filter 구현

6. Vector Search 구현

7. Program 기반 검색 구현

8. SupportProgram 기반 검색 구현

9. Retrieval Result Model 연결

10. Evidence Validation 구현

11. 공식 정보 안내 에이전트 연결

12. Retrieval 평가

13. Ranking / Re-ranking 개선
```

---

## 테스트 포인트

```text
올바른 국가의 문서가 검색되는가

올바른 Program의 문서가 검색되는가

올바른 SupportProgram의 문서가 검색되는가

한국인에게 적용되지 않는 자료가 잘못 사용되지 않는가

Program과 SupportProgram 근거가 혼동되지 않는가

공식 기관 자료가 우선되는가

Source URL이 유지되는가

날짜 Metadata가 유지되는가

적용 시점이 다른 자료를 구분하는가

검색 결과가 없는 경우 안전하게 처리되는가

잘못된 Retrieval Result가 Evidence로 통과하지 않는가

공식 근거 충돌을 탐지할 수 있는가
```

---

## 현재 상태

현재는 Retrieval 구조와 검색 기준을 설계하는 단계입니다.

향후 실제 5개 국가의 공식 문서와 지원제도 데이터를 수집한 뒤,
검색 성능을 평가하면서 다음 항목을 구체화합니다.

```text
Metadata Field
Chunk Size
Chunk Overlap
Embedding Model
Similarity 기준
검색 개수
Ranking 방식
Re-ranking 필요 여부
Evidence Validation 기준
```

실제 데이터 특성을 확인하면서
Retrieval Schema와 검색 전략을 보완합니다.

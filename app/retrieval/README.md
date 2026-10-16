# app/retrieval

Global-In의 공식 문서 검색 및 RAG(Retrieval-Augmented Generation) 기능을 구현하는 디렉터리입니다.

사용자의 질문과 선택된 국가·진출 경로를 기준으로 PostgreSQL의 pgvector에 저장된 공식 문서를 검색하고, 최종 응답 생성에 사용할 근거(Evidence)를 제공합니다.

---

## 주요 역할

`app/retrieval/`은 다음 역할을 담당합니다.

```text
User Query
   ↓
검색 조건 생성
   ↓
Metadata Filtering
   ↓
Vector Search
   ↓
관련 공식 문서 검색
   ↓
검색 결과 정렬
   ↓
Evidence 후보 반환
```
Retrieval은 최종 답변을 직접 생성하지 않습니다.
관련 공식 자료를 찾아 Agent와 Response Generator가 사용할 수 있도록 전달하는 역할을 담당합니다.

--- 

## 검색 대상
```
정부 공식 안내
이민·출입국 기관 문서
대사관 및 영사관 안내
공식 FAQ
세부 자격 요건
예외 규정
신청 절차
체류 및 근무 조건
```
가능한 한 공식 기관 자료를 우선 사용합니다.

---

## PostgreSQL과 pgvector

Global-In은 별도의 Vector Database 대신 PostgreSQL의 pgvector 확장을 사용합니다.

구조화된 프로그램 정보는 일반 PostgreSQL Table에 저장하고, 공식 문서의 텍스트 Chunk와 Embedding은 pgvector를 이용하여 검색합니다.
```
PostgreSQL
│
├─ Structured Program Data
│
└─ Official Document Chunks
      └─ pgvector Embedding
```

---

## RAG 처리 흐름

기본 Retrieval 흐름은 다음과 같습니다.
```
사용자 질문
   ↓
현재 Agent State 확인
   ↓
country / purpose / program_id 확인
   ↓
Metadata Filtering
   ↓
Query Embedding 생성
   ↓
pgvector Similarity Search
   ↓
관련 Chunk 검색
   ↓
검색 결과 정렬
   ↓
Evidence 후보 반환
```

---

## Metadata Filtering

Vector Similarity만으로 검색하면 다른 국가나 다른 프로그램의 문서가 섞일 수 있습니다.

따라서 검색 전에 Metadata를 이용하여 검색 범위를 제한합니다.

예상 Metadata:
```
country
purpose
program_id
official_agency
document_type
language
original_updated_at
verified_at
```
예를 들어 일본 취업 관련 질문이라면:
```
country = Japan
purpose = Employment
```
조건을 먼저 적용한 뒤 해당 범위에서 Vector Search를 수행합니다.

---

## 겸색 예시

사용자 질문:
```
일본 취업 비자에서 경력 조건은 어떻게 돼?
```
Agent Sate:
```
country = Japan
purpose = Employment
selected_program = ...
```
Retrieval:
```
1. Japan Metadata Filter
2. Employment Filter
3. selected_program Filter
4. Query Embedding 생성
5. pgvector 검색
6. 관련 공식 문서 반환
```

---

## Document Chunk

공식 문서 전체를 하나의 Embedding으로 저장하지 않고 검색에 적절한 크기로 분할하여 저장합니다.

예상 구조:
```
Official Document
   ↓
Text Extraction
   ↓
Cleaning
   ↓
Chunking
   ↓
Embedding
   ↓
pgvector
```
각 Chunk에는 본문 뿐 아니라 출처 정보를 함께 저장합니다.

예:
```
chunk_id
document_id
content
embedding

country
purpose
program_id

official_agency
source_title
source_url

original_updated_at
verified_at
```

---

## Chunking 원칙

Chunking 시 다음을 고려합니다.
- 의미 단위 보존
- 너무 짧은 Chunk 방지
- 서로 다른 규정을 한 Chunk에 과도하게 포함하지 않음
- 제목 및 Section 정보 유지
- 출처 Metadata 유지
정확한 Chunk 크기와 Overlap은 실제 검색 성능을 평가한 뒤 결정합니다.

---

## Embedding

문서 Chunk와 사용자 Query를 Embedding Vector로 변환합니다.
```
Document
   ↓
Embedding Model
   ↓
Vector

User Query
   ↓
Embedding Model
   ↓
Vector
```
이후 pgvector에서 Vector Similarity를 계산하여 관련 문서를 검색합니다.

Embedding Model은 **구현 단계**에서 선택합니다.

---

## Retrieval 결과

Retrieval 결과는 단순 문자열이 아니라 가능한 한 구조화된 형태로 반환합니다.

예:
```
{
  "content": "공식 문서 내용",
  "country": "Japan",
  "program_id": "example_program",
  "official_agency": "Example Agency",
  "source_title": "Official Guide",
  "source_url": "https://...",
  "original_updated_at": "2026-01-01",
  "verified_at": "2026-10-17",
  "score": 0.91
}
```
실제 Schema는 `app/models/`에서 정의합니다.

---

## Evidence와 Retrieval의 차이

Retrieval 결과가 바로 최종 Evidence가 되는 것은 아닙니다.
```
Retrieval Result
   ↓
Evidence Check
   ↓
Validated Evidence
```
검색된 자료가 다음 조건을 만족하는지 추가로 확인합니다.
```
질문과 관련 있는가
국가가 일치하는가
프로그램이 일치하는가
공식 출처인가
정보가 최신 상태인가
```

---

## Program Resolver와 Retrieval의 차이

두 기능은 역할이 다릅니다.

### Program Resolver
```
어떤 프로그램을 검토할 것인가?
```
를 결정합니다. **주로 PostgreSQL의 구조화된 데이터를 조회**합니다.


### Retrieval
```
그 프로그램에 대한 공식 근거는 무엇인가?
```
를 검색합니다, **주로 pgvector에 저장된 공식 문서를 검색**합니다.

---

## 예상 파일 구조
```
app/retrieval/
├─ __init__.py
├─ retriever.py
├─ embeddings.py
├─ filters.py
├─ ranking.py
└─ README.md
```
실제 구조는 구현 과정에서 변경될 수 있습니다.

---

### retriever.py

pgvector 검색의 중심 로직을 구현합니다.

담당:
```
Query 입력
Metadata Filter 적용
Vector Search
검색 결과 반환
```


### embeddings.py

Embedding 생성과 관련된 기능을 관리합니다.

담당:
```
Query Embedding
Document Embedding
Embedding Model 설정
```


### filters.py

Metadata Filtering 조건을 생성합니다.

예:
```
country
purpose
program_id
document_type
```


### ranking.py

검색된 문서의 정렬 또는 추가 Ranking 로직을 담당합니다.

초기 MVP에서는 단순한 Vector Similarity 기반으로 시작하고, 필요할 경우 Re-ranking을 추가할 수 있습니다.


--- 

## Agent와의 관계
```
LangGraph
   ↓
Retrieval Node
   ↓
app/retrieval
   ↓
pgvector
   ↓
Official Documents
   ↓
Evidence 후보
   ↓
Evidence Check
```
Agent는 검색 알고리즘을 직접 구현하지 않고 Retrieval Module을 호출합니다.

---

## Services와의 관계

DB Connection이나 Embedding API 호출은 필요한 경우 `app/services/`를 통해 처리합니다.

---
## 구현 원칙
- 공식 출처 우선
- Vector Search 전에 Metadata Filtering 적용
- 검색 결과에 Source Metadata 포함
- 다른 국가 또는 프로그램 자료 혼입 최소화
- Retrieval 결과와 최종 Evidence 구분
- 출처 URL과 날짜 정보를 유지
- 검색 실패 시 LLM이 근거를 임의로 생성하지 않도록 처리
- 초기에는 단순하고 검증 가능한 검색 구조로 구현
- 필요 시 Re-ranking 추가

---

## 개발 순서
```
1. pgvector 연결
2. Document Schema 확정
3. Chunking 데이터 적재
4. Embedding 생성
5. Metadata Filter 구현
6. Vector Search 구현
7. Retrieval 결과 Model 연결
8. Evidence Check 연결
9. 검색 품질 평가
```

---

## 테스트 포인트
```
올바른 국가 문서가 검색되는가
올바른 프로그램 문서가 검색되는가
다른 국가 자료가 섞이지 않는가
공식 출처 Metadata가 유지되는가
출처 URL이 정상적으로 반환되는가
검색 결과가 없을 때 안전하게 처리되는가
오래된 자료를 구분할 수 있는가
```

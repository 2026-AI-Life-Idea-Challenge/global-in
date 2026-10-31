<div align="center">

# 🌍 Global-In

**맞춤형 해외진출 상담 및 자격 검토 멀티 에이전트**

일본·호주·미국·독일·캐나다의 워킹홀리데이·유학·취업 정보를 공식 근거로 추천하고,<br/>
신청 요건 검토부터 준비 절차까지 안내하는 AI 상담 서비스입니다.

![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_17-pgvector-4169E1?logo=postgresql&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI_API-412991?logo=openai&logoColor=white)

2026 AI 라이프 솔루션 챌린지 출품작 · 팀 **외부인들** · 아이디어 03번

</div>

| 홈 | AI 상담 |
|---|---|
| ![Global-In 홈 화면](docs/images/home.png) | ![AI 상담 화면](docs/images/chat.png) |

- **테스트 URL**: _배포 후 추가_
- **데모 영상**: _추가 예정_

---

## 해결하려는 문제

해외진출을 처음 준비하는 20~30대 청년은 다음 문제를 겪습니다.

- **정보가 흩어져 있음** — 대사관·이민청·외무성·KOTRA 사이트가 제각각입니다.
- **언어 장벽** — 공식 원문이 영어·일본어·독일어입니다.
- **내 상황에 맞는지 모름** — 나이·학력·경력·재정에 따라 자격 조건이 다릅니다.
- **비교가 어려움** — 같은 목적이라도 국가마다 자격·기간·비용·절차가 다릅니다.

Global-In은 단순 검색이 아니라, 대화로 사용자 조건을 파악하고 공식 근거에 맞춰 경로를 추천·검토합니다. 근거가 부족하거나 예외가 있는 경우에는 단정하지 않고 **‘추가 확인 필요’** 로 안내합니다.

## 주요 기능

| 기능 | 설명 |
|---|---|
| AI 상담 | 대화로 목적·국가·나이·학력·경력 등 조건을 파악하고, 빠진 정보만 추가로 질문합니다. |
| 맞춤 추천 | 조건에 맞는 비자·체류 프로그램과 국내외 지원제도를 추천하고 비교합니다. |
| 자격 검토 | 공식 요건과 사용자 조건을 비교해 **충족 / 추가 확인 필요 / 미충족** 으로 구분합니다. |
| 공식 정보 안내 | 검색된 공식 자료를 바탕으로 출처 URL과 함께 한국어로 답변합니다. |
| 준비 플랜 | 준비 → 신청 → 승인 → 출국 → 입국 후 단계별 체크리스트를 만들고 진행 상태를 관리합니다. |
| 프로그램·지원제도 찾기 | 국가·목적별로 프로그램과 지원제도를 탐색하고 비교표로 확인합니다. |

## 동작 구조

### 시스템 구성

브라우저는 프런트엔드만 호출합니다. 백엔드 호출에 필요한 내부 키는 Next.js 서버(API Route)에서만 붙이므로 브라우저에 노출되지 않습니다.

```mermaid
flowchart TB
    U(["👤 사용자"]) --> FE

    subgraph FE["Next.js 프런트엔드"]
        direction LR
        UI["화면<br/>상담 · 찾기 · 비교 · 플랜"] --> BFF["API Route<br/>내부 키 첨부"]
    end

    FE -- "X-Internal-API-Key" --> BE

    subgraph BE["FastAPI 백엔드"]
        direction LR
        API["상담 API<br/>/consult"] --> G["LangGraph<br/>오케스트레이터"]
        G --> S["하이브리드 검색"]
        S --> EMB["Qwen3 임베딩<br/>서버 내 실행"]
    end

    BE -- "답변 생성 · 근거 검증" --> LLM(["OpenAI API"])
    BE -- "규칙 · 근거 · 세션" --> DB[("PostgreSQL 17<br/>+ pgvector")]

    classDef ext fill:#f3f4f6,stroke:#9ca3af,color:#111827
    classDef core fill:#e0ecff,stroke:#3b82f6,color:#1e3a8a
    classDef store fill:#fef3c7,stroke:#d97706,color:#78350f
    class U,LLM ext
    class UI,BFF,API,G,S,EMB core
    class DB store
```

### 에이전트 흐름

LangGraph가 첫 단계에서 질문 의도를 파악한 뒤, **필요한 에이전트만** 이어서 호출합니다. 어느 단계든 판단에 필요한 정보가 부족하면 그 자리에서 멈추고 사용자에게 추가 질문을 돌려줍니다.

```mermaid
flowchart TD
    Q(["💬 사용자 메시지"]) --> UU["① 사용자 이해<br/>프로필 추출 · 의도 파악"]

    UU -- "추천 요청" --> RR["② 맞춤 추천<br/>프로그램 · 지원제도"]
    UU -- "자격 문의" --> ER["③ 자격 검토<br/>Python 규칙 평가"]
    UU -- "정보 문의" --> OI["④ 공식 정보 안내<br/>근거 검색 · 출처 표시"]
    UU -- "준비 문의" --> PP["⑤ 준비 계획<br/>단계별 체크리스트"]
    UU -- "정보 부족" --> ASK(["❓ 추가 질문"])

    RR --> ER
    ER --> OI
    OI --> PP
    PP --> A(["✅ 최종 응답"])

    classDef agent fill:#e0ecff,stroke:#3b82f6,color:#1e3a8a
    classDef io fill:#f3f4f6,stroke:#9ca3af,color:#111827
    classDef ask fill:#fef3c7,stroke:#d97706,color:#78350f
    class UU,RR,ER,OI,PP agent
    class Q,A io
    class ASK ask
```

### 자격 검토: 규칙이 판정하고 LLM은 설명

자격 요건 비교는 Python 규칙이 맡습니다. LLM은 판정 결과를 사용자에게 설명하는 역할만 합니다. 검증되지 않은 규칙이나 근거가 부족한 요건은 확정하지 않고 **추가 확인 필요**로 남깁니다.

```mermaid
flowchart LR
    P["사용자 프로필<br/>나이 · 국적 · 학력 · 경력 · 재정"] --> E{"Python 규칙 평가"}
    RS[("자격 규칙 · 요건<br/>공식 근거 연결")] --> E

    E -- "PASS" --> OK["✅ 충족"]
    E -- "UNKNOWN" --> UK["⚠️ 추가 확인 필요"]
    E -- "FAIL" --> NO["❌ 미충족"]

    OK & UK & NO --> X["LLM이 결과를 설명<br/>근거 · 출처와 함께"]

    classDef pass fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef warn fill:#fef3c7,stroke:#d97706,color:#78350f
    classDef fail fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    class OK pass
    class UK warn
    class NO fail
```

### 공식 정보 안내: 근거 우선 검색 (RAG)

국가·주제·프로그램 메타데이터로 범위를 먼저 좁힌 뒤 키워드 검색과 벡터 검색을 결합합니다. 답변의 인용문이 원문과 일치하는지 검사하고, 근거가 부족한 질문은 부분 답변이나 근거 부족으로 구분합니다.

```mermaid
flowchart TB
    Q["질문 + 사용자 프로필"] --> F["메타데이터 필터<br/>국가 · 주제 · 프로그램"]
    F --> K["키워드 검색<br/>PostgreSQL 전문 검색"]
    F --> V["벡터 검색<br/>pgvector"]
    K --> RRF["순위 결합<br/>RRF"]
    V --> RRF
    RRF --> D["LLM 답변 초안<br/>근거 ID 인용"]
    D --> C{"인용 검증<br/>원문 일치 · 근거 검토"}

    C -- "근거 충분" --> A1["✅ 답변 + 출처 URL"]
    C -- "일부만 확인" --> A2["⚠️ 부분 답변"]
    C -- "근거 없음" --> A3["ℹ️ 근거 부족 안내"]

    classDef pass fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef warn fill:#fef3c7,stroke:#d97706,color:#78350f
    classDef info fill:#f3f4f6,stroke:#9ca3af,color:#111827
    class A1 pass
    class A2 warn
    class A3 info
```

## 데이터

각국 이민청·대사관·외무성 등 공식 기관의 원문(HTML·PDF)을 수집·가공했습니다.

```mermaid
flowchart LR
    S["🏛️ 공식 기관 원문<br/>이민청 · 대사관 · 외무성"] --> C["수집<br/>HTML · PDF"]
    C --> P["가공<br/>정책 후보 · 근거 추출"]
    P --> R["검토<br/>원문 대조 · 법률 검토"]
    R --> DB[("PostgreSQL<br/>프로그램 · 정책 · 근거")]
    C --> CH["문서 청크"] --> EM["Qwen3 임베딩<br/>1024차원"] --> VDB[("pgvector")]

    classDef store fill:#fef3c7,stroke:#d97706,color:#78350f
    class DB,VDB store
```

| 항목 | 규모 |
|---|---|
| 대상 국가 | 5개국 (일본·호주·미국·독일·캐나다) |
| 비자·체류 프로그램 | 40건 (워킹홀리데이·유학·취업) |
| 자격·절차 정책 후보 | 590건 |
| 공식 원문 근거 (Evidence) | 1,241건 — 출처 URL·원문 위치·SHA-256 해시·확인일 저장 |
| 국내외 지원제도 | 12건 (한국 측 7 + 목적지 국가 관련 5) |
| 검색용 문서 / 청크 | 583건 / 585개 — Qwen3-Embedding-0.6B (1024차원), pgvector HNSW |

미국처럼 워킹홀리데이 제도가 없는 국가는 J-1 Summer Work Travel 등 실제 제도에 매핑해, 사용자에게 보이는 분류와 공식 제도명을 구분했습니다. 자세한 구축 현황은 [docs/data/db_final_status_20261028.md](docs/data/db_final_status_20261028.md)를 참고하세요.

## 기술 스택

| 영역 | 기술 |
|---|---|
| 프런트엔드 | Next.js 16, React 19, Tailwind CSS 4 |
| 백엔드 | FastAPI, Uvicorn, Pydantic |
| 에이전트 | LangGraph, OpenAI API |
| 데이터베이스 | PostgreSQL 17 + pgvector |
| 임베딩 | Qwen/Qwen3-Embedding-0.6B (transformers, torch) |
| 데이터 수집 | requests, BeautifulSoup |

## 실행 방법

### 준비물

- Python 3.11, Node.js 20 이상
- PostgreSQL 17과 pgvector 확장
- OpenAI API 키
- 팀에서 별도로 전달하는 DB 백업 파일(`.dump`) — 용량 때문에 저장소에는 포함하지 않습니다.

### 1. 데이터베이스 복원

```bash
createdb global_in
```

```bash
pg_restore -d global_in --no-owner --no-privileges global_in_xxx.dump
```

빈 DB에 백업을 복원할 때는 `scripts/init_db.sql`을 먼저 실행하지 않습니다(백업에 스키마가 포함되어 있습니다).

### 2. 백엔드 (FastAPI)

```bash
python3.11 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

`.env.example`을 `.env`로 복사한 뒤 값을 채웁니다.

| 변수 | 설명 |
|---|---|
| `DATABASE_URL` | 정책 DB 접속 주소 (`postgresql://USER:PASSWORD@HOST:5432/global_in`) |
| `INTERNAL_API_KEY` | 내부 API 인증 키. 프런트엔드와 같은 값을 사용합니다. |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `CONSULT_SESSION_DATABASE_URL` | (선택) 상담 세션 저장소. 비우면 `data/runtime/consultation.sqlite`를 사용합니다. |

```bash
uvicorn app.api.main:app --reload --port 8000
```

API 문서는 http://localhost:8000/docs 에서 확인할 수 있습니다.

검색에 쓰는 임베딩 모델(Qwen3-Embedding-0.6B, 약 1.2GB)은 실행 중에 자동으로 내려받지 않습니다. 처음 한 번만 아래 명령으로 받아 둡니다.

```bash
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-Embedding-0.6B', revision='97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3')"
```

### 3. 프런트엔드 (Next.js)

```bash
cd frontend
```

```bash
npm install
```

`frontend/.env.example`을 `frontend/.env.local`로 복사한 뒤 `BACKEND_URL`(기본 `http://localhost:8000`)과 `INTERNAL_API_KEY`(백엔드와 같은 값)를 채웁니다.

```bash
npm run dev
```

http://localhost:3000 에서 서비스를 사용할 수 있습니다.

### 4. 테스트

```bash
python -m pytest tests/unit
```

`tests/unit/test_rule_evaluator.py`는 지식 릴리즈 파일(`data/processed/knowledge/20261028/releases/.../knowledge_release.json`)이 있어야 실행되며, 이 파일은 DB 백업과 함께 별도로 전달합니다. `tests/integration`은 복원된 DB가 필요합니다.

## 배포

프런트엔드는 Vercel, 백엔드와 DB는 Railway에 올리는 구성을 기준으로 합니다. 백엔드는 루트의 `Dockerfile`로 빌드하며, 임베딩 모델이 이미지에 포함되어 메모리가 4GB 이상 필요합니다.

```mermaid
flowchart LR
    U(["👤 사용자"]) -- "HTTPS" --> V["Vercel<br/>Next.js"]
    V -- "BACKEND_URL<br/>+ 내부 키" --> B["Railway<br/>FastAPI (Docker)"]
    B -- "내부 네트워크" --> D[("Railway<br/>PostgreSQL + pgvector")]
    B --> O(["OpenAI API"])
```

단계별 절차와 환경변수는 [docs/DEPLOY.md](docs/DEPLOY.md)를 참고하세요.

## API

공개 API는 인증 없이, 내부 API와 상담 API는 `X-Internal-API-Key` 헤더로 호출합니다.

| 구분 | Method | Endpoint | 설명 |
|---|---|---|---|
| 공개 | GET | `/health` | 상태 확인 |
| 공개 | GET | `/public/programs` | 프로그램 목록 (`country`, `category`, `limit`, `offset`) |
| 공개 | GET | `/public/programs/{program_id}` | 프로그램 상세 |
| 공개 | GET | `/public/support-programs` | 지원제도 목록 |
| 내부 | GET | `/programs`, `/programs/{program_id}` | 프로그램 및 내부 메타데이터 |
| 내부 | GET | `/programs/{program_id}/policies` | 정책 후보 |
| 내부 | GET | `/programs/{program_id}/evidence` | 원문 근거 |
| 내부 | GET | `/support-programs` | 지원제도 및 메타데이터 |
| 상담 | POST | `/consult/sessions` 외 | 상담 세션 생성, 메시지 전송, 카탈로그·준비 플랜 조회 |

## 프로젝트 구조

```text
global-in/
├── app/
│   ├── agent/       # LangGraph 그래프와 5개 에이전트
│   ├── api/         # FastAPI 엔트리포인트, 상담 라우터
│   ├── retrieval/   # 메타데이터 필터, 키워드·벡터·하이브리드 검색
│   ├── rules/       # 자격 요건 규칙 평가기
│   ├── models/      # Pydantic 모델, 프로그램 매핑
│   └── services/    # LLM 호출, 상담 세션 저장소
├── frontend/        # Next.js 웹 앱 (상담, 프로그램 찾기, 비교, 플랜, 프로필)
├── data/            # 수집 원문(raw)과 가공 데이터(processed)
├── scripts/         # 수집·적재·검색 평가 스크립트, init_db.sql
├── tests/           # 단위·통합 테스트
├── docs/            # 설계, 데이터 현황, 법률 검토, 배포 문서
└── Dockerfile       # 백엔드 배포 이미지
```

## 한계와 개선 방향

- **법적 검증 범위**: 정책 데이터는 내부 검토를 거쳤지만 법률상 최종 승인본은 아닙니다. 그래서 확정적인 비자 발급·자격 판정 대신 출처와 확인일을 함께 보여주고, 예외는 ‘추가 확인 필요’로 안내합니다.
- **접수 가능 여부**: 지원제도의 현재 모집 상태는 일부만 확인되어 있습니다(UNKNOWN 유지). 모집 공고 연동이 다음 과제입니다.
- **정보 최신성**: 정책 자동 갱신은 아직 없습니다. 원문 해시와 확인일을 저장하는 구조를 바탕으로 변경 감지와 재수집을 자동화할 계획입니다.
- **범위**: 5개국 40개 프로그램이 대상입니다. 공통 스키마를 따르므로 국가·경로는 데이터만 추가해 넓힐 수 있습니다.
- **운영 비용**: 임베딩 모델을 서버에서 직접 실행하므로 메모리가 큰 서버가 필요합니다.

## 팀 외부인들

| 이름 | 소속 |
|---|---|
| 고여은 | 선문대학교 컴퓨터공학부 |
| 김미진 | 한국외국어대학교 컴퓨터공학부 |
| 조혜린 | 한국외국어대학교 컴퓨터공학부 |
| 홍혜원 | 한국외국어대학교 산업경영학부 |

초기 설계 문서(에이전트 역할 정의, 데이터 원칙 등)는 [docs/planning/design-overview.md](docs/planning/design-overview.md)에 있습니다.

# 배포 가이드

배포는 세 부분으로 나뉜다.

| 구성 | 호스팅 | 결과 URL 예시 |
|---|---|---|
| 정책 DB (PostgreSQL 17 + pgvector) | Railway | 비공개 (Railway 내부 네트워크) |
| 백엔드 (FastAPI, `Dockerfile`) | Railway | `https://global-in-api.up.railway.app` |
| 프론트엔드 (Next.js, `frontend/`) | Vercel | `https://global-in.vercel.app` ← 공유할 주소 |

브라우저는 프론트엔드만 호출한다. 프론트엔드 서버가 `INTERNAL_API_KEY`를 붙여 백엔드를 호출하므로, 이 키는 브라우저에 노출되지 않는다.

아래 URL은 배포 예시이며 실제 서비스 주소가 아니다. 배포 전 현재 작업을 커밋하고 배포 대상 브랜치·환경변수를 확인한다. 로컬에서 문서를 검토하거나 빌드하는 것만으로 서비스가 배포되지는 않는다.

## 0. 준비

- 계정: GitHub, Railway(Hobby 플랜 권장), Vercel
- 비밀값 두 개를 생성해 둔다.

```bash
python3 -c "import secrets; print('INTERNAL_API_KEY=' + secrets.token_hex(32)); print('CONSULT_OWNER_SECRET=' + secrets.token_hex(32))"
```

- OpenAI API 키
- 배포할 코드가 GitHub `develop`(또는 배포용 브랜치)에 push되어 있어야 한다.

## 1. DB (Railway)

1. Railway에서 New Project를 만들고 템플릿 **pgvector**로 Postgres를 추가한다. 버전이 **17 이상**인지 확인한다. 덤프가 17.11 서버에서 생성되었다.
2. DB 서비스의 Variables에서 외부 접속용 `DATABASE_PUBLIC_URL`을 복사한다.
3. 로컬에서 덤프를 복원한다. pg_restore가 없으면 Docker로 실행한다.

```bash
export DB_PUBLIC_URL='postgresql://...railway...'
```

```bash
docker run --rm -v "$PWD":/dump:ro pgvector/pgvector:pg17 pg_restore --no-owner --no-privileges --dbname "$DB_PUBLIC_URL" /dump/global_in_current_20261028_192738.dump
```

4. 상담 세션 테이블(`consult_runtime` 스키마)을 한 번 생성한다.

```bash
CONSULT_SESSION_DATABASE_URL="$DB_PUBLIC_URL" .venv/bin/python -c "import os; from app.services.postgres_sessions import PostgresSessions; PostgresSessions(os.environ['CONSULT_SESSION_DATABASE_URL']).initialize()"
```

위 명령은 Bash 기준이다. Windows PowerShell에서는 가상환경을 만든 저장소 루트에서 다음과 같이 실행한다. `$env:DB_PUBLIC_URL`에는 외부 접속용 DB 주소를 설정한다.

```powershell
$env:CONSULT_SESSION_DATABASE_URL = $env:DB_PUBLIC_URL
.\.venv\Scripts\python.exe -c "import os; from app.services.postgres_sessions import PostgresSessions; PostgresSessions(os.environ['CONSULT_SESSION_DATABASE_URL']).initialize()"
```

## 2. 백엔드 (Railway)

1. 같은 프로젝트에서 New → GitHub Repo → `global-in`을 선택한다. 루트의 `Dockerfile`이 자동으로 사용된다.
   - 이미지에는 Qwen3-Embedding-0.6B 모델이 포함되며 크기는 약 1.4GB(압축)다. 첫 빌드에 10분 이상 걸릴 수 있다.
   - 첫 검색 요청 때 모델을 메모리에 올리며, 이때 약 3GB를 사용한다. 서비스 메모리 한도를 **4GB 이상**으로 둔다.
   - Railway는 사용량 과금이다. 모델이 올라간 상태로 계속 켜 두면 메모리 비용이 대부분을 차지하므로, 시연 기간이 끝나면 서비스를 중지한다.
2. Variables를 입력한다. DB 서비스 이름이 `pgvector`라면 다음과 같다.

| 변수 | 값 |
|---|---|
| `DATABASE_URL` | `${{pgvector.DATABASE_URL}}` (내부 URL) |
| `CONSULT_SESSION_DATABASE_URL` | `${{pgvector.DATABASE_URL}}` |
| `INTERNAL_API_KEY` | 0단계에서 생성한 값 |
| `OPENAI_API_KEY` | OpenAI 키 |

3. Settings에서 Healthcheck Path를 `/health`로 지정하고, Networking → Generate Domain으로 공개 URL을 발급한다.
4. 확인한다. `{"status":"ok"}`가 나오면 성공이다.

```bash
curl https://<백엔드 도메인>/health
```

## 3. 프론트엔드 (Vercel)

1. Vercel에서 Add New → Project → `global-in` 저장소를 import한다.
2. **Root Directory를 `frontend`로 지정**한다. Framework는 Next.js로 자동 인식된다.
3. Environment Variables를 입력한다.

| 변수 | 값 |
|---|---|
| `BACKEND_URL` | `https://<백엔드 도메인>` (끝에 `/` 없이) |
| `INTERNAL_API_KEY` | 백엔드와 같은 값 |
| `CONSULT_OWNER_SECRET` | 0단계에서 생성한 값 |
| `CONSULT_PUBLIC_ORIGIN` | 비워 둔다. 프록시 뒤에서 접속 주소가 다르게 보일 때만 `https://<실제 도메인>`을 넣는다 |

4. Deploy 후 Vercel 도메인에 접속해 상담 화면(`/chat`)에서 질문을 보내 본다.

5. 상담뿐 아니라 프로그램 목록·상세, 프로필 반영, 준비 플랜도 확인한다. 현재 프런트엔드 상담 요청의 백엔드 대기 제한은 120초이며, 백엔드 상담 처리 예산은 기본 100초다. 호스팅의 함수 실행 시간 제한이 이 요청을 처리할 수 있도록 배포 설정을 확인한다. `/health` 성공만으로 DB 검색·AI 답변까지 검증되지는 않는다.

## 업데이트

- GitHub에 push하면 Railway와 Vercel이 각각 자동으로 재배포한다. 배포할 브랜치는 각 서비스 Settings에서 지정한다.
- DB 내용을 바꾸면 새 덤프를 1단계와 같은 방법으로 복원한다. 기존 테이블이 있으면 `pg_restore`에 `--clean --if-exists`를 추가한다.

## 문제 해결

| 증상 | 확인할 것 |
|---|---|
| 백엔드가 시작 직후 종료 | `DATABASE_URL` 누락 또는 오타. 시작 시 DB 연결을 검사한다. |
| 프론트에서 401/503 | 양쪽 `INTERNAL_API_KEY` 값이 같은지, 백엔드에 값이 설정되어 있는지 |
| 키를 맞췄는데도 인증 실패 | 환경변수를 변경한 프런트엔드와 백엔드를 모두 재배포했는지 |
| 상담 요청 시 403 (cross-origin) | `CONSULT_PUBLIC_ORIGIN`을 설정했다면 실제 접속 주소(https 포함)와 정확히 같은지 |
| 상담 중 "session store unavailable" | 1-4단계 세션 테이블 생성 여부 |
| 검색 단계에서 메모리 부족(OOM) | 백엔드 메모리 한도를 4GB 이상으로 올린다 |
| 프로그램 검색에서 로컬 임베딩을 사용할 수 없다는 경고 | 패키지와 모델 캐시를 확인한다. 프로그램 검색은 키워드 검색으로 이어지지만 검색 결과가 달라질 수 있다. |

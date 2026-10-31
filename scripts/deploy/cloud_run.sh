#!/usr/bin/env bash
# 백엔드를 Google Cloud Run에 배포한다 (Cloud Build가 루트 Dockerfile로 이미지를 빌드).
#
# 필요한 파일 (둘 다 git에 올라가지 않음):
#   .env.local   neon link가 만든 DATABASE_URL, DATABASE_URL_UNPOOLED
#   .env.deploy  INTERNAL_API_KEY, OPENAI_API_KEY
# 사용법: GCP_PROJECT=<프로젝트 ID> scripts/deploy/cloud_run.sh
set -euo pipefail

PROJECT="${GCP_PROJECT:?GCP_PROJECT에 Google Cloud 프로젝트 ID를 지정하세요}"
# Neon DB(ap-southeast-2, 시드니)와 같은 지역에 두어 DB 왕복 지연을 줄인다.
REGION="${GCP_REGION:-australia-southeast1}"
SERVICE="${GCP_SERVICE:-global-in-api}"

cd "$(dirname "$0")/../.."
set -a
. ./.env.local
. ./.env.deploy
set +a

for name in DATABASE_URL DATABASE_URL_UNPOOLED INTERNAL_API_KEY OPENAI_API_KEY; do
  [ -n "${!name:-}" ] || { echo "$name 값이 비어 있습니다" >&2; exit 1; }
done

env_file="$(mktemp)"
trap 'rm -f "$env_file"' EXIT
chmod 600 "$env_file"
# 상담 세션 저장소는 statement_timeout 시작 옵션을 쓰므로 Neon pooler가 아닌 direct 주소를 쓴다.
python3 - "$env_file" <<'EOF'
import json, os, sys
values = {
    "DATABASE_URL": os.environ["DATABASE_URL"],
    "CONSULT_SESSION_DATABASE_URL": os.environ["DATABASE_URL_UNPOOLED"],
    "INTERNAL_API_KEY": os.environ["INTERNAL_API_KEY"],
    "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
}
# Langfuse 트레이싱(선택): .env.deploy에 키가 있을 때만 켠다.
for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
    if os.environ.get(name):
        values[name] = os.environ[name]
if "LANGFUSE_PUBLIC_KEY" in values:
    values["LANGFUSE_TRACING_ENVIRONMENT"] = "production"
with open(sys.argv[1], "w") as f:
    f.writelines(f"{k}: {json.dumps(v)}\n" for k, v in values.items())
EOF

# 임베딩 모델 때문에 메모리 4Gi가 필요하다. 접속이 없으면 0대로 줄어 비용이 들지 않고, 최대 1대로 비용 상한을 둔다.
gcloud run deploy "$SERVICE" \
  --project "$PROJECT" --region "$REGION" --source . \
  --memory 4Gi --cpu 2 --cpu-boost \
  --min-instances 0 --max-instances 1 --concurrency 4 --timeout 300 \
  --allow-unauthenticated \
  --env-vars-file "$env_file" \
  --quiet

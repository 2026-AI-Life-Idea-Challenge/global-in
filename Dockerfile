# Global-In FastAPI 백엔드 이미지 (Railway / Render 등 Docker 호스팅용)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf

WORKDIR /srv

# torch는 CPU 전용 휠을 먼저 설치해 CUDA 휠(수 GB)이 받아지지 않게 한다.
COPY requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.7.1 \
 && pip install -r requirements.txt

# query_embedding.py는 local_files_only=True로 모델을 읽으므로 빌드 시점에 같은 revision을 받아 둔다.
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-Embedding-0.6B', revision='97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3')"

COPY app ./app

RUN useradd --create-home appuser && mkdir -p data/runtime && chown -R appuser /srv
USER appuser

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

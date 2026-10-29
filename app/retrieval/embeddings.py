"""
app/retrieval/embeddings.py

Query 및 문서 청크 Embedding 생성.
DB 저장 임베딩과 동일한 모델(Qwen/Qwen3-Embedding-0.6B, 1024차원)을 사용합니다.
"""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

_EMB_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Embedding 모델 로딩: {_EMB_MODEL}")
        _model = SentenceTransformer(_EMB_MODEL)
        logger.info("Embedding 모델 로딩 완료")
    return _model


def embed_query(text: str) -> list[float]:
    """단일 Query 텍스트를 Embedding 벡터로 변환합니다."""
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """여러 텍스트를 한 번에 Embedding 합니다."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]

"""
app/retrieval/embeddings.py

Query 및 문서 청크 Embedding 생성.
실제 Embedding API 연결을 담당하며, 모델 선택은 환경 변수로 제어합니다.
"""
from __future__ import annotations

import os
from typing import Any

import anthropic

# Anthropic Embeddings (voyage-3) 사용 — 한국어·영어·다국어 성능 우수
_EMB_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-3")


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
    return anthropic.Anthropic(api_key=api_key)


def embed_query(text: str) -> list[float]:
    """
    단일 Query 텍스트를 Embedding 벡터로 변환합니다.
    """
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    여러 텍스트를 한 번의 API 호출로 Embedding 합니다.

    Returns:
        각 텍스트에 대한 벡터 리스트
    """
    client = _get_client()
    response = client.embeddings.create(
        model=_EMB_MODEL,
        input=texts,
        input_type="query",
    )
    # anthropic SDK: response.embeddings[i].embedding
    return [item.embedding for item in response.embeddings]

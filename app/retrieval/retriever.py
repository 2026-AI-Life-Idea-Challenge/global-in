"""
app/retrieval/retriever.py

Retrieval 핵심 실행 로직.
1. Query Embedding 생성
2. Metadata Filtering (knowledge_chunks.metadata jsonb)
3. pgvector Similarity Search (knowledge_chunk_embeddings)
4. Ranking
5. 결과 반환
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.retrieval.embeddings import embed_query
from app.services.db import get_conn

logger = logging.getLogger(__name__)


def _build_metadata_where(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    """
    filters 딕셔너리를 knowledge_chunks.metadata jsonb 기반 WHERE 절로 변환.

    지원 필터 키:
        destination_country  → metadata->'destination_countries' @> '["AU"]'
        information_topic    → metadata->'topics' @> '["eligible_occupation"]'
        program_id           → metadata->'targets' @> '["AU:subclass_186_de"]'
    """
    clauses: list[str] = []
    params: list[Any] = []

    mapping = {
        "destination_country": "destination_countries",
        "information_topic": "topics",
        "program_id": "targets",
    }

    for filter_key, meta_key in mapping.items():
        val = filters.get(filter_key)
        if not val:
            continue
        values = val if isinstance(val, list) else [val]
        clauses.append(f"c.metadata->'{meta_key}' @> %s::jsonb")
        params.append(json.dumps(values))

    where = (" AND " + " AND ".join(clauses)) if clauses else ""
    return where, params


def retrieve(
    query_text: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 10,
    similarity_threshold: float = 0.5,
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    """
    pgvector 기반 Retrieval 을 실행하고 결과를 반환합니다.

    Returns:
        dict 리스트. 각 항목:
            chunk_id, document_id, content, score,
            destination_country, source_title, information_topic
        없으면 빈 리스트.
    """
    if not filters:
        filters = {}

    # 1. Query Embedding
    try:
        query_vector = embed_query(query_text)
    except Exception as e:
        logger.warning(f"Embedding 생성 실패: {e}")
        return []

    # 2. Metadata Filter → SQL
    where_clause, filter_params = _build_metadata_where(filters)

    # 3. pgvector cosine similarity search
    vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

    sql = f"""
        SELECT
            c.chunk_id,
            c.document_id,
            c.revision_id,
            c.body                          AS content,
            c.metadata->>'title'            AS source_title,
            (c.metadata->'destination_countries'->>0) AS destination_country,
            (c.metadata->'topics'->>0)      AS information_topic,
            c.metadata                      AS metadata,
            1 - (e.embedding <=> %s::vector) AS score
        FROM knowledge_chunks c
        JOIN knowledge_chunk_embeddings e ON c.chunk_id = e.chunk_id
        WHERE c.active = true
          AND c.embedding_approved = true
          {where_clause}
          AND 1 - (e.embedding <=> %s::vector) >= %s
        ORDER BY e.embedding <=> %s::vector
        LIMIT %s
    """

    params = (
        [vector_literal]
        + filter_params
        + [vector_literal, similarity_threshold, vector_literal, top_k * 3]
    )

    try:
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception as e:
        logger.warning(f"pgvector 검색 실패: {e}")
        return []

    if not rows:
        return []

    # dict 변환
    keys = [
        "chunk_id", "document_id", "revision_id", "content",
        "source_title", "destination_country", "information_topic",
        "metadata", "score",
    ]
    results = [dict(zip(keys, row)) for row in rows]

    return results[:top_k]


def retrieve_relevant_chunks(
    query_text: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 5,
    similarity_threshold: float = 0.45,
) -> list[dict[str, Any]]:
    """
    official_information 에이전트에서 사용하는 간단한 래퍼.
    chunk_text 키로 본문을 반환합니다.
    """
    raw = retrieve(
        query_text=query_text,
        filters=filters,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
    )
    # official_information.py 가 기대하는 키 형식으로 변환
    out = []
    for r in raw:
        out.append({
            "chunk_text": r.get("content", ""),
            "chunk_id": r.get("chunk_id", ""),
            "document_id": r.get("document_id", ""),
            "source_title": r.get("source_title", ""),
            "destination_country": r.get("destination_country"),
            "information_topic": r.get("information_topic"),
            "score": r.get("score", 0.0),
        })
    return out

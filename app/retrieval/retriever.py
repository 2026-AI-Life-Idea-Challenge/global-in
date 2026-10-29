"""
app/retrieval/retriever.py

Retrieval 핵심 실행 로직.
1. Query Embedding 생성
2. Metadata Filtering (SQL WHERE 절)
3. pgvector Similarity Search
4. Ranking
5. Evidence 후보 반환

document_chunks 테이블 예상 스키마:
    chunk_id          TEXT PRIMARY KEY
    document_id       TEXT
    content           TEXT
    embedding         vector(...)
    destination_country TEXT
    issuer_country    TEXT
    purpose           TEXT
    program_id        TEXT
    support_program_id TEXT
    target_nationality TEXT
    information_topic TEXT
    source_type       TEXT
    official_agency   TEXT
    source_title      TEXT
    source_url        TEXT
    original_updated_at DATE
    effective_from    DATE
    effective_until   DATE
    verified_at       DATE
"""
from __future__ import annotations

import json
from typing import Any

from app.retrieval.embeddings import embed_query
from app.retrieval.filters import filters_to_sql_where
from app.retrieval.ranking import rank
from app.retrieval.evidence import validate_all
from app.services.db import get_conn


_TABLE = "document_chunks"


def retrieve(
    query_text: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 10,
    similarity_threshold: float = 0.5,
    as_of: str | None = None,
) -> list[dict[str, Any]]:
    """
    pgvector 기반 Retrieval 을 실행하고 검증된 Evidence 후보를 반환합니다.

    Args:
        query_text: 검색할 텍스트 (사용자 질문 + 맥락)
        filters: Metadata 필터 (build_filters() 반환값)
        top_k: 최종 반환 개수
        similarity_threshold: 최소 유사도 (이하 결과 제외)
        as_of: Evidence 검증 기준일

    Returns:
        ValidatedEvidence 후보 list (is_valid=True 인 것만)
        없으면 빈 리스트.
    """
    if not filters:
        filters = {}

    # 1. Query Embedding
    try:
        query_vector = embed_query(query_text)
    except Exception as e:
        # Embedding API 오류 시 빈 결과 반환 (안전 처리)
        import logging
        logging.getLogger(__name__).warning(f"Embedding 생성 실패: {e}")
        return []

    # 2. Metadata Filter → SQL
    where_clause, filter_params = filters_to_sql_where(filters)

    # 3. pgvector cosine similarity search
    # 벡터를 PostgreSQL array literal 로 변환
    vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

    sql = f"""
        SELECT
            chunk_id,
            document_id,
            content,
            destination_country,
            issuer_country,
            purpose,
            program_id,
            support_program_id,
            target_nationality,
            information_topic,
            source_type,
            official_agency,
            source_title,
            source_url,
            original_updated_at::text,
            effective_from::text,
            effective_until::text,
            verified_at::text,
            1 - (embedding <=> %s::vector) AS score
        FROM {_TABLE} c
        WHERE 1=1
          {where_clause}
          AND 1 - (embedding <=> %s::vector) >= %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    try:
        with get_conn() as conn:
            rows = conn.execute(
                sql,
                [vector_literal] + filter_params + [vector_literal, similarity_threshold, vector_literal, top_k * 3],
            ).fetchall()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"pgvector 검색 실패: {e}")
        return []

    if not rows:
        return []

    # 4. Ranking
    ranked = rank(list(rows), filters, top_k=top_k * 2)

    # 5. Evidence Validation
    validated = validate_all(ranked, filters, as_of)

    return validated[:top_k]

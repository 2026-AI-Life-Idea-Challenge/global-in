"""Search active program evidence by exact pgvector cosine similarity."""

from math import isfinite
from numbers import Real

from pgvector import Vector
from psycopg.rows import dict_row

from app.retrieval.query_embedding import EMBEDDING_DIMENSION, MODEL_NAME
from app.services.database import get_connection


def search_program_evidence_by_vector(
    program_id: str,
    query_vector: list[float],
    limit: int = 5,
) -> list[dict]:
    """Return evidence chunks by similarity, then chunk_id for equal scores.

    Similarity is not a probability of correctness or answer-use approval.
    Invalid inputs raise ValueError before connecting; DB errors propagate.
    """
    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id는 비어 있지 않은 문자열이어야 합니다.")
    program_id = program_id.strip()

    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit은 1 이상 100 이하의 정수여야 합니다.")

    if not isinstance(query_vector, list) or len(query_vector) != EMBEDDING_DIMENSION:
        raise ValueError("query_vector는 숫자 1024개를 담은 리스트여야 합니다.")

    values: list[float] = []
    for value in query_vector:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("query_vector의 원소는 bool을 제외한 실수여야 합니다.")
        try:
            number = float(value)
        except (OverflowError, ValueError) as error:
            raise ValueError("query_vector의 원소는 유한한 실수여야 합니다.") from error
        if not isfinite(number):
            raise ValueError("query_vector의 원소는 유한한 실수여야 합니다.")
        values.append(number)

    # pgvector stores float32: validate the actual representation before DB I/O.
    try:
        vector = Vector(values)
    except (OverflowError, ValueError) as error:
        raise ValueError("query_vector를 float32 벡터로 변환할 수 없습니다.") from error
    stored_values = vector.to_list()
    if not all(isfinite(value) for value in stored_values):
        raise ValueError("query_vector는 float32로도 유한한 값이어야 합니다.")
    if not any(value != 0.0 for value in stored_values):
        raise ValueError("query_vector는 0벡터일 수 없습니다.")

    query = """
        WITH candidates AS MATERIALIZED (
            SELECT
                p.program_id,
                d.document_id,
                d.revision_id,
                c.chunk_id,
                c.ordinal,
                d.title,
                c.body,
                d.knowledge_kind,
                d.metadata AS document_metadata,
                d.active AS document_active,
                c.active AS chunk_active,
                c.embedding_approved AS chunk_embedding_approved,
                d.release_id AS document_release_id,
                c.release_id AS chunk_release_id,
                e.embedding
            FROM public.programs AS p
            JOIN public.knowledge_document_targets AS t
              ON t.target_id = p.program_id
             AND t.target_type = %s
            JOIN public.knowledge_documents AS d
              ON d.document_id = t.document_id
             AND d.revision_id = t.revision_id
            JOIN public.knowledge_chunks AS c
              ON c.document_id = d.document_id
             AND c.revision_id = d.revision_id
            JOIN public.knowledge_chunk_embeddings AS e
              ON e.chunk_id = c.chunk_id
             AND e.document_id = c.document_id
             AND e.revision_id = c.revision_id
             AND e.embedding_model = %s
            WHERE p.program_id = %s
              AND d.active = TRUE
              AND c.active = TRUE
        )
        SELECT
            program_id,
            document_id,
            revision_id,
            chunk_id,
            ordinal,
            title,
            body,
            knowledge_kind,
            document_metadata -> 'source_references' AS source_references,
            document_active,
            chunk_active,
            document_metadata -> 'embedding_approved'
                AS document_embedding_approved,
            chunk_embedding_approved,
            document_metadata -> 'answer_approved' AS answer_approved,
            document_metadata -> 'content_review_status' AS content_review_status,
            document_release_id,
            chunk_release_id,
            1 - (embedding <=> %s::public.vector) AS similarity
        FROM candidates
        ORDER BY similarity DESC, chunk_id ASC
        LIMIT %s
    """

    # Materializing the program's candidates avoids approximate global-index
    # retrieval dropping matching chunks before program/active filters apply.
    # Target PK and UNIQUE(chunk_id, embedding_model) ensure one row per chunk.
    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                query,
                ("PROGRAM", MODEL_NAME, program_id, vector.to_text(), limit),
            )
            rows = cursor.fetchall()

    for row in rows:
        references = row["source_references"]
        if references is None:
            references = []
        row["source_references"] = references

        source_urls: list[str] = []
        seen_urls: set[str] = set()
        for reference in references:
            source_url = reference.get("source_url")
            if (
                isinstance(source_url, str)
                and source_url.strip()
                and source_url not in seen_urls
            ):
                seen_urls.add(source_url)
                source_urls.append(source_url)
        row["source_urls"] = source_urls

    return rows

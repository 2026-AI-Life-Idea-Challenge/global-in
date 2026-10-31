from psycopg.rows import dict_row

from app.services.database import get_connection


def search_program_evidence(
    program_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """프로그램에 연결된 활성 문서·청크를 내부 자료로 조회한다.

    반환 결과는 사용자 답변 사용 승인이나 자격 충족을 뜻하지 않는다.
    """
    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id는 비어 있지 않은 문자열이어야 합니다.")

    program_id = program_id.strip()

    # bool은 int의 하위 타입이므로 정확한 int만 허용한다.
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit은 1 이상 100 이하의 정수여야 합니다.")

    if type(offset) is not int or offset < 0:
        raise ValueError("offset은 0 이상의 정수여야 합니다.")

    query = """
        SELECT
            p.program_id,
            d.document_id,
            d.revision_id,
            c.chunk_id,
            c.ordinal,
            d.title,
            c.body,
            d.knowledge_kind,
            d.metadata -> 'source_references' AS source_references,
            d.active AS document_active,
            c.active AS chunk_active,
            d.metadata -> 'embedding_approved'
                AS document_embedding_approved,
            c.embedding_approved AS chunk_embedding_approved,
            d.metadata -> 'answer_approved' AS answer_approved,
            d.metadata -> 'content_review_status' AS content_review_status,
            d.release_id AS document_release_id,
            c.release_id AS chunk_release_id
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
        WHERE p.program_id = %s
          AND d.active = TRUE
          AND c.active = TRUE
        ORDER BY d.document_id, d.revision_id, c.ordinal, c.chunk_id
        LIMIT %s OFFSET %s
    """

    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, ("PROGRAM", program_id, limit, offset))
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

"""지원제도에 연결된 활성 문서·청크를 내부 자료로 조회한다."""

from psycopg.rows import dict_row

from app.services.database import get_connection


def search_support_evidence(
    support_program_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """지원제도별 활성 근거를 문서·개정·청크 순서로 반환한다.

    기존 프로그램 근거의 18개 필드 중 program_id를 support_program_id로
    구분한다. 문서·청크는 document_id와 revision_id를 모두 사용해 연결하며
    release_id 일치나 답변·임베딩 승인 여부로 필터링하지 않는다.
    대상 연결의 복합 기본키와 chunk_id 기본키로 청크당 한 행을 조회한다.
    같은 본문을 가진 서로 다른 청크는 각각 유지한다.

    출처는 문서 metadata.source_references를 보존하고, source_urls에는
    비어 있지 않은 원본 source_url을 최초 순서대로 중복 제거해 담는다.
    URL의 fragment를 유지하며 다른 URL 필드로 대체하지 않는다.
    출처가 없으면 두 출처 배열은 [], 누락된 문서 상태는 None이다.

    결과는 사용자 답변 사용 승인이나 개인의 자격 충족을 뜻하지 않는다.
    []는 조회된 활성 근거가 없다는 뜻이다. 입력 오류는 DB 연결 전에
    ValueError로 처리하며 DB 및 SQL 오류는 그대로 전달한다.
    """
    if not isinstance(support_program_id, str) or not support_program_id.strip():
        raise ValueError("support_program_id는 비어 있지 않은 문자열이어야 합니다.")
    support_program_id = support_program_id.strip()
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit은 1 이상 100 이하의 정수여야 합니다.")
    if type(offset) is not int or offset < 0:
        raise ValueError("offset은 0 이상의 정수여야 합니다.")

    query = """
        SELECT
            t.target_id AS support_program_id,
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
        FROM public.knowledge_document_targets AS t
        JOIN public.knowledge_documents AS d
          ON d.document_id = t.document_id
         AND d.revision_id = t.revision_id
        JOIN public.knowledge_chunks AS c
          ON c.document_id = d.document_id
         AND c.revision_id = d.revision_id
        WHERE t.target_type = %s
          AND t.target_id = %s
          AND d.active = TRUE
          AND c.active = TRUE
        ORDER BY d.document_id, d.revision_id, c.ordinal, c.chunk_id
        LIMIT %s OFFSET %s
    """

    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, ("SUPPORT_PROGRAM", support_program_id, limit, offset))
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

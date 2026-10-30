"""Search all filtered programs with global keyword/vector rankings and RRF.

Single-program search and RAG are unchanged. Each result represents one chunk;
program_ids/programs contain every link within the requested program scope.
Scores describe retrieval order, not eligibility, suitability or answer approval.
"""

from pgvector import Vector
from psycopg import IsolationLevel
from psycopg.rows import dict_row

from app.retrieval.hybrid_search import EVIDENCE_FIELDS, RRF_K
from app.retrieval.keyword_search import (
    TEXT_SEARCH_CONFIG, _build_tsquery, expand_search_terms,
)
from app.retrieval.program_search import (
    SUPPORTED_CATEGORIES, SUPPORTED_COUNTRIES, _validate_filter,
)
from app.retrieval.query_embedding import MODEL_NAME, embed_query_local
from app.services.database import get_connection


MULTI_EVIDENCE_FIELDS = tuple(
    field for field in EVIDENCE_FIELDS if field != "program_id"
) + ("program_ids", "programs")

# Group document links before joining chunks: a shared chunk is scored once,
# while all of its in-scope program links survive the final result limit.
_SCOPE_SQL = """
    WITH links AS (
        SELECT t.document_id, t.revision_id,
               array_agg(DISTINCT t.target_id ORDER BY t.target_id) AS program_ids
        FROM public.knowledge_document_targets AS t
        WHERE t.target_type = %s AND t.target_id = ANY(%s)
        GROUP BY t.document_id, t.revision_id
    ), candidates AS MATERIALIZED (
        SELECT d.document_id, d.revision_id, c.chunk_id, c.ordinal,
               d.title, c.body, d.knowledge_kind, links.program_ids,
               d.metadata -> 'source_references' AS source_references,
               d.active AS document_active, c.active AS chunk_active,
               d.metadata -> 'embedding_approved' AS document_embedding_approved,
               c.embedding_approved AS chunk_embedding_approved,
               d.metadata -> 'answer_approved' AS answer_approved,
               d.metadata -> 'content_review_status' AS content_review_status,
               d.release_id AS document_release_id,
               c.release_id AS chunk_release_id
        FROM links
        JOIN public.knowledge_documents AS d
          ON d.document_id = links.document_id
         AND d.revision_id = links.revision_id
        JOIN public.knowledge_chunks AS c
          ON c.document_id = d.document_id AND c.revision_id = d.revision_id
        WHERE d.active = TRUE AND c.active = TRUE
    )
"""

_VECTOR_SQL = _SCOPE_SQL + """
    SELECT c.*, 1 - (e.embedding <=> %s::public.vector) AS similarity
    FROM candidates AS c
    JOIN public.knowledge_chunk_embeddings AS e
      ON e.chunk_id = c.chunk_id AND e.document_id = c.document_id
     AND e.revision_id = c.revision_id AND e.embedding_model = %s
    ORDER BY similarity DESC, c.chunk_id ASC
"""

_KEYWORD_SQL = _SCOPE_SQL + """
    , search_query AS (
        SELECT to_tsquery(%s::regconfig, %s) AS query
    ), searchable AS (
        SELECT c.*,
               setweight(to_tsvector(%s::regconfig, c.title), 'A')
                   || setweight(to_tsvector(%s::regconfig, c.body), 'B')
                   AS search_vector
        FROM candidates AS c
    )
    SELECT s.*, ts_rank_cd(s.search_vector, q.query) AS keyword_score
    FROM searchable AS s CROSS JOIN search_query AS q
    WHERE s.search_vector @@ q.query
    ORDER BY keyword_score DESC, s.chunk_id ASC
"""


def _load_programs(connection, country: str | None, category: str | None) -> list[dict]:
    """Use the existing candidate filters, without its default pagination cap."""
    conditions = []
    parameters = []
    if country is not None:
        conditions.append("country = %s")
        parameters.append(country)
    if category is not None:
        conditions.append("category = %s")
        parameters.append(category)
    query = "SELECT program_id, name, country, category FROM public.programs"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY program_id ASC"
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, parameters)
        return cursor.fetchall()


def _evidence(row: dict, programs: dict[str, dict]) -> dict:
    result = {
        field: row[field]
        for field in EVIDENCE_FIELDS
        if field not in ("program_id", "source_urls")
    }
    references = row["source_references"]
    result["source_references"] = references if references is not None else []
    result["source_urls"] = list(dict.fromkeys(
        reference["source_url"]
        for reference in result["source_references"]
        if isinstance(reference.get("source_url"), str)
        and reference["source_url"].strip()
    ))
    result["program_ids"] = sorted(set(row["program_ids"]))
    result["programs"] = [dict(programs[key]) for key in result["program_ids"]]
    return result


def _fuse_global_rankings(
    vector_rows: list[dict],
    keyword_rows: list[dict],
    programs: list[dict],
    limit: int,
) -> list[dict]:
    """Rank unique chunks across the entire scope, then apply the only limit."""
    programs_by_id = {row["program_id"]: row for row in programs}
    merged = {}
    for source, rows, score_field in (
        ("vector", vector_rows, "similarity"),
        ("keyword", keyword_rows, "keyword_score"),
    ):
        seen = set()
        rank = 0
        for row in sorted(rows, key=lambda item: (-item[score_field], item["chunk_id"])):
            chunk_id = row["chunk_id"]
            base = _evidence(row, programs_by_id)
            if chunk_id in merged and any(
                merged[chunk_id][field] != base[field]
                for field in MULTI_EVIDENCE_FIELDS
            ):
                raise RuntimeError("같은 청크의 근거 또는 프로그램 연결 정보가 다릅니다.")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            rank += 1
            if chunk_id not in merged:
                merged[chunk_id] = {
                    **base, "vector_rank": None, "vector_similarity": None,
                    "keyword_rank": None, "keyword_score": None, "rrf_score": 0.0,
                }
            result = merged[chunk_id]
            result[source + "_rank"] = rank
            result["vector_similarity" if source == "vector" else "keyword_score"] = row[score_field]
            result["rrf_score"] += 1.0 / (RRF_K + rank)
    return sorted(
        merged.values(), key=lambda row: (-row["rrf_score"], row["chunk_id"]),
    )[:limit]


def search_programs_evidence_hybrid(
    text: str,
    country: str | None = None,
    category: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Return globally ranked evidence from every matching program.

    None omits its filter. Inputs are checked before DB/model access. The
    question is embedded once when candidates exist; the original text is used.
    Candidate programs and source rankings have no intermediate result cap.
    A nonmatching keyword has no rank; a missing model embedding has no vector
    rank but does not prevent keyword retrieval. Errors propagate unchanged.

    The 17 chunk/document fields from single-program retrieval are preserved;
    program_ids and programs replace its singular program_id. Links refer only
    to the requested scope. limit (1..100, excluding bool) counts unique chunks,
    not programs. No per-program quota, recommendation or approval is implied.

    All three SELECTs share a read-only, repeatable-read snapshot. Ranking all
    eligible chunks uses memory proportional to the scope; no silent truncation
    or ANN candidate cutoff is used. Existing single-program callers are intact.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text는 공백이 아닌 문자를 포함한 문자열이어야 합니다.")
    _validate_filter("country", country, SUPPORTED_COUNTRIES)
    _validate_filter("category", category, SUPPORTED_CATEGORIES)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit은 1 이상 100 이하의 정수여야 합니다.")
    text_query = _build_tsquery(expand_search_terms(text))

    with get_connection() as connection:
        connection.read_only = True
        connection.isolation_level = IsolationLevel.REPEATABLE_READ
        programs = _load_programs(connection, country, category)
        if not programs:
            return []
        program_ids = [row["program_id"] for row in programs]
        keyword_rows = []
        if text_query:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    _KEYWORD_SQL,
                    ("PROGRAM", program_ids, TEXT_SEARCH_CONFIG, text_query,
                     TEXT_SEARCH_CONFIG, TEXT_SEARCH_CONFIG),
                )
                keyword_rows = cursor.fetchall()
        query_vector = embed_query_local(text)
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                _VECTOR_SQL,
                ("PROGRAM", program_ids, Vector(query_vector).to_text(), MODEL_NAME),
            )
            vector_rows = cursor.fetchall()
    return _fuse_global_rankings(vector_rows, keyword_rows, programs, limit)

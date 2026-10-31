"""Fuse independent keyword and vector rankings without changing either."""

import logging

from app.retrieval.keyword_search import search_program_evidence_by_keyword
from app.retrieval.query_embedding import LocalEmbeddingUnavailable, embed_query_local
from app.retrieval.vector_search import search_program_evidence_by_vector

CANDIDATE_LIMIT = 100
RRF_K = 60
EVIDENCE_FIELDS = (
    "program_id", "document_id", "revision_id", "chunk_id", "ordinal",
    "title", "body", "knowledge_kind", "source_urls", "source_references",
    "document_active", "chunk_active", "document_embedding_approved",
    "chunk_embedding_approved", "answer_approved", "content_review_status",
    "document_release_id", "chunk_release_id",
)


def _fuse_rankings(
    vector_rows: list[dict],
    keyword_rows: list[dict],
    limit: int,
) -> list[dict]:
    """RRF over deduplicated lists; a missing rank contributes zero."""
    merged = {}
    for source, rows in (("vector", vector_rows), ("keyword", keyword_rows)):
        seen = set()
        rank = 0
        for row in rows:
            chunk_id = row["chunk_id"]
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            rank += 1
            if chunk_id not in merged:
                merged[chunk_id] = {
                    **{field: row[field] for field in EVIDENCE_FIELDS},
                    "vector_rank": None,
                    "vector_similarity": None,
                    "keyword_rank": None,
                    "keyword_score": None,
                    "rrf_score": 0.0,
                }
            result = merged[chunk_id]
            if any(result[field] != row[field] for field in EVIDENCE_FIELDS):
                raise RuntimeError("두 검색에서 같은 청크의 근거 필드가 다릅니다.")
            result[source + "_rank"] = rank
            if source == "vector":
                result["vector_similarity"] = row["similarity"]
            else:
                result["keyword_score"] = row["keyword_score"]
            result["rrf_score"] += 1.0 / (RRF_K + rank)
    return sorted(
        merged.values(),
        key=lambda row: (-row["rrf_score"], row["chunk_id"]),
    )[:limit]


def has_source_url(urls) -> bool:
    """사용자에게 보여줄 수 있는 출처 URL이 하나라도 있는지 확인한다."""
    return isinstance(urls, list) and any(isinstance(u, str) and u.strip() for u in urls)


def search_program_evidence_hybrid(
    program_id: str,
    text: str,
    limit: int = 5,
    require_source_url: bool = False,
) -> list[dict]:
    """Fuse up to 100 candidates per search, using raw query embeddings.

    The 18 evidence fields are preserved. Vector cosine similarity, keyword
    score, each source's rank, and RRF score are separate fields. A keyword
    nonmatch has keyword_rank=None and keyword_score=None. Results do not
    imply answerability or answer-use approval. If the optional local model is
    unavailable, keyword retrieval continues. DB and inference errors propagate.

    require_source_url=True(실사용 모드)는 출처 URL이 없는 청크를 RRF 순위 계산
    전에 제외한다. 남은 청크끼리 순위를 매긴다. 각 검색의 후보 100개 안에서
    제외하므로, 후보 대부분이 출처 없는 청크면 반환 개수가 limit보다 적을 수 있다.
    """
    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id는 비어 있지 않은 문자열이어야 합니다.")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text는 공백이 아닌 문자를 포함한 문자열이어야 합니다.")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit은 1 이상 100 이하의 정수여야 합니다.")
    if type(require_source_url) is not bool:
        raise ValueError("require_source_url은 bool이어야 합니다.")
    program_id = program_id.strip()

    keyword_rows = search_program_evidence_by_keyword(
        program_id, text, limit=CANDIDATE_LIMIT
    )
    try:
        vector = embed_query_local(text)
    except LocalEmbeddingUnavailable:
        logging.getLogger(__name__).warning('Local embedding unavailable; using keyword evidence search')
        vector_rows = []
    else:
        vector_rows = search_program_evidence_by_vector(
            program_id, vector, limit=CANDIDATE_LIMIT
        )
    if require_source_url:
        keyword_rows = [row for row in keyword_rows if has_source_url(row["source_urls"])]
        vector_rows = [row for row in vector_rows if has_source_url(row["source_urls"])]
    return _fuse_rankings(vector_rows, keyword_rows, limit)

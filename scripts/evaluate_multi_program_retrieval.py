"""Read-only evaluation of multi-program retrieval, without LLM calls.

Run from the project root with the existing global-in Python:
    python -B -m scripts.evaluate_multi_program_retrieval

Loads only the cached embedding model. Prints short examples and checks, never
connection settings, full vectors or complete documents. Writes no report file.
Empty/shared-link fixtures are covered by the offline unit tests; no DB fixtures
are inserted. This is a retrieval/scope check, not a recommendation evaluation.
"""

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from pgvector import Vector
from psycopg import IsolationLevel
from psycopg.rows import dict_row

from app.retrieval import multi_program_search as search
from app.retrieval.hybrid_search import EVIDENCE_FIELDS, RRF_K
from app.retrieval.keyword_search import TEXT_SEARCH_CONFIG, _build_tsquery, expand_search_terms
from app.retrieval.query_embedding import MODEL_NAME, MODEL_REVISION
from app.services.database import get_connection


CASES = (
    ("au_working_holiday", "초기 체류 자금과 출국 항공료는 얼마나 준비해야 하나요?", "australia", "working_holiday", 10),
    ("all_working_holiday", "워킹홀리데이 신청 연령과 나이 제한에 대한 근거를 찾고 싶어요.", None, "working_holiday", 10),
    ("all_australia", "What funds are required for the initial stay and onward travel?", "australia", None, 5),
    ("all_programs", "What passport requirements apply to applicants?", None, None, 5),
)


def emit(event, **values):
    print(json.dumps({"event": event, **values}, ensure_ascii=False), flush=True)


def protected_hashes():
    paths = list(Path("app/retrieval").glob("*.py"))
    paths += [Path(name) for name in (
        "app/services/database.py", "app/services/program_rag.py",
        "app/services/rag_llm.py", "app/models/rag.py", "requirements.txt",
    )]
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def reference(text, vector, country, category):
    """Independent unbounded row/link query and ranking oracle."""
    conditions = []
    filter_values = []
    if country is not None:
        conditions.append("p.country = %s")
        filter_values.append(country)
    if category is not None:
        conditions.append("p.category = %s")
        filter_values.append(category)
    where = " AND ".join(conditions) or "TRUE"
    query = """
        WITH q AS (SELECT to_tsquery(%s::regconfig, %s) AS query),
        linked AS (
            SELECT p.program_id, p.name, p.country, p.category,
                   d.document_id, d.revision_id, c.chunk_id, c.ordinal,
                   d.title, c.body, d.knowledge_kind,
                   d.metadata -> 'source_references' AS source_references,
                   d.active AS document_active, c.active AS chunk_active,
                   d.metadata -> 'embedding_approved' AS document_embedding_approved,
                   c.embedding_approved AS chunk_embedding_approved,
                   d.metadata -> 'answer_approved' AS answer_approved,
                   d.metadata -> 'content_review_status' AS content_review_status,
                   d.release_id AS document_release_id, c.release_id AS chunk_release_id,
                   1 - (e.embedding <=> %s::public.vector) AS similarity,
                   setweight(to_tsvector(%s::regconfig, d.title), 'A')
                       || setweight(to_tsvector(%s::regconfig, c.body), 'B') AS search_vector
            FROM public.programs AS p
            JOIN public.knowledge_document_targets AS t
              ON t.target_id = p.program_id AND t.target_type = %s
            JOIN public.knowledge_documents AS d
              ON d.document_id = t.document_id AND d.revision_id = t.revision_id
            JOIN public.knowledge_chunks AS c
              ON c.document_id = d.document_id AND c.revision_id = d.revision_id
            LEFT JOIN public.knowledge_chunk_embeddings AS e
              ON e.chunk_id = c.chunk_id AND e.document_id = c.document_id
             AND e.revision_id = c.revision_id AND e.embedding_model = %s
            WHERE d.active = TRUE AND c.active = TRUE AND
    """ + where + """
        )
        SELECT linked.*,
               CASE WHEN search_vector @@ q.query
                    THEN ts_rank_cd(search_vector, q.query) END AS keyword_score
        FROM linked CROSS JOIN q
    """
    with get_connection() as connection:
        connection.read_only = True
        connection.isolation_level = IsolationLevel.REPEATABLE_READ
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT p.program_id FROM public.programs p WHERE " + where,
                filter_values,
            )
            candidate_ids = {row["program_id"] for row in cursor.fetchall()}
            cursor.execute(query, (
                TEXT_SEARCH_CONFIG, _build_tsquery(expand_search_terms(text)),
                Vector(vector).to_text(), TEXT_SEARCH_CONFIG, TEXT_SEARCH_CONFIG,
                "PROGRAM", MODEL_NAME, *filter_values,
            ))
            links = cursor.fetchall()

    rows = {}
    for link in links:
        key = link["chunk_id"]
        if key not in rows:
            base = {field: link[field] for field in EVIDENCE_FIELDS if field not in ("program_id", "source_urls")}
            base["source_references"] = base["source_references"] if base["source_references"] is not None else []
            base["source_urls"] = []
            for ref in base["source_references"]:
                url = ref.get("source_url")
                if isinstance(url, str) and url.strip() and url not in base["source_urls"]:
                    base["source_urls"].append(url)
            rows[key] = {
                **base, "program_ids": [], "programs": [], "rrf_score": 0.0,
                "vector_rank": None, "vector_similarity": link["similarity"],
                "keyword_rank": None, "keyword_score": link["keyword_score"],
            }
        row = rows[key]
        if link["program_id"] not in row["program_ids"]:
            row["program_ids"].append(link["program_id"])
            row["programs"].append({field: link[field] for field in ("program_id", "name", "country", "category")})
    for row in rows.values():
        row["program_ids"].sort()
        row["programs"].sort(key=lambda item: item["program_id"])
    for rank_key, score_key in (("vector_rank", "vector_similarity"), ("keyword_rank", "keyword_score")):
        ranked = sorted(
            (row for row in rows.values() if row[score_key] is not None),
            key=lambda row: (-row[score_key], row["chunk_id"]),
        )
        for rank, row in enumerate(ranked, 1):
            row[rank_key] = rank
            row["rrf_score"] += 1 / (RRF_K + rank)
    result = sorted(
        (row for row in rows.values() if row["vector_rank"] is not None or row["keyword_rank"] is not None),
        key=lambda row: (-row["rrf_score"], row["chunk_id"]),
    )
    return candidate_ids, rows, result


class CheckedCursor:
    def __init__(self, cursor, connection, audit):
        self.cursor, self.connection, self.audit = cursor, connection, audit

    def __enter__(self):
        self.cursor.__enter__()
        self.audit["opened_cursors"] += 1
        return self

    def __exit__(self, *args):
        try:
            return self.cursor.__exit__(*args)
        finally:
            self.audit["closed_cursors"] += 1

    def execute(self, query, parameters):
        assert self.connection.read_only is True
        assert self.connection.isolation_level == IsolationLevel.REPEATABLE_READ
        assert query.lstrip().upper().startswith(("SELECT", "WITH"))
        self.cursor.execute("SHOW transaction_read_only")
        assert self.cursor.fetchone()["transaction_read_only"] == "on"
        self.audit["readonly_checks"] += 1
        return self.cursor.execute(query, parameters)

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class CheckedConnection:
    def __init__(self, connection, audit):
        object.__setattr__(self, "connection", connection)
        object.__setattr__(self, "audit", audit)

    def cursor(self, **kwargs):
        return CheckedCursor(self.connection.cursor(**kwargs), self.connection, self.audit)

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __setattr__(self, name, value):
        setattr(self.connection, name, value)


def main():
    os.environ.update({
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1", "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
        "HF_HUB_DISABLE_PROGRESS_BARS": "1", "TOKENIZERS_PARALLELISM": "false",
    })
    before = protected_hashes()
    embed = search.embed_query_local
    reports = []
    emit("settings", model=MODEL_NAME, revision=MODEL_REVISION,
         device="cpu", dtype="float32", rrf_k=RRF_K,
         intermediate_cap=None, live_llm_calls=0)
    for case_id, text, country, category, limit in CASES:
        vectors = []
        audit = {"readonly_checks": 0, "opened_cursors": 0, "closed_cursors": 0, "closed_connections": 0}

        def capture(question):
            vectors.append(embed(question))
            return vectors[-1]

        @contextmanager
        def checked_connection():
            connection = None
            try:
                with get_connection() as connection:
                    yield CheckedConnection(connection, audit)
            finally:
                if connection is not None and connection.closed:
                    audit["closed_connections"] += 1

        started = perf_counter()
        with patch.object(search, "get_connection", side_effect=checked_connection), patch.object(search, "embed_query_local", side_effect=capture):
            actual = search.search_programs_evidence_hybrid(text, country, category, limit)
        elapsed = perf_counter() - started
        assert len(vectors) == 1, "Embedding must run exactly once per nonempty request"
        candidate_ids, all_rows, expected = reference(text, vectors[0], country, category)
        assert actual == expected[:limit], "Evidence, links, global ranks or scores differ from the unbounded oracle"
        assert len(actual) == len({row["chunk_id"] for row in actual})
        for row in actual:
            assert row["document_active"] is True and row["chunk_active"] is True
            assert set(row["program_ids"]) <= candidate_ids
            assert row["program_ids"] == [item["program_id"] for item in row["programs"]]
            assert math.isfinite(row["rrf_score"])
        # Reuse the captured vector to check final limits without more inference.
        for check_limit in (1, 100):
            with patch.object(search, "get_connection", side_effect=checked_connection), patch.object(search, "embed_query_local", return_value=vectors[0]) as cached:
                limited = search.search_programs_evidence_hybrid(text, country, category, check_limit)
            cached.assert_called_once_with(text)
            assert limited == expected[:check_limit]
        assert audit["closed_connections"] == 3
        assert audit["opened_cursors"] == audit["closed_cursors"]
        report = {
            "case_id": case_id, "question": text, "country": country, "category": category,
            "candidate_programs": len(candidate_ids), "eligible_unique_chunks": len(all_rows),
            "vector_candidates": sum(row["vector_rank"] is not None for row in all_rows.values()),
            "keyword_candidates": sum(row["keyword_rank"] is not None for row in all_rows.values()),
            "returned_chunks": len(actual), "limit": limit,
            "embedding_calls": len(vectors), "request_seconds": round(elapsed, 3),
            "oracle_and_limits_passed": True, "connection_audit": audit,
            "shared_chunks_in_scope": sum(len(row["program_ids"]) > 1 for row in all_rows.values()),
            "unapproved_results": sum(row["answer_approved"] is False for row in actual),
            "top3": [{
                "chunk_id": row["chunk_id"], "program_ids": row["program_ids"],
                "title": row["title"], "excerpt": row["body"][:240],
                "source_urls": row["source_urls"], "answer_approved": row["answer_approved"],
                **{key: row[key] for key in ("vector_rank", "vector_similarity", "keyword_rank", "keyword_score", "rrf_score")},
            } for row in actual[:3]],
        }
        reports.append(report)
        emit("case", **report)
    assert protected_hashes() == before, "Protected files changed during evaluation"
    emit("summary", cases=len(reports), passed=len(reports),
         embedding_calculations=sum(row["embedding_calls"] for row in reports),
         protected_files_unchanged=True,
         empty_and_shared_link_validation="offline fixtures; no real shared chunks observed",
         limitation="Small qualitative sample. Retrieval scores do not establish answerability, eligibility or recommendation quality.")


if __name__ == "__main__":
    main()

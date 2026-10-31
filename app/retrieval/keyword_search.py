"""Read-only PostgreSQL title/body search with small bilingual topic rules."""

import re

from psycopg.rows import dict_row

from app.services.database import get_connection

TEXT_SEARCH_CONFIG = "pg_catalog.simple"
TOPIC_LEXICON = {
    "age": {
        "pattern": r"나이|연령|몇\s*(?:살|세)|\b(?:age|ages|aged)\b",
        "terms": ("age", "ages", "aged", "나이", "연령", "상한"),
    },
    "funds": {
        "pattern": r"자금|금액|체류비|생활비|잔고|재정|예산|\b(?:money|funds?|savings?|budget|financial)\b",
        "terms": ("money", "fund", "funds", "savings", "budget", "자금", "금액", "체류비", "생활비", "잔고"),
    },
    "passport": {
        "pattern": r"여권|\bpassports?\b",
        "terms": ("passport", "passports", "여권"),
    },
    "character": {
        "pattern": r"인성|범죄|경찰|\b(?:character|police|criminal)\b",
        "terms": ("character", "police", "criminal", "인성", "범죄", "경찰"),
    },
    "insurance": {
        "pattern": r"보험|\binsurance\b|\bhealth\s+cover(?:age)?\b",
        "terms": ("insurance", "보험", "건강보험", "의료보험", "health insurance"),
    },
    "employer": {
        "pattern": r"고용주|\bemployers?\b",
        "terms": ("employer", "employers", "고용주"),
    },
}
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_HANGUL = re.compile(r"[\uac00-\ud7a3]")
_STOP_WORDS = set(
    "a an the is are am be have has had do does did can could should would may "
    "might must for to of in on at by as with and or from this that these those "
    "it its i me my we our you your what which how when where who why please need "
    "required requirements requirement apply applying application applications "
    "applicant applicants program visa working holiday subclass first second third "
    "비자 호주 워킹홀리데이 신청 질문 알려주세요".split()
)


def expand_search_terms(text: str) -> list[str]:
    """Expand recognized topics; otherwise keep non-filler query tokens.

    This is a small dictionary, not a translation or Korean morphology model.
    Program context is enforced by SQL, so recognized topics use their terms
    instead of allowing generic visa words to match every document.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text는 공백이 아닌 문자를 포함한 문자열이어야 합니다.")
    normalized = text.casefold()
    terms = []
    for rule in TOPIC_LEXICON.values():
        if re.search(rule["pattern"], normalized):
            terms.extend(rule["terms"])
    if not terms:
        terms = [
            token for token in _TOKEN.findall(normalized)
            if token not in _STOP_WORDS
        ]
    return list(dict.fromkeys(terms))


def _build_tsquery(terms: list[str]) -> str:
    expressions = []
    for term in terms:
        tokens = _TOKEN.findall(term.casefold())
        # Quotes/operators cannot enter via a token. The complete tsquery is
        # still bound as an SQL parameter. Prefixes handle Korean particles.
        parts = [
            "'" + token + "'" + (":*" if _HANGUL.search(token) else "")
            for token in tokens
        ]
        if parts:
            expressions.append("(" + " <-> ".join(parts) + ")")
    return " | ".join(expressions)


def search_program_evidence_by_keyword(
    program_id: str,
    text: str,
    limit: int = 5,
) -> list[dict]:
    """Return matching active chunks with keyword_rank and keyword_score.

    Nonmatches are absent. Scores and ranks do not establish answerability
    or approval to use evidence in an answer. Database errors propagate.
    """
    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id는 비어 있지 않은 문자열이어야 합니다.")
    program_id = program_id.strip()
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit은 1 이상 100 이하의 정수여야 합니다.")
    terms = expand_search_terms(text)
    text_query = _build_tsquery(terms)
    if not text_query:
        return []

    query = """
        WITH search_query AS (
            SELECT to_tsquery(%s::regconfig, %s) AS query
        ), candidates AS (
            SELECT
                p.program_id, d.document_id, d.revision_id,
                c.chunk_id, c.ordinal, d.title, c.body, d.knowledge_kind,
                d.metadata AS document_metadata,
                d.active AS document_active, c.active AS chunk_active,
                c.embedding_approved AS chunk_embedding_approved,
                d.release_id AS document_release_id,
                c.release_id AS chunk_release_id,
                setweight(to_tsvector(%s::regconfig, d.title), 'A')
                    || setweight(to_tsvector(%s::regconfig, c.body), 'B')
                    AS search_vector
            FROM public.programs AS p
            JOIN public.knowledge_document_targets AS t
              ON t.target_id = p.program_id AND t.target_type = %s
            JOIN public.knowledge_documents AS d
              ON d.document_id = t.document_id AND d.revision_id = t.revision_id
            JOIN public.knowledge_chunks AS c
              ON c.document_id = d.document_id AND c.revision_id = d.revision_id
            WHERE p.program_id = %s
              AND d.active = TRUE AND c.active = TRUE
        )
        SELECT
            program_id, document_id, revision_id, chunk_id, ordinal,
            title, body, knowledge_kind,
            document_metadata -> 'source_references' AS source_references,
            document_active, chunk_active,
            document_metadata -> 'embedding_approved'
                AS document_embedding_approved,
            chunk_embedding_approved,
            document_metadata -> 'answer_approved' AS answer_approved,
            document_metadata -> 'content_review_status' AS content_review_status,
            document_release_id, chunk_release_id,
            ts_rank_cd(search_vector, search_query.query) AS keyword_score
        FROM candidates CROSS JOIN search_query
        WHERE search_vector @@ search_query.query
        ORDER BY keyword_score DESC, chunk_id ASC
        LIMIT %s
    """
    with get_connection() as connection:
        connection.read_only = True
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                query,
                (
                    TEXT_SEARCH_CONFIG, text_query,
                    TEXT_SEARCH_CONFIG, TEXT_SEARCH_CONFIG,
                    "PROGRAM", program_id, limit,
                ),
            )
            rows = cursor.fetchall()

    for rank, row in enumerate(rows, 1):
        references = row["source_references"]
        if references is None:
            references = []
        row["source_references"] = references
        urls = []
        seen = set()
        for reference in references:
            source_url = reference.get("source_url")
            if (
                isinstance(source_url, str)
                and source_url.strip()
                and source_url not in seen
            ):
                seen.add(source_url)
                urls.append(source_url)
        row["source_urls"] = urls
        row["keyword_rank"] = rank
    return rows

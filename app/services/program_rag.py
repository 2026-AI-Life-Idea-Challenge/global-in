"""Single-program retrieval -> draft -> citation checks -> source binding."""

from copy import deepcopy
import re

from pydantic import ValidationError

from app.models.rag import (
    SOURCE_POLICIES, OverviewDraft, RagCitation, RagClaim, RagDraft, RagGeneration,
    RagResponseValidationError, RagResult, RagSearchError, UnansweredPart,
    answer_status, schema_validation_issues,
)
from app.retrieval.hybrid_search import (
    EVIDENCE_FIELDS, has_source_url, search_program_evidence_hybrid,
)
from app.services.rag_llm import build_citation_spans, generate_rag_draft, validate_mode
from app.services.answer_quality import guard_unsupported_absolutes

RETRIEVAL_LIMIT = 5
# overview(막연한 준비 질문)는 같은 검색을 주제별로 나눠 실행한다. 생성은 한 번이다.
OVERVIEW_QUERY_TOPICS = ("모집 일정 신청 기간", "신청 자격 기본 조건", "신청 절차 준비 순서")
ANSWER_HEADERS = {
    "development": "개발 검증용 답변 · 현재 검색된 자료 기준",
    "production": "현재 검색된 자료 기준 답변",
}


def search_queries(question: str, layout: str) -> list[str]:
    if layout == "overview":
        return [f"{question} {topic}" for topic in OVERVIEW_QUERY_TOPICS]
    return [question]


def merge_unique_chunks(batches: list[list[dict]]) -> list[dict]:
    """주제별 검색 결과를 순서대로 합치고 같은 청크는 한 번만 둔다."""
    rows, seen = [], set()
    for batch in batches:
        for row in batch:
            if row["chunk_id"] not in seen:
                seen.add(row["chunk_id"])
                rows.append(row)
    return rows


def ensure_source_policy(rows: list[dict], mode: str) -> None:
    """실사용 모드에서 출처 없는 근거가 생성 단계로 넘어가지 않도록 막는다."""
    if mode == "production" and any(not has_source_url(row["source_urls"]) for row in rows):
        raise RagSearchError("실사용 모드 검색 결과에 출처 URL이 없는 근거가 있습니다.")


def generation_kwargs(profile, mode, layout, today) -> dict:
    """기본값은 넘기지 않아 개발 모드 호출이 기존과 같게 유지된다."""
    kwargs = {"profile": deepcopy(profile)} if profile else {}
    if mode != "development":
        kwargs["mode"] = mode
    if layout != "default":
        kwargs["layout"] = layout
    if today is not None:
        kwargs["today"] = today
    return kwargs


def release_fields(mode: str, layout: str, draft) -> dict:
    return {
        "development_only": mode == "development", "release_mode": mode,
        "source_policy": SOURCE_POLICIES[mode], "layout": layout,
        "part_sections": [item.section for item in draft.items] if layout == "overview" else None,
    }
SHORTAGE_REASON = "현재 검색된 자료 기준으로 이 부분에 직접 답할 근거가 부족합니다."
GENERATED_URL = re.compile(r"(?:[a-z][a-z0-9+.-]*://|www\.)", re.IGNORECASE)


def _validate_evidence(program_id: str, rows: list[dict]) -> None:
    seen = set()
    if not isinstance(rows, list):
        raise RagSearchError("검색 결과가 목록 형식이 아닙니다.")
    for row in rows:
        if not isinstance(row, dict) or not set(EVIDENCE_FIELDS).issubset(row):
            raise RagSearchError("검색 결과의 근거 필드가 누락되었습니다.")
        if row["program_id"] != program_id or (
            row["document_active"] is not True or row["chunk_active"] is not True
        ):
            raise RagSearchError("프로그램 또는 활성 상태가 검색 범위를 벗어났습니다.")
        for key in ("chunk_id", "document_id", "revision_id", "title", "body"):
            if not isinstance(row[key], str):
                raise RagSearchError("검색 결과의 식별자 또는 본문 형식이 잘못되었습니다.")
        if not row["chunk_id"].strip() or row["chunk_id"] in seen:
            raise RagSearchError("청크 식별자가 비어 있거나 중복되었습니다.")
        seen.add(row["chunk_id"])
        if not isinstance(row["source_references"], list) or not isinstance(row["source_urls"], list):
            raise RagSearchError("검색 결과의 출처 배열 형식이 잘못되었습니다.")
        if any(not isinstance(url, str) or not url.strip() for url in row["source_urls"]):
            raise RagSearchError("검색 결과에 잘못된 출처 URL이 있습니다.")


def _bind_citations(draft: RagDraft, evidence: list[dict]) -> list[RagClaim]:
    by_id = {row["chunk_id"]: row for row in evidence}
    spans = build_citation_spans(evidence)
    claims = []
    for i, item in enumerate(draft.items):
        if item.answer is None:
            continue
        if GENERATED_URL.search(item.answer):
            raise RagResponseValidationError(
                "주장 본문에 생성한 URL을 넣을 수 없습니다.",
                code="generated_url", field=("items", i, "answer"),
            )
        citations = []
        seen = set()
        for j, citation_id in enumerate(item.citation_ids):
            if citation_id in seen:
                continue
            seen.add(citation_id)
            span = spans.get(citation_id)
            if span is None:
                raise RagResponseValidationError(
                    "제공하지 않은 근거 구절 ID입니다.", code="unknown_citation_id",
                    field=("items", i, "citation_ids", j),
                )
            row = by_id.get(span.chunk_id)
            if row is None or span.quote not in row["body"]:
                raise RagResponseValidationError(
                    "인용문이 청크 원문과 일치하지 않습니다.", code="quote_not_exact",
                    field=("items", i, "citation_ids", j),
                )
            citations.append(RagCitation(
                chunk_id=span.chunk_id, quote=span.quote,
                **{key: deepcopy(row[key]) for key in (
                    "document_id", "revision_id", "title", "source_urls",
                    "source_references", "answer_approved", "content_review_status",
                )},
                source_missing=not row["source_urls"],
            ))
        claims.append(RagClaim(
            text=item.answer, part_indexes=[i], citations=citations
        ))
    return claims


def answer_program_question(
    program_id: str, question: str, profile: dict | None = None,
    *, mode: str = "development", layout: str = "default", today=None,
) -> dict:
    """Development only. Citation checks do not prove semantic entailment.

    Errors are raised by stage. ``insufficient_evidence`` describes only the
    retrieved passages, not the entire database or the actual visa rules.
    ``profile`` is only what the user stated; it never changes retrieval.
    mode="production"은 출처 URL 있는 근거만 쓰고 대한민국 국적 기준으로 생성한다.
    layout="overview"는 주제별 검색 결과를 합쳐 한 번 생성한다.
    """
    validate_mode(mode, layout)
    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id는 비어 있지 않은 문자열이어야 합니다.")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question은 공백이 아닌 문자를 포함한 문자열이어야 합니다.")
    program_id = program_id.strip()
    search_kwargs = {"require_source_url": True} if mode == "production" else {}
    try:
        batches = [search_program_evidence_hybrid(program_id, query, limit=RETRIEVAL_LIMIT, **search_kwargs)
                   for query in search_queries(question, layout)]
    except Exception as exc:
        raise RagSearchError("프로그램 근거 검색에 실패했습니다.") from exc
    for batch in batches:
        _validate_evidence(program_id, batch)
    rows = merge_unique_chunks(batches)
    ensure_source_policy(rows, mode)
    draft_type = OverviewDraft if layout == "overview" else RagDraft
    evidence = deepcopy(rows)
    requested_model = model = None
    if not evidence:
        empty = {"question_part": question, "answer": None, "citation_ids": []}
        draft = draft_type.model_validate(
            {"items": [{**empty, "section": "conditions"} if layout == "overview" else empty]})
    else:
        # Pass a separate copy so generation cannot alter source/status provenance.
        generation = generate_rag_draft(
            program_id, question, deepcopy(evidence), **generation_kwargs(profile, mode, layout, today),
        )
        if not isinstance(generation, RagGeneration):
            raise RagResponseValidationError(
                "LLM 생성 결과 형식이 잘못되었습니다.", code="invalid_generation_type"
            )
        try:
            draft = draft_type.model_validate(generation.draft.model_dump())
        except ValidationError as exc:
            raise RagResponseValidationError(
                "답변 항목 구조가 올바르지 않습니다.", issues=schema_validation_issues(exc)
            ) from exc
        except AttributeError as exc:
            raise RagResponseValidationError(
                "LLM 답변 항목 형식이 잘못되었습니다.", code="invalid_draft_type"
            ) from exc
        requested_model, model = generation.requested_model, generation.model
    try:
        draft = guard_unsupported_absolutes(draft, evidence, program_id=program_id)
        claims = _bind_citations(draft, evidence)
        unanswered = [
            UnansweredPart(
                part_index=i, question_part=item.question_part, reason=SHORTAGE_REASON
            ) for i, item in enumerate(draft.items) if item.answer is None
        ]
        lines = [ANSWER_HEADERS[mode]]
        lines.extend(f"{claim.text} [{i}]" for i, claim in enumerate(claims, 1))
        if unanswered:
            lines.append(SHORTAGE_REASON)
            lines.extend(f"- {part.question_part}" for part in unanswered)
        result = RagResult(
            program_id=program_id, question=question, status=answer_status(len(claims), len(unanswered)),
            answer="\n".join(lines), question_parts=[item.question_part for item in draft.items],
            claims=claims, unanswered_parts=unanswered, evidence=evidence,
            requested_model=requested_model, model=model, **release_fields(mode, layout, draft),
        )
    except ValidationError as exc:
        raise RagResponseValidationError(
            "최종 답변 구조 검증에 실패했습니다.", issues=schema_validation_issues(exc)
        ) from exc
    return result.model_dump()

"""Single-program retrieval -> draft -> citation checks -> source binding."""

from copy import deepcopy
import re

from pydantic import ValidationError

from app.models.rag import (
    DraftItem, RagCitation, RagClaim, RagDraft, RagGeneration, RagResponseValidationError,
    RagResult, RagSearchError, UnansweredPart,
    answer_status, schema_validation_issues,
)
from app.retrieval.hybrid_search import EVIDENCE_FIELDS, search_program_evidence_hybrid
from app.services.rag_llm import build_citation_spans, generate_rag_draft

RETRIEVAL_LIMIT = 5
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


def answer_program_question(program_id: str, question: str) -> dict:
    """Development only. Citation checks do not prove semantic entailment.

    Errors are raised by stage. ``insufficient_evidence`` describes only the
    retrieved passages, not the entire database or the actual visa rules.
    """
    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id는 비어 있지 않은 문자열이어야 합니다.")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question은 공백이 아닌 문자를 포함한 문자열이어야 합니다.")
    program_id = program_id.strip()
    try:
        rows = search_program_evidence_hybrid(program_id, question, limit=RETRIEVAL_LIMIT)
    except Exception as exc:
        raise RagSearchError("프로그램 근거 검색에 실패했습니다.") from exc
    _validate_evidence(program_id, rows)
    evidence = deepcopy(rows)
    requested_model = model = None
    if not evidence:
        draft = RagDraft(
            items=[DraftItem(question_part=question, answer=None, citation_ids=[])],
        )
    else:
        # Pass a separate copy so generation cannot alter source/status provenance.
        generation = generate_rag_draft(program_id, question, deepcopy(evidence))
        if not isinstance(generation, RagGeneration):
            raise RagResponseValidationError(
                "LLM 생성 결과 형식이 잘못되었습니다.", code="invalid_generation_type"
            )
        try:
            draft = RagDraft.model_validate(generation.draft.model_dump())
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
        claims = _bind_citations(draft, evidence)
        unanswered = [
            UnansweredPart(
                part_index=i, question_part=item.question_part, reason=SHORTAGE_REASON
            ) for i, item in enumerate(draft.items) if item.answer is None
        ]
        lines = ["개발 검증용 답변 · 현재 검색된 자료 기준"]
        lines.extend(f"{claim.text} [{i}]" for i, claim in enumerate(claims, 1))
        if unanswered:
            lines.append(SHORTAGE_REASON)
            lines.extend(f"- {part.question_part}" for part in unanswered)
        result = RagResult(
            program_id=program_id, question=question, status=answer_status(len(claims), len(unanswered)),
            answer="\n".join(lines), question_parts=[item.question_part for item in draft.items],
            claims=claims, unanswered_parts=unanswered, evidence=evidence,
            requested_model=requested_model, model=model,
        )
    except ValidationError as exc:
        raise RagResponseValidationError(
            "최종 답변 구조 검증에 실패했습니다.", issues=schema_validation_issues(exc)
        ) from exc
    return result.model_dump()

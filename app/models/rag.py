"""Contracts for development-only, single-program grounded answers."""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

AnswerStatus = Literal["answered", "partial", "insufficient_evidence"]
ReleaseMode = Literal["development", "production"]
SourcePolicy = Literal["active", "active_with_source_url"]
AnswerLayout = Literal["default", "overview"]
# 막연한 준비 질문(overview)의 표시 구역. 비용은 다루지 않는다.
OverviewSection = Literal["status", "conditions", "condition_notes", "steps"]
OVERVIEW_SECTIONS = ("status", "conditions", "condition_notes", "steps")
SOURCE_POLICIES = {"development": "active", "production": "active_with_source_url"}


class RagSearchError(RuntimeError):
    """Retrieval failed; this is not an evidence-shortage result."""


class RagLLMError(RuntimeError):
    """The LLM could not complete generation."""


class RagConfigurationError(RagLLMError):
    """The LLM environment is not configured."""


class RagResponseValidationError(RuntimeError):
    """Generated structure or citations failed validation."""

    def __init__(self, message, *, code="response_validation", field=(), issues=None):
        super().__init__(message)
        # Codes and schema paths only: never retain response text or SDK messages.
        self.issues = issues if issues is not None else [
            {"code": code, "field": list(field)}
        ]


_SCHEMA_FIELDS = {
    "status", "question_parts", "claims", "unanswered_parts", "text",
    "part_indexes", "citations", "chunk_id", "quote", "part_index",
    "question_part", "reason", "items", "answer", "citation_ids",
}
_RULE_FIELDS = {
    "empty_question_parts": "question_parts",
    "duplicate_question_parts": "question_parts",
    "duplicate_unanswered_parts": "unanswered_parts",
    "coverage_mismatch": "part_indexes",
    "status_mismatch": "status",
    "empty_question_part": "question_part",
    "empty_answer": "answer",
    "answer_without_citations": "citation_ids",
    "citations_without_answer": "citation_ids",
}


def schema_validation_issues(exc):
    """Extract safe types/paths; omit input, context and error messages."""
    issues = []
    for error in exc.errors(include_input=False, include_context=False, include_url=False):
        field = [
            item if type(item) is int or item in _SCHEMA_FIELDS else "<field>"
            for item in error["loc"]
        ]
        code = error["type"]
        if code in _RULE_FIELDS:
            field.append(_RULE_FIELDS[code])
        issues.append({"code": code, "field": field})
    return issues


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DraftCitation(StrictModel):
    chunk_id: str
    quote: str

    @model_validator(mode="after")
    def nonempty(self):
        if not self.chunk_id.strip() or not self.quote.strip():
            raise ValueError("인용 청크와 원문은 비어 있을 수 없습니다.")
        return self


class DraftItem(StrictModel):
    """One requested part and its answer, or an explicit evidence shortage."""

    question_part: str
    answer: str | None
    citation_ids: list[str]

    @model_validator(mode="after")
    def grounded(self):
        if not self.question_part.strip():
            raise PydanticCustomError("empty_question_part", "질문 항목은 비어 있을 수 없습니다.")
        if self.answer is None:
            if self.citation_ids:
                raise PydanticCustomError("citations_without_answer", "근거 부족 항목에는 인용을 달 수 없습니다.")
        elif not self.answer.strip():
            raise PydanticCustomError("empty_answer", "답변은 비어 있을 수 없습니다.")
        elif not self.citation_ids:
            raise PydanticCustomError("answer_without_citations", "답변에는 인용 ID가 필요합니다.")
        return self


def answer_status(answered_count: int, unanswered_count: int) -> AnswerStatus:
    if not answered_count:
        return "insufficient_evidence"
    return "partial" if unanswered_count else "answered"


def _validate_coverage(status, parts, claims, unanswered):
    if not parts or any(not item.strip() for item in parts):
        raise PydanticCustomError("empty_question_parts", "질문의 세부 항목이 필요합니다.")
    if len(parts) != len(set(parts)):
        raise PydanticCustomError("duplicate_question_parts", "질문 항목이 중복되었습니다.")
    if len(unanswered) != len(set(unanswered)):
        raise PydanticCustomError("duplicate_unanswered_parts", "미답변 항목이 중복되었습니다.")
    covered = {i for claim in claims for i in claim.part_indexes}
    missing = set(unanswered)
    valid = set(range(len(parts)))
    if covered & missing or covered | missing != valid:
        raise PydanticCustomError("coverage_mismatch", "각 질문 항목은 답변 또는 미답변 중 하나여야 합니다.")
    expected = answer_status(len(claims), len(missing))
    if status != expected:
        raise PydanticCustomError("status_mismatch", "status와 claims·unanswered_parts가 일치하지 않습니다.")


class RagDraft(StrictModel):
    """LLM wire format: no status, indexes, quotes, URLs or approval fields."""

    items: list[DraftItem] = Field(min_length=1)


class OverviewDraftItem(DraftItem):
    """overview 전용: 같은 항목 계약에 표시 구역만 더한다."""

    section: OverviewSection


class OverviewDraft(RagDraft):
    items: list[OverviewDraftItem] = Field(min_length=1)


def validate_release_fields(result) -> None:
    """실사용/개발 표시와 근거 기준·표시 구역이 서로 맞는지 확인한다.

    실사용 모드도 공개 승인(public_release_status)이나 자격 판정을 뜻하지 않는다.
    """
    if result.development_only != (result.release_mode == "development"):
        raise ValueError("development_only와 release_mode가 일치하지 않습니다.")
    if result.source_policy != SOURCE_POLICIES[result.release_mode]:
        raise ValueError("release_mode에 맞지 않는 근거 기준입니다.")
    if result.source_policy == "active_with_source_url" and any(
            not row.get("source_urls") for row in result.evidence):
        raise ValueError("실사용 모드 근거에 출처 URL이 없습니다.")
    if result.layout == "overview":
        if result.part_sections is None or len(result.part_sections) != len(result.question_parts):
            raise ValueError("overview 표시 구역이 질문 항목과 맞지 않습니다.")
    elif result.part_sections is not None:
        raise ValueError("기본 표시에는 표시 구역을 둘 수 없습니다.")


@dataclass(frozen=True)
class CitationSpan:
    chunk_id: str
    quote: str


@dataclass(frozen=True)
class RagGeneration:
    draft: RagDraft
    requested_model: str
    model: str


class RagCitation(DraftCitation):
    document_id: str
    revision_id: str
    title: str
    source_urls: list[str]
    source_references: list[Any]
    source_missing: bool
    answer_approved: Any
    content_review_status: Any


class RagClaim(StrictModel):
    text: str
    part_indexes: list[int]
    citations: list[RagCitation]


class UnansweredPart(StrictModel):
    part_index: int
    question_part: str
    reason: str


class RagResult(StrictModel):
    program_id: str
    question: str
    status: AnswerStatus
    answer: str
    question_parts: list[str]
    claims: list[RagClaim]
    unanswered_parts: list[UnansweredPart]
    evidence: list[dict[str, Any]]
    requested_model: str | None
    model: str | None
    development_only: bool = True
    release_mode: ReleaseMode = "development"
    source_policy: SourcePolicy = "active"
    layout: AnswerLayout = "default"
    part_sections: list[OverviewSection] | None = None
    public_release_status: Literal["not_assessed"] = "not_assessed"
    eligibility_assessed: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self):
        validate_release_fields(self)
        _validate_coverage(
            self.status, self.question_parts, self.claims,
            [part.part_index for part in self.unanswered_parts],
        )
        for part in self.unanswered_parts:
            if part.question_part != self.question_parts[part.part_index]:
                raise ValueError("미답변 항목 내용이 질문 항목과 다릅니다.")
        if any(not claim.citations for claim in self.claims):
            raise ValueError("출처 없는 주장을 반환할 수 없습니다.")
        return self

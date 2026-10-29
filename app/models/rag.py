"""Contracts for development-only, single-program grounded answers."""

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_core import PydanticCustomError

AnswerStatus = Literal["answered", "partial", "insufficient_evidence"]


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
    "question_part", "reason",
}
_RULE_FIELDS = {
    "empty_question_parts": "question_parts",
    "duplicate_question_parts": "question_parts",
    "duplicate_unanswered_parts": "unanswered_parts",
    "coverage_mismatch": "part_indexes",
    "status_mismatch": "status",
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
        if not field and code in _RULE_FIELDS:
            field = [_RULE_FIELDS[code]]
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


class DraftClaim(StrictModel):
    text: str
    part_indexes: list[int]
    citations: list[DraftCitation]

    @model_validator(mode="after")
    def grounded(self):
        if not self.text.strip() or not self.part_indexes or not self.citations:
            raise ValueError("주장은 내용·질문 항목·인용을 모두 가져야 합니다.")
        if len(set(self.part_indexes)) != len(self.part_indexes):
            raise ValueError("질문 항목 번호가 중복되었습니다.")
        keys = [(item.chunk_id, item.quote) for item in self.citations]
        if len(keys) != len(set(keys)):
            raise ValueError("같은 인용을 중복할 수 없습니다.")
        return self


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
    expected = "partial" if claims and missing else (
        "answered" if claims else "insufficient_evidence"
    )
    if status != expected:
        raise PydanticCustomError("status_mismatch", "status와 claims·unanswered_parts가 일치하지 않습니다.")


class RagDraft(StrictModel):
    """Only this schema is sent to the LLM; no URL or approval fields."""

    status: AnswerStatus
    question_parts: list[str]
    claims: list[DraftClaim]
    unanswered_parts: list[int]

    @model_validator(mode="after")
    def consistent(self):
        _validate_coverage(
            self.status, self.question_parts, self.claims, self.unanswered_parts
        )
        return self


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
    development_only: Literal[True] = True
    public_release_status: Literal["not_assessed"] = "not_assessed"
    eligibility_assessed: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self):
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

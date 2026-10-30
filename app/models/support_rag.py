"""선택한 지원제도의 개발 검증용 RAG 반환 계약."""

from datetime import date
from typing import Any, Literal

from pydantic import model_validator

from app.models.rag import (
    AnswerStatus, ReleaseMode, RagClaim, SourcePolicy, StrictModel, UnansweredPart,
    _validate_coverage, validate_release_fields,
)


class SupportInfo(StrictModel):
    support_program_id: str
    name: str
    availability: Literal["OPEN", "CLOSED", "UPCOMING", "UNKNOWN"] | None
    source_verified_at: date | None
    profile: dict[str, Any] | None
    profile_release_id: str | None


class SupportRagResult(StrictModel):
    support_program_id: str
    question: str
    status: AnswerStatus
    answer: str
    question_parts: list[str]
    claims: list[RagClaim]
    unanswered_parts: list[UnansweredPart]
    evidence: list[dict[str, Any]]
    support_info: SupportInfo | None
    availability_notice: str
    requested_model: str | None
    model: str | None
    development_only: bool = True
    release_mode: ReleaseMode = "development"
    source_policy: SourcePolicy = "active"
    # 지원제도 RAG는 기본 표시만 사용한다.
    layout: Literal["default"] = "default"
    part_sections: None = None
    public_release_status: Literal["not_assessed"] = "not_assessed"
    eligibility_assessed: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self):
        validate_release_fields(self)
        _validate_coverage(
            self.status, self.question_parts, self.claims,
            [part.part_index for part in self.unanswered_parts],
        )
        if self.support_info and self.support_info.support_program_id != self.support_program_id:
            raise ValueError("지원제도 정보의 대상 ID가 다릅니다.")
        for part in self.unanswered_parts:
            if part.question_part != self.question_parts[part.part_index]:
                raise ValueError("미답변 항목과 질문 항목이 다릅니다.")
        if any(not claim.citations for claim in self.claims):
            raise ValueError("출처 없는 주장을 반환할 수 없습니다.")
        if any(row.get("support_program_id") != self.support_program_id for row in self.evidence):
            raise ValueError("근거의 지원제도 ID가 다릅니다.")
        return self

"""Program-scoped items and provenance for development-only multi-program RAG."""

import json
from typing import Any, Literal

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from app.models.rag import (
    AnswerLayout, AnswerStatus, DraftItem, OverviewSection, RagCitation, RagClaim, RagDraft,
    ReleaseMode, SourcePolicy, StrictModel, UnansweredPart, _validate_coverage,
    validate_release_fields,
)

_COVERAGE_BODY = (
    "검색 범위의 전체 후보와 "
    "상위 근거에 연결된 프로그램, 실제 답변에 인용한 프로그램을 구분합니다. "
    "후보 전체의 조건 비교를 완료했다는 의미가 아니며, 검색되지 않은 조건은 "
    "확인 불가입니다. 검색 순위는 추천 적합도나 신청 가능성을 뜻하지 않습니다."
)
COVERAGE_NOTE = "현재 검색된 자료 기준의 개발 검증용 답변입니다. " + _COVERAGE_BODY
PRODUCTION_COVERAGE_NOTE = "현재 검색된 자료 기준의 답변입니다. " + _COVERAGE_BODY
COVERAGE_NOTES = {"development": COVERAGE_NOTE, "production": PRODUCTION_COVERAGE_NOTE}


class ProgramInfo(StrictModel):
    program_id: str
    name: str
    country: str
    category: str | None

    @model_validator(mode="after")
    def nonempty(self):
        if any(not value.strip() for value in (self.program_id, self.name, self.country)):
            raise ValueError("프로그램 식별자·이름·국가는 비어 있을 수 없습니다.")
        return self


class ProgramDraftItem(DraftItem):
    # None is reserved for a scope-level evidence shortage, never an answer.
    program_id: str | None

    @model_validator(mode="after")
    def scoped(self):
        if self.program_id is not None and not self.program_id.strip():
            raise PydanticCustomError("empty_program_id", "프로그램 ID가 비어 있습니다.")
        if self.answer is not None and self.program_id is None:
            raise PydanticCustomError("answer_without_program", "답변에는 프로그램 ID가 필요합니다.")
        return self


class ProgramsDraft(RagDraft):
    items: list[ProgramDraftItem] = Field(min_length=1)


class OverviewProgramDraftItem(ProgramDraftItem):
    section: OverviewSection


class OverviewProgramsDraft(ProgramsDraft):
    items: list[OverviewProgramDraftItem] = Field(min_length=1)


class ProgramCitation(RagCitation):
    program_id: str
    program_name: str


class ProgramClaim(RagClaim):
    program_id: str
    program_name: str
    citations: list[ProgramCitation]


class ProgramUnanswered(UnansweredPart):
    program_id: str | None
    program_name: str | None


class ProgramsRagResult(StrictModel):
    question: str
    country: str | None
    category: str | None
    status: AnswerStatus
    answer: str
    question_parts: list[str]
    claims: list[ProgramClaim]
    unanswered_parts: list[ProgramUnanswered]
    candidate_programs: list[ProgramInfo]
    retrieved_programs: list[ProgramInfo]
    answered_programs: list[ProgramInfo]
    programs_without_retrieved_evidence: list[ProgramInfo]
    evidence: list[dict[str, Any]]
    retrieval_limit: int
    coverage_note: Literal[COVERAGE_NOTE, PRODUCTION_COVERAGE_NOTE] = COVERAGE_NOTE
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
        if self.coverage_note != COVERAGE_NOTES[self.release_mode]:
            raise ValueError("release_mode에 맞지 않는 범위 안내입니다.")
        candidates = {p.program_id: p for p in self.candidate_programs}
        if len(candidates) != len(self.candidate_programs):
            raise ValueError("후보 프로그램이 중복되었습니다.")
        retrieved = {pid for row in self.evidence for pid in row["program_ids"]}
        answered = {claim.program_id for claim in self.claims}
        for records, ids in (
            (self.retrieved_programs, retrieved),
            (self.answered_programs, answered),
            (self.programs_without_retrieved_evidence, set(candidates) - retrieved),
        ):
            if records != [candidates[pid] for pid in sorted(ids) if pid in candidates] or not ids <= candidates.keys():
                raise ValueError("프로그램 범위 목록이 근거·주장과 다릅니다.")

        owners = {}
        for claim in self.claims:
            if (claim.program_id not in candidates
                    or claim.program_name != candidates[claim.program_id].name
                    or not claim.citations or len(claim.part_indexes) != 1):
                raise ValueError("주장과 프로그램의 연결이 잘못되었습니다.")
            for citation in claim.citations:
                if (citation.program_id != claim.program_id
                        or citation.program_name != claim.program_name):
                    raise ValueError("주장과 인용의 프로그램이 다릅니다.")
            index = claim.part_indexes[0]
            if index in owners:
                raise ValueError("같은 질문 항목을 중복 답변했습니다.")
            owners[index] = claim.program_id
        for part in self.unanswered_parts:
            if part.program_id is None:
                if part.program_name is not None:
                    raise ValueError("범위 전체의 근거 부족에 프로그램명이 붙었습니다.")
            elif (part.program_id not in candidates
                    or part.program_name != candidates[part.program_id].name):
                raise ValueError("미답변 항목의 프로그램이 잘못되었습니다.")
            if not 0 <= part.part_index < len(self.question_parts):
                raise ValueError("미답변 항목의 인덱스가 범위를 벗어났습니다.")
            if part.question_part != self.question_parts[part.part_index]:
                raise ValueError("미답변 항목과 질문 항목이 다릅니다.")
        # Duplicate wording across different programs is valid. Reuse the old
        # coverage/status check with a program-qualified identity per item.
        owners.update({p.part_index: p.program_id for p in self.unanswered_parts})
        qualified = [json.dumps([owners.get(i), text], ensure_ascii=False)
                     for i, text in enumerate(self.question_parts)]
        _validate_coverage(
            self.status, qualified, self.claims,
            [part.part_index for part in self.unanswered_parts],
        )
        return self

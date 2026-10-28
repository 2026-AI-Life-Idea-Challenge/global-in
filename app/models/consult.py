"""상담(C 파트) 공통 계약. 사용자 이해·준비 안내 에이전트와 A·B·D가 주고받는 형식."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.program import Country

Purpose = Literal["working_holiday", "study", "employment"]
Intent = Literal["recommend", "check", "prepare", "update_info", "other"]

# A(자격 검토)의 overall / outcome 값
Outcome = Literal["조건 충족", "조건 미충족", "추가 확인 필요"]
Judgeability = Literal["rule_based", "conditional", "manual_check"]


# ---------- 사용자 프로필 ----------

class UserProfile(BaseModel):
    """모르는 값은 None. A에는 model_dump() 결과를 넘긴다."""

    model_config = ConfigDict(extra="forbid")

    target_country: Country | None = None
    purpose: Purpose | None = None
    age: int | None = Field(default=None, ge=15, le=80)
    education: str | None = None
    language_scores: dict[str, str] = Field(default_factory=dict)
    funds_krw: int | None = Field(default=None, ge=0)
    prior_visa_history: list[str] = Field(default_factory=list)


class ProfileDelta(BaseModel):
    """사용자 이해 에이전트(LLM)가 한 발화에서 뽑아내는 값. 언급 안 된 필드는 None."""

    intent: Intent = "other"
    target_country: Country | None = None
    purpose: Purpose | None = None
    age: int | None = None
    education: str | None = None
    language_scores: dict[str, str] | None = None
    funds_krw: int | None = None
    prior_visa_history: list[str] | None = None

    def updates(self) -> dict[str, Any]:
        return self.model_dump(exclude={"intent"}, exclude_none=True)


# ---------- B (탐색·근거) ----------

class Citation(BaseModel):
    """답변에 붙이는 출처. knowledge_documents.source_references 기준."""

    chunk_id: str
    title: str
    source_url: str


class ProgramCandidate(BaseModel):
    program_id: str  # 예: "CA:iec_working_holiday"
    name: str
    country: Country
    purpose: Purpose
    summary: str
    citations: list[Citation] = Field(default_factory=list)


# ---------- A (자격 검토) — A가 C에 넘기는 payload ----------

class RequirementPayload(BaseModel):
    requirement_id: str
    outcome: Outcome
    judgeability: Judgeability
    pending_reviews: list[Any] = Field(default_factory=list)


class EligibilityPayload(BaseModel):
    program_id: str
    overall: Outcome
    requirements: list[RequirementPayload]
    unknown_requirement_ids: list[str] = Field(default_factory=list)


# ---------- D (화면) — 상담 API ----------

class FollowUpQuestion(BaseModel):
    field: str
    question: str
    input_type: Literal["text", "number", "select"]
    options: list[str] = Field(default_factory=list)


class PrepItem(BaseModel):
    id: str
    program_id: str
    title: str
    description: str
    status: Literal["todo", "check_needed", "blocked"]
    done: bool = False
    citations: list[Citation] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ProfileUpdateRequest(BaseModel):
    """화면에서 조건을 직접 수정할 때. 보낸 필드만 바뀐다."""

    model_config = ConfigDict(extra="forbid")

    target_country: Country | None = None
    purpose: Purpose | None = None
    age: int | None = Field(default=None, ge=15, le=80)
    education: str | None = None
    language_scores: dict[str, str] | None = None
    funds_krw: int | None = Field(default=None, ge=0)
    prior_visa_history: list[str] | None = None


class ChatResponse(BaseModel):
    session_id: str
    stage: Literal["asking", "result"]
    reply: str
    follow_up_questions: list[FollowUpQuestion] = Field(default_factory=list)
    profile: UserProfile
    programs: list[ProgramCandidate] = Field(default_factory=list)
    eligibility: list[EligibilityPayload] = Field(default_factory=list)
    prep_items: list[PrepItem] = Field(default_factory=list)

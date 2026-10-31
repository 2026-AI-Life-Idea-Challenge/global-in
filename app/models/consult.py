"""상담(C 파트) 공통 계약. 사용자 이해·준비 안내 에이전트와 A·B·D가 주고받는 형식."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.program import Country
from app.models.user_profile import UserProfile

# 공통 UserProfile.target_visa_type 값
VisaType = Literal["working_holiday", "student", "employment"]
Intent = Literal["recommend", "check", "prepare", "update_info", "other"]

# A(자격 검토)의 overall / outcome 값
Outcome = Literal["조건 충족", "조건 미충족", "추가 확인 필요"]
Judgeability = Literal["rule_based", "conditional", "manual_check"]


# ---------- 사용자 프로필 (공통 UserProfile은 app/models/user_profile.py) ----------

class ProfileDelta(BaseModel):
    """사용자 이해 에이전트(LLM)가 한 발화에서 뽑아내는 값. 언급 안 된 필드는 None."""

    intent: Intent = "other"
    date_of_birth: str | None = None
    nationalities: list[str] | None = None
    target_country: Country | None = None
    target_visa_type: VisaType | None = None
    purpose: str | None = None

    def updates(self) -> dict[str, Any]:
        return self.model_dump(exclude={"intent"}, exclude_none=True)


class ProfileUpdateRequest(BaseModel):
    """공통 UserProfile에 넣기 전 C가 받는 값의 검증. 화면 PATCH와 LLM 추출값 모두 이걸 거친다."""

    model_config = ConfigDict(extra="forbid")

    date_of_birth: date | None = None
    nationalities: list[str] | None = None
    residence_country: str | None = Field(default=None, pattern=r'^[A-Z]{2}$')
    education: str | None = Field(default=None, max_length=500)
    education_status: str | None = Field(default=None, max_length=500)
    major: str | None = Field(default=None, max_length=500)
    career: str | None = Field(default=None, max_length=500)
    career_duration: str | None = Field(default=None, max_length=500)
    languages: str | None = Field(default=None, max_length=500)
    certifications: str | None = Field(default=None, max_length=500)
    target_country: Country | None = None
    target_visa_type: VisaType | None = None
    purpose: str | None = Field(default=None, max_length=500)

    @model_validator(mode='before')
    @classmethod
    def _ignore_unset_response_only_fields(cls, value):
        # UserProfile responses include nullable internal fields. Null means no
        # user input; non-null unknown fields still fail the strict contract.
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key in cls.model_fields or item is not None}
        return value

    @field_validator("date_of_birth")
    @classmethod
    def _plausible_birth_date(cls, value: date | None) -> date | None:
        if value is not None and not (date(date.today().year - 80, 1, 1) <= value <= date.today()):
            raise ValueError("date_of_birth out of range")
        return value

    @field_validator("nationalities")
    @classmethod
    def _iso_alpha2(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and not all(len(code) == 2 and code.isascii() and code.isalpha() for code in value):
            raise ValueError("nationalities must be ISO 3166-1 alpha-2 codes")
        return [code.upper() for code in value] if value is not None else None


# ---------- B (탐색·근거) ----------

class Citation(BaseModel):
    """답변에 붙이는 출처. knowledge_documents.source_references 기준."""

    chunk_id: str
    title: str
    source_url: str
    verified_at: str | None = None
    content_review_status: str | None = None
    quote: str | None = None


class ProgramCandidate(BaseModel):
    program_id: str  # 예: "CA:iec_working_holiday"
    name: str
    country: Country
    visa_type: VisaType
    summary: str
    citations: list[Citation] = Field(default_factory=list)


# ---------- A (자격 검토) — A가 C에 넘기는 payload ----------

class RequirementPayload(BaseModel):
    requirement_id: str
    outcome: Outcome
    judgeability: Judgeability
    pending_reviews: list[Any] = Field(default_factory=list)
    reason: str | None = None
    description: str | None = None


class EligibilityPayload(BaseModel):
    program_id: str
    overall: Outcome
    requirements: list[RequirementPayload]
    unknown_requirement_ids: list[str] = Field(default_factory=list)


# ---------- D (화면) — 상담 API ----------

class FollowUpQuestion(BaseModel):
    field: str
    question: str
    input_type: Literal["text", "number", "select", "date"]
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
    profile: ProfileUpdateRequest | None = None


class SupportCandidate(BaseModel):
    support_program_id: str
    name: str
    availability: str = 'UNKNOWN'
    source_verified_at: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class SupportEligibilityPayload(BaseModel):
    support_program_id: str
    overall: Outcome
    requirements: list[RequirementPayload] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    stage: Literal["asking", "result"]
    reply: str
    follow_up_questions: list[FollowUpQuestion] = Field(default_factory=list)
    profile: UserProfile
    programs: list[ProgramCandidate] = Field(default_factory=list)
    eligibility: list[EligibilityPayload] = Field(default_factory=list)
    prep_items: list[PrepItem] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    support_programs: list[SupportCandidate] = Field(default_factory=list)
    support_eligibility: list[SupportEligibilityPayload] = Field(default_factory=list)
    rag_statuses: list[dict[str, Any]] = Field(default_factory=list)
    answer_sections: list[dict[str, Any]] = Field(default_factory=list)

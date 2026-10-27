
from typing import Any, Literal

from pydantic import BaseModel, Field


Country = Literal[
    "japan",
    "australia",
    "usa",
    "germany",
    "canada",
]

SupportCountry = Country | Literal["multi_country"]


class Program(BaseModel):
    """국가별 비자·체류 프로그램의 공통 표현."""

    program_id: str
    country: Country
    name: str

    category: str | None = None
    route_id: str | None = None
    visa_subclass: str | None = None
    stream: str | None = None

    source_program_id: str | None = None
    source_file: str | None = None

    review_status: str = "needs_review"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SupportProgram(BaseModel):
    """비자 프로그램과 분리되는 지원사업."""

    support_program_id: str
    country: SupportCountry
    name: str

    provider: str | None = None
    source_file: str | None = None

    review_status: str = "needs_review"
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    """공식 자료에서 추출한 근거의 공통 표현."""

    evidence_id: str
    program_id: str
    country: Country

    source_evidence_id: str | None = None
    source_id: str | None = None
    source_url: str | None = None
    source_file: str | None = None
    source_sha256: str | None = None

    exact_quote: str | None = None
    source_location: str | None = None

    review_status: str = "needs_review"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyCandidate(BaseModel):
    """법적 검토 및 승인 전의 정책 후보."""

    policy_id: str
    program_id: str
    country: Country

    topic: str | None = None
    source_evidence_ids: list[str] = Field(default_factory=list)
    policy_text: str | None = None

    review_status: str = "needs_review"

    legal_validation_approved: bool = False
    approved_for_eligibility_decision: bool = False
    approved_for_embedding: bool = False
    approved_for_user_answers: bool = False

    metadata: dict[str, Any] = Field(default_factory=dict)
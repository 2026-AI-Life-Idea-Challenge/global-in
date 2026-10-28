"""Versioned data contracts shared by all five agent roles.

Content review, source authority, availability and individual eligibility are
independent. Unknown source dates and applicability remain explicit.
"""
from datetime import date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Availability(str, Enum):
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    UPCOMING = 'UPCOMING'
    UNKNOWN = 'UNKNOWN'


class TargetRef(BaseModel):
    model_config = ConfigDict(extra='forbid')
    target_type: Literal['PROGRAM', 'SUPPORT_PROGRAM']
    target_id: str = Field(min_length=1)


class SourceRef(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_url: HttpUrl
    title: str
    official_organization: str
    source_type: Literal['law', 'administrative_guidance', 'support_notice', 'institution_guidance', 'faq']
    publisher_countries: list[str]
    published_at: date | None = None
    updated_at: date | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    verified_at: date
    capture_file: str
    capture_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    capture_kind: str


class SupportProfile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['knowledge-v1'] = 'knowledge-v1'
    support_program_id: str
    name: str
    provider: str
    publisher_countries: list[str]
    destination_countries: list[str]
    topics: list[str]
    korean_applicability: Literal['explicit_korean_scope', 'all_nationalities_conditional', 'international_student_conditional', 'unknown']
    applicability_conditions: list[str]
    eligibility_summary: str
    benefits_summary: str
    application_method: str
    application_region: str | None = None
    availability: Availability = Availability.UNKNOWN
    availability_scope: str
    application_start: date | None = None
    application_end: date | None = None
    mandatory_documents: list[str] = Field(default_factory=list)
    conditional_documents: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    source: SourceRef
    additional_sources: list[SourceRef] = Field(default_factory=list)
    judgeability: Literal['manual_check', 'conditional'] = 'manual_check'
    automatic_eligibility_approved: Literal[False] = False

    @model_validator(mode='after')
    def validate_window(self):
        if self.application_start and self.application_end and self.application_start > self.application_end:
            raise ValueError('application window is reversed')
        if self.availability == Availability.OPEN and not self.availability_scope.strip():
            raise ValueError('OPEN requires a verified scope')
        return self


class Requirement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    requirement_id: str
    target: TargetRef
    source_document_ids: list[str] = Field(min_length=1)
    judgeability: Literal['rule_based', 'manual_check', 'conditional']
    expression: dict[str, Any]
    description: str
    effective_from: date | None = None
    effective_until: date | None = None
    verified_at: date
    all_requirements_complete: Literal[False] = False
    execution_path_complete: bool = False


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_id: str
    revision_id: str
    targets: list[TargetRef] = Field(min_length=1)
    title: str
    text: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    knowledge_kind: Literal['official_excerpt', 'reviewed_policy', 'reviewer_interpretation']
    source_references: list[dict[str, Any]] = Field(min_length=1)
    publisher_countries: list[str]
    destination_countries: list[str]
    topics: list[str]
    verified_at: date
    official_published_at: date | None = None
    official_updated_at: date | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    content_review_status: Literal['checked_scope_limited'] = 'checked_scope_limited'
    application_availability: Availability = Availability.UNKNOWN
    active: bool = True
    embedding_approved: Literal[False] = False
    eligibility_decision_approved: Literal[False] = False
    answer_approved: Literal[False] = False
    uncertainty: list[str] = Field(default_factory=list)

"""
app/agent/state.py

LangGraph 기반 에이전트 간 공유 상태 정의.
모든 에이전트는 이 AgentState 를 읽고 업데이트합니다.
"""
from __future__ import annotations

from typing import Any, Literal
from typing_extensions import TypedDict, Annotated
import operator


# ── 단순 Append-merge 헬퍼 ─────────────────────────────────────────────────
def _append(a: list, b: list) -> list:
    """LangGraph reducer: 두 리스트를 합칩니다."""
    return (a or []) + (b or [])


# ── Next-node 결정에 쓰이는 상수 ──────────────────────────────────────────
NextNode = Literal[
    "user_understanding",
    "route_recommendation",
    "eligibility_review",
    "official_information",
    "preparation_planning",
    "ask_user",          # 추가 질문이 필요할 때 종료 지점
    "end",
]


# ── 대화 메시지 단일 Turn ──────────────────────────────────────────────────
class Message(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


# ── 자격 검토 결과 ─────────────────────────────────────────────────────────
class EligibilityResult(TypedDict):
    target_type: Literal["program", "support_program"]
    target_id: str
    status: Literal["조건 충족", "조건 미충족", "추가 확인 필요"]
    condition_results: list[dict[str, Any]]
    missing_conditions: list[str]
    review_requests: list[dict[str, Any]]


# ── 검색된 공식 문서 청크 ─────────────────────────────────────────────────
class RetrievedDocument(TypedDict):
    chunk_id: str
    document_id: str
    content: str
    destination_country: str | None
    program_id: str | None
    support_program_id: str | None
    information_topic: str | None
    official_agency: str | None
    source_title: str | None
    source_url: str | None
    original_updated_at: str | None
    verified_at: str | None
    score: float


# ── 검증된 공식 근거 ──────────────────────────────────────────────────────
class ValidatedEvidence(TypedDict):
    chunk_id: str
    content: str
    official_agency: str | None
    source_title: str | None
    source_url: str | None
    verified_at: str | None
    is_valid: bool
    validation_notes: str


# ── Checklist 항목 ─────────────────────────────────────────────────────────
class ChecklistItem(TypedDict):
    item_id: str
    category: Literal["visa", "support_program", "common"]
    target_id: str | None
    title: str
    description: str
    status: Literal["완료", "준비 필요", "추가 확인"]
    stage: Literal["preparation", "application", "post_approval", "pre_departure", "post_entry"]
    required: bool


# ── Roadmap 단계 ───────────────────────────────────────────────────────────
class RoadmapStep(TypedDict):
    step_id: str
    stage: str
    title: str
    description: str
    target_ids: list[str]
    estimated_period: str | None
    official_deadline: str | None
    next_action: str


# ── 공유 Agent State ───────────────────────────────────────────────────────
class AgentState(TypedDict):
    # 세션 식별
    session_id: str

    # 현재 사용자 입력
    user_query: str

    # 대화 히스토리 (LangGraph reducer: append)
    history: Annotated[list[Message], _append]

    # 사용자 프로필 (점진적으로 채워짐)
    user_profile: dict[str, Any]

    # 의도 분류
    intent: str

    # 사용자 프로필 중 아직 확인되지 않은 필드들
    missing_fields: list[str]

    # 에이전트가 사용자에게 되묻는 질문 (있으면 ask_user 노드로 이동)
    follow_up_question: str | None

    # 진출 경로 탐색 결과
    candidate_countries: list[str]
    candidate_programs: list[dict[str, Any]]
    candidate_support_programs: list[dict[str, Any]]

    # 현재 선택된 프로그램 (자격 검토·준비 계획 단계에서 사용)
    selected_program: dict[str, Any] | None

    # 자격 검토 결과
    eligibility_results: list[EligibilityResult]

    # RAG 검색 결과
    retrieved_documents: Annotated[list[RetrievedDocument], _append]

    # 검증 완료된 공식 근거
    validated_evidence: list[ValidatedEvidence]

    # 준비 Checklist
    checklist: list[ChecklistItem]

    # 단계별 Roadmap
    roadmap: list[RoadmapStep]

    # 최종 응답 (사용자에게 전달)
    final_answer: str

    # 다음 실행할 노드 (router 결정)
    next_node: NextNode

    # 현재 처리 중인 에이전트 이름 (디버그·로깅용)
    current_agent: str


def initial_state(
    session_id: str,
    user_query: str,
    history: list[Message] | None = None,
    user_profile: dict[str, Any] | None = None,
) -> AgentState:
    """
    새 대화 턴의 초기 AgentState 를 생성합니다.
    기존 user_profile 이 있으면 이어서 사용합니다.
    """
    return AgentState(
        session_id=session_id,
        user_query=user_query,
        history=history or [],
        user_profile=user_profile or {},
        intent="",
        missing_fields=[],
        follow_up_question=None,
        candidate_countries=[],
        candidate_programs=[],
        candidate_support_programs=[],
        selected_program=None,
        eligibility_results=[],
        retrieved_documents=[],
        validated_evidence=[],
        checklist=[],
        roadmap=[],
        final_answer="",
        next_node="user_understanding",
        current_agent="",
    )

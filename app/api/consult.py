"""상담 API (D 연동용). main.py에서 내부 API 키 검사와 함께 등록된다.

POST  /consult/sessions                    → {"session_id"}
POST  /consult/sessions/{id}/messages      {"message"}   → ChatResponse
PATCH /consult/sessions/{id}/profile       {필드: 값}    → ChatResponse (조건 수정 후 재검토)
"""

import uuid

from fastapi import APIRouter, HTTPException

from app.agent.graph import build_graph
from app.agent.user_understanding import llm_extractor
from app.models.consult import ChatRequest, ChatResponse, ProfileUpdateRequest
from app.models.user_profile import UserProfile


def create_router(graph=None) -> APIRouter:
    router = APIRouter(prefix="/consult", tags=["consult"])
    sessions: set[str] = set()
    holder = {"graph": graph}

    def run(session_id: str, user_message: str | None, profile_updates: dict) -> ChatResponse:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="session not found")
        if holder["graph"] is None:  # LLM 클라이언트는 첫 요청 때 만든다 (API 키 없이도 import 가능)
            holder["graph"] = build_graph(llm_extractor())
        state = holder["graph"].invoke(
            {"user_message": user_message, "profile_updates": profile_updates},
            config={"configurable": {"thread_id": session_id}},
        )
        return ChatResponse(
            session_id=session_id,
            stage=state["stage"],
            reply=state["reply"],
            follow_up_questions=state.get("follow_up_questions", []),
            profile=state.get("profile") or UserProfile(),
            programs=state.get("programs", []),
            eligibility=state.get("eligibility", []),
            prep_items=state.get("prep_items", []),
        )

    @router.post("/sessions")
    def create_session() -> dict:
        session_id = uuid.uuid4().hex
        sessions.add(session_id)
        return {"session_id": session_id}

    @router.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: ChatRequest) -> ChatResponse:
        return run(session_id, body.message, {})

    @router.patch("/sessions/{session_id}/profile")
    def update_profile(session_id: str, body: ProfileUpdateRequest) -> ChatResponse:
        return run(session_id, None, body.model_dump(mode="json", exclude_none=True))

    return router

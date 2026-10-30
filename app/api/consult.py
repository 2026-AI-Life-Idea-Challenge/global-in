"""상담 API (D 연동용). main.py에서 내부 API 키 검사와 함께 등록된다.

POST  /consult/sessions                    → {"session_id"}
POST  /consult/sessions/{id}/messages      {"message"}   → ChatResponse
PATCH /consult/sessions/{id}/profile       {필드: 값}    → ChatResponse (조건 수정 후 재검토)
"""

import uuid
import logging

from fastapi import APIRouter, HTTPException

from app.agent.graph import get_compiled_graph
from app.agent.state import initial_state
from copy import deepcopy
from threading import Lock
from app.models.consult import ChatRequest, ChatResponse, ProfileUpdateRequest
from app.models.user_profile import UserProfile


def create_router(graph=None) -> APIRouter:
    router = APIRouter(prefix="/consult", tags=["consult"])
    sessions: dict[str, dict] = {}
    locks: dict[str, Lock] = {}
    holder = {"graph": graph}

    def run(session_id: str, user_message: str | None, profile_updates: dict) -> ChatResponse:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="session not found")
        # The current graph takes a complete AgentState and has no checkpointer.
        if not locks[session_id].acquire(blocking=False):
            raise HTTPException(status_code=409, detail="session request in progress")
        try:
            previous = sessions[session_id]
            profile = {**previous.get('user_profile', {}), **profile_updates}
            query = user_message or '변경한 프로필을 반영해 기존 결과를 다시 검토해 주세요.'
            incoming = initial_state(session_id, query, deepcopy(previous.get('history', [])), profile)
            incoming['candidate_programs'] = deepcopy(previous.get('candidate_programs', []))
            incoming['candidate_support_programs'] = deepcopy(previous.get('candidate_support_programs', []))
            if holder['graph'] is None:
                holder['graph'] = get_compiled_graph()
            state = holder['graph'].invoke(incoming)
            response = to_response(session_id, state)
            state['history'] = previous.get('history', []) + [dict(role='user', content=query), dict(role='assistant', content=response.reply)]
            sessions[session_id] = state
            return response
        except HTTPException:
            raise
        except Exception:
            logging.getLogger(__name__).exception('Consultation failed')
            raise HTTPException(status_code=503, detail='consultation temporarily unavailable') from None
        finally:
            locks[session_id].release()

    def to_response(session_id, state):
        question = state.get('follow_up_question')
        programs = []
        for item in state.get('candidate_programs', []):
            category = item.get('visa_type') or item.get('category')
            category = 'student' if category == 'study' else category
            if category in ('working_holiday', 'student', 'employment'):
                programs.append(dict(program_id=item['program_id'], name=item['name'], country=item['country'], visa_type=category,
                                     summary=item.get('description') or item.get('recommendation_reason') or '', citations=[]))
        eligibility = []
        for item in state.get('eligibility_results', []):
            if item.get('target_type') == 'program':
                eligibility.append(dict(program_id=item['target_id'], overall=item['status'], requirements=[
                    dict(requirement_id=condition.get('requirement_id') or condition.get('policy_id') or '',
                         outcome=condition.get('status', '추가 확인 필요'), judgeability=condition.get('judgeability', 'manual_check'),
                         pending_reviews=condition.get('review_requests', [])) for condition in item.get('condition_results', [])]))
        return ChatResponse(
            session_id=session_id,
            stage='asking' if question else 'result',
            reply=question or state.get('final_answer') or '확인된 결과가 없습니다. 질문을 구체적으로 알려주세요.',
            follow_up_questions=[dict(field='additional_information', question=question, input_type='text')] if question else [],
            profile=state.get('user_profile') or UserProfile(), programs=programs, eligibility=eligibility,
            prep_items=[dict(id=item['item_id'], program_id=item.get('target_id') or '', title=item['title'],
                             description=item.get('description', ''), status='check_needed', done=False, citations=[])
                        for item in state.get('checklist', [])],
            citations=[dict(chunk_id=item.get('chunk_id', ''), title=item.get('source_title') or '공식 근거', source_url=item['source_url'])
                       for item in state.get('validated_evidence', []) if item.get('source_url')],
        )

    @router.post("/sessions")
    def create_session() -> dict:
        session_id = uuid.uuid4().hex
        sessions[session_id] = {}
        locks[session_id] = Lock()
        return {"session_id": session_id}

    @router.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: ChatRequest) -> ChatResponse:
        return run(session_id, body.message, {})

    @router.patch("/sessions/{session_id}/profile")
    def update_profile(session_id: str, body: ProfileUpdateRequest) -> ChatResponse:
        return run(session_id, None, body.model_dump(mode="json", exclude_unset=True))

    return router

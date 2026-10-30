"""상담 API (D 연동용). main.py에서 내부 API 키 검사와 함께 등록된다.

POST  /consult/sessions                    → {"session_id"}
POST  /consult/sessions/{id}/messages      {"message"}   → ChatResponse
PATCH /consult/sessions/{id}/profile       {필드: 값}    → ChatResponse (조건 수정 후 재검토)
"""

import uuid
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.agent.graph import get_compiled_graph
from app.agent.state import initial_state
from copy import deepcopy
from app.services.consultation_sessions import MemorySessions, SQLiteSessions, MissingSession, BusySession
from app.models.consult import ChatRequest, ChatResponse, ProfileUpdateRequest
from app.models.user_profile import UserProfile


def create_router(graph=None, store=None) -> APIRouter:
    router = APIRouter(prefix="/consult", tags=["consult"])
    if store is None:
        store = MemorySessions() if graph is not None else SQLiteSessions(
            os.environ.get('CONSULT_SESSION_DB', str(Path(__file__).resolve().parents[2]/'data/runtime/consultation.sqlite')))
    holder = {"graph": graph}

    def run(session_id: str, user_message: str | None, profile_updates: dict) -> ChatResponse:
        try:
            previous, token = store.acquire(session_id)
        except MissingSession:
            raise HTTPException(status_code=404, detail="session not found")
        except BusySession:
            raise HTTPException(status_code=409, detail="session request in progress")
        try:
            profile = {**previous.get('user_profile', {}), **profile_updates}
            scope_changed = any(field in profile_updates and profile_updates[field] != previous.get('user_profile', {}).get(field)
                                for field in ('target_country', 'target_visa_type'))
            query = user_message or '변경한 프로필을 반영해 기존 결과를 다시 검토해 주세요.'
            incoming = initial_state(session_id, query, deepcopy(previous.get('history', [])), profile)
            incoming['profile_updated'] = user_message is None
            incoming['information_scope'] = 'both' if user_message is None and scope_changed else previous.get('information_scope', 'both')
            incoming['requested_program_ids'] = [] if scope_changed else previous.get('requested_program_ids', [])
            incoming['requested_support_ids'] = [] if scope_changed else previous.get('requested_support_ids', [])
            incoming['candidate_programs'] = deepcopy(previous.get('candidate_programs', []))
            incoming['candidate_support_programs'] = deepcopy(previous.get('candidate_support_programs', []))
            if holder['graph'] is None:
                holder['graph'] = get_compiled_graph()
            state = holder['graph'].invoke(incoming)
            response = to_response(session_id, state)
            state['history'] = previous.get('history', []) + [dict(role='user', content=query), dict(role='assistant', content=response.reply)]
            store.commit(session_id, token, state)
            return response
        except BusySession:
            raise HTTPException(status_code=409, detail='session lease expired; retry the request') from None
        except HTTPException:
            raise
        except Exception:
            logging.getLogger(__name__).exception('Consultation failed')
            raise HTTPException(status_code=503, detail='consultation temporarily unavailable') from None
        finally:
            store.release(session_id, token)

    def to_response(session_id, state):
        def citations(items):
            return [dict(chunk_id=item.get('chunk_id', ''), title=item.get('source_title') or item.get('title') or '공식 근거',
                         source_url=url, verified_at=str(item['verified_at']) if item.get('verified_at') else None,
                         content_review_status=item.get('content_review_status'))
                    for item in items for url in ([item['source_url']] if item.get('source_url') else item.get('source_urls', []))
                    if isinstance(url, str) and url.startswith(('https://', 'http://'))]
        question = state.get('follow_up_question')
        def support_sources(support):
            profile = support.get('profile') or {}
            sources = [profile.get('source') or {}] + (profile.get('additional_sources') or [])
            return citations([dict(source, chunk_id='support-profile:'+support['support_program_id']) for source in sources if isinstance(source, dict)])
        evidence = state.get('validated_evidence', [])
        programs = []
        for item in state.get('candidate_programs', []):
            category = item.get('visa_type') or item.get('category')
            category = 'student' if category == 'study' else category
            if category in ('working_holiday', 'student', 'employment'):
                programs.append(dict(program_id=item['program_id'], name=item['name'], country=item['country'], visa_type=category,
                                     summary=item.get('description') or item.get('recommendation_reason') or '공식 조건 확인이 필요한 후보입니다.',
                                     citations=citations([e for e in evidence if e.get('program_id') == item['program_id']])))
        eligibility = []
        for item in state.get('eligibility_results', []):
            if item.get('target_type') == 'program':
                eligibility.append(dict(program_id=item['target_id'], overall=item['status'], requirements=[
                    dict(requirement_id=condition.get('requirement_id') or condition.get('policy_id') or '',
                         outcome=condition.get('status', '추가 확인 필요'), judgeability=condition.get('judgeability', 'manual_check'),
                         pending_reviews=condition.get('review_requests', []), reason=condition.get('reason')) for condition in item.get('condition_results', [])],
                    unknown_requirement_ids=[c.get('requirement_id', '') for c in item.get('condition_results', []) if c.get('status') == '추가 확인 필요']))
        return ChatResponse(
            session_id=session_id,
            stage='asking' if question else 'result',
            reply=question or state.get('final_answer') or '확인된 결과가 없습니다. 질문을 구체적으로 알려주세요.',
            follow_up_questions=[dict(field='additional_information', question=question, input_type='text')] if question else [],
            profile=state.get('user_profile') or UserProfile(), programs=programs, eligibility=eligibility,
            prep_items=[dict(id=item['item_id'], program_id=item.get('target_id') or '', title=item['title'],
                             description=item.get('description', ''), status='check_needed', done=False, citations=citations(item.get('citations', [])))
                        for item in state.get('checklist', [])],
            citations=citations(evidence),
            support_programs=[dict(support_program_id=s['support_program_id'], name=s['name'], availability=s.get('availability') or 'UNKNOWN',
                                   source_verified_at=str(s['source_verified_at']) if s.get('source_verified_at') else None,
                                   citations=citations([e for e in evidence if e.get('support_program_id') == s['support_program_id']]) or support_sources(s))
                              for s in state.get('candidate_support_programs', [])],
            support_eligibility=[dict(support_program_id=r['target_id'], overall=r['status'], requirements=[
                dict(requirement_id=c.get('requirement_id', ''), outcome=c['status'], judgeability=c.get('judgeability', 'manual_check'),
                     pending_reviews=c.get('review_requests', []), reason=c.get('reason')) for c in r.get('condition_results', [])])
                for r in state.get('eligibility_results', []) if r['target_type'] == 'support_program'],
            rag_statuses=[dict(status=r['status'], target_id=r.get('program_id') or r.get('support_program_id'),
                               development_only=r.get('development_only', True), release_mode=r.get('release_mode', 'development'),
                               unanswered_parts=r.get('unanswered_parts', [])) for r in state.get('rag_results', [])],
        )

    @router.post("/sessions")
    def create_session() -> dict:
        session_id = store.create()
        return {"session_id": session_id}

    @router.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: ChatRequest) -> ChatResponse:
        return run(session_id, body.message, body.profile.model_dump(mode='json', exclude_unset=True) if body.profile else {})

    @router.patch("/sessions/{session_id}/profile")
    def update_profile(session_id: str, body: ProfileUpdateRequest) -> ChatResponse:
        return run(session_id, None, body.model_dump(mode="json", exclude_unset=True))

    return router

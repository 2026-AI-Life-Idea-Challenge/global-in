"""상담 API (D 연동용). main.py에서 내부 API 키 검사와 함께 등록된다.

POST  /consult/sessions                    → {"session_id"}
POST  /consult/sessions/{id}/messages      {"message"}   → ChatResponse
PATCH /consult/sessions/{id}/profile       {필드: 값}    → ChatResponse (조건 수정 후 재검토)
"""

import uuid
import logging
import os
import re
from threading import BoundedSemaphore
import time
from app.services import request_budget, tracing
from pathlib import Path

from fastapi import APIRouter, HTTPException, Header

from app.agent.graph import get_compiled_graph
from app.agent.state import initial_state
from copy import deepcopy
from app.services.consultation_sessions import MemorySessions, SQLiteSessions, MissingSession, BusySession
from app.models.consult import ChatRequest, ChatResponse, ProfileUpdateRequest, PreparationRequest
from app.models.user_profile import UserProfile


def create_router(graph=None, store=None, require_owner=None) -> APIRouter:
    router = APIRouter(prefix="/consult", tags=["consult"])
    require_owner = graph is None if require_owner is None else require_owner
    if store is None:
        if os.environ.get('CONSULT_SESSION_DATABASE_URL') and graph is None:
            from app.services.postgres_sessions import PostgresSessions
            store = PostgresSessions(os.environ['CONSULT_SESSION_DATABASE_URL'])
        else:
            store = MemorySessions() if graph is not None else SQLiteSessions(
                os.environ.get('CONSULT_SESSION_DB', str(Path(__file__).resolve().parents[2]/'data/runtime/consultation.sqlite')))
    holder = {"graph": graph}
    capacity = BoundedSemaphore(max(1,int(os.environ.get('CONSULT_MAX_CONCURRENT','4'))))

    def owner_id(value):
        if not value and not require_owner: return ''
        if not value or not re.fullmatch('[a-f0-9]{64}',value):
            raise HTTPException(status_code=401,detail='consultation owner required')
        return value

    def run(session_id: str, user_message: str | None, profile_updates: dict, owner='') -> ChatResponse:
        try:
            previous, token = store.acquire(session_id, owner)
        except MissingSession:
            raise HTTPException(status_code=404, detail="session not found")
        except BusySession:
            raise HTTPException(status_code=409, detail="session request in progress")
        except Exception:
            logging.getLogger(__name__).exception('Consultation session store unavailable')
            raise HTTPException(status_code=503,detail='session store temporarily unavailable') from None
        admitted = capacity.acquire(blocking=False)
        if not admitted:
            store.release(session_id,token)
            raise HTTPException(status_code=503,detail='consultation capacity reached',headers={'Retry-After':'2'})
        deadline_token=request_budget.deadline.set(time.monotonic()+min(110,float(os.environ.get('CONSULT_REQUEST_TIMEOUT','100'))))
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
            with tracing.consult_turn(session_id=session_id, owner=owner, query=query,
                                      kind='message' if user_message is not None else 'profile-update') as (graph_kwargs, record_reply):
                state = holder['graph'].invoke(incoming, **graph_kwargs)
                response = to_response(session_id, state)
                record_reply(response.reply)
            state['history'] = (previous.get('history', []) + [dict(role='user', content=query), dict(role='assistant', content=response.reply)])[-20:]
            # Catalogs and evidence are rebuilt from current DB records each turn.
            saved={key:state[key] for key in ('user_profile','history','information_scope','requested_program_ids','requested_support_ids') if key in state}
            store.commit(session_id, token, saved)
            return response
        except BusySession:
            raise HTTPException(status_code=409, detail='session lease expired; retry the request') from None
        except HTTPException:
            raise
        except Exception:
            logging.getLogger(__name__).exception('Consultation failed')
            raise HTTPException(status_code=503, detail='consultation temporarily unavailable') from None
        finally:
            request_budget.deadline.reset(deadline_token)
            capacity.release()
            store.release(session_id, token)

    def to_response(session_id, state):
        def citations(items):
            return [dict(chunk_id=item.get('chunk_id', ''), title=item.get('source_title') or item.get('title') or '공식 근거',
                         source_url=url, verified_at=str(date) if (date := item.get('verified_at') or next(
                             (ref.get('verified_at') or ref.get('checked_at') for ref in item.get('source_references', [])
                              if isinstance(ref, dict) and ref.get('source_url') == url), None)) else None,
                         content_review_status=item.get('content_review_status'), quote=item.get('quote') or item.get('content'))
                    for item in items for url in ([item['source_url']] if item.get('source_url') else item.get('source_urls', []))
                    if isinstance(url, str) and url.startswith(('https://', 'http://'))]
        question = state.get('follow_up_question')
        def support_sources(support):
            profile = support.get('profile') or {}
            sources = [profile.get('source') or {}] + (profile.get('additional_sources') or [])
            return citations([dict(source, chunk_id='support-profile:'+support['support_program_id']) for source in sources if isinstance(source, dict)])
        evidence = state.get('validated_evidence', [])
        names = {p['program_id']: p['name'] for p in state.get('candidate_programs', [])}
        names.update({s['support_program_id']: s['name'] for s in state.get('candidate_support_programs', [])})
        answer_sections = []
        for result in state.get('rag_results', []):
            for claim in result.get('claims', []):
                target = claim.get('program_id') or result.get('program_id') or result.get('support_program_id')
                labels = [result['question_parts'][i] for i in claim.get('part_indexes', []) if 0 <= i < len(result.get('question_parts', []))]
                answer_sections.append(dict(title=' · '.join(labels) or '공식 안내', text=claim['text'], target_name=names.get(target),
                                            citations=citations(claim.get('citations', [])),
                                            scope_notes=sorted({match for citation in claim.get('citations', [])
                                                for match in re.findall(r'20\d{2}년[^,.\n]{0,35}(?:기준|대상)', citation.get('quote', ''))})))
        programs = []
        for item in state.get('candidate_programs', []):
            category = item.get('visa_type') or item.get('category')
            category = 'student' if category == 'study' else category
            if category in ('working_holiday', 'student', 'employment'):
                programs.append(dict(program_id=item['program_id'], name=item['name'], country=item['country'], visa_type=category,
                                     summary=next((claim['text'] for result in state.get('rag_results', []) for claim in result.get('claims', []) if (claim.get('program_id') or result.get('program_id')) == item['program_id']), None) or item.get('description') or item.get('recommendation_reason') or '해당 경로의 신청 조건과 준비 방법을 상담에서 확인해 보세요.',
                                     citations=citations([e for e in evidence if e.get('program_id') == item['program_id']])))
        if state.get('overview'):
            programs = [program for program in programs if program['citations']]
        eligibility = []
        for item in state.get('eligibility_results', []):
            if item.get('target_type') == 'program':
                eligibility.append(dict(program_id=item['target_id'], overall=item['status'], requirements=[
                    dict(requirement_id=condition.get('requirement_id') or condition.get('policy_id') or '',
                         outcome=condition.get('status', '추가 확인 필요'), judgeability=condition.get('judgeability', 'manual_check'),
                         pending_reviews=condition.get('review_requests', []), reason=condition.get('reason'), description=condition.get('description')) for condition in item.get('condition_results', [])],
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
                     pending_reviews=c.get('review_requests', []), reason=c.get('reason'), description=c.get('description')) for c in r.get('condition_results', [])])
                for r in state.get('eligibility_results', []) if r['target_type'] == 'support_program'],
            rag_statuses=[dict(status=r['status'], target_id=r.get('program_id') or r.get('support_program_id'),
                               development_only=r.get('development_only', True), release_mode=r.get('release_mode', 'development'),
                               unanswered_parts=r.get('unanswered_parts', [])) for r in state.get('rag_results', [])],
            answer_sections=answer_sections,
        )

    @router.post("/sessions")
    def create_session(x_consult_owner: str | None = Header(default=None)) -> dict:
        owner=owner_id(x_consult_owner)
        try: session_id = store.create(owner)
        except Exception:
            raise HTTPException(status_code=503,detail='session store temporarily unavailable') from None
        return {"session_id": session_id}

    @router.post('/preparation')
    def preparation(body: PreparationRequest):
        from app.services.personal_preparation import build_preparation
        try:
            result = build_preparation(body.target_id, body.profile.model_dump(mode='json', exclude_unset=True))
        except Exception:
            logging.getLogger(__name__).exception('Preparation generation failed')
            raise HTTPException(status_code=503, detail='preparation temporarily unavailable') from None
        if result is None:
            raise HTTPException(status_code=404, detail='catalog item not found')
        return result

    @router.get('/catalog')
    def catalog():
        from app.services.consultation_catalog import load_catalog
        try:
            return load_catalog()
        except Exception:
            logging.getLogger(__name__).exception('Consultation catalog failed')
            raise HTTPException(status_code=503, detail='catalog temporarily unavailable') from None

    @router.post("/sessions/{session_id}/messages")
    def send_message(session_id: str, body: ChatRequest, x_consult_owner: str | None = Header(default=None)) -> ChatResponse:
        return run(session_id, body.message, body.profile.model_dump(mode='json', exclude_unset=True) if body.profile else {}, owner_id(x_consult_owner))

    @router.get('/catalog/{target_id}')
    def catalog_detail(target_id: str):
        from app.services.consultation_catalog import load_catalog_detail
        try: result=load_catalog_detail(target_id)
        except Exception:
            logging.getLogger(__name__).exception('Consultation detail failed')
            raise HTTPException(status_code=503,detail='catalog temporarily unavailable') from None
        if result is None:raise HTTPException(status_code=404,detail='catalog item not found')
        return result

    @router.patch("/sessions/{session_id}/profile")
    def update_profile(session_id: str, body: ProfileUpdateRequest, x_consult_owner: str | None = Header(default=None)) -> ChatResponse:
        return run(session_id, None, body.model_dump(mode="json", exclude_unset=True), owner_id(x_consult_owner))

    return router
